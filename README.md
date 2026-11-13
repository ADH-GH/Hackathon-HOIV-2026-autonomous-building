# Autonomous building operations for PLATO-40

Team Alf & Friends · proximata Hackathon '26 · Rhomberg track
"PLATO · CLARA Future — The Autonomous Building".

PLATO-40 is a fictional 40-room self-check-in hotel. All data is synthetic.
Nothing here is a statement about real PLATO buildings or about what CLARA does today.

## Status

**Work in progress.** The three mandatory scenarios S01 to S03 are implemented and tested.
Level 2 beyond the surge days, Level 3 (`insights.md`) and the dashboard are not done yet.

| Part | State |
|---|---|
| Single-command pipeline, output contract, autonomy rules | working, tested |
| Dataset loader (blank = missing, UTC, time of availability) | working, tested; columns from the dataset README (PLATO-40 v2) |
| Mock executor with simulated action trail | working, tested |
| Contract check for a decisions file (`check`) | working, tested |
| Decision viewer, one offline HTML file (`report`) | working on hand-made sample decisions only |
| Signal helpers: cumulative meters, robust baseline, episode grouping, local time | working, tested; not used by a detector yet |
| S02 water leak (burst, quiet, hidden) | implemented, tested, run on quickstart and dev |
| S01 turnaround (requests, day capacity, waiting guests; covers surge days) | implemented, tested, run on quickstart and dev |
| S03 energy vs comfort (heat pump degradation, cold-snap pre-heating, cold-room reports) | implemented, tested, run on quickstart and dev |
| S04 maintenance cascade, logistics, energy optimisation beyond pre-heating | not started |
| Level 3 (`insights.md`), dashboard per scenario | not started |

## Run

Python 3.11 or newer. No dependencies.

```bash
python -m building_ops run <data_dir> --out decisions.jsonl
```

That one command takes the data directory and writes `decisions.jsonl`. For the holdout:

```bash
python -m building_ops run <holdout_dir> --out decisions_holdout.jsonl
```

Other commands:

```bash
python -m building_ops inspect <data_dir>                 # files, columns, row counts, blank shares
python -m building_ops run <data_dir> --actions out/actions.jsonl   # also the simulated action trail
python -m building_ops check decisions.jsonl              # contract and autonomy rules; exit code 1 on errors
python -m building_ops report decisions.jsonl --actions out/actions.jsonl --out out/report.html
python -m building_ops sample                             # viewer on invented sample decisions, labelled as sample
python -m unittest discover -s tests -t .                 # tests
```

## Data

Not committed. Put the quickstart, dev and holdout runs in separate directories under
`data/`; they are independent runs and must not be concatenated.

Attribution: "PLATO-40 synthetic dataset, proximata Hackathon '26 · Rhomberg track" (CC BY 4.0).

## Architecture

```
building_ops/
  dataset.py      loads one data directory; blank cells are None; known_at() hides the future
  decisions.py    the Decision record, the output contract, the autonomy rules, de-duplication
  detectors/      one module per scenario class; each yields Decisions with evidence
  occupancy.py    who occupies a room at a point in time, from the lifecycle events
  pipeline.py     runs the detectors, de-duplicates, writes decisions.jsonl
  executor.py     mock executor: simulated action trail, approvals are queued not run
  signals.py      meter differences, robust baseline, episode grouping, Europe/Vienna time
  check.py        checks a decisions file against the contract and the autonomy rules
  report.py       decision viewer as one self-contained HTML file
  sample.py       invented sample decisions for the viewer; never a result
```

Rules that are enforced in one place, so a detector cannot break them:

- **Autonomy** (`decisions.py`): the oversight level follows from the action. A detector
  can ask for more oversight, never for less. Technician, contractor, blocking or moving a
  room need human approval; entering an occupied room, a water shutoff and safety-relevant
  interventions also need guest consent.
- **One alert per incident** (`decisions.py`): decisions are de-duplicated per episode and action.
- **Missing is not zero** (`dataset.py`): blank cells are `None`.
- **Time of availability** (`dataset.py`): `known_at(table, t)` returns only rows known at `t`.
  It refuses to run until the availability column is configured from the dataset README.
