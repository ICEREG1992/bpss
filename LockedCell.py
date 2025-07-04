from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from Helpers import resource_path

class LockedCellWidget(QWidget):
    def __init__(self, text):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)

        self.innerText = ""

        self.label = QLabel(text)
        lock_icon = QLabel()
        lock_icon.setPixmap(QPixmap(resource_path("media/lock.png")).scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(lock_icon)

        self.setLayout(layout)
        self.setEnabled(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #eeeeee;")
    
    def setText(self, text):
        self.label.setText(text)

    def text(self):
        return self.label.text()
    
    def setInnerText(self, text):
        self.innerText = text

    def innerText(self):
        return self.innerText

    def setSelected(self, selected: bool):
        if selected:
            self.setStyleSheet("background-color: #a0c4ff;")
        else:
            self.setStyleSheet("background-color: #eeeeee;")
