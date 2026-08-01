"""Interface commune a tous les converters."""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.job import ConversionJob, ConversionReport


class BaseConverter(ABC):
    @abstractmethod
    def convert(self, job: ConversionJob) -> ConversionReport:
        """Effectue la conversion decrite par `job` et renvoie le rapport.

        Doit ecrire le resultat dans `job.output_path` quand le statut est OK/PARTIAL.
        """
        raise NotImplementedError
