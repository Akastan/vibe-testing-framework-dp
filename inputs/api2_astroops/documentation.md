# AstroOps API – Technická dokumentace

## Přehled

REST API pro správu flotily nízkoorbitálních satelitů (LEO). 20 endpointů, 22 HTTP status kódů. Fyzikální a operační limity místo klasického CRUD.

---

## Byznys pravidla

### Energetický rozpočet

Každý satelit má `power_capacity` (maximum) a `current_power` (dostupná energie). Zapnutí payloadu odečte `power_draw`, vypnutí přičte zpět (s cappováním na `power_capacity`). Pokud by `current_power - power_draw < 0`, vrací 412 Precondition Failed. Zapnutí/vypnutí již aktivního/neaktivního payloadu je idempotentní (vrací 200, power se nemění).

### Komunikační okna (AOS/LOS)

Pole `in_signal` řídí, zda je satelit v dosahu. Při `in_signal=false`:
- Příkazy (payload power, create/authorize/abort maneuver) vrací 503 Service Unavailable.
- Výjimka: pokud `next_window_start` je do 5 minut, vrací 425 Too Early.
- Telemetrie se přijímá VŽDY (data se bufferují).

### Globální zámek (Maneuver Lock)

Satelit s manévrem ve stavu `executing` je zamčen. Payload operace, nové manévry i autorizace/abort jiných manévrů vrací 423 Locked.

### Stavový automat manévru

```
draft -> calculating -> authorized -> executing -> completed
  |           |              |            |
  +---------->+-----> aborted <-----------+
```

Manévr se vytváří rovnou jako `calculating` (ne `draft`). Autorizace vyžaduje `X-Clearance: flight-director` (jinak 403). `force_execute: true` v authorize přeskočí `authorized` a rovnou spustí `executing`. Neplatné přechody (z terminálních stavů, přeskočení) vrací 400.

### Safe Mode

Při nízké baterii (`battery_level < 15%` v telemetrii) satelit automaticky přejde do safe_mode a vypnou se všechny payloady. Manuálně lze přepnout přes `PATCH /satellites/{id}/mode`. V safe_mode nelze zapínat payloady (400) ani plánovat manévry (400).

### Deorbitace

`DELETE /satellites/{id}` vrací 202 Accepted. Satelit přejde na `offline` (terminální). Všechny sub-entity vrací 404. Nelze deorbitovat satelit s executing manévrem (423).

### ITAR restrikce

Citlivé payloady (`is_sensitive=true`) vyžadují `X-Clearance: flight-director` pro zapnutí i stažení dat (jinak 403). Kamery s target_coordinates v zakázané zóně vrací 451.

### Downlink kvóta

Každý satelit má limit 100 stažení dat per session. Po vyčerpání: 402 Payment Required.

### Rate limit telemetrie

Max 50 záznamů v jedné dávce. Překročení: 429 Too Many Requests.

---

## Autorizace

Dva mechanismy:
1. **Bearer token** (`Authorization: Bearer <token>`) — povinný na všech endpointech kromě `/health` a `/reset`. Chybí → 401.
2. **Flight Director clearance** (`X-Clearance: flight-director`) — nutný pro: autorizaci manévrů, zapnutí citlivých payloadů, stažení dat z citlivých payloadů. Chybí → 403.

---

## Validační priority (pořadí kontrol)

1. 401 Unauthorized (chybí token)
2. 404 Not Found (entita neexistuje / offline)
3. 422 Unprocessable Entity (Pydantic validace)
4. 400 Bad Request (neplatný stav/přechod)
5. 423 Locked (executing manévr)
6. 503/425 (LOS / Too Early)
7. 403 Forbidden (chybí clearance)
8. 412 Precondition Failed (energie)
9. 409 Conflict (duplicita, časová kolize)
10. Specifické (429, 415, 406, 402, 451, 501)

---

## Known issues a edge cases

