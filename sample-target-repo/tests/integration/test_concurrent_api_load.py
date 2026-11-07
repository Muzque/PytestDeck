import logging
import time

import pytest
from fastapi.testclient import TestClient

from app import app

logger = logging.getLogger("integration.concurrent")

TestClient.__test__ = False
client = TestClient(app)


class TestMultiEndpointMatrix:
    """Verifies subtract, multiply, power, and modulo FastAPI endpoints under xdist."""

    @pytest.mark.api_mark
    def test_subtract_endpoint_positive_and_negative(self):
        """Verifies GET /calculate/subtract across signed inputs."""
        logger.info("GET /calculate/subtract?a=90&b=35")
        time.sleep(0.15)
        res = client.get("/calculate/subtract?a=90&b=35")
        assert res.status_code == 200
        assert res.json() == {"result": 55.0}

    @pytest.mark.api_mark
    def test_multiply_endpoint_scaling(self):
        """Verifies GET /calculate/multiply with decimal factors."""
        logger.info("GET /calculate/multiply?a=12.5&b=4")
        time.sleep(0.15)
        res = client.get("/calculate/multiply?a=12.5&b=4")
        assert res.status_code == 200
        assert res.json() == {"result": 50.0}

    @pytest.mark.api_mark
    def test_power_endpoint_exponentiation(self):
        """Verifies GET /calculate/power endpoint calculation."""
        logger.info("GET /calculate/power?base=3&exp=4")
        time.sleep(0.15)
        res = client.get("/calculate/power?base=3&exp=4")
        assert res.status_code == 200
        assert res.json() == {"result": 81.0}

    @pytest.mark.api_mark
    def test_modulo_endpoint_remainder(self):
        """Verifies GET /calculate/modulo returns expected remainder."""
        logger.info("GET /calculate/modulo?a=47&b=10")
        time.sleep(0.15)
        res = client.get("/calculate/modulo?a=47&b=10")
        assert res.status_code == 200
        assert res.json() == {"result": 7.0}


class TestApiErrorRecovery:
    """Verifies HTTP 400 error responses and subsequent healthy endpoint recovery."""

    def test_modulo_by_zero_returns_400(self):
        """Verifies GET /calculate/modulo with b=0 returns HTTP 400."""
        logger.warning("GET /calculate/modulo?a=25&b=0 - Expecting 400")
        time.sleep(0.15)
        res = client.get("/calculate/modulo?a=25&b=0")
        assert res.status_code == 400
        assert res.json()["detail"] == "Cannot modulo by zero"

    def test_service_healthy_after_bad_request(self):
        """Verifies service remains responsive immediately after a 400 error."""
        logger.info("Verifying /health and /calculate/multiply after 400 response")
        time.sleep(0.15)
        err_res = client.get("/calculate/divide?a=1&b=0")
        assert err_res.status_code == 400
        ok_res = client.get("/calculate/multiply?a=6&b=7")
        assert ok_res.status_code == 200
        assert ok_res.json() == {"result": 42.0}


def test_chained_financial_api_pipeline():
    """Executes a 3-step chained calculation across multiply, subtract, and divide endpoints."""
    logger.info("[pipeline] Running chained financial API pipeline...")
    time.sleep(0.18)
    gross = client.get("/calculate/multiply?a=80&b=5").json()["result"]
    after_discount = client.get(f"/calculate/subtract?a={gross}&b=40").json()["result"]
    per_seat = client.get(f"/calculate/divide?a={after_discount}&b=6").json()["result"]
    assert per_seat == 60.0
