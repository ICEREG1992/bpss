import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox, QApplication
)
from PyQt5.QtGui import QPixmap, QIcon
from Helpers import col_to_key, resource_path

class DisambiguateDialog(QDialog):
    def __init__(self, hash, key, col, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disambiguate Cell")
        self.setFixedSize(220, 100)
        self.setWindowIcon(QIcon(resource_path("media/bpss.png")))

        self.hash = hash
        self.key = key
        self.col = col

        self.load_ptrs()

        layout = QVBoxLayout()

        label = QLabel("Which instance of the string is this?")
        layout.addWidget(label)

        self.dropdown = self.create_dropdown()
        layout.addWidget(self.dropdown)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_ptrs(self):
        try:
            filename = self.hash + ".json"
            with open(filename, "r") as file:
                self.ptrs = json.load(file)
        except FileNotFoundError:
            print(f"Error: {self.file} file not found.")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {self.file}.")
        except Exception as e:
            print(f"Error loading data: {e}")

    def write_ptrs(self):
        filename = self.hash + ".json"
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(self.ptrs, file, indent=2)

    def create_dropdown(self):
        dropdown = QComboBox()
        
        # get options from file
        col = col_to_key(self.col)
        options = self.ptrs[self.key]["ptrs"][col]
        if len(options) <= 1:
            # look elsewhere
            print("your pointers are in another castle...")
            s = self.ptrs[self.key]["strings"][col]
            candidates = [a["ptrs"][col] for a in self.ptrs.values() if a["strings"][col] == s]
            options = [o for o in candidates if len(o) > 1][0]
            print(str(options))
        
        options = [str(i) for i in options]
        dropdown.addItems(options)
        return dropdown

    def selected_option(self):
        return int(self.dropdown.currentText())

    def save_and_accept(self):
        # write the override to data
        if self.ptrs[self.key].get("overrides"):
            self.ptrs[self.key]["overrides"][col_to_key(self.col)] = self.selected_option()
        else:
            self.ptrs[self.key]["overrides"] = {}
            self.ptrs[self.key]["overrides"][col_to_key(self.col)] = self.selected_option()
        # save it to file
        self.write_ptrs()
        self.accept()