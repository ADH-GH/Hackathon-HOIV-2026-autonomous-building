# Insights: feedback to CLARA and to PLATO

Computed from the `dev` dataset (365 days) by `python -m building_ops insights <data_dir> --decisions decisions.jsonl`. Every number below comes from that command. This is a retrospective analysis of a finished year; unlike the detectors it may read work orders and alarms.

**All findings concern the fictional PLATO-40 only.** They are not statements about real PLATO buildings or about what CLARA does today. The data is synthetic and the models behind it are simplified, so each finding states its uncertainty. No savings are claimed.

## For CLARA: operating rules for next year

### C1. Leak detection by continuity, not by a night-flow threshold

**Finding.** The year had 5 water repairs (burst hoses, running toilets, one pipe leak). The BMS night-flow alarm was raised 1 time(s). Reading the meters for flow that never returns to zero, for sustained high flow and for the night gap between main meter and room meters finds all of them, between 22 and 186 hours before the repair was logged (median 59 h, incl. the heat pump cases).

**Recommendation.** Replace the single night-flow threshold with three meter rules: 2 h of at least 8 L per 15 min, 5 h without a zero interval, and a night gap of 2 L per 15 min between main meter and room sum.

**Expected benefit.** Running toilets are caught on day one instead of after about a week (simulated on the replay, not a measured saving).

**Uncertainty.** Synthetic leak shapes; real fixtures leak less regularly. Thresholds were set on this year and held on the independent quickstart run. Confidence 0.8.

**Evidence.** `work_orders.csv`: corrective orders mentioning hose, toilet or leak; `events.jsonl`: bms_alarm WATER_NIGHT_FLOW; `decisions.jsonl`: flag_anomaly on the same assets, see README 'Water leak thresholds'

### C2. Tie the low-temperature alarm to occupancy

**Finding.** 156 of 160 ROOM_TEMP_LOW alarms were raised for rooms that were vacant at that moment, where 18 °C is the intended setback.

**Recommendation.** Raise ROOM_TEMP_LOW only for occupied rooms with the window closed, against the comfort band of 20 °C, and keep a separate frost limit for vacant rooms.

**Expected benefit.** About 97.5 % fewer low-temperature alarms; the remaining ones mean a guest is cold.

**Uncertainty.** Occupancy is taken from lifecycle events; a guest who left without checking out would count as present. Confidence 0.85.

**Evidence.** `events.jsonl`: bms_alarm ROOM_TEMP_LOW raised; `events.jsonl`: check-in and check-out events for occupancy

### C3. Pre-heat before arrival instead of at check-in

**Finding.** In the heating season 353 of 1380 check-ins (25.6 %) were into a room below 20 °C; such a room needed a median of 75 minutes to reach 20 °C.

**Recommendation.** End the 18 °C setback about 90 minutes before the expected arrival: the booked check-in time, or the earlier time from an early check-in request once the room is clean.

**Expected benefit.** Guests enter a room inside the comfort band; heating shifts by about 90 minutes per arrival (energy effect not measured).

**Uncertainty.** A motion sensor and a 15-minute grid give coarse arrival times; the thermal model is simplified. Confidence 0.7.

**Evidence.** `events.jsonl`: checkin, checkin_early, checkin_after_wait in Nov to Mar; `room_telemetry.csv`: temperature_c from check-in until 20 °C

### C4. Send the robot first, and plan for an absent cleaner in the morning

**Finding.** Human cleaning took 40.5 minutes on average when a robot had cleaned the floor first (n = 3103) and 52.8 minutes without (n = 611). 15 of the 24 guests who waited for a room did so on the 24 days with an absent cleaner; the median wait was 45 minutes.

**Recommendation.** Dispatch robots to every vacated turnover room before the cleaner arrives, order the day by arrival time, and when an absence is known, ask in the morning for approval to put the on-call housekeeper on notice instead of waiting for the first guest at a closed door.

**Expected benefit.** Shorter turnovers on every day and fewer waiting guests on the few days that cause most of the waiting.

**Uncertainty.** The robot comparison is observational: days without a robot may differ in other ways. The replay did not follow our plan. Confidence 0.65.

**Evidence.** `events.jsonl`: robot_floor_cleaning_completed, cleaning_started, cleaning_completed; `events.jsonl`: arrival_waiting_room, checkin_after_wait; `staff_roster.csv`: cleaner shifts with status sick or vacation

### C5. Change ventilation filters by condition and before the technician is away

**Finding.** Planned filter changes happened at about 203, 235 Pa differential pressure. 2 unplanned changes happened at about 262, 261 Pa, 2 of them within a week of a technician absence. 2 planned changes were postponed first ("AHU1 filter change postponed - rooftop unit only reachable with lift platform, not available").

**Recommendation.** Project the filter pressure forward from its trend; if it will pass 240 Pa during a known technician absence, bring the change forward or order a contractor before the absence starts.

