from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFileDialog, QSizePolicy
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from Helpers import resource_path

class FileBrowseCellWidget(QWidget):
    textChanged = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 0, 4, 0)

        # File drop behavior

        self.setAcceptDrops(True)

        # Build layout

        self.label = QLabel(text)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.mouseDoubleClickEvent = self.enable_edit_mode
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.line_edit = QLineEdit(text)
        self.line_edit.hide()
        self.line_edit.editingFinished.connect(self.finish_edit)
        
        self.browse_button = QPushButton()
        self.browse_button.setIcon(QIcon(QPixmap(resource_path("media/browse.png")).scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        self.browse_button.setIconSize(self.browse_button.icon().actualSize(self.browse_button.size()))
        self.browse_button.setFlat(True)  # Remove button border
        self.browse_button.setFixedSize(16, 16)  # Optional: size constraint
        self.browse_button.clicked.connect(self.open_file_dialog)

        layout.addWidget(self.browse_button)
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        
        self.setLayout(layout)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.LinkAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.setText(file_path)

    def enable_edit_mode(self, event):
        self.label.hide()
        self.line_edit.setText(self.label.text())
        self.line_edit.show()
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    def finish_edit(self):
        self.label.setText(self.line_edit.text())
        self.line_edit.hide()
        self.label.show()
        self.textChanged.emit(self.line_edit.text())

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.label.setText(file_path)
            self.textChanged.emit(self.label.text())

    def setText(self, text):
        self.label.setText(text)

    def text(self):
        return self.label.text()

    def setSelected(self, selected: bool):
        if selected:
            self.setStyleSheet("background-color: #0078D7;")
        else:
            self.setStyleSheet("background-color: #FFFFFF;")
