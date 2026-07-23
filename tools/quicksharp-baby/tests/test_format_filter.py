from pathlib import Path

from quicksharp_baby.app import _mode_for_path, _pair_key


def test_modes() -> None:
    assert _mode_for_path(Path("A.JPG")) == "JPG"
    assert _mode_for_path(Path("A.ARW")) == "RAW"
    assert _mode_for_path(Path("A.TIFF")) == "TIF"


def test_exact_stem_pairing() -> None:
    assert _pair_key(Path("IMG_001.JPG")) == _pair_key(Path("IMG_001.ARW"))
    assert _pair_key(Path("IMG_001_EDIT.TIF")) != _pair_key(Path("IMG_001.ARW"))
