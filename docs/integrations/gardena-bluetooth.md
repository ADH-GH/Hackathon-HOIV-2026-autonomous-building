# Native GARDENA Bluetooth observations (1889-20)

This optional adapter reads supported status characteristics through macOS
CoreBluetooth. It does not require Home Assistant. It is separate from the
fictional hotel's room meters, datasets and autonomy figures. No physical device
has been scanned, connected or tested during development.

## Install the isolated optional environment

The application still supports Python 3.11 with no runtime dependencies. The
optional BLE profile requires Python 3.12+ on macOS. The tested profile is Python
3.12.8, gardena-bluetooth 3.1.0, Bleak 3.1.0 and the complete resolved versions in
`requirements/gardena-macos-py312.txt`.

```sh
python3.12 -m venv .venv-gardena
source .venv-gardena/bin/activate
python -m pip install -r requirements/gardena-macos-py312.txt
python -m pip install --no-deps -e .
python -m unittest discover -s tests -t .
```

`pip install -e '.[gardena-ble]'` installs the optional top-level pins, but the
macOS requirements file is the reproducibility profile for transitive versions.
No upstream `cli` extra is needed. Importing or running ordinary PLATO commands
never imports Bleak or initializes Bluetooth. The optional tests use fake scanners
and GATT clients even with the profile installed.

Source reviewed: the published 3.1.0 wheel (SHA256
`69e43f4ef370d1ce9f6e7d98589e7662348ddc45b86f8aeafa8eb5e48680f062`).
The adapter uses upstream characteristic decoders and advertisement parsing,
not copied wire encodings. It intentionally avoids the upstream general Client,
segmented reads, query/ack exchanges, notifications and clock synchronization.

## Offline demonstration (no Bluetooth or optional packages)

```sh
python -m building_ops gardena replay \
  --input tests/fixtures/gardena_ble/abnormal_duration.jsonl \
  --watering-limit-seconds 60 --out out/gardena/demo-decisions.jsonl
python -m building_ops check out/gardena/demo-decisions.jsonl --strict-safety
```

Use a new destination for each replay; existing evidence is not overwritten.
The adjacent `.evidence.json` reports provenance, policy, hashes and unknown
operational outcomes. The fixture limit is a synthetic monitoring policy, not a
manufacturer fault threshold. Normal defaults are 3,600 seconds for prolonged
watering, 20% for battery review and 180 seconds for freshness; CLI flags expose
these policies. Missing data is never a closed valve, zero flow or completed task.

## Optional static dashboard

```sh
python -m building_ops dashboard <hotel_dataset> decisions.jsonl \
  --gardena-observations tests/fixtures/gardena_ble/watering.jsonl \
  --gardena-as-of 2026-11-15T12:03:00Z --out out/gardena/dashboard.html
```

The external tab is hidden without the optional file. It shows exact UTC host
observation times, provenance, state, diagnostics, stale data and findings. It is
not live updating. External records are not added to the hotel episode log or
classification percentages. Transport IDs and serial numbers are not accepted by
the observation schema or embedded into the page. Choose a non-identifying alias.
Reported valve bits do not prove physical valve movement or measured water flow.

## Explicitly authorized hardware gates — not executed by this contribution

1. Obtain the owner's explicit permission for this device, host and bounded reads.
   Confirm macOS Bluetooth is enabled and Terminal/Python has Bluetooth access.
2. Confirm no existing controller/app will be displaced. The upstream package
   warns that prior pairing can require a reset for a new controller. **Stop** if
   reset, unpairing, reconfiguration, firmware changes or unexpected writes would
   be needed; never perform them automatically.
3. Discover only after authorization:
   `python -m building_ops gardena scan --authorize-hardware --seconds 12`.
   The normal result uses a pseudonymous handle. To select the local peripheral,
   the owner may rerun with `--show-device-ids`; do not publish that output.
4. CoreBluetooth uses host-specific peripheral UUIDs, not ordinary MAC addresses.
   Discovery filters by service `98bd0001-0b0e-421a-84e5-ddbf75dc6de4`, including
   macOS 12.0–12.2's service-filter requirement. A water-computer advertisement
   is not exact model identification.
