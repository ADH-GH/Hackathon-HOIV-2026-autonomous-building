import unittest
from datetime import datetime, timezone

from building_ops.decisions import (APPROVAL_AND_CONSENT, AUTONOMOUS, HUMAN_APPROVAL,
                                    Decision, DecisionError, dedupe)

T = datetime(2026, 1, 5, 6, 30, tzinfo=timezone.utc)


def make(action="flag_anomaly", **kw):
    base = dict(timestamp_utc=T, affected_assets=["room_101"], issue_type="water_leak",
                action=action, priority="high", reason="night flow above the room's base")
    base.update(kw)
    return Decision(**base)


class ContractTest(unittest.TestCase):
    def test_required_fields_present(self):
        d = make().finalize()
        for key in ("event_id", "timestamp_utc", "affected_assets", "issue_type", "action",
                    "priority", "reason", "requires_human_approval"):
            self.assertIn(key, d)
        self.assertEqual(d["timestamp_utc"], "2026-01-05T06:30:00Z")

    def test_event_id_is_stable(self):
        self.assertEqual(make().finalize()["event_id"], make().finalize()["event_id"])

    def test_rejects_bad_input(self):
        for bad in (dict(action="open_window"), dict(priority="urgent"), dict(reason=" "),
                    dict(affected_assets=[]), dict(confidence=1.2),
                    dict(timestamp_utc=datetime(2026, 1, 5, 6, 30))):
            with self.assertRaises(DecisionError):
                make(**bad).finalize()


class AutonomyTest(unittest.TestCase):
    def level(self, action, **kw):
        return make(action, **kw).finalize()["autonomy"]

    def test_autonomous_actions(self):
        for action in ("schedule_cleaning", "dispatch_robot", "notify_guest", "flag_anomaly",
                       "optimize_energy", "adjust_room_setpoint"):
            self.assertEqual(self.level(action), AUTONOMOUS, action)
        self.assertEqual(self.level("order_service", service_kind="waste_pickup"), AUTONOMOUS)

    def test_approval_actions(self):
        for action in ("dispatch_technician", "block_room", "reassign_room"):
            d = make(action).finalize()
            self.assertEqual(d["autonomy"], HUMAN_APPROVAL, action)
            self.assertTrue(d["requires_human_approval"])
            self.assertFalse(d["requires_guest_consent"])
        self.assertEqual(self.level("order_service"), HUMAN_APPROVAL)
        self.assertEqual(self.level("order_service", service_kind="contractor"), HUMAN_APPROVAL)
        self.assertEqual(self.level("adjust_room_setpoint", outside_comfort_band=True), HUMAN_APPROVAL)
        self.assertEqual(self.level("notify_guest", notable_cost=True), HUMAN_APPROVAL)

    def test_consent_actions(self):
        for kw in (dict(enters_occupied_room=True), dict(water_shutoff=True), dict(safety_relevant=True)):
            d = make("request_inspection", **kw).finalize()
            self.assertEqual(d["autonomy"], APPROVAL_AND_CONSENT)
            self.assertTrue(d["requires_human_approval"] and d["requires_guest_consent"])

    def test_detector_cannot_lower_oversight(self):
        d = make("dispatch_technician", autonomy=AUTONOMOUS).finalize()
        self.assertTrue(d["requires_human_approval"])

    def test_detector_can_raise_oversight(self):
        d = make("flag_anomaly", autonomy=HUMAN_APPROVAL).finalize()
        self.assertTrue(d["requires_human_approval"])


class DedupeTest(unittest.TestCase):
    def test_one_alert_per_episode_and_action(self):
        later = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
        a = make(episode_id="leak-101").finalize()
        b = make(episode_id="leak-101", timestamp_utc=later).finalize()
        c = make("request_inspection", episode_id="leak-101", timestamp_utc=later).finalize()
        kept = dedupe([b, c, a])
        self.assertEqual([d["event_id"] for d in kept], [a["event_id"], c["event_id"]])


if __name__ == "__main__":
    unittest.main()
