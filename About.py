from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt

from Helpers import resource_path
import webbrowser

class AboutDialog(QDialog):

    def __init__(self, hash=None):
        super().__init__()
        self.setWindowTitle("About")
        self.setFixedSize(320, 150)
        self.setWindowIcon(QIcon(resource_path("media/bpss.png")))

        layout = QVBoxLayout()     

        version_layout = QHBoxLayout()
        version_label = QLabel("Version 0.3.3")
        hash_label = QLabel(hash)
        hash_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        version_layout.addWidget(version_label)
        version_layout.addWidget(hash_label)

        layout.addLayout(version_layout, 2)

        dev_layout = QHBoxLayout()

        link_label = QLabel()
        link_label.setText('Developed by <a href="https://github.com/ICEREG1992/bpss">William Sullivan</a>')
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setOpenExternalLinks(False)  # So we can handle the click ourselves
        link_label.linkActivated.connect(lambda url: webbrowser.open(url))

        dev_layout.addWidget(link_label)
        dev_layout.addStretch()
        layout.addLayout(dev_layout, 2)

        thanks_label = QLabel("Special thanks to burninrubber0 and JeBobs")
        layout.addWidget(thanks_label, 2)
    
        layout.addStretch(2)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        self.setLayout(layout)

    def open_link(event):
        webbrowser.open("https://github.com/ICEREG1992/bpss")   