
# ═══ FILE: app/main.py ═══

from datetime import datetime
from fastapi import FastAPI, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app import crud, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AstroOps API", version="1.0.0", description="Satellite Mission Control")


# ── Exception handlers ──

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ── Auth dependency ──

UNPROTECTED = {"/health", "/reset", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in UNPROTECTED or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
        return await call_next(request)
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer ") or len(auth.split(" ", 1)[1].strip()) == 0:
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization token"})
    return await call_next(request)


@app.middleware("http")
async def content_type_check(request: Request, call_next):
    """Return 415 for telemetry endpoint with non-JSON content type."""
    if request.method == "POST" and "/telemetry" in request.url.path and request.url.path != "/reset":
        ct = request.headers.get("content-type", "")
        if ct and "application/json" not in ct:
            return JSONResponse(
                status_code=415,
                content={"detail": f"Unsupported media type: {ct}. Expected application/json."},
            )
    return await call_next(request)


# ═══════════════════════════════════════════
# Satellites (5)
# ═══════════════════════════════════════════

@app.post("/satellites", response_model=schemas.SatelliteResponse, status_code=201)
def create_satellite(data: schemas.SatelliteCreate, db: Session = Depends(get_db)):
    sat = crud.create_satellite(db, data)
    active = sum(1 for p in sat.payloads if p.is_active)
    resp = schemas.SatelliteResponse.model_validate(sat)
    resp.active_payloads = active
    return resp


@app.get("/satellites", response_model=list[schemas.SatelliteListResponse])
def list_satellites(
    status: str | None = None,
    orbit_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud.list_satellites(db, status, orbit_type, skip, limit)


@app.get("/satellites/{satellite_id}", response_model=schemas.SatelliteResponse)
def get_satellite(satellite_id: int, db: Session = Depends(get_db)):
    sat = crud.get_satellite(db, satellite_id)
    active = sum(1 for p in sat.payloads if p.is_active)
    resp = schemas.SatelliteResponse.model_validate(sat)
    resp.active_payloads = active
    return resp


@app.patch("/satellites/{satellite_id}/mode", response_model=schemas.SatelliteResponse)
def update_satellite_mode(
    satellite_id: int, data: schemas.SatelliteModeUpdate, db: Session = Depends(get_db)
):
    sat = crud.update_satellite_mode(db, satellite_id, data)
    active = sum(1 for p in sat.payloads if p.is_active)
    resp = schemas.SatelliteResponse.model_validate(sat)
    resp.active_payloads = active
    return resp


@app.delete("/satellites/{satellite_id}", status_code=202)
def deorbit_satellite(satellite_id: int, db: Session = Depends(get_db)):
    sat = crud.deorbit_satellite(db, satellite_id)
    return {"detail": f"Deorbit initiated for satellite {sat.name}", "satellite_id": sat.id, "status": sat.status}


# ═══════════════════════════════════════════
# Payloads (4)
# ═══════════════════════════════════════════

@app.get("/satellites/{satellite_id}/payloads", response_model=list[schemas.PayloadResponse])
def list_payloads(satellite_id: int, db: Session = Depends(get_db)):
    return crud.list_payloads(db, satellite_id)


@app.post("/satellites/{satellite_id}/payloads", response_model=schemas.PayloadResponse, status_code=201)
def create_payload(satellite_id: int, data: schemas.PayloadCreate, db: Session = Depends(get_db)):
    return crud.create_payload(db, satellite_id, data)


@app.patch("/payloads/{payload_id}/power", response_model=schemas.PayloadPowerResponse)
def update_payload_power(
    payload_id: int,
    data: schemas.PayloadPowerUpdate,
    x_clearance: str | None = Header(None),
    db: Session = Depends(get_db),
):
    return crud.update_payload_power(db, payload_id, data, x_clearance)


@app.get("/payloads/{payload_id}/data")
def get_payload_data(
    payload_id: int,
    offset: int = Query(0, ge=0),
    chunk_size: int = Query(1000, ge=1),
    x_clearance: str | None = Header(None),
    accept: str | None = Header(None),
    db: Session = Depends(get_db),
):
    result = crud.get_payload_data(db, payload_id, x_clearance, accept, offset, chunk_size)
    status = 206 if result["is_partial"] else 200
    return JSONResponse(status_code=status, content=result)


# ═══════════════════════════════════════════
# Maneuvers (5 + 1 helper)
# ═══════════════════════════════════════════

@app.post("/satellites/{satellite_id}/maneuvers", response_model=schemas.ManeuverResponse, status_code=201)
def create_maneuver(satellite_id: int, data: schemas.ManeuverCreate, db: Session = Depends(get_db)):
    return crud.create_maneuver(db, satellite_id, data)


@app.get("/satellites/{satellite_id}/maneuvers", response_model=list[schemas.ManeuverResponse])
def list_maneuvers(satellite_id: int, status: str | None = None, db: Session = Depends(get_db)):
    return crud.list_maneuvers(db, satellite_id, status)


@app.get("/maneuvers/{maneuver_id}", response_model=schemas.ManeuverResponse)
def get_maneuver(maneuver_id: int, db: Session = Depends(get_db)):
    return crud.get_maneuver(db, maneuver_id)


@app.post("/maneuvers/{maneuver_id}/authorize", response_model=schemas.ManeuverResponse)
def authorize_maneuver(
    maneuver_id: int,
    data: schemas.ManeuverAuthorize = schemas.ManeuverAuthorize(),
    x_clearance: str | None = Header(None),
    db: Session = Depends(get_db),
):
    return crud.authorize_maneuver(db, maneuver_id, data, x_clearance)


@app.delete("/maneuvers/{maneuver_id}/abort", status_code=204)
def abort_maneuver(maneuver_id: int, db: Session = Depends(get_db)):
    crud.abort_maneuver(db, maneuver_id)
    return None


@app.post("/maneuvers/{maneuver_id}/complete", response_model=schemas.ManeuverResponse)
def complete_maneuver(maneuver_id: int, db: Session = Depends(get_db)):
    return crud.complete_maneuver(db, maneuver_id)


# ═══════════════════════════════════════════
# Telemetry (3)
# ═══════════════════════════════════════════

@app.post("/satellites/{satellite_id}/telemetry", response_model=schemas.TelemetryIngestResponse, status_code=201)
def ingest_telemetry(satellite_id: int, data: schemas.TelemetryIngest, db: Session = Depends(get_db)):
    return crud.ingest_telemetry(db, satellite_id, data)


@app.get("/satellites/{satellite_id}/telemetry", response_model=list[schemas.TelemetryResponse])
def query_telemetry(
    satellite_id: int,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    metric: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud.query_telemetry(db, satellite_id, from_dt, to_dt, metric, skip, limit)


@app.delete("/satellites/{satellite_id}/telemetry", status_code=204)
def delete_telemetry(
    satellite_id: int,
    before: datetime | None = None,
    db: Session = Depends(get_db),
):
    crud.delete_telemetry(db, satellite_id, before)
    return None


# ═══════════════════════════════════════════
# System & Ops (3 + reset)
# ═══════════════════════════════════════════

@app.get("/health", response_model=schemas.HealthResponse)
def health_check(db: Session = Depends(get_db)):
    return crud.get_health(db)


@app.get("/windows", response_model=schemas.WindowsResponse)
def get_windows(satellite_id: int = Query(...), db: Session = Depends(get_db)):
    return crud.get_windows(db, satellite_id)


@app.post("/emergency/safemode", response_model=schemas.EmergencyResponse)
def emergency_safemode(db: Session = Depends(get_db)):
    return crud.emergency_safemode(db)


@app.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    crud.reset_database(db)
    return {"detail": "Database reset successful"}

# ═══ FILE: app/crud.py ═══

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import models, schemas

BATTERY_CRITICAL_THRESHOLD = 15.0
TELEMETRY_BATCH_LIMIT = 50
DOWNLINK_QUOTA = 100
WINDOW_SOON_MINUTES = 5

RESTRICTED_ZONES = [
    {"lat_min": 34.0, "lat_max": 36.0, "lon_min": 44.0, "lon_max": 46.0},
    {"lat_min": 48.0, "lat_max": 50.0, "lon_min": 2.0, "lon_max": 4.0},
]

MANEUVER_ACTIVE_STATUSES = {"calculating", "authorized", "executing"}
MANEUVER_TERMINAL_STATUSES = {"completed", "aborted"}
MANEUVER_TRANSITIONS = {
    "calculating": "authorized",
    "authorized": "executing",
    "executing": "completed",
}


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def _get_satellite_or_404(db: Session, satellite_id: int) -> models.Satellite:
    sat = db.query(models.Satellite).filter(models.Satellite.id == satellite_id).first()
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found")
    if sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")
    return sat


def _get_satellite_raw(db: Session, satellite_id: int) -> models.Satellite:
    """Get satellite without offline check (for telemetry which needs offline check separately)."""
    sat = db.query(models.Satellite).filter(models.Satellite.id == satellite_id).first()
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found")
    return sat


def _get_payload_or_404(db: Session, payload_id: int) -> models.Payload:
    p = db.query(models.Payload).filter(models.Payload.id == payload_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Payload not found")
    sat = db.query(models.Satellite).filter(models.Satellite.id == p.satellite_id).first()
    if sat and sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")
    return p


def _get_maneuver_or_404(db: Session, maneuver_id: int) -> models.Maneuver:
    m = db.query(models.Maneuver).filter(models.Maneuver.id == maneuver_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Maneuver not found")
    sat = db.query(models.Satellite).filter(models.Satellite.id == m.satellite_id).first()
    if sat and sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")
    return m


def _check_signal(sat: models.Satellite):
    """Check AOS/LOS. Raises 425 or 503."""
    if sat.in_signal:
        return
    if sat.next_window_start:
        now = datetime.now(timezone.utc)
        window = sat.next_window_start
        if window.tzinfo is None:
            window = window.replace(tzinfo=timezone.utc)
        delta = (window - now).total_seconds()
        if 0 < delta <= WINDOW_SOON_MINUTES * 60:
            raise HTTPException(
                status_code=425,
                detail=f"Communication window opens at {sat.next_window_start.isoformat()}. Command queued.",
            )
    raise HTTPException(
        status_code=503,
        detail=f"Loss of Signal. Satellite {sat.name} is not in communication range.",
    )


def _check_maneuver_lock(db: Session, sat: models.Satellite):
    """Check if satellite has executing maneuver. Raises 423."""
    executing = (
        db.query(models.Maneuver)
        .filter(
            models.Maneuver.satellite_id == sat.id,
            models.Maneuver.status == "executing",
        )
        .first()
    )
    if executing:
        raise HTTPException(
            status_code=423,
            detail=f"Satellite {sat.name} is locked: maneuver {executing.id} is executing.",
        )


def _deactivate_all_payloads(db: Session, sat: models.Satellite):
    """Turn off all active payloads and return power."""
    for p in sat.payloads:
        if p.is_active:
            p.is_active = False
            sat.current_power = min(sat.current_power + p.power_draw, sat.power_capacity)


def _is_in_restricted_zone(coords: dict) -> bool:
    lat = coords.get("lat", 0)
    lon = coords.get("lon", 0)
    for zone in RESTRICTED_ZONES:
        if zone["lat_min"] <= lat <= zone["lat_max"] and zone["lon_min"] <= lon <= zone["lon_max"]:
            return True
    return False


# ═══════════════════════════════════════════
# Satellites
# ═══════════════════════════════════════════

def create_satellite(db: Session, data: schemas.SatelliteCreate) -> models.Satellite:
    existing = db.query(models.Satellite).filter(models.Satellite.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Satellite with name '{data.name}' already exists")

    sat = models.Satellite(
        name=data.name,
        orbit_type=data.orbit_type,
        power_capacity=data.power_capacity,
        current_power=data.power_capacity,
        status="active",
        in_signal=True,
    )
    db.add(sat)
    db.commit()
    db.refresh(sat)
    return sat


def list_satellites(db: Session, status: str | None, orbit_type: str | None, skip: int, limit: int):
    q = db.query(models.Satellite)
    if status:
        q = q.filter(models.Satellite.status == status)
    if orbit_type:
        q = q.filter(models.Satellite.orbit_type == orbit_type)
    return q.offset(skip).limit(limit).all()


def get_satellite(db: Session, satellite_id: int) -> models.Satellite:
    return _get_satellite_or_404(db, satellite_id)


def update_satellite_mode(db: Session, satellite_id: int, data: schemas.SatelliteModeUpdate) -> models.Satellite:
    sat = _get_satellite_or_404(db, satellite_id)

    if data.status is not None:
        current = sat.status
        target = data.status

        # offline is terminal
        if current == "offline":
            raise HTTPException(status_code=400, detail="Cannot change mode of offline (deorbited) satellite")
        if target == "offline":
            raise HTTPException(status_code=400, detail="Cannot set satellite to offline via mode change. Use DELETE for deorbit.")

        # maneuvering -> active forbidden (managed by maneuver automat)
        if current == "maneuvering" and target == "active":
            raise HTTPException(status_code=400, detail="Cannot switch from maneuvering to active. Maneuver must complete or abort first.")

        # active -> active, safe_mode -> safe_mode = no-op
        if current == target:
            pass
        elif target == "safe_mode":
            sat.status = "safe_mode"
            _deactivate_all_payloads(db, sat)
        elif target == "active":
            if current != "safe_mode":
                raise HTTPException(status_code=400, detail=f"Cannot switch from '{current}' to 'active'. Only safe_mode -> active is allowed.")
            sat.status = "active"
        elif target == "maneuvering":
            raise HTTPException(status_code=400, detail="Cannot manually set satellite to maneuvering. This is managed by the maneuver system.")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid status transition: {current} -> {target}")

    if data.in_signal is not None:
        sat.in_signal = data.in_signal

    if data.next_window_start is not None:
        sat.next_window_start = data.next_window_start

    db.commit()
    db.refresh(sat)
    return sat


def deorbit_satellite(db: Session, satellite_id: int) -> models.Satellite:
    sat = _get_satellite_or_404(db, satellite_id)

    if sat.status == "offline":
        raise HTTPException(status_code=400, detail="Satellite is already deorbited")

    _check_maneuver_lock(db, sat)

    _deactivate_all_payloads(db, sat)

    # Abort non-executing maneuvers
    active_maneuvers = (
        db.query(models.Maneuver)
        .filter(
            models.Maneuver.satellite_id == sat.id,
            models.Maneuver.status.in_(["draft", "calculating", "authorized"]),
        )
        .all()
    )
    for m in active_maneuvers:
        m.status = "aborted"

    sat.status = "offline"
    db.commit()
    db.refresh(sat)
    return sat


# ═══════════════════════════════════════════
# Payloads
# ═══════════════════════════════════════════

def list_payloads(db: Session, satellite_id: int):
    sat = _get_satellite_or_404(db, satellite_id)
    return db.query(models.Payload).filter(models.Payload.satellite_id == sat.id).all()


def create_payload(db: Session, satellite_id: int, data: schemas.PayloadCreate) -> models.Payload:
    sat = _get_satellite_or_404(db, satellite_id)

    p = models.Payload(
        satellite_id=sat.id,
        name=data.name,
        type=data.type,
        power_draw=data.power_draw,
        data_format=data.data_format,
        is_sensitive=data.is_sensitive,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_payload_power(
    db: Session,
    payload_id: int,
    data: schemas.PayloadPowerUpdate,
    clearance: str | None,
) -> schemas.PayloadPowerResponse:
    p = _get_payload_or_404(db, payload_id)
    sat = db.query(models.Satellite).filter(models.Satellite.id == p.satellite_id).first()

    # Validation priority: 400 (bad state) -> 423 (lock) -> 503/425 (signal) -> 403 (clearance) -> 412 (power) -> 451 (ITAR)
    if data.state == "on" and sat.status == "safe_mode":
        raise HTTPException(status_code=400, detail="Cannot activate payload while satellite is in safe_mode")

    _check_maneuver_lock(db, sat)
    _check_signal(sat)

    if data.state == "on":
        if p.is_sensitive and clearance != "flight-director":
            raise HTTPException(
                status_code=403,
                detail="Flight Director clearance required. Provide X-Clearance: flight-director header.",
            )

        # ITAR check for cameras with target_coordinates
        if data.target_coordinates and p.type == "camera":
            if _is_in_restricted_zone(data.target_coordinates):
                raise HTTPException(
                    status_code=451,
                    detail="ITAR restriction: target coordinates fall within restricted zone.",
                )

        if not p.is_active:
            if sat.current_power - p.power_draw < 0:
                raise HTTPException(
                    status_code=412,
                    detail=f"Insufficient power. Required: {p.power_draw}W, available: {sat.current_power}W",
                )
            p.is_active = True
            sat.current_power -= p.power_draw
    elif data.state == "off":
        if p.is_active:
            p.is_active = False
            sat.current_power = min(sat.current_power + p.power_draw, sat.power_capacity)

    db.commit()
    db.refresh(p)
    db.refresh(sat)
    return schemas.PayloadPowerResponse(
        id=p.id, is_active=p.is_active, satellite_current_power=sat.current_power
    )


def get_payload_data(
    db: Session,
    payload_id: int,
    clearance: str | None,
    accept: str | None,
    offset: int,
    chunk_size: int,
) -> dict:
    p = _get_payload_or_404(db, payload_id)
    sat = db.query(models.Satellite).filter(models.Satellite.id == p.satellite_id).first()

    if p.type == "experimental":
        raise HTTPException(status_code=501, detail="Experimental payload does not support data retrieval")

    if p.is_sensitive and clearance != "flight-director":
        raise HTTPException(
            status_code=403,
            detail="Flight Director clearance required. Provide X-Clearance: flight-director header.",
        )

    if accept and accept != "*/*":
        format_to_mime = {"json": "application/json", "binary": "application/octet-stream", "protobuf": "application/protobuf"}
        expected = format_to_mime.get(p.data_format, "")
        if accept != expected and accept not in (expected, "*/*"):
            raise HTTPException(
                status_code=406,
                detail=f"Payload data format is '{p.data_format}'. Requested Accept '{accept}' is not compatible.",
            )

    if sat.download_count >= DOWNLINK_QUOTA:
        raise HTTPException(status_code=402, detail="Downlink quota exhausted. Payment required for additional downloads.")

    sat.download_count += 1
    db.commit()

    total_records = 500  # simulated
    is_partial = offset > 0 or chunk_size < total_records
    return {
        "payload_id": p.id,
        "format": p.data_format,
        "offset": offset,
        "chunk_size": chunk_size,
        "total_records": total_records,
        "is_partial": is_partial,
        "data": [{"sample": f"record_{i}"} for i in range(offset, min(offset + chunk_size, total_records))],
    }


# ═══════════════════════════════════════════
# Maneuvers
# ═══════════════════════════════════════════

def create_maneuver(db: Session, satellite_id: int, data: schemas.ManeuverCreate) -> models.Maneuver:
    sat = _get_satellite_or_404(db, satellite_id)

    if sat.status == "safe_mode":
        raise HTTPException(status_code=400, detail="Cannot plan maneuver while satellite is in safe_mode")

    _check_maneuver_lock(db, sat)
    _check_signal(sat)

    # Time collision check
    overlapping = (
        db.query(models.Maneuver)
        .filter(
            models.Maneuver.satellite_id == sat.id,
            models.Maneuver.status.in_(MANEUVER_ACTIVE_STATUSES),
            models.Maneuver.scheduled_start < data.scheduled_end,
            models.Maneuver.scheduled_end > data.scheduled_start,
        )
        .first()
    )
    if overlapping:
        raise HTTPException(
            status_code=409,
            detail=f"Time collision with maneuver {overlapping.id} ({overlapping.scheduled_start} - {overlapping.scheduled_end})",
        )

    m = models.Maneuver(
        satellite_id=sat.id,
        delta_v=data.delta_v,
        direction=data.direction,
        scheduled_start=data.scheduled_start,
        scheduled_end=data.scheduled_end,
        status="calculating",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_maneuvers(db: Session, satellite_id: int, status: str | None):
    sat = _get_satellite_or_404(db, satellite_id)
    q = db.query(models.Maneuver).filter(models.Maneuver.satellite_id == sat.id)
    if status:
        q = q.filter(models.Maneuver.status == status)
    return q.order_by(models.Maneuver.created_at.desc()).all()


def get_maneuver(db: Session, maneuver_id: int) -> models.Maneuver:
    return _get_maneuver_or_404(db, maneuver_id)


def authorize_maneuver(
    db: Session, maneuver_id: int, data: schemas.ManeuverAuthorize, clearance: str | None
) -> models.Maneuver:
    m = _get_maneuver_or_404(db, maneuver_id)
    sat = db.query(models.Satellite).filter(models.Satellite.id == m.satellite_id).first()

    # State validation
    if m.status in MANEUVER_TERMINAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot authorize maneuver in '{m.status}' state")
    if m.status != "calculating":
        raise HTTPException(status_code=400, detail=f"Cannot authorize maneuver in '{m.status}' state. Must be 'calculating'.")

    _check_maneuver_lock(db, sat)
    _check_signal(sat)

    if clearance != "flight-director":
        raise HTTPException(
            status_code=403,
            detail="Flight Director clearance required. Provide X-Clearance: flight-director header.",
        )

    m.status = "authorized"
    m.authorized_by = "flight-director"

    if data.force_execute:
        m.status = "executing"
        sat.status = "maneuvering"

    db.commit()
    db.refresh(m)
    return m


def abort_maneuver(db: Session, maneuver_id: int) -> models.Maneuver:
    m = _get_maneuver_or_404(db, maneuver_id)
    sat = db.query(models.Satellite).filter(models.Satellite.id == m.satellite_id).first()

    if m.status in MANEUVER_TERMINAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot abort maneuver in '{m.status}' state (terminal)")

    _check_signal(sat)

    was_executing = m.status == "executing"
    m.status = "aborted"

    if was_executing:
        sat.status = "active"

    db.commit()
    db.refresh(m)
    return m


def complete_maneuver(db: Session, maneuver_id: int) -> models.Maneuver:
    m = _get_maneuver_or_404(db, maneuver_id)
    sat = db.query(models.Satellite).filter(models.Satellite.id == m.satellite_id).first()

    if m.status != "executing":
        raise HTTPException(status_code=400, detail=f"Cannot complete maneuver in '{m.status}' state. Must be 'executing'.")

    m.status = "completed"
    sat.status = "active"

    db.commit()
    db.refresh(m)
    return m


# ═══════════════════════════════════════════
# Telemetry
# ═══════════════════════════════════════════

def ingest_telemetry(db: Session, satellite_id: int, data: schemas.TelemetryIngest) -> schemas.TelemetryIngestResponse:
    sat = _get_satellite_raw(db, satellite_id)
    if sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")

    if len(data.readings) > TELEMETRY_BATCH_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Batch size {len(data.readings)} exceeds limit of {TELEMETRY_BATCH_LIMIT} readings",
        )

    warnings = []
    triggered_safe_mode = False

    for r in data.readings:
        t = models.Telemetry(
            satellite_id=sat.id,
            timestamp=r.timestamp,
            battery_level=r.battery_level,
            temperature_c=r.temperature_c,
            radiation_msv=r.radiation_msv,
            signal_strength_dbm=r.signal_strength_dbm,
        )
        db.add(t)

        if r.battery_level < BATTERY_CRITICAL_THRESHOLD and not triggered_safe_mode:
            if sat.status not in ("safe_mode", "offline"):
                sat.status = "safe_mode"
                _deactivate_all_payloads(db, sat)
                triggered_safe_mode = True
                warnings.append(
                    f"Battery critical ({r.battery_level}%). Satellite {sat.name} switched to safe_mode. All payloads deactivated."
                )

    db.commit()
    return schemas.TelemetryIngestResponse(ingested=len(data.readings), warnings=warnings)


def query_telemetry(
    db: Session, satellite_id: int, from_dt: datetime | None, to_dt: datetime | None,
    metric: str | None, skip: int, limit: int,
):
    sat = _get_satellite_raw(db, satellite_id)
    if sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")

    q = db.query(models.Telemetry).filter(models.Telemetry.satellite_id == sat.id)
    if from_dt:
        q = q.filter(models.Telemetry.timestamp >= from_dt)
    if to_dt:
        q = q.filter(models.Telemetry.timestamp <= to_dt)
    return q.order_by(models.Telemetry.timestamp.desc()).offset(skip).limit(limit).all()


def delete_telemetry(db: Session, satellite_id: int, before: datetime | None) -> int:
    sat = _get_satellite_raw(db, satellite_id)
    if sat.status == "offline":
        raise HTTPException(status_code=404, detail="Satellite has been deorbited")

    q = db.query(models.Telemetry).filter(models.Telemetry.satellite_id == sat.id)
    if before:
        q = q.filter(models.Telemetry.timestamp < before)
    count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return count


# ═══════════════════════════════════════════
# System & Ops
# ═══════════════════════════════════════════

def get_health(db: Session) -> dict:
    try:
        db.execute(models.Satellite.__table__.select().limit(1))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")


def get_windows(db: Session, satellite_id: int) -> dict:
    sat = _get_satellite_or_404(db, satellite_id)
    return {
        "satellite_id": sat.id,
        "satellite_name": sat.name,
        "in_signal": sat.in_signal,
        "next_window_start": sat.next_window_start,
    }


def emergency_safemode(db: Session) -> schemas.EmergencyResponse:
    sats = db.query(models.Satellite).filter(models.Satellite.status != "offline").all()

    sats_affected = 0
    payloads_deactivated = 0
    maneuvers_aborted = 0

    for sat in sats:
        if sat.status != "safe_mode":
            sat.status = "safe_mode"
            sats_affected += 1

        for p in sat.payloads:
            if p.is_active:
                p.is_active = False
                sat.current_power = min(sat.current_power + p.power_draw, sat.power_capacity)
                payloads_deactivated += 1

        active_maneuvers = (
            db.query(models.Maneuver)
            .filter(
                models.Maneuver.satellite_id == sat.id,
                models.Maneuver.status.in_(["draft", "calculating", "authorized"]),
            )
            .all()
        )
        for m in active_maneuvers:
            m.status = "aborted"
            maneuvers_aborted += 1

    db.commit()
    return schemas.EmergencyResponse(
        satellites_affected=sats_affected,
        payloads_deactivated=payloads_deactivated,
        maneuvers_aborted=maneuvers_aborted,
    )


def reset_database(db: Session):
    db.query(models.Telemetry).delete()
    db.query(models.Maneuver).delete()
    db.query(models.Payload).delete()
    db.query(models.Satellite).delete()
    db.commit()

# ═══ FILE: app/schemas.py ═══

from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional


# ── Satellite ──

VALID_ORBIT_TYPES = {"LEO", "MEO", "GEO"}
VALID_SATELLITE_STATUSES = {"active", "safe_mode", "maneuvering", "offline"}


class SatelliteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    orbit_type: str
    power_capacity: float = Field(..., gt=0)

    @field_validator("orbit_type")
    @classmethod
    def validate_orbit_type(cls, v):
        if v not in VALID_ORBIT_TYPES:
            raise ValueError(f"orbit_type must be one of {VALID_ORBIT_TYPES}")
        return v


class SatelliteModeUpdate(BaseModel):
    status: Optional[str] = None
    in_signal: Optional[bool] = None
    next_window_start: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_SATELLITE_STATUSES:
            raise ValueError(f"status must be one of {VALID_SATELLITE_STATUSES}")
        return v


class SatelliteResponse(BaseModel):
    id: int
    name: str
    orbit_type: str
    status: str
    power_capacity: float
    current_power: float
    in_signal: bool
    next_window_start: Optional[datetime]
    download_count: int
    created_at: datetime
    active_payloads: int = 0

    model_config = {"from_attributes": True}


class SatelliteListResponse(BaseModel):
    id: int
    name: str
    orbit_type: str
    status: str
    power_capacity: float
    current_power: float
    in_signal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Payload ──

VALID_PAYLOAD_TYPES = {"radar", "camera", "comms_relay", "experimental"}
VALID_DATA_FORMATS = {"json", "binary", "protobuf"}


class PayloadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str
    power_draw: float = Field(..., gt=0)
    data_format: str = "json"
    is_sensitive: bool = False

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_PAYLOAD_TYPES:
            raise ValueError(f"type must be one of {VALID_PAYLOAD_TYPES}")
        return v

    @field_validator("data_format")
    @classmethod
    def validate_data_format(cls, v):
        if v not in VALID_DATA_FORMATS:
            raise ValueError(f"data_format must be one of {VALID_DATA_FORMATS}")
        return v


class PayloadPowerUpdate(BaseModel):
    state: str
    target_coordinates: Optional[dict] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        if v not in {"on", "off"}:
            raise ValueError("state must be 'on' or 'off'")
        return v


class PayloadResponse(BaseModel):
    id: int
    satellite_id: int
    name: str
    type: str
    power_draw: float
    is_active: bool
    data_format: str
    is_sensitive: bool

    model_config = {"from_attributes": True}


class PayloadPowerResponse(BaseModel):
    id: int
    is_active: bool
    satellite_current_power: float


# ── Maneuver ──

VALID_DIRECTIONS = {"prograde", "retrograde", "radial_in", "radial_out", "normal", "anti_normal"}
VALID_MANEUVER_STATUSES = {"draft", "calculating", "authorized", "executing", "completed", "aborted"}


class ManeuverCreate(BaseModel):
    delta_v: float = Field(..., gt=0)
    direction: str
    scheduled_start: datetime
    scheduled_end: datetime

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in VALID_DIRECTIONS:
            raise ValueError(f"direction must be one of {VALID_DIRECTIONS}")
        return v

    @model_validator(mode="after")
    def validate_times(self):
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class ManeuverAuthorize(BaseModel):
    force_execute: bool = False


class ManeuverResponse(BaseModel):
    id: int
    satellite_id: int
    delta_v: float
    direction: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    authorized_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Telemetry ──

class TelemetryReading(BaseModel):
    timestamp: datetime
    battery_level: float = Field(..., ge=0, le=100)
    temperature_c: float
    radiation_msv: float = Field(..., ge=0)
    signal_strength_dbm: float


class TelemetryIngest(BaseModel):
    readings: list[TelemetryReading] = Field(..., min_length=1)


class TelemetryIngestResponse(BaseModel):
    ingested: int
    warnings: list[str] = []


class TelemetryResponse(BaseModel):
    id: int
    satellite_id: int
    timestamp: datetime
    battery_level: float
    temperature_c: float
    radiation_msv: float
    signal_strength_dbm: float

    model_config = {"from_attributes": True}


# ── System ──

class HealthResponse(BaseModel):
    status: str
    database: str


class WindowsResponse(BaseModel):
    satellite_id: int
    satellite_name: str
    in_signal: bool
    next_window_start: Optional[datetime]


class EmergencyResponse(BaseModel):
    satellites_affected: int
    payloads_deactivated: int
    maneuvers_aborted: int


# ── Generic Error ──

class ErrorResponse(BaseModel):
    detail: str

# ═══ FILE: app/models.py ═══

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Satellite(Base):
    __tablename__ = "satellites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    orbit_type = Column(String, nullable=False)  # LEO, MEO, GEO
    status = Column(String, nullable=False, default="active")  # active, safe_mode, maneuvering, offline
    power_capacity = Column(Float, nullable=False)
    current_power = Column(Float, nullable=False)
    in_signal = Column(Boolean, nullable=False, default=True)
    next_window_start = Column(DateTime, nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    payloads = relationship("Payload", back_populates="satellite", lazy="selectin")
    maneuvers = relationship("Maneuver", back_populates="satellite", lazy="selectin")
    telemetry_readings = relationship("Telemetry", back_populates="satellite", cascade="all, delete-orphan")


class Payload(Base):
    __tablename__ = "payloads"

    id = Column(Integer, primary_key=True, index=True)
    satellite_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # radar, camera, comms_relay, experimental
    power_draw = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    data_format = Column(String, nullable=False, default="json")  # json, binary, protobuf
    is_sensitive = Column(Boolean, nullable=False, default=False)

    satellite = relationship("Satellite", back_populates="payloads")


class Maneuver(Base):
    __tablename__ = "maneuvers"

    id = Column(Integer, primary_key=True, index=True)
    satellite_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    delta_v = Column(Float, nullable=False)
    direction = Column(String, nullable=False)  # prograde, retrograde, radial_in, radial_out, normal, anti_normal
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="calculating")  # draft, calculating, authorized, executing, completed, aborted
    authorized_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    satellite = relationship("Satellite", back_populates="maneuvers")


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    satellite_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    battery_level = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    radiation_msv = Column(Float, nullable=False)
    signal_strength_dbm = Column(Float, nullable=False)

    satellite = relationship("Satellite", back_populates="telemetry_readings")
