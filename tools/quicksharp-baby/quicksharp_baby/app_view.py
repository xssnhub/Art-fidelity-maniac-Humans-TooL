from __future__ import annotations

from .app_support import *  # noqa: F401,F403


class AppViewMixin:
    def navigate(self, delta: int) -> None:
            if not self.files:
                return
            target = self.current_index + delta
            if 0 <= target < len(self.files):
                self.show_index(target)

    def show_index(self, index: int) -> None:
            if not (0 <= index < len(self.files)):
                return
            self.current_index = index
            self.current_path = self.files[index]
            self.request_id += 1
            request_id = self.request_id
            path = self.current_path
            self._update_selected_thumbnail()
            self._update_status(loading=True)
            self.main_canvas.delete("image")
            self.main_canvas.itemconfigure(self.empty_icon, state="hidden")
            self.main_canvas.itemconfigure(self.empty_text, text="載入中…", state="normal")

            self.executor.submit(self._load_worker, request_id, index, path)
            self._preload_neighbors(index)

    def _load_worker(self, request_id: int, index: int, path: Path) -> None:
            try:
                image = self.image_cache.load(path)
            except Exception as exc:
                self.root.after(0, lambda: self._load_failed(request_id, path, exc))
                return
            self.root.after(0, lambda: self._apply_loaded(request_id, index, path, image))

    def _apply_loaded(
            self,
            request_id: int,
            index: int,
            path: Path,
            image: Image.Image,
        ) -> None:
            if request_id != self.request_id or index != self.current_index:
                return
            self.current_image = image
            self.current_path = path
            self.view.normalized()
            self.main_canvas.itemconfigure(self.empty_icon, state="hidden")
            self.main_canvas.itemconfigure(self.empty_text, state="hidden")
            self._update_status(loading=False)
            self.schedule_render()

    def _load_failed(self, request_id: int, path: Path, exc: Exception) -> None:
            if request_id != self.request_id:
                return
            self.current_image = None
            self.main_canvas.itemconfigure(self.empty_icon, state="hidden")
            self.main_canvas.itemconfigure(
                self.empty_text,
                text=f"無法讀取\n{path.name}",
                state="normal",
            )
            self._update_status(loading=False)
            self._toast(str(exc))

    def _preload_neighbors(self, index: int) -> None:
            # RAW stays truly on-demand: no neighboring RAW files are decoded.
            if self.current_mode == "RAW":
                return
            for neighbor in (index + 1, index - 1):
                if 0 <= neighbor < len(self.files):
                    path = self.files[neighbor]
                    self.executor.submit(self._quiet_preload, path)

    def _quiet_preload(self, path: Path) -> None:
            try:
                self.image_cache.load(path)
            except Exception:
                pass

    def schedule_render(self) -> None:
            if self._render_job is not None:
                self.root.after_cancel(self._render_job)
            self._render_job = self.root.after(16, self._render)

    def _render(self) -> None:
            self._render_job = None
            image = self.current_image
            if image is None:
                return

            canvas_w = max(1, self.main_canvas.winfo_width())
            canvas_h = max(1, self.main_canvas.winfo_height())
            source_rect = visible_source_rect(
                image.width,
                image.height,
                canvas_w,
                canvas_h,
                self.view,
            )
            left, top, right, bottom = source_rect

            visible = Image.new("RGB", (canvas_w, canvas_h), "#101010")
            crop_left = max(0.0, left)
            crop_top = max(0.0, top)
            crop_right = min(float(image.width), right)
            crop_bottom = min(float(image.height), bottom)

            if crop_right > crop_left and crop_bottom > crop_top:
                crop = image.crop((crop_left, crop_top, crop_right, crop_bottom))
                target_w = max(1, round((crop_right - crop_left) * self.view.zoom))
                target_h = max(1, round((crop_bottom - crop_top) * self.view.zoom))
                if self.view.zoom >= 2.0:
                    resample = Image.Resampling.NEAREST
                elif self.view.zoom >= 1.0:
                    resample = Image.Resampling.BILINEAR
                else:
                    resample = Image.Resampling.LANCZOS
                crop = crop.resize((target_w, target_h), resample)
                screen_x = round((crop_left - left) * self.view.zoom)
                screen_y = round((crop_top - top) * self.view.zoom)
                visible.paste(crop, (screen_x, screen_y))

            self._main_photo = ImageTk.PhotoImage(visible)
            self.main_canvas.delete("image")
            self.main_canvas.create_image(0, 0, image=self._main_photo, anchor="nw", tags="image")
            self.main_canvas.tag_lower("image")
            self._render_navigator(source_rect)

    def _render_navigator(self, source_rect: tuple[float, float, float, float]) -> None:
            image = self.current_image
            if image is None:
                return
            nav_w = max(1, self.nav_canvas.winfo_width())
            nav_h = max(1, self.nav_canvas.winfo_height())
            if nav_w <= 5 or nav_h <= 5:
                self.root.after(30, self.schedule_render)
                return

            thumbnail = image.copy()
            thumbnail.thumbnail((nav_w - 8, nav_h - 8), Image.Resampling.LANCZOS)
            self._nav_photo = ImageTk.PhotoImage(thumbnail)
            offset_x = (nav_w - thumbnail.width) / 2
            offset_y = (nav_h - thumbnail.height) / 2
            scale = thumbnail.width / image.width

            self.nav_canvas.delete("all")
            self.nav_canvas.create_image(offset_x, offset_y, image=self._nav_photo, anchor="nw")

            left, top, right, bottom = source_rect
            rect = (
                offset_x + clamp(left, 0, image.width) * scale,
                offset_y + clamp(top, 0, image.height) * scale,
                offset_x + clamp(right, 0, image.width) * scale,
                offset_y + clamp(bottom, 0, image.height) * scale,
            )
            self.nav_canvas.create_rectangle(
                *rect,
                outline="#ffffff",
                width=2,
                tags="viewport",
            )
            self.nav_canvas.nav_geometry = (offset_x, offset_y, thumbnail.width, thumbnail.height)