5. Read the selected device only:
   `python -m building_ops gardena observe --authorize-hardware --device-id <LOCAL_UUID> --once --alias balcony_irrigation --out out/gardena/observations.jsonl`.
   Exact readable model 1889-20/01889-20 is required. If model data is absent,
   stop for owner identification; `--confirm-model 1889-20` records an explicit
   owner assertion rather than pretending it was device-verified. A different
   reported model is rejected. No automatic connect-to-all behavior exists.
6. If permitted, use `--samples 3 --interval-seconds 60` for bounded repeated
   observations. Each operation has a timeout, and cleanup runs on completion
   or failure. Loss of connection records unknown current state and stops intake.
   Protected reads may trigger macOS authorization. No explicit pair/unpair call
   is made; OS-level pairing behavior is not represented as absent or bypassed.
7. Replay and check the captured observations offline. Record host/runtime/library
   versions, model identification basis, supported/missing fields, times and test
   limits. Keep live reads distinct from synthetic fixtures and imported assertions.

The adapter defines no operational write path. Its client rejects GATT writes,
notification subscriptions, pairing and unpairing; reads are restricted to model
and six simple status characteristics. This is not a sandbox against an operator
modifying Python code. No valve control, schedule, pause, firmware or clock method
is exposed. Never substitute the upstream diagnostic CLI without a separate review.

## Observation schema and retention

Version 1 records have a host UTC timestamp, alias/model/provenance, connection,
quality (`VALID`, `PARTIAL`, `STALE`, `DISCONNECTED`, `UNAVAILABLE`, `INVALID`),
reported valve state, active-watering flag, remaining/manual seconds, battery,
activation reason and missing-field list. Unavailable measurements are null or
`unknown`, never invented zero/false. Native valve observations always have null
flow. The reader uses `physical_device_read`; injected test backends use
`simulated_fixture`; imported observations retain their explicit source mode.
Those labels are provenance declarations, not cryptographic authenticity.

Collection appends only, deduplicates identical observations and rejects conflicts.
Default limits are 10,000 observations and 8 MiB. Reaching retention limits stops
collection; existing history is not pruned. A collector lock rejects concurrent
writers. An interrupted process may leave its lock: confirm the collector is no
longer running before an owner manually removes that lock, never the observations.

## Optional independent flow evidence

Replay accepts `--flow-input <jsonl> --flow-tolerance-l-min <configured_value>`.
Each record requires device_alias, UTC timestamp, finite nonnegative L/min value
(or null when unavailable), quality, independent source identifier, source_mode,
hydraulic_scope_confirmed and calibration_reference. All values are declarations
that require separate physical verification; a calibration-reference string is
not proof of calibration. Mode, placement, freshness, persistence and settling
must qualify before a discrepancy is proposed. No volume is inferred from valve
duration. No meter hardware is selected or assumed compatible by this contribution.

## Evidence and remaining gaps

| Capability | Before | Implemented evidence | Remaining gap |
|---|---|---|---|
| BLE discovery | Absent | Mock scanner/service/manufacturer filtering | Authorized radio test |
| Status reads | Absent | Installed pinned decoders + mocked GATT | Actual 1889-20 reads |
| Telemetry ingestion | Absent | Schema/append/replay tests | Physical source authenticity |
| Irrigation monitoring | Absent | Normal, duration, stale, disconnect, battery and independent-flow scenarios | Site policy calibration |
| Dashboard | Hotel only | Optional isolated static view, JS renderer test | Authorized physical observation display |
| Water measurement | Absent | Optional independently supplied evidence | Real calibrated sensor |
| Valve actuation | Absent | Intentionally excluded; no-write guard tests | Out of scope |
| Autonomous resolution | Unverified | Remains not_measured | Authenticated target/outcome evidence |

References: [library](https://github.com/elupus/gardena-bluetooth),
[PyPI](https://pypi.org/project/gardena-bluetooth/3.1.0/),
[Bleak macOS](https://bleak.readthedocs.io/en/latest/backends/macos.html),
[manufacturer](https://www.gardena.com/int/products/watering/water-controls/water-control-bluetooth/970481101.html).
