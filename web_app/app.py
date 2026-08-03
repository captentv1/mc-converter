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

FILE_BASED_TYPES = {JobType.MOD, JobType.RESOURCEPACK}


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
    target_loader = Loader(request.form["target_loader"])
    detected_note = None

    if job_type in FILE_BASED_TYPES:
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return _render(report=None, error="Choisis un fichier a convertir.")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        input_path = UPLOAD_DIR / uploaded.filename
        uploaded.save(input_path)

        # "auto" ou version vide -> on deduit du fichier lui-meme (manifest du
        # mod, pack.mcmeta du resource pack) plutot que de demander a l'utilisateur.
        if source_loader_raw == "auto" or not source_version:
            result = detection.detect_mod(input_path) if job_type == JobType.MOD else detection.detect_resourcepack(input_path)
            if source_loader_raw == "auto":
                if result.loader is None and job_type == JobType.MOD:
                    return _render(report=None, error="Loader non detecte automatiquement ; choisis-le manuellement.")
                source_loader = result.loader or Loader.VANILLA
            else:
                source_loader = Loader(source_loader_raw)
            # La version source ne sert qu'a l'affichage (les converters se
            # basent sur la version CIBLE) : si elle n'est pas detectable,
            # on continue quand meme avec un texte informatif plutot que de
            # bloquer toute la conversion pour un champ non essentiel.
            if not source_version:
                source_version = result.version or "inconnue"
            detected_note = " ; ".join(result.notes) if result.notes else None
        else:
            source_loader = Loader(source_loader_raw)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"{input_path.stem}_{target_version}_{target_loader.value}{input_path.suffix}"
    else:
        source_loader = Loader(source_loader_raw) if source_loader_raw != "auto" else Loader.VANILLA
        server_path = request.form.get("server_path", "").strip()
        if not server_path or not Path(server_path).is_dir():
            return _render(report=None, error="Pour un monde ou un modpack, indique un chemin de dossier valide sur ce PC.")
        input_path = Path(server_path)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
