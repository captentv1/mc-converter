from core import mapping


def test_get_pack_format_known_version():
    assert mapping.get_pack_format("1.20.1") == 15
    assert mapping.get_pack_format("1.18.2") == 9


def test_get_pack_format_unknown_version_returns_none():
    assert mapping.get_pack_format("99.99") is None


def test_fabric_quilt_are_cross_compatible():
    assert mapping.loaders_are_cross_compatible("fabric", "quilt")
    assert mapping.loaders_are_cross_compatible("quilt", "fabric")


def test_forge_fabric_are_not_cross_compatible():
    assert not mapping.loaders_are_cross_compatible("forge", "fabric")


def test_forge_neoforge_have_partial_conversion_only():
    assert not mapping.loaders_are_cross_compatible("forge", "neoforge")
    assert mapping.loaders_have_partial_conversion("forge", "neoforge")
    assert mapping.loaders_have_partial_conversion("neoforge", "forge")
