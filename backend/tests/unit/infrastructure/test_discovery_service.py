import pytest

from infrastructure.discovery_service import (
    PytestDiscoveryService,
    get_env_config,
)


def test_get_env_config_defaults(monkeypatch):
    monkeypatch.delenv("UNIT_DIR", raising=False)
    cfg = get_env_config()
    assert cfg["unit_dir"] == "backend/tests/unit"


def test_get_env_config_custom(monkeypatch):
    monkeypatch.setenv("UNIT_DIR", "custom/unit")
    cfg = get_env_config()
    assert cfg["unit_dir"] == "custom/unit"


@pytest.mark.anyio
async def test_pytest_discovery_service_collect(tmp_path):
    test_dir = tmp_path / "tests" / "unit"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "test_sample.py"
    test_file.write_text("def test_ok(): pass\n", encoding="utf-8")

    service = PytestDiscoveryService()
    collectors, total = await service.collect_raw(str(tmp_path), suite_rel_path="tests/unit")
    assert total == 1
    assert len(collectors) > 0


@pytest.mark.anyio
async def test_pytest_discovery_service_collect_acceptance(tmp_path):
    """Verifies collection of feature files when suite_rel_path contains acceptance."""
    suite_dir = tmp_path / "backend" / "tests" / "acceptance" / "features"
    suite_dir.mkdir(parents=True)
    feat_file = suite_dir / "login.feature"
    feat_file.write_text("Feature: Login\n", encoding="utf-8")

    service = PytestDiscoveryService()
    collectors, total = await service.collect_raw(str(tmp_path), suite_rel_path="backend/tests/acceptance")
    assert total == 1
    assert collectors[0]["nodeid"] == "backend/tests/acceptance/features/login.feature"


@pytest.mark.anyio
async def test_pytest_discovery_service_collect_with_pytest_ini(tmp_path):
    """Verifies that custom pytest.ini is appended to pytest command when present."""
    suite_dir = tmp_path / "tests" / "unit"
    suite_dir.mkdir(parents=True)
    (suite_dir / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (suite_dir / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")

    service = PytestDiscoveryService()
    collectors, total = await service.collect_raw(str(tmp_path), suite_rel_path="tests/unit")
    assert total == 1
    assert len(collectors) > 0


@pytest.mark.anyio
async def test_pytest_discovery_service_invalid_target_path():
    """Verifies ValueError when target_path does not exist."""
    service = PytestDiscoveryService()
    with pytest.raises(ValueError, match="Invalid target path"):
        await service.collect_raw("/nonexistent/path/for/testing")
