import zipfile
import os
from pathlib import Path
from datetime import datetime


def zip_files(files: list, output: str = None) -> dict:
    """
    Compresse une liste de fichiers en un fichier ZIP.
    files : liste de chemins
    output : chemin du ZIP de sortie (optionnel, généré automatiquement)
    """
    try:
        if not output:
            name   = datetime.now().strftime("archive_%Y%m%d_%H%M%S.zip")
            output = str(Path.home() / "Documents" / name)

        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        added = []
        with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                p = Path(f).expanduser()
                if p.is_file():
                    zf.write(str(p), p.name)
                    added.append(p.name)
                elif p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            zf.write(str(child), str(child.relative_to(p.parent)))
                            added.append(str(child.relative_to(p.parent)))

        size = out_path.stat().st_size
        return {
            "success":   True,
            "archive":   str(out_path),
            "fichiers":  added,
            "total":     len(added),
            "taille":    f"{size / 1024:.1f} Ko",
        }
    except Exception as e:
        return {"error": str(e)}


def unzip_file(path: str, destination: str = None) -> dict:
    """Extrait le contenu d'un fichier ZIP."""
    try:
        p    = Path(path).expanduser()
        dest = Path(destination) if destination else p.parent / p.stem
        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(p), "r") as zf:
            names = zf.namelist()
            zf.extractall(str(dest))

        return {
            "success":     True,
            "extrait_dans": str(dest),
            "fichiers":    names,
            "total":       len(names),
        }
    except Exception as e:
        return {"error": str(e)}


def list_archive(path: str) -> dict:
    """Liste le contenu d'un fichier ZIP sans l'extraire."""
    try:
        p = Path(path).expanduser()
        with zipfile.ZipFile(str(p), "r") as zf:
            infos = [
                {"nom": i.filename, "taille": f"{i.file_size / 1024:.1f} Ko"}
                for i in zf.infolist()
            ]
        return {"success": True, "archive": p.name, "contenu": infos, "total": len(infos)}
    except Exception as e:
        return {"error": str(e)}
