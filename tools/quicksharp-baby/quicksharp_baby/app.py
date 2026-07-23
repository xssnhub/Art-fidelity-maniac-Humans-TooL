from __future__ import annotations

import os
from pathlib import Path

from .app_support import Tk, filedialog, _mode_for_path, _pair_key
from .app_actions import AppActionsMixin
from .app_import import AppImportMixin
from .app_interaction import AppInteractionMixin
from .app_ui import AppUIMixin
from .app_view import AppViewMixin


class QuickSharpBaby(
    AppUIMixin,
    AppImportMixin,
    AppViewMixin,
    AppInteractionMixin,
    AppActionsMixin,
):
    APP_NAME = "快晰寶貝｜QuickSharp Baby"

    def choose_folder(self) -> None:
            # Keep this identical to the v0.1.0 picker.  Adding parent, initialdir
            # or mustexist changed the native Ubuntu dialog behaviour on the
            # user's system and made nested folders appear unreadable.
            selected = filedialog.askdirectory(title="選擇照片資料夾")
            if selected:
                self.open_folder(Path(selected))


def run(paths: list[Path] | tuple[Path, ...] | Path | None = None) -> None:
    root = Tk()
    app = QuickSharpBaby(root)
    if paths is not None:
        if isinstance(paths, Path):
            initial_paths = [paths]
        else:
            initial_paths = list(paths)
        if initial_paths:
            root.after(100, lambda: app.open_paths(initial_paths))
    if os.getenv("QUICKSHARP_TEST") == "1":
        root.after(1200, app.close)
    root.mainloop()
