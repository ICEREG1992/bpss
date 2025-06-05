from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QProgressBar

class ProgressWidget(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setWindowTitle(text)
        self.setGeometry(100, 100, 300, 100)

        # Create widgets
        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def set_progress(self, val):
        if val < 100:
            self.progress.setValue(val)

    def add_progress(self, val):
        current = self.progress.value()
        if current < 100:
            self.progress.setValue(current + val)