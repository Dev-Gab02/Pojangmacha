import flet as ft
import time
import threading

def splash_view(page: ft.Page, on_complete):
    """
    Display splash screen with logo for 3 seconds
    Mobile optimized: 400x700
    """
    page.title = "Pojangmacha"
    
    logo = ft.Image(
        src="assets/logo.jpg",
        width=300,
        height=300,
        fit=ft.ImageFit.CONTAIN
    )
    
    splash_container = ft.Container(
        content=ft.Column([
            logo
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#FEB23F",
        expand=True,
        alignment=ft.alignment.center,
        width=400,
        height=700
    )
    
    page.clean()
    page.add(splash_container)
    page.update()
    
    def splash_timer():
        time.sleep(3)
        on_complete()
    
    thread = threading.Thread(target=splash_timer, daemon=True)
    thread.start()