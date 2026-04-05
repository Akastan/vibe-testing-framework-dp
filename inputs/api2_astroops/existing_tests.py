"""
Reference integration tests for AstroOps API.
Run with: pytest tests/test_existing.py -v
Server must be running on http://localhost:8000
"""
import uuid
import requests

BASE = "http://localhost:8000"
AUTH = {"Authorization": "Bearer test-token"}
CLEARANCE = {**AUTH, "X-Clearance": "flight-director"}


def unique(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def reset_db():
    r = requests.post(f"{BASE}/reset", timeout=30)
    assert r.status_code == 200


def create_satellite(name=None, power=1000.0, orbit="LEO"):
    name = name or unique("SAT-")
    r = requests.post(
        f"{BASE}/satellites",
        json={"name": name, "orbit_type": orbit, "power_capacity": power},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 201
    return r.json()


def create_payload(sat_id, name=None, ptype="radar", draw=100.0, fmt="json", sensitive=False):
    name = name or unique("PL-")
    r = requests.post(
        f"{BASE}/satellites/{sat_id}/payloads",
        json={"name": name, "type": ptype, "power_draw": draw, "data_format": fmt, "is_sensitive": sensitive},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 201
    return r.json()


def create_maneuver(sat_id, delta_v=2.5, direction="prograde", start="2099-01-01T00:00:00Z", end="2099-01-01T01:00:00Z"):
    r = requests.post(
        f"{BASE}/satellites/{sat_id}/maneuvers",
        json={"delta_v": delta_v, "direction": direction, "scheduled_start": start, "scheduled_end": end},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 201
    return r.json()


# ═══════════════════════════════════════════
# Health
# ═══════════════════════════════════════════

def test_health():
    reset_db()
    r = requests.get(f"{BASE}/health", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ═══════════════════════════════════════════
# Satellites - CRUD
# ═══════════════════════════════════════════

def test_create_satellite():
    reset_db()
    sat = create_satellite("ALPHA-1", 1500.0, "LEO")
    assert sat["name"] == "ALPHA-1"
    assert sat["power_capacity"] == 1500.0
    assert sat["current_power"] == 1500.0
    assert sat["status"] == "active"
    assert sat["in_signal"] is True


def test_create_satellite_duplicate_name_409():
    reset_db()
    create_satellite("DUP-SAT")
    r = requests.post(
        f"{BASE}/satellites",
        json={"name": "DUP-SAT", "orbit_type": "LEO", "power_capacity": 500},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 409


def test_create_satellite_invalid_orbit_422():
    reset_db()
    r = requests.post(
        f"{BASE}/satellites",
        json={"name": unique("SAT-"), "orbit_type": "INVALID", "power_capacity": 500},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


def test_create_satellite_negative_power_422():
    reset_db()
    r = requests.post(
        f"{BASE}/satellites",
        json={"name": unique("SAT-"), "orbit_type": "LEO", "power_capacity": -100},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


def test_list_satellites_filter_status():
    reset_db()
    create_satellite("S1")
    create_satellite("S2")
    r = requests.get(f"{BASE}/satellites", params={"status": "active"}, headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_satellite_404():
    reset_db()
    r = requests.get(f"{BASE}/satellites/9999", headers=AUTH, timeout=30)
    assert r.status_code == 404


def test_get_satellite_detail():
    reset_db()
    sat = create_satellite()
    r = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["id"] == sat["id"]


# ═══════════════════════════════════════════
# Satellites - Mode switching
# ═══════════════════════════════════════════

def test_switch_to_safe_mode():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=200)
    requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)

    r = requests.patch(
        f"{BASE}/satellites/{sat['id']}/mode",
        json={"status": "safe_mode"}, headers=AUTH, timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "safe_mode"
    assert r.json()["active_payloads"] == 0
    assert r.json()["current_power"] == sat["power_capacity"]


def test_switch_safe_to_active():
    reset_db()
    sat = create_satellite()
    requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"status": "safe_mode"}, headers=AUTH, timeout=30)
    r = requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"status": "active"}, headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_switch_maneuvering_to_active_400():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    r = requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"status": "active"}, headers=AUTH, timeout=30)
    assert r.status_code == 400


def test_set_in_signal():
    reset_db()
    sat = create_satellite()
    r = requests.patch(
        f"{BASE}/satellites/{sat['id']}/mode",
        json={"in_signal": False, "next_window_start": "2099-12-31T23:59:59Z"},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["in_signal"] is False


# ═══════════════════════════════════════════
# Satellites - Deorbit
# ═══════════════════════════════════════════

def test_deorbit_satellite_202():
    reset_db()
    sat = create_satellite()
    r = requests.delete(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r.status_code == 202
    # Satellite now offline
    r2 = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r2.status_code == 404


def test_deorbit_offline_400():
    reset_db()
    sat = create_satellite()
    requests.delete(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    r = requests.delete(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r.status_code == 404  # offline = not found


def test_deorbit_during_maneuver_423():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    r = requests.delete(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r.status_code == 423


# ═══════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════

def test_missing_auth_401():
    reset_db()
    r = requests.get(f"{BASE}/satellites", timeout=30)
    assert r.status_code == 401


def test_health_no_auth_required():
    r = requests.get(f"{BASE}/health", timeout=30)
    assert r.status_code == 200


# ═══════════════════════════════════════════
# Payloads
# ═══════════════════════════════════════════

def test_create_and_list_payloads():
    reset_db()
    sat = create_satellite()
    create_payload(sat["id"], ptype="radar", draw=100)
    create_payload(sat["id"], ptype="camera", draw=200, sensitive=True)
    r = requests.get(f"{BASE}/satellites/{sat['id']}/payloads", headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_payload_power_on_success():
    reset_db()
    sat = create_satellite(power=500)
    pl = create_payload(sat["id"], draw=200)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["is_active"] is True
    assert r.json()["satellite_current_power"] == 300.0


def test_payload_power_on_insufficient_412():
    reset_db()
    sat = create_satellite(power=100)
    pl = create_payload(sat["id"], draw=200)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 412


def test_payload_power_idempotent_off():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "off"}, headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_payload_power_on_safe_mode_400():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"status": "safe_mode"}, headers=AUTH, timeout=30)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 400


def test_payload_locked_during_maneuver_423():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 423


def test_payload_los_503():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"in_signal": False}, headers=AUTH, timeout=30)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 503


def test_sensitive_payload_no_clearance_403():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="camera", draw=100, sensitive=True)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 403


def test_sensitive_payload_with_clearance():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="camera", draw=100, sensitive=True)
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=CLEARANCE, timeout=30)
    assert r.status_code == 200
    assert r.json()["is_active"] is True


def test_payload_data_experimental_501():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="experimental", draw=50)
    r = requests.get(f"{BASE}/payloads/{pl['id']}/data", headers=AUTH, timeout=30)
    assert r.status_code == 501


