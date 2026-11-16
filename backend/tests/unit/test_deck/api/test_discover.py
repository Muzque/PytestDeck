from pathlib import Path

import pytest
from fastapi import HTTPException

from test_deck.api.discover import (
    DiscoverRequest,
    TestDetailRequest,
    discover_tests,
    get_test_detail_endpoint,
)


@pytest.mark.anyio
async def test_discover_and_detail_endpoints(tmp_path: Path):
    unit_dir = tmp_path / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    test_file = unit_dir / "test_sample.py"
    test_file.write_text(
        'def test_hello():\n    """Sample docstring."""\n    assert 1 == 1\n',
        encoding="utf-8",
    )

    disc = await discover_tests(
        DiscoverRequest(target_path=str(tmp_path), suite_rel_path="tests/unit")
    )
    assert disc["suite"] == "tests/unit"
    assert "tree" in disc

    detail = await get_test_detail_endpoint(
        TestDetailRequest(
            target_path=str(tmp_path),
            node_id="tests/unit/test_sample.py::test_hello",
        )
    )
    assert detail["name"] == "test_hello"

    with pytest.raises(HTTPException) as exc_info:
        await discover_tests(
            DiscoverRequest(target_path="/nonexistent/path/xyz", suite_rel_path="tests/unit")
        )
    assert exc_info.value.status_code == 400
