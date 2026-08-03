"""Interface web locale (Flask) pour MC-Converter. Appelle le meme CoreEngine que desktop_app."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, request

from core import detection
from core.job import ConversionJob, JobType, Loader
from core.orchestrator import CoreEngine

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Deux dimensions independantes : ou va chercher l'entree (fichier uploade vs
# chemin de dossier local), et si un loader (Forge/Fabric/...) a seulement un
# sens pour ce type. Un resource pack ou un monde n'ont pas de "loader" ;
# vanilla n'a pas de "mod" — donc jamais les deux memes regroupements.
FILE_BASED_TYPES = {JobType.MOD, JobType.RESOURCEPACK}
LOADER_RELEVANT_TYPES = {JobType.MOD, JobType.MODPACK}


def _render(**kwargs):
    return render_template("index.html", types=list(JobType), loaders=list(Loader), **kwargs)


app = Flask(__name__)
engine = CoreEngine()


@app.route("/", methods=["GET"])
def index():
    return _render(report=None)


@app.route("/convert", methods=["POST"])
def convert():
    job_type = JobType(request.form["type"])
    source_version = request.form["source_version"].strip()
    target_version = request.form["target_version"].strip()
    source_loader_raw = request.form["source_loader"]
    target_loader_raw = request.form["target_loader"]
    detected_note = None

    # 1. Resoudre l'entree : fichier uploade ou dossier local.
    if job_type in FILE_BASED_TYPES:
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return _render(report=None, error="Choisis un fichier a convertir.")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        input_path = UPLOAD_DIR / uploaded.filename
        uploaded.save(input_path)
    else:
        server_path = request.form.get("server_path", "").strip()
        if not server_path or not Path(server_path).is_dir():
            return _render(report=None, error="Indique un chemin de dossier valide sur ce PC.")
        input_path = Path(server_path)

    # 2. Loader/version source : detection automatique si pertinent pour ce
    # type et que l'utilisateur n'a pas force une valeur.
    if job_type in LOADER_RELEVANT_TYPES:
        need_detection = source_loader_raw == "auto" or not source_version
        if need_detection:
            if job_type == JobType.MOD:
                result = detection.detect_mod(input_path)
            else:
                result = detection.detect_modpack(input_path)
            if source_loader_raw == "auto":
                if result.loader is None:
                    return _render(report=None, error="Loader non detecte automatiquement ; choisis-le manuellement.")
                source_loader = result.loader
            else:
                source_loader = Loader(source_loader_raw)
            # La version source est informative (les converters se basent
            # sur la version CIBLE) : jamais bloquant si introuvable.
            if not source_version:
                source_version = result.version or "inconnue"
            detected_note = " ; ".join(result.notes) if result.notes else None
        else:
            source_loader = Loader(source_loader_raw)
        target_loader = Loader(target_loader_raw)
    else:
        if job_type == JobType.RESOURCEPACK and (source_loader_raw == "auto" or not source_version):
            result = detection.detect_resourcepack(input_path)
            if not source_version:
                source_version = result.version or "inconnue"
            detected_note = " ; ".join(result.notes) if result.notes else None
        source_loader = Loader.VANILLA
        target_loader = Loader.VANILLA
        if not source_version:
            source_version = "inconnue"

    # 3. Chemin de sortie.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if job_type in FILE_BASED_TYPES:
        output_path = OUTPUT_DIR / f"{input_path.stem}_{target_version}_{target_loader.value}{input_path.suffix}"
    else:
        output_path = OUTPUT_DIR / f"{input_path.name}_{target_version}_{target_loader.value}"

    job = ConversionJob(
        type=job_type,
        source_version=source_version,
        target_version=target_version,
        source_loader=source_loader,
        target_loader=target_loader,
        input_path=input_path,
        output_path=output_path,
    )
    job = engine.submit_job(job)

    return _render(report=job.report, job=job, detected_note=detected_note)


if __name__ == "__main__":
    app.run(debug=True, port=5090)
