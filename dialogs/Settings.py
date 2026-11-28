import sys
import json
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QCheckBox,
    QFileDialog, QHBoxLayout, QVBoxLayout, QDialogButtonBox, QMessageBox
)
from PyQt5.QtGui import QIcon
from Helpers import resource_path, coerce_bool

SETTINGS_FILE = "settings.json"

class SettingsDialog(QDialog):
    def __init__(self, first=False):
        super().__init__()
        self.first = first
        window_title = "First Time Setup" if first else "Settings"
        self.setWindowTitle(window_title)
        self.setWindowIcon(QIcon(resource_path("media/bpss.png")))
        self.settings = self.load_settings()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.control_height = QPushButton("Close").sizeHint().height()

        self.warn_disambiguation_checkbox = QCheckBox("Warn when disambiguating locked cells")
        self.warn_disambiguation_checkbox.setChecked(self.settings.get("warn", True))
        self.cut_songs_checkbox = QCheckBox("Use Cut Songs in BPR Mod")
        self.cut_songs_checkbox.setChecked(self.settings.get("mod", False))
        self.match_checkbox = QCheckBox("Match sample rate")
        self.match_checkbox.setChecked(self.settings.get("match", True))
        self.normalize_checkbox = QCheckBox("Normalize loudness")
        self.normalize_checkbox.setChecked(self.settings.get("normalize", True))

        if self.first:
            self.warn_disambiguation_checkbox.hide()
            self.cut_songs_checkbox.hide()
            self.match_checkbox.hide()
            self.normalize_checkbox.hide()
        else:
            self.clear_cache_button = QPushButton("Clear SX Cache")
            self.clear_cache_button.setFixedWidth(120)
            self.clear_cache_button.setMinimumHeight(self.control_height)
            self.clear_cache_button.clicked.connect(self.clear_sx_cache)
        
        # Build layout

        self.burnout_path = self.create_dir_selector("Burnout Paradise Installation Path", "game", layout)
        self.soundx_path = self.create_file_selector("EA SoundXchange Path", "audio", layout)
        self.yap_path = self.create_file_selector("YAP Path", "yap", layout)

        layout.addSpacing(10)
        
        layout.addWidget(self.warn_disambiguation_checkbox)
        layout.addWidget(self.cut_songs_checkbox)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self.match_checkbox)
        audio_row.addWidget(self.normalize_checkbox)
        audio_row.addStretch()
        layout.addLayout(audio_row)

        if not self.first:
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(self.clear_cache_button)
            layout.addLayout(button_layout)
        layout.addStretch()
        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        for button in buttons.buttons():
            button.setMinimumHeight(self.control_height)
        layout.addWidget(buttons)

        # Right before we set the layout, see if sx or YAP are in place
        if (os.path.isfile("./sx.exe")):
            self.soundx_path = os.path.join("sx.exe")
        if (os.path.isfile("./YAP.exe")):
            self.yap_path = os.path.join("YAP.exe")
        self.setLayout(layout)

        # Let the layout decide the height
        self.setFixedSize(450, self.sizeHint().height())

    def create_dir_selector(self, label_text, key, parent_layout):
        label = QLabel(label_text)
        line_edit = QLineEdit(self.settings.get(key, ""))
        line_edit.setMinimumHeight(self.control_height)
        browse_button = QPushButton("Browse")
        browse_button.setMinimumHeight(self.control_height)

        def browse():
            start_path = line_edit.text() or "."
            path = QFileDialog.getExistingDirectory(self, f"Select {label_text}", start_path)
            if path:
                line_edit.setText(path)

        browse_button.clicked.connect(browse)

        hbox = QHBoxLayout()
        hbox.addWidget(line_edit)
        hbox.addWidget(browse_button)

        parent_layout.addWidget(label)
        parent_layout.addLayout(hbox)

        # Store reference for saving later
        setattr(self, f"{key}_input", line_edit)
        return line_edit

    def create_file_selector(self, label_text, key, parent_layout):
        label = QLabel(label_text)
        line_edit = QLineEdit(self.settings.get(key, ""))
        line_edit.setMinimumHeight(self.control_height)
        browse_button = QPushButton("Browse")
        browse_button.setMinimumHeight(self.control_height)

        def browse():
            start_path = line_edit.text() or "."
            path, _ = QFileDialog.getOpenFileName(self, f"Select {label_text}", start_path)
            if path:
                line_edit.setText(path)

        browse_button.clicked.connect(browse)

        hbox = QHBoxLayout()
        hbox.addWidget(line_edit)
        hbox.addWidget(browse_button)

        parent_layout.addWidget(label)
        parent_layout.addLayout(hbox)

        # Store reference for saving later
        setattr(self, f"{key}_input", line_edit)
        return line_edit

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                settings["warn"] = coerce_bool(settings.get("warn", True), default=True)
                settings["mod"] = coerce_bool(settings.get("mod", False), default=False)
                settings["actions"] = coerce_bool(settings.get("actions", False), default=False)
                settings["match"] = coerce_bool(settings.get("match", True), default=True)
                settings["normalize"] = coerce_bool(settings.get("normalize", True), default=True)
                return settings
        return {}

    def clear_sx_cache(self):
        cache_dir = os.path.join("temp", "sx_cache")
        result = QMessageBox.question(
            self,
            "Clear SX Cache",
            "Are you sure you want to clear the SX conversion cache?\n\nThis will free disk space, but will cause subsequent apply operations to take longer (until the cache is rebuilt).\n\nThis action can not be undone!",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        if result != QMessageBox.Yes:
            return

        try:
            if os.path.isdir(cache_dir):
                shutil.rmtree(cache_dir)
                QMessageBox.information(self, "SX Cache Cleared", "SX conversion cache was cleared.")
            else:
                QMessageBox.information(self, "SX Cache", "No SX cache folder was found.")
        except Exception as e:
            QMessageBox.critical(self, "Clear Cache Failed", f"Could not clear SX cache.\n\nReason: {e}")

    def save_and_accept(self):
        # (key, label shown to the user, value, check that the path really exists)
        paths = [
            ("game", "Burnout Paradise Installation Path", self.game_input.text().strip(), os.path.isdir),
            ("audio", "EA SoundXchange Path", self.audio_input.text().strip(), os.path.isfile),
            ("yap", "YAP Path", self.yap_input.text().strip(), os.path.isfile),
        ]

        missing = [label for _, label, value, _ in paths if not value]
        if missing:
            QMessageBox.warning(
                self,
                "Missing Input",
                "Please fill in all required paths:\n\n" + "\n".join(missing),
            )
            return

        not_found = [label for _, label, value, exists in paths if not exists(value)]
        if not_found:
            QMessageBox.warning(
                self,
                "Path Not Found",
                "These paths could not be found:\n\n" + "\n".join(not_found),
            )
            return

        for key, _, value, _ in paths:
            self.settings[key] = value
        self.settings["warn"] = self.warn_disambiguation_checkbox.isChecked()
        self.settings["mod"] = self.cut_songs_checkbox.isChecked()
        self.settings["match"] = self.match_checkbox.isChecked()
        self.settings["normalize"] = self.normalize_checkbox.isChecked()
        # Retain existing optional fields if they exist
        self.settings.setdefault("prev", "")
        self.settings.setdefault("actions", False)

        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

        self.accept()
