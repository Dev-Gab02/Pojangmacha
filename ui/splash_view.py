import flet as ft
import time
import threading

def splash_view(page: ft.Page, on_complete):
    """
    Display splash screen with logo for 3 seconds
    Args:
        page: Flet page object
        on_complete: Callback function to execute after splash
    """
    page.title = "Pojangmacha"
    
    # Logo image - centered only
    logo = ft.Image(
        src="assets/logo.jpg",
        width=400,
        height=400,
        fit=ft.ImageFit.CONTAIN
    )
    
    # Splash container - matches logo background color
    splash_container = ft.Container(
        content=ft.Column([
            logo
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#FEB23F",  # Exact orange from your logo
        expand=True,
        alignment=ft.alignment.center
    )
    
    # Display splash screen
    page.clean()
    page.add(splash_container)
    page.update()
    
    # Wait 3 seconds then navigate to login
    def splash_timer():
        time.sleep(3)
        on_complete()
    
    thread = threading.Thread(target=splash_timer, daemon=True)
    thread.start()