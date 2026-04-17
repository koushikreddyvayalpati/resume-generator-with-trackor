import json
import os
import platform
import subprocess
import sys
from pathlib import Path


APP_NAME = "ResumeTool"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).joinpath(*parts)
    return app_base_dir().joinpath(*parts)


def user_home() -> Path:
    return Path.home()


def app_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        base = Path(root) if root else user_home() / "AppData" / "Local"
        return base / APP_NAME
    if system == "Darwin":
        return user_home() / "Library" / "Application Support" / APP_NAME
    return Path(os.getenv("XDG_DATA_HOME", user_home() / ".local" / "share")) / APP_NAME


def default_output_dir() -> Path:
    if platform.system() == "Windows":
        return user_home() / "Documents" / "Resumes"
    return app_base_dir() / "resumes"


def settings_path() -> Path:
    env_path = os.getenv("RESUME_SETTINGS_PATH")
    if env_path:
        return Path(env_path)
    if is_frozen() or os.getenv("RESUME_DESKTOP_MODE") == "1":
        return app_data_dir() / "settings.json"
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
    if system == "Windows":
        os.startfile(target)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
