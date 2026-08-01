import io
import zipfile

from core import static_analysis


def _zip_bytes(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_analyze_jar_finds_top_level_references(tmp_path):
    jar = tmp_path / "mod.jar"
    jar.write_bytes(_zip_bytes({
        "com/example/Mod.class": b"\xca\xfe\xba\xbe" + b"net/neoforged/fml/common/Mod",
    }))

    result = static_analysis.analyze_jar(jar)

    assert result.references["neoforge"] > 0
    assert result.nested_jars_scanned == 0


def test_analyze_jar_descends_into_bundled_jarjar(tmp_path):
    """Reproduit le cas 'jarJar' de NeoForge : le jar principal n'a aucune
    classe au premier niveau, tout est dans un jar imbrique."""
    nested = _zip_bytes({
        "com/example/Inner.class": b"\xca\xfe\xba\xbe" + b"net/neoforged/api/distmarker",
    })
    outer = tmp_path / "bundled.jar"
    outer.write_bytes(_zip_bytes({
        "META-INF/jarjar/inner.jar": nested,
    }))

    result = static_analysis.analyze_jar(outer)

    assert result.references["neoforge"] > 0
    assert result.nested_jars_scanned == 1
