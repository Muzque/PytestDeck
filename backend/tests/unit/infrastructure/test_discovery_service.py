import pytest

from infrastructure.discovery_service import (
    PytestDiscoveryService,
    parse_pytestdeck_config,
)


def test_parse_pytestdeck_config_nonexistent(tmp_path):
    cfg = parse_pytestdeck_config(tmp_path / "nonexistent.toml")
    assert cfg == {}


def test_parse_pytestdeck_config_valid(tmp_path):
    toml_file = tmp_path / "pytestdeck.toml"
    toml_file.write_text('[pytestdeck]\nunit_dir = "tests/unit"\n', encoding="utf-8")
    cfg = parse_pytestdeck_config(toml_file)
    assert cfg.get("unit_dir") == "tests/unit"


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
