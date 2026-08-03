import json
import zipfile

from core import detection
from core.job import Loader


def _make_zip(path, entries: dict):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)


def test_detect_mod_fabric(tmp_path):
    jar = tmp_path / "mod.jar"
    _make_zip(jar, {
        "fabric.mod.json": json.dumps({"id": "mymod", "depends": {"minecraft": ">=1.20.1"}}),
    })

    result = detection.detect_mod(jar)

    assert result.loader == Loader.FABRIC
    assert result.version == "1.20.1"


def test_detect_mod_neoforge_from_version_range(tmp_path):
    jar = tmp_path / "mod.jar"
    toml = """modLoader="javafml"
[[dependencies.mymod]]
    modId="minecraft"
    versionRange="[1.21.1,1.22)"
"""
    _make_zip(jar, {"META-INF/neoforge.mods.toml": toml})

    result = detection.detect_mod(jar)

    assert result.loader == Loader.NEOFORGE
    assert result.version == "1.21.1"


def test_detect_mod_no_manifest_returns_empty(tmp_path):
    jar = tmp_path / "mod.jar"
    _make_zip(jar, {"com/example/Mod.class": b"\xca\xfe\xba\xbe"})

    result = detection.detect_mod(jar)

    assert result.loader is None
    assert result.notes


def test_detect_resourcepack_from_pack_format(tmp_path):
    pack = tmp_path / "pack.zip"
    _make_zip(pack, {"pack.mcmeta": json.dumps({"pack": {"pack_format": 15, "description": "t"}})})

    result = detection.detect_resourcepack(pack)

    assert result.version == "1.20-1.20.1"
