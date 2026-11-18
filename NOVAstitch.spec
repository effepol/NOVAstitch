# -*- mode: python ; coding: utf-8 -*-
# Ricetta di PyInstaller per NOVAstitch (cartella, NON file unico: serve per la
# licenza LGPL di Qt, che deve restare sostituibile, e genera meno falsi allarmi
# degli antivirus).
import sys

win = sys.platform == "win32"

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[("risorse", "risorse")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NOVAstitch",
    debug=False,
    strip=False,
    upx=False,                      # UPX aumenta i falsi positivi degli antivirus
    console=False,                  # nessuna finestra nera
    icon="risorse/icona.ico" if win else None,
    version="version_info.txt" if win else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="NOVAstitch",
)
