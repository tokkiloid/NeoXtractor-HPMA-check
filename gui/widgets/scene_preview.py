"""
"Scene Viewer" in the preview's viewer list: a stage scene (.scn) picked in the file list is drawn with its models
placed and their textures matched, as the Scene Viewer window loads it. Loading runs in the background and stops
when another file is picked. Registered by gui.addons before the main window builds its viewers.
"""

import threading

from PySide6 import QtCore, QtWidgets

from core.file import IFile
from core.logger import get_logger
from gui.widgets.viewer import Viewer

NAME = "Scene Viewer"


class _Signals(QtCore.QObject):
    progress = QtCore.Signal(int, str, int, int)  # generation, text, value, total
    loaded = QtCore.Signal(int, object, str)  # generation, objects, report


class ScenePreview(Viewer):
    """A stage scene drawn in the preview area."""

    name = NAME
    accepted_extensions = {"scn"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.generation = 0
        self._cancel = threading.Event()
        self._objects = []
        self._file = None
        self._stage, self._game = "", None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = QtWidgets.QHBoxLayout()
        self.play = QtWidgets.QPushButton("Pause")
        self.play.setToolTip("Pause or play the stage's animated models")
        self.play.clicked.connect(self._toggle_play)
        bar.addWidget(self.play)
        self.bones = QtWidgets.QCheckBox("Show Bones")
        self.bones.toggled.connect(self._toggle_bones)
        bar.addWidget(self.bones)
        bar.addStretch(1)
        self.open_window = QtWidgets.QPushButton("Open in Scene Viewer")
        self.open_window.setToolTip("Load this stage into the Scene Viewer window, to combine it with other models")
        self.open_window.clicked.connect(self._open_in_window)
        bar.addWidget(self.open_window)
        layout.addLayout(bar)
        try:
            from gui.widgets.scene_render import SceneRenderWidget

            self.view = SceneRenderWidget()
        except Exception as exc:
            get_logger().exception("The scene preview has no 3D view")
            self.view = QtWidgets.QLabel(f"3D preview unavailable: {exc}")
        layout.addWidget(self.view, 1)
        from gui.widgets.viewer_overlay import ViewOverlays

        self.overlays = ViewOverlays(self.view)
        self._signals = _Signals(self)
        self._signals.progress.connect(self._progress)
        self._signals.loaded.connect(self._loaded)

    def set_file(self, file: IFile):
        self.unload_file()
        self._file = file
        archive = QtWidgets.QApplication.instance().property("npk_file")
        from core.npk.stage_export import game_root_for, read_options_for

        game = game_root_for(archive.file_path) if getattr(archive, "file_path", None) else None
        stage = str(getattr(file, "filename", "") or "scene").replace("/", "\\").rsplit("\\", 1)[-1].rsplit(".", 1)[0]
        self._stage, self._game = stage, game
        self.open_window.setEnabled(game is not None)
        if game is None:
            self.overlays.set_info([("Stage", stage), ("Status", "Open the pack from the game's res folder.")])
            return
        data = bytes(file.data)
        options = read_options_for(archive)
        generation, cancel = self.generation, self._cancel
        self.overlays.set_info([("Stage", stage), ("Status", "Loading…")])

        def work():
            from core.npk.stage_export import PackIndex, StageLoader
            from gui.widgets.scene_render import pil_to_qimage

            loader = StageLoader(
                PackIndex(game, options),
                cancelled=cancel.is_set,
                progress=lambda text, value, total: self._signals.progress.emit(generation, text, value, total),
            )
            try:
                objects = loader.load_data(data, stage)
                qimages = {}
                for obj in objects:
                    for part in obj["parts"]:
                        image = part.pop("image", None)
                        if image is not None:
                            if id(image) not in qimages:
                                qimages[id(image)] = pil_to_qimage(image)
                            part["qimage"] = qimages[id(image)]
                report = "\n".join(sorted(set(loader.report)))
            except InterruptedError:
                return
            except Exception as exc:
                get_logger().exception("Could not load the stage %s", stage)
                objects, report = [], f"Could not load this stage: {exc}"
            try:
                self._signals.loaded.emit(generation, objects, report)
            except RuntimeError:
                pass  # the viewer was closed while the stage loaded

        threading.Thread(target=work, daemon=True).start()

    def unload_file(self):
        """Stop a stage still loading and empty the view."""
        self._cancel.set()
        self._cancel = threading.Event()
        self.generation += 1
        if self._objects and hasattr(self.view, "remove_objects"):
            self.view.remove_objects(self._objects)
            self.view.update()
        self._objects = []
        self._file = None

    def _progress(self, generation, text, value, total):
        if generation == self.generation:
            self.overlays.set_info([("Status", f"{text} ({value}/{max(total, 1)})")])

    def _loaded(self, generation, objects, report):
        if generation != self.generation or not hasattr(self.view, "add_object"):
            return
        from gui.widgets.scene_render import SceneObject

        for spec in objects:
            obj = SceneObject(spec["name"], spec["mesh"], spec.get("matrix"), spec.get("path"), "")
            obj.set_animation(spec.get("animation"))
            for number, part in enumerate(obj.parts):
                info = spec["parts"][number] if number < len(spec["parts"]) else None
                if not info:
                    continue
                part.material = info.get("material") or part.material
                if info.get("qimage") is not None:
                    part.texture_key = self.view.set_texture(
                        "game:" + (info.get("texture") or f"{id(info)}"),
                        info["qimage"],
                        (info.get("texture") or "").rsplit("\\", 1)[-1],
                    )
                    part.alpha = info.get("alpha", "OPAQUE")
                    part.cutoff = info.get("cutoff", 0.5)
            self.view.add_object(obj)
            self._objects.append(obj)
        self.view.show_bones = self.bones.isChecked()
        if self._objects:
            self.view.focus(self._objects)
        self.view.update()
        rows = [("Objects", f"{len(self._objects):,}")]
        if report:
            for line in report.splitlines():
                get_logger().info("Scene preview: %s", line)
            rows.append(("Notes", "Some parts couldn't be read: see the log." if self._objects else report[:200]))
        self.overlays.set_info(rows)

    def _toggle_play(self):
        if hasattr(self.view, "set_playing"):
            playing = not self.view.playing
            self.view.set_playing(playing)
            self.play.setText("Pause" if playing else "Play")

    def _toggle_bones(self, checked):
        if hasattr(self.view, "show_bones"):
            self.view.show_bones = checked
            self.view.update()

    def _open_in_window(self):
        """The same stage in the Scene Viewer window, from the file's own bytes (scene packs name them by hash)."""
        app = QtWidgets.QApplication.instance()
        archive = app.property("npk_file")
        window = next((w for w in app.topLevelWidgets() if hasattr(w, "entry_category_filter_combobox")), None)
        if self._file is None or self._game is None or window is None or archive is None:
            return
        from core.npk.stage_export import read_options_for
        from gui.widgets import scene_viewer

        scene_viewer.viewer_for(window).open_stage(
            self._game, f"{self._stage}.scn", read_options_for(archive), bytes(self._file.data)
        )


def register() -> None:
    """Add the Scene Viewer to NeoXtractor's viewers, after the Mesh Viewer (before the main window is built)."""
    from gui.utils import viewer

    if ScenePreview in viewer.ALL_VIEWERS:
        return
    names = [v.name for v in viewer.ALL_VIEWERS]
    at = names.index("Mesh Viewer") + 1 if "Mesh Viewer" in names else len(viewer.ALL_VIEWERS)
    viewer.ALL_VIEWERS.insert(at, ScenePreview)
