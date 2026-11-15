# Native GARDENA telemetry: scope and verification

This optional macOS observation path targets GARDENA Water Control Bluetooth
1889-20. It preserves the original Python replay pipeline and uses the shared
decision safety contract from PR #2. That prerequisite is not reimplemented here.

## What is implemented

Explicitly authorized discovery and selected-device reads, pinned upstream
characteristic decoding, model qualification, UTC/provenance/quality records,
append-only bounded capture, offline irrigation monitoring, strict decision
validation and an optional static dashboard view. Home Assistant is not required.

The connection is only part of the work: missing characteristics remain unknown,
lost communication does not imply closure or continuing flow, and replayed device
reports do not acquire control authority. No actuator, schedule, clock, firmware,
factory-reset or explicit pairing/unpairing operation is exposed.

## Local verification

The isolated Python 3.12.8 profile with gardena-bluetooth 3.1.0/Bleak 3.1.0 passes
83 unittest cases without skips: 64 baseline cases, five existing safety cases
and 14 native-adapter/monitoring/dashboard cases. Tests use fake scanners/GATT
clients, including actual pinned upstream decoders; no physical hardware is used.

The mock positive control follows selected reads through append-only capture,
the actual replay CLI, a battery finding, strict checking and exported evidence.
Its write counter remains zero and its private mock identifier is not exported.
Other controls cover normal/prolonged watering, stale/missing/disconnected data,
independent flow qualification, retention, model uncertainty and authorization.

```sh
python -m unittest discover -s tests -t .
python -m compileall -q building_ops tests
python -m building_ops check decisions.jsonl
python -m building_ops check decisions_holdout.jsonl
python -m building_ops gardena replay --input tests/fixtures/gardena_ble/abnormal_duration.jsonl --watering-limit-seconds 60 --out out/gardena-review/decisions.jsonl
python -m building_ops check out/gardena-review/decisions.jsonl --strict-safety
```

Use a new output destination. Normal installations skip the two optional decoder
tests explicitly. The pinned macOS environment exercises both. Setup instructions,
privacy limits and owner-authorized hardware gates are in
`docs/integrations/gardena-bluetooth.md`.

The workflow uses pinned official actions, read-only repository permissions,
no persisted checkout credentials, Linux Python 3.11/Node24 and a macOS Python
3.12 pinned-decoder profile. Local Node tests used 20.20.2; configuration alone
does not establish a successful remote run. Consult actual workflow results.

## Evidence boundary

No physical device was scanned or connected. Supported firmware characteristics,
actual model identity and physical measurements await owner-authorized validation.
Reported valve state is not measured water flow; no volume is inferred from
watering duration. A separately supplied sensor needs independent scope and
calibration evidence. Static dashboard output is not live control. Real-world
execution and resolution remain unverified.

The original decision, insight, holdout and published dashboard/API artifacts are
unchanged. External observations are not added to historical hotel denominators.
The Home Assistant adapter and broader engineering stack remain separate work.
