from pathlib import Path

from quicksharp_baby.core import ViewState, natural_key, visible_source_rect


def test_natural_sort() -> None:
    names = [Path("10.jpg"), Path("2.jpg"), Path("1.jpg")]
    assert [p.name for p in sorted(names, key=natural_key)] == ["1.jpg", "2.jpg", "10.jpg"]


def test_same_normalized_center_maps_across_sizes() -> None:
    state = ViewState(zoom=3.0, center_x=0.72, center_y=0.18)
    rect_a = visible_source_rect(4000, 4000, 1200, 800, state)
    rect_b = visible_source_rect(8000, 8000, 1200, 800, state)
    center_a = ((rect_a[0] + rect_a[2]) / 2 / 4000, (rect_a[1] + rect_a[3]) / 2 / 4000)
    center_b = ((rect_b[0] + rect_b[2]) / 2 / 8000, (rect_b[1] + rect_b[3]) / 2 / 8000)
    assert center_a == center_b == (0.72, 0.18)


def test_zoom_supports_large_screen_inspection() -> None:
    state = ViewState(zoom=99.0).normalized()
    assert state.zoom == 16.0
