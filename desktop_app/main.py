"""Interface desktop PyQt6 pour MC-Converter. Appelle le meme CoreEngine que web_app."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QFileDialog, QPlainTextEdit, QGridLayout, QVBoxLayout, QMessageBox,
)

from core import detection
from core.job import ConversionJob, JobType, Loader, Status
from core.orchestrator import CoreEngine

AUTO = "Auto-detecter"
LOADERS = [l.value for l in Loader]
TYPES = [t.value for t in JobType]


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MC-Converter")
        self.resize(560, 500)
        self.engine = CoreEngine()
        self.input_path: Path | None = None

        self.type_box = QComboBox(); self.type_box.addItems(TYPES)
        self.source_version = QLineEdit(placeholderText="vide = auto-detecte depuis le fichier")
        self.target_version = QLineEdit(placeholderText="ex: 1.21.1")
        self.source_loader = QComboBox(); self.source_loader.addItems([AUTO, *LOADERS])
        self.target_loader = QComboBox(); self.target_loader.addItems(LOADERS)
        self.path_label = QLabel("Aucun fichier/dossier selectionne")
        self.detection_label = QLabel("")
        self.detection_label.setStyleSheet("color: #4a7c4e;")
        pick_file_btn = QPushButton("Choisir un fichier…")
        pick_dir_btn = QPushButton("Choisir un dossier…")
        convert_btn = QPushButton("Convertir")
        convert_btn.setStyleSheet("font-weight:600;")
        self.output = QPlainTextEdit(readOnly=True)

        pick_file_btn.clicked.connect(self.pick_file)
        pick_dir_btn.clicked.connect(self.pick_dir)
        convert_btn.clicked.connect(self.run_conversion)

        grid = QGridLayout()
        grid.addWidget(QLabel("Type"), 0, 0); grid.addWidget(self.type_box, 0, 1)
        grid.addWidget(QLabel("Version source"), 1, 0); grid.addWidget(self.source_version, 1, 1)
        grid.addWidget(QLabel("Version cible"), 2, 0); grid.addWidget(self.target_version, 2, 1)
        grid.addWidget(QLabel("Loader source"), 3, 0); grid.addWidget(self.source_loader, 3, 1)
        grid.addWidget(QLabel("Loader cible"), 4, 0); grid.addWidget(self.target_loader, 4, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(pick_file_btn)
        layout.addWidget(pick_dir_btn)
        layout.addWidget(self.path_label)
        layout.addWidget(self.detection_label)
        layout.addWidget(convert_btn)
        layout.addWidget(QLabel("Rapport"))
        layout.addWidget(self.output)

    def pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un mod/resource pack", filter="Archives (*.jar *.zip)")
        if path:
            self.input_path = Path(path)
            self.path_label.setText(str(self.input_path))
            self._run_detection_preview()

    def pick_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier (monde ou modpack)")
        if path:
            self.input_path = Path(path)
            self.path_label.setText(str(self.input_path))
            self.detection_label.setText("")

    def _run_detection_preview(self) -> None:
        """Detecte tout de suite au choix du fichier, pour que l'utilisateur
        voie le loader/version deduits avant meme de cliquer sur Convertir."""
        job_type = JobType(self.type_box.currentText())
        if job_type == JobType.MOD:
            result = detection.detect_mod(self.input_path)
        elif job_type == JobType.RESOURCEPACK:
            result = detection.detect_resourcepack(self.input_path)
        else:
            self.detection_label.setText("")
            return

        parts = []
        if result.loader is not None:
            parts.append(f"loader detecte : {result.loader.value}")
        if result.version:
            parts.append(f"version detectee : {result.version}")
        self.detection_label.setText(" ; ".join(parts) if parts else "Detection automatique : rien trouve dans le fichier.")

    def run_conversion(self) -> None:
        if self.input_path is None:
            QMessageBox.warning(self, "MC-Converter", "Choisis d'abord un fichier ou un dossier.")
            return
        if not self.target_version.text():
            QMessageBox.warning(self, "MC-Converter", "Renseigne la version cible.")
            return

        job_type = JobType(self.type_box.currentText())
        source_version = self.source_version.text().strip()
        source_loader_choice = self.source_loader.currentText()

        if job_type in (JobType.MOD, JobType.RESOURCEPACK) and (source_loader_choice == AUTO or not source_version):
            result = detection.detect_mod(self.input_path) if job_type == JobType.MOD else detection.detect_resourcepack(self.input_path)
            if source_loader_choice == AUTO:
                if result.loader is None and job_type == JobType.MOD:
                    QMessageBox.warning(self, "MC-Converter", "Loader non detecte automatiquement ; choisis-le dans la liste.")
                    return
                source_loader = result.loader or Loader.VANILLA
            else:
                source_loader = Loader(source_loader_choice)
            # Purement informatif (les converters se basent sur la version
            # CIBLE) : on ne bloque pas la conversion si elle est introuvable.
            if not source_version:
                source_version = result.version or "inconnue"
        else:
            source_loader = Loader(source_loader_choice) if source_loader_choice != AUTO else Loader.VANILLA
            if not source_version:
                QMessageBox.warning(self, "MC-Converter", "Renseigne la version source.")
                return

        job = ConversionJob(
            type=job_type,
            source_version=source_version,
            target_version=self.target_version.text().strip(),
            source_loader=source_loader,
            target_loader=Loader(self.target_loader.currentText()),
            input_path=self.input_path,
        )

        try:
            job = self.engine.submit_job(job)
        except Exception as exc:  # affichage d'erreur dans l'UI plutot qu'un crash silencieux
            self.output.setPlainText(f"Erreur : {exc}")
            return

        self._show_report(job)

    def _show_report(self, job: ConversionJob) -> None:
        r = job.report
        lines = [
            f"Statut : {r.status.value}",
            f"Source detectee/utilisee : {job.source_version} / {job.source_loader.value}",
            f"Sortie : {job.output_path}", "", r.message,
        ]
        if r.warnings:
            lines += ["", "Avertissements :"] + [f"  - {w}" for w in r.warnings]
        if r.unsupported:
            lines += ["", "Non pris en charge automatiquement :"] + [f"  - {u}" for u in r.unsupported]
        self.output.setPlainText("\n".join(lines))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
