# Cross-Model Porovnání: DeepSeek Chat vs Gemini 3.1 Flash Lite Preview

## Konfigurace experimentu

| Parametr | DeepSeek | Gemini |
|----------|----------|--------|
| Model | deepseek-chat | gemini-3.1-flash-lite-preview |
| Provider | DeepSeek (OpenAI-kompatibilní) | Google |
| Ekosystém | Čína | USA |
| Temperature | 0.4 | 0.4 |
| Max iterací | 5 | 5 |
| Runů na kombinaci | 5 | 5 |
| Testů na run | 30 | 30 |
| Stale threshold | 2 | 2 |
| API | bookstore (50 endpointů) | bookstore (50 endpointů) |

---

## 1. Validity Rate — celkový přehled

### Průměrná validity per level

| Level | DeepSeek Avg | DeepSeek Std | Gemini Avg | Gemini Std | Δ (DS−Gem) |
|-------|-------------|-------------|-----------|-----------|------------|
| **L0** | 98.67% | 1.6 | 75.33% | 11.5 | **+23.3 p.b.** |
| **L1** | 98.67% | 1.6 | 77.33% | 18.2 | **+21.3 p.b.** |
| **L2** | 98.67% | 1.6 | 85.33% | 21.3 | **+13.3 p.b.** |
| **L3** | 96.67% | 3.0 | 96.67% | 2.1 | **0.0 p.b.** |
| **L4** | 97.33% | 2.5 | 96.67% | 4.2 | **+0.7 p.b.** |

### Klíčové vzorce

**DeepSeek: vysoká baseline, plochý trend.** Validity je ≥96.67 % na všech úrovních. Kontext nepřidává validity — model generuje funkční testy již z OpenAPI specifikace (L0). Mírný pokles na L3–L4 je způsoben ambicióznějšími testy (rate limit, bulk partial).

**Gemini: monotónní růst, dramatický skok L2→L3.** Validity roste od 75.33 % (L0) k 96.67 % (L3=L4). Klíčový přelom nastává mezi L2 (85.33 %) a L3 (96.67 %), kde DB schéma eliminuje ISBN helper problém. Na L0–L2 je Gemini výrazně nestabilní (std 11–21).

**Konvergence na L3–L4:** Oba modely dosahují ~96.67 % na L3 a L4. Rozdíl se uzavírá díky tomu, že Gemini na L3+ překonává svůj hlavní problém (helper kaskádové selhání), zatímco DeepSeek tento problém nemá na žádné úrovni.

### Variabilita (stabilita)

| Level | DeepSeek Range | Gemini Range |
|-------|---------------|-------------|
| L0 | 96.67–100.0% | 60.0–86.67% |
| L1 | 96.67–100.0% | 43.33–96.67% |
| L2 | 96.67–100.0% | 43.33–100.0% |
| L3 | 93.33–100.0% | 93.33–100.0% |
| L4 | 93.33–100.0% | 90.0–100.0% |

DeepSeek má konzistentně úzký rozsah (≤6.67 p.b.) na všech úrovních. Gemini má na L0–L2 rozsah až 56.67 p.b. (L1: 43.33–96.67 %) kvůli bimodální distribuci — runy buď fungují (≥90 %) nebo masivně selhávají (≤60 %) kvůli helper kaskádě.

---

## 2. Sémantická kvalita — Assertion Depth a Response Validation

### Assertion depth

| Level | DeepSeek | Gemini | Δ |
|-------|---------|--------|---|
| L0 | 2.17 | 1.36 | **+0.81** |
| L1 | 3.25 | 1.33 | **+1.92** |
| L2 | 3.31 | 1.30 | **+2.01** |
| L3 | 3.07 | 1.29 | **+1.78** |
| L4 | 3.37 | 1.24 | **+2.13** |

DeepSeek generuje 2–3× hlubší aserce než Gemini na všech úrovních. DeepSeek assertion depth roste L0→L1 (+1.08), pak plateau. Gemini assertion depth paradoxně mírně klesá s kontextem (1.36→1.24).

### Response validation

