"""Point d'entree unique utilise par le desktop (PyQt6) et le web (Flask)."""
from __future__ import annotations

from core.job import ConversionJob, JobType
from core.converters.mod_converter import ModConverter
from core.converters.modpack_converter import ModpackConverter
from core.converters.world_converter import WorldConverter
from core.converters.resourcepack_converter import ResourcePackConverter


class CoreEngine:
    def __init__(self) -> None:
        self._converters = {
            JobType.MOD: ModConverter(),
            JobType.MODPACK: ModpackConverter(),
            JobType.WORLD: WorldConverter(),
            JobType.RESOURCEPACK: ResourcePackConverter(),
        }

    def submit_job(self, job: ConversionJob) -> ConversionJob:
        converter = self._converters[job.type]
        job.report = converter.convert(job)
        return job