def test_payload_data_wrong_accept_406():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="radar", draw=50, fmt="binary")
    h = {**AUTH, "Accept": "application/json"}
    r = requests.get(f"{BASE}/payloads/{pl['id']}/data", headers=h, timeout=30)
    assert r.status_code == 406


def test_payload_data_sensitive_no_clearance_403():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="camera", draw=50, fmt="json", sensitive=True)
    r = requests.get(f"{BASE}/payloads/{pl['id']}/data", headers=AUTH, timeout=30)
    assert r.status_code == 403


def test_payload_itar_451():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="camera", draw=100, sensitive=False)
    r = requests.patch(
        f"{BASE}/payloads/{pl['id']}/power",
        json={"state": "on", "target_coordinates": {"lat": 35.0, "lon": 45.0}},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 451


# ═══════════════════════════════════════════
# Maneuvers
# ═══════════════════════════════════════════

def test_create_maneuver():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    assert m["status"] == "calculating"
    assert m["satellite_id"] == sat["id"]


def test_maneuver_safe_mode_400():
    reset_db()
    sat = create_satellite()
    requests.patch(f"{BASE}/satellites/{sat['id']}/mode", json={"status": "safe_mode"}, headers=AUTH, timeout=30)
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/maneuvers",
        json={"delta_v": 1.0, "direction": "prograde", "scheduled_start": "2099-06-01T00:00:00Z", "scheduled_end": "2099-06-01T01:00:00Z"},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 400


def test_maneuver_time_collision_409():
    reset_db()
    sat = create_satellite()
    create_maneuver(sat["id"], start="2099-01-01T00:00:00Z", end="2099-01-01T02:00:00Z")
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/maneuvers",
        json={"delta_v": 1.0, "direction": "retrograde", "scheduled_start": "2099-01-01T01:00:00Z", "scheduled_end": "2099-01-01T03:00:00Z"},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 409


def test_authorize_maneuver_success():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    r = requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", headers=CLEARANCE, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "authorized"


def test_authorize_no_clearance_403():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    r = requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", headers=AUTH, timeout=30)
    assert r.status_code == 403


def test_authorize_force_execute():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    r = requests.post(
        f"{BASE}/maneuvers/{m['id']}/authorize",
        json={"force_execute": True}, headers=CLEARANCE, timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "executing"
    # Satellite should be maneuvering
    r2 = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r2.json()["status"] == "maneuvering"


def test_abort_maneuver_204():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    r = requests.delete(f"{BASE}/maneuvers/{m['id']}/abort", headers=AUTH, timeout=30)
    assert r.status_code == 204


def test_abort_executing_returns_active():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    r = requests.delete(f"{BASE}/maneuvers/{m['id']}/abort", headers=AUTH, timeout=30)
    assert r.status_code == 204
    r2 = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r2.json()["status"] == "active"


def test_abort_completed_400():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    requests.post(f"{BASE}/maneuvers/{m['id']}/complete", headers=AUTH, timeout=30)
    r = requests.delete(f"{BASE}/maneuvers/{m['id']}/abort", headers=AUTH, timeout=30)
    assert r.status_code == 400


def test_complete_maneuver():
    reset_db()
    sat = create_satellite()
    m = create_maneuver(sat["id"])
    requests.post(f"{BASE}/maneuvers/{m['id']}/authorize", json={"force_execute": True}, headers=CLEARANCE, timeout=30)
    r = requests.post(f"{BASE}/maneuvers/{m['id']}/complete", headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    r2 = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r2.json()["status"] == "active"


def test_maneuver_invalid_direction_422():
    reset_db()
    sat = create_satellite()
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/maneuvers",
        json={"delta_v": 1.0, "direction": "sideways", "scheduled_start": "2099-01-01T00:00:00Z", "scheduled_end": "2099-01-01T01:00:00Z"},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


def test_maneuver_end_before_start_422():
    reset_db()
    sat = create_satellite()
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/maneuvers",
        json={"delta_v": 1.0, "direction": "prograde", "scheduled_start": "2099-01-01T02:00:00Z", "scheduled_end": "2099-01-01T01:00:00Z"},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


# ═══════════════════════════════════════════
# Telemetry
# ═══════════════════════════════════════════

def test_ingest_telemetry():
    reset_db()
    sat = create_satellite()
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": [
            {"timestamp": "2026-04-05T10:00:00Z", "battery_level": 85.0, "temperature_c": 22.0, "radiation_msv": 0.1, "signal_strength_dbm": -70},
        ]},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 201
    assert r.json()["ingested"] == 1
    assert r.json()["warnings"] == []


def test_telemetry_auto_safe_mode():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)

    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": [
            {"timestamp": "2026-04-05T10:00:00Z", "battery_level": 10.0, "temperature_c": 50.0, "radiation_msv": 0.5, "signal_strength_dbm": -90},
        ]},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 201
    assert len(r.json()["warnings"]) > 0

    r2 = requests.get(f"{BASE}/satellites/{sat['id']}", headers=AUTH, timeout=30)
    assert r2.json()["status"] == "safe_mode"
    assert r2.json()["active_payloads"] == 0


