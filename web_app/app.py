"""Interface web locale (Flask) pour MC-Converter. Appelle le meme CoreEngine que desktop_app."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, request

from core.job import ConversionJob, JobType, Loader
from core.orchestrator import CoreEngine

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

FILE_BASED_TYPES = {JobType.MOD, JobType.RESOURCEPACK}

app = Flask(__name__)
engine = CoreEngine()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", types=list(JobType), loaders=list(Loader), report=None)


@app.route("/convert", methods=["POST"])
def convert():
    job_type = JobType(request.form["type"])
    source_version = request.form["source_version"].strip()
    target_version = request.form["target_version"].strip()
    source_loader = Loader(request.form["source_loader"])
    target_loader = Loader(request.form["target_loader"])

    if job_type in FILE_BASED_TYPES:
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return render_template(
                "index.html", types=list(JobType), loaders=list(Loader),
                report=None, error="Choisis un fichier a convertir.",
            )
        input_path = UPLOAD_DIR / uploaded.filename
        uploaded.save(input_path)
        output_path = OUTPUT_DIR / f"{input_path.stem}_{target_version}_{target_loader.value}{input_path.suffix}"
    else:
        server_path = request.form.get("server_path", "").strip()
        if not server_path or not Path(server_path).is_dir():
            return render_template(
                "index.html", types=list(JobType), loaders=list(Loader), report=None,
                error="Pour un monde ou un modpack, indique un chemin de dossier valide sur ce PC.",
            )
        input_path = Path(server_path)
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

    return render_template("index.html", types=list(JobType), loaders=list(Loader), report=job.report, job=job)


if __name__ == "__main__":
    app.run(debug=True, port=5090)