**Expected benefit.** No unplanned filter changes and no period of reduced airflow (simulated estimate).

**Uncertainty.** Two unplanned cases in one synthetic year; the degradation rate is not constant. Confidence 0.7.

**Evidence.** `equipment.csv`: AHU1 filter_dp_pa, daily median; `work_orders.csv`: AHU1 preventive, postponed and corrective orders; `staff_roster.csv`: technician shifts with status sick or vacation

### C6. Restock and collect by forecast, not by fixed weekday

**Finding.** The vending machine ran out 20 times, by weekday: {'Sun': 14, 'Thu': 4, 'Sat': 2}. Regular restock is Monday and Thursday. The central waste container was full on: {'Mon': 2, 'Sun': 1}; regular pickup is Tuesday and Friday.

**Recommendation.** Order an extra restock or pickup about 24 hours ahead whenever the current consumption rate will empty the machine or fill the container before the next regular visit; weekends first.

**Expected benefit.** Stock-outs and overflow move from the weekend to zero (simulated estimate).

**Uncertainty.** Demand is synthetic; the 24-hour lead time is taken from the dataset README. Confidence 0.7.

**Evidence.** `events.jsonl`: vending_out_of_stock, waste_bin_full; `logistics.csv`: hourly stock and fill levels

### C7. Watch the heat pump's COP against the outdoor temperature

**Finding.** On normal days the 6-hour median COP stays within 3 % of 2.796 + 0.0761 × outdoor °C. Before each heat pump service of the year it dropped by about 15 %, visible 54 to 59 hours before the work order.

**Recommendation.** Add a COP residual check (10 % below the model for 6 hours, at least 16 valid readings) and link it to the forecast: a degraded plant ahead of a cold night is critical.

**Expected benefit.** Service is organised two days earlier, before occupied rooms get cold (simulated on the replay).

**Uncertainty.** The model was fitted on this year; it held on the independent quickstart run but needs refitting for a real plant. Confidence 0.8.

**Evidence.** `equipment.csv`: HP1 heat_output_kw, electric_kw, status; `weather.csv`: outdoor_c; `work_orders.csv`: HP1 corrective

### C8. Check new water meters after an exchange

**Finding.** After the meter exchanges in the year (WM_R105, WM_R405) the new meters stepped backwards repeatedly, which a cumulative meter cannot do.

**Recommendation.** Run a 24-hour plausibility check after every meter exchange and exclude a meter from leak detection while it fails.

**Expected benefit.** No false leak alarms from a faulty meter, and no blind spot either.

**Uncertainty.** Could be a property of the synthetic meter model rather than of a product. Confidence 0.75.

**Evidence.** `work_orders.csv`: type metering; `room_water.csv`: decreasing meter_total_l after the exchange

## For PLATO: design of the next building

### P1. South rooms overheat in summer; the building has no cooling

**Finding.** In June to August occupied south rooms were above 26 °C for 36.1 % of the time, north rooms for 29.0 %. Guests sent 201 'too hot' requests (by month: {6: 42, 7: 159}; by orientation: {'N': 84, 'S': 117}) against 29 'too cold'. High-temperature alarms: {'N': 41, 'S': 84}.

**Recommendation.** Next building: external shading on the south façade as standard, and a reversible heat pump or active night cooling sized for a July heat wave.

**Expected benefit.** Fewer heat complaints, which are the largest comfort issue of the year by count (qualitative).

**Uncertainty.** Both orientations overheat; the south excess is about 7 percentage points. Weather and thermal zones are synthetic and uncalibrated. Confidence 0.75.

**Evidence.** `room_telemetry.csv`: temperature_c of occupied rooms, Jun to Aug, by orientation; `guest_requests.csv`: temperature_hot by month and room; `events.jsonl`: bms_alarm ROOM_TEMP_HIGH; `building.json`: operations.cooling = none

### P2. The first floor is the cold floor

**Finding.** In December to February occupied first-floor rooms with closed windows were below 20 °C for 17.3 % of the time, floors 2 to 4 for 9.8, 11.3 and 10.4 %.

**Recommendation.** Next building: more insulation in the floor slab of the lowest storey, which stands above open parking, and a higher heating capacity for those rooms.

**Expected benefit.** First-floor comfort on the level of the other floors (qualitative).

**Uncertainty.** The dataset does not state why floor 1 is colder; the exposed underside is our reading of the PLATO concept, not a measured cause. Confidence 0.6.

**Evidence.** `room_telemetry.csv`: temperature_c of occupied rooms, Dec to Feb, window closed, by floor; `building.json`: room floors

### P3. The sensor gateway on floor 3 drops out

**Finding.** 114 of 159 sensor communication-loss alarms came from floor 3 ({1: 31, 2: 8, 3: 114, 4: 6}). Missing temperature readings by floor: {1: 0.32 %, 2: 0.47 %, 3: 0.91 %, 4: 0.37 %}.