def test_telemetry_batch_limit_422():
    reset_db()
    sat = create_satellite()
    readings = [
        {"timestamp": f"2026-04-05T{i:02d}:00:00Z", "battery_level": 80, "temperature_c": 20, "radiation_msv": 0.1, "signal_strength_dbm": -70}
        for i in range(51)
    ]
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": readings},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


def test_query_telemetry():
    reset_db()
    sat = create_satellite()
    requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": [
            {"timestamp": "2026-04-05T10:00:00Z", "battery_level": 80, "temperature_c": 20, "radiation_msv": 0.1, "signal_strength_dbm": -70},
            {"timestamp": "2026-04-05T11:00:00Z", "battery_level": 75, "temperature_c": 21, "radiation_msv": 0.2, "signal_strength_dbm": -72},
        ]},
        headers=AUTH, timeout=30,
    )
    r = requests.get(f"{BASE}/satellites/{sat['id']}/telemetry", headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_delete_telemetry_204():
    reset_db()
    sat = create_satellite()
    requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": [
            {"timestamp": "2026-04-05T10:00:00Z", "battery_level": 80, "temperature_c": 20, "radiation_msv": 0.1, "signal_strength_dbm": -70},
        ]},
        headers=AUTH, timeout=30,
    )
    r = requests.delete(f"{BASE}/satellites/{sat['id']}/telemetry", headers=AUTH, timeout=30)
    assert r.status_code == 204


