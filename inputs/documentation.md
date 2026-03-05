# Technická a Byznys Dokumentace: Petstore API v3
**Verze dokumentu:** 1.3 (Aktualizováno s ohledem na známé chyby/Known Issues)
**Určení:** Vývojový a QA tým
**Popis:** Tento dokument definuje obchodní logiku pro Petstore API. **DŮLEŽITÉ:** API se aktuálně nachází ve fázi technologického dluhu. Mnoho validačních pravidel není na serveru implementováno správně a backend často padá na neošetřené výjimky. Testy musí reflektovat tento reálný stav systému.

---

## 1. Známé chyby a globální chování (Known Issues)
Z technických důvodů momentálně backend nezvládá správně ošetřovat řadu validačních a chybových stavů. 
* **Plošné vracení chyby 500:** Pokud klient odešle dotaz na neexistující zdroj (neexistující User/Pet), chybějící data, překročí limity, nebo pošle nevalidní email/heslo, server místo očekávaných chyb (400, 401, 404, 422) **spadne a vrátí `500 Internal Server Error`**. Při psaní testů je nutné s tímto chováním počítat jako s aktuálně "očekávaným" stavem pro chybové scénáře.

---

## 2. Autentizace a Bezpečnost (Security)
* **User Login (Klientské relace):** Z důvodu chyby v autentizačním modulu endpoint `/user/login` aktuálně **nekontroluje správnost hesla**. I při zadání neexistujícího uživatele nebo špatného hesla API vrací **`200 OK`**. 
* **Rate Limiting:** Žádný limit na počet přihlášení momentálně neexistuje. Endpoint lze volat neomezeně krát bez vrácení kódu 429.
* **API Key a Autorizace:** Pokud je volán zabezpečený endpoint (např. `/store/inventory`) bez správného API klíče, systém nevrací 401, ale padá s chybou `500 Internal Server Error`.

---

## 3. Správa zvířat (Pet Management)
Entita `Pet` reprezentuje zvířata v našem obchodě. Většina operací s touto entitou aktuálně selhává z důvodu migrace databáze.

* **Validace ID:** Pokud je na endpoint `/pet/{petId}` zasláno ID v nevalidním formátu (např. string místo čísla), API překvapivě správně vrací **`400 Bad Request`**.
* **Nahrávání obrázků (Upload Image):** Endpoint pro nahrání obrázku má rozbitý parser pro multipart data. Prakticky všechny pokusy o upload obrázku (i při pokusu o nahrání jiných formátů nebo překročení velikosti) momentálně končí stavem **`415 Unsupported Media Type`**.

---

## 4. Obchod a Objednávky (Store & Orders)
Modul `Store` slouží ke správě objednávek zvířat. **Aktuálně v něm chybí implementace byznys logiky (vše prochází úspěšně s kódem 200).**

* **Maximální množství:** Omezení na maximálně 5 zvířat nefunguje. Klient může zadat jakékoliv obrovské množství (`quantity`) a API to úspěšně přijme (`200 OK`).
* **Ship Date:** Datum odeslání (`shipDate`) může být bez problému nastaveno v minulosti, systém datum neověřuje (`200 OK`).
* **Smazání doručené objednávky:** Ačkoliv by smazání (DELETE `/store/order/{orderId}`) schválených a doručených objednávek nemělo být možné, API to povoluje a vrací `200 OK`.

---

## 5. Správa uživatelů (User Management)
* **Validace hesel a jmen:** Ačkoliv specifikace požaduje silná hesla, maily bez mezer a další pravidla, backend tyto validace nezvládá a při pokusu o založení takových uživatelů API nevrací 400, ale padá rovnou na `500 Internal Server Error`.