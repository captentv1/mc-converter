"""Detection automatique du loader et de la version source d'un fichier.

But : l'utilisateur envoie juste un mod/resource pack, sans avoir a
connaitre/retaper sa version et son loader — l'info est deja dans le
fichier (manifest du mod, pack.mcmeta). Detection uniquement, aucune
modification du fichier source.
"""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from core import mapping
from core.job import Loader
from core.converters.mod_converter import ALL_MANIFESTS

VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")


@dataclass
class Detection:
    loader: Loader | None = None
    version: str | None = None
    notes: list[str] = field(default_factory=list)


def detect_mod(jar_path: Path) -> Detection:
    with zipfile.ZipFile(jar_path, "r") as z:
        names = set(z.namelist())
        for loader, manifest_name in ALL_MANIFESTS.items():
            if manifest_name not in names:
                continue
            raw = z.read(manifest_name)
            version = _extract_mc_version(manifest_name, raw)
            notes = [f"Loader detecte via {manifest_name}"]
            if version is None:
                notes.append("Version Minecraft non trouvee dans le manifest ; a saisir manuellement.")
            return Detection(loader=loader, version=version, notes=notes)
    return Detection(notes=["Aucun manifest de loader connu trouve dans ce jar."])


def detect_modpack(folder: Path) -> Detection:
    """Un modpack n'a pas de manifest a lui : on echantillonne le premier
    .jar de mods/ et on suppose que tout le pack partage le meme loader
    (vrai dans l'immense majorite des cas — un launcher ne melange pas
    les loaders au sein d'une meme instance)."""
    mods_dir = folder / "mods"
    if not mods_dir.is_dir():
        return Detection(notes=["Dossier 'mods' introuvable."])
    jars = sorted(mods_dir.glob("*.jar"))
    if not jars:
        return Detection(notes=["Aucun .jar trouve dans mods/."])
    result = detect_mod(jars[0])
    result.notes = [f"Deduit de {jars[0].name} (echantillon)"] + result.notes
    return result


def detect_resourcepack(path: Path) -> Detection:
    if path.is_dir():
        mcmeta_path = path / "pack.mcmeta"
        if not mcmeta_path.exists():
            return Detection(notes=["pack.mcmeta introuvable."])
        data = json.loads(mcmeta_path.read_text(encoding="utf-8"))
    else:
        with zipfile.ZipFile(path, "r") as z:
            if "pack.mcmeta" not in z.namelist():
                return Detection(notes=["pack.mcmeta introuvable dans l'archive."])
            data = json.loads(z.read("pack.mcmeta").decode("utf-8"))

    fmt = data.get("pack", {}).get("pack_format")
    if fmt is None:
        return Detection(notes=["Aucun 'pack_format' dans pack.mcmeta."])

    version_range = mapping.get_version_range_for_pack_format(fmt)
    if version_range is None:
        return Detection(notes=[f"pack_format {fmt} inconnu de data/mapping/pack_format.json."])
    return Detection(version=version_range, notes=[f"pack_format {fmt} -> versions {version_range}"])


def _extract_mc_version(manifest_name: str, raw: bytes) -> str | None:
    if manifest_name.endswith(".json"):
        data = json.loads(raw.decode("utf-8"))
        dependency = data.get("depends", {}).get("minecraft")
    else:
        text = raw.decode("utf-8")
        match = re.search(r'modId\s*=\s*"minecraft"[\s\S]*?versionRange\s*=\s*"([^"]*)"', text)
        dependency = match.group(1) if match else None

    if not dependency:
        return None
    version_match = VERSION_RE.search(dependency)
    return version_match.group(0) if version_match else None
