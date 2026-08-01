"""Conversion d'un modpack : applique ModConverter a chaque .jar du dossier
`mods/` et agrege le rapport. Les fichiers de config (`config/`, `.json`
d'options) sont copies tels quels ; ils ne dependent pas du loader.
"""
from __future__ import annotations

import shutil

from core.job import ConversionJob, ConversionReport, Status, JobType
from core.converters.base import BaseConverter
from core.converters.mod_converter import ModConverter


class ModpackConverter(BaseConverter):
    def __init__(self) -> None:
        self._mod_converter = ModConverter()

    def convert(self, job: ConversionJob) -> ConversionReport:
        report = ConversionReport()

        mods_dir = job.input_path / "mods"
        if not mods_dir.is_dir():
            report.status = Status.FAILED
            report.message = f"Dossier 'mods' introuvable dans {job.input_path}"
            return report

        if job.output_path.exists():
            shutil.rmtree(job.output_path)
        shutil.copytree(job.input_path, job.output_path)
        out_mods_dir = job.output_path / "mods"

        converted, partial, failed = 0, 0, 0
        for jar_path in mods_dir.glob("*.jar"):
            mod_job = ConversionJob(
                type=JobType.MOD,
                source_version=job.source_version,
                target_version=job.target_version,
                source_loader=job.source_loader,
                target_loader=job.target_loader,
                input_path=jar_path,
                output_path=out_mods_dir / jar_path.name,
            )
            mod_report = self._mod_converter.convert(mod_job)
            report.warnings.extend(f"{jar_path.name}: {w}" for w in mod_report.warnings)
            report.unsupported.extend(mod_report.unsupported)
            if mod_report.status == Status.OK:
                converted += 1
            elif mod_report.status == Status.PARTIAL:
                # Manifest traduit mais code non porte : le jar est garde
                # (utile) plutot que supprime, le rapport signale le reste
                # a faire via warnings/unsupported.
                partial += 1
            else:
                failed += 1
                (out_mods_dir / jar_path.name).unlink(missing_ok=True)

        if failed == 0 and partial == 0:
            report.status = Status.OK
        elif converted + partial > 0:
            report.status = Status.PARTIAL
        else:
            report.status = Status.FAILED
        report.message = (
            f"{converted} mod(s) converti(s) sans reserve, {partial} avec manifest traduit "
            f"mais code a porter manuellement, {failed} non convertis (a remplacer/porter)."
        )
        return report
