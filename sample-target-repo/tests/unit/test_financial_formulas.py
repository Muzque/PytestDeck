import time
import pytest
from calculator import Calculator


class TestDiscountAndTaxTier:
    """Verifies financial discount, sales tax, and margin formulas."""

    def setup_method(self):
        self.calc = Calculator()

    @pytest.mark.regression
    def test_tiered_discount_application(self):
        """Computes 15% promotional discount on a $240 subtotal."""
        print("\n[finance] Applying 15% discount to subtotal 240.0...", flush=True)
        time.sleep(0.14)
        discount = self.calc.multiply(240.0, 0.15)
        net_price = self.calc.subtract(240.0, discount)
        assert net_price == 204.0

    @pytest.mark.regression
    def test_sales_tax_addition(self):
        """Computes 8.5% sales tax on net price $200."""
        print("\n[finance] Computing 8.5% tax on 200.0...", flush=True)
        time.sleep(0.14)
        tax = self.calc.multiply(200.0, 0.085)
        gross_total = self.calc.add(200.0, tax)
        assert gross_total == 217.0

    def test_net_margin_percentage(self):
        """Computes profit margin percentage from revenue and cost."""
        print("\n[finance] Calculating net margin percentage...", flush=True)
        time.sleep(0.14)
        profit = self.calc.subtract(500.0, 350.0)
        margin_pct = self.calc.percentage(profit, 500.0)
        assert margin_pct == 30.0


def test_compound_growth_steps():
    """Verifies 2-period 10% compound growth using power and multiply."""
    print("\n[finance] Computing 2-period 10% compound growth on 1000...", flush=True)
    time.sleep(0.14)
    calc = Calculator()
    factor = calc.power(1.10, 2)
    ending_balance = calc.multiply(1000.0, factor)
    assert ending_balance == pytest.approx(1210.0)


def test_currency_rounding_stability():
    """Verifies fractional cent clamping and division stability."""
    print("\n[finance] Checking fractional cent rounding stability...", flush=True)
    time.sleep(0.14)
    calc = Calculator()
    installment = round(calc.divide(100.0, 3), 2)
    assert calc.clamp(installment, 0.0, 50.0) == 33.33
