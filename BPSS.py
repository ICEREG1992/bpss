import os
import sys
import json
import hashlib
import zipfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QHeaderView, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QVBoxLayout,
                            QTableWidgetItem, QHBoxLayout, QWidget, QToolBar, QAction, QStyle, QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread, QEvent, QItemSelectionModel
from PyQt5.QtGui import QBrush, QColor, QIcon, QPixmap, QKeySequence
import mutagen

from Disambiguate import DisambiguateDialog
from Settings import SettingsDialog
from LockedCell import LockedCellWidget
from FileBrowseCell import FileBrowseCellWidget
from Progress import ProgressWidget
from Workers import ResetWorker, WriteWorker, LoadWorker
from About import AboutDialog
from Helpers import col_to_key, resource_path

SETTINGS_FILE = "settings.json"
BLANK_ROW = {'strings': {'title': '', 'album': '', 'artist': '', 'stream': ''}, 'source': ''}

class SoundtrackViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Burnout Paradise Soundtrack Switcher")
        self.setWindowIcon(QIcon(resource_path("media/bpss.png")))
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
        self.defaults_file = resource_path("defaults.json")

        # Create toolbar
        self.create_toolbar()
        
        # Create central widget to hold table
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QHBoxLayout(central_widget)

        # Load settings
        self.settings = self.load_settings()
        if not self.validate_settings():
            dialog = SettingsDialog(first=True)
            if dialog.exec_():
                print("First time settings updated")
                # force a reload of settings
                self.settings = self.load_settings()
            else:
                print("Settings canceled")
                QMessageBox.warning(self, "Missing Input", "You will be unable to apply new soundtracks until you set all settings.")
        
        # Load defaults
        self.defaults = self.load_defaults()

        # Create table widget
        self.create_table()

        # Add table to layout
        self.layout.addWidget(self.table, 3)

        self.actions = None

        # Create actions widget
        if "actions" in self.settings.keys():
            if self.settings["actions"]:
                self.create_actions()
                self.layout.addWidget(self.actions, 1)
                self.actions_action.setChecked(True)
        else:
            self.settings["actions"] = False
            self.write_settings()
    
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
    
    def write_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)
    
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
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(toolbar)
        
        # File operations
        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Open", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        export_action = QAction(self.style().standardIcon(QStyle.SP_DriveFDIcon), "Export", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_file)
        toolbar.addAction(export_action)
        
        # First vertical spacer
        toolbar.addSeparator()
        
        # Filter/Apply operations
        apply_action = QAction(self.style().standardIcon(QStyle.SP_DialogApplyButton), "Apply", self)
        apply_action.setShortcut(QKeySequence("Ctrl+Return"))
        apply_action.triggered.connect(self.apply_action)
        toolbar.addAction(apply_action)
        
        unapply_action = QAction(self.style().standardIcon(QStyle.SP_DialogCancelButton), "Unapply", self)
        unapply_action.setShortcut(QKeySequence("Ctrl+Shift+Return"))
        unapply_action.triggered.connect(self.unapply_action)
        toolbar.addAction(unapply_action)
        
        reset_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Reset", self)
        reset_action.setShortcut(QKeySequence("Ctrl+R"))
        reset_action.triggered.connect(self.reset_action)
        toolbar.addAction(reset_action)
        
        # Second vertical spacer
        toolbar.addSeparator()

        # Actions pane
        self.actions_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Actions", self)
        self.actions_action.setShortcut(QKeySequence("Space"))
        self.actions_action.triggered.connect(self.toggle_actions)
        self.actions_action.setCheckable(True)
        toolbar.addAction(self.actions_action)
        
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
        self.table.setSortingEnabled(False)

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
            print(f"Generating new ptrs for {filename}")
            
            self.progress = ProgressWidget("Finding pointers...")
            self.progress.show()
            
            self.thread = QThread()
            self.progress.worker_thread = self.thread
            self.worker = LoadWorker(self.settings, filename)
            self.worker.moveToThread(self.thread)

            # Connect signals
            self.thread.started.connect(self.worker.run)
            self.worker.progress_changed.connect(self.progress.set_progress)
            self.thread.finished.connect(self.progress.close)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.finished.connect(self.fill_table)
            self.thread.finished.connect(self.thread.deleteLater)

            self.worker.error.connect(self.handle_load_exception)
            
            self.thread.start()

    def fill_table(self):
        try:
            self.settings = self.load_settings()
            if not self.get_ptrs_hash():
                return
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
                # if this is BurnoutPR, don't show cut songs
                if "BurnoutPR" in self.settings.get("game", "") and not self.settings.get("mod", False):
                    self.table.setRowHidden(24, True)
                    self.table.setRowHidden(25, True)
                    index_flag = True
                else:
                    self.table.setRowHidden(24, False)
                    self.table.setRowHidden(25, False)
                    index_flag = False

                # Get strings data (title, stream, album, artist)
                strings = entry.get("strings", {})
                title = strings.get("title", "")
                album = strings.get("album", "")
                artist = strings.get("artist", "")
                stream = strings.get("stream", "")
                
                # Get override data
                overrides = entry.get("overrides", {})
                
                # Create index item with proper numeric sorting
                index_item = QTableWidgetItem()
                final_index = row_index + 1 if (not (index_flag and row_index >= 26)) else row_index - 1
                index_item.setData(Qt.DisplayRole, final_index)  # Store as number for sorting
                index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
                index_item.setTextAlignment(Qt.AlignCenter)

                # Create file browse widget with update hook
                file_browse_widget = FileBrowseCellWidget("")
                
                match self.defaults[key]["type"]:
                    case 0: # regular soundtrack
                        match self.defaults[key]["lock"]:
                            case 0: # no lock
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)
                            case 1: # no album (FRICTION)
                                album_ptrs = entry.get("ptrs").get("album")
                                if len(album_ptrs) > 1:
                                    stock[album] = album_ptrs[1:]
                                    album_color = len(sync)
                                    sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2)]
                                    self.table.setItem(row_index, 2, self.make_unique_cell(album, album_color))
                                    if overrides.get("album"):
                                        self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, album_color, overrides.get("album")))
                                elif len(album_ptrs) == 0:
                                    backfill.append([row_index, 2, key, 0])
                                else:
                                    self.table.setItem(row_index, 2, QTableWidgetItem(album)) # false alarm, no need for synced cell
                                
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                # look above for album cell
                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)
                            case 3: # artist/album sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))

                                sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2), (row_index, 3)]
                                song_color = list(sync).index(self.defaults[key]["defaults"]["album"])
                                if overrides.get("album"):
                                    self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, song_color, overrides.get("album")))
                                else:
                                    self.table.setItem(row_index, 2, self.make_unique_cell(album, song_color))
                                
                                if overrides.get("artist"):
                                    self.table.setItem(row_index, 3, self.make_disambiguated_cell(artist, song_color, overrides.get("artist")))
                                else:
                                    self.table.setItem(row_index, 3, self.make_unique_cell(artist, song_color))

                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)
                            case 6: # stream/artist sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                self.table.setItem(row_index, 2, QTableWidgetItem(album))
                                if overrides.get("artist"):
                                    self.table.setItem(row_index, 3, self.make_disambiguated_cell(artist, artist, overrides.get("artist")))
                                else:
                                    self.table.setCellWidget(row_index, 3, LockedCellWidget(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)
                            case 7: # stream/artist/album sync
                                self.table.setItem(row_index, 0, index_item)
                                self.table.setItem(row_index, 1, QTableWidgetItem(title))
                                if overrides.get("album"):
                                    self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, album, overrides.get("album")))
                                else:
                                    self.table.setCellWidget(row_index, 2, LockedCellWidget(album))
                                if overrides.get("artist"):
                                    self.table.setItem(row_index, 3, self.make_disambiguated_cell(artist, artist, overrides.get("artist")))
                                else:
                                    self.table.setCellWidget(row_index, 3, LockedCellWidget(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)

                            case 9: # song/album sync                               
                                self.table.setItem(row_index, 0, index_item)

                                sync[self.defaults[key]["defaults"]["title"]] = [(row_index, 1), (row_index, 2)]
                                song_color = list(sync).index(self.defaults[key]["defaults"]["title"])
                                
                                if overrides.get("title"):
                                    self.table.setItem(row_index, 1, self.make_disambiguated_cell(title, song_color, overrides.get("title")))
                                else:
                                    self.table.setItem(row_index, 1, self.make_unique_cell(title, song_color))
                                
                                if overrides.get("album"):
                                    self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, song_color, overrides.get("album")))
                                else:
                                    self.table.setItem(row_index, 2, self.make_unique_cell(album, song_color))

                                self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                                self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                                self.table.setCellWidget(row_index, 5, file_browse_widget)

                    case 1: # burnout soundtrack
                        # steal any duplicate strings
                        artist_ptrs = entry.get("ptrs").get("artist")
                        if len(artist_ptrs) > 1:
                            stock[artist] = artist_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["artist"]] = [(row_index, 3)]
                            artist_color = list(sync).index(self.defaults[key]["defaults"]["artist"])
                            self.table.setItem(row_index, 3, self.make_unique_cell(artist, artist_color))
                            if overrides.get("artist"):
                                self.table.setItem(row_index, 3, self.make_disambiguated_cell(artist, album_color, overrides.get("artist")))
                                
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, key, 1])
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        album_ptrs = entry.get("ptrs").get("album")
                        if len(album_ptrs) > 1:
                            stock[album] = album_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2)]
                            album_color = list(sync).index(self.defaults[key]["defaults"]["album"])
                            self.table.setItem(row_index, 2, self.make_unique_cell(album, album_color))
                            if overrides.get("album"):
                                self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, album_color, overrides.get("album")))
                                
                        elif len(album_ptrs) == 0:
                            backfill.append([row_index, 2, key, 0])
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
                            if overrides.get("artist"):
                                self.table.setItem(row_index, 3, self.make_disambiguated_cell(artist, album_color, overrides.get("artist")))
                                
                        elif len(artist_ptrs) == 0:
                            backfill.append([row_index, 3, key, 3])
                        else:
                            self.table.setItem(row_index, 3, QTableWidgetItem(artist))
                        
                        album_ptrs = entry.get("ptrs").get("album")
                        if len(album_ptrs) > 1:
                            stock[album] = album_ptrs[1:]
                            sync[self.defaults[key]["defaults"]["album"]] = [(row_index, 2)]
                            album_color = list(sync).index(self.defaults[key]["defaults"]["album"])
                            self.table.setItem(row_index, 2, self.make_unique_cell(album, album_color))
                            if overrides.get("album"):
                                self.table.setItem(row_index, 2, self.make_disambiguated_cell(album, album_color, overrides.get("album")))
                                
                        elif len(album_ptrs) == 0:
                            backfill.append([row_index, 2, key, 0])
                        else:
                            self.table.setItem(row_index, 2, QTableWidgetItem(album))

                        self.table.setItem(row_index, 0, index_item)
                        self.table.setItem(row_index, 1, QTableWidgetItem(title))
                        # look above for album cell
                        # look above for artist cell
                        self.table.setCellWidget(row_index, 4, LockedCellWidget(stream))
                        self.table.setCellWidget(row_index, 5, file_browse_widget)  # Ensure source is never None

            # backfill
            for i in backfill:
                column = col_to_key(i[1])
                default_value = self.defaults[i[2]]["defaults"][column]
                sync[default_value].append((i[0], i[1]))
                stock[default_value].pop()
                unique_color = list(sync).index(default_value)
                self.table.setItem(i[0], i[1], self.make_unique_cell(default_value, unique_color))
                if ptrs[i[2]].get("overrides") and ptrs[i[2]]["overrides"].get(column):
                    self.table.setItem(i[0], i[1], self.make_disambiguated_cell(default_value, unique_color, ptrs[i[2]]["overrides"].get(column)))   

            # populate table sync
            for k in sync.keys():
                self.synced_cells.append(sync[k])
            
            # fix column sizes
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.table.setColumnWidth(0, 30)  # Set to 30 pixels wide

            for col in range(1, self.table.columnCount()):
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        
        except FileNotFoundError:
            QMessageBox.critical(self, "Critical Error", f"Fill Error: Pointers file \"{self.get_ptrs_hash()}.json\" not found. Try pressing Reset.")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Critical Error", f"Fill Error: Invalid JSON in \"{self.get_ptrs_hash()}.json\". Try pressing Reset.")
        except Exception as e:
            QMessageBox.critical(self, "Critical Error", f"Fill Error: {e}")
    
    def load_file(self):
        # get data from file
        try:
            self.settings = self.load_settings()
            # Load JSON data
            if (self.file):
                with open(self.file, "r") as file:
                    st = json.load(file)

                # Edit table
                for (key, entry) in st.items():
                    row_index = list(self.defaults.keys()).index(key)
                    self.set_table_row(row_index, entry)
                    # Hack to handle zip source paths
                    if "zip" in entry.keys():
                        self.table.cellWidget(row_index, 5).setText(os.path.join(os.path.dirname(self.file), entry.get("zip", "")))
            
        except FileNotFoundError:
            QMessageBox.critical(self, "Critical Error", f"Load Error: Pointers file \"{self.file}\" not found.")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Critical Error", f"Load Error: Invalid JSON in \"{self.file}\".")
        except Exception as e:
            QMessageBox.critical(self, "Critical Error", f"Load Error: {e}")
    
    def write_file(self, export = False):
        rows = self.table.rowCount()

        out = {}
        for r in range(rows):
            save = False
            default = self.defaults[list(self.defaults.keys())[r]]
            row_data = self.get_table_row(r)
            
            for key, value in row_data["strings"].items():
                if value != default["defaults"][key]:
                    save = True

            if export:
                # convert source to relative path at "zip" if exporting
                source_path = row_data.get("source", "")
                if source_path:
                    row_data["zip"] = os.path.basename(source_path)
            
            if save:
                out[list(self.defaults.keys())[r]] = row_data
        
        with open(self.file, "w", encoding="utf-8") as file:
            json.dump(out, file, indent=2)
        
    
    def make_unique_cell(self, text, color) -> QTableWidgetItem:
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
        if isinstance(color, int):
            widget.setBackground(QBrush(QColor(colors[color])))
        else:
            widget.setBackground(color)
        return widget
    
    def make_disambiguated_cell(self, text, prev_color, override) -> QTableWidgetItem:
        widget = QTableWidgetItem(QIcon(resource_path("media/star.png")), text)
        widget.disambiguated = True
        widget.prev_color = prev_color
        widget.setToolTip(str(override))
        return widget

    def handle_item_changed(self, changed_item: QTableWidgetItem):
        self.changes = True
        row = changed_item.row()
        col = changed_item.column()
        text = changed_item.text()

        # handle synced cells
        for group in self.synced_cells:
            if (row, col) in group and not hasattr(self.get_item_or_cellwidget(row, col), "disambiguated"):
                for (r, c) in group:
                    if (r, c) != (row, col) and not hasattr(self.get_item_or_cellwidget(r, c), "disambiguated"):
                        self.get_item_or_cellwidget(r, c).setText(text)
                break  # Only one group per cell

    def handle_selection_changed(self):
        selected = self.table.selectedIndexes()
        # handle selection and de-selection of cellwidgets with a full table sweep
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if isinstance(widget, LockedCellWidget):
                    if any(index.row() == row and index.column() == col for index in selected):
                        widget.setSelected(True)
                    else:
                        widget.setSelected(False)
        # show/hide disambiguate button if actions pane is open
        if self.actions:
            self.disambiguate_btn.hide()
            self.undisambiguate_btn.hide()
            if len(selected) == 1:
                cell = selected[0]
                if self.is_disambiguatable(cell):
                    self.disambiguate_btn.show()
                if hasattr(self.get_item_or_cellwidget(cell.row(), cell.column()), "disambiguated"):
                    self.undisambiguate_btn.show()

    def is_disambiguatable(self, cell):
        row = cell.row()
        col = cell.column()
        key = list(self.defaults.keys())[row]
        match self.defaults[key]["type"]:
            case 0: # regular soundtrack
                match self.defaults[key]["lock"]:
                    case 1:
                        if col == 2:
                            return True
                    case 3:
                        if col == 2 or col == 3:
                            return True
                    case 6:
                        if col == 3:
                            return True
                    case 7:
                        if col == 2 or col == 3:
                            return True
                    case 9:
                        if col == 1 or col == 2:
                            return True
            case 1: # burnout soundtrack
                if col == 2 or col == 3:
                    return True
            case 2: # classical soundtrack
                if col == 2 or col == 3:
                    return True


    def create_actions(self):
        # Right side - actions panel (takes 1/3 of space)
        actions_frame = QFrame()
        actions_frame.setFrameStyle(QFrame.StyledPanel)
        actions_layout = QVBoxLayout(actions_frame)

        # Song manipulation shortcuts
        self.action_move_up = QAction("Move Song Up", self)
        self.action_move_up.setShortcut(QKeySequence("Ctrl+Up"))
        self.action_move_up.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.action_move_up.triggered.connect(self.move_song_up)
        self.addAction(self.action_move_up)  # Needed so shortcut works

        self.action_move_down = QAction("Move Song Down", self)
        self.action_move_down.setShortcut(QKeySequence("Ctrl+Down"))
        self.action_move_down.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.action_move_down.triggered.connect(self.move_song_down)
        self.addAction(self.action_move_down)

        # Song manipulation actions
        move_up_btn = QPushButton(self.action_move_up.text())
        move_up_btn.setStyleSheet("text-align: left;")
        move_up_btn.setIcon(self.action_move_up.icon())
        move_up_btn.clicked.connect(self.action_move_up.trigger)

        move_down_btn = QPushButton(self.action_move_down.text())
        move_down_btn.setStyleSheet("text-align: left;")
        move_down_btn.setIcon(self.action_move_down.icon())
        move_down_btn.clicked.connect(self.action_move_down.trigger)
        
        # File operations
        clear_btn = QPushButton("Clear Song")
        clear_btn.setStyleSheet("text-align: left;")
        clear_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_btn.clicked.connect(self.clear_song)

        # insert_btn = QPushButton("Insert New Song")
        # insert_btn.setStyleSheet("text-align: left;")
        # insert_btn.setIcon(QIcon(QPixmap(resource_path("media/plus.png")).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        # insert_btn.clicked.connect(self.insert_song)

        # Disambiguation
        self.disambiguate_btn = QPushButton("Disambiguate Cell")
        self.disambiguate_btn.setStyleSheet("text-align: left;")
        self.disambiguate_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton))
        self.disambiguate_btn.clicked.connect(self.disambiguate_cell)
        self.disambiguate_btn.hide()

        self.undisambiguate_btn = QPushButton("Un-disambiguate Cell")
        self.undisambiguate_btn.setStyleSheet("text-align: left;")
        self.undisambiguate_btn.setIcon(self.style().standardIcon(QStyle.SP_LineEditClearButton))
        self.undisambiguate_btn.clicked.connect(self.undisambiguate_cell)
        self.undisambiguate_btn.hide()
        
        # Add to layout
        actions_layout.addWidget(move_up_btn)
        actions_layout.addWidget(move_down_btn)
        # actions_layout.addWidget(insert_btn)
        actions_layout.addWidget(clear_btn)
        actions_layout.addWidget(self.disambiguate_btn)
        actions_layout.addWidget(self.undisambiguate_btn)
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
            os.path.dirname(self.settings["prev"]) if self.settings["prev"] else "",
            "Soundtrack or Zip Files (*.soundtrack *.zip)"
        )
        if not file_path:
            return
        if file_path.lower().endswith(".zip"):
            temp_dir = os.path.join("temp", os.path.splitext(os.path.basename(file_path))[0])
            os.makedirs(temp_dir, exist_ok=True)

            with zipfile.ZipFile(file_path, "r") as z:
                z.extractall(temp_dir)

            candidates = [
                os.path.join(temp_dir, f)
                for f in os.listdir(temp_dir)
                if f.lower().endswith(".soundtrack")
            ]

            if not candidates:
                print("Zip contains no .soundtrack file")
                return

            soundtrack_path = candidates[0]
            self.file = soundtrack_path

        else:
            self.file = file_path

        self.load_data()
        self.load_file()
        self.update_window_title()
        self.changes = False
        self.settings["prev"] = self.file
        self.write_settings()
        print(self.file)
        
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
            self.update_window_title()
        else:
            print("Save As... canceled")
        
    def export_file(self):
        print("Export file action triggered")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export File To",
            "./" if not self.file else os.path.splitext(self.file)[0] + ".zip",
            "Zip Files (*.zip)"
        )
        if not file_path:
            print("Export canceled")
            return

        self.file = os.path.join("temp", os.path.splitext(os.path.basename(file_path))[0] + ".soundtrack")
        print(self.file)
        self.write_file(export = True)

        print("Creating archive at", file_path)

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(self.file, os.path.basename(self.file))

            rows = self.table.rowCount()

            for r in range(rows):
                source_path = self.table.cellWidget(r, 5)
                if not source_path:
                    print("No source path for row", r)
                    continue
                src = source_path.text()
                if src:
                    if self.validate_file(src, r):
                        print("Adding", src, "to archive")
                        z.write(src, os.path.basename(src))
                    else:
                        print("failed validation")
                        return

    def handle_apply_exception(self, e):
        self.handle_worker_exception("Apply", e)

    def handle_unapply_exception(self, e):
        self.handle_worker_exception("Unapply", e)

    def handle_load_exception(self, e):
        self.handle_worker_exception("Load", e)
    
    def handle_worker_exception(self, type, e):
        QMessageBox.critical(self, f"Critical Error", f"{type} Error: {e}")            
        
    def apply_action(self):
        print("Apply action triggered")
        # todo: change this to a yes/no dialogue that asks if you'd like to save before applying, if there are changes
        if self.changes and self.file:
            self.write_file()
        elif self.changes:
            self.save_file()

        # make sure all of the files are legit
        rows = self.table.rowCount()
        for r in range(rows):
            source = self.table.cellWidget(r, 5).text()
            if source:
                if not self.validate_file(source, r):
                    return
        
        self.thread = QThread()
        self.worker = WriteWorker(self.settings, self.file, str(self.get_ptrs_hash()) + ".json")
        self.worker.moveToThread(self.thread)

        self.progress = ProgressWidget("Applying Soundtrack...")
        self.progress.worker_thread = self.thread
        self.progress.show()

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.progress.set_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.progress.close)
        self.thread.finished.connect(self.load_file)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.handle_apply_exception)
        
        self.thread.start()

    def validate_file(self, source, r):
        if not os.path.isfile(source):
            QMessageBox.warning(self, "Missing File", f"Could not find source file for {self.get_item_or_cellwidget(r, 1).text()}.")
            return False
        
        if not source.lower().endswith(('.wav', '.mp3', '.aiff')):
            QMessageBox.warning(self, "Incorrect Format", f"Source file for {self.get_item_or_cellwidget(r, 1).text()} is not wav, mp3, or aiff.")
            return False
        elif source.lower().endswith(('.mp3')):
            # codec check
            audio = mutagen.File(source)
            if audio.__class__.__name__ == "MP4":
                QMessageBox.warning(self, "Unsupported Codec", f"The source file for {self.get_item_or_cellwidget(r, 1).text()} uses an unsupported codec (mp4a). Please use the mpga codec or covert it to a different audio format.")
                return False
            
        return True


    def unapply_action(self):
        print("Unapply action triggered")

        self.thread = QThread()
        self.worker = ResetWorker(self.settings)
        self.worker.moveToThread(self.thread)

        self.progress = ProgressWidget("Reverting Changes...")
        self.progress.worker_thread = self.thread
        self.progress.show()

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.progress.set_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.progress.close)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.handle_unapply_exception)

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
            msg.setWindowIcon(QIcon(resource_path("media/bpss.png")))

            # Show the message box and capture the response
            result = msg.exec_()

            if result != QMessageBox.Ok:
                return
            
        self.load_data()
        if self.file:
            self.load_file()
        self.changes = False

    def toggle_actions(self):
        print("Toggle actions pane")
        if self.actions:
            self.layout.removeWidget(self.actions)
            self.actions.hide()
            self.actions = None
            self.settings["actions"] = False
            self.write_settings()
            self.actions_action.setChecked(False)
        else:
            self.create_actions()
            self.layout.addWidget(self.actions, 1)
            self.settings["actions"] = True
            self.write_settings()
            self.actions_action.setChecked(True)
            self.handle_selection_changed()

    def show_settings(self):
        print("Settings action triggered")
        prev_hash = self.get_ptrs_hash()
        prev_mod = self.settings.get("mod", False)
        dialog = SettingsDialog()
        if dialog.exec_():
            print("Settings updated")
            self.settings = self.load_settings()
            if self.get_ptrs_hash() != prev_hash:
                # create a new pts json
                filename = self.get_ptrs_hash() + ".json"
                if not os.path.isfile(filename):
                    print(f"Generating new ptrs for {filename}")
                    
                    self.progress = ProgressWidget("Finding pointers...")
                    self.progress.show()
                    
                    self.thread = QThread()
                    self.progress.thread = self.thread
                    self.worker = LoadWorker(self.settings, filename)
                    self.worker.moveToThread(self.thread)

                    # Connect signals
                    self.thread.started.connect(self.worker.run)
                    self.worker.progress_changed.connect(self.progress.set_progress)
                    self.worker.finished.connect(self.progress.close)
                    self.worker.finished.connect(self.thread.quit)
                    self.worker.finished.connect(self.worker.deleteLater)
                    self.worker.finished.connect(self.fill_table)
                    self.thread.finished.connect(self.thread.deleteLater)
                    
                    self.thread.start()
                else:
                    self.fill_table()
            if prev_mod != self.settings.get("mod", False):
                self.reset_action()
        else:
            print("Settings canceled")
        
    def show_about(self):
        print("About action triggered")
        dialog = AboutDialog(self.get_ptrs_hash())
        if dialog.exec_():
            print("Showing About")

    def move_song_up(self):
        self.move_song(down=False)

    def move_song_down(self):
        self.move_song(down=True)
    
    def move_song(self, down):
        print("Move song down action triggered")
        row = self.table.currentRow()
        col = self.table.currentColumn()
        next_row = (row+1) % self.table.rowCount() if down else (row-1) % self.table.rowCount()

        row_data = self.get_table_row(row, inner=True)
        below_data = self.get_table_row(next_row, inner=True)
        print(str(below_data))

        self.set_table_row(row, below_data, inner=True)
        self.set_table_row(next_row, row_data, inner=True)

        index = self.table.model().index(next_row, col)

        # Clear existing selection and select this index
        
        self.table.setCurrentIndex(index)
        self.table.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)


    def insert_song(self):
        print("Insert blank song action triggered")
        
    def clear_song(self):
        print("Delete song action triggered")
        row = self.table.currentRow()
        self.set_table_row(row, BLANK_ROW, inner=True)

    def play_song(self):
        print("Play song action triggered")

    def disambiguate_cell(self):
        print("Disambiguating cell")

        selected = self.table.selectedIndexes()[0]
        key = list(self.defaults.keys())[selected.row()]
        row = selected.row()
        col = selected.column()

        cell = self.get_item_or_cellwidget(row, col)

        # TODO if cell is locked, show warning here
        if isinstance(cell, LockedCellWidget) and self.settings["warn"]:
            msg = QMessageBox()
            msg.setWindowTitle("Warning")
            msg.setText("Disambiguating a locked cell can lead to crashes when viewing or playing the associated song. Would you like to continue?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowIcon(QIcon(resource_path("media/bpss.png")))

            # Show the message box and capture the response
            result = msg.exec_()

            if result != QMessageBox.Ok:
                return

        dialog = DisambiguateDialog(self.get_ptrs_hash(), key, col)
        if dialog.exec_():
            print("Disambiguation submitted")
            # remove cell color, add disambiguated tag, replace cell widget
            if isinstance(cell, LockedCellWidget):
                cell = self.table.cellWidget(row, col)
                self.table.setItem(row, col, self.make_disambiguated_cell(cell.text(), cell.text(), dialog.selected_option()))
                self.table.setCellWidget(row, col, None)
            else:
                self.table.setItem(row, col, self.make_disambiguated_cell(cell.text(), cell.background(), dialog.selected_option()))
            # reveal Un-disambiguate button
            self.undisambiguate_btn.show()
        else:
            print("Disambiguation canceled")

    def undisambiguate_cell(self):
        print("Undisambiguating cell")
        selected = self.table.selectedIndexes()[0]
        key = list(self.defaults.keys())[selected.row()]

        # remove entry from the overrides object
        try:
            filename = str(self.get_ptrs_hash()) + ".json"
            if os.path.isfile(filename):
                with open(filename, "r") as file:
                    ptrs = json.load(file)
                del ptrs[key]["overrides"][col_to_key(selected.column())]
                if len(ptrs[key]["overrides"]) == 0:
                    del ptrs[key]["overrides"]
                with open(filename, "w") as file:
                    json.dump(ptrs, file, indent=2)

        except FileNotFoundError:
            QMessageBox.critical(self, "Critical Error", f"Undisambiguate Error: Pointers file \"{self.get_ptrs_hash()}.json\" not found. Try pressing Reset.")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Critical Error", f"Undisambiguate Error: Invalid JSON in \"{self.get_ptrs_hash()}.json\". Try pressing Reset.")
        except Exception as e:
            QMessageBox.critical(self, "Critical Error", f"Undisambiguate Error: {e}")
        # revert cell to previous state
        # test for locked cell via jank method
        cell = self.table.item(selected.row(), selected.column())
        if isinstance(cell.prev_color, QBrush) or isinstance(cell.prev_color, int):
            self.table.setItem(selected.row(), selected.column(), self.make_unique_cell(cell.text(), cell.prev_color))
        else:
            self.table.setItem(selected.row(), selected.column(), None)
            self.table.setCellWidget(selected.row(), selected.column(), LockedCellWidget(cell.prev_color))
        self.undisambiguate_btn.show()
    
    def get_item_or_cellwidget(self, row, col):
        if self.table.item(row, col):
            return self.table.item(row, col)
        else:
            return self.table.cellWidget(row, col)
    
    def get_table_row(self, ind, inner=False):
        print("Getting table row " + str(ind))
        row_data = {}
        default = self.defaults[list(self.defaults.keys())[ind]]
        match default["type"]:
            case 0: # regular soundtrack
                match default["lock"]:
                    case 0: # no lock
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
                    case 1: # no album (FRICTION)
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 2), "innerText"):
                            row_data["strings"]["album"] = self.get_item_or_cellwidget(ind, 2).innerText
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
                    case 3: # artist/album sync
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 2), "innerText"):
                            row_data["strings"]["album"] = self.get_item_or_cellwidget(ind, 2).innerText
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
                    case 6: # stream/artist sync
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 3), "innerText"):
                            row_data["strings"]["artist"] = self.get_item_or_cellwidget(ind, 3).innerText
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
                    case 7: # stream/artist/album sync
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 2), "innerText"):
                            row_data["strings"]["album"] = self.get_item_or_cellwidget(ind, 2).innerText
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 3), "innerText"):
                            row_data["strings"]["artist"] = self.get_item_or_cellwidget(ind, 3).innerText
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
                    case 9: # song/album sync
                        row_data["strings"] = {
                            "title": self.get_item_or_cellwidget(ind, 1).text(),
                            "album": self.get_item_or_cellwidget(ind, 2).text(),
                            "artist": self.get_item_or_cellwidget(ind, 3).text(),
                            "stream": self.get_item_or_cellwidget(ind, 4).text()
                        }
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 1), "innerText"):
                            row_data["strings"]["title"] = self.get_item_or_cellwidget(ind, 1).innerText
                        if inner and hasattr(self.get_item_or_cellwidget(ind, 2), "innerText"):
                            row_data["strings"]["album"] = self.get_item_or_cellwidget(ind, 2).innerText
                        row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
            case 1: # burnout soundtrack
                row_data["strings"] = {
                    "title": self.get_item_or_cellwidget(ind, 1).text(),
                    "album": self.get_item_or_cellwidget(ind, 2).text(),
                    "artist": self.get_item_or_cellwidget(ind, 3).text(),
                    "stream": self.get_item_or_cellwidget(ind, 4).text()
                }
                row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
            case 2: # classical soundtrack
                row_data["strings"] = {
                    "title": self.get_item_or_cellwidget(ind, 1).text(),
                    "album": self.get_item_or_cellwidget(ind, 2).text(),
                    "artist": self.get_item_or_cellwidget(ind, 3).text(),
                    "stream": self.get_item_or_cellwidget(ind, 4).text()
                }
                row_data["source"] = self.get_item_or_cellwidget(ind, 5).text()
        
        return row_data

    def set_table_row(self, ind, row, inner=False):
        print("Setting table row " + str(ind))
        strings = row.get("strings", "")
        title = strings.get("title", "")
        album = strings.get("album", "")
        artist = strings.get("artist", "")
        stream = strings.get("stream", "")
        
        # Get source and file
        source = row.get("source", "")

        key = list(self.defaults.keys())[ind]

        print(title)

        if not inner:
            self.table.cellWidget(ind, 4).setText(stream)

        # Apply soundtrack content
        match self.defaults[key]["type"]:
            case 0: # regular soundtrack
                match self.defaults[key]["lock"]:
                    case 0: # no lock
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        self.get_item_or_cellwidget(ind, 2).setText(album)
                        self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
                    case 1: # no album (FRICTION)
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        if inner:
                            self.get_item_or_cellwidget(ind, 2).innerText = album
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                        else:
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                        self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
                    case 3: # artist/album sync
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        if inner:
                            self.get_item_or_cellwidget(ind, 2).innerText = album
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                        else:
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                        self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
                    case 6: # stream/artist sync
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        self.get_item_or_cellwidget(ind, 2).setText(album)
                        if inner:
                            if hasattr(self.get_item_or_cellwidget(ind, 3), "disambiguated"):
                                self.get_item_or_cellwidget(ind, 3).setText(artist)
                            else:
                                self.get_item_or_cellwidget(ind, 3).innerText = artist
                        else:
                            self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
                    case 7: # stream/artist/album sync
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        if inner:
                            if hasattr(self.get_item_or_cellwidget(ind, 2), "disambiguated"):
                                self.get_item_or_cellwidget(ind, 2).setText(album)
                            else:
                                self.get_item_or_cellwidget(ind, 2).innerText = album
                            if hasattr(self.get_item_or_cellwidget(ind, 3), "disambiguated"):
                                self.get_item_or_cellwidget(ind, 3).setText(artist)
                            else:
                                self.get_item_or_cellwidget(ind, 3).innerText = artist
                        else:
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                            self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
                    case 9: # song/album sync
                        if inner:
                            self.get_item_or_cellwidget(ind, 2).innerText = album
                            self.get_item_or_cellwidget(ind, 2).setText(album)
                        else:
                            self.get_item_or_cellwidget(ind, 2).setText(album) # do it out of order so events propagate and prioritize title
                        self.get_item_or_cellwidget(ind, 1).setText(title)
                        self.get_item_or_cellwidget(ind, 3).setText(artist)
                        self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None

            case 1: # burnout soundtrack
                self.get_item_or_cellwidget(ind, 1).setText(title)
                self.get_item_or_cellwidget(ind, 2).setText(album)
                self.get_item_or_cellwidget(ind, 3).setText(artist)
                self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None
            case 2: # classical soundtrack
                self.get_item_or_cellwidget(ind, 1).setText(title)
                self.get_item_or_cellwidget(ind, 2).setText(album)
                self.get_item_or_cellwidget(ind, 3).setText(artist)
                self.get_item_or_cellwidget(ind, 5).setText(source or "")  # Ensure source is never None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = SoundtrackViewer()
    viewer.show()
    sys.exit(app.exec_())