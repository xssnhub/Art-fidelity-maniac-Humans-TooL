from pathlib import Path

from quicksharp_baby.core import list_folder_contents, scan_folder


def test_folder_browser_shows_nested_folders_and_supported_files(tmp_path: Path) -> None:
    child = tmp_path / "子層"
    child.mkdir()
    (tmp_path / "02.JPG").write_bytes(b"jpg")
    (tmp_path / "01.tif").write_bytes(b"tif")
    (tmp_path / "notes.txt").write_text("ignore")

    folders, photos = list_folder_contents(tmp_path)

    assert folders == [child]
    assert [path.name for path in photos] == ["01.tif", "02.JPG"]


def test_import_reads_exact_selected_layer_only(tmp_path: Path) -> None:
    child = tmp_path / "子層"
    child.mkdir()
    (tmp_path / "root.jpg").write_bytes(b"jpg")
    (child / "child.jpg").write_bytes(b"jpg")

    assert [path.name for path in scan_folder(tmp_path)] == ["root.jpg"]
    assert [path.name for path in scan_folder(child)] == ["child.jpg"]
