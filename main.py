import flet as ft

def main(page: ft.Page):
    page.title = "Pojangmacha"
    page.add(ft.Text("Welcome to Pojangmacha!"))

if __name__ == "__main__":
    ft.app(target=main)
