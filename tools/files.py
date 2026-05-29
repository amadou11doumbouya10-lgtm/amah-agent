import os
import shutil
from pathlib import Path
from datetime import datetime

CATEGORIES = {
    "Images":        [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".raw"],
    "Vidéos":        [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
    "Audio":         [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    "Documents":     [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".pages"],
    "Tableurs":      [".xls", ".xlsx", ".csv", ".ods", ".numbers"],
    "Présentations": [".ppt", ".pptx", ".odp", ".key"],
    "Archives":      [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Code":          [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".sql", ".sh", ".bat", ".jsx", ".tsx", ".php", ".java", ".c", ".cpp", ".h"],
    "Exécutables":   [".exe", ".msi", ".apk", ".dmg", ".deb"],
}


def list_files(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Dossier introuvable : {path}"}

    items = []
    for item in sorted(p.iterdir()):
        try:
            stat = item.stat()
            size = stat.st_size
            items.append({
                "nom":          item.name,
                "type":         "dossier" if item.is_dir() else "fichier",
                "extension":    item.suffix.lower() if item.is_file() else "",
                "taille":       _format_size(size),
                "modifié":      datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
            })
        except PermissionError:
            items.append({"nom": item.name, "type": "accès refusé"})

    return {
        "chemin":  str(p),
        "total":   len(items),
        "fichiers": [i for i in items if i.get("type") == "fichier"],
        "dossiers": [i for i in items if i.get("type") == "dossier"],
    }


def organize_folder(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Dossier introuvable : {path}"}

    moved = {}
    skipped = []
    errors = []

    for file in p.iterdir():
        if not file.is_file():
            continue

        ext = file.suffix.lower()
        category = next((cat for cat, exts in CATEGORIES.items() if ext in exts), None)

        if not category:
            skipped.append(file.name)
            continue

        dest_folder = p / category
        dest_folder.mkdir(exist_ok=True)
        dest = dest_folder / file.name

        if dest.exists():
            stem, suffix = file.stem, file.suffix
            counter = 1
            while dest.exists():
                dest = dest_folder / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            shutil.move(str(file), str(dest))
            moved.setdefault(category, []).append(file.name)
        except Exception as e:
            errors.append(f"{file.name}: {e}")

    total = sum(len(v) for v in moved.values())
    return {
        "success":       True,
        "total_déplacés": total,
        "par_catégorie": {k: len(v) for k, v in moved.items()},
        "non_classés":   skipped,
        "erreurs":       errors,
    }


def find_files(path: str, pattern: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Dossier introuvable : {path}"}

    results = []
    try:
        for match in p.rglob(pattern):
            try:
                stat = match.stat()
                results.append({
                    "nom":       match.name,
                    "chemin":    str(match),
                    "taille":    _format_size(stat.st_size),
                    "modifié":   datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                })
            except Exception:
                results.append({"nom": match.name, "chemin": str(match)})
    except Exception as e:
        return {"error": str(e)}

    return {
        "pattern":   pattern,
        "dossier":   str(p),
        "trouvés":   len(results),
        "fichiers":  results[:50],
    }


def move_file(source: str, destination: str) -> dict:
    src = Path(source).expanduser()
    dst = Path(destination).expanduser()

    if not src.exists():
        return {"error": f"Fichier source introuvable : {source}"}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"success": True, "de": str(src), "vers": str(dst)}
    except Exception as e:
        return {"error": str(e)}


def create_folder(path: str) -> dict:
    p = Path(path).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
        return {"success": True, "chemin": str(p)}
    except Exception as e:
        return {"error": str(e)}


def read_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Fichier introuvable : {path}"}
    if not p.is_file():
        return {"error": "Ce chemin est un dossier, pas un fichier."}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 8000:
            content = content[:8000] + "\n\n[... contenu tronqué à 8000 caractères ...]"
        return {"success": True, "nom": p.name, "contenu": content}
    except Exception as e:
        return {"error": str(e)}


def get_folder_info(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"Dossier introuvable : {path}"}

    total_size = 0
    total_files = 0
    extensions = {}

    try:
        for file in p.rglob("*"):
            if file.is_file():
                try:
                    size = file.stat().st_size
                    total_size += size
                    total_files += 1
                    ext = file.suffix.lower() or "(sans extension)"
                    extensions[ext] = extensions.get(ext, 0) + 1
                except Exception:
                    pass
    except Exception as e:
        return {"error": str(e)}

    top_ext = sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "chemin":          str(p),
        "taille_totale":   _format_size(total_size),
        "nombre_fichiers": total_files,
        "top_extensions":  dict(top_ext),
    }


def _format_size(size: int) -> str:
    for unit in ["o", "Ko", "Mo", "Go"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
