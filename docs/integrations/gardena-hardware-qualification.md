# GARDENA hardware acceptance — outstanding

Current outcome: **NOT_TESTED**. No real controller was scanned, connected or
operated during this contribution. Mocked BLE tests verify software paths, not
physical compatibility. Do not edit that conclusion without actual evidence.

Use an isolated supported macOS Python 3.12+ environment and the pinned dependency
file in [the setup guide](gardena-bluetooth.md). CoreBluetooth uses a host-local
UUID, not a public MAC address. Never publish that UUID. OS/runtime Bluetooth
permission is separate from explicit owner authorization. A service-filtered scan
supports the documented older macOS scan restriction; no explicit pair/reset or
clock synchronization is permitted by this native adapter.

## Acceptance gates

1. **H1 — permission:** obtain the actual owner's explicit approval for the exact
   selected controller, bounded duration and status reads. Ownership/discoverability
   alone is not authorization. Record permission privately, not in public fixtures.
2. **H2 — discovery:** only then run `gardena scan --authorize-hardware --seconds 12`.
   Reveal IDs locally only when needed for selection. Record product classification
   and whether exact 1889-20 identity is established. Stop on uncertainty.
3. **H3 — connection:** select one authorized UUID. Read model and available status
   characteristics; preserve missing fields. Stop if pairing/reset/app displacement,
   an unexpected write or unsupported model would be required.
4. **H4 — observation:** collect a small bounded `observe --samples` session.
   Record supported/missing fields, UTC timestamps, errors and cleanup. The adapter
   cannot activate watering. Ctrl-C cancels and runs disconnect cleanup.
5. **H5 — application:** replay the acquired JSONL, generate canonical evidence,
   standalone report and `gardena ask` responses. Keep private raw captures out of
   published GitHub Pages. Preserve original bytes and hashes before redaction.
6. **H6 — optional transition:** only with separate owner permission, observe an
   owner-initiated ordinary watering session. PLATO does not open/close the valve.
   Never create uncontrolled discharge merely to provoke a finding.
7. **H7 — evidence:** document actual observations, sample count, software revision,
   dependency versions, timestamps, hashes, missing coverage and remaining gaps.

Classify the result narrowly: `NOT_TESTED`, `BLOCKED_BY_AUTHORIZATION`,
`DEVICE_NOT_FOUND`, `CONNECTION_FAILED`, `PARTIAL_TELEMETRY`,
`READ_ONLY_OBSERVATION_VERIFIED`, or `PHYSICAL_FLOW_VERIFIED`. The last requires a
separate independently calibrated meter and qualified timing/hydraulic scope;
it cannot follow from a successful BLE read alone. A source_mode declaration is
not physical proof. Store an authorized test report separately; replay itself
continues to report unverified provenance rather than automatically upgrading it.

Software-complete, hardware-qualified, flow-qualified and operationally verified
are distinct states. Even successful hardware/flow testing does not establish
autonomous incident resolution, authenticated approval or production readiness.
An external voice session likewise needs its own opt-in test; passing client tool
handlers does not certify provider-spoken answers.
