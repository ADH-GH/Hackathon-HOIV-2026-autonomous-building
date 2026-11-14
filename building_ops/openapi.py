"""OpenAPI description of the interface a live deployment would need.

    python -m building_ops.openapi > docs/api/openapi.json

This is a contract, not a server. Today the pipeline reads a directory of files and writes
decisions.jsonl. The description says how the same tables would arrive from real systems
(ingest), how decisions and approvals would be read and answered, and how actions would leave
towards real systems (webhooks). Field names are those of the PLATO-40 dataset and of
DECISION_CONTRACT v2, and the enumerations are taken from the code, so the two cannot drift.
"""
from __future__ import annotations

import json

from .decisions import ACTIONS, LEVELS, PRIORITIES

TS = {"type": "string", "format": "date-time", "description": "ISO 8601, UTC"}
NUM = {"type": "number"}
INT = {"type": "integer"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


# One entry per table the detectors read: path, tag, the system that owns the data, what the row is,
# its columns, the columns that must be present, and the column that says when the row became known.
TABLES = [
    ("bookings", "Bookings", "PMS", "Property management system",
     "A reservation, created or changed. Send the full row again when it changes.",
     {"booking_id": STR, "room_id": STR, "created_utc": TS, "arrival_utc": TS, "departure_utc": TS, "guest_count": INT,
      "channel": STR, "status": enum("confirmed", "cancelled")},
     ["booking_id", "room_id", "created_utc", "arrival_utc", "departure_utc", "status"], "created_utc"),
    ("room-events", "Room events", "PMS", "Property management system, housekeeping app, robot fleet, vending and waste telemetry",
     "Something that happened: a check-in, a check-out, a cleaning step, a restock, an alarm of the building management system.",
     {"event_id": STR, "timestamp_utc": TS,
      "type": enum("checkin", "checkin_early", "checkin_after_wait", "arrival_waiting_room", "checkout", "checkout_early", "no_show",
                   "stay_in_progress", "room_reassigned", "cleaning_started", "cleaning_completed", "robot_floor_cleaning_started",
                   "robot_floor_cleaning_completed", "floor_bin_emptied", "waste_pickup", "waste_bin_full", "vending_restocked",
                   "vending_out_of_stock", "bms_alarm"),
      "room_id": STR, "booking_id": STR, "asset_id": STR, "resource_id": STR, "guests": INT},
     ["event_id", "timestamp_utc", "type"], None),
    ("guest-requests", "Guest requests", "Guest messaging", "Guest messaging: chat, SMS, e-mail or the PMS inbox",
     "A message from a guest, with its language and the time an answer is due.",
     {"request_id": STR, "timestamp_utc": TS, "room_id": STR, "booking_id": STR, "channel": STR, "language": STR,
      "request_type": enum("access_issue", "air_quality", "arrival_delay", "cleaning_request", "early_checkin", "extra_towels", "invoice",
                           "late_checkout", "luggage_storage", "maintenance_issue", "noise_complaint", "parking", "temperature_cold",
                           "temperature_hot"),
      "text": STR, "priority": enum(*PRIORITIES), "response_due_utc": TS, "requires_guest_consent": BOOL},
     ["request_id", "timestamp_utc", "request_type"], None),
    ("access-log", "Access log", "Access control", "Door and lock system",
     "One use of a credential at a door. Send a pseudonymous credential reference, never a name.",
     {"timestamp_utc": TS, "door_id": STR, "credential": STR, "result": STR}, ["timestamp_utc", "door_id", "result"], None),
    ("room-telemetry", "Room telemetry", "Room controls", "Room automation or building management system",
     "One reading per room, every 15 minutes in the dataset. A missing value stays missing: send null, not zero.",
     {"timestamp_utc": TS, "room_id": STR, "temperature_c": nullable(NUM), "setpoint_c": nullable(NUM), "humidity_pct": nullable(NUM),
      "co2_ppm": nullable(NUM), "presence": nullable(BOOL), "window_open": nullable(BOOL), "housekeeping_state": STR},
     ["timestamp_utc", "room_id"], None),
    ("water-meters", "Water meters", "Metering", "Water meters of the rooms and the main supply",
     "A cumulative meter reading in litres. Use the meter id of the room (for example R403) or WM_MAIN for the main supply.",
     {"timestamp_utc": TS, "meter_id": STR, "meter_total_l": nullable(NUM)}, ["timestamp_utc", "meter_id"], None),
    ("energy", "Energy", "Energy", "Grid meter, PV inverter and battery",
     "Building load, PV output, battery state and grid exchange at one moment.",
     {"timestamp_utc": TS, "building_load_kw": nullable(NUM), "hvac_electric_kw": nullable(NUM), "pv_kw": nullable(NUM),
      "battery_discharge_kw_signed": nullable(NUM), "battery_soc_kwh": nullable(NUM), "grid_import_kw": nullable(NUM),
      "grid_export_kw": nullable(NUM)}, ["timestamp_utc"], None),
    ("equipment", "Equipment", "Plant", "Heat pump and air handling unit, through the building management system",
     "One metric of one plant asset at one moment.",
     {"timestamp_utc": TS, "asset_id": STR,
      "metric": enum("airflow_m3h", "electric_kw", "fan_kw", "filter_dp_pa", "heat_output_kw", "status", "supply_air_c", "supply_temp_c"),
      "value": nullable({"type": ["number", "string"]})}, ["timestamp_utc", "asset_id", "metric"], None),
    ("logistics", "Logistics", "Logistics", "Vending machine and waste container telemetry",
     "A stock count or a fill level.",
     {"timestamp_utc": TS, "asset_id": STR, "metric": enum("fill_pct", "stock_drinks", "stock_snacks"), "value": nullable(NUM)},
     ["timestamp_utc", "asset_id", "metric"], None),
    ("weather", "Weather", "Weather", "Weather station or weather service",
     "Observed outdoor conditions.", {"timestamp_utc": TS, "outdoor_c": nullable(NUM), "cloud_cover_pct": nullable(NUM)},
     ["timestamp_utc"], None),
    ("weather-forecast", "Weather forecast", "Weather", "Weather service",
     "A forecast value with the time it was issued. A decision may only use forecasts issued before it.",
     {"issued_utc": TS, "target_utc": TS, "outdoor_c_forecast": NUM}, ["issued_utc", "target_utc", "outdoor_c_forecast"], "issued_utc"),
    ("tariff", "Tariff", "Energy market", "Day-ahead electricity price feed",
     "An hourly price with the time it was published. A decision may only use prices published before it.",
     {"timestamp_utc": TS, "price_eur_kwh": NUM, "published_utc": TS}, ["timestamp_utc", "price_eur_kwh", "published_utc"], "published_utc"),
    ("staff-roster", "Staff roster", "Workforce", "Roster of cleaners, technicians and robots",
     "A shift and its status, with the time that status became known. Send the row again when someone calls in sick.",
     {"shift_id": STR, "resource_id": STR, "role": enum("cleaner", "technician", "robot"), "start_utc": TS, "end_utc": TS,
      "status": enum("scheduled", "sick", "vacation", "out_of_service"), "status_known_utc": TS},
     ["shift_id", "resource_id", "role", "start_utc", "end_utc", "status", "status_known_utc"], "status_known_utc"),
    ("work-orders", "Work orders", "Maintenance", "Maintenance or ticket system",
     "A work order and its state. The detectors do not read work orders; they close the loop: they show whether an action was carried out.",
     {"work_order_id": STR, "created_utc": TS, "asset_id": STR, "type": enum("corrective", "preventive", "metering"), "status": STR,
      "scheduled_utc": nullable(TS), "completed_utc": nullable(TS), "assigned_to": STR, "summary": STR},
     ["work_order_id", "created_utc", "asset_id", "type", "status"], "created_utc"),
]

DECISION = {
    "type": "object",
    "description": "One decision, exactly as written to decisions.jsonl (DECISION_CONTRACT v2).",
    "required": ["event_id", "timestamp_utc", "affected_assets", "issue_type", "action", "priority", "reason", "requires_human_approval"],
    "properties": {
        "event_id": STR, "episode_id": {**STR, "description": "Groups the decisions of one case"},
        "timestamp_utc": {**TS, "description": "The moment the decision is taken, using only information available at that time"},
        "affected_assets": {"type": "array", "items": STR, "minItems": 1},
        "issue_type": {**STR, "examples": ["room_turnaround", "water_leak", "heating_comfort", "ventilation_maintenance", "occupancy_surge",
                                           "energy_optimization", "logistics", "data_quality"]},
        "action": enum(*ACTIONS), "priority": enum(*PRIORITIES), "reason": STR,
        "requires_human_approval": BOOL, "requires_guest_consent": BOOL, "autonomy": enum(*LEVELS),
        "stage": STR, "evidence": {"type": "array", "items": STR}, "resource_id": STR, "expected_outcome": STR, "verification_plan": STR,
        "dependencies": {"type": "array", "items": STR}, "guest_request_ids": {"type": "array", "items": STR},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

SCHEMAS = {
    "Decision": DECISION,
    "DecisionState": {
        "type": "object", "description": "A decision with what happened to it since.",
        "required": ["decision", "state"],
        "properties": {
            "decision": {"$ref": "#/components/schemas/Decision"},
            "state": enum("executed", "waiting_for_approval", "waiting_for_consent", "approved", "rejected", "failed", "expired"),
            "consent": {"$ref": "#/components/schemas/Consent"},
            "decided_by": {**STR, "description": "The person who approved or rejected"}, "decided_utc": TS,
            "action_results": {"type": "array", "items": {"$ref": "#/components/schemas/ActionResult"}},
        },
    },
    "Case": {
        "type": "object", "description": "All decisions of one episode, oldest first.",
        "required": ["episode_id", "issue_type", "priority", "first_decision_utc", "decisions"],
        "properties": {"episode_id": STR, "title": STR, "issue_type": STR, "priority": enum(*PRIORITIES), "first_decision_utc": TS,
                       "affected_assets": {"type": "array", "items": STR},
                       "decisions": {"type": "array", "items": {"$ref": "#/components/schemas/DecisionState"}}},
    },
    "Status": {
        "type": "object",
        "properties": {"as_of_utc": TS, "decisions_total": INT, "cases_open": INT, "critical_open": INT, "waiting_for_approval": INT,
                       "waiting_for_consent": INT,
                       "feeds": {"type": "array", "description": "One entry per ingest feed: a silent feed is a finding, not a quiet building.",
                                 "items": {"type": "object", "properties": {"feed": STR, "last_row_utc": TS, "last_received_utc": TS,
                                                                            "state": enum("ok", "late", "silent")}}}},
    },
    "Consent": {
        "type": "object", "required": ["given_by", "channel", "recorded_utc"],
        "description": "Proof that the guest agreed. A consent requirement is not consent granted.",
        "properties": {"given_by": {**STR, "description": "Booking id of the guest, not a name"}, "channel": enum("phone", "chat", "in_person", "app"),
                       "recorded_utc": TS, "recorded_by": STR, "note": STR},
    },
    "ApprovalRequest": {
        "type": "object", "required": ["decided_by"],
        "properties": {"decided_by": {**STR, "description": "Identity of the approver from the identity provider"}, "note": STR},
    },
    "ActionRequest": {
        "type": "object", "description": "What a connector is asked to do. Sent once per action; repeat deliveries carry the same action_id.",
        "required": ["action_id", "action", "decision", "dry_run"],
        "properties": {"action_id": STR, "action": enum(*ACTIONS), "decision": {"$ref": "#/components/schemas/Decision"},
                       "parameters": {"type": "object", "additionalProperties": True,
                                      "description": "Action-specific values, for example room_id and setpoint_c, or the message text and language"},
                       "approved_by": STR, "consent": {"$ref": "#/components/schemas/Consent"},
                       "dry_run": {**BOOL, "description": "true while the deployment runs in shadow mode: log it, do not do it"},
                       "not_after_utc": {**TS, "description": "Do not carry the action out after this time"}},
    },
    "ActionResult": {
        "type": "object", "required": ["action_id", "status", "reported_utc"],
        "properties": {"action_id": STR, "status": enum("accepted", "done", "failed", "refused"), "reported_utc": TS,
                       "external_reference": {**STR, "description": "Id in the target system, for example a work order or message id"},
                       "detail": STR},
    },
    "EmergencyRequest": {
        "type": "object", "required": ["reported_by"],
        "properties": {"episode_id": {**STR, "description": "The case it is about, if known"}, "asset_id": {**STR, "description": "Room or asset, if no case is known"},
                       "what": {**STR, "description": "The caller's own words"}, "reported_by": STR,
                       "callback_number": {**STR, "description": "Number to bridge to the on-call team"}},
    },
    "Emergency": {
        "type": "object", "required": ["emergency_id", "state", "opened_utc"],
        "properties": {"emergency_id": STR, "state": enum("connecting", "connected", "no_answer", "closed"), "opened_utc": TS, "closed_utc": TS,
                       "on_call": {**STR, "description": "Role that was reached, not a private number"}, "case": {"$ref": "#/components/schemas/Case"}},
    },
    "IngestResult": {
        "type": "object", "required": ["accepted", "rejected"],
        "properties": {"accepted": INT, "duplicates": {**INT, "description": "Rows already known and unchanged"},
                       "rejected": {"type": "array", "items": {"type": "object", "properties": {"index": INT, "reason": STR}}}},
    },
    "Error": {"type": "object", "required": ["error"], "properties": {"error": STR, "detail": STR}},
}


def ref(name):
    return {"$ref": "#/components/schemas/" + name}


def body(schema, description=None):
    out = {"required": True, "content": {"application/json": {"schema": schema}}}
    if description:
        out["description"] = description
    return out


def ok(schema, description="OK"):
    return {"description": description, "content": {"application/json": {"schema": schema}}}


ERRORS = {"401": {"description": "Missing or wrong X-Auth key"}, "422": ok(ref("Error"), "The request does not match the schema")}


def build() -> dict:
    paths, tags = {}, [
        {"name": "Ingest", "description": "Connectors push rows here, one feed per table the detectors read. Every row carries the time it happened; "
                                          "where the dataset has a column for when a row became known, that column is required, because a decision may "
                                          "only use what was known at its moment. Rows are idempotent: sending a row again changes nothing, sending a "
                                          "changed row replaces it."},
        {"name": "Decisions", "description": "What the system decided, with the evidence, as cases and as single decisions."},
        {"name": "Approvals", "description": "Decisions that wait for a person. The rules live in the pipeline, not in the caller: an approval for a "
                                             "decision that needs guest consent is refused until the consent is on record."},
        {"name": "Actions", "description": "Actions leave as webhooks to the connector of the target system. The connector reports back here."},
        {"name": "Emergency", "description": "Bridge a caller to the on-call team and hand the team one case."},
        {"name": "System"},
    ]
    for path, title, system, owner, what, columns, required, known in TABLES:
        name = "".join(w.capitalize() for w in path.split("-")) + "Row"
        SCHEMAS[name] = {"type": "object", "description": what, "required": required, "properties": columns}
        note = f" Time of availability: `{known}`." if known else ""
        paths["/ingest/" + path] = {"post": {
            "tags": ["Ingest"], "operationId": "ingest" + name[:-3], "summary": f"{title} — from: {owner}",
            "description": what + note,
            "parameters": [{"name": "Idempotency-Key", "in": "header", "required": False, "schema": STR,
                            "description": "Repeat a batch safely after a timeout"}],
            "requestBody": body({"type": "object", "required": ["rows"],
                                 "properties": {"source": {**STR, "description": "Name of the connector instance"},
                                                "rows": {"type": "array", "minItems": 1, "maxItems": 5000, "items": ref(name)}}}),
            "responses": {"202": ok(ref("IngestResult"), "Rows taken over"), **ERRORS}}}

    event = {"name": "event_id", "in": "path", "required": True, "schema": STR}
    paths.update({
        "/status": {"get": {"tags": ["System"], "operationId": "getStatus", "summary": "Open cases, waiting approvals and the health of every feed",
                            "responses": {"200": ok(ref("Status")), "401": ERRORS["401"]}}},
        "/health": {"get": {"tags": ["System"], "operationId": "getHealth", "summary": "Liveness", "security": [],
                            "responses": {"200": ok({"type": "object", "properties": {"ok": BOOL, "version": STR}})}}},
        "/decisions": {"get": {
            "tags": ["Decisions"], "operationId": "listDecisions", "summary": "Decisions, newest first",
            "parameters": [{"name": "since", "in": "query", "schema": TS}, {"name": "issue_type", "in": "query", "schema": STR},
                           {"name": "autonomy", "in": "query", "schema": enum(*LEVELS)},
                           {"name": "state", "in": "query", "schema": SCHEMAS["DecisionState"]["properties"]["state"]},
                           {"name": "asset_id", "in": "query", "schema": STR},
                           {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100}},
                           {"name": "cursor", "in": "query", "schema": STR}],
            "responses": {"200": ok({"type": "object", "properties": {"items": {"type": "array", "items": ref("DecisionState")}, "next_cursor": STR}}),
                          "401": ERRORS["401"]}}},
        "/decisions/{event_id}": {"get": {"tags": ["Decisions"], "operationId": "getDecision", "summary": "One decision with its state", "parameters": [event],
                                          "responses": {"200": ok(ref("DecisionState")), "404": ok(ref("Error"), "Unknown decision")}}},
        "/decisions/stream": {"get": {"tags": ["Decisions"], "operationId": "streamDecisions", "summary": "New decisions as server-sent events",
                                      "description": "One event per decision, `data:` holds a Decision. For dashboards and for the voice assistant.",
                                      "responses": {"200": {"description": "text/event-stream", "content": {"text/event-stream": {"schema": STR}}}}}},
        "/cases": {"get": {"tags": ["Decisions"], "operationId": "listCases", "summary": "Cases, most urgent first",
                           "parameters": [{"name": "open", "in": "query", "schema": BOOL}, {"name": "priority", "in": "query", "schema": enum(*PRIORITIES)},
                                          {"name": "issue_type", "in": "query", "schema": STR}],
                           "responses": {"200": ok({"type": "object", "properties": {"items": {"type": "array", "items": ref("Case")}}})}}},
        "/cases/{episode_id}": {"get": {"tags": ["Decisions"], "operationId": "getCase", "summary": "One case with all its decisions",
                                        "parameters": [{"name": "episode_id", "in": "path", "required": True, "schema": STR}],
                                        "responses": {"200": ok(ref("Case")), "404": ok(ref("Error"), "Unknown case")}}},
        "/approvals": {"get": {"tags": ["Approvals"], "operationId": "listApprovals", "summary": "Decisions that wait for a person, most urgent first",
                               "responses": {"200": ok({"type": "object", "properties": {"items": {"type": "array", "items": ref("DecisionState")}}})}}},
        "/decisions/{event_id}/consent": {"post": {
            "tags": ["Approvals"], "operationId": "recordConsent", "summary": "Record the guest's consent", "parameters": [event],
            "requestBody": body(ref("Consent")),
            "responses": {"200": ok(ref("DecisionState")), "409": ok(ref("Error"), "This decision does not need consent, or is already decided")}}},
        "/decisions/{event_id}/approve": {"post": {
            "tags": ["Approvals"], "operationId": "approveDecision", "summary": "Approve; the action is then sent to its connector", "parameters": [event],
            "requestBody": body(ref("ApprovalRequest")),
            "responses": {"200": ok(ref("DecisionState")), "409": ok(ref("Error"), "Guest consent is required and not on record, or already decided")}}},
        "/decisions/{event_id}/reject": {"post": {
            "tags": ["Approvals"], "operationId": "rejectDecision", "summary": "Reject; nothing is executed", "parameters": [event],
            "requestBody": body(ref("ApprovalRequest")),
            "responses": {"200": ok(ref("DecisionState")), "409": ok(ref("Error"), "Already decided")}}},
        "/actions/{action_id}/result": {"post": {
            "tags": ["Actions"], "operationId": "reportActionResult", "summary": "A connector reports what became of an action",
            "parameters": [{"name": "action_id", "in": "path", "required": True, "schema": STR}], "requestBody": body(ref("ActionResult")),
            "responses": {"200": ok(ref("ActionResult")), "404": ok(ref("Error"), "Unknown action")}}},
        "/emergencies": {"post": {
            "tags": ["Emergency"], "operationId": "openEmergency", "summary": "Open an emergency and bridge the caller to the on-call team",
            "description": "Needs no approval: calling people in is more oversight, not less. Returns the one case the team should see.",
            "requestBody": body(ref("EmergencyRequest")),
            "responses": {"201": ok(ref("Emergency"), "Emergency opened"), **ERRORS}}},
        "/emergencies/{emergency_id}": {
            "get": {"tags": ["Emergency"], "operationId": "getEmergency", "summary": "State of an emergency",
                    "parameters": [{"name": "emergency_id", "in": "path", "required": True, "schema": STR}], "responses": {"200": ok(ref("Emergency"))}},
            "delete": {"tags": ["Emergency"], "operationId": "closeEmergency", "summary": "Close an emergency",
                       "parameters": [{"name": "emergency_id", "in": "path", "required": True, "schema": STR}], "responses": {"200": ok(ref("Emergency"))}}},
    })
    hook = {"post": {
        "tags": ["Actions"], "operationId": "onActionRequested", "summary": "The system asks a connector to carry out an action",
        "description": "Sent to the URL registered for the action. The request carries the same X-Auth key the connector was given and an "
                       "X-Signature header: HMAC-SHA256 of the raw body with the shared secret. Answer 2xx with an ActionResult; a slow "
                       "target system answers `accepted` and reports the outcome later to /actions/{action_id}/result.",
        "requestBody": body(ref("ActionRequest")),
        "responses": {"200": ok(ref("ActionResult"), "Taken over or done")}}}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "PLATO-40 Building Operations API", "version": "0.1.0-draft",
            "description": "Interface for running the decision pipeline on live systems instead of the replayed dataset.\n\n"
                           "**Status: a design, not a running service.** The hackathon submission reads a directory of files and writes "
                           "`decisions.jsonl`; no server implements these paths yet. The field names are those of the PLATO-40 dataset and of "
                           "DECISION_CONTRACT v2, so a connector that fills these feeds gives the detectors exactly what they read today.\n\n"
                           "Three directions: **ingest** (real systems push rows in), **decisions and approvals** (people and dashboards read "
                           "and answer), **actions** (the system calls a connector, the connector reports back). PLATO-40 is a fictional "
                           "property; nothing here describes a real PLATO building or what CLARA does today.",
            "contact": {"name": "Alf-David Heermann", "email": "alfheermann@gmail.com"},
            "license": {"name": "MIT"},
        },
        "servers": [{"url": "https://building-ops.example/v1", "description": "Placeholder. There is no deployed server."}],
        "security": [{"XAuth": []}],
        "tags": tags, "paths": paths, "webhooks": {"actionRequested": hook},
        "components": {"schemas": SCHEMAS,
                       "securitySchemes": {"XAuth": {"type": "apiKey", "in": "header", "name": "X-Auth",
                                                     "description": "One key per connector, limited to its own feeds and actions"}}},
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=1, ensure_ascii=False))
