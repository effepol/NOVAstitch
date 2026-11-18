# -*- mode: python ; coding: utf-8 -*-
# Ricetta di PyInstaller per NOVAstitch su macOS (crea NOVAstitch.app).
# Architettura: variabile NOVA_ARCH = "universal2" oppure "arm64"/"x86_64"; se manca, quella del Mac.
import os

arch = os.environ.get("NOVA_ARCH") or None

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("risorse", "risorse"),
        ("LICENZA_it.txt", "."),
        ("LICENSE_en.txt", "."),
        ("licenze", "licenze"),
    ],
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
    upx=False,
    console=False,
    target_arch=arch,
    codesign_identity=None,         # niente firma a pagamento: la firma "ad hoc" la facciamo dopo
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="NOVAstitch",
)
app = BUNDLE(
    coll,
    name="NOVAstitch.app",
    icon="risorse/icona.icns",
    bundle_identifier="it.poletticentrocucito.novastitch",
    version="0.1",
    info_plist={
        "CFBundleName": "NOVAstitch",
        "CFBundleDisplayName": "NOVAstitch",
        "CFBundleShortVersionString": "0.1",
        "CFBundleVersion": "0.1",
        "NSHumanReadableCopyright": "Copyright (c) 2026 Poletti Centro Cucito",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": os.environ.get("NOVA_MINMAC", "14.0"),
        "LSApplicationCategoryType": "public.app-category.graphics-design",
    },
)