| Level | DeepSeek (%) | Gemini (%) | Δ |
|-------|-------------|-----------|---|
| L0 | 54.0 | 28.67 | **+25.3 p.b.** |
| L1 | 90.0 | 25.33 | **+64.7 p.b.** |
| L2 | 95.33 | 25.33 | **+70.0 p.b.** |
| L3 | 95.33 | 23.33 | **+72.0 p.b.** |
| L4 | 97.34 | 22.0 | **+75.3 p.b.** |

Extrémní rozdíl: DeepSeek kontroluje response body v 90–97 % testů (L1+), Gemini jen ve 22–29 %. Gemini testy typicky ověřují pouze status kód (`assert r.status_code == 200`), DeepSeek ověřuje i strukturu a hodnoty response.

**Opačné trendy:** DeepSeek response validation roste s kontextem (54→97 %). Gemini klesá (29→22 %) — model s více kontextem generuje méně defenzivní testy.

---

## 3. Testovací strategie

### Endpoint coverage

| Level | DeepSeek (%) | Gemini (%) |
|-------|-------------|-----------|
| L0 | 40.8 | 43.6 |
| L1 | 32.4 | 40.4 |
| L2 | 33.6 | 44.0 |
| L3 | 38.8 | 45.6 |
| L4 | 36.8 | 39.2 |

Gemini pokrývá mírně více endpointů (39–46 %) než DeepSeek (32–41 %). DeepSeek na L1+ se fokusuje na menší sadu endpointů a testuje je hlouběji (vyšší assertion depth). Gemini rozhazuje testy šířeji ale povrchněji.

### Test type distribution

| Level | DeepSeek HP/Err/Edge | Gemini HP/Err/Edge |
|-------|---------------------|-------------------|
| L0 | 49/43/7 | 37/51/12 |
| L1 | 53/45/2 | 28/70/2 |
| L2 | 55/44/1 | 38/60/2 |
| L3 | 41/53/7 | 31/67/3 |
| L4 | 37/58/5 | 39/55/6 |

Gemini generuje konzistentně více error testů (55–70 %) než DeepSeek (43–58 %). DeepSeek má na L0–L2 nadpoloviční podíl happy path testů, přechod k error-first nastává až na L3. Gemini je error-first již od L1.

### Status code diversity

| Level | DeepSeek | Gemini |
|-------|---------|--------|
| L0 | 10.4 | 12.8 |
| L1 | 10.6 | 14.0 |
| L2 | 10.2 | 15.2 |
| L3 | 12.2 | 15.0 |
| L4 | 13.6 | 15.2 |

Gemini má vyšší diverzitu status kódů (13–15) oproti DeepSeek (10–14). Gemini používá více exotických kódů (301 Redirect, 304 Not Modified, 405 Method Not Allowed) již od L0. DeepSeek diverzita roste výrazně až na L3–L4.

---

## 4. Code Coverage

### Total coverage

| Level | DeepSeek Avg | Gemini Avg | Δ |
|-------|-------------|-----------|---|
| L0 | 69.6% | 64.2% | **+5.4 p.b.** |
| L1 | 71.5% | 65.4% | **+6.1 p.b.** |
| L2 | 72.5% | 68.2% | **+4.3 p.b.** |
| L3 | 72.7% | 70.7% | **+2.0 p.b.** |
| L4 | 73.5% | 70.5% | **+3.0 p.b.** |

DeepSeek dosahuje vyšší code coverage na všech úrovních. Gap se zužuje s kontextem: L0 +5.4 p.b. → L3 +2.0 p.b. Oba modely vykazují monotónní růst coverage s kontextem.

### crud.py coverage (business logika)

| Level | DeepSeek | Gemini | Δ |
|-------|---------|--------|---|
| L0 | 41.9% | 31.7% | **+10.2 p.b.** |
| L1 | 50.0% | 33.3% | **+16.7 p.b.** |
| L2 | 52.2% | 38.8% | **+13.4 p.b.** |
| L3 | 51.4% | 44.5% | **+6.9 p.b.** |
| L4 | 53.2% | 44.8% | **+8.4 p.b.** |

Největší rozdíl je v coverage business logiky (crud.py). DeepSeek proniká hlouběji do business vrstvy díky response body validaci — testy aktivují validační a kalkulační logiku v crud.py. Gemini status-code-only testy aktivují pouze routing vrstvu.

