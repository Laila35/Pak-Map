# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_path = Path('.').resolve()

def collect_tree(src_dir: Path, dest_dir: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for path in src_dir.rglob("*"):
        if path.is_file():
            relative = path.relative_to(src_dir)
            target_dir = Path(dest_dir) / relative.parent
            out.append((str(path), str(target_dir)))
    return out

datas = []
for src_dir, dest_dir in [
    (project_path / "map", "map"),
    (project_path / "ui", "ui"),
    (project_path / "boundaries", "boundaries"),
]:
    datas += collect_tree(src_dir, dest_dir)

env_file = project_path / ".env"
if env_file.exists():
    datas.append((str(env_file), "."))

hiddenimports = []

analysis = Analysis(
    [str(project_path / "main.py")],
    pathex=[str(project_path)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Pak-Map",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="Pak-Map",
)
