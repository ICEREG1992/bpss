import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox, QApplication
)

class DisambiguateDialog(QDialog):
    def __init__(self, hash, key, col, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disambiguate Cell")
        self.setFixedSize(220, 100)

        self.hash = hash
        self.key = key
        self.col = col

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

    def create_dropdown(self):
        dropdown = QComboBox()
        
        # get options from file
        # try:
        filename = self.hash + ".json"
        with open(filename, "r") as file:
            ptrs = json.load(file)
            col = self.col_to_key(self.col)
            options = ptrs[self.key]["ptrs"][col]
            if len(options) <= 1:
                # look elsewhere
                print("your pointers are in another castle...")
                s = ptrs[self.key]["strings"][col]
                candidates = [a["ptrs"][col] for a in ptrs.values() if a["strings"][col] == s]
                options = [o for o in candidates if len(o) > 1][0]
                print(str(options))
        # except FileNotFoundError:
        #     print(f"Error: {self.file} file not found.")
        # except json.JSONDecodeError:
        #     print(f"Error: Invalid JSON format in {self.file}.")
        # except Exception as e:
        #     print(f"Error loading data: {e}")
        options = [str(i) for i in options]
        dropdown.addItems(options)
        return dropdown

    def selected_option(self):
        return self.dropdown.currentIndex()
    
    def col_to_key(self, col):
        match col:
            case 1:
                return "title"
            case 2:
                return "album"
            case 3:
                return "artist"

    def save_and_accept(self):
        print("accept")
        self.accept()