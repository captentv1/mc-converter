"""Contrat de données partagé entre les interfaces (desktop/web) et le Core Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobType(str, Enum):
    MOD = "mod"
    MODPACK = "modpack"
    WORLD = "world"
    RESOURCEPACK = "resourcepack"


class Loader(str, Enum):
    VANILLA = "vanilla"
    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"


class Status(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ConversionReport:
    status: Status = Status.FAILED
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


@dataclass
class ConversionJob:
    type: JobType
    source_version: str
    target_version: str
    input_path: Path
    source_loader: Loader = Loader.VANILLA
    target_loader: Loader = Loader.VANILLA
    output_path: Path | None = None
    report: ConversionReport = field(default_factory=ConversionReport)

    def __post_init__(self) -> None:
        self.input_path = Path(self.input_path)
        if self.output_path is None:
            suffix = self.input_path.suffix
            stem = self.input_path.stem
            self.output_path = self.input_path.with_name(
                f"{stem}_{self.target_version}_{self.target_loader.value}{suffix}"
            )
        else:
            self.output_path = Path(self.output_path)
