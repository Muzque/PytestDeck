import time
import pytest
from calculator import Calculator


class TestRollingStatistics:
    """Verifies multi-step statistical aggregations using Calculator operations."""

    def setup_method(self):
        self.calc = Calculator()

    def test_cumulative_sum_series(self):
        """Computes cumulative sum across a numeric series."""
        print("\n[stats] Computing cumulative sum series...", flush=True)
        time.sleep(0.22)
        total = 0
        for val in (10, 20, 30, 40):
            total = self.calc.add(total, val)
        assert total == 100

    def test_arithmetic_mean_calculation(self):
        """Computes arithmetic mean of sample observations."""
        print("\n[stats] Computing arithmetic mean...", flush=True)
        time.sleep(0.22)
        sum_val = self.calc.add(self.calc.add(15, 25), 50)
        mean = self.calc.divide(sum_val, 3)
        assert mean == 30.0

    def test_variance_spread_step(self):
        """Computes squared deviation spread across sample points."""
        print("\n[stats] Computing variance spread...", flush=True)
        time.sleep(0.22)
        diff = self.calc.subtract(25, 15)
        sq = self.calc.multiply(diff, diff)
        assert sq == 100


def test_weighted_moving_average():
    """Verifies weighted moving average calculation."""
    print("\n[stats] Calculating weighted moving average...", flush=True)
    time.sleep(0.22)
    calc = Calculator()
    w1 = calc.multiply(10, 1)
    w2 = calc.multiply(20, 2)
    w3 = calc.multiply(30, 3)
    total = calc.add(calc.add(w1, w2), w3)
    assert calc.divide(total, 6) == pytest.approx(23.3333, rel=1e-3)


def test_normalization_scaling():
    """Verifies min-max normalization scaling to [0, 1]."""
    print("\n[stats] Scaling values to unit interval...", flush=True)
    time.sleep(0.22)
    calc = Calculator()
    numerator = calc.subtract(75, 50)
    denominator = calc.subtract(100, 50)
    assert calc.divide(numerator, denominator) == 0.5
