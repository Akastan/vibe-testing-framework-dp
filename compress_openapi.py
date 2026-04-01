"""
Komprese OpenAPI specifikace pro modely s omezeným context window.

Vstup:  inputs/openapi.yaml (~20k tokenů, ~62k znaků)
Výstup: inputs/openapi_slim.yaml (~5k tokenů, ~15k znaků)

Strategie komprese:
1. Zachová VŠECHNY endpointy, metody, parametry, status kódy
2. Inlinuje schema definice přímo do endpointů (krátký popis)
3. Odstraní redundantní 422 responses (zmíní se jednou globálně)
4. Odstraní HTTPValidationError a ValidationError schémata
5. Sloučí Create/Update/Response varianty entit do jednoho popisu

Zachovává: Co API dělá (endpointy, kontrakty, validace, status kódy)
Odstraňuje: Jak přesně vypadá JSON (detailní schema properties)

Použití:
    python compress_openapi.py
    python compress_openapi.py --input inputs/openapi.yaml --output inputs/openapi_slim.yaml
"""
import yaml
import sys
import os


# Manuálně definované kompaktní popisy schémat
# (nahrazují plné $ref schema definice)
SCHEMA_SUMMARIES = {
    "AuthorCreate": "name(str,1-100,required), bio(str?), born_year(int?,0-2026)",
    "AuthorUpdate": "name(str?,1-100), bio(str?), born_year(int?,0-2026)",
    "AuthorResponse": "id, name, bio, born_year, created_at",
    "CategoryCreate": "name(str,1-50,required), description(str?)",
    "CategoryUpdate": "name(str?,1-50), description(str?)",
    "CategoryResponse": "id, name, description",
    "BookCreate": "title(str,1-200,req), isbn(str,10-13,req), price(float,>=0,req), published_year(int,1000-2026,req), stock(int,>=0,default=0), author_id(int,req), category_id(int,req)",
    "BookUpdate": "title?, isbn?, price?, published_year?, stock?, author_id?, category_id?",
    "BookResponse": "id, title, isbn, price, published_year, stock, author_id, category_id, created_at, author{}, category{}, tags[]",
    "BookListResponse": "id, title, isbn, price, published_year, stock, author_id, category_id",
    "ReviewCreate": "rating(int,1-5,req), comment(str?), reviewer_name(str,1-100,req)",
    "ReviewResponse": "id, book_id, rating, comment, reviewer_name, created_at",
    "DiscountRequest": "discount_percent(float,gt=0,le=50,req)",
    "DiscountResponse": "book_id, title, original_price, discount_percent, discounted_price",
    "TagCreate": "name(str,1-30,req)",
    "TagUpdate": "name(str?,1-30)",
    "TagResponse": "id, name, created_at",
    "BookTagAction": "tag_ids(list[int],min=1,req)",
    "OrderCreate": "customer_name(str,1-100,req), customer_email(str,1-200,req), items(list[OrderItem],min=1,req)",
    "OrderItemCreate": "book_id(int,req), quantity(int,>=1,req)",
    "OrderItemResponse": "id, book_id, quantity, unit_price",
    "OrderResponse": "id, customer_name, customer_email, status, created_at, updated_at, items[], total_price",
    "OrderListResponse": "id, customer_name, customer_email, status, total_price, created_at",
    "OrderStatusUpdate": "status(str, one of: confirmed|shipped|delivered|cancelled)",
    "PaginatedBooks": "items[], total, page, page_size, total_pages",
    "PaginatedOrders": "items[], total, page, page_size, total_pages",
}


