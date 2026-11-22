"""
The Audio category: the open pack's sound banks and sounds in folders (language, then the bank that plays a sound),
from the paths the game's file list gives their hashed names. Selecting a sound previews it; double-clicking opens it
in the Audio Viewer. Attached by gui.addons in the place of the plain "Audio" file-list category.
"""

import os

from PySide6 import QtCore, QtWidgets

from core.logger import get_logger
from core.npk import wwise_names
from core.npk.enums import NPKEntryFileCategories
from gui import addons
from gui.utils.file_list_theme import follow_file_list_theme, tree_icons
from gui.utils.page_filters import watch_page_filters

AUDIO = "audio"
ROW_ROLE = QtCore.Qt.ItemDataRole.UserRole + 60  # the archive row of a sound
UNSORTED = "unsorted"  # sounds whose path isn't known


class _Signals(QtCore.QObject):
    names_ready = QtCore.Signal()


class AudioPage(QtWidgets.QWidget):
    """The open pack's sounds as a folder tree."""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.archive = None
        self._waiting = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(2)  # the folder or sound, and a folder's file count
        self.tree.setHeaderHidden(True)
        self.tree.setColumnWidth(0, 340)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._folder_icon, self._file_icon = tree_icons(self.tree)
        follow_file_list_theme(self.tree)
        self.tree.currentItemChanged.connect(self._selected)
        self.tree.itemDoubleClicked.connect(self._open)
        self.tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        layout.addWidget(self.tree, 1)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._signals = _Signals(self)
        self._signals.names_ready.connect(self._names_ready)
        wwise_names._NOTIFY.append(self._signals.names_ready.emit)

    def activate(self):
        """Shown: list the open pack's sounds (again when another pack was opened)."""
        archive = QtWidgets.QApplication.instance().property("npk_file")
        if archive is self.archive and self.tree.topLevelItemCount():
            self.apply_filter(self._search_text())
            return
        self.archive = archive
        self.fill()

    def clear(self):
        self.archive = None
        self.tree.clear()
        self.status.setText("")

    def _names_ready(self):
        if self._waiting and self.isVisible():
            self._waiting = False
            self.fill()

    def fill(self):
        self.tree.clear()
        archive = self.archive
        model = self.window_.list_widget.model()
        if archive is None or model is None:
            self.status.setText("")
            return
        if not wwise_names.ready():
            self._waiting = True  # filled when the sound tables are read
            self.status.setText("Reading the game's sound names…")
            return
        peek = getattr(archive, "peek_entry", archive.find_entry_by_id)
        folders: dict[str, QtWidgets.QTreeWidgetItem] = {}
        counts: dict[str, int] = {}
        files = []
        for row in range(model.rowCount()):
            try:
                if peek(row).category != NPKEntryFileCategories.BANK:
                    continue
            except Exception:
                get_logger().debug("Could not read the entry %d for the Audio page", row, exc_info=True)
                continue
            name = model.get_filename(model.index(row))
            path = wwise_names.tree_path(name) or "\\".join([UNSORTED, name.replace("/", "\\").rsplit("\\", 1)[-1]])
            files.append((path, row))
        self.tree.setUpdatesEnabled(False)
        for path, row in sorted(files, key=lambda item: item[0].lower()):
            parts = path.split("\\")
            parent = self.tree.invisibleRootItem()
            for depth in range(1, len(parts)):
                key = "\\".join(parts[:depth]).lower()
                node = folders.get(key)
                if node is None:
                    node = QtWidgets.QTreeWidgetItem(parent, [parts[depth - 1], ""])
                    node.setIcon(0, self._folder_icon)
                    folders[key] = node
                counts[key] = counts.get(key, 0) + 1
                parent = node
            item = QtWidgets.QTreeWidgetItem(parent, [parts[-1], ""])
            item.setIcon(0, self._file_icon)
            item.setData(0, ROW_ROLE, row)
            item.setToolTip(0, path)
        for key, node in folders.items():
            node.setText(1, f"{counts[key]:,}")
        self.tree.setUpdatesEnabled(True)
        self.status.setText(f"{len(files):,} sounds and banks." if files else "This pack holds no sounds.")
        self.apply_filter(self._search_text())

    def _search_text(self):
        search = getattr(self.window_, "name_filter_input", None)
        return search.text() if search is not None else ""

    def apply_filter(self, text):
        """Show the sounds whose path (folders, bank, name) holds every word of the search."""
        words = str(text or "").lower().split()

        def visit(item, trail):
            shown = 0
            for number in range(item.childCount()):
                child = item.child(number)
                path = f"{trail}\\{child.text(0)}".lower() if trail else child.text(0).lower()
                if child.childCount():
                    visible = visit(child, path)
                    child.setHidden(visible == 0)
                    if words and visible:
                        child.setExpanded(True)
                    shown += visible
                else:
                    match = all(word in path for word in words)
                    child.setHidden(not match)
                    shown += match
            return shown

        visit(self.tree.invisibleRootItem(), "")

    def _rows(self, items):
        """Archive rows of the sounds under the given items (folders count with everything in them)."""
        rows, stack = [], list(items)
        while stack:
            item = stack.pop()
            row = item.data(0, ROW_ROLE)
            if row is not None:
                if not item.isHidden():
                    rows.append((row, item.toolTip(0)))
            else:
                stack.extend(item.child(n) for n in range(item.childCount()))
        return rows

    def _selected(self, item, _previous):
        row = item.data(0, ROW_ROLE) if item is not None else None
        if row is not None and self.archive is not None:
            self.window_.preview_widget.set_file(self.archive.find_entry_by_id(row))

    def _open(self, item, _column):
        row = item.data(0, ROW_ROLE)
        if row is not None and self.archive is not None:
            self.window_.list_widget.open_entry.emit(row, self.archive.find_entry_by_id(row))

    def _menu(self, position):
        items = self.tree.selectedItems()
        if not items:
            return
        menu = QtWidgets.QMenu(self.tree)
        menu.addAction("Save selected…", lambda: self.save(items))
        item = self.tree.itemAt(position)
        if item is not None and item.data(0, ROW_ROLE) is not None:
            menu.addAction("Open in Audio Viewer", lambda: self._open(item, 0))
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def save(self, items):
        """The selected sounds (and everything in selected folders) as they are in the pack, in their folders."""
        rows = self._rows(items)
        if not rows or self.archive is None:
            return
        target = QtWidgets.QFileDialog.getExistingDirectory(self, "Save sounds")
        if not target:
            return
        saved, failed = 0, []
        for row, path in rows:
            parts = [part for part in path.split("\\") if part not in ("", ".", "..")]
            file_path = os.path.join(target, *parts)
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "wb") as stream:
                    stream.write(self.archive.find_entry_by_id(row).get_export_data(decoded=False))
                saved += 1
            except Exception as exc:
                get_logger().exception("Could not save %s", path)
                failed.append(f"{path}: {exc}")
        message = f"Saved {saved:,} files to {target}." + (
            f"\n{len(failed)} failed:\n" + "\n".join(failed[:5]) if failed else ""
        )
        QtWidgets.QMessageBox.information(self, "Save sounds", message)


def install(app) -> None:
    """Put the Audio page in the place of the plain "Audio" category of every main window."""
    for window in app.topLevelWidgets():
        combo = getattr(window, "entry_category_filter_combobox", None)
        if combo is None or getattr(window, "_audio_page", None) is not None:
            continue
        row = combo.findData(NPKEntryFileCategories.BANK)
        if row < 0:
            continue
        page = AudioPage(window)
        window._audio_page = page
        addons.left_stack(window).addWidget(page)
        addons.PAGES.add(AUDIO)
        combo.setItemData(row, AUDIO)

        def show_if_selected(*_args, window=window, combo=combo, page=page):
            if combo.currentData() != AUDIO:
                return
            window.left_content.setCurrentWidget(page)
            window.filter.filter_type = None
            for name in ("extract_button_widget", "mesh_biped_head_filter_checkbox"):
                widget = getattr(window, name, None)
                if widget is not None:
                    widget.hide()
            page.activate()

        combo.currentIndexChanged.connect(show_if_selected)
        window.loading_complete_signal.connect(show_if_selected)
        window.unload_npk_action.triggered.connect(lambda _checked=False, page=page: page.clear())
        window.name_filter_input.textChanged.connect(page.apply_filter)
        watch_page_filters(window)
