import time
import pytest
from fastapi.testclient import TestClient
from app import app

TestClient.__test__ = False
client = TestClient(app)

def test_health_check_endpoint():
    print("\n[integration] GET /health - Checking service status")
    response = client.get("/health")
    print(f"[integration] Status Code: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sample-target-repo"}

def test_add_endpoint():
    print("\n[integration] GET /calculate/add?a=15&b=25 - Testing addition endpoint")
    response = client.get("/calculate/add?a=15&b=25")
    print(f"[integration] Status Code: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"result": 40.0}

def test_divide_endpoint_valid():
    print("\n[integration] GET /calculate/divide?a=20&b=4 - Testing division endpoint")
    response = client.get("/calculate/divide?a=20&b=4")
    print(f"[integration] Status Code: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"result": 5.0}

def test_divide_endpoint_by_zero():
    print("\n[integration] GET /calculate/divide?a=10&b=0 - Testing division by zero handling")
    response = client.get("/calculate/divide?a=10&b=0")
    print(f"[integration] Status Code: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot divide by zero"}

@pytest.mark.slow
def test_long_running_batch_calculation():
    """Simulates a multi-stage, long-running batch calculation workflow across API endpoints."""
    print("\n" + "=" * 65, flush=True)
    print("[integration-long] Starting long-running batch calculation workflow...", flush=True)
    print("=" * 65, flush=True)

    stages = [
        ("Stage 1/5", "Pinging /health endpoint to verify service readiness", "/health", None),
        ("Stage 2/5", "Batch addition: 15.5 + 34.5", "/calculate/add?a=15.5&b=34.5", 50.0),
        ("Stage 3/5", "Intermediate division: 250.0 / 5.0", "/calculate/divide?a=250&b=5", 50.0),
        ("Stage 4/5", "Chained calculation check: 99.9 + 0.1", "/calculate/add?a=99.9&b=0.1", 100.0),
        ("Stage 5/5", "Final boundary pipeline verification: 1000.0 / 8.0", "/calculate/divide?a=1000&b=8", 125.0),
    ]

    for stage_num, desc, path, expected in stages:
        print(f"\n[integration-long] [{stage_num}] {desc}...", flush=True)
        print(f"[integration-long] Sending request: GET {path}", flush=True)
        time.sleep(1.0)
        response = client.get(path)
        print(f"[integration-long] Received status {response.status_code}: {response.json()}", flush=True)
        assert response.status_code == 200
        if expected is not None:
            assert response.json()["result"] == expected

    print("\n" + "=" * 65, flush=True)
    print("[integration-long] Long-running test completed successfully (5/5 stages passed)!", flush=True)
    print("=" * 65 + "\n", flush=True)


class TestCalculatorApiService:
    """Integration test suite class verifying FastAPI calculator endpoints."""

    def test_health_check_status_code(self):
        print("\n[class-test] TestCalculatorApiService.test_health_check_status_code")
        response = client.get("/health")
        print(f"[class-test] Status Code: {response.status_code}")
        assert response.status_code == 200

    def test_health_check_payload_structure(self):
        print("\n[class-test] TestCalculatorApiService.test_health_check_payload_structure")
        response = client.get("/health")
        data = response.json()
        print(f"[class-test] Response Body: {data}")
        assert data.get("status") == "ok"
        assert data.get("service") == "sample-target-repo"

    def test_add_positive_integers(self):
        print("\n[class-test] TestCalculatorApiService.test_add_positive_integers: 10 + 25")
        response = client.get("/calculate/add?a=10&b=25")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 35.0}

    def test_add_negative_integers(self):
        print("\n[class-test] TestCalculatorApiService.test_add_negative_integers: -10 + -20")
        response = client.get("/calculate/add?a=-10&b=-20")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": -30.0}

    def test_add_mixed_sign_numbers(self):
        print("\n[class-test] TestCalculatorApiService.test_add_mixed_sign_numbers: 100 + -40")
        response = client.get("/calculate/add?a=100&b=-40")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 60.0}

    def test_add_zero_identity(self):
        print("\n[class-test] TestCalculatorApiService.test_add_zero_identity: 55 + 0")
        response = client.get("/calculate/add?a=55&b=0")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 55.0}

    def test_add_floating_point_numbers(self):
        print("\n[class-test] TestCalculatorApiService.test_add_floating_point_numbers: 12.3 + 7.7")
        response = client.get("/calculate/add?a=12.3&b=7.7")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json()["result"] == pytest.approx(20.0)

    def test_add_large_numbers(self):
        print("\n[class-test] TestCalculatorApiService.test_add_large_numbers: 1000000 + 2000000")
        response = client.get("/calculate/add?a=1000000&b=2000000")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 3000000.0}

    def test_divide_exact_integers(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_exact_integers: 80 / 4")
        response = client.get("/calculate/divide?a=80&b=4")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 20.0}

    def test_divide_fractional_result(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_fractional_result: 9 / 2")
        response = client.get("/calculate/divide?a=9&b=2")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 4.5}

    def test_divide_negative_numerator(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_negative_numerator: -45 / 9")
        response = client.get("/calculate/divide?a=-45&b=9")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": -5.0}

    def test_divide_negative_denominator(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_negative_denominator: 45 / -9")
        response = client.get("/calculate/divide?a=45&b=-9")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": -5.0}

    def test_divide_both_negative(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_both_negative: -45 / -9")
        response = client.get("/calculate/divide?a=-45&b=-9")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 5.0}

    def test_divide_zero_numerator(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_zero_numerator: 0 / 15")
        response = client.get("/calculate/divide?a=0&b=15")
        print(f"[class-test] Result: {response.json()}")
        assert response.status_code == 200
        assert response.json() == {"result": 0.0}

    def test_divide_by_zero_status_code(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_by_zero_status_code: 25 / 0")
        response = client.get("/calculate/divide?a=25&b=0")
        print(f"[class-test] Status Code: {response.status_code}, Body: {response.json()}")
        assert response.status_code == 400

    def test_divide_by_zero_error_message(self):
        print("\n[class-test] TestCalculatorApiService.test_divide_by_zero_error_message: checking detail")
        response = client.get("/calculate/divide?a=25&b=0")
        print(f"[class-test] Error Detail: {response.json().get('detail')}")
        assert response.json() == {"detail": "Cannot divide by zero"}

