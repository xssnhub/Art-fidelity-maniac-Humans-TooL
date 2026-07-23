from __future__ import annotations

import io
import shutil
import subprocess
import threading
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

from .core import RAW_EXTENSIONS


class ImageLoadError(RuntimeError):
    pass


def _convert_to_srgb(image: Image.Image) -> Image.Image:
    """Apply the embedded ICC profile when Pillow can read it."""
    profile_data = image.info.get("icc_profile")
    if not profile_data:
        return image.convert("RGB")
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(profile_data))
        target_profile = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(
            image,
            source_profile,
            target_profile,
            outputMode="RGB",
        )
    except Exception:
        return image.convert("RGB")


def load_standard(path: Path) -> Image.Image:
    try:
        with Image.open(path) as opened:
            frame = opened.copy()
    except Exception as exc:
        raise ImageLoadError(f"無法讀取影像：{path.name}") from exc

    frame = ImageOps.exif_transpose(frame)
    return _convert_to_srgb(frame)


def load_raw_via_imagemagick(path: Path, max_dimension: int = 9000) -> Image.Image:
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        raise ImageLoadError("RAW 需要 ImageMagick，但系統目前找不到 magick 指令。")

    command = [
        magick,
        f"{path}[0]",
        "-auto-orient",
        "-colorspace", "sRGB",
        "-resize", f"{max_dimension}x{max_dimension}>",
        "-depth", "8",
        "png:-",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        with Image.open(io.BytesIO(completed.stdout)) as opened:
            return opened.convert("RGB").copy()
    except subprocess.TimeoutExpired as exc:
        raise ImageLoadError(f"RAW 解碼逾時：{path.name}") from exc
    except Exception as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace").strip()
        raise ImageLoadError(f"無法解碼 RAW：{path.name}\n{detail}") from exc


def load_image(path: Path) -> Image.Image:
    if path.suffix.casefold() in RAW_EXTENSIONS:
        return load_raw_via_imagemagick(path)
    return load_standard(path)


def load_thumbnail(path: Path, size: tuple[int, int] = (110, 82)) -> Image.Image:
    """Create a display thumbnail without touching the source file."""
    if path.suffix.casefold() in RAW_EXTENSIONS:
        magick = shutil.which("magick") or shutil.which("convert")
        if not magick:
            raise ImageLoadError("找不到 RAW 縮圖解碼器。")
        command = [
            magick,
            f"{path}[0]",
            "-auto-orient",
            "-thumbnail", f"{size[0]}x{size[1]}",
            "-colorspace", "sRGB",
            "-depth", "8",
            "png:-",
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45,
            )
            with Image.open(io.BytesIO(completed.stdout)) as opened:
                return opened.convert("RGB").copy()
        except Exception as exc:
            raise ImageLoadError(f"無法建立 RAW 縮圖：{path.name}") from exc

    image = load_standard(path)
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


class ImageCache:
    """A deliberately tiny cache so the viewer stays light."""

    def __init__(self, max_items: int = 3) -> None:
        self.max_items = max_items
        self._items: OrderedDict[Path, Image.Image] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, path: Path) -> Image.Image | None:
        with self._lock:
            image = self._items.get(path)
            if image is not None:
                self._items.move_to_end(path)
            return image

    def put(self, path: Path, image: Image.Image) -> None:
        with self._lock:
            self._items[path] = image
            self._items.move_to_end(path)
            while len(self._items) > self.max_items:
                _, old = self._items.popitem(last=False)
                try:
                    old.close()
                except Exception:
                    pass

    def load(self, path: Path) -> Image.Image:
        cached = self.get(path)
        if cached is not None:
            return cached
        image = load_image(path)
        self.put(path, image)
        return image

    def clear(self) -> None:
        with self._lock:
            for image in self._items.values():
                try:
                    image.close()
                except Exception:
                    pass
            self._items.clear()
