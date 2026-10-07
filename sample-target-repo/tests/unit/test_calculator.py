import pytest
from calculator import Calculator

def test_add():
    print("\n[unit] Running test_add: calculating 2 + 3")
    calc = Calculator()
    result = calc.add(2, 3)
    print(f"[unit] Result: {result}")
    assert result == 5

def test_subtract():
    print("\n[unit] Running test_subtract: calculating 10 - 4")
    calc = Calculator()
    result = calc.subtract(10, 4)
    print(f"[unit] Result: {result}")
    assert result == 6

def test_multiply():
    print("\n[unit] Running test_multiply: calculating 3 * 4")
    calc = Calculator()
    result = calc.multiply(3, 4)
    print(f"[unit] Result: {result}")
    assert result == 12

def test_divide():
    print("\n[unit] Running test_divide: calculating 8 / 2")
    calc = Calculator()
    result = calc.divide(8, 2)
    print(f"[unit] Result: {result}")
    assert result == 4

def test_divide_by_zero():
    print("\n[unit] Running test_divide_by_zero: calculating 5 / 0 (expecting ValueError)")
    calc = Calculator()
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        calc.divide(5, 0)
    print("[unit] Successfully caught ValueError as expected")
