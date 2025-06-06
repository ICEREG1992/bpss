from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from Helpers import resource_path

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(300, 150)
        self.setWindowIcon(QIcon(resource_path("bpss.png")))

        layout = QVBoxLayout()

        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setText(
            '<div style="line-height: 1.8;">'
            "Version 0.1.0<br>"
            'Developed by <a href="https://github.com/ICEREG1992/bpss">William Sullivan</a><br>'
            "Special thanks to burninrubber0 and JeBobs"
            '</div>'
        )

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        layout.addWidget(label)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        self.setLayout(layout)