- `POST /satellites/{id}/telemetry` přijímá data i při LOS (bufferování).
- Telemetrie s `Content-Type` jiným než `application/json` vrací 415.
- `GET /payloads/{id}/data` na experimentální payload vrací 501 (ne 404).
- Deorbitovaný satelit: payloady, manévry, telemetrie = 404 (ne 410 Gone).
- Emergency safemode NEabortuje `executing` manévry (ty musí doběhnout).
- `scheduled_end` musí být striktně po `scheduled_start` (ne rovno).
- Časová kolize se kontroluje jen proti `calculating`, `authorized`, `executing` manévrům.

---

## Status kódy (22)

### 2xx
- 200: GET, PATCH, authorize, emergency, health, windows
- 201: POST create (satellite, payload, maneuver, telemetry)
- 202: DELETE satellite (deorbitace)
- 204: DELETE abort maneuver, DELETE telemetry
- 206: GET payload data s offset/chunk_size (partial)

### 4xx
- 400: Neplatný stavový přechod, operace v safe_mode, deorbitace offline
- 401: Chybí Authorization header
- 402: Vyčerpaná downlink kvóta
- 403: Chybí Flight Director clearance
- 404: Neexistující entita, deorbitovaný satelit
- 405: Nesprávná HTTP metoda (FastAPI automatic)
- 406: Nekompatibilní Accept header s payload data_format
- 409: Duplicitní název, časová kolize manévrů
- 412: Nedostatek energie pro zapnutí payloadu
- 415: Špatný Content-Type na telemetrii
- 422: Pydantic validace (záporné hodnoty, neznámé typy)
- 423: Satelit zamčen executing manévrem
- 425: Příkaz před komunikačním oknem (< 5 min)
- 429: Překročení limitu telemetrické dávky
- 451: ITAR restrikce (zakázaná geolokace)

### 5xx
- 500: Interní chyba (DB nedostupná)
- 501: Experimentální payload nepodporuje data retrieval
- 503: Loss of Signal (satelit mimo dosah)

---

## Endpointy (20)

### Satellites
- `POST /satellites` → 201. Body: name (unique), orbit_type (LEO/MEO/GEO), power_capacity (>0).
- `GET /satellites` → 200. Query: status, orbit_type, skip, limit.
- `GET /satellites/{id}` → 200. Zahrnuje active_payloads count.
- `PATCH /satellites/{id}/mode` → 200. Body: status, in_signal, next_window_start.
- `DELETE /satellites/{id}` → 202. Deorbitace (asynchronní).

### Payloads
- `GET /satellites/{id}/payloads` → 200. Seznam payloadů.
- `POST /satellites/{id}/payloads` → 201. Body: name, type, power_draw, data_format, is_sensitive.
- `PATCH /payloads/{id}/power` → 200. Body: state (on/off), target_coordinates (optional).
- `GET /payloads/{id}/data` → 200/206. Query: offset, chunk_size. Headers: Accept, X-Clearance.

### Maneuvers
- `POST /satellites/{id}/maneuvers` → 201. Body: delta_v (>0), direction, scheduled_start, scheduled_end.
- `GET /satellites/{id}/maneuvers` → 200. Query: status.
- `GET /maneuvers/{id}` → 200.
- `POST /maneuvers/{id}/authorize` → 200. Body: force_execute (bool). Header: X-Clearance.
- `DELETE /maneuvers/{id}/abort` → 204.

### Telemetry
- `POST /satellites/{id}/telemetry` → 201. Body: readings[] (max 50). Triggers auto-safe_mode.
- `GET /satellites/{id}/telemetry` → 200. Query: from, to, metric, skip, limit.
- `DELETE /satellites/{id}/telemetry` → 204. Query: before.

### System
- `GET /health` → 200.
- `GET /windows` → 200. Query: satellite_id (required).
- `POST /emergency/safemode` → 200. Globální kill switch.