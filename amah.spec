# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    # config.py lit system_prompt.txt au démarrage : sans lui, le .exe plantait
    datas=[('system_prompt.txt', '.')],
    # tools/__init__.py charge les outils par leur nom (importlib) : PyInstaller
    # ne les voit pas, d'où collect_submodules (games, webcam, code_tools...
    # manquaient dans l'ancienne liste écrite à la main).
    hiddenimports=collect_submodules('tools') + [
        'groq',
        'rich',
        'rich.console',
        'rich.panel',
        'ddgs',
        'docx',
        'fpdf',
        'pypdf',
        'psutil',
        'dotenv',
        'sqlite3',
        'tkinter',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'imaplib',
        'smtplib',
        'email',
        'email.mime.text',
        'email.header',
        'playwright',
        'playwright.sync_api',
        'greenlet',
        'openpyxl',
        'openpyxl.styles',
        'pyttsx3',
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'zipfile',
        'secrets',
        'socket',
        'tools.files',
        'tools.documents',
        'tools.search',
        'tools.system',
        'tools.memory',
        'tools.email_tool',
        'tools.browser',
        'tools.voice',
        'tools.notifications',
        'tools.excel',
        'tools.clipboard',
        'tools.utils',
        'tools.archive',
        'tools.image_tool',
        'tools.meteo',
        'tools.translator',
        'tools.qrcode_tool',
        'tools.voice_recognition',
        'tools.scheduler',
        'tools.stats',
        'tools.updater',
        'tools.license',
        'tools.computer_settings',
        'tools.youtube_tool',
        'tools.flight_finder',
        'tools.screen_vision',
        'tools.planner',
        'deep_translator',
        'qrcode',
        'speech_recognition',
        'bs4',
        'fitz',
        'pymupdf',
    ],
    hookspath=[],
    runtime_hooks=[],
    # SDK Amazon (~20 Mo) tiré par speech_recognition pour recognize_lex /
    # recognize_amazon, importé seulement dans ces fonctions ; Amah utilise
    # recognize_google.
    excludes=['boto3', 'botocore', 's3transfer'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Format dossier (onedir) : dist/Amah Agent/Amah Agent.exe + _internal/.
# En fichier unique, le .exe décompressait ~480 Mo dans %TEMP% à chaque
# lancement (~46 s de démarrage) ; ici les fichiers restent sur le disque.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Amah Agent',
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
    icon='amah.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Amah Agent',
)
