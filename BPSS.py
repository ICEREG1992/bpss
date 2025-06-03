import os
import sys
import json
import hashlib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QHeaderView, QFrame, QVBoxLayout,
                            QTableWidgetItem, QHBoxLayout, QWidget, QToolBar, QAction, QStyle, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

from processing import loadPtrs
from settings import SettingsDialog

SETTINGS_FILE = "settings.json"

class SoundtrackViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Burnout Paradise Soundtrack Switcher")
        self.setWindowIcon(QtGui.QIcon("bpss.png"))
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        window_width = 900
        window_height = 600

        # Calculate center position
        center_x = screen_rect.center().x() - window_width // 2
        center_y = screen_rect.center().y() - window_height // 2

        # Set the geometry: x, y, width, height
        self.setGeometry(center_x, center_y, window_width, window_height)
        self.setFixedSize(window_width, window_height)
        
        self.synced_cells = []  # List of lists of (row, column) tuples

        # Create toolbar
        self.create_toolbar()
        
        # Create central widget to hold table
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Load settings
        self.settings = self.load_settings()
        if not self.validate_settings():
            dialog = SettingsDialog(first=True)
            if dialog.exec_():
                print("First time settings updated")
            else:
                print("Settings canceled")
                QMessageBox.warning(self, "Missing Input", "You will be unable to apply new soundtracks until you set all settings.")
        
        # Create table widget
        self.create_table()

        # Add table to layout
        layout.addWidget(self.table, 3)


        # Create actions widget
        self.create_actions()

        layout.addWidget(self.actions, 1)
    
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {}

    def validate_settings(self):
        required_keys = [
            "game",
            "audio",
            "yap"
        ]

        missing = [v for v in required_keys if not v in self.settings]
        return not missing
    
    def get_ptrs_hash(self):
        if self.settings["game"]:
            return hashlib.sha256(self.settings["game"].encode()).hexdigest()[:8]
        else:
            return None

        
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)
        
        # File operations
        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        load_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Load", self)
        load_action.triggered.connect(self.load_file)
        toolbar.addAction(load_action)
        
        save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        export_action = QAction(self.style().standardIcon(QStyle.SP_DriveHDIcon), "Export", self)
        export_action.triggered.connect(self.export_file)
        toolbar.addAction(export_action)
        
        # First vertical spacer
        toolbar.addSeparator()
        
        # Filter/Apply operations
        apply_action = QAction(self.style().standardIcon(QStyle.SP_DialogApplyButton), "Apply", self)
        apply_action.triggered.connect(self.apply_action)
        toolbar.addAction(apply_action)
        
        unapply_action = QAction(self.style().standardIcon(QStyle.SP_DialogCancelButton), "Unapply", self)
        unapply_action.triggered.connect(self.unapply_action)
        toolbar.addAction(unapply_action)
        
        reset_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Reset", self)
        reset_action.triggered.connect(self.reset_action)
        toolbar.addAction(reset_action)
        
        # Second vertical spacer
        toolbar.addSeparator()
        
        # Settings and help
        settings_action = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        help_action = QAction(self.style().standardIcon(QStyle.SP_MessageBoxQuestion), "Help", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

    def create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["#", "Title", "Album", "Artist", "Stream", "Source", "File"])
        
        # Hide vertical headers (row numbers on the left)
        self.table.verticalHeader().setVisible(False)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        self.load_data()
        
        # set up item syncing
        self.table.itemChanged.connect(self.handle_item_changed)

    def load_data(self):
        try:
            self.settings = self.load_settings()
            # Load JSON data
            filename = self.get_ptrs_hash() + ".json"
            if os.path.isfile(filename):
                with open(filename, "r") as file:
                    ptrs = json.load(file)
            else:
                print("Generating new ptrs")
                loadPtrs(self.settings, filename)
                with open(filename, "r") as file:
                    ptrs = json.load(file)

            # Load Defaults
            with open("songs.json", "r") as file:
                defaults = json.load(file)
                
            # Set row count based on number of entries
            self.table.setRowCount(len(ptrs))
            
            stock = {}
            backfill = []
            sync = {}
            
            # Populate table
            for row_index, (key, entry) in enumerate(ptrs.items()):
                # Get strings data (title, stream, album, artist)
                strings = entry.get("strings", {})
                title = strings.get("title", "")
                album = strings.get("album", "")
                artist = strings.get("artist", "")
                stream = strings.get("stream", "")
                
                # Get source and file
                source = entry.get("source", "")
                file_path = entry.get("file", "")
                
                # Create index item with proper numeric sorting
                index_item = QTableWidgetItem()
                index_item.setData(Qt.DisplayRole, row_index + 1)  # Store as number for sorting
                index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)

                sync_icon = QIcon("sync.png")
                browse_icon = QIcon("browse.png")
                
                match defaults[key]["type"]:
                    case 0: # regular soundtrack
                        match defaults[key]["lock"]:
                            case 0: # no lock
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))
                            case 1: # no album (FRICTION)
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setCellWidget(row_index, 2, self.make_locked_cell(album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))                                
                            case 3: # artist/album sync
                                self.synced_cells.append([(row_index, 2), (row_index, 3)])
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(sync_icon, album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(sync_icon, artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))                                
                            case 6: # stream/artist sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                self.table.setCellWidget(row_index, 3, self.make_locked_cell(artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))                                
                            case 7: # stream/artist/album sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setCellWidget(row_index, 2, self.make_locked_cell(album))
                                self.table.setCellWidget(row_index, 3, self.make_locked_cell(artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))

                            case 9: # song/album sync
                                self.synced_cells.append([(row_index, 1), (row_index, 2)])
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(sync_icon, title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(sync_icon, album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                                self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                                self.table.setItem(row_index, 6, QTableWidgetItem(file_path))

                    case 1: # burnout soundtrack
                        # steal any duplicate strings
                        artist_ptrs = entry.get("ptrs").get("artist")
                        if len(artist_ptrs) > 1:
                            stock[artist] = artist_ptrs[1:]
                            sync[defaults[key]["defaults"]["artist"]] = [(row_index, 3)]
                            artist_color = list(sync).index(defaults[key]["defaults"]["artist"])
                            self.table.setItem(row_index, 3, self.make_unique_cell(artist, artist_color))
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, defaults[key]["defaults"]["artist"], 1])
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        album_ptrs = entry.get("ptrs").get("album")
                        if len(album_ptrs) > 1:
                            stock[album] = album_ptrs[1:]
                            sync[defaults[key]["defaults"]["album"]] = [(row_index, 2)]
                            album_color = list(sync).index(defaults[key]["defaults"]["album"])
                            self.table.setItem(row_index, 2, self.make_unique_cell(album, album_color))
                        elif len(album_ptrs) == 0:
                            backfill.append([row_index, 2, defaults[key]["defaults"]["album"], 0])
                            self.table.setItem(row_index, 2, QTableWidgetItem(album))
                        else:
                            self.table.setItem(row_index, 2, QTableWidgetItem(album))
                            
                        self.table.setItem(row_index, 0, index_item)
                        self.table.setItem(row_index, 1, QTableWidgetItem(title))
                        # look above for album cell
                        # look above for artist cell
                        self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                        self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                        self.table.setItem(row_index, 6, QTableWidgetItem(file_path))                        
                    case 2: # classical soundtrack
                        # steal any duplicate strings
                        artist_ptrs = entry.get("ptrs").get("artist")
                        if len(artist_ptrs) > 1:
                            stock[artist] = artist_ptrs[1:]
                            sync[defaults[key]["defaults"]["artist"]] = [(row_index, 3)]
                            artist_color = list(sync).index(defaults[key]["defaults"]["artist"])
                            self.table.setItem(row_index, 3, self.make_unique_cell(artist, artist_color))
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, defaults[key]["defaults"]["artist"], 3])
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        self.table.setItem(row_index, 0, index_item)
                        self.table.setItem(row_index, 1, QTableWidgetItem(title))
                        self.table.setCellWidget(row_index, 2, self.make_locked_cell(album))
                        # look above for artist cell
                        self.table.setCellWidget(row_index, 4, self.make_locked_cell(stream))
                        self.table.setItem(row_index, 5, QTableWidgetItem(browse_icon, source or ""))  # Ensure source is never None
                        self.table.setItem(row_index, 6, QTableWidgetItem(file_path))

            # backfill
            for i in backfill:
                sync[i[2]].append((i[0], i[1]))
                stock[i[2]].pop()
                unique_color = list(sync).index(i[2])
                self.table.setItem(i[0], i[1], self.make_unique_cell(i[2], unique_color))

            # populate table sync
            for k in sync.keys():
                self.synced_cells.append(sync[k])
            
            # fix column sizes
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.table.setColumnWidth(0, 30)  # Set to 30 pixels wide

            for col in range(1, self.table.columnCount()):
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        
        except FileNotFoundError:
            print("Error: test.soundtrack file not found.")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in test.soundtrack.")
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def make_locked_cell(self, text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)
        
        text_label = QLabel(text)
        lock_icon = QLabel()
        lock_icon.setPixmap(QPixmap("lock.png").scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        layout.addWidget(text_label)
        layout.addStretch()
        layout.addWidget(lock_icon)
        widget.setLayout(layout)
        widget.setEnabled(False)
        widget.setStyleSheet("background-color: #eeeeee;")
        return widget
    
    def make_unique_cell(self, text, color: int) -> QTableWidgetItem:
        colors = [
        "#FFB3BA",  # Light Red
        "#FFDFBA",  # Peach
        "#FFFFBA",  # Pale Yellow
        "#BAFFC9",  # Mint
        "#BAE1FF",  # Baby Blue
        "#E6BAFF",  # Lavender
        "#FFD6E8",  # Pink Rose
        "#A0E7E5",  # Sky Blue
        "#D5FFB3",  # Pastel Lime
        "#FFF0BA"   # Butter Yellow
        ]

        widget = QTableWidgetItem(text)
        widget.setBackground(QBrush(QColor(colors[color])))
        return widget

    def handle_item_changed(self, changed_item: QTableWidgetItem):
        row = changed_item.row()
        col = changed_item.column()
        text = changed_item.text()

        # handle synced cells
        for group in self.synced_cells:
            if (row, col) in group:
                for (r, c) in group:
                    if (r, c) != (row, col):
                        self.table.item(r, c).setText(text)
                break  # Only one group per cell

        # handle file wiping
        if col == 5:
            self.table.item(row, 6).setText("")
    
    def add_sync_icon(self, row: int, col: int):
        label = QLabel(self.table)
        label.setPixmap(QPixmap("sync.png").scaled(12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        label.setStyleSheet("background: transparent")
        label.setFixedSize(12, 12)
        label.move(
            self.table.columnViewportPosition(col) + self.table.columnWidth(col) - 14,
            self.table.rowViewportPosition(row) + 2
        )
        label.show()


    def create_actions(self):
        # Right side - actions panel (takes 1/3 of space)
        actions_frame = QFrame()
        actions_frame.setFrameStyle(QFrame.StyledPanel)
        actions_layout = QVBoxLayout(actions_frame)

        # Song manipulation actions
        move_up_btn = QPushButton("Move Song Up")
        move_up_btn.setStyleSheet("text-align: left;")
        move_up_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        move_up_btn.clicked.connect(self.move_song_up)
        
        move_down_btn = QPushButton("Move Song Down") 
        move_down_btn.setStyleSheet("text-align: left;")
        move_down_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        move_down_btn.clicked.connect(self.move_song_down)
        
        # File operations
        browse_file_btn = QPushButton("Browse for File")
        browse_file_btn.setStyleSheet("text-align: left;")
        browse_file_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        browse_file_btn.clicked.connect(self.browse_for_file)
        
        delete_btn = QPushButton("Delete Song")
        delete_btn.setStyleSheet("text-align: left;")
        delete_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        delete_btn.clicked.connect(self.delete_song)
        
        # Add to layout
        actions_layout.addWidget(move_up_btn)
        actions_layout.addWidget(move_down_btn)
        actions_layout.addWidget(browse_file_btn)
        actions_layout.addWidget(delete_btn)
        actions_layout.addStretch()  # Push buttons to top
        
        self.actions = actions_frame
    
    # Toolbar action methods (placeholder implementations)
    def new_file(self):
        print("New file action triggered")
        
    def load_file(self):
        print("Load file action triggered")
        
    def save_file(self):
        print("Save file action triggered")
        
    def export_file(self):
        print("Export file action triggered")
        
    def apply_action(self):
        print("Apply action triggered")
        
    def unapply_action(self):
        print("Unapply action triggered")
        
    def reset_action(self):
        print("Reset action triggered")
        self.load_data()
        
    def show_settings(self):
        print("Settings action triggered")
        dialog = SettingsDialog()
        if dialog.exec_():
            print("Settings updated")
        else:
            print("Settings canceled")
        
    def show_help(self):
        print("Help action triggered")

    def move_song_up(self):
        print("Move song up action triggered")

    def move_song_down(self):
        print("Move song down action triggered")

    def browse_for_file(self):
        print("Browse for file action triggered")

    def duplicate_song(self):
        print("Duplicate song action triggered")

    def delete_song(self):
        print("Delete song action triggered")

    def edit_song(self):
        print("Edit song action triggered")

    def play_song(self):
        print("Play song action triggered")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = SoundtrackViewer()
    viewer.show()
    sys.exit(app.exec_())