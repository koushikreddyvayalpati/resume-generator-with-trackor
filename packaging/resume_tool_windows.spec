# Build from the repository root on Windows:
#   pyinstaller --clean --noconfirm packaging\resume_tool_windows.spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path.cwd()


datas = [
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "static"), "static"),
    (str(ROOT / "config" / "base_resume.json"), "config"),
    (str(ROOT / "resumes" / "Tharun Manikonda Resume.docx"), "resumes"),
]

libreoffice_portable = ROOT / "vendor" / "LibreOfficePortable"
libreoffice_program = ROOT / "vendor" / "libreoffice"

if libreoffice_portable.exists():
    datas.append((str(libreoffice_portable), "LibreOfficePortable"))
elif libreoffice_program.exists():
    datas.append((str(libreoffice_program), "libreoffice"))


a = Analysis(
    [str(ROOT / "desktop_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("docx") + ["tkinter", "waitress"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ResumeTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ResumeTool",
)
