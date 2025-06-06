from PyQt5.QtCore import QObject, QThread, pyqtSignal
from processing import write_pointers, reset_files
import time

class ResetWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def run(self):
        def update_progress(val, string):
            self.progress_changed.emit(val, string)

        reset_files(self.settings, update_progress)
        time.sleep(.5)
        self.finished.emit()

class WriteWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, settings, soundtrack, pointers):
        super().__init__()
        self.settings = settings
        self.soundtrack = soundtrack
        self.pointers = pointers

    def run(self):
        def update_progress(val, string):
            self.progress_changed.emit(val, string)

        write_pointers(self.settings, self.soundtrack, self.pointers, update_progress)
        time.sleep(.5)
        self.finished.emit()