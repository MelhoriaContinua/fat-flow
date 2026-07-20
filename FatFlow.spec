# -*- mode: python ; coding: utf-8 -*-

# === Gera data/.env.encrypted a partir de data/.env (SOMENTE no build) ===
# O data/.env (texto puro) fica apenas na maquina de desenvolvimento e nunca e
# versionado nem embutido no executavel. Aqui ele e criptografado e o resultado
# (.env.encrypted) e o unico arquivo de credenciais empacotado no .exe.
import os
import sys as _sys

_CORE_DIR = os.path.join(os.getcwd(), 'core')
if _CORE_DIR not in _sys.path:
    _sys.path.insert(0, _CORE_DIR)

from encrypt_env import encrypt_env_file
encrypt_env_file()
print(">> [build] data/.env.encrypted gerado a partir de data/.env")


a = Analysis(
    ['core\\app_gui.py'],
    pathex=['core'],
    binaries=[],
    datas=[
        # ATENCAO: nao empacotar 'data' inteira para nao incluir o .env em texto puro.
        ('data\\.env.encrypted', 'data'),
        ('data\\fatflow.key', 'data'),
        ('data\\Relacionamento_Culturas_Cultivares.xlsx', 'data'),
        ('img', 'img'),
        ('core\\data_processing.py', 'core'),
        ('core\\get_cultivares.py', 'core'),
        ('core\\scrap_oobj.py', 'core'),
    ],
    hiddenimports=[
        'webdriver_manager',
        # nomes top-level (o app importa 'get_cultivares'/'scrap_oobj' via pathex=['core'])
        'get_cultivares',
        'scrap_oobj',
        'data_processing',
        'core.data_processing',
        'core.get_cultivares',
        'core.scrap_oobj',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FatFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['img\\icon_desktop.ico'],
)