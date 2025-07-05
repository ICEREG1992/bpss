from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox, QApplication
)

class DisambiguateDialog(QDialog):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disambiguate Cell")

        layout = QVBoxLayout()

        label = QLabel("Which instance of the string is this?")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.addItems([str(a) for a in options])
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def selected_option(self):
        return self.combo.currentText()