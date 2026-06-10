import json
import os
import re
import urllib.parse
import urllib.request
import webbrowser
import winreg
from pathlib import Path


def _steam_install_path() -> str | None:
    """Trouve le chemin d'installation de Steam via le registre Windows."""
    candidates = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Valve\Steam",            "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam",            "InstallPath"),
    ]
    for hive, subkey, value_name in candidates:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                path, _ = winreg.QueryValueEx(key, value_name)
                if path:
                    return path.replace("/", "\\")
        except OSError:
            continue
    return None


def _epic_launcher_path() -> str | None:
    """Trouve l'exe d'Epic Games Launcher dans les emplacements standards."""
    for env_var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_var)
        if not base:
            continue
        exe = Path(base) / "Epic Games" / "Launcher" / "Portal" / "Binaries" / "Win32" / "EpicGamesLauncher.exe"
        if exe.exists():
            return str(exe)
    return None


def _parse_acf(path: Path) -> dict | None:
    """Extrait appid + nom d'un fichier appmanifest_*.acf."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    appid = re.search(r'"appid"\s*"(\d+)"', text)
    name  = re.search(r'"name"\s*"([^"]+)"', text)
    if appid and name:
        return {"appid": appid.group(1), "name": name.group(1)}
    return None


def _steam_library_folders(steam_path: Path) -> list[Path]:
    """Liste tous les dossiers steamapps (bibliotheque principale + additionnelles)."""
    folders = [steam_path / "steamapps"]
    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        text = vdf.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'"path"\s*"([^"]+)"', text):
            extra = Path(m.group(1).replace("\\\\", "\\")) / "steamapps"
            if extra not in folders:
                folders.append(extra)
    return folders


def open_steam() -> dict:
    """Ouvre l'application Steam."""
    steam_path = _steam_install_path()
    if steam_path:
        exe = Path(steam_path) / "steam.exe"
        if exe.exists():
            try:
                os.startfile(str(exe))
                return {"success": True, "message": "Steam lance."}
            except Exception as e:
                return {"error": str(e)}
    try:
        os.startfile("steam://open/main")
        return {"success": True, "message": "Steam lance."}
    except Exception:
        return {"error": "Steam introuvable sur ce PC. Telecharge-le sur store.steampowered.com"}


def open_epic_games() -> dict:
    """Ouvre Epic Games Launcher."""
    exe = _epic_launcher_path()
    if exe:
        try:
            os.startfile(exe)
            return {"success": True, "message": "Epic Games Launcher lance."}
        except Exception as e:
            return {"error": str(e)}
    try:
        os.startfile("com.epicgames.launcher://apps")
        return {"success": True, "message": "Epic Games Launcher lance."}
    except Exception:
        return {"error": "Epic Games Launcher introuvable sur ce PC. Telecharge-le sur store.epicgames.com/download"}


def list_installed_steam_games() -> dict:
    """Liste les jeux Steam installes (lit les fichiers .acf de chaque bibliotheque)."""
    steam_path = _steam_install_path()
    if not steam_path:
        return {"error": "Steam introuvable sur ce PC."}

    games = []
    for folder in _steam_library_folders(Path(steam_path)):
        if not folder.exists():
            continue
        for acf in folder.glob("appmanifest_*.acf"):
            game = _parse_acf(acf)
            if game:
                games.append(game)

    return {"success": True, "total": len(games), "jeux": games}


def launch_game_steam(game_name: str) -> dict:
    """Lance un jeu Steam deja installe (correspondance partielle sur le nom)."""
    result = list_installed_steam_games()
    if "error" in result:
        return result

    name_lower = game_name.lower()
    match = next((g for g in result["jeux"] if name_lower in g["name"].lower()), None)
    if not match:
        return {"error": f"Jeu '{game_name}' non trouve parmi les jeux installes."}

    try:
        os.startfile(f"steam://rungameid/{match['appid']}")
        return {"success": True, "jeu": match["name"], "appid": match["appid"]}
    except Exception as e:
        return {"error": str(e)}


def search_game_on_steam(game_name: str) -> dict:
    """Ouvre la recherche Steam Store pour un jeu dans le navigateur."""
    url = f"https://store.steampowered.com/search/?term={urllib.parse.quote(game_name)}"
    try:
        webbrowser.open(url)
        return {"success": True, "url": url, "recherche": game_name}
    except Exception as e:
        return {"error": str(e)}


def install_game_steam(game_name: str) -> dict:
    """Cherche un jeu sur le Steam Store, ouvre sa page et lance son installation si Steam est present."""
    try:
        search_url = (
            "https://store.steampowered.com/api/storesearch/"
            f"?term={urllib.parse.quote(game_name)}&cc=fr&l=french"
        )
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("items", [])
        if not items:
            return {"error": f"Aucun jeu trouve pour '{game_name}' sur le Steam Store."}

        game     = items[0]
        appid    = game["id"]
        store_url = f"https://store.steampowered.com/app/{appid}"
        webbrowser.open(store_url)

        if _steam_install_path():
            try:
                os.startfile(f"steam://install/{appid}")
            except Exception:
                pass

        return {"success": True, "jeu": game["name"], "appid": appid, "url": store_url}
    except Exception as e:
        return {"error": str(e)}
