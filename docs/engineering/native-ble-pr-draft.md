# feat: integrate GARDENA 1889-20 via native macOS Bluetooth telemetry

Local review draft only. No PR number is reserved or assigned by this document.
Base: aa2d3ff (existing unmerged safety PR #2). Review this branch against that
base, not as if its safety dependency were already merged upstream. PRs #2/#4
are unchanged. No remote publication or hardware test is authorized here.

## Problem
The historical prototype has no direct, isolated native-device observation path.
Valve status must not be mistaken for water consumption or actuator success.

## Evidence
Five reduced synthetic fixtures cover normal, closed, disconnected, stale and
prolonged observations. Fake scanner and GATT backends exercise the real adapter
interface without accessing macOS Bluetooth. A separate installed-profile test
runs actual gardena-bluetooth 3.1.0 decoders and invokes write guards against mocks.

## Root cause / capability gap
The existing file-based detector and dashboard paths do not collect or qualify
external Bluetooth observations. No new persistent backend is necessary.

## Implementation
Optional lazy BLE imports, explicitly authorized/selected bounded reads, simple
characteristic whitelist, denied writes, versioned private-ID-free observations,
append-only bounded intake, monitoring proposals and an isolated static dashboard
view. Physical, fixture and imported modes remain separate. Shared safety contract
and risk context are retained; no executor is called by collection/replay.

## Verification
Run `python -m unittest discover -s tests -t .`, then repeat with the isolated
pinned BLE environment. Run the documented synthetic replay and strict check.
Existing hotel tests and historical byte comparisons must pass. Installation and
recorded test counts are documented in the integration evidence, not hardware
certification. No current annual dataset was available or regenerated.

## Claim alignment
Adds a reproducible observation-to-finding-to-evidence path, not real autonomous
building operation or demonstrated physical-device connectivity.

## Remaining limitations
Hardware pairing, permissions, actual supported characteristics, physical model
identity and live measurements await separate owner-authorized verification.
Real flow needs an independent calibrated sensor. No controls, schedules, clock,
firmware or pairing settings are changed; operational outcomes stay not_measured.
