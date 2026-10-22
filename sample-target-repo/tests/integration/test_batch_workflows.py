import logging
import time

import pytest
from fastapi.testclient import TestClient

from app import app

logger = logging.getLogger("integration.workflows")

TestClient.__test__ = False
client = TestClient(app)


class TestSequentialCalculationWorkflow:
    """Verifies multi-step sequential API workflows with observable per-test execution pacing."""

    def test_step_1_initial_deposit_addition(self):
        """Executes initial balance addition request against /calculate/add."""
        logger.info("[workflow] Step 1: Adding initial deposit 100 + 250")
        time.sleep(0.25)
        res = client.get("/calculate/add?a=100&b=250")
        assert res.status_code == 200
        assert res.json()["result"] == 350.0

    def test_step_2_split_allocation_division(self):
        """Splits accumulated balance across 5 accounts via /calculate/divide."""
        logger.info("[workflow] Step 2: Dividing 350 across 5 allocations")
        time.sleep(0.25)
        res = client.get("/calculate/divide?a=350&b=5")
        assert res.status_code == 200
        assert res.json()["result"] == 70.0

    def test_step_3_fee_adjustment_addition(self):
        """Applies negative fee adjustment via /calculate/add."""
        logger.info("[workflow] Step 3: Applying -5.5 fee adjustment to 70.0")
        time.sleep(0.25)
        res = client.get("/calculate/add?a=70.0&b=-5.5")
        assert res.status_code == 200
        assert res.json()["result"] == pytest.approx(64.5)

    def test_step_4_invalid_zero_allocation_guard(self):
        """Verifies zero-allocation request returns HTTP 400."""
        logger.info("[workflow] Step 4: Verifying zero-allocation guard")
        time.sleep(0.25)
        res = client.get("/calculate/divide?a=64.5&b=0")
        assert res.status_code == 400
        assert res.json()["detail"] == "Cannot divide by zero"


def test_reconciliation_roundtrip_check():
    """Verifies roundtrip addition and division consistency across API calls."""
    logger.info("[workflow] Running reconciliation roundtrip check...")
    time.sleep(0.25)
    add_res = client.get("/calculate/add?a=42&b=58")
    assert add_res.status_code == 200
    total = add_res.json()["result"]
    div_res = client.get(f"/calculate/divide?a={total}&b=4")
    assert div_res.status_code == 200
    assert div_res.json()["result"] == 25.0
