# GARDENA experience: software qualification

## What the software now demonstrates

A contributor can run one offline command and inspect observations, observed
watering spans, qualified findings, exact policy, read-only answers and source
records without the hotel dataset or Bluetooth hardware. Native acquisition
remains explicitly owner-authorized and read-only. This is a software
qualification, not a physical experiment.

| Capability | Implemented | Tested | Physically verified | Remaining limitation |
|---|---|---|---|---|
| Native discovery/selected reads | Yes, PR #6 | Fake transport + pinned decoders | No | Owner-authorized macOS/device session |
| Canonical policy/evidence | Yes, PR #8 | Custom/default limits, stale cutoff, conflicting manifests | Not applicable | Hashes are not authentication |
| Doctor/demo/standalone report | Yes, PR #9 | CLI, packaged fixtures, HTML | Not applicable | Static report, not live control |
| Read-only text/tools | Yes, PR #10 | Python + actual Node handlers; local Safari check | Not applicable | Supported structured intents only |
| Optional voice client | Yes, PR #10 | Opt-in guards and handler output | No external voice session | Agent/provider/browser-origin verification |
| Independent flow contract | Yes, PR #11 | Positive/negative synthetic controls | No | Real calibration, placement and clock evidence |
| Water consumption/leak location | No quantitative volume/location | Denial/unknown behavior | No | Independent measurement; no duration-derived litres |
| Valve actuation | Intentionally absent | Native no-write/authorization controls | No | Separately authorized project, not this integration |
| Autonomous incident resolution | Not established | No operational test | No | Execution and independent outcome evidence |

## Current verification snapshot

Code revision: `de81739edde681f880ad23d8fa51e959d0ff8655` (this document is a
subsequent documentation-only addition). [Exact-code fork CI](https://github.com/RobLe3/Hackathon-HOIV-2026-autonomous-building/actions/runs/43759950305)
passed all jobs. Linux Python 3.11/3.13 ran 100 cases with two optional native
decoder skips; macOS 15 pinned Python 3.12 ran 100 with no skips. CI executes the
actual doctor, demo, strict contract check and consumption-question commands.
These are fork checks, not upstream merge approval or real hardware trials.

Local pinned Python 3.12.8 passes 100 cases, zero skips; ordinary Python 3.11.9
and 3.13.18 pass with the two optional decoder skips. Optional dependencies are
`gardena-bluetooth==3.1.0`, `bleak==3.1.0`, `bleak-retry-connector==4.7.1`; the full
resolved macOS profile remains in `requirements/gardena-macos-py312.txt`.

Compared with native PR #6's 83 cases, 17 were added across the focused
follow-ups: four canonical-assessment, five experience, three interaction,
four flow/recovery and one timestamp case. Counts describe test methods, not
independent physical experiments. The shared timestamp correction is already
present in the separate HA PR #7; it is not a second distinct safety feature.

Compilation and original/holdout audit commands pass (904/1,143 records). Eight
protected historical artifacts match baseline `93ae810` byte-for-byte. A hotel
fixture generated with and without external canonical evidence retains identical
episode data; its GARDENA findings match the exported decisions. A separate local
compatibility worktree combining code `a4be284` with unchanged PR #4 passed 105
pinned cases; PR #4 itself was not rewritten or merged.

A wheel was built with normal isolated build dependencies and its packaged demo
and text answer ran from a target installation outside the source directory.
An initial `--no-build-isolation` attempt lacked setuptools; it was not a runtime
failure. The default application still adds no runtime dependency. The standalone
page was actually opened in Safari; observed spans, synthetic provenance and
policy-linked questions were inspected. Screenshots were captured in the chat;
browser chrome/private local paths were not published to the repository.

## Reproduce from the contributor fork

```sh
git checkout feat/gardena-flow-evidence
python -m unittest discover -s tests -t .
python -m compileall -q building_ops tests
python -m building_ops check decisions.jsonl
python -m building_ops check decisions_holdout.jsonl
python -m building_ops gardena doctor
python -m building_ops gardena demo --out out/gardena-demo
python -m building_ops check out/gardena-demo/decisions.jsonl --strict-safety
python -m building_ops gardena ask --evidence out/gardena-demo/decisions.evidence.json --question "Has watering exceeded its configured duration?"
```

Open `out/gardena-demo/experience.html`. The demo contains 19 synthetic controller
observations plus eight separate synthetic flow assertions and produces five
strict shadow findings. Normal watering and unqualified flow do not produce leak
claims. Recovery does not reconstruct the lost interval. Observed open spans are
bounded report intervals, not continuous physical sampling.

Fixture/decision/assessment bytes are repeatable at the same code revision. The
HTML records actual generation time and is therefore not byte-identical across
wall-clock renders; fixed-clock rendering tests cover deterministic layout/data.
Evidence outputs refuse existing destinations. Legacy flow records stay auditable
but cannot silently acquire version-2 qualification; incompatible manifests must
be replayed with complete policy and inputs.

## SHA-256: observed release-demo run at the code revision above

| Artifact | SHA-256 |
|---|---|
| Controller input `demo.jsonl` | `8253f0b838bcd9177541c75bd03fc58c5a0a523b12530b212a380ff0356d571d` |
| Separate flow `flow.jsonl` | `dab5ea2352ea756825c21bd3b403294d6afc2601956fbf699a30fd48d6ebd05a` |
| `decisions.jsonl` | `3dc9e9388a881c74d53e09e09859545c35383349a336fd6197fe30750a9d2d9a` |
| `decisions.evidence.json` | `37bc0741264f91b1762c02aef4b286afef398472d5bf398536fddb64451354cb` |
| `experience.html` | `ed8e690f72b083dbe7f747412485a45c0e67e5b444b8d87012d393de3dd002d3` |

The manifest hash includes code revision; another revision changes it. The HTML
hash describes the actual render at `2026-11-15T20:46:33.677968Z`, not a universal
expected hash. The fixture cutoff is `2026-11-15T12:02:00Z`, explicitly separate
from generation time.

## Review progression and outstanding gates

[Policy #8](https://github.com/ADH-GH/Hackathon-HOIV-2026-autonomous-building/pull/8)
→ [offline experience #9](https://github.com/ADH-GH/Hackathon-HOIV-2026-autonomous-building/pull/9)
→ [read-only interaction #10](https://github.com/ADH-GH/Hackathon-HOIV-2026-autonomous-building/pull/10)
→ [qualified flow/final delivery #11](https://github.com/ADH-GH/Hackathon-HOIV-2026-autonomous-building/pull/11).
The chain builds on native #6 and safety #2; all prerequisites remain explicitly
stacked. Existing #4 and HA #7 are not rewritten. Issue #5 remains the umbrella;
no duplicate issue or merge/reviewer request is needed to record software delivery.

Read [native setup](../integrations/gardena-bluetooth.md),
[flow qualification](../integrations/gardena-flow-evidence.md) and
[hardware acceptance](../integrations/gardena-hardware-qualification.md) before any
physical experiment. CoreBluetooth uses private host-local UUIDs; app permissions,
model uncertainty and pairing conflicts are stop conditions, not permission to
reset or displace another controller. No live system was accessed here.

**Software journey: complete within synthetic/mocked scope. Hardware: NOT_TESTED.
Physical flow: NOT_TESTED. External voice session: NOT_TESTED. Operational
resolution: not measured.** Maintainer review/merge and separately owner-authorized
qualification remain external gates; none is inferred from successful CI.
