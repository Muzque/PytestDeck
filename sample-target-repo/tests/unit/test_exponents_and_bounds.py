import time
import pytest
from calculator import Calculator


class TestExponentsAndModulo:
    """Verifies exponentiation and modulo operations across positive, zero, and negative inputs."""

    def setup_method(self):
        self.calc = Calculator()

    @pytest.mark.smoke
    def test_integer_power_growth(self):
        """Verifies integer base raised to positive exponent."""
        print("\n[advanced] Computing 2^10 power growth...", flush=True)
        time.sleep(0.12)
        assert self.calc.power(2, 10) == 1024.0

    def test_zero_and_negative_exponents(self):
        """Verifies x^0 == 1 and negative exponent fractional results."""
        print("\n[advanced] Checking zero and negative exponents...", flush=True)
        time.sleep(0.12)
        assert self.calc.power(99, 0) == 1.0
        assert self.calc.power(2, -2) == 0.25

    def test_modulo_remainder_positive(self):
        """Verifies remainder calculation on integer and float dividends."""
        print("\n[advanced] Computing modulo remainder 29 % 6...", flush=True)
        time.sleep(0.12)
        assert self.calc.modulo(29, 6) == 5.0

    def test_modulo_by_zero_raises_error(self):
        """Verifies modulo by zero raises ValueError."""
        print("\n[advanced] Verifying modulo by zero guard...", flush=True)
        time.sleep(0.12)
        with pytest.raises(ValueError, match="Cannot modulo by zero"):
            self.calc.modulo(15, 0)


class TestPercentageAndClamping:
    """Verifies percentage ratios and range clamping helpers."""

    def setup_method(self):
        self.calc = Calculator()

    def test_percentage_ratio_calculation(self):
        """Verifies part-to-whole percentage conversion."""
        print("\n[advanced] Calculating percentage 45 of 180...", flush=True)
        time.sleep(0.12)
        assert self.calc.percentage(45, 180) == 25.0

    def test_percentage_zero_whole_raises(self):
        """Verifies percentage with zero whole raises ValueError."""
        print("\n[advanced] Checking zero whole guard in percentage...", flush=True)
        time.sleep(0.12)
        with pytest.raises(ValueError, match="Whole cannot be zero"):
            self.calc.percentage(10, 0)

    def test_clamp_within_and_outside_bounds(self):
        """Verifies clamping values below low, within range, and above high."""
        print("\n[advanced] Verifying clamp lower/upper/in-range behavior...", flush=True)
        time.sleep(0.12)
        assert self.calc.clamp(-10, 0, 100) == 0
        assert self.calc.clamp(42, 0, 100) == 42
        assert self.calc.clamp(250, 0, 100) == 100

    def test_clamp_invalid_bounds_raises(self):
        """Verifies clamp raises ValueError when low > high."""
        print("\n[advanced] Verifying clamp invalid bounds guard...", flush=True)
        time.sleep(0.12)
        with pytest.raises(ValueError, match="low cannot exceed high"):
            self.calc.clamp(5, 20, 10)


@pytest.mark.regression
@pytest.mark.parametrize(
    "base,exp,expected",
    [
        (2, 3, 8.0),
        (5, 2, 25.0),
        (10, 0, 1.0),
    ],
)
def test_power_parametrized(base, exp, expected):
    """Verifies power operation across parametrized base/exponent pairs."""
    time.sleep(0.1)
    calc = Calculator()
    assert calc.power(base, exp) == expected
