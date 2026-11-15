# Home Assistant GARDENA contribution: evidence and limits

The native BLE path provides a deliberately direct observation boundary. This
second route is for owners who already operate an approved Home Assistant bridge:
the same irrigation questions can be evaluated from cached REST entity reports,
without adding another Bluetooth session or changing the hotel replay pipeline.

## Review boundary

This branch depends on native PR #6 and its safety prerequisite #2. Until those
are accepted, the main-based diff includes those unchanged prerequisites. Review
the HA feature against native head `466f2bba7f9c6d47a91c8cf72503ecef5b487f12`.
No SenML adapter, optimizer changes or unrelated engineering stack is included.
The only shared behavioral prerequisite added here preserves fractional decision
timestamps rather than truncating them to an earlier second.

## Reproduce

```sh
python -m unittest discover -s tests -t .
python -m compileall -q building_ops tests
python -m tests.qualify_ha
python -m building_ops check decisions.jsonl
python -m building_ops check decisions_holdout.jsonl
```

Fresh local verification: 100 cases pass on Python 3.12.8 with the optional pinned
BLE dependencies, zero skips. Python 3.11.9 and 3.13.13 pass with two explicitly
optional native decoder cases skipped. Against the native branch's 83 cases,
this adds 11 HA cases, five transport/artifact cases and one timestamp case.
Counts are test methods, not independent hardware experiments.

The CLI qualifier replays both rate and cumulative synthetic fixtures twice,
compares all output bytes at identical source paths, requires a positive finding,
and validates the resulting decisions with strict safety. It accesses no network.
Transport tests use injected responses or literal loopback HTTP, including a
successful GET, redirects denied, malformed/oversized JSON, invalid credentials,
connection loss/recovery and bounded retries. An atomic replacement failure
preserves previous file bytes; this is not a multi-file transaction guarantee.

Historical audits accept 904 original and 1,143 holdout decisions in audit mode;
missing historical risk context is not execution authorization. Eight historical
artifacts (both decision files, both insight files, published dashboard/holdout
HTML and API HTML/JSON) match reference `93ae810` byte-for-byte.

| Capability | Before this addition | Evidence now | Remaining gap |
|---|---|---|---|
| HA cached report ingestion | No HA CLI | Explicit mapping/discovery, finite GET collection and replay | Authorized live bridge not tested |
| Independent rate/counter input | No HA flow qualification | Synthetic conversion, resets, gaps and scoped pairing tests | Real sensor calibration and placement |
| Irrigation findings | Native observation route | HA stale/loss/battery and persistent valve/flow discrepancies | No exact leak localization |
| Traceable decisions | Native strict contract | Deterministic qualified shadow decisions and JSON/Markdown reports | No authenticated operator or real action outcome |
| Hardware control | Excluded | PLATO issues only GET requests | HA bridge setup may write device clock |

[Setup, schema and demonstration instructions](gardena-home-assistant.md) describe
what to configure and when to stop. Reports distinguish synthetic/imported/HA
observations; `physical_state_verified` remains false. A configured independent
flow declaration is not proof of calibrated measurement. Valve status alone
never establishes litres, a leak, or successful operational resolution.

This contribution makes the next physical experiment reproducible; it does not
claim that experiment has already taken place. Neither manufacturer endorsement
nor an award claim is implied.
