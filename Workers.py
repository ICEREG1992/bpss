from PyQt5.QtCore import QObject, QThread, pyqtSignal
from processing import load_pointers, write_pointers, reset_files
import time

class ResetWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def run(self):
        def update_progress(val, string):
            self.progress_changed.emit(val, string)
        
        try:
            reset_files(self.settings, update_progress)
        except Exception as e:
            self.error.emit(e)
        time.sleep(.5)
        self.finished.emit()

class WriteWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, settings, soundtrack, pointers):
        super().__init__()
        self.settings = settings
        self.soundtrack = soundtrack
        self.pointers = pointers

    def run(self):
        def update_progress(val, string):
            self.progress_changed.emit(val, string)

        try:
            write_pointers(self.settings, self.soundtrack, self.pointers, update_progress)
        except Exception as e:
            self.error.emit(e)
        time.sleep(.5)
        self.finished.emit()

class LoadWorker(QObject):
    progress_changed = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, settings, filename):
        super().__init__()
        self.settings = settings
        self.filename = filename

    def run(self):
        def update_progress(val, string):
            self.progress_changed.emit(val, string)

        try:
            load_pointers(self.settings, self.filename, update_progress)
        except Exception as e:
            self.error.emit(e)
        time.sleep(.5)
        self.finished.emit()