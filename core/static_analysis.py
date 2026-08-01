"""Analyse statique hors-ligne des .class d'un jar, sans aucun appel reseau
ni cle API — indispensable pour un outil open source utilisable par tous
sans compte/service tiers.

Principe : les references de classes/paquets dans un .class compile
apparaissent en clair (ASCII) dans le pool de constantes. Un simple scan des
octets bruts a la recherche de prefixes de paquets connus (Forge, NeoForge,
Fabric, Quilt) suffit a savoir quelles API un mod utilise, sans decompiler
ni executer quoi que ce soit.

Certains mods NeoForge (fonctionnalite "jarJar") embarquent d'autres jars
complets sous META-INF/jarjar/*.jar plutot que d'exposer leurs .class
directement a la racine — un jar "bundle" peut ainsi n'avoir aucune classe
au premier niveau. Le scan descend donc dans les jars imbriques (profondeur
limitee pour eviter tout risque de zip bomb).

Ce module ne modifie jamais le jar : il sert a documenter, pour un humain
(ou pour construire une future table de correspondance communautaire), quels
points d'API bloquent une conversion automatique entre deux loaders.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field

# Prefixes de paquets identifiant l'API d'un loader dans le bytecode.
LOADER_PACKAGE_PREFIXES: dict[str, list[bytes]] = {
    "forge": [b"net/minecraftforge/"],
    "neoforge": [b"net/neoforged/"],
    "fabric": [b"net/fabricmc/"],
    "quilt": [b"org/quiltmc/"],
}

MAX_NESTED_JAR_DEPTH = 2


@dataclass
class StaticAnalysis:
    references: dict[str, int] = field(default_factory=dict)  # loader -> nb de hits
    sample_classes: list[str] = field(default_factory=list)
    nested_jars_scanned: int = 0

    def summary(self, target_loader: str) -> str:
        hits = ", ".join(f"{loader}={count}" for loader, count in self.references.items() if count)
        foreign = {l: c for l, c in self.references.items() if c and l != target_loader}
        nested_note = f" ({self.nested_jars_scanned} jar(s) imbrique(s) analyse(s))" if self.nested_jars_scanned else ""
        if not foreign:
            return f"Aucune reference d'API de loader detectee dans le bytecode scanne{nested_note}."
        return (
            f"References d'API detectees dans le bytecode{nested_note} ({hits}). "
            f"Ce mod utilise directement l'API de {', '.join(foreign)}, "
            f"incompatible avec {target_loader} : reecriture manuelle necessaire "
            "pour ces points d'accroche."
        )


def analyze_jar(jar_path) -> StaticAnalysis:
    counts = {loader: 0 for loader in LOADER_PACKAGE_PREFIXES}
    sample: list[str] = []
    nested_count = 0

    def scan(fileobj, depth: int) -> None:
        nonlocal nested_count
        with zipfile.ZipFile(fileobj) as jar:
            names = jar.namelist()
            class_files = [n for n in names if n.endswith(".class")]
            if depth == 0:
                sample.extend(class_files[:15])
            for name in class_files:
                raw = jar.read(name)
                for loader, prefixes in LOADER_PACKAGE_PREFIXES.items():
                    for prefix in prefixes:
                        counts[loader] += raw.count(prefix)

            if depth < MAX_NESTED_JAR_DEPTH:
                for name in names:
                    if name.endswith(".jar"):
                        nested_count += 1
                        scan(io.BytesIO(jar.read(name)), depth + 1)

    with open(jar_path, "rb") as f:
        scan(f, 0)

    return StaticAnalysis(references=counts, sample_classes=sample, nested_jars_scanned=nested_count)