- **Simulated is labelled** (`executor.py`): every executed action carries `simulated: true`.

## Water leak thresholds

Set on the dev year (`python -m building_ops run data/dev`), from the meters alone.

| Pattern | Rule | Longest benign stretch in dev | Leaks in dev |
|---|---|---|---|
| Burst | 8 consecutive 15-min intervals with at least 8 L each (2 h) | 5 intervals | 97 intervals each |
| Quiet | 20 consecutive intervals with flow above zero (5 h) | 13 intervals | 47 to 773 intervals |
| Hidden | median night gap (01:00-05:00 local) main meter minus sum of rooms at least 2 L per 15 min | 0.1 L | about 7 L |

Result on dev: 5 incidents flagged (bursts in R201 and R401, quiet leaks in R403 and R208, one
on the main meter), each matching a corrective work order written later in `work_orders.csv`;
no leak alert without one. Quickstart: R104 and R305, both matching. Work orders are used
only to check the result, never as input. A meter that reads backwards repeatedly is reported
once as `data_quality` and excluded; a counter restart is treated as a meter exchange.

## Turnaround (S01)

Three triggers: an early check-in request, the start of a day whose turnovers exceed what the
cleaners on duty can finish by 15:00 (6 rooms per cleaner), and a guest standing at a room
that is not ready. Capacity counts only shifts with status `scheduled`, as known at the
decision time; an absence counts from `status_known_utc`. A room is released only when a
human cleaner reports it clean, never on a robot's work.

Checked against the replay (the replay did not follow our plan, so this is a consistency
check, not a measured effect): of 349 early check-in answers on dev, 341 gave a time at
which the room really was clean, 8 were too early by 15 to 90 minutes, all on days when
guests ended up waiting. Day plans were raised on 8 days; 5 of them are among the 16 days
on which a guest waited, and they cover 13 of the 24 waiting guests. The other 11 waiting
days have one guest each who arrived before a single room was cleaned.

## Energy vs comfort (S03)

The heat pump's COP follows the outdoor temperature: `COP = 2.796 + 0.0761 * T` (fitted on
19,486 running intervals of dev, heating season below 15 °C). The 6-hour median stays within
3 % of that on normal days and drops to about -15.5 % before each of the heat pump services
in `work_orders.csv`. The rule is: median gap of -10 % or worse with at least 16 valid
readings in 6 hours. Dev: 2 episodes flagged, both followed by a "refrigerant leak" service
54 and 59 hours later, none without one. Quickstart, an independent run that the model was
not fitted on: 1 flagged, service 62 hours later.

Cold-snap pre-heating uses the newest forecast issued at the decision time (minimum of
-8 °C or colder) and only prices already published. Savings are never claimed.

## Local time

Operations follow Europe/Vienna. All times in reasons, messages and the viewer are Vienna
wall-clock time with the zone name (CET in winter, CEST in summer); `timestamp_utc` and the
evidence references stay in UTC as the contract requires. Shift starts, check-in and the
on-call window are computed from local wall-clock times, so they move with daylight saving.

## Assumptions and limits

- `order_service` is treated as autonomous only for `waste_pickup` and `restock`; any other
  kind needs human approval.
- Cancelled bookings carry no cancellation time; they are left out entirely, which uses one
  piece of information that may not have been known at decision time.
- `release_room` is only emitted on a `cleaning_completed` event by a human resource.
- Guest messages are templates in de, en, it, fr, es, nl; no message is sent.
- Extra field `proposed_message` / `message_language` on `notify_guest`, and `stage` to tell
  the steps of one episode apart.
- No effect of any action is measured. The data is a replay.

## Holdout protocol

1. Tag the code `pre-holdout` before the holdout dataset is released.
2. Run the pipeline unchanged on the holdout and commit `decisions_holdout.jsonl`.
3. Any change after the tag is listed here with its reason.

Changes after `pre-holdout`: none (tag not set yet).

## Licence

MIT, see [LICENSE](LICENSE).
