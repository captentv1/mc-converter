"""Interface desktop PyQt6 pour MC-Converter. Appelle le meme CoreEngine que web_app."""
from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QFileDialog, QPlainTextEdit, QGridLayout, QVBoxLayout, QHBoxLayout,
    QMessageBox, QButtonGroup,
)

from core import detection
from core.job import ConversionJob, JobType, Loader, Status
from core.orchestrator import CoreEngine

AUTO = "Auto-detecter"
# "vanilla" n'a pas de sens comme loader d'un mod/modpack (un mod a
# forcement un vrai loader) ; le champ n'est de toute facon pas utilise
# par les converters world/resourcepack, donc pas besoin de le proposer.
LOADERS = [l.value for l in Loader if l != Loader.VANILLA]
LOADER_RELEVANT_TYPES = (JobType.MOD, JobType.MODPACK)
FILE_BASED_TYPES = (JobType.MOD, JobType.RESOURCEPACK)

TYPE_LABELS = {
    JobType.MOD: "Mod",
    JobType.MODPACK: "Modpack",
    JobType.WORLD: "Monde",
    JobType.RESOURCEPACK: "Resource pack",
}

SIDEBAR_STYLE = """
QPushButton {
    text-align: left; padding: 10px 12px; border: none; border-radius: 6px;
    color: #5a564d; background: transparent; font-size: 13px;
}
QPushButton:hover { background: #edeae1; }
QPushButton:checked { background: #e4ede3; color: #2f5a33; font-weight: 600; }
"""


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MC-Converter")
        self.resize(720, 520)
        self.engine = CoreEngine()
        self.input_path: Path | None = None
        self.current_type = JobType.MOD

        self._build_ui()
        self._apply_type(JobType.MOD)

    def _build_ui(self) -> None:
        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background: #ffffff; border-right: 1px solid #dcd6c8;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        title = QLabel("MC-Converter")
        title.setStyleSheet("font-weight: 700; padding: 0 4px 12px;")
        sidebar_layout.addWidget(title)

        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        self.type_buttons: dict[JobType, QPushButton] = {}
        for job_type in JobType:
            btn = QPushButton(TYPE_LABELS[job_type])
            btn.setCheckable(True)
            btn.setStyleSheet(SIDEBAR_STYLE)
            btn.clicked.connect(partial(self._apply_type, job_type))
            self.type_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            self.type_buttons[job_type] = btn
        sidebar_layout.addStretch()

        # --- Formulaire ---
        self.source_version = QLineEdit(placeholderText="vide = auto-detecte depuis le fichier")
        self.target_version = QLineEdit(placeholderText="ex: 1.21.1")
        self.source_loader = QComboBox(); self.source_loader.addItems([AUTO, *LOADERS])
        self.target_loader = QComboBox(); self.target_loader.addItems(LOADERS)
        self.path_label = QLabel("Aucun fichier/dossier selectionne")
        self.detection_label = QLabel("")
        self.detection_label.setStyleSheet("color: #4a7c4e;")
        self.pick_file_btn = QPushButton("Choisir un fichier…")
        self.pick_dir_btn = QPushButton("Choisir un dossier…")
        convert_btn = QPushButton("Convertir")
        convert_btn.setStyleSheet("font-weight:600;")
        self.output = QPlainTextEdit(readOnly=True)

        self.pick_file_btn.clicked.connect(self.pick_file)
        self.pick_dir_btn.clicked.connect(self.pick_dir)
        convert_btn.clicked.connect(self.run_conversion)

        self.loader_labels = [QLabel("Loader source"), QLabel("Loader cible")]

        self.grid = QGridLayout()
        self.grid.addWidget(QLabel("Version source"), 0, 0); self.grid.addWidget(self.source_version, 0, 1)
        self.grid.addWidget(QLabel("Version cible"), 1, 0); self.grid.addWidget(self.target_version, 1, 1)
        self.grid.addWidget(self.loader_labels[0], 2, 0); self.grid.addWidget(self.source_loader, 2, 1)
        self.grid.addWidget(self.loader_labels[1], 3, 0); self.grid.addWidget(self.target_loader, 3, 1)

        content = QVBoxLayout()
        content.addLayout(self.grid)
        content.addWidget(self.pick_file_btn)
        content.addWidget(self.pick_dir_btn)
        content.addWidget(self.path_label)
        content.addWidget(self.detection_label)
        content.addWidget(convert_btn)
        content.addWidget(QLabel("Rapport"))
        content.addWidget(self.output)

        content_widget = QWidget()
        content_widget.setLayout(content)
        content_widget.setContentsMargins(0, 0, 0, 0)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)

        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(content_widget)
        root.addWidget(main_area, stretch=1)

    def _apply_type(self, job_type: JobType) -> None:
        self.current_type = job_type
        self.type_buttons[job_type].setChecked(True)
        self.input_path = None
        self.path_label.setText("Aucun fichier/dossier selectionne")
        self.detection_label.setText("")

        file_based = job_type in FILE_BASED_TYPES
        self.pick_file_btn.setVisible(file_based)
        self.pick_dir_btn.setVisible(not file_based)

        loader_relevant = job_type in LOADER_RELEVANT_TYPES
        for widget in (self.source_loader, self.target_loader, *self.loader_labels):
            widget.setVisible(loader_relevant)

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
            self._run_detection_preview()

    def _detect(self, job_type: JobType):
        if job_type == JobType.MOD:
            return detection.detect_mod(self.input_path)
        if job_type == JobType.MODPACK:
            return detection.detect_modpack(self.input_path)
        if job_type == JobType.RESOURCEPACK:
            return detection.detect_resourcepack(self.input_path)
        return None

    def _run_detection_preview(self) -> None:
        """Detecte tout de suite au choix du fichier/dossier, pour que
        l'utilisateur voie le loader/version deduits avant meme de cliquer
        sur Convertir."""
        result = self._detect(self.current_type)
        if result is None:
            self.detection_label.setText("")
            return

        parts = []
        if result.loader is not None:
            parts.append(f"loader detecte : {result.loader.value}")
        if result.version:
            parts.append(f"version detectee : {result.version}")
        self.detection_label.setText(" ; ".join(parts) if parts else "Detection automatique : rien trouve.")

    def run_conversion(self) -> None:
        if self.input_path is None:
            QMessageBox.warning(self, "MC-Converter", "Choisis d'abord un fichier ou un dossier.")
            return
        if not self.target_version.text():
            QMessageBox.warning(self, "MC-Converter", "Renseigne la version cible.")
            return

        job_type = self.current_type
        source_version = self.source_version.text().strip()
        source_loader_choice = self.source_loader.currentText()
        target_loader = Loader(self.target_loader.currentText()) if job_type in LOADER_RELEVANT_TYPES else Loader.VANILLA

        if job_type in LOADER_RELEVANT_TYPES:
            if source_loader_choice == AUTO or not source_version:
                result = self._detect(job_type)
                if source_loader_choice == AUTO:
                    if result.loader is None:
                        QMessageBox.warning(self, "MC-Converter", "Loader non detecte automatiquement ; choisis-le dans la liste.")
                        return
                    source_loader = result.loader
                else:
                    source_loader = Loader(source_loader_choice)
                # Purement informatif (les converters se basent sur la
                # version CIBLE) : on ne bloque pas si elle est introuvable.
                if not source_version:
                    source_version = result.version or "inconnue"
            else:
                source_loader = Loader(source_loader_choice)
        else:
            source_loader = Loader.VANILLA
            if not source_version:
                result = self._detect(job_type)
                source_version = (result.version if result else None) or "inconnue"

        job = ConversionJob(
            type=job_type,
            source_version=source_version,
            target_version=self.target_version.text().strip(),
            source_loader=source_loader,
            target_loader=target_loader,
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
