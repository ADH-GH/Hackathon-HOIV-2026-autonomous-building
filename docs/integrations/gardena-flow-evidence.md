# Independent flow evidence: a separate measurement contract

A BLE valve report is not a water meter. Version-2 flow records are separate
JSONL assertions, never inserted into BLE measurements or the hotel dataset.
Each record contains these fields (values below describe a synthetic fixture):

```json
{
  "schema_version": 2,
  "device_alias": "Flow_discrepancy",
  "timestamp_utc": "2026-11-15T12:00:00Z",
  "flow_liters_per_minute": 2,
  "units": "L/min",
  "quality": "VALID",
  "source": "synthetic_independent_meter",
  "source_mode": "simulated_fixture",
  "independent": true,
  "hydraulic_scope_confirmed": true,
  "hydraulic_zone": "fixture_zone",
  "calibration_reference": "synthetic_fixture_only",
  "time_sync_reference": "synthetic_shared_fixture_clock",
  "timestamp_uncertainty_seconds": 0
}
```

The explicit policy mapping selects which controller alias belongs to which
hydraulic zone. Supply a JSON object such as
`{"Flow_discrepancy":"fixture_zone"}` through `gardena replay --flow-map`.
The separate meter file goes through `--flow-input`; configure
`--flow-tolerance-l-min` explicitly. No arbitrary unit conversion is inferred:
this profile accepts L/min only; normalize other sources before import and keep
conversion provenance. Volume/consumption integration is not implemented.

A discrepancy needs version 2, independent=true, valid nonnegative flow,
calibration and clock references, confirmed hydraulic scope and matching configured
zone. Sample age plus declared timing uncertainty must fit the policy skew limit.
Fresh successive samples must persist after settling. Cached samples, future-only
samples, conflicting identities, gaps, wrong zones and missing values cannot
establish persistent flow. Zero is a real supplied value, not missing data.

| Observation pair | Bounded interpretation |
|---|---|
| Open, no qualified flow | Reported valve operation; water flow unverified |
| Closed, persistent qualified positive flow | Potential flow/state discrepancy; inspect placement/bypass/drainage |
| Open, persistent qualified zero flow | Possible supply, obstruction, valve or sensor issue |
| Unknown valve or unavailable flow | No reliable pair conclusion |

Legacy unversioned records remain readable/auditable but no longer establish
qualified discrepancies. Replay with version-2 records and an explicit relationship
map. Do not merely relabel old data: obtain the missing calibration, timing and
scope evidence. Earlier manifests missing the new policy field fail compatibility
validation and must be replayed, not silently given authority.

Declarations and references are not cryptographic authentication or proof of
calibration. The demo's references are explicitly synthetic. Physical flow remains
NOT_TESTED, no exact leak location is asserted and no litres are invented from
watering duration. Owner-authorized sensor validation is a separate milestone.
