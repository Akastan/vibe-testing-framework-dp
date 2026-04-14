from __future__ import annotations


class PromptBuilder:
    """Builds prompts from experiment.yaml config for a given API + level."""

    _KNOWLEDGE_LEVELS = ("L1", "L2", "L3", "L4")

    def __init__(self, api_cfg: dict, level: str):
        self.api_name = api_cfg["name"]
        self.level = level
        self.base_url = api_cfg["base_url"]
        self.framework_rules: list[str] = api_cfg.get("framework_rules", [])

        if level in self._KNOWLEDGE_LEVELS:
            self.api_knowledge: list[str] = api_cfg.get("api_knowledge", [])
        else:
            self.api_knowledge = []

    # ──────────────────────────────────────────────────
    #  Internal blocks
    # ──────────────────────────────────────────────────

    def _framework_block(self) -> str:
        if not self.framework_rules:
            return ""
        lines = "\n".join(f"- {r}" for r in self.framework_rules)
        return f"\nTECHNICAL FRAMEWORK REQUIREMENTS:\n{lines}\n"

    def _knowledge_block(self) -> str:
        if not self.api_knowledge:
            return ""
        lines = "\n".join(f"- {r}" for r in self.api_knowledge)
        return (
            f"\nKNOWN BEHAVIOR OF THIS API (use when writing helpers and assertions):\n"
            f"{lines}\n"
        )

    def _stale_block(self, stale_tests: list[str] | None = None) -> str:
        if not stale_tests:
            return ""
        names = ", ".join(stale_tests)
        return (
            f"\nSTALE TESTS (do not fix, they are fundamentally unfixable):\n"
            f"{names}\n"
            f"Focus ONLY on the other failing tests.\n"
        )

    def _context_block(self, context: str, max_chars: int = 4000) -> str:
        """Truncated API context for repair prompts."""
        if not context:
            return ""
        trimmed = context[:max_chars]
        if len(context) > max_chars:
            trimmed += "\n... (truncated)"
        return f"\nAPI CONTEXT (to understand expected behavior):\n{trimmed}\n"

    # ══════════════════════════════════════════════════
    #  PHASE 2: Planning
    # ══════════════════════════════════════════════════

    def planning_prompt(self, context: str, test_count: int) -> str:
        return f"""Analyze this API and prepare to create a test plan.

API CONTEXT:
{context}
{self._knowledge_block()}
=========================================
CRITICAL INSTRUCTIONS FOR OUTPUT:
Based on the API context above, create a test plan with EXACTLY {test_count} tests.

TEST RULES:
- type = "happy_path" | "edge_case" | "error"
- name = snake_case without diacritics, unique across the entire plan
- endpoint must be the exact path from the API specification (with path parameters like {{book_id}})
- method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
- One endpoint (method+path) = one object in the array, with multiple test_cases inside
- EXACTLY {test_count} tests in total, no more, no less
- DO NOT GENERATE tests for database reset or the /reset endpoint

REQUIRED JSON STRUCTURE:
{{
  "test_plan": [
    {{
      "endpoint": "/path",
      "method": "GET",
      "test_cases": [
        {{
          "name": "test_name",
          "type": "happy_path",
          "expected_status": 200,
          "description": "Description of what the test verifies"
        }}
      ]
    }}
  ]
}}

PLAN EXACTLY {test_count} TESTS.
YOU DECIDE WHICH ENDPOINTS ARE WORTH TESTING.
YOU MUST RESPOND WITH ONLY VALID JSON. 
NO MARKDOWN, NO PROSE, NO EXPLANATIONS.
Start your response with {{ and end with }}.
"""

    def planning_fill_prompt(self, current_plan_json: str, actual: int, target: int) -> str:
        missing = target - actual
        return (
            f"This test plan has {actual} tests, but I need EXACTLY {target}.\n\n"
            f"CURRENT PLAN:\n{current_plan_json}\n\n"
            f"=========================================\n"
            f"CRITICAL INSTRUCTIONS FOR OUTPUT:\n"
            f"Add {missing} new tests. Focus on endpoints and scenarios that are not yet "
            f"sufficiently covered (edge cases, error handling, validation).\n"
            f"Return the ENTIRE plan (old + new).\n\n"
            f"YOU MUST RESPOND WITH ONLY VALID JSON.\n"
            f"NO MARKDOWN, NO PROSE, NO EXPLANATIONS.\n"
            f"Start your response with {{ and end with }}."
        )

    # ══════════════════════════════════════════════════
    #  PHASE 3: Code Generation
    # ══════════════════════════════════════════════════

    def generation_prompt(self, plan_json: str, context: str, base_url: str) -> str:
        return f"""You will write pytest tests in Python (using the requests library) for this REST API.
BASE_URL = "{base_url}"

API CONTEXT:
{context}

TEST PLAN:
{plan_json}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
1. UNIQUE NAMES (mandatory, otherwise tests will collide):
   - For unique names, use the uuid4 suffix: def unique(prefix="test"): return f"{{prefix}}_{{uuid.uuid4().hex[:8]}}"
   - This function adds 9 characters (_ + 8 unique chars). Important for length-restricted names.
   - Generate unique names in EVERY helper call.
2. ASSERTION QUALITY: Do NOT check ONLY the status code. Each test should also verify the response:
   - Happy path (201/200): verify keys in the response body (assert "id" in data)
   - Error: verify detail (assert "detail" in r.json())
   - GET list: verify structure (assert "items" in data or assert isinstance(data, list))
   - Side effects: after creation, verify stock reduction; after deletion, verify 404 on GET
3. GLOBAL STATE CLEANUP (TEARDOWN):
   - If a test changes the global API state (e.g., enabling maintenance mode, changing global settings), you MUST revert this state back to the default (disable it) at the end of the same test! 
   - If you don't do this, you will block the API and all subsequent tests will fail with 503.
4. DO NOT GENERATE tests for database reset or the /reset endpoint.

STRICTLY FOLLOW THE PLAN AND GENERATE EXACTLY THE SPECIFIED NUMBER OF TESTS.
YOU MUST RESPOND WITH ONLY VALID PYTHON CODE.
NO MARKDOWN BLOCKS (do not use ```python), NO PROSE, NO EXPLANATIONS.
"""

    # ══════════════════════════════════════════════════
    #  PHASE 3: Repairs
    # ══════════════════════════════════════════════════

    def repair_batch_prompt(
        self,
        test_entries: list[tuple[str, str, str]],
        helpers: str,
        context: str,
        base_url: str,
        stale_tests: list[str] | None = None,
    ) -> str:
        """Batch repair of multiple failing tests in a single prompt.

        Args:
            test_entries: [(test_name, test_code, error_msg), ...]
            helpers: helper functions code
            context: API context (truncated)
            base_url: API base URL
            stale_tests: list of stale tests (for info)
        """
        tests_block = ""
        for i, (name, code, error) in enumerate(test_entries, 1):
            tests_block += f"\n── TEST {i}: {name} ──\n"
            tests_block += f"CODE:\n{code}\n"
            tests_block += f"ERROR:\n{error}\n"

        return f"""Fix these failing test functions. Each test has its code and error.
BASE_URL = "{base_url}"
{self._context_block(context)}
AVAILABLE HELPERS (DO NOT MODIFY THEM, only use them):
{helpers}

FAILING TESTS ({len(test_entries)}):
{tests_block}
{self._knowledge_block()}{self._stale_block(stale_tests)}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Fix EVERY function above. Keep the exact function names.
- Use existing helper functions, do not invent new ones.
- Analyze the ERROR for each test and fix the ROOT CAUSE, not just the symptom:
  - If an assert fails on a wrong status code → check if the test sends correct data according to the API context.
  - If an assert fails on a response value → check if the test verifies the correct field/value.
  - If a test fails during setup (helper) → check if the test correctly creates prerequisites.
- Return ONLY the fixed functions (def test_...), no helpers or imports.

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (all {len(test_entries)} fixed functions).
NO MARKDOWN BLOCKS, NO PROSE, NO IMPORTS, NO HELPERS, NO EXPLANATIONS.
"""

    def repair_helpers_prompt(
            self, helpers: str, sample_errors: list[str],
            failing_count: int, context: str, base_url: str,
    ) -> str:
        errors_text = "\n".join(sample_errors)
        return f"""Most tests are failing due to bugs in helper functions. Fix the helpers.
BASE_URL = "{base_url}"
{self._context_block(context)}
CURRENT HELPERS (return the COMPLETE fixed version INCLUDING ALL imports):
{helpers}

ERROR SAMPLES ({failing_count} tests failing in total):
{errors_text}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Return the COMPLETE block: all imports + all helper functions.
- DO NOT OMIT any import or helper present in the CURRENT version above.
- Keep helper signatures compatible with existing tests.
- Ensure unique names and data using the unique function: def unique(prefix="test"): return f"{{prefix}}_{{uuid.uuid4().hex[:8]}}"
- Analyze the ERRORS and fix the ROOT CAUSE in the helpers:
  - BEWARE OF STRING LENGTHS: Count the characters of the unique function and prefix. The sum might exceed the limit.
  - If helpers send data in the wrong format → fix it according to the API context.
  - If helpers are missing required headers (API key, ETag) → add them.

OUTPUT FORMAT REQUIREMENTS:
- YOU MUST RESPOND WITH ONLY VALID PYTHON CODE (all imports + all helpers).
- NO MARKDOWN BLOCKS (` ```python `) AROUND THE CODE!
- NO PROSE OUTSIDE OF COMMENTS.
- WARNING: Before the code itself, you MUST write 1-2 lines as a Python comment (#) where you analyze the main error from the log and state how you will fix it.
"""

    def fill_tests_prompt(
        self, missing: int, helpers: str, existing_names: list[str],
        context: str, base_url: str,
    ) -> str:
        names_str = ", ".join(existing_names)
        return f"""Generate new pytest tests for this REST API.
BASE_URL = "{base_url}"

API CONTEXT:
{context[:3000]}

AVAILABLE HELPERS (use them, do not invent new ones):
{helpers}

EXISTING TESTS (DO NOT USE these names):
{names_str}
{self._knowledge_block()}{self._framework_block()}
=========================================
CRITICAL CODING INSTRUCTIONS:
- Generate EXACTLY {missing} new test functions (def test_...(): ...).
- Each test must be self-contained.
- Focus on scenarios not covered by existing tests.
- Do not just check the status code — verify the response body as well.

YOU MUST RESPOND WITH ONLY VALID PYTHON CODE ({missing} new functions).
NO MARKDOWN BLOCKS, NO IMPORTS, NO HELPERS, NO PROSE, NO EXPLANATIONS.
"""