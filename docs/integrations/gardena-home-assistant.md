# GARDENA through Home Assistant: cached, read-only shadow telemetry

This optional Python-standard-library adapter reads Home Assistant REST states.
It does not initialize Bluetooth, call services, or control a valve. It keeps
external observations separate from the fictional hotel dataset and its historic
autonomy denominator. Development used synthetic files and loopback HTTP only.

## What “read-only” covers

PLATO issues GET requests to `/api/states` (or, through the small Reader API,
`/api/states/<entity>`). Home Assistant documents these state reads and bearer
authentication in its [REST API reference](https://contributors.home-assistant.io/core/internals/rest-api/).
The adapter rejects redirects and non-HTTPS external URLs, uses normal TLS
verification, and does not send credentials to another origin. A token belongs in
an environment variable, not a mapping, command argument, output file or commit.
Loopback tests do not inherit ambient `HA_TOKEN` unless explicitly requested.

**The bridge is not an end-to-end no-write guarantee.** Home Assistant's GARDENA
[coordinator setup](https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/gardena_bluetooth/coordinator.py)
calls device timestamp synchronization. PLATO does not invoke setup, but an owner
must assess that separate bridge behavior before enabling it. The native
[BLE adapter](gardena-bluetooth.md) has a different, strict GATT no-write boundary.

Home Assistant lists the 01889-20 as supported, but documents pairing/reset and
Android-app lockout limitations in its [GARDENA integration guide](https://www.home-assistant.io/integrations/gardena_bluetooth/).
Stop if access would require an unapproved reset, reconfiguration, pairing change
or displacing an owner's app. No such operations are implemented here.

## Reproduce without a device or network

From the repository root, in a new output directory:

```sh
python -m building_ops gardena-ha check-mapping --mapping tests/fixtures/gardena_ha/mapping.json
python -m building_ops gardena-ha replay --input tests/fixtures/gardena_ha/rate.jsonl --mapping tests/fixtures/gardena_ha/mapping.json --synthetic --out out/ha-demo
python -m building_ops check out/ha-demo/decisions.jsonl --strict-safety
python -m unittest tests.test_gardena_ha_complete tests.test_gardena -v
```

Five synthetic snapshots contain a closed valve and independently mapped flow
of 2 L/min. The default policy waits 30 seconds after a state change and requires
60 seconds of advancing source reports before proposing one discrepancy finding.
It is not a leak-location conclusion. `cumulative.jsonl` supplies the same rate
as counter deltas; change `flow.kind` to `cumulative` in a **copy** of the mapping
to replay it. The initial counter observation establishes a baseline, not zero
flow. Tests also exercise open/zero-flow, lost/recovered connection, stale data,
counter resets, scope isolation, malformed imports and GET-only loopback reads.

Outputs are normalized `observations.jsonl`, strict `decisions.jsonl`,
`evidence.json`, `evidence.md` and `frames.private.jsonl`. Existing evidence
directories are not overwritten. The private frame file retains configured
entity identifiers; mappings and source paths can also identify a property.
**Do not publish the directory wholesale.** Public observations and decision
evidence hash entity identifiers, but hashing is not anonymization against a
known-identifier dictionary. Review aliases, mappings and paths before sharing.

## Configure explicit mappings

Generate a local skeleton; it does not discover or select a device:

```sh
python -m building_ops gardena-ha mapping-template --asset GARDEN_A --valve-entity valve.owner_selected --out out/ha-mapping.json
```

The version-1 mapping supports one to ten uniquely aliased assets. Each has an
explicit `valve_state` binding plus optional `active_watering`,
`remaining_open_seconds` and `battery_percent` entities. Switch/valve states are
decoded only as documented in `normalize()`; unsupported transitional states
remain unknown. Diagnostic entities need not exist on every firmware.
Model identity is `unknown` or `owner_declared`, never verified by entity names.

An optional, separate `flow` sensor can report a rate (`L/min`, `L/h`, `L/s`,
`m³/h`, `m3/h`) or cumulative volume (`L`, `m³`, `m3`, with total/total_increasing
state semantics). Rate becomes L/min; volume becomes litres. Counter differences
are interval-average rates, not instantaneous readings. Resets, missing values,
duplicate timestamps and overlong intervals never become invented zeroes.

Discrepancy checks require all three declarations: `independent: true`,
`hydraulic_scope_confirmed: true`, and a nonempty `calibration_reference`.
Confirm sensor placement and calibration outside PLATO. These declarations are
not authenticated measurement evidence. Without them, telemetry and battery/data
quality findings still work, but valve/flow conclusions are disabled. Valve-open
time is never converted to measured litres.

All policy keys in the fixture are explicit and configurable. Freshness, skew,
maximum gap, persistence, settling, flow tolerance and low-battery thresholds are
monitoring assumptions, not manufacturer fault limits. Set them for the actual
sensor reporting interval and plumbing; do not tune hotel benchmark thresholds.

## Authorized live demonstration — not performed

Only after explicit owner authorization, with an already approved HA bridge:

```sh
# Set HA_TOKEN privately in your shell; do not paste it into commands or reports.
python -m building_ops gardena-ha discover --url https://YOUR_APPROVED_HA --authorize-live --show-entity-ids
python -m building_ops gardena-ha collect --url https://YOUR_APPROVED_HA --authorize-live --mapping out/ha-mapping.json --samples 5 --interval-seconds 60 --out out/ha-private
```

Discovery lists supported **candidate** entities; it does not prove device model,
GARDENA ownership or hydraulic scope. Raw entity IDs require the explicit flag.
An operator selects and checks mappings. No automatic device binding occurs.
Do not execute these examples merely to obtain a green test result.

Collection makes one bounded state-list GET per snapshot, at most ten snapshots,
1–60 seconds apart. Each GET has at most three attempts, a configurable socket
timeout up to ten seconds, a one-MiB response bound and a response-read deadline.
OS scheduling/DNS are not hard real-time guarantees. Connection failure produces
an unavailable frame; the next scheduled snapshot retries independently. This is
a finite collector, not a daemon, persistent reconnect service or live dashboard.
Transport failures yield CLI exit 1 while preserving evidence for inspection.

## Schema and qualification

Each normalized version-1 metric record includes source `gardena_ha`, alias,
receipt UTC, HA `last_reported` as `source_timestamp`, original last-change/update
metadata, metric, nullable value, `quality`, payload hash and provenance. Public
output replaces entity ID with its hash. Quality is `valid`, `unknown`, `stale` or
`invalid`; missing/failed reads stay nullable. Freshness uses **last_reported**,
not last_updated: no report timestamp means unknown, not freshly measured.
HA report time is not independently verified physical-sampling time. Cached
unchanged source reports do not accumulate discrepancy persistence.

Snapshots apply atomically per asset and declared environment. Freshness/skew,
state settling, advancing source time and consecutive coverage qualify a pair.
Cumulative intervals must start after settling; an interval spanning a valve
transition cannot establish a current-state discrepancy. Gaps reset persistence.

Evidence qualification is `failed` if no valid valve report exists, `partial` if
some normalized measurements are unusable, otherwise `complete`. This measures
report completeness only; the first cumulative baseline therefore makes its
report partial. Sources and hashes, code revision and implementation hashes are
recorded. `physical_state_verified` remains false and real-world resolution
remains `not_measured`. Synthetic replay never establishes live integration.
