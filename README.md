# Autonomous building operations for PLATO-40

Team Alf & Friends · proximata Hackathon '26 · Rhomberg track
"PLATO · CLARA Future — The Autonomous Building".

**Live dashboard:** https://adh-gh.github.io/Hackathon-HOIV-2026-autonomous-building/ (the file `docs/index.html`, written by the dashboard command below from `decisions.jsonl` with `--web-fonts` and `--voice-agent`; it loads the fonts, and the ElevenLabs client only when "Voice briefing" is clicked).

PLATO-40 is a fictional 40-room self-check-in hotel. All data is synthetic.
Nothing here is a statement about real PLATO buildings or about what CLARA does today.

## Status

**Status.** S01 to S05 and both unnumbered Level 2 items (energy optimisation, logistics) are implemented and tested, Level 3 (`insights.md`) is computed
from the dev year, and the dashboard shows every case. Not done: robot transport of
floor waste bins.

| Part | State |
|---|---|
| Single-command pipeline, output contract, autonomy rules | working, tested |
| Dataset loader (blank = missing, UTC, time of availability) | working, tested; columns from the dataset README (PLATO-40 v2) |
| Mock executor with simulated action trail | working, tested |
| Contract check for a decisions file (`check`) | working, tested |
| Decision viewer, one offline HTML file (`report`) | working on hand-made sample decisions only |
| Signal helpers: cumulative meters, robust baseline, episode grouping, local time | working, tested; not used by a detector yet |
| S02 water leak (burst, quiet, hidden) | implemented, tested, run on quickstart and dev |
| S01 turnaround (early check-in requests, waiting guests, day capacity) | implemented, tested, run on quickstart and dev |
| S05 event weekend (full house with cleaners short: plan the day before from the bookings, again on the morning) | implemented, tested, run on quickstart and dev |
| S03 energy vs comfort (heat pump degradation, cold-snap pre-heating, cold-room reports) | implemented, tested, run on quickstart and dev |
| S04 maintenance cascade (fast filter loading, sensor gap, technician away) | implemented, tested, run on quickstart and dev |
| Logistics: extra waste pickup and vending restock ordered ahead from the bookings | implemented, tested, run on quickstart and dev |
| Level 2 energy optimisation: a day-ahead battery plan from published prices and a persistence forecast | implemented, tested, run on quickstart and dev |
| Robot transport of floor bins | not started |
| Dashboard: every case with its evidence, decisions and autonomy level (`dashboard`) | working; checked by screenshot on dev |
| Level 3: `insights.md`, `insights.jsonl` (`insights`) | computed from dev: 13 recommendations with numbers, evidence, uncertainty; target architecture |
| Approval queue in the dashboard (approve, reject, guest consent, exportable log) | working; effect is simulated |
| Voice control of the dashboard through an ElevenLabs agent (`--voice-agent`) | tool handlers verified by self-test; spoken conversation untested |

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
python -m building_ops dashboard <data_dir> decisions.jsonl --actions out/actions.jsonl --out out/dashboard.html
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
  dashboard.py    dashboard: per case the raw-data slice behind the decision, the decision chain, the later work order
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

## Event weekend (S05)

A surge day is one with at least 18 booked arrivals and more same-day turnovers than the
scheduled cleaners can finish by 15:00. It is planned twice. At 07:00 the day before, from the
bookings and the roster as known then: flag the shortfall, ask for approval to arrange cover (an
extra shift if someone can take it, otherwise the on-call housekeeper on notice), and tell the
arriving guests that an early check-in cannot be promised. At 07:00 on the day, and again when an
absence becomes known: the cleaning order, robots ahead, on-call for the rooms beyond capacity.
Cover always needs approval; no capacity is assumed that the roster does not show. Dev: 7 surge
days flagged, 3 of them already the day before; the replay shows 13 of the year's 24 waiting guests
on those days. Dashboard tab "S05 Event weekend".

The tabs follow the brief: S01 to S05 are its five numbered scenarios; energy optimisation and
logistics are its two unnumbered Level 2 items and are labelled that way, not as S06 or S07.

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

## Dashboard

`python -m building_ops dashboard data/dev decisions.jsonl --out docs/index.html --web-fonts --voice-agent <agent id>` writes the hosted copy.
`python -m building_ops dashboard data/dev decisions.jsonl --actions out/actions.jsonl` writes one
HTML file that opens from disk and makes no network request. Overview, one tab per scenario and
the full decision log. Each case shows the slice of raw data the decision rests on (meter flow,
COP against the model, the forecast that was issued, the room's readings or its events of the
day), the decisions in order with autonomy level, evidence and verification, and the mock
executor's status. Where the dataset has a later corrective work order it is shown as a check
and labelled as such; detectors never read it. Deep links work: `dashboard.html#S02` or
`#S02:<episode id>`. Dark by default with a light theme toggle. Colours and fonts follow the
showcase page; without `--web-fonts` the fonts fall back to the system's and the page makes no
network request.

## Maintenance cascade (S04)

