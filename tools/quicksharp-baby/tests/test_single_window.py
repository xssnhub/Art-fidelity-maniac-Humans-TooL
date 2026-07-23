from tkinter import Tk, Toplevel

from quicksharp_baby.app import QuickSharpBaby


def test_filmstrip_is_not_a_detached_window() -> None:
    root = Tk()
    app = QuickSharpBaby(root)
    root.update_idletasks()

    assert app.filmstrip.winfo_toplevel() == root
    assert not any(isinstance(child, Toplevel) for child in root.winfo_children())

    app._show_filmstrip()
    root.update_idletasks()
    assert app.filmstrip.winfo_manager() == "place"

    root.withdraw()
    root.update_idletasks()
    assert not app.filmstrip.winfo_viewable()

    root.deiconify()
    root.update_idletasks()
    assert app.filmstrip.winfo_toplevel() == root

    app.close()
