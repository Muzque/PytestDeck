import time
import pytest
from calculator import Calculator


class TestAlgebraicIdentities:
    """Verifies algebraic commutativity, distributivity, and inverse roundtrips inside validators/."""

    def setup_method(self):
        self.calc = Calculator()

    def test_additive_commutativity(self):
        """Verifies a + b == b + a across signed floats."""
        print("\n[validators] Verifying additive commutativity...", flush=True)
        time.sleep(0.12)
        assert self.calc.add(18.75, -6.25) == self.calc.add(-6.25, 18.75)

    def test_multiplicative_distributivity(self):
        """Verifies a * (b + c) == (a * b) + (a * c)."""
        print("\n[validators] Verifying multiplicative distributivity...", flush=True)
        time.sleep(0.12)
        lhs = self.calc.multiply(4.0, self.calc.add(7.0, 3.0))
        rhs = self.calc.add(self.calc.multiply(4.0, 7.0), self.calc.multiply(4.0, 3.0))
        assert lhs == rhs == 40.0

    def test_inverse_operation_roundtrip(self):
        """Verifies (x * k) / k returns original value x."""
        print("\n[validators] Checking multiplication/division inverse roundtrip...", flush=True)
        time.sleep(0.12)
        scaled = self.calc.multiply(42.5, 8.0)
        restored = self.calc.divide(scaled, 8.0)
        assert restored == pytest.approx(42.5)


def test_clamp_boundary_invariants():
    """Verifies clamping exact boundary endpoints returns the endpoints unchanged."""
    print("\n[validators] Checking exact clamp boundary endpoints...", flush=True)
    time.sleep(0.12)
    calc = Calculator()
    assert calc.clamp(0.0, 0.0, 1.0) == 0.0
    assert calc.clamp(1.0, 0.0, 1.0) == 1.0
