import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton,
    QFileDialog, QHBoxLayout, QVBoxLayout, QDialogButtonBox, QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt5.QtGui import QIcon

SETTINGS_FILE = "settings.json"

class SettingsDialog(QDialog):
    def __init__(self, first=False):
        super().__init__()
        window_title = "First Time Setup" if first else "Settings"
        self.setWindowTitle(window_title)
        self.setWindowIcon(QIcon("bpss.png"))
        self.setFixedSize(450, 250)
        self.settings = self.load_settings()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create each path entry row
        self.burnout_path = self.create_dir_selector("Burnout Paradise Installation Path", "game", layout)
        self.soundx_path = self.create_file_selector("EA SoundXchange Path", "audio", layout)
        self.yap_path = self.create_file_selector("YAP Path", "yap", layout)
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
                return json.load(f)
        return {}

    def save_and_accept(self):
        required_fields = {
            "game": self.game_input.text(),
            "audio": self.audio_input.text(),
            "yap": self.yap_input.text()
        }

        missing = [key for key, val in required_fields.items() if not val]

        if missing:
            QMessageBox.warning(self, "Missing Input", "Please fill in all required paths.")
            return

        for f in required_fields.keys():
            self.settings[f] = required_fields[f]
        # Retain existing optional fields if they exist
        self.settings.setdefault("prev", "")
        self.settings.setdefault("mod", "")

        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

        self.accept()