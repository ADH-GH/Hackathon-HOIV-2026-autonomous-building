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

## Root Cause
The existing file-based detector and dashboard paths do not collect or qualify
external Bluetooth observations. No new persistent backend is necessary.

## Change
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

## Claim Alignment
Adds a reproducible observation-to-finding-to-evidence path, not real autonomous
building operation or demonstrated physical-device connectivity.

## Remaining Limitations
Hardware pairing, permissions, actual supported characteristics, physical model
identity and live measurements await separate owner-authorized verification.
Real flow needs an independent calibrated sensor. No controls, schedules, clock,
firmware or pairing settings are changed; operational outcomes stay not_measured.

## Observed local results

On Python 3.12.8, the native branch runs 83 unittest cases. The default environment
passes with two optional-decoder tests explicitly skipped; the installed pinned
macOS environment passes all 83 without skips. Node v20.20.2 executed the actual
static view renderer and checked generated script syntax; Node 24 is configured
for CI, not claimed locally tested. Compileall and historical file comparisons
pass. Fixture replay emits one prolonged-watering decision that passes strict
safety checking. Workflow files were prepared locally; remote CI was not run.
No physical scan, connection, pairing change or actuator command was performed.

## Final integrated chain control

The current engineering stack strengthens the existing mock-backend positive
case: discovery/explicit selection, status reads, append-only observations, actual
replay CLI, low-battery finding, strict decision CLI and simulation evidence are
exercised as one chain. The fake transport's write counter remains zero and its
private mock identifier never enters observations/decisions. This expands an
existing case without inflating the test count. It does not claim physical device
communication or modify the independently tested 83-case native branch head.