Only readings taken at normal fan power are compared; the planned reduced operation at night
lowers airflow and filter pressure together and is neither a fault nor a recovery. Steps:
the 6-hour median pressure rises 15 Pa or more in 24 hours (normal loading is about 1.5 Pa
per day); the pressure sensor is silent for 6 hours, after which fan power and airflow are
read instead; the fan reaches its limit of 5.3 kW or airflow falls below 95 % of nominal.
Service goes to the technician only if a shift within 48 hours is known as worked, otherwise
to a contractor, always with approval. Dev: both cascades flagged 11 and 9 days before the
unplanned filter change in `work_orders.csv`, two harmless sensor gaps reported as low-priority
data quality, nothing else. Quickstart: one cascade, flagged 8 days before the change.

## Energy optimisation (Level 2)

When a day's prices are published (13:00 Vienna time the day before), the battery is planned for
that day by dynamic programming over its state of charge: charge from PV surplus and in the
cheapest hours, discharge in the most expensive ones, within 40 kW and 10 to 95 kWh, with the
round-trip efficiency split between charging and discharging. The forecast is the load and PV of
the last complete day. Electricity fed into the grid is valued at zero; that is our assumption,
the dataset does not say. The plan moves electricity in time only and never touches a setpoint.
A plan is logged as a decision when it saves at least 10 EUR against no battery on the forecast.

Dev, simulated, each day's plan run against the load and PV measured that day (361 days):
28,807 EUR grid cost without a battery, 27,038 EUR in the replay with its own battery control,
26,653 EUR with our plans, 25,907 EUR with perfect foresight. That is 1.4 % below the replay, and
on 130 of the 361 days our plan was the more expensive one, because yesterday's sun is a weak
forecast. No saving was measured: the replay does not react to a plan. Dashboard tab
"Level 2 · Energy".

## Logistics (Level 2)

Consumption is estimated per guest over the past 72 hours and projected forward over the guests
booked for each coming hour, as known at that moment: guests in the house for the vending
machine, departing guests for the waste container, which fills in one step per day after the
check-outs. An extra service is ordered when the limit would be reached more than 8 hours before
the regular visit and the extra visit (24 h lead) still comes at least 6 hours before it. For
the container the projection must overshoot by 15 points, because an extra pickup costs money
and the daily step varies; that margin was chosen on the dev year.

Dev, against the outage events in the replay: the vending machine ran dry 20 times; 15 of those
had an order at least 24 hours earlier, and 16 of the 20 orders were followed by a real
stock-out. The container was full 3 times; all 3 had an order at least 24 hours earlier, 5 further
orders were not followed by an overflow (two of them reached 87 and 90 %). Quickstart: no
outage, no order. Robot transport of floor bins is not planned: no floor bin exceeded 59 %.

## Voice control (optional)

`python -m building_ops dashboard ... --voice-agent <agent id>` adds a "Voice briefing" button to the
header. A click starts a call with an ElevenLabs agent, which first reports the status, the critical
cases and what waits for approval, and then takes questions. It answers status questions, opens views and cases
and reads the approval queue; it approves or rejects only after it has read the item back and
heard a clear yes. Its ten tools are client tools that run in the page
(`voice/create_agent.py` holds the agent configuration), so there is no server. The rules stay in
the page's code, not in the prompt: an item that needs guest consent cannot be approved until
consent is recorded, by voice or by click. The agent only accepts calls from an allowlist of
origins and has a daily conversation limit; conversations are billed by ElevenLabs. Voice needs
network, a microphone and a page served over https or localhost. The tool handlers can be checked
without network or microphone: open the page with `?voicetest`. The spoken conversation itself has
not been tested by us. Saying "emergency", or pressing the Emergency button in the voice box, clears the screen down to the one
affected case (where, what was found, the evidence, what the system has done so far) and shows the
on-call emergency team as connected. That connection is simulated and labelled as such; no call is
placed. For loud rooms the call starts in push-to-talk: the
microphone is open only while the button or the space bar is held, and a text field takes typed
requests instead. The agent itself is set to ignore background voices, to wait longer before it
takes the turn, and to favour the words that matter. Without the flag the dashboard has no voice
button and loads nothing for it.

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

The tag `pre-holdout` was set on 2026-11-14, before the holdout release.

Changes after `pre-holdout`: presentation only. The dashboard page got a background pattern and a
favicon. No detector, threshold or rule was changed, so the decisions are the same.

## Real data

The submission runs on the replayed dataset. [`connectors.md`](connectors.md) plans the step to a
real building: which connectors deliver the fifteen tables, which carry out the actions, and in
which order to switch them on. The interface is an OpenAPI description, generated from the code
with `python -m building_ops.openapi > docs/api/openapi.json` and readable at
<https://adh-gh.github.io/Hackathon-HOIV-2026-autonomous-building/api/>. It is a design; no server
implements it.

## Creator

Alf-David Heermann, <alfheermann@gmail.com>, team Alf & Friends, proximata Hackathon '26, Rhomberg track.

## Licence

MIT, see [LICENSE](LICENSE).
