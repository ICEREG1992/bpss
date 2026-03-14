import sys
import json
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QCheckBox,
    QFileDialog, QHBoxLayout, QVBoxLayout, QDialogButtonBox, QSpacerItem, QSizePolicy, QMessageBox
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
        self.setFixedSize(450, 250)
        self.settings = self.load_settings()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create each path entry row
        self.burnout_path = self.create_dir_selector("Burnout Paradise Installation Path", "game", layout)
        self.soundx_path = self.create_file_selector("EA SoundXchange Path", "audio", layout)
        self.yap_path = self.create_file_selector("YAP Path", "yap", layout)
        self.warn_disambiguation_checkbox = QCheckBox("Warn when disambiguating locked cells")
        self.warn_disambiguation_checkbox.setChecked(self.settings.get("warn", True))
        self.cut_songs_checkbox = QCheckBox("Use Cut Songs in BPR Mod")
        self.cut_songs_checkbox.setChecked(self.settings.get("mod", False))
        if self.first:
            self.warn_disambiguation_checkbox.hide()
            self.cut_songs_checkbox.hide()
        else:
            self.clear_cache_button = QPushButton("Clear SX Cache")
            self.clear_cache_button.clicked.connect(self.clear_sx_cache)
        layout.addWidget(self.warn_disambiguation_checkbox)
        layout.addWidget(self.cut_songs_checkbox)
        if not self.first:
            layout.addWidget(self.clear_cache_button)
        spacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addSpacerItem(spacer)
        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def create_dir_selector(self, label_text, key, parent_layout):
        label = QLabel(label_text)
        line_edit = QLineEdit(self.settings.get(key, ""))
        browse_button = QPushButton("Browse")

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
        browse_button = QPushButton("Browse")

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
        required_fields = {
            "game": self.game_input.text(),
            "audio": self.audio_input.text(),
            "yap": self.yap_input.text(),
            "warn": self.warn_disambiguation_checkbox.isChecked(),
            "mod": self.cut_songs_checkbox.isChecked()
        }

        missing = [key for key, val in required_fields.items() if val is None]

        if missing:
            QMessageBox.warning(self, "Missing Input", "Please fill in all required paths.")
            return

        for f in required_fields.keys():
            self.settings[f] = required_fields[f]
        # Retain existing optional fields if they exist
        self.settings.setdefault("prev", "")
        self.settings.setdefault("actions", False)

        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

        self.accept()
