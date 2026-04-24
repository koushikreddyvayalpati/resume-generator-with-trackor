import json
import platform
import subprocess
from pathlib import Path


def app_base_dir() -> Path:
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    return app_base_dir().joinpath(*parts)


def user_home() -> Path:
    return Path.home()


def default_output_dir() -> Path:
    return app_base_dir() / "resumes"


def settings_path() -> Path:
    return resource_path("config", "settings.json")


def load_json_file(path: Path, fallback: dict) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Warning: Could not load {path}: {exc}")
    return dict(fallback)


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def open_path(path: Path) -> None:
    target = str(path)
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
