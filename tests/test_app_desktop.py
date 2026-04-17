import importlib
import sys
from pathlib import Path


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_DESKTOP_MODE", "1")
    monkeypatch.setenv("RESUME_SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "resumes"))

    for module_name in ["app"]:
        sys.modules.pop(module_name, None)

    app_module = importlib.import_module("app")
    Path(app_module.settings["output_directory"]).mkdir(parents=True, exist_ok=True)
    return app_module


def test_settings_are_loaded_from_desktop_settings_path(tmp_path, monkeypatch):
    app_module = load_app(tmp_path, monkeypatch)

    assert str(tmp_path / "settings.json") == str(app_module.SETTINGS_FILE)
    assert app_module.settings["output_directory"] == str(tmp_path / "resumes")


def test_pdf_download_serves_inline_pdf_from_output_directory(tmp_path, monkeypatch):
    app_module = load_app(tmp_path, monkeypatch)
    pdf_path = Path(app_module.settings["output_directory"]) / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n% sample\n")

    with app_module.app.test_client() as client:
        response = client.get(
            "/api/download",
            query_string={"path": str(pdf_path), "preview": "true"},
        )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("inline")
    assert response.data.startswith(b"%PDF")


def test_pdf_download_rejects_paths_outside_output_directory(tmp_path, monkeypatch):
    app_module = load_app(tmp_path, monkeypatch)
    outside_pdf = tmp_path / "outside.pdf"
    outside_pdf.write_bytes(b"%PDF-1.7\n")

    with app_module.app.test_client() as client:
        response = client.get(
            "/api/download",
            query_string={"path": str(outside_pdf), "preview": "true"},
        )

    assert response.status_code == 403


def test_open_folder_rejects_paths_outside_output_directory(tmp_path, monkeypatch):
    app_module = load_app(tmp_path, monkeypatch)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    with app_module.app.test_client() as client:
        response = client.post("/api/open-folder", json={"path": str(outside_dir)})

    assert response.status_code == 403
