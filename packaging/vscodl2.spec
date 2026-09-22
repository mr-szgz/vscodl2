datas = [
    ("../LICENSE", "."),
    ("../Logo.png", "."),
    ("../THIRD_PARTY_NOTICES.md", "."),
]

gui = Analysis(
    ["gui_entry.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
gui.binaries = [
    entry for entry in gui.binaries
    if entry[0].lower() not in {"icuuc.dll", "icudt78.dll"}
]
gui_pyz = PYZ(gui.pure)
gui_exe = EXE(
    gui_pyz,
    gui.scripts,
    [],
    exclude_binaries=True,
    name="VSCODL2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

worker = Analysis(
    ["worker_entry.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
worker_pyz = PYZ(worker.pure)
worker_exe = EXE(
    worker_pyz,
    worker.scripts,
    [],
    exclude_binaries=True,
    name="VSCODL2-worker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    gui_exe,
    worker_exe,
    gui.binaries,
    gui.datas,
    worker.binaries,
    worker.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VSCODL2",
)
