# core/utils.py
import flet as ft
from typing import Optional

_loading_ctrl: Optional[ft.AlertDialog] = None

def show_loading(page: ft.Page, text: str = "Please wait..."):
    """Show a small modal loading indicator."""
    global _loading_ctrl
    if _loading_ctrl is None:
        _loading_ctrl = ft.AlertDialog(
            modal=True,
            content=ft.Row([ft.ProgressRing(), ft.Text(text)], alignment=ft.MainAxisAlignment.CENTER),
            actions=[]
        )
    if _loading_ctrl not in page.overlay:
        page.overlay.append(_loading_ctrl)
    _loading_ctrl.open = True
    page.update()

def hide_loading(page: ft.Page):
    """Hide loading indicator."""
    global _loading_ctrl
    if _loading_ctrl:
        _loading_ctrl.open = False
        page.update()
