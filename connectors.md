# From the replayed dataset to a real building

The submission runs on the PLATO-40 dataset: a directory of files in, `decisions.jsonl` out, every
effect simulated. This note plans the step to real data. It is a plan. No connector exists yet and
no server implements the interface.

The interface is described in [`docs/api/openapi.json`](docs/api/openapi.json), generated from the
code by `python -m building_ops.openapi`, and readable as a page at
<https://adh-gh.github.io/Hackathon-HOIV-2026-autonomous-building/api/>.

## The idea: keep the tables, replace the files

The detectors read fifteen tables. A real deployment keeps exactly these tables and fills them from
live systems, one feed per table. A connector's whole job is to translate its system's data into
the rows of one feed, and, in the other direction, to carry out one kind of action. The detectors
do not change.

## Connectors that deliver data

| # | Connector | Feeds it fills | Read by | Typical interface |
|---|---|---|---|---|
| 1 | Property management system | bookings, room events (check-in, check-out, no-show, reassignment) | S01, S05, logistics, heating | REST API with webhooks |
| 2 | Guest messaging | guest requests | S01, S03 | Chat or SMS provider, or the inbox of the property management system |
| 3 | Access control | access log | S01 (arrival at the door) | Lock system API or event export |
| 4 | Room controls | room telemetry (temperature, setpoint, humidity, CO₂, presence, window) | S03, S01 | KNX or BACnet through a gateway, often MQTT |
| 5 | Water metering | room meters, main meter | S02 | M-Bus, wireless M-Bus or LoRaWAN through a meter gateway |
| 6 | Energy | grid meter, PV inverter, battery state | Energy plan | Modbus TCP or the inverter and battery vendor's API |
| 7 | Plant | heat pump and air handling unit metrics | S03, S04 | BACnet or Modbus through the building management system |
| 8 | Logistics | vending stock, waste fill levels, restock and pickup events | Logistics | Vending telemetry API, fill-level sensors |
| 9 | Housekeeping and robots | cleaning and robot events | S01, S05 | Housekeeping app, robot fleet API |
| 10 | Roster | shifts and absences of cleaners, technicians and robots | S01, S04, S05 | Workforce or HR system, or a shared calendar |
| 11 | Weather | observations and forecasts with their issue time | S03, energy plan | Public weather service |
| 12 | Electricity price | day-ahead prices with their publication time | Energy plan, heating | Day-ahead price feed of the supplier or the market |
| 13 | Maintenance | work orders and their state | Closing the loop, not detection | Ticket or maintenance system |

The interface column names what is usual for that class of system. Which product stands in a given
building, and what its interface really offers, has to be checked on site.

## Connectors that carry out actions

Each action of the decision contract goes to one target system. The autonomy level is decided by
the pipeline before anything is sent; a connector never decides it.

| Action | Target system | Level today |
|---|---|---|
| `schedule_cleaning` | Housekeeping app | autonomous |
| `dispatch_robot` | Robot fleet | autonomous |
| `notify_guest` | Guest messaging | autonomous |
| `adjust_room_setpoint` | Room controls | autonomous inside the comfort band |
| `optimize_energy` | Battery controller, room controls | autonomous |
| `release_room`, `block_room`, `reassign_room` | Property management system | release autonomous, block needs approval |
| `order_service` | Supplier or ticket system | restock and waste pickup autonomous, contractors need approval |
| `dispatch_technician`, `request_inspection` | Maintenance system | approval; entering an occupied room also needs guest consent |
| `flag_anomaly`, `request_human_approval` | Operator dashboard, on-call notification | autonomous |
| Emergency | Telephony: bridge the caller to the on-call number | no approval, it calls people in |

Two further connectors serve people, not data: an **identity provider** so that an approval carries
a name, and **telephony** for the emergency bridge and for the voice assistant on a phone line.

## What changes with real data

- **Time of availability becomes real.** The replay knows when a price or a forecast was published
  because the dataset says so. Live, every feed must deliver that time itself, and rows arrive late
  and out of order. The interface makes the "known at" column mandatory where the dataset has one.
- **Silence is a finding.** In the dataset a missing value is blank. Live, a feed that stops
  sending looks the same as a quiet building. `/status` therefore reports every feed as ok, late or
  silent, and the detectors already treat a missing reading as missing, not as zero.
- **Identifiers must be mapped.** Rooms, meters and assets have different names in every system.
  Each connector needs a mapping table to the ids of `building.json`.
- **Thresholds were set on synthetic data.** The leak, heat pump and filter rules are calibrated on
  one fictional year. A real building needs a period in which the system only watches.
- **Personal data.** Access logs and guest messages are personal data. The feeds take a booking id
  and a pseudonymous credential, never a name, and the retention period has to be decided with the
  operator before the first row is stored.
- **Write access is the risk.** Reading a meter cannot hurt anyone; changing a setpoint or sending
  a message can. Every action carries a `dry_run` flag, and the order below gives write access last.

## Order of work

1. **Read only, shadow mode.** Connect the feeds, run the detectors, show decisions on the
   dashboard, send nothing. Compare with what the staff did. Start with the feeds that carry the
   strongest results: water meters, plant metrics, bookings.
2. **Tickets and messages to staff.** Findings become work orders and notifications. Everything
   that changes the building still waits for a person.
3. **Low-risk actions.** Cleaning plans, robot tasks, guest messages, restock and pickup orders.
4. **Building control.** Setpoints inside the comfort band and the battery plan, each behind its
   own switch, with the measured effect replacing the simulated estimate.

## What is not planned here

A server, a database, a message queue, hosting and monitoring. The interface says what must cross
the boundary; how it is run is a separate decision.
