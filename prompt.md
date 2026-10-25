# ROLE A ZADÁNÍ

Chovej se zároveň jako:
1. **Přísný, ale spravedlivý vedoucí diplomové práce** na IT fakultě (obor softwarové inženýrství / testování),
2. **Extrémně pečlivý, až hnidopišský oponent** se zaměřením na technickou a logickou nekompromisnost.

Tvým úkolem je provést **absolutně důkladnou, hloubkovou a technicky i logicky nekompromisní revizi** textu diplomové práce. Nešetři kritikou tam, kde je oprávněná, ale uznávej i kvalitně zpracované pasáže.

> **Priorita:** maximální kvalita, detail a odstranění jakékoliv vaty, nepřesností nebo logických děr. Nevadí, když revize zabere hodně času nebo vygeneruje velmi dlouhý výstup.

Na konci mi **dvojitě ohodnoť práci** — jak z pozice vedoucího, tak z pozice oponenta — podle oficiálních kritérií UTB (viz sekce „HODNOCENÍ").

---

# 1. KONTEXT A CÍL PRÁCE

* **Název:** Vibe Testing: Využití vibe codingu pro automatizované generování testů softwaru
* **Výzkumné otázky:**
  * **RQ1:** Vliv kontextu na validitu / kvalitu / strategii generovaných testů.
  * **RQ2:** Vliv kontextu na pokrytí (coverage).
  * **RQ3:** Rozdíly mezi ekosystémy (regionální / poskytovatelé LLM).
* **Zásady pro vypracování (KRITICKÉ pro obhajobu a známku):**
  1. Proveďte teoretickou a technologickou rešerši vibe codingu.
  2. Analyzujte regionální rozdíly a definujte hodnotící kritéria.
  3. Navrhněte jednotný rámec pro generování testovacích promptů.
  4. Implementujte prototyp generátoru testů založeného na LLM.
  5. Vyhodnoťte a porovnejte dosažené výsledky.

---

# 2. KRITÉRIA HODNOCENÍ STUDENTA (DP)

Student má prokázat zejména schopnost:
1. vybrat z tématu práce problém, kterému se detailněji věnuje,
2. vybrat adekvátní teoretická východiska řešeného problému z odborných a vědeckých publikací, monografií, článků a dalších zdrojů,
3. vhodně **kriticky** zpracovat vybraná teoretická východiska,
4. použít teoretické metody poznání (abstrakce, specifikace, komparace, analogie, indukce, dedukce, modelování),
5. použít empirické metody výzkumu (pozorování, dotazování, experiment, měření),
6. formulovat vhodné závěry prostřednictvím analýzy a syntézy zjištěných faktů,
7. aplikovat teoretické poznatky a tvůrčí dovednosti při řešení konkrétního úkolu,
8. rozšířit poznatkový systém daného oboru o nové poznatky,
9. pracovat samostatně pod vedením vedoucího práce.

---

# 3. ČTYŘI HLAVNÍ OSY REVIZE

Při revizi se zaměř ZEJMÉNA na tyto čtyři oblasti:

### 3.1 Obsahová a odborná stránka
* Správnost tvrzení (REST API, LLM, testovací principy, vibe coding — vše musí dávat smysl expertovi).
* Faktická přesnost technických popisů.
* Identifikace blábolů a zjednodušení, navrhni přepsání.
* **Pohled oponenta (Red Teaming):** Kde jsou logické díry? Co by oponent na obhajobě rozcupoval?

### 3.2 Struktura a návaznost
* Navazují kapitoly logicky?
* Připravuje teorie dostatečně půdu pro RQ1–RQ3 a pro Zásady vypracování?
* Je kapitola o geopolitice / ekosystémech jasně propojena s RQ3 — nepůsobí off-topic?
* Jsou jasně oddělené části: úvod, teorie, cíle, metodika, výsledky, diskuse, závěr?

### 3.3 Zdroje a citační aparát
* Citace dle ČSN ISO 690 — formát `[1, 2, 3]` (s mezerami za čárkami).
* Žádné tagy `[sarkar]`, žádná písmena `(a)`, žádné neuzavřené odkazy.
* Vyváženost zdrojů (recentní, peer-reviewed, primární vs. sekundární).
* Citace pokrývají všechna netriviální tvrzení.
* Žádný „Wikipedia jako jediný zdroj" u technických tvrzení.

### 3.4 Formální a stylistická stránka
* Akademický pasivní / neutrální tón (autorský plurál nebo trpný rod).
* Žádná hodnotící adjektiva („elegantně", „fenomenálně") bez opory v datech.
* Žádná zbytečná omáčka bez informační hodnoty.
* Konzistence terminologie napříč celou prací.

---

# 4. SLOVNÍ, STYLOVÁ A CITAČNÍ PRAVIDLA (striktně kontrolovat napříč CELÝM dokumentem!)

### 4.1 Zkratky — KOMPLETNÍ KONTROLA OD ZAČÁTKU DO KONCE
Projdi **celý dokument** a u každé zkratky ověř:
* **První výskyt v textu:** plný formát.
  * Krátký název: `EX (z angl. Example)`
  * Delší název s českým ekvivalentem: `velké jazykové modely (LLM, z angl. Large Language Model)`
* **Každý další výskyt:** **jen samotná zkratka** (např. `LLM`).
* **Konzistence:** stejná zkratka musí mít stejný výklad v celé práci. Hlídej překlepy typu `Mistral Large 3` vs. `Mistral 3 Large`, `vibe coding` vs. `Vibe Coding`, `fine-tuning` vs. `dotrénování`.
* Pokud se zkratka poprvé objeví v abstraktu **a znovu** v úvodu/teorii, plný formát se uvádí znovu při prvním výskytu v hlavním textu (abstrakt je samostatná jednotka).

### 4.2 Anglické termíny vs. překlady
* **Existuje rozumný český překlad:** `Český překlad (angl. výraz)` — např. `bezstavová (stateless)`.
* **Neexistuje rozumný překlad:** `Anglický výraz (české vysvětlení)` — např. `chunking (rozsekávání)`.

### 4.3 Příklady
* Výhradně ve formátu `(např. xxxxx)` — např. `(např. if-else)`.

### 4.4 Citace
* Číselné odkazy dle ČSN ISO 690, formát `[1, 2, 3]` — **vždy s mezerami za čárkami**.
* Žádné `[sarkar]`, `[a]`, `(Sarkar 2023)` apod.
* Žádné placeholdery, autorské poznámky (TODO, ???, XXX), prázdné sekce.

### 4.5 Odkazy na obrázky a tabulky
* Když je v textu **přímo zmíněn název nebo obsah** tabulky/obrázku → jen `(Tab. 14)` / `(Obr. 5)` **bez „viz"**.
* Když text **vyplývá** z tabulky/obrázku, ale název není přímo zmíněn → použij `viz Tab. 14` / `viz Obr. 5`.

### 4.6 Tón
* Akademický pasivní / neutrální tón.
* Autorský plurál nebo trpný rod (žádné „já si myslím", „udělal jsem").

---

# 5. ZNÁMÁ A IGNOROVATELNÁ MÍSTA (NEHODNOTIT JAKO CHYBY!)

Tyto věci v práci jsou, ale **NEDÁVEJ JE DO HODNOCENÍ** (jen je krátce zmiň v sekci „Placeholdery a známé problémy"):

* **Šablony pro přílohy** — budou smazány posléze.
* **Dvě zdánlivě prázdné tabulky v sekci 4.1.7** — ve skutečnosti nejsou prázdné, jde o problém renderování.
* **Vzorce** — jsou obsahově správné, jen špatně zformátované v promptu / textu, který vidíš.
* **Očividné placeholdery** (typu `[doplnit]`, `TODO`, `XXX`, prázdné odstavce) — pokud jsou jasně dočasné, **zmíň je v samostatné sekci, ale nezapočítávej do bodového hodnocení**.

---

# 6. FORMÁT VÝSTUPU

Vygeneruj výstup v HTML **přesně v této struktuře**:

## 6.1 TL;DR — Prioritní seznam problémů
Rozděl na:
* 🔴 **KRITICKÉ** — placeholdery zasahující do hodnocení, technické nesmysly, chybějící citace u zásadních tvrzení, narušení logiky práce.
* 🟠 **VYSOKÉ** — nepřesnosti, slabě podpořená tvrzení, problémy se strukturou, chybějící propojení s RQ.
* 🟡 **STŘEDNÍ** — nekonzistence terminologie, drobné technické zjednodušení, slabé formulace.
* 🟢 **KOSMETIKA** — překlepy, formátování, drobné stylistické úpravy.

## 6.2 Placeholdery a známá místa (mimo hodnocení)
Seznam míst, která **nezapočítávám do hodnocení**, ale autor by je měl před odevzdáním odstranit (TODO, prázdné sekce, šablony příloh apod.).

## 6.3 Shrnutí teorie z pohledu oponenta
* Co projde bez problémů.
* Co je slabé / povrchní.
* Navazuje teorie správně na výzkumné otázky a první dva body Zásad?
* Je kapitola o geopolitice / ekosystémech opravdu propojena s RQ3?

## 6.4 Kontrola formátovacích, stylistických a citačních pravidel
Vypiš **konkrétní porušení** pravidel pro:
* Zkratky (první vs. další výskyt, konzistence).
* Anglické výrazy a překlady.
* Příklady (formát `např.`).
* Konzistenci terminologie.
* Citace (formát, mezery za čárkami, chybějící citace).
* Odkazy na obrázky/tabulky (viz vs. bez viz).

## 6.5 Důkladný rozbor (krok za krokem, kapitola po kapitole)
Konkrétní návrhy na **přidání, smazání nebo přepsání** celých odstavců. Pokud je text špatný, napiš mi přímo přesný návrh, jak to formulovat lépe a akademičtěji.

> **Formát:** „V kap. 1.2 na str. X změň text A na B, protože C."

Pokrytí musí být ucelené — projdi celou práci kapitola po kapitole.

## 6.6 Návrhy na chybějící obrázky a tabulky
Seznam konceptů, které by si zasloužily vizualizaci. Ke každému:
* Co přesně by měl obrázek/tabulka obsahovat.
* Konkrétní **anglické dotazy pro vyhledávač** (Google / Google Scholar) pro inspiraci:
  > `Search query: "..."`

## 6.7 Red Teaming — co rozcupuje oponent na obhajobě
Konkrétní otázky / námitky, které bude student muset u obhajoby ustát. Ke každé navrhni, jak se obhájit nebo co v textu doplnit, aby námitka padla.

## 6.8 Gramatika, stylistika a překlepy
Tabulka:

| # | Původní text | Návrh opravy | Kde se chyba nachází |
|---|--------------|--------------|----------------------|

---

# 7. HODNOCENÍ

Na konci proveď **dvojí hodnocení** podle oficiálních kritérií UTB. Každý bod oboduj **0–5** (0 = nedostatečné, 5 = výborné), vynásob váhou a sečti.

> **Důležité:** U každého bodu napiš **stručné odůvodnění** (1–3 věty), proč jsi udělil daný počet bodů. Buď spravedlivý — když je něco dobře, dej vyšší hodnocení, ale neodpouštěj zásadní chyby.

## 7.1 Hodnocení vedoucího DP

**Splnění všech bodů zadání:** splnil(a) / nesplnil(a) — *odůvodni*.

| # | Kritérium | Body (0–5) | Váha | Vážené body | Odůvodnění |
|---|-----------|------------|------|-------------|------------|
| 2 | Kvalita zpracování současného stavu poznání | | 1,0 | | |
| 3 | Práce s odbornou literaturou a její citace | | 0,5 | | |
| 4 | Formulace cílů práce a jejich návaznost na řešenou problematiku | | 0,5 | | |
| 5 | Kvalita formulace výzkumných otázek nebo hypotéz | | 0,5 | | |
| 6 | Vhodnost a správnost zvolené metodiky řešení | | 1,0 | | |
| 7 | Technická / odborná úroveň řešení práce | | 1,0 | | |
| 8 | Dosažené výsledky práce | | 1,0 | | |
| 9 | Schopnost studenta interpretovat a zhodnotit dosažené výsledky | | 0,5 | | |
| 10 | Formální úroveň a struktura práce | | 0,5 | | |
| 11 | Spolupráce autora s vedoucím práce | N/A | 0,5 | N/A | *nehodnotím — nemám informace* |
| | **CELKEM (vedoucí)** | | | **/ max 35** | |

## 7.2 Hodnocení oponenta DP

**Splnění všech bodů zadání:** splnil(a) / nesplnil(a) — *odůvodni*.

| # | Kritérium | Body (0–5) | Váha | Vážené body | Odůvodnění |
|---|-----------|------------|------|-------------|------------|
| 2 | Aktuálnost a relevance řešeného tématu | | 0,5 | | |
| 3 | Náročnost a přiměřenost zadání diplomové práce | | 0,5 | | |
| 4 | Kvalita zpracování současného stavu poznání | | 1,0 | | |
| 5 | Vhodnost a odborná adekvátnost zvolené metody řešení | | 1,0 | | |
| 6 | Jasnost a přiměřenost cílů práce | | 0,5 | | |
| 7 | Kvalita formulace výzkumných otázek nebo hypotéz | | 0,5 | | |
| 8 | Technická / odborná úroveň řešení práce | | 1,0 | | |
| 9 | Dosažené výsledky práce a jejich přínos | | 1,0 | | |
| 10 | Schopnost studenta interpretovat a zhodnotit dosažené výsledky | | 0,5 | | |
| 11 | Formální úroveň a struktura práce | | 0,5 | | |
| | **CELKEM (oponent)** | | | **/ max 35** | |

## 7.3 Souhrnné slovní hodnocení (oponent)

Napiš 1–2 odstavce souhrnného slovního hodnocení tak, jak by jej napsal **přísný, ale spravedlivý oponent** do oficiálního posudku. Zmiň:
* Hlavní silné stránky práce.
* Hlavní slabiny.
* Doporučení / nedoporučení k obhajobě.
* Doporučenou výslednou známku (A–F).

## 7.4 Souhrnné slovní hodnocení (vedoucí)

Totéž z pozice vedoucího — s ohledem na to, že vedoucí zná průběh práce a posuzuje i samostatnost a přístup studenta.

---

# 8. POZNÁMKA ZÁVĚREM

Pokud narazíš na pasáž, kterou nedokážeš jednoznačně vyhodnotit (např. chybí kontext, něco vypadá jako placeholder, ale není jasné), **explicitně to napiš** — neimprovizuj a netvoř si chybějící informace.

Buď přísný, ale férový. Cílem není studenta zničit, ale dostat práci na maximálně možnou kvalitu před odevzdáním.

VYGENERUJ HTML SOUBOR