### main.py coverage (routing)

| Level | DeepSeek | Gemini | Δ |
|-------|---------|--------|---|
| L0 | 72.1% | 67.0% | +5.1 |
| L1 | 68.0% | 69.1% | −1.1 |
| L2 | 68.4% | 71.4% | −3.0 |
| L3 | 70.4% | 72.3% | −1.9 |
| L4 | 70.8% | 71.5% | −0.7 |

Na main.py (routing) jsou výsledky vyrovnané. Gemini má mírně vyšší main.py coverage na L1+ díky širšímu endpoint coverage. DeepSeek má vyšší main.py na L0 díky "rozhazování" testů.

### Gap (main.py − crud.py)

| Level | DeepSeek Gap | Gemini Gap |
|-------|-------------|-----------|
| L0 | 30.2 | 35.3 |
| L1 | 18.0 | 35.8 |
| L2 | 16.2 | 32.6 |
| L3 | 19.0 | 27.8 |
| L4 | 17.6 | 26.7 |

DeepSeek gap klesá dramaticky L0→L1 (30→18) a stabilizuje kolem 16–19 p.b. Gemini gap klesá pozvolněji (35→27 p.b.). Nižší gap = testy efektivněji pronikají do business logiky.

---

## 5. Failure Analysis

### Dominantní failure kategorie

| Kategorie | DeepSeek | Gemini |
|-----------|---------|--------|
| wrong_status_code | **67% všech selhání** | **31% (L0–L2), 72% (L3–L4)** |
| helper cascade ("other") | **0%** | **64–83% (L0–L2), 12–18% (L3–L4)** |
| assertion_value_mismatch | 20% | 3% |
| timeout | 0% | 2.5% (L2, L4) |

**Zásadní strukturální rozdíl:** Gemini na L0–L2 trpí helper kaskádovým selháním (ISBN problém v `create_book`), které tvoří 64–83 % všech chyb. DeepSeek tento problém nemá díky konzistentnímu UUID-based ISBN generování.

### Root cause: ISBN helper problém

| Aspekt | DeepSeek | Gemini |
|--------|---------|--------|
| ISBN strategie | `unique("isbn")[:13]` (UUID) | Hardcoded `'1234567890123'` nebo `hex[:13]` |
| Duplicate ISBN chyba | Nikdy | 3/5 runů na L0, 3/5 na L1, 2/5 na L2 |
| Kaskádové selhání | 0 testů | 10–17 testů per run |
| Eliminováno na | N/A | L3 (DB schéma: `VARCHAR(13)`) |

### Stale testy

| Level | DeepSeek Avg | Gemini Avg |
|-------|-------------|-----------|
| L0 | 0.4 | 7.4 |
| L1 | 0.4 | 6.8 |
| L2 | 0.4 | 4.4 |
| L3 | 1.0 | 1.0 |
| L4 | 0.8 | 1.0 |

Na L0–L2 má Gemini 11–18× více stale testů. Na L3–L4 jsou oba modely vyrovnané (0.8–1.0).

### Fix rate

| Level | DeepSeek | Gemini |
|-------|---------|--------|
| L0 | 0% | 33.3% |
| L1 | 50% | 39.1% |
| L2 | 0% | 47.5% |
| L3 | 0% | 63.6% |
| L4 | — | 62.5% |

Paradoxně, Gemini má vyšší fix rate. Důvod: Gemini generuje více failing testů (9–13 per run na L0–L2), z nichž mnohé jsou opravitelné (helper cascade po helper_fallback). DeepSeek generuje málo failing testů (0.4–1.0 per run), ale ty jsou principiálně neopravitelné (timing, boundary).

---

## 6. Repair Loop

### Iterace ke konvergenci

| Level | DeepSeek | Gemini |
|-------|---------|--------|
| L0 | 1.8 | 3.6 |
| L1 | 2.2 | 3.6 |
| L2 | 1.8 | 3.0 |
| L3 | 2.2 | 2.8 |
| L4 | 2.6 | 2.2 |

DeepSeek konverguje rychleji (1.8–2.6 iterací) než Gemini (2.2–3.6). Gemini potřebuje více iterací kvůli helper_fallback cyklu (isolated → helper → isolated → stale).

