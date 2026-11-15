import unittest
from tests.test_water_leak import Fixture, run, leaks


class RecurrenceTest(unittest.TestCase):
    def fixture(self, second=424):
        fx = Fixture(steps=600)
        for start in (4, second):
            for i in range(start, start + 20):
                fx.flow['R105'][i] = 1
        return fx

    def test_two_five_hour_leaks_separated_by_100_hours(self):
        self.assertEqual(len(leaks(run(self.fixture()))), 2)
        for omitted in (4, 424):
            fx = self.fixture()
            fx.flow['R105'][omitted:omitted + 20] = [0] * 20
            self.assertEqual(len(leaks(run(fx))), 1)

    def test_ordinary_short_usage_allows_recovery(self):
        fx = self.fixture()
        for i in (70, 150, 250):
            fx.flow['R105'][i] = 10
        self.assertEqual(len(leaks(run(fx))), 2)

    def test_unknown_or_invalid_readings_do_not_prove_recovery(self):
        for invalid in ('blank', 'reset'):
            fx = self.fixture()
            if invalid == 'blank':
                fx.blank.add(('R105', 250))
            else:
                fx.override[('R105', 250)] = 0
            self.assertEqual(len(leaks(run(fx))), 1)

    def test_recovery_boundary(self):
        # Last leak increment is 23. Zero-flow interval 24 starts at 23.
        # At index 311, 72 hours of qualifying observation have elapsed.
        self.assertEqual(len(leaks(run(self.fixture(second=311)))), 2)
        # A full new qualifying pattern before recovery prevents closure.
        self.assertEqual(len(leaks(run(self.fixture(second=280)))), 1)

    def test_continuous_and_escalating_leaks(self):
        fx = Fixture()
        fx.flow['R105'][4:300] = [1] * 296
        self.assertEqual(len(leaks(run(fx))), 1)
        fx.flow['R105'][100:120] = [10] * 20
        self.assertTrue(any(d['priority'] == 'critical' for d in run(fx)))
