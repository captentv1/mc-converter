import json
import zipfile

import pytest

from core.job import ConversionJob, JobType, Loader, Status
from core.orchestrator import CoreEngine

FORGE_TOML = """modLoader="javafml"
loaderVersion="[47,)"
license="MIT"

[[mods]]
modId="myforgemod"
version="1.0"

[[dependencies.myforgemod]]
    modId="forge"
    mandatory=true
    versionRange="[47,)"
    ordering="NONE"
    side="BOTH"

[[dependencies.myforgemod]]
    modId="minecraft"
    mandatory=true
    versionRange="[1.19.2,1.20)"
    ordering="NONE"
    side="BOTH"
"""


@pytest.fixture
def engine():
    return CoreEngine()


def _make_zip(path, entries: dict):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)


def test_resourcepack_bumps_pack_format(tmp_path, engine):
    src = tmp_path / "pack.zip"
    _make_zip(src, {"pack.mcmeta": json.dumps({"pack": {"pack_format": 9, "description": "t"}})})

    job = ConversionJob(
        type=JobType.RESOURCEPACK, source_version="1.19.2", target_version="1.20.1",
        input_path=src, output_path=tmp_path / "out.zip",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.OK
    with zipfile.ZipFile(job.output_path) as z:
        assert json.loads(z.read("pack.mcmeta"))["pack"]["pack_format"] == 15


def test_mod_same_loader_bumps_minecraft_dependency(tmp_path, engine):
    src = tmp_path / "mymod.jar"
    _make_zip(src, {
        "fabric.mod.json": json.dumps({"id": "mymod", "version": "1.0", "depends": {"minecraft": ">=1.19.2"}}),
    })

    job = ConversionJob(
        type=JobType.MOD, source_version="1.19.2", target_version="1.20.1",
        source_loader=Loader.FABRIC, target_loader=Loader.FABRIC,
        input_path=src, output_path=tmp_path / "out.jar",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.OK
    with zipfile.ZipFile(job.output_path) as z:
        assert json.loads(z.read("fabric.mod.json"))["depends"]["minecraft"] == ">=1.20.1"


def test_mod_forge_to_neoforge_translates_manifest_but_flags_code(tmp_path, engine):
    src = tmp_path / "forgemod.jar"
    _make_zip(src, {
        "META-INF/mods.toml": FORGE_TOML,
        "com/example/MyForgeMod.class": b"\xca\xfe\xba\xbe" + b"net/minecraftforge/fml/common/Mod" * 3,
    })

    job = ConversionJob(
        type=JobType.MOD, source_version="1.19.2", target_version="1.20.1",
        source_loader=Loader.FORGE, target_loader=Loader.NEOFORGE,
        input_path=src, output_path=tmp_path / "out.jar",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.PARTIAL
    assert job.report.unsupported, "le code non porte doit etre signale"
    with zipfile.ZipFile(job.output_path) as z:
        names = z.namelist()
        assert "META-INF/neoforge.mods.toml" in names
        assert "META-INF/mods.toml" not in names
        toml_text = z.read("META-INF/neoforge.mods.toml").decode()
        assert 'modId="neoforge"' in toml_text
        assert "[1.20.1,)" in toml_text


def test_mod_forge_to_fabric_is_reported_unsupported_with_analysis(tmp_path, engine):
    src = tmp_path / "forgemod.jar"
    _make_zip(src, {
        "META-INF/mods.toml": FORGE_TOML,
        "com/example/MyForgeMod.class": b"\xca\xfe\xba\xbe" + b"net/minecraftforge/fml/common/Mod",
    })

    job = ConversionJob(
        type=JobType.MOD, source_version="1.19.2", target_version="1.20.1",
        source_loader=Loader.FORGE, target_loader=Loader.FABRIC,
        input_path=src, output_path=tmp_path / "out.jar",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.PARTIAL
    assert job.report.unsupported
    assert any("forge" in w for w in job.report.warnings)


def test_mod_already_multiloader_is_used_as_is(tmp_path, engine):
    """Certains jars reels embarquent nativement mods.toml ET neoforge.mods.toml
    (multiloader). Pas de traduction a faire ni de dedup a rater dans ce cas."""
    src = tmp_path / "multiloader.jar"
    _make_zip(src, {
        "META-INF/mods.toml": FORGE_TOML,
        "META-INF/neoforge.mods.toml": FORGE_TOML.replace('modId="forge"', 'modId="neoforge"'),
        "com/example/Mod.class": b"\xca\xfe\xba\xbe",
    })

    job = ConversionJob(
        type=JobType.MOD, source_version="1.19.2", target_version="1.19.2",
        source_loader=Loader.NEOFORGE, target_loader=Loader.FORGE,
        input_path=src, output_path=tmp_path / "out.jar",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.OK
    assert "multiloader" in job.report.message
    with zipfile.ZipFile(job.output_path) as z:
        # les deux manifests d'origine sont preserves tels quels, aucun doublon
        assert z.namelist().count("META-INF/mods.toml") == 1
        assert "META-INF/neoforge.mods.toml" in z.namelist()


def test_resourcepack_unknown_target_version_fails(tmp_path, engine):
    src = tmp_path / "pack.zip"
    _make_zip(src, {"pack.mcmeta": json.dumps({"pack": {"pack_format": 9, "description": "t"}})})

    job = ConversionJob(
        type=JobType.RESOURCEPACK, source_version="1.19.2", target_version="99.99",
        input_path=src, output_path=tmp_path / "out.zip",
    )
    job = engine.submit_job(job)

    assert job.report.status == Status.FAILED