### Helper architektura

| Aspekt | DeepSeek | Gemini |
|--------|---------|--------|
| Avg helper count | 3.8–7.4 | 4.0 (konzistentně) |
| Typická sada | unique, create_author, create_category, create_book, create_tag (+order) | unique, create_author, create_category, create_book |
| create_book ISBN | UUID-based, vždy správný | Problematický na L0–L2 |
| Variabilita | Vyšší (1–15 helperů) | Nízká (vždy 4) |

DeepSeek generuje více helperů s vyšší variabilitou. Gemini je konzistentní (vždy 4 helpery) ale s rizikovým ISBN formátem.

---

## 7. Token Usage a Cost

### Per-level průměrné náklady

| Level | DeepSeek Cost | Gemini Cost | Poměr |
|-------|-------------|-----------|-------|
| L0 | $0.0045 | $0.020 | **4.4× levnější** |
| L1 | $0.0057 | $0.025 | **4.4× levnější** |
| L2 | $0.0057 | $0.025 | **4.4× levnější** |
| L3 | $0.0064 | $0.028 | **4.4× levnější** |
| L4 | $0.0069 | $0.027 | **3.9× levnější** |

### Celkový cost za 25 runů

| Model | Celkový cost | Avg validity |
|-------|-------------|-------------|
| DeepSeek | **$0.146** | **98.0%** |
| Gemini | **$0.63** | **86.27%** |

DeepSeek dosahuje vyšší kvality za 4× nižší cenu.

### Cache utilization

| Level | DeepSeek Cache % | Gemini Cache % |
|-------|-----------------|---------------|
| L0 | 85% | 14% |
| L1 | 91% | 30% |
| L2 | 96% | 45% |
| L3 | 94% | 39% |
| L4 | 95% | 60% |

DeepSeek agresivnější prefix caching (85–96 %) oproti Gemini (14–60 %).

---

## 8. Instruction Compliance

| Level | DeepSeek Compliance | Gemini Compliance |
|-------|--------------------|--------------------|
| L0 | 84 | 80 |
| L1 | 88 | 100 |
| L2 | 92 | 84 |
| L3 | 92 | 84 |
| L4 | 100 | 100 |

Gemini má neočekávaně 100 % compliance na L1 (timeout na všech HTTP voláních) ale klesá na L2–L3. DeepSeek roste monotónně. Oba dosahují 100 % na L4.

---

## 9. Kontextová komprese

Identická pro oba modely (sdílený preprocessing):

| Level | Original tokens | Compressed tokens | Savings (%) |
|-------|-----------------|-------------------|-------------|
| L0 | 30,741 | 15,958 | 48.1 |
| L1 | 38,876 | 23,783 | 38.8 |
| L2 | 59,487 | 43,917 | 26.2 |
| L3 | 60,341 | 44,770 | 25.8 |
| L4 | 69,009 | 53,438 | 22.6 |

---

## 10. Hodnocení hypotéz

### H1a: Monotónní růst TVR s kontextem

| Model | Výsledek |
|-------|---------|
| DeepSeek | **Zamítnuta** — TVR je vysoká (98.67 %) již na L0, neroste s kontextem. Antitetický vzorec. |
| Gemini | **Částečně potvrzena** — TVR roste L0→L3 (75→97 %), ale ne monotónně (L1 ≈ L0 kvůli outlierům). Klíčový skok je L2→L3, ne L0→L1. |

### H1b: Ostrý skok code coverage při přechodu na white-box (L1→L2)

| Model | Výsledek |
|-------|---------|
| DeepSeek | **Zamítnuta** — skok L1→L2 je jen +1.0 p.b. total. Největší skok je L0→L1 (+1.9 p.b.). |
| Gemini | **Částečně potvrzena** — skok L1→L2 je +2.8 p.b. total (+5.5 p.b. crud.py), ale větší skok je L2→L3 (+2.5 p.b. total, +5.7 crud.py). |

### H1c: EP coverage vysoká na L0, neroste lineárně

| Model | Výsledek |
|-------|---------|
| DeepSeek | **Potvrzena** — L0 má nejvyšší EP coverage (40.8 %), klesá na L1 (32.4 %). |
| Gemini | **Částečně potvrzena** — EP coverage je relativně stabilní (39–46 %) bez jasného trendu. |

