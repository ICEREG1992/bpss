import os
import sys
import json
import hashlib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QHeaderView, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QVBoxLayout,
                            QTableWidgetItem, QHBoxLayout, QWidget, QToolBar, QAction, QStyle, QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QBrush, QColor, QIcon

from Settings import SettingsDialog
from LockedCell import LockedCellWidget
from FileBrowseCell import FileBrowseCellWidget
from Progress import ProgressWidget
from Workers import ResetWorker, WriteWorker, LoadWorker
from About import AboutDialog
from Helpers import resource_path

SETTINGS_FILE = "settings.json"

class SoundtrackViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Burnout Paradise Soundtrack Switcher")
        self.setWindowIcon(QIcon(resource_path("bpss.png")))
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

        # establish important variables
        self.changes = False
        self.file = None
        self.synced_cells = []  # List of lists of (row, column) tuples
        self.defaults_file = resource_path("songs.json")

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
        
        # Load defaults
        self.defaults = self.load_defaults()

        # Create table widget
        self.create_table()

        # Add table to layout
        layout.addWidget(self.table, 3)


        # Create actions widget
        # self.create_actions()
        # layout.addWidget(self.actions, 1)
    
    def update_window_title(self):
        if self.file:
            self.setWindowTitle(f"Burnout Paradise Soundtrack Switcher [{self.file}]")
        else:
            self.setWindowTitle("Burnout Paradise Soundtrack Switcher")
    
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {}
    
    def load_defaults(self):
        if os.path.exists(self.defaults_file):
            with open(self.defaults_file, "r") as f:
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
        if "game" in self.settings.keys():
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
        
        open_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
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
        
        # Settings and about
        settings_action = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        about_action = QAction(self.style().standardIcon(QStyle.SP_MessageBoxQuestion), "About", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

    def create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "Title", "Album", "Artist", "Stream", "Source"])
        
        # Hide vertical headers (row numbers on the left)
        self.table.verticalHeader().setVisible(False)
        
        # Enable sorting
        self.table.setSortingEnabled(True)

        # Load table with data
        self.load_data()
        
        # set up item syncing
        self.table.itemChanged.connect(self.handle_item_changed)

        # set up highlighting of locked cells
        self.table.itemSelectionChanged.connect(self.handle_selection_changed)

    def load_data(self):
        # Check for JSON data
        filename = str(self.get_ptrs_hash()) + ".json"
        if os.path.isfile(filename):
            self.fill_table()
        else:
            print("Generating new ptrs")
            
            self.progress = ProgressWidget("Finding pointers...")
            self.progress.show()
            
            self.thread = QThread()
            self.worker = LoadWorker(self.settings, filename)
            self.worker.moveToThread(self.thread)

            # Connect signals
            self.thread.started.connect(self.worker.run)
            self.worker.progress_changed.connect(self.progress.set_progress)
            self.worker.finished.connect(self.progress.close)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.fill_table)
            self.thread.finished.connect(self.thread.deleteLater)
            
            self.thread.start()

    def fill_table(self):
        try:
            self.settings = self.load_settings()
            filename = self.get_ptrs_hash() + ".json"
            with open(filename, "r") as file:
                ptrs = json.load(file)

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
                
                # Create index item with proper numeric sorting
                index_item = QTableWidgetItem()
                index_item.setData(Qt.DisplayRole, row_index + 1)  # Store as number for sorting
                index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
                index_item.setTextAlignment(Qt.AlignCenter)

                # Create file browse widget with update hook
                file_browse_widget = FileBrowseCellWidget(source or "")
                
                match self.defaults[key]["type"]:
                    case 0: # regular soundtrack
                        match self.defaults[key]["lock"]:
                            case 0: # no lock
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None
                            case 1: # no album (FRICTION)
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setCellWidget(row_index, 2, LockedCellWidget(album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None
                            case 3: # artist/album sync
                                # self.synced_cells.append([(row_index, 2), (row_index, 3)])
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))

                                sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2), (row_index, 3)]
                                song_color = list(sync).index(self.defaults[key]["defaults"]["album"])
                                self.table.setItem(row_index, 2, self.make_unique_cell(album, song_color))
                                self.table.setItem(row_index, 3, self.make_unique_cell(artist, song_color))

                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None
                            case 6: # stream/artist sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                self.table.setCellWidget(row_index, 3, LockedCellWidget(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None
                            case 7: # stream/artist/album sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setCellWidget(row_index, 2, LockedCellWidget(album))
                                self.table.setCellWidget(row_index, 3, LockedCellWidget(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None

                            case 9: # song/album sync                               
                                self.table.setItem(row_index, 0, index_item)

                                sync[self.defaults[key]["defaults"]["title"]] = [(row_index, 1), (row_index, 2)]
                                song_color = list(sync).index(self.defaults[key]["defaults"]["title"])
                                self.table.setItem(row_index, 1, self.make_unique_cell(title, song_color))
                                self.table.setItem(row_index, 2, self.make_unique_cell(album, song_color))

                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None

                    case 1: # burnout soundtrack
                        # steal any duplicate strings
                        artist_ptrs = entry.get("ptrs").get("artist")
                        if len(artist_ptrs) > 1:
                            stock[artist] = artist_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["artist"]] = [(row_index, 3)]
                            artist_color = list(sync).index(self.defaults[key]["defaults"]["artist"])
                            self.table.setItem(row_index, 3, self.make_unique_cell(artist, artist_color))
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, self.defaults[key]["defaults"]["artist"], 1])
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        album_ptrs = entry.get("ptrs").get("album")
                        if len(album_ptrs) > 1:
                            stock[album] = album_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2)]
                            album_color = list(sync).index(self.defaults[key]["defaults"]["album"])
                            self.table.setItem(row_index, 2, self.make_unique_cell(album, album_color))
                        elif len(album_ptrs) == 0:
                            backfill.append([row_index, 2, self.defaults[key]["defaults"]["album"], 0])
                            self.table.setItem(row_index, 2, QTableWidgetItem(album))
                        else:
                            self.table.setItem(row_index, 2, QTableWidgetItem(album))
                            
                        self.table.setItem(row_index, 0, index_item)
                        self.table.setItem(row_index, 1, QTableWidgetItem(title))
                        # look above for album cell
                        # look above for artist cell
                        self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                        self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None 
                    case 2: # classical soundtrack
                        # steal any duplicate strings
                        artist_ptrs = entry.get("ptrs").get("artist")
                        if len(artist_ptrs) > 1:
                            stock[artist] = artist_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["artist"]] = [(row_index, 3)]
                            artist_color = list(sync).index(self.defaults[key]["defaults"]["artist"])
                            self.table.setItem(row_index, 3, self.make_unique_cell(artist, artist_color))
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, self.defaults[key]["defaults"]["artist"], 3])
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        self.table.setItem(row_index, 0, index_item)
                        self.table.setItem(row_index, 1, QTableWidgetItem(title))
                        self.table.setCellWidget(row_index, 2, LockedCellWidget(album))
                        # look above for artist cell
                        self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                        self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None

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
            print("Error: Pointers file not found.")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in pointers file.")
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def load_file(self):
        # get data from file
        try:
            self.settings = self.load_settings()
            # Load JSON data
            with open(self.file, "r") as file:
                st = json.load(file)

            # Edit table
            for (key, entry) in st.items():
                # Get strings data (title, stream, album, artist)
                strings = entry.get("strings", {})
                title = strings.get("title", "")
                album = strings.get("album", "")
                artist = strings.get("artist", "")
                stream = strings.get("stream", "")
                
                # Get source and file
                source = entry.get("source", "")

                row_index = list(self.defaults.keys()).index(key)

                # Apply soundtrack content
                match self.defaults[key]["type"]:
                    case 0: # regular soundtrack
                        match self.defaults[key]["lock"]:
                            case 0: # no lock
                                self.table.item(row_index, 1).setText(title)
                                self.table.item(row_index, 2).setText(album)
                                self.table.item(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                            case 1: # no album (FRICTION)
                                self.table.item(row_index, 1).setText(title)
                                self.table.item(row_index, 2).setText(album)
                                self.table.item(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                            case 3: # artist/album sync
                                self.table.item(row_index, 1).setText(title)
                                self.table.item(row_index, 2).setText(album)
                                self.table.item(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                            case 6: # stream/artist sync
                                self.table.item(row_index, 1).setText(title)
                                self.table.item(row_index, 2).setText(album)
                                self.table.cellWidget(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                            case 7: # stream/artist/album sync
                                self.table.item(row_index, 1).setText(title)
                                self.table.cellWidget(row_index, 2).setText(album)
                                self.table.cellWidget(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                            case 9: # song/album sync
                                self.table.item(row_index, 1).setText(title)
                                self.table.item(row_index, 2).setText(album)
                                self.table.item(row_index, 3).setText(artist)
                                self.table.cellWidget(row_index, 4).setText(stream)
                                self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None

                    case 1: # burnout soundtrack
                        self.table.item(row_index, 1).setText(title)
                        self.table.item(row_index, 2).setText(album)
                        self.table.item(row_index, 3).setText(artist)
                        self.table.cellWidget(row_index, 4).setText(stream)
                        self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
                    case 2: # classical soundtrack
                        self.table.item(row_index, 1).setText(title)
                        self.table.cellWidget(row_index, 2).setText(album)
                        self.table.item(row_index, 3).setText(artist)
                        self.table.cellWidget(row_index, 4).setText(stream)
                        self.table.cellWidget(row_index, 5).setText(source or "")  # Ensure source is never None
            
        except FileNotFoundError:
            print(f"Error: {self.file} file not found.")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {self.file}.")
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def write_file(self):
        rows = self.table.rowCount()

        out = {}
        for r in range(rows):
            save = False
            default = self.defaults[list(self.defaults.keys())[r]]
            row_data = {}
            match default["type"]:
                case 0: # regular soundtrack
                    match default["lock"]:
                        case 0: # no lock
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.item(r, 2).text(),
                                "artist": self.table.item(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                        case 1: # no album (FRICTION)
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.cellWidget(r, 2).text(),
                                "artist": self.table.item(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                        case 3: # artist/album sync
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.item(r, 2).text(),
                                "artist": self.table.item(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                        case 6: # stream/artist sync
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.item(r, 2).text(),
                                "artist": self.table.cellWidget(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                        case 7: # stream/artist/album sync
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.cellWidget(r, 2).text(),
                                "artist": self.table.cellWidget(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                        case 9: # song/album sync
                            row_data["strings"] = {
                                "title": self.table.item(r, 1).text(),
                                "album": self.table.item(r, 2).text(),
                                "artist": self.table.item(r, 3).text(),
                                "stream": self.table.cellWidget(r, 4).text()
                            }
                            row_data["source"] = self.table.cellWidget(r, 5).text()
                case 1: # burnout soundtrack
                    row_data["strings"] = {
                        "title": self.table.item(r, 1).text(),
                        "album": self.table.item(r, 2).text(),
                        "artist": self.table.item(r, 3).text(),
                        "stream": self.table.cellWidget(r, 4).text()
                    }
                    row_data["source"] = self.table.cellWidget(r, 5).text()
                case 2: # classical soundtrack
                    row_data["strings"] = {
                        "title": self.table.item(r, 1).text(),
                        "album": self.table.cellWidget(r, 2).text(),
                        "artist": self.table.item(r, 3).text(),
                        "stream": self.table.cellWidget(r, 4).text()
                    }
                    row_data["source"] = self.table.cellWidget(r, 5).text()
            
            for key, value in row_data["strings"].items():
                if value != default["defaults"][key]:
                    save = True
            
            if save:
                out[list(self.defaults.keys())[r]] = row_data
        
        with open(self.file, "w", encoding="utf-8") as file:
            json.dump(out, file, indent=2)
        
    
    def make_unique_cell(self, text, color: int) -> QTableWidgetItem:
        colors = [
            "#A8E6A1",  # pastel forest green (replacing pastel red)
            "#FFDFBA",  # pastel orange
            "#FFFFBA",  # pastel yellow
            "#BAFFC9",  # pastel green
            "#BAE1FF",  # pastel blue
            "#E3BAFF",  # pastel purple
            "#FFCCE5",  # pastel pink
            "#CCFFEE",  # mint
            "#FFD0AA",  # pastel peach
            "#FFF0BA",  # light gold
            "#FFD1DC",  # cotton candy pink
            "#C5E1A5",  # light lime
            "#F8BBD0",  # light rose
            "#D1C4E9",  # lavender
            "#B3E5FC"   # baby blue
        ]

        widget = QTableWidgetItem(text)
        widget.setBackground(QBrush(QColor(colors[color])))
        return widget
    

    def handle_item_changed(self, changed_item: QTableWidgetItem):
        self.changes = True
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


    def handle_selection_changed(self):
        selected = self.table.selectedIndexes()
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if isinstance(widget, LockedCellWidget):
                    if any(index.row() == row and index.column() == col for index in selected):
                        widget.setSelected(True)
                    else:
                        widget.setSelected(False)


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
        self.file = None
        self.load_data()
        self.changes = False
        self.update_window_title()
        
    def open_file(self):
        print("Load file action triggered")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Soundtrack Files (*.soundtrack)"
        )
        if file_path:
            self.file = file_path
            self.load_file()
            self.update_window_title()
            self.changes = False
            print(file_path)
        
    def save_file(self):
        print("Save file action triggered")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            "./" if not self.file else self.file,
            "Soundtrack Files (*.soundtrack)"
        )
        if file_path:
            self.file = file_path
            print(file_path)
            self.write_file()
            self.changes = False
        else:
            print("Save As... canceled")
        
    def export_file(self):
        print("Export file action triggered")
        
    def apply_action(self):
        print("Apply action triggered")
        # todo: change this to a yes/no dialogue that asks if you'd like to save before applying, if there are changes
        if self.changes and self.file:
            self.write_file()
        elif self.changes:
            self.save_file()
        self.progress = ProgressWidget("Applying Soundtrack...")
        self.progress.show()
        
        self.thread = QThread()
        self.worker = WriteWorker(self.settings, self.file, self.get_ptrs_hash() + ".json")
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.progress.set_progress)
        self.worker.finished.connect(self.progress.close)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.load_file)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

        
    def unapply_action(self):
        print("Unapply action triggered")
        self.progress = ProgressWidget("Reverting Changes...")
        self.progress.show()

        self.thread = QThread()
        self.worker = ResetWorker(self.settings)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.progress.set_progress)
        self.worker.finished.connect(self.progress.close)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        
    def reset_action(self):
        print("Reset action triggered")
        if self.changes:
            # Create the message box
            msg = QMessageBox()
            msg.setWindowTitle("Reset Soundtrack")
            msg.setText("Are you sure you want to reset to defaults?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.setIcon(QMessageBox.Question)

            # Show the message box and capture the response
            result = msg.exec_()

            if result != QMessageBox.Ok:
                return
            
        self.load_data()
        if self.file:
            self.load_file()
        self.changes = False
        
    def show_settings(self):
        print("Settings action triggered")
        dialog = SettingsDialog()
        if dialog.exec_():
            print("Settings updated")
        else:
            print("Settings canceled")
        
    def show_about(self):
        print("About action triggered")
        dialog = AboutDialog(self.get_ptrs_hash())
        if dialog.exec_():
            print("Showing About")

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