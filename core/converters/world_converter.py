"""Conversion d'un monde (save) vers une nouvelle version MC.

Le vrai travail de migration des chunks est fait par le DataFixerUpper de
Minecraft lui-meme : ce converter prepare une copie propre du monde, et
indique la commande a lancer (serveur vanilla de la version cible, une
seule fois) pour declencher la mise a niveau reelle. Aucune re-implementation
du DataFixerUpper n'est tentee ici.
"""
from __future__ import annotations

import shutil

from core.job import ConversionJob, ConversionReport, Status
from core.converters.base import BaseConverter


class WorldConverter(BaseConverter):
    def convert(self, job: ConversionJob) -> ConversionReport:
        report = ConversionReport()

        level_dat = job.input_path / "level.dat"
        if not level_dat.is_file():
            report.status = Status.FAILED
            report.message = f"level.dat introuvable dans {job.input_path} (dossier de monde invalide)"
            return report

        if job.output_path.exists():
            shutil.rmtree(job.output_path)
        shutil.copytree(job.input_path, job.output_path)

        report.status = Status.PARTIAL
        report.message = "Copie preparee. Mise a niveau reelle a lancer via un serveur vanilla."
        report.warnings.append(
            f"Etape manuelle requise : lancer une fois "
            f"'java -jar server-{job.target_version}.jar --nogui' avec ce dossier comme "
            "monde, puis eteindre le serveur des que 'Preparing spawn area' se termine. "
            "Minecraft migre alors automatiquement les chunks via son DataFixerUpper."
        )
        return report
