class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b

    def subtract(self, a: float, b: float) -> float:
        return a - b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    def power(self, base: float, exp: float) -> float:
        return float(base**exp)

    def modulo(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot modulo by zero")
        return a % b

    def percentage(self, part: float, whole: float) -> float:
        if whole == 0:
            raise ValueError("Whole cannot be zero")
        return (part / whole) * 100.0

    def clamp(self, value: float, low: float, high: float) -> float:
        if low > high:
            raise ValueError("low cannot exceed high")
        return max(low, min(high, value))