### H2a: Happy path klesá pod 40 % na L3+

| Model | Výsledek |
|-------|---------|
| DeepSeek | **Částečně potvrzena** — klesá z 49 % (L0) na 37 % (L4). Pod 40 % až na L3. |
| Gemini | **Potvrzena** — HP je pod 40 % na L1 (28 %), L3 (31 %), L4 (39 %). |

### H2b: Status code diverzita roste na L3 díky DB schématu

| Model | Výsledek |
|-------|---------|
| DeepSeek | **Potvrzena** — skok L2→L3 (+2.0 kódy). |
| Gemini | **Nepotvrzena** — diverzita je vysoká již od L0 (12.8) a roste jen mírně. |

---

## 11. Shrnutí klíčových rozdílů

### Kde DeepSeek vyniká

1. **Vysoká baseline validity (98.67 % na L0)** — nepotřebuje kontext pro funkční testy.
2. **Hluboké aserce (2–3× Gemini)** — kontroluje response body, ne jen status kódy.
3. **Žádné helper kaskádové selhání** — UUID-based ISBN eliminuje systémový problém.
4. **Vyšší code coverage** (+2–6 p.b. total, +7–17 p.b. crud.py).
5. **4× nižší cost** při vyšší kvalitě.
6. **Rychlejší konvergence** (1.8–2.6 vs. 2.2–3.6 iterací).
7. **Konzistentní výsledky** (std 1.6–3.0 vs. 2.1–21.3).

### Kde Gemini vyniká

1. **Širší endpoint coverage** (+2–12 p.b.).
2. **Vyšší status code diverzita** (+2–5 kódů).
3. **Více error testů** — agresivnější error-first strategie.
4. **Vyšší fix rate** — repair loop opraví více testů (ale začíná s více chybami).
5. **Monotónní růst s kontextem** — jasný vzorec zlepšování, užitečný pro predikci.

### Fundamentální rozdíl

DeepSeek a Gemini reprezentují **dva odlišné profily** LLM-generovaného testování:

- **DeepSeek = high baseline, deep but narrow.** Model generuje málo ale kvalitních testů s hlubokými asercemi. Kontext zlepšuje sémantickou kvalitu (assertion depth, response validation) ale ne validity. Failure mode: timing-dependent a boundary testy.

- **Gemini = context-dependent, broad but shallow.** Model potřebuje kontext pro funkční testy (L0–L2 nestabilní). Generuje více testů se širším pokrytím ale mělkými asercemi. Failure mode: helper kaskádové selhání (L0–L2), wrong_status_code (L3+).

### Cost-effectiveness

| Metrika | DeepSeek | Gemini |
|---------|---------|--------|
| Cost per 1% validity | $0.0059 | $0.0073 |
| Cost per 1% code coverage | $0.0080 | $0.0089 |
| Validity per $0.01 | 6.71% | 1.37% |

DeepSeek je nákladově efektivnější na obou metrikách.

---

## 12. Doporučení pro praxi

1. **Pro maximální validity s minimálním kontextem:** DeepSeek — dosahuje 98+ % i na L0.
2. **Pro maximální benefit z kontextu:** Gemini — ukazuje jasný monotónní růst, kontext se "vyplatí".
3. **Pro cost-sensitive nasazení:** DeepSeek — 4× levnější při vyšší kvalitě.
4. **Pro široké explorativní testování:** Gemini — širší EP coverage a status code diverzita.
5. **Pro hluboké regression testování:** DeepSeek — assertion depth 2–3× vyšší.

### Limitace porovnání

1. **Různé cenové modely:** DeepSeek pricing je výrazně nižší, což ovlivňuje cost-effectiveness metriky.
2. **Gemini verze:** gemini-3.1-flash-lite-preview je "lite" varianta — plný Gemini Flash by mohl dosahovat lepších výsledků.
3. **Single API:** Výsledky jsou specifické pro bookstore API (50 endpointů, FastAPI + SQLite). Jiná API mohou vykazovat odlišné vzorce.
4. **Stale tracker vliv:** Agresivní stale tracker (threshold 2) penalizuje Gemini více kvůli helper cascade normalizaci.