**Recommendation.** Next building: review gateway placement and antenna on floor 3's position in the stack, add a second gateway per floor or a mesh fallback, and monitor gateway health as an asset of its own.

**Expected benefit.** Fewer blind periods; detectors that need valid readings stay available (qualitative).

**Uncertainty.** One year, one building; the cause (placement, hardware, interference) is not in the data. Confidence 0.7.

**Evidence.** `events.jsonl`: bms_alarm SENSOR_COMM_LOSS by room and floor; `room_telemetry.csv`: blank temperature_c by floor; `building.json`: gateways per floor

### P4. Noise complaints concentrate on the upper floors

**Finding.** Noise complaints per 100 occupied room-nights by floor: {1: 0.6, 2: 2.28, 3: 2.69, 4: 2.34} (counts: {1: 13, 2: 50, 3: 58, 4: 52}).

**Recommendation.** Next building: check impact-sound insulation between the timber modules and the position of corridors, lift and plant relative to the upper rooms.

**Expected benefit.** Fewer noise complaints, the third most frequent request type (qualitative).

**Uncertainty.** Complaints depend on the neighbours as much as on the building; the text of the requests points to neighbouring rooms. Confidence 0.5.

**Evidence.** `guest_requests.csv`: noise_complaint by room; `events.jsonl`: occupancy for room-nights per floor

### P5. Design for leaks and for maintenance access

**Finding.** 5 water repairs in one year: R201 2026-03-20: Burst flexible hose under washbasin replaced; floor dried; room inspected; R403 2026-06-28: Toilet fill valve replaced (continuous running); WM_MAIN 2026-07-18: Leak on DHW circulation pipe in technical room repaired; R401 2026-08-17: Burst flexible hose under washbasin replaced; floor dried; room inspected; R208 2026-11-17: Toilet fill valve replaced (continuous running). Planned filter changes were postponed 2 times: "AHU1 filter change postponed - rooftop unit only reachable with lift platform, not available".

**Recommendation.** Next building: a leak sensor under each washbasin and a motorised shut-off per room that needs approval to close, braided hoses with a fixed replacement interval, sub-metering of the technical room, and permanent safe access to the rooftop unit.

**Expected benefit.** A burst hose is closed in minutes instead of running for a day; planned maintenance is not postponed for access (qualitative).

**Uncertainty.** Fault frequencies are engineered for the hackathon and say nothing about real products. Confidence 0.65.

**Evidence.** `work_orders.csv`: corrective orders for rooms and WM_MAIN; `work_orders.csv`: AHU1 postponed

## Target architecture

What the real autonomous building would need. Boxes marked (built) exist in this repository as a prototype on the replay.

```
 Sources                    Platform                         Decide and act                      People
 -------                    --------                         --------------                      ------
 Booking system  ---+
 Access control  ---+       Ingestion with time of           Agents, one per domain:             Guests
 Room sensors    ---+-----> availability (built)   ------->   operations / turnaround (built)     (messages in their language,
 Water meters    ---+       Data quality: gaps, resets,       water (built)                        consent for room entry)
 Heat pump, AHU  ---+       jitter, implausible values        energy and comfort (built)
 PV, battery     ---+       (built for water, heat pump)      maintenance                         Operations staff
 Weather, prices ---+       State: occupancy, room            housekeeping and robots             (approval queue, built)
 Roster, robots  ---+       readiness, asset health           guest service
 Work orders     ---+       Episode store and audit trail             |                           Technician, contractors
                            (built: decisions.jsonl)                  v
                                                             Autonomy gate (built):
                                                             autonomous / human approval /
                                                             approval + guest consent
                                                                      |
                                                                      v
                                                             Executors: setpoints, battery,
                                                             cleaning plan, robot tasks,
                                                             orders, messages
                                                             (mock executor built)
                                                                      |
                                                                      v
                                                             Verification: did the signal
                                                             recover? else escalate
                                                                      |
                                                                      v
                                                             Learning loop (this file):
                                                             rules for CLARA, design for PLATO
```

- **Data.** Everything carries two times: when it happened and when it became known. Meters and telemetry at 15 minutes; forecasts, prices, roster and bookings with their publication time.
- **Agents.** One agent per domain proposes decisions with evidence. They do not act on their own authority: every proposal passes the autonomy gate, which is code, not a prompt.
- **Robots.** Floor cleaning before the cleaner, waste bin transport, both only in vacated rooms and common areas. A robot never certifies or releases a room.
- **Interfaces.** Booking system and self-check-in kiosk, access control, building management system for setpoints and plant data, meter gateway, robot fleet manager, energy management for PV and battery, guest messaging, a work order system, and the approval queue for staff.
- **Safety.** Entering an occupied room, shutting off water and safety-relevant control stay with people. Simulated effects stay labelled as simulated until a measurement confirms them.
