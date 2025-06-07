from PyQt5.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from Helpers import resource_path

class ProgressWidget(QDialog):
    def __init__(self, text):
        super().__init__()
        self.setWindowTitle(text)
        self.setFixedSize(400, 100)
        self.setWindowIcon(QIcon(resource_path("bpss.png")))
        self.setWindowModality(Qt.ApplicationModal)

        # Create widgets
        self.status_label = QLabel("", self)  # <-- status text
        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.progress, 3)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_progress(self, val, status):
        if val <= 100:
            self.progress.setValue(val)
        if status:
            self.status_label.setText(status)