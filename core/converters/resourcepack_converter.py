"""Conversion d'un resource pack (ou data pack) vers une nouvelle version MC.

Le seul changement necessaire pour la grande majorite des cas est le
`pack_format` dans pack.mcmeta. Fonctionne sur un dossier ou une archive .zip.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from core import mapping
from core.job import ConversionJob, ConversionReport, Status
from core.converters.base import BaseConverter

MCMETA_NAME = "pack.mcmeta"


class ResourcePackConverter(BaseConverter):
    def convert(self, job: ConversionJob) -> ConversionReport:
        report = ConversionReport()

        target_format = mapping.get_pack_format(job.target_version)
        if target_format is None:
            report.status = Status.FAILED
            report.message = (
                f"Version cible '{job.target_version}' inconnue dans data/mapping/pack_format.json"
            )
            return report

        if job.input_path.is_dir():
            ok = self._convert_dir(job, target_format, report)
        elif job.input_path.suffix.lower() == ".zip":
            ok = self._convert_zip(job, target_format, report)
        else:
            report.status = Status.FAILED
            report.message = "Le resource pack doit etre un dossier ou une archive .zip"
            return report

        if ok:
            report.status = Status.OK
            report.message = f"pack_format mis a jour vers {target_format} ({job.target_version})"
        return report

    def _convert_dir(self, job: ConversionJob, target_format: int, report: ConversionReport) -> bool:
        if job.output_path.exists():
            shutil.rmtree(job.output_path)
        shutil.copytree(job.input_path, job.output_path)

        mcmeta_path = job.output_path / MCMETA_NAME
        if not mcmeta_path.exists():
            report.status = Status.FAILED
            report.message = f"{MCMETA_NAME} introuvable dans {job.input_path}"
            return False

        data = json.loads(mcmeta_path.read_text(encoding="utf-8"))
        data.setdefault("pack", {})["pack_format"] = target_format
        mcmeta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True

    def _convert_zip(self, job: ConversionJob, target_format: int, report: ConversionReport) -> bool:
        with zipfile.ZipFile(job.input_path, "r") as src:
            names = src.namelist()
            if MCMETA_NAME not in names:
                report.status = Status.FAILED
                report.message = f"{MCMETA_NAME} introuvable dans l'archive"
                return False

            mcmeta = json.loads(src.read(MCMETA_NAME).decode("utf-8"))
            mcmeta.setdefault("pack", {})["pack_format"] = target_format

            with zipfile.ZipFile(job.output_path, "w", zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    if item.filename == MCMETA_NAME:
                        dst.writestr(item, json.dumps(mcmeta, indent=2, ensure_ascii=False))
                    else:
                        dst.writestr(item, src.read(item.filename))
        return True
