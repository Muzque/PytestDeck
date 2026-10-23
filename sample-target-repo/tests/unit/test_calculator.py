import time
import pytest
from calculator import Calculator

@pytest.mark.smoke
def test_add():
    print("\n[unit] Running test_add: calculating 2 + 3", flush=True)
    time.sleep(0.15)
    calc = Calculator()
    result = calc.add(2, 3)
    print(f"[unit] Result: {result}", flush=True)
    assert result == 5

@pytest.mark.smoke
def test_subtract():
    print("\n[unit] Running test_subtract: calculating 10 - 4", flush=True)
    time.sleep(0.15)
    calc = Calculator()
    result = calc.subtract(10, 4)
    print(f"[unit] Result: {result}", flush=True)
    assert result == 6

def test_multiply():
    print("\n[unit] Running test_multiply: calculating 3 * 4", flush=True)
    time.sleep(0.15)
    calc = Calculator()
    result = calc.multiply(3, 4)
    print(f"[unit] Result: {result}", flush=True)
    assert result == 12

def test_divide():
    print("\n[unit] Running test_divide: calculating 8 / 2", flush=True)
    time.sleep(0.15)
    calc = Calculator()
    result = calc.divide(8, 2)
    print(f"[unit] Result: {result}", flush=True)
    assert result == 4

def test_divide_by_zero():
    print("\n[unit] Running test_divide_by_zero: calculating 5 / 0 (expecting ValueError)", flush=True)
    time.sleep(0.15)
    calc = Calculator()
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        calc.divide(5, 0)
    print("[unit] Successfully caught ValueError as expected", flush=True)


@pytest.mark.parametrize("a,b,expected", [
    (1, 1, 2),
    (10, 20, 30),
    (-5, 5, 0),
    (2.5, 3.5, 6.0),
])
def test_add_parameterized(a, b, expected):
    """Verifies addition with diverse inputs via parametrization."""
    time.sleep(0.12)
    calc = Calculator()
    assert calc.add(a, b) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        pytest.param(1, 2, 3, id="1 + 2 = 3 (positive)"),
        pytest.param(-4, 10, 6, id="a=-4, b=10 -> 6"),
    ],
)
def test_add_with_custom_ids(a, b, expected):
    """Verifies parametrized test cases with spaces, equals, and punctuation in node IDs."""
    time.sleep(0.12)
    calc = Calculator()
    assert calc.add(a, b) == expected

