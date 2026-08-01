"""Chargement des tables de correspondance versions <-> loaders."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mapping"


def _load(name: str) -> dict:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _pack_format_table() -> dict[str, int]:
    return {k: v for k, v in _load("pack_format.json").items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def _loaders_table() -> dict[str, dict]:
    return {k: v for k, v in _load("loaders.json").items() if not k.startswith("_")}


def get_pack_format(version: str) -> int | None:
    """Renvoie le pack_format Minecraft pour une version donnee (ex: '1.20.1')."""
    for version_range, pack_format in _pack_format_table().items():
        bounds = version_range.split("-")
        low = bounds[0]
        high = bounds[1] if len(bounds) > 1 else bounds[0]
        if _version_in_range(version, low, high):
            return pack_format
    return None


def _version_key(v: str) -> tuple[int, ...]:
    return tuple(int(part) for part in v.split("."))


def _version_in_range(version: str, low: str, high: str) -> bool:
    try:
        v, lo, hi = _version_key(version), _version_key(low), _version_key(high)
    except ValueError:
        return False
    return lo <= v <= hi


def get_loader_info(loader: str) -> dict:
    return _loaders_table().get(loader, {})


def loaders_are_cross_compatible(source_loader: str, target_loader: str) -> bool:
    if source_loader == target_loader:
        return True
    info = get_loader_info(source_loader)
    return target_loader in info.get("cross_loader_compatible_with", [])


def loaders_have_partial_conversion(source_loader: str, target_loader: str) -> bool:
    """Manifest traduisible automatiquement, mais pas le code (ex: Forge <-> NeoForge)."""
    info = get_loader_info(source_loader)
    return target_loader in info.get("partial_manifest_conversion_with", [])
