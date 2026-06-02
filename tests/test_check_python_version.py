import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "check_python_version.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_python_version", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_version_guard_accepts_python_310_and_newer() -> None:
    guard = load_module()

    assert guard.is_supported((3, 10, 0))
    assert guard.is_supported((3, 12, 1))


def test_python_version_guard_rejects_python_39() -> None:
    guard = load_module()

    assert not guard.is_supported((3, 9, 18))
    assert guard.format_version((3, 9, 18)) == "3.9.18"
