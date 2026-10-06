from pathlib import Path
from unittest.mock import patch

from infrastructure.storage_service import (
    get_pytestdeck_root,
    get_target_repo_name,
    get_target_storage_dir,
)


def test_get_pytestdeck_root_env_override(tmp_path, monkeypatch):
    custom_root = tmp_path / "custom_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(custom_root))
    assert get_pytestdeck_root() == custom_root.resolve()


def test_get_pytestdeck_root_finds_project_root():
    root = get_pytestdeck_root()
    assert (root / "backend").is_dir()


def test_get_target_repo_name(tmp_path):
    target_repo = tmp_path / "my_microservice"
    target_repo.mkdir()
    assert get_target_repo_name(target_repo) == "my_microservice"
    assert get_target_repo_name(str(target_repo)) == "my_microservice"


def test_get_target_storage_dir_never_touches_target_repo(tmp_path, monkeypatch):
    # Mock PytestDeck root to tmp_path / "pytestdeck_root"
    mock_app_root = tmp_path / "pytestdeck_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_app_root))

    # Create target repo
    target_repo = tmp_path / "external_repo"
    target_repo.mkdir()

    storage_dir = get_target_storage_dir(target_repo)

    # Must be under PytestDeck/.pytestdeck/<target_repo>/
    assert storage_dir == mock_app_root / ".pytestdeck" / "external_repo"
    assert storage_dir.exists()

    # PytestDeck root .pytestdeck has .gitignore
    gitignore = mock_app_root / ".pytestdeck" / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text(encoding="utf-8") == "*\n"

    # CRITICAL: Target repository must remain 100% clean and untouched
    assert list(target_repo.iterdir()) == []
    assert not (target_repo / ".pytestdeck").exists()


def test_get_target_storage_dir_fallback_on_os_error(tmp_path, monkeypatch):
    mock_app_root = tmp_path / "pytestdeck_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_app_root))

    real_mkdir = Path.mkdir

    def selective_mkdir(self, *args, **kwargs):
        if str(mock_app_root) in str(self):
            raise OSError("Read-only")
        return real_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", selective_mkdir):
        fallback = get_target_storage_dir("sample_repo")
        assert "pytestdeck" in str(fallback)
        assert fallback.name == "sample_repo"
