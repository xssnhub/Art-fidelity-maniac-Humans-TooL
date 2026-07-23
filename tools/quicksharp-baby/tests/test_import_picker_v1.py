from __future__ import annotations

import ast
from pathlib import Path


def test_choose_folder_uses_v010_native_picker_signature() -> None:
    source = (Path(__file__).parents[1] / "quicksharp_baby" / "app.py").read_text()
    tree = ast.parse(source)
    choose = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "choose_folder"
    )
    calls = [node for node in ast.walk(choose) if isinstance(node, ast.Call)]
    picker = next(
        call for call in calls
        if isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "filedialog"
        and call.func.attr == "askdirectory"
    )
    assert len(picker.args) == 0
    assert [keyword.arg for keyword in picker.keywords] == ["title"]
