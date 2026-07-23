from __future__ import annotations

from .app_support import *  # noqa: F401,F403


class AppImportMixin:
    def _setup_drop_target(self) -> None:
            """Enable native Ubuntu drag-and-drop through the tiny tkdnd package."""
            try:
                self.root.tk.call("package", "require", "tkdnd")
                command = self.root.register(self._handle_drop_data)
                for widget in (self.root, self.main_canvas, self.filmstrip):
                    self.root.tk.call("tkdnd::drop_target", "register", widget._w, "DND_Files")
                    self.root.tk.call(
                        "bind", widget._w, "<<Drop>>", f"{command} %D"
                    )
                self._dnd_ready = True
            except Exception:
                self._dnd_ready = False

    def _decode_drop_path(self, raw: str) -> Path:
            text = raw.strip()
            if text.startswith("file://"):
                parsed = urlparse(text)
                text = unquote(parsed.path)
            return Path(text).expanduser()

    def _handle_drop_data(self, data: str) -> str:
            try:
                raw_paths = self.root.tk.splitlist(data)
            except Exception:
                raw_paths = (data,)
            paths = [self._decode_drop_path(value) for value in raw_paths]
            self.open_paths(paths)
            return "copy"

    def open_paths(self, paths: list[Path] | tuple[Path, ...]) -> None:
            existing = [path for path in paths if path.exists()]
            if not existing:
                self._toast("拖入的路徑不存在")
                return

            folder = next((path for path in existing if path.is_dir()), None)
            if folder is not None:
                self.open_folder(folder)
                return

            photo = next(
                (
                    path for path in existing
                    if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
                ),
                None,
            )
            if photo is None:
                self._toast("請拖入照片資料夾或支援的影像檔")
                return
            self.open_folder(photo.parent, preferred_path=photo)

    def open_folder(self, folder: Path, preferred_path: Path | None = None) -> None:
            files = scan_folder(folder)
            if not files:
                messagebox.showinfo(self.APP_NAME, "這個資料夾裡沒有支援的照片。")
                return

            self.current_folder = folder
            self.folder_generation += 1
            self.request_id += 1
            self.image_cache.clear()
            self.all_files = files
            self._rebuild_mode_lists()

            preferred_mode = _mode_for_path(preferred_path) if preferred_path is not None else None
            if preferred_mode and preferred_path in self.files_by_mode.get(preferred_mode, []):
                initial_mode = preferred_mode
            elif self.files_by_mode["JPG"]:
                initial_mode = "JPG"
            elif self.files_by_mode["TIF"]:
                initial_mode = "TIF"
            else:
                initial_mode = "RAW"

            self.current_mode = initial_mode
            self._load_mode_list(
                initial_mode,
                preferred_stem=_pair_key(preferred_path) if preferred_path is not None else None,
                show_first=True,
                preferred_path=preferred_path,
            )
            counts = " · ".join(
                f"{mode} {len(self.files_by_mode[mode])}" for mode in VIEW_MODES
                if self.files_by_mode[mode]
            )
            self._show_filmstrip()
            self._toast(f"已匯入 {len(files)} 張｜{counts}")

    def _rebuild_mode_lists(self) -> None:
            grouped = {mode: [] for mode in VIEW_MODES}
            for path in self.all_files:
                mode = _mode_for_path(path)
                if mode is not None:
                    grouped[mode].append(path)
            for mode in VIEW_MODES:
                grouped[mode].sort(key=natural_key)
            self.files_by_mode = grouped
            self._update_mode_buttons()

    def _find_pair_index(self, mode: str, stem: str) -> int | None:
            target = stem.casefold()
            for index, path in enumerate(self.files_by_mode.get(mode, [])):
                if _pair_key(path) == target:
                    return index
            return None

    def _find_pair_path(self, mode: str, stem: str) -> Path | None:
            index = self._find_pair_index(mode, stem)
            if index is None:
                return None
            return self.files_by_mode[mode][index]

    def switch_mode(self, mode: str) -> None:
            if mode == self.current_mode:
                return
            target_files = self.files_by_mode.get(mode, [])
            if not target_files:
                self._toast(f"資料夾裡沒有 {mode} 檔")
                return

            current_stem = _pair_key(self.current_path) if self.current_path else None
            if current_stem is not None and self._find_pair_index(mode, current_stem) is None:
                self._toast(f"{self.current_path.stem} 沒有配對 {mode}")
                return

            self.current_mode = mode
            self._load_mode_list(mode, preferred_stem=current_stem, show_first=True)
            if mode == "RAW":
                self._toast("RAW 按需載入｜未預先解碼其他 RAW")
            else:
                self._toast(f"已切換到 {mode} 視圖")

    def _load_mode_list(
            self,
            mode: str,
            preferred_stem: str | None,
            show_first: bool,
            preferred_path: Path | None = None,
        ) -> None:
            self.folder_generation += 1
            self.request_id += 1
            self.image_cache.clear()
            self.files = list(self.files_by_mode.get(mode, []))
            self.current_index = -1
            self.current_image = None
            self.current_path = None
            self._thumb_photos.clear()
            self._clear_thumbnails()
            self._create_thumbnail_placeholders()
            self._update_mode_buttons()

            if not self.files:
                self.main_canvas.delete("image")
                self.main_canvas.itemconfigure(self.empty_icon, state="normal")
                self.main_canvas.itemconfigure(
                    self.empty_text, text=f"沒有 {mode} 照片", state="normal"
                )
                self._update_status(loading=False)
                return

            index = 0
            if preferred_path is not None and preferred_path in self.files:
                index = self.files.index(preferred_path)
            elif preferred_stem is not None:
                paired = self._find_pair_index(mode, preferred_stem)
                if paired is not None:
                    index = paired
            if show_first:
                self.show_index(index)

    def _clear_thumbnails(self) -> None:
            for widget in self._thumb_widgets:
                widget.destroy()
            self._thumb_widgets.clear()

    def _create_thumbnail_placeholders(self) -> None:
            generation = self.folder_generation
            for index, path in enumerate(self.files):
                frame = Frame(
                    self.thumb_inner,
                    bg="#2a2a2a",
                    width=118,
                    height=112,
                    highlightthickness=2,
                    highlightbackground="#2a2a2a",
                )
                frame.pack(side=LEFT, padx=3, pady=5)
                frame.pack_propagate(False)

                image_label = Label(
                    frame,
                    text="…",
                    bg="#161616",
                    fg="#888888",
                    width=15,
                    height=5,
                    cursor="hand2",
                )
                image_label.pack(fill=BOTH, expand=True, padx=3, pady=(3, 0))
                name_label = Label(
                    frame,
                    text=path.name,
                    bg="#2a2a2a",
                    fg="#dddddd",
                    font=("Sans", 8),
                    anchor="center",
                )
                name_label.pack(fill=X, padx=2, pady=2)

                for widget in (frame, image_label, name_label):
                    widget.bind("<Button-1>", lambda _event, i=index: self.show_index(i))
                    widget.bind("<MouseWheel>", self._scroll_filmstrip)
                    widget.bind("<Button-4>", lambda _event: self.thumb_canvas.xview_scroll(-3, "units"))
                    widget.bind("<Button-5>", lambda _event: self.thumb_canvas.xview_scroll(3, "units"))

                frame.image_label = image_label  # type: ignore[attr-defined]
                self._thumb_widgets.append(frame)

                # RAW view never decodes the whole RAW strip. Reuse the paired JPG
                # thumbnail when available; otherwise leave a lightweight RAW tile.
                thumbnail_source = path
                if self.current_mode == "RAW":
                    thumbnail_source = self._find_pair_path("JPG", _pair_key(path))
                    if thumbnail_source is None:
                        image_label.configure(text="RAW", fg="#b8b8b8")
                        continue
                self.executor.submit(
                    self._thumbnail_worker, generation, index, thumbnail_source
                )

    def _thumbnail_worker(self, generation: int, index: int, path: Path) -> None:
            try:
                thumb = load_thumbnail(path)
                self.root.after(0, lambda: self._apply_thumbnail(generation, index, thumb))
            except Exception:
                self.root.after(0, lambda: self._apply_thumbnail_error(generation, index))

    def _apply_thumbnail(self, generation: int, index: int, image: Image.Image) -> None:
            if generation != self.folder_generation or index >= len(self._thumb_widgets):
                return
            photo = ImageTk.PhotoImage(image)
            self._thumb_photos[index] = photo
            label = self._thumb_widgets[index].image_label  # type: ignore[attr-defined]
            label.configure(image=photo, text="")

    def _apply_thumbnail_error(self, generation: int, index: int) -> None:
            if generation != self.folder_generation or index >= len(self._thumb_widgets):
                return
            label = self._thumb_widgets[index].image_label  # type: ignore[attr-defined]
            label.configure(text="讀取失敗", fg="#c97777")
