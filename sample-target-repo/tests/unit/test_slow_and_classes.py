import sys
import time
import pytest


class TestClassWithSlowSetup:
    """Demonstrates class-level fixture with slow setup and teardown for timer verification."""

    @classmethod
    def setup_class(cls):
        print("\n\x1b[34m[setup_class]\x1b[0m Starting heavy class resource initialization...", flush=True)
        time.sleep(0.6)
        cls.shared_resource = {"connected": True, "pool_size": 10}
        print("\x1b[32m[setup_class]\x1b[0m Heavy class resources initialized successfully.", flush=True)

    @classmethod
    def teardown_class(cls):
        print("\n\x1b[34m[teardown_class]\x1b[0m Tearing down heavy class resources...", flush=True)
        time.sleep(0.3)
        cls.shared_resource = None
        print("\x1b[32m[teardown_class]\x1b[0m Heavy class resources released.", flush=True)

    def test_query_fast_one(self):
        """Verifies fast query 1 against the initialized class resource."""
        print("[method-1] Executing query 1 against shared resource...", flush=True)
        assert self.shared_resource["connected"] is True
        assert self.shared_resource["pool_size"] == 10

    def test_query_fast_two(self):
        """Verifies fast query 2 against the initialized class resource."""
        print("[method-2] Executing query 2 against shared resource...", flush=True)
        assert self.shared_resource["pool_size"] >= 5


class TestClassWithMethodFixtures:
    """Verifies per-method setup and teardown timing and output capture."""

    @pytest.fixture(autouse=True)
    def method_timer(self):
        print("\n[fixture] Method pre-setup initialized", flush=True)
        yield
        print("[fixture] Method post-teardown completed", flush=True)

    def test_fixture_case_alpha(self):
        print("[test-alpha] Running alpha case", flush=True)
        assert 1 + 1 == 2

    def test_fixture_case_beta(self):
        print("[test-beta] Running beta case", flush=True)
        assert 2 * 3 == 6


@pytest.mark.slow
def test_long_running_pipeline():
    """Simulates a multi-phase long-running pipeline with console progress."""
    print("\n" + "=" * 50, flush=True)
    print("\x1b[1;36m[pipeline]\x1b[0m Starting 3-phase simulation...", flush=True)
    phases = [
        ("Phase 1: Ingesting dataset chunks", 0.4),
        ("Phase 2: Computing statistical moments", 0.4),
        ("Phase 3: Validating schema compliance", 0.4),
    ]
    for desc, delay in phases:
        print(f"  -> {desc}...", flush=True)
        time.sleep(delay)
    print("\x1b[1;32m[pipeline]\x1b[0m All 3 phases completed successfully!", flush=True)
    print("=" * 50 + "\n", flush=True)
    assert True


def test_mixed_stdout_stderr_streams():
    """Outputs both to stdout and stderr to verify stream capture."""
    print("[stdout] Normal information message", file=sys.stdout, flush=True)
    print("[stderr] Warning: sample non-fatal diagnostics", file=sys.stderr, flush=True)
    assert True


@pytest.mark.skip(reason="Demonstrating skipped test indicator in PytestDeck tree")
def test_intentionally_skipped_case():
    """This test is skipped unconditionally."""
    pass


@pytest.mark.xfail(reason="Demonstrating xfail (expected failure) status")
def test_intentionally_xfailed_case():
    """This test is marked as expected to fail."""
    assert False, "Expected failure occurred as designed"