def compress_openapi(input_path: str, output_path: str):
    """Komprimuje OpenAPI spec do slim verze."""
    with open(input_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    slim = {
        "openapi": spec.get("openapi", "3.1.0"),
        "info": {
            "title": spec["info"]["title"],
            "version": spec["info"]["version"],
            "description": spec["info"].get("description", ""),
        },
        "note": "Compressed spec. All endpoints preserve exact paths, methods, params, and status codes. Schema details are summarized inline.",
        "validation_note": "All endpoints may return 422 for invalid input data (Pydantic validation).",
        "paths": {},
        "schemas_summary": SCHEMA_SUMMARIES,
    }

    for path, methods in spec.get("paths", {}).items():
        slim_methods = {}
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoint = {
                    "summary": details.get("summary", ""),
                }

                # Description (pokud existuje a není jen summary)
                desc = details.get("description", "")
                if desc and desc != details.get("summary", ""):
                    endpoint["description"] = desc

                # Parameters (query + path)
                params = details.get("parameters", [])
                if params:
                    compact_params = []
                    for p in params:
                        schema = p.get("schema", {})
                        param_str = f"{p['name']}({p.get('in','query')})"

                        # Přidej typ a constraints
                        ptype = schema.get("type", "")
                        if ptype:
                            constraints = []
                            if "minimum" in schema:
                                constraints.append(f">={schema['minimum']}")
                            if "maximum" in schema:
                                constraints.append(f"<={schema['maximum']}")
                            if "default" in schema:
                                constraints.append(f"default={schema['default']}")
                            if not p.get("required", False):
                                constraints.append("optional")

                            if constraints:
                                param_str += f":{ptype},{','.join(constraints)}"
                            else:
                                param_str += f":{ptype}"

                        compact_params.append(param_str)
                    endpoint["params"] = compact_params

                # Request body — schema summary
                rb = details.get("requestBody", {})
                if rb:
                    content = rb.get("content", {})
                    json_content = content.get("application/json", {})
                    schema = json_content.get("schema", {})
                    ref = schema.get("$ref", "")
                    if ref:
                        schema_name = ref.split("/")[-1]
                        if schema_name in SCHEMA_SUMMARIES:
                            endpoint["request_body"] = f"{schema_name}: {SCHEMA_SUMMARIES[schema_name]}"
                        else:
                            endpoint["request_body"] = schema_name

                # Responses — jen status kódy a stručný popis
                responses = details.get("responses", {})
                compact_responses = {}
                for code, resp in responses.items():
                    if code == "422":
                        continue  # Zmíněno globálně
                    resp_desc = resp.get("description", "")
                    content = resp.get("content", {})
                    json_content = content.get("application/json", {})
                    schema = json_content.get("schema", {})
                    ref = schema.get("$ref", "")
                    if ref:
                        schema_name = ref.split("/")[-1]
                        compact_responses[code] = f"{resp_desc} → {schema_name}"
                    else:
                        compact_responses[code] = resp_desc
                endpoint["responses"] = compact_responses

                slim_methods[method] = endpoint
        slim["paths"][path] = slim_methods

    # Zapis
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(slim, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)

    # Stats
    with open(input_path, "r", encoding="utf-8") as f:
        orig_size = len(f.read())
    with open(output_path, "r", encoding="utf-8") as f:
        slim_size = len(f.read())

    orig_tokens = orig_size // 3
    slim_tokens = slim_size // 3

    print(f"✅ Komprese dokončena:")
    print(f"   Původní:      {orig_size:,} znaků (~{orig_tokens:,} tokenů)")
    print(f"   Komprimovaná: {slim_size:,} znaků (~{slim_tokens:,} tokenů)")
    print(f"   Kompresní poměr: {slim_size/orig_size:.1%}")
    print(f"   Úspora: ~{orig_tokens - slim_tokens:,} tokenů")
    print(f"   Výstup: {output_path}")


if __name__ == "__main__":
    input_path = "inputs/openapi.yaml"
    output_path = "inputs/openapi_slim.yaml"

    if "--input" in sys.argv:
        input_path = sys.argv[sys.argv.index("--input") + 1]
    if "--output" in sys.argv:
        output_path = sys.argv[sys.argv.index("--output") + 1]

    if not os.path.exists(input_path):
        print(f"❌ Soubor {input_path} nenalezen")
        sys.exit(1)

    compress_openapi(input_path, output_path)