def test_telemetry_invalid_battery_422():
    reset_db()
    sat = create_satellite()
    r = requests.post(
        f"{BASE}/satellites/{sat['id']}/telemetry",
        json={"readings": [
            {"timestamp": "2026-04-05T10:00:00Z", "battery_level": 150, "temperature_c": 20, "radiation_msv": 0.1, "signal_strength_dbm": -70},
        ]},
        headers=AUTH, timeout=30,
    )
    assert r.status_code == 422


# ═══════════════════════════════════════════
# System & Ops
# ═══════════════════════════════════════════

def test_windows():
    reset_db()
    sat = create_satellite()
    r = requests.get(f"{BASE}/windows", params={"satellite_id": sat["id"]}, headers=AUTH, timeout=30)
    assert r.status_code == 200
    assert r.json()["in_signal"] is True


def test_windows_404():
    reset_db()
    r = requests.get(f"{BASE}/windows", params={"satellite_id": 9999}, headers=AUTH, timeout=30)
    assert r.status_code == 404


def test_emergency_safemode():
    reset_db()
    s1 = create_satellite("E1")
    s2 = create_satellite("E2")
    p1 = create_payload(s1["id"], draw=100)
    requests.patch(f"{BASE}/payloads/{p1['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    m1 = create_maneuver(s2["id"])

    r = requests.post(f"{BASE}/emergency/safemode", headers=AUTH, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["satellites_affected"] == 2
    assert body["payloads_deactivated"] == 1
    assert body["maneuvers_aborted"] == 1

    # Verify satellites are in safe_mode
    r2 = requests.get(f"{BASE}/satellites/{s1['id']}", headers=AUTH, timeout=30)
    assert r2.json()["status"] == "safe_mode"


# ═══════════════════════════════════════════
# 425 Too Early
# ═══════════════════════════════════════════

def test_payload_too_early_425():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], draw=100)
    # Set LOS with window opening in 3 minutes
    from datetime import datetime, timedelta, timezone
    soon = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
    requests.patch(
        f"{BASE}/satellites/{sat['id']}/mode",
        json={"in_signal": False, "next_window_start": soon},
        headers=AUTH, timeout=30,
    )
    r = requests.patch(f"{BASE}/payloads/{pl['id']}/power", json={"state": "on"}, headers=AUTH, timeout=30)
    assert r.status_code == 425


# ═══════════════════════════════════════════
# 402 Payment Required (downlink quota)
# ═══════════════════════════════════════════

def test_downlink_quota_402():
    reset_db()
    sat = create_satellite()
    pl = create_payload(sat["id"], ptype="radar", draw=50, fmt="json")
    # Exhaust quota
    for _ in range(100):
        requests.get(f"{BASE}/payloads/{pl['id']}/data", headers=AUTH, timeout=30)
    r = requests.get(f"{BASE}/payloads/{pl['id']}/data", headers=AUTH, timeout=30)
    assert r.status_code == 402