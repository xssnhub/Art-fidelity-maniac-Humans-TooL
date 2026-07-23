from __future__ import annotations

from .app_support import *  # noqa: F401,F403


class AppUIMixin:
    def __init__(self, root: Tk) -> None:
            self.root = root
            self.root.title(self.APP_NAME)
            self.root.configure(bg="#101010")
            self.root.minsize(900, 600)

            self.all_files: list[Path] = []
            self.files_by_mode: dict[str, list[Path]] = {mode: [] for mode in VIEW_MODES}
            self.files: list[Path] = []
            self.current_mode = "JPG"
            self.current_folder: Path | None = None
            self._dnd_ready = False
            self.current_index = -1
            self.current_image: Image.Image | None = None
            self.current_path: Path | None = None
            self.view = ViewState()
            self.request_id = 0
            self.folder_generation = 0
            self.image_cache = ImageCache(max_items=3)
            self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="quicksharp")
            self._render_job: str | None = None
            self._main_photo: ImageTk.PhotoImage | None = None
            self._nav_photo: ImageTk.PhotoImage | None = None
            self._thumb_photos: dict[int, ImageTk.PhotoImage] = {}
            self._thumb_widgets: list[Frame] = []
            self._drag_start: tuple[int, int, float, float] | None = None
            self._nav_drag_offset: tuple[int, int] | None = None
            self._nav_move_origin: tuple[int, int, int, int] | None = None
            self._is_fullscreen = True

            self._build_ui()
            self._bind_events()
            self.root.after(50, self._enter_fullscreen)

    def _build_ui(self) -> None:
            self.main_canvas = Canvas(
                self.root,
                bg="#101010",
                highlightthickness=0,
                cursor="crosshair",
            )
            self.main_canvas.pack(fill=BOTH, expand=True)

            self.empty_icon = self.main_canvas.create_text(
                450,
                235,
                text="🔬",
                fill="#dedede",
                font=("Sans", 48),
            )
            self.empty_text = self.main_canvas.create_text(
                450,
                305,
                text="點一下，或拖入資料夾／照片\n開始巡圖",
                fill="#cfcfcf",
                font=("Sans", 18),
                justify="center",
            )

            # Keep the lower strip inside the main window.  Earlier prototypes
            # used an override-redirect Toplevel for per-window alpha; on Ubuntu
            # that detached panel could survive after the owner was minimized.
            # A single-window overlay follows minimize, restore, resize and close
            # automatically, which is more important than true widget alpha.
            self._filmstrip_visible = False
            self.filmstrip = Frame(
                self.root,
                bg="#232323",
                height=FILMSTRIP_HEIGHT,
                highlightthickness=1,
                highlightbackground="#454545",
            )
            self.filmstrip.pack_propagate(False)

            self.thumb_canvas = Canvas(
                self.filmstrip,
                bg="#232323",
                highlightthickness=0,
                height=FILMSTRIP_HEIGHT - 6,
            )
            self.thumb_canvas.pack(side=LEFT, fill=BOTH, expand=True)

            self.thumb_inner = Frame(self.thumb_canvas, bg="#232323")
            self.thumb_window = self.thumb_canvas.create_window(
                (0, 0), window=self.thumb_inner, anchor="nw"
            )
            self.thumb_inner.bind("<Configure>", self._update_thumb_scrollregion)
            self.thumb_canvas.bind("<Configure>", self._resize_thumb_window_height)

            controls = Frame(self.filmstrip, bg="#181818", width=190)
            controls.pack(side=RIGHT, fill="y")
            controls.pack_propagate(False)

            self.status_label = Label(
                controls,
                text="0 / 0",
                fg="#d8d8d8",
                bg="#181818",
                anchor="center",
                font=("Sans", 10),
            )
            self.status_label.pack(fill=X, padx=8, pady=(10, 5))

            mode_bar = Frame(controls, bg="#181818")
            mode_bar.pack(fill=X, padx=10, pady=(1, 5))
            self.mode_buttons: dict[str, Button] = {}
            for mode in VIEW_MODES:
                button = Button(
                    mode_bar,
                    text=mode,
                    command=lambda selected=mode: self.switch_mode(selected),
                    bg="#303030",
                    fg="#d7d7d7",
                    activebackground="#555555",
                    activeforeground="white",
                    relief="flat",
                    padx=2,
                    pady=4,
                    font=("Sans", 9, "bold"),
                )
                button.pack(side=LEFT, fill=X, expand=True, padx=1)
                self.mode_buttons[mode] = button
            self._update_mode_buttons()

            zoom_bar = Frame(controls, bg="#181818")
            zoom_bar.pack(fill=X, padx=10, pady=(1, 4))
            Button(
                zoom_bar, text="−", command=lambda: self._zoom_step(None, -1),
                bg="#303030", fg="white", activebackground="#555555",
                activeforeground="white", relief="flat", pady=3,
                font=("Sans", 12, "bold"),
            ).pack(side=LEFT, fill=X, expand=True, padx=(0, 2))
            self.zoom_label = Label(
                zoom_bar, text="300%", bg="#181818", fg="#eeeeee",
                width=7, anchor="center", font=("Sans", 10, "bold"),
            )
            self.zoom_label.pack(side=LEFT, padx=2)
            Button(
                zoom_bar, text="+", command=lambda: self._zoom_step(None, 1),
                bg="#303030", fg="white", activebackground="#555555",
                activeforeground="white", relief="flat", pady=3,
                font=("Sans", 12, "bold"),
            ).pack(side=LEFT, fill=X, expand=True, padx=(2, 0))

            action_bar = Frame(controls, bg="#181818")
            action_bar.pack(fill=X, padx=10, pady=(2, 5))

            self.import_button = Button(
                action_bar,
                text="匯入",
                command=self.choose_folder,
                bg="#353535",
                fg="white",
                activebackground="#4a4a4a",
                activeforeground="white",
                relief="flat",
                padx=4,
                pady=5,
            )
            self.import_button.pack(side=LEFT, fill=X, expand=True, padx=(0, 2))

            self.trash_button = Button(
                action_bar,
                text="🗑 刪除",
                command=self.trash_current,
                bg="#353535",
                fg="white",
                activebackground="#5a3232",
                activeforeground="white",
                relief="flat",
                padx=4,
                pady=5,
            )
            self.trash_button.pack(side=LEFT, fill=X, expand=True, padx=(2, 0))

            # Movable navigator overlay.
            self.navigator = Frame(
                self.root,
                bg="#171717",
                highlightthickness=1,
                highlightbackground="#777777",
            )
            self.navigator.place(x=20, y=300, width=250, height=188)

            self.nav_header = Label(
                self.navigator,
                text="導覽器",
                bg="#222222",
                fg="#dddddd",
                anchor="w",
                padx=7,
                font=("Sans", 9),
            )
            self.nav_header.pack(fill=X)

            self.nav_canvas = Canvas(
                self.navigator,
                bg="#0d0d0d",
                highlightthickness=0,
            )
            self.nav_canvas.pack(fill=BOTH, expand=True)

            self.toast_label = Label(
                self.root,
                text="",
                fg="white",
                bg="#2d2d2d",
                padx=12,
                pady=7,
                font=("Sans", 10),
            )

    def _bind_events(self) -> None:
            self.root.bind_all("<Right>", lambda _event: self._main_shortcut(self.navigate, 1))
            self.root.bind_all("<Left>", lambda _event: self._main_shortcut(self.navigate, -1))
            self.root.bind_all("<Delete>", lambda _event: self._main_shortcut(self.trash_current))
            self.root.bind_all("<Escape>", lambda _event: self._leave_fullscreen())
            self.root.bind_all("<plus>", lambda _event: self._main_shortcut(self._zoom_step, None, 1))
            self.root.bind_all("<equal>", lambda _event: self._main_shortcut(self._zoom_step, None, 1))
            self.root.bind_all("<minus>", lambda _event: self._main_shortcut(self._zoom_step, None, -1))
            self.root.bind_all("<KP_Add>", lambda _event: self._main_shortcut(self._zoom_step, None, 1))
            self.root.bind_all("<KP_Subtract>", lambda _event: self._main_shortcut(self._zoom_step, None, -1))

            self.main_canvas.bind("<Configure>", self._on_canvas_configure)
            self.main_canvas.bind("<ButtonPress-1>", self._start_pan)
            self.main_canvas.bind("<B1-Motion>", self._pan)
            self.main_canvas.bind("<ButtonRelease-1>", lambda _event: self._stop_pan())
            self.main_canvas.bind("<MouseWheel>", self._zoom_wheel)
            self.main_canvas.bind("<Button-4>", lambda event: self._zoom_step(event, 1))
            self.main_canvas.bind("<Button-5>", lambda event: self._zoom_step(event, -1))

            self.nav_canvas.bind("<ButtonPress-1>", self._start_nav_pan)
            self.nav_canvas.bind("<B1-Motion>", self._nav_pan)
            self.nav_canvas.bind("<ButtonRelease-1>", lambda _event: self._stop_nav_pan())

            self.nav_header.bind("<ButtonPress-1>", self._start_move_navigator)
            self.nav_header.bind("<B1-Motion>", self._move_navigator)
            self.nav_header.bind("<ButtonRelease-1>", lambda _event: self._stop_move_navigator())

            for widget in (self.thumb_canvas, self.thumb_inner):
                widget.bind("<MouseWheel>", self._scroll_filmstrip)
                widget.bind("<Button-4>", lambda _event: self.thumb_canvas.xview_scroll(-3, "units"))
                widget.bind("<Button-5>", lambda _event: self.thumb_canvas.xview_scroll(3, "units"))

            self._setup_drop_target()
            self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _main_shortcut(self, callback, *args) -> None:
            callback(*args)

    def _update_selected_thumbnail(self) -> None:
            for index, frame in enumerate(self._thumb_widgets):
                selected = index == self.current_index
                frame.configure(
                    highlightbackground="#ffffff" if selected else "#2a2a2a",
                    bg="#3a3a3a" if selected else "#2a2a2a",
                )
            if 0 <= self.current_index < len(self._thumb_widgets):
                frame = self._thumb_widgets[self.current_index]
                self.root.update_idletasks()
                x = frame.winfo_x()
                width = max(1, self.thumb_inner.winfo_width())
                canvas_width = max(1, self.thumb_canvas.winfo_width())
                target = clamp((x - canvas_width / 2) / max(1, width - canvas_width), 0.0, 1.0)
                self.thumb_canvas.xview_moveto(target)

    def _update_status(self, loading: bool) -> None:
            zoom_label = getattr(self, "zoom_label", None)
            if zoom_label is not None:
                zoom_label.configure(text=f"{round(self.view.zoom * 100)}%")
            if not self.files or self.current_index < 0:
                self.status_label.configure(text=f"{self.current_mode}｜0 / 0")
                return
            path = self.files[self.current_index]
            suffix = path.suffix.lstrip(".").upper()
            state = "載入中" if loading else f"{round(self.view.zoom * 100)}%"
            self.status_label.configure(
                text=f"{self.current_mode}｜{self.current_index + 1} / {len(self.files)}\n{suffix} · {state}\n{path.name}"
            )

    def _update_mode_buttons(self) -> None:
            buttons = getattr(self, "mode_buttons", {})
            for mode, button in buttons.items():
                active = mode == self.current_mode
                available = bool(self.files_by_mode.get(mode, []))
                button.configure(
                    bg="#eeeeee" if active else "#303030",
                    fg="#111111" if active else "#d7d7d7",
                    state="normal" if available or active else "disabled",
                    disabledforeground="#606060",
                )

    def _toast(self, text: str, duration_ms: int = 2500) -> None:
            self.toast_label.configure(text=text)
            self.toast_label.place(relx=0.5, rely=0.08, anchor="n")
            self.toast_label.lift()
            self.root.after(duration_ms, self.toast_label.place_forget)

    def _on_canvas_configure(self, event) -> None:
            center_x = max(1, event.width) / 2
            center_y = max(1, event.height) / 2
            self.main_canvas.coords(self.empty_icon, center_x, center_y - 42)
            self.main_canvas.coords(self.empty_text, center_x, center_y + 40)
            self.schedule_render()

    def _show_filmstrip(self) -> None:
            """Overlay the filmstrip inside the owner window.

            Because this is a normal child widget, Ubuntu minimizes and restores
            it together with the main image window.  No window-manager polling or
            owner/child synchronization is needed.
            """
            if self._filmstrip_visible:
                self.filmstrip.lift()
                return
            self.filmstrip.place(
                relx=0,
                rely=1,
                anchor="sw",
                relwidth=1,
                height=FILMSTRIP_HEIGHT,
            )
            self.filmstrip.lift()
            self._filmstrip_visible = True

    def _hide_filmstrip(self) -> None:
            if not self._filmstrip_visible:
                return
            self.filmstrip.place_forget()
            self._filmstrip_visible = False

    def _update_thumb_scrollregion(self, _event=None) -> None:
            self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))

    def _resize_thumb_window_height(self, event) -> None:
            self.thumb_canvas.itemconfigure(self.thumb_window, height=event.height)

    def _scroll_filmstrip(self, event) -> None:
            delta = -1 if event.delta > 0 else 1
            self.thumb_canvas.xview_scroll(delta * 4, "units")

    def _enter_fullscreen(self) -> None:
            try:
                self.root.attributes("-fullscreen", True)
                self._is_fullscreen = True
            except Exception:
                try:
                    self.root.state("zoomed")
                except Exception:
                    pass
            self._position_navigator_default()
            if self.files:
                self._show_filmstrip()

    def _leave_fullscreen(self) -> None:
            if self._is_fullscreen:
                self.root.attributes("-fullscreen", False)
                self._is_fullscreen = False
            else:
                self.close()

    def _position_navigator_default(self) -> None:
            self.root.update_idletasks()
            y = max(20, self.root.winfo_height() - FILMSTRIP_HEIGHT - 208)
            self.navigator.place(x=20, y=y, width=250, height=188)

    def close(self) -> None:
            self._hide_filmstrip()
            self.request_id += 1
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.image_cache.clear()
            self.root.destroy()
