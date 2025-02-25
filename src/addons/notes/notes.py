
import os
import json

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtWidgets import (
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QShortcut,
    QTabWidget,
    QSizePolicy,
    QInputDialog,
    QMessageBox,
)
from PyQt5.QtGui import (
    QTextCursor,
    QPainter,
    QPen,
    QColor,
    QKeySequence,
)

from addon import AddOnBase

from ui.dialog import ConfirmationDialog
from ui.custom_button import RedButton, GrnButton
from ui.settings import UI_SCALE
from ui.utils import get_font


class NoteTab(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

        # Create QTextEdit within the QWidget
        self.text_edit = QTextEdit()
        self.text_edit.setFont(get_font(size=16))
        self.text_edit.textChanged.connect(self.save_text_to_file)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setStyleSheet(
            """
            QTextEdit {
                padding: 0px;
                margin: 0px;
                border: none;
                background-color: black;
            }
            
            """
        )

        # Load text into QTextEdit after it's been created
        self.load_text_from_file()

        # Add QTextEdit to layout with padding
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)

        # Set the margins
        layout.setContentsMargins(int(24 * UI_SCALE), int(24 * UI_SCALE), int(22 * UI_SCALE), int(22 * UI_SCALE))

        self.setLayout(layout)

    def load_text_from_file(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                self.text_edit.setPlainText(file.read())
            self.text_edit.moveCursor(QTextCursor.End)

    def save_text_to_file(self):
        with open(self.file_path, "w") as file:
            file.write(self.text_edit.toPlainText())




class CustomTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addTabButton = GrnButton(self)
        self.addTabButton.clicked.connect(parent.add_new_tab)
        
        # Set the background of the tab widget to be transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QTabWidget {
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
            }
            QTabBar::tab:selected {
                background: transparent;
            }
        """)
        
    def movePlusButton(self, no_of_tabs=0):
        """Move the plus button to the correct location."""
        w = self.count()
        if w > 0:
            rect = self.tabBar().tabRect(w - 1)
            self.addTabButton.move(rect.right() + 5, rect.top()+5)
        else:
            self.addTabButton.move(5, 5)


class JottingDownWindow(QWidget):
    window_toggle_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.window_toggle_signal.connect(self.toggle_window)

        self.notes_folder = "addons/notes/data"
        if not os.path.exists(self.notes_folder):
            os.makedirs(self.notes_folder)

        self.config_file = os.path.join(self.notes_folder, "config.json")
        self.tab_widget = CustomTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Set padding here
        self.setLayout(layout)

        layout.addWidget(self.tab_widget)

        self.load_tabs()

        new_tab_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        new_tab_shortcut.activated.connect(self.add_new_tab)

        self.setStyleSheet("""
            QWidget, QVBoxLayout {
                border: 1px solid;
                border-radius: 9px;
                background-color: white;
            }
        """)
        self.setFixedSize(int(650 * UI_SCALE), int(450 * UI_SCALE))
        self.old_pos = None


    def load_tabs(self):
        # Load existing .txt files in the notes folder as tabs
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as file:
                config = json.load(file)

            # Load tabs based on the order in config["files"]
            for tabno, file_path in enumerate(config["files"]):
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    note_tab = NoteTab(file_path)  # create an instance of NoteTab
                    self.tab_widget.addTab(note_tab, file_name)  # add the NoteTab instance, not the QTextEdit
                    self.add_button_to_tab(tabno)

            self.tab_widget.setCurrentIndex(config["last_active"])
        else:
            # If config file doesn't exist, load tabs by iterating
            # over files in the notes folder

            for tabno, file_name in enumerate(os.listdir(self.notes_folder)):
                if file_name.endswith(".txt"):
                    file_path = os.path.join(self.notes_folder, file_name)
                    self.tab_widget.addTab(NoteTab(file_path), file_name)
                    self.add_button_to_tab(tabno)
            # If no tabs are found after loading existing .txt files, add the
            #  default "notes" file
        if self.tab_widget.count() == 0:
            self.add_new_tab("notes")
        self.tab_widget.movePlusButton()

    def add_button_to_tab(self, tabno):
        self.button = RedButton(self.tab_widget, "radial")
        self.tab_widget.tabBar().setTabButton(tabno, 2, self.button)
        tab_text = self.tab_widget.tabBar().tabText(tabno)
        self.button.clicked.connect(lambda: self.delete_tab(tab_text))

    def save_tabs(self):
        config = {
            "files": [
                self.notes_folder + "/" + self.tab_widget.tabText(i)
                for i in range(self.tab_widget.count())
            ],
            "last_active": self.tab_widget.currentIndex(),
        }
        with open(self.config_file, "w") as file:
            json.dump(config, file)

    def delete_tab_text_file(self, file_name):
        file_path = os.path.join(self.notes_folder, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            QMessageBox.warning(self, "File Exists", f"{file_path} does not exist.")

    def delete_tab(self, tab_text):
        tabid = self.get_tab_number_from_text(tab_text)
        file_name = self.tab_widget.tabText(tabid)
        dialog = ConfirmationDialog(f"Delete tab {file_name}?")
        res = dialog.exec()
        if not res:
            return
        self.tab_widget.removeTab(tabid)
        self.delete_tab_text_file(file_name)
        self.tab_widget.movePlusButton()
        self.save_tabs()

    def get_tab_number_from_text(self, tab_text):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == tab_text:
                return i
        return -1

    def add_new_tab(self, file_name=""):
        if not file_name:
            file_name, ok = QInputDialog.getText(
                self, "New Note", "Enter the note name:"
            )
            if not ok or not file_name:
                return
        file_name = f"{file_name}.txt"


        file_path = os.path.join(self.notes_folder, file_name)
        if not os.path.exists(file_path):
            note_tab = NoteTab(file_path)  # create an instance of NoteTab
            self.tab_widget.addTab(note_tab, file_name)  # add the NoteTab instance, not the QTextEdit
            self.add_button_to_tab(len(self.tab_widget) - 1)
            self.tab_widget.movePlusButton()
            self.save_tabs()


        else:
            QMessageBox.warning(
                self, "File Exists", f"A file with the name {file_name} already exists."
            )

    def toggle_window(self) -> None:
        if self.isHidden():
            window.show()
            window.activateWindow()
            if current_widget := self.tab_widget.currentWidget():
                current_widget.setFocus()
        else:
            window.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if not self.old_pos:
            return
        delta = QPoint(event.globalPos() - self.old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None

    def closeEvent(self, event):
        self.save_tabs()


window = JottingDownWindow()

AddOnBase().activate = window.window_toggle_signal.emit
AddOnBase().set_activate_shortcut(QKeySequence("Ctrl+`"))