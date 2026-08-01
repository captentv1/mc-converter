"""Conversion d'un mod (.jar) entre versions MC et/ou entre loaders.

Trois cas, du plus au moins automatisable :

1. Meme loader : bump de la contrainte de version Minecraft dans le
   manifest. Entierement automatique.
2. Loaders cross-compatibles (Fabric <-> Quilt) : Quilt charge nativement
   un jar Fabric, donc simple repackage. Entierement automatique.
3. Loaders "partiellement" convertibles (Forge <-> NeoForge) : le manifest
   peut etre traduit (renommage mods.toml <-> neoforge.mods.toml, modId de
   la dependance loader) mais PAS le bytecode. NeoForge est un fork de
   Forge avec des paquets Java differents (net.minecraftforge ->
   net.neoforged) ; les .class du mod continuent de referencer l'ancien
   paquet et doivent etre reecrits a la main. On rend ca visible via une
   analyse statique locale (core/static_analysis.py), jamais en tentant un
   remplacement de texte dans le bytecode compile (ca corromprait le
   .class : le pool de constantes est prefixe par une longueur en octets).
4. Loaders incompatibles (Forge <-> Fabric, etc.) : uniquement l'analyse
   statique, le mod est place dans `report.unsupported`.

Aucun appel reseau ni cle API dans ce module : tout est local, pour rester
utilisable par n'importe qui une fois le projet publie en open source.
"""
from __future__ import annotations

import json
import re
import zipfile

from core import mapping, static_analysis
from core.job import ConversionJob, ConversionReport, Status, Loader
from core.converters.base import BaseConverter

JSON_MANIFESTS = {Loader.FABRIC: "fabric.mod.json", Loader.QUILT: "quilt.mod.json"}
TOML_MANIFESTS = {Loader.FORGE: "META-INF/mods.toml", Loader.NEOFORGE: "META-INF/neoforge.mods.toml"}
ALL_MANIFESTS = {**JSON_MANIFESTS, **TOML_MANIFESTS}


class ModConverter(BaseConverter):
    def convert(self, job: ConversionJob) -> ConversionReport:
        report = ConversionReport()
        source, target = job.source_loader.value, job.target_loader.value
        same_loader = job.source_loader == job.target_loader
        cross_compatible = mapping.loaders_are_cross_compatible(source, target)
        partial = mapping.loaders_have_partial_conversion(source, target)

        if not same_loader and not cross_compatible and not partial:
            analysis = static_analysis.analyze_jar(job.input_path)
            report.status = Status.PARTIAL
            report.message = "Conversion cross-loader non automatisable au niveau du code."
            report.unsupported.append(f"{job.input_path.name}: {source} -> {target}")
            report.warnings.append(analysis.summary(target))
            return report

        with zipfile.ZipFile(job.input_path, "r") as src:
            names = set(src.namelist())
            manifest_name = self._find_manifest(job.source_loader, names)
            if manifest_name is None:
                report.status = Status.FAILED
                report.message = f"Manifest de loader introuvable pour {source}"
                return report

            raw = src.read(manifest_name)
            translate = partial and not same_loader
            target_manifest_name = ALL_MANIFESTS.get(job.target_loader, manifest_name) if translate else manifest_name

            if manifest_name.endswith(".json"):
                updated_raw, warnings = self._bump_json_manifest(raw, job)
            else:
                updated_raw, warnings = self._bump_toml_manifest(raw, job, translate)
            report.warnings.extend(warnings)

            with zipfile.ZipFile(job.output_path, "w", zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    if item.filename == manifest_name:
                        dst.writestr(target_manifest_name, updated_raw)
                    else:
                        dst.writestr(item, src.read(item.filename))

        if translate:
            analysis = static_analysis.analyze_jar(job.input_path)
            report.status = Status.PARTIAL
            report.unsupported.append(
                f"{job.input_path.name}: code encore ecrit pour {source}, portage manuel du bytecode requis"
            )
            report.warnings.append(analysis.summary(target))
            report.message = (
                f"Manifest traduit {source} -> {target} et version Minecraft mise a jour. "
                "Le CODE du mod n'a pas ete repackage (voir avertissements)."
            )
        else:
            report.status = Status.OK
            report.message = f"Manifest mis a jour pour Minecraft {job.target_version} ({source} -> {target})"
        return report

    @staticmethod
    def _find_manifest(loader: Loader, names: set[str]) -> str | None:
        candidate = ALL_MANIFESTS.get(loader)
        if candidate and candidate in names:
            return candidate
        # Fabric <-> Quilt: un mod Fabric pur n'a que fabric.mod.json, meme charge par Quilt.
        for name in ALL_MANIFESTS.values():
            if name in names:
                return name
        return None

    @staticmethod
    def _bump_json_manifest(raw: bytes, job: ConversionJob) -> tuple[bytes, list[str]]:
        data = json.loads(raw.decode("utf-8"))
        depends = data.get("depends", {})
        warnings: list[str] = []
        if "minecraft" in depends:
            depends["minecraft"] = f">={job.target_version}"
            data["depends"] = depends
        else:
            warnings.append("Aucune dependance 'minecraft' trouvee dans le manifest ; a verifier manuellement.")
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"), warnings

    @staticmethod
    def _bump_toml_manifest(raw: bytes, job: ConversionJob, translate_loader: bool) -> tuple[bytes, list[str]]:
        text = raw.decode("utf-8")
        warnings: list[str] = []

        mc_pattern = re.compile(r'(modId\s*=\s*"minecraft"[\s\S]*?versionRange\s*=\s*")([^"]*)(")')
        text, count = mc_pattern.subn(
            lambda m: f'{m.group(1)}[{job.target_version},){m.group(3)}', text
        )
        if not count:
            warnings.append("Bloc de dependance 'minecraft' non trouve dans mods.toml ; a verifier manuellement.")

        if translate_loader:
            source, target = job.source_loader.value, job.target_loader.value
            loader_pattern = re.compile(rf'modId\s*=\s*"{source}"')
            text, loader_count = loader_pattern.subn(f'modId="{target}"', text)
            if loader_count:
                warnings.append(
                    f"Dependance 'modId=\"{source}\"' renommee en '{target}' ; "
                    f"la 'versionRange' de cette dependance reste a verifier manuellement "
                    f"(numerotation de version differente entre Forge et NeoForge)."
                )
            warnings.append(
                "loaderVersion (haut du fichier) non modifiee automatiquement ; "
                f"verifier la plage compatible avec {target} pour Minecraft {job.target_version}."
            )

        return text.encode("utf-8"), warnings
