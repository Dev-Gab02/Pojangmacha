import flet as ft

def checkout_view(page, on_back, total=0, cart_items=None, on_checkout=None):
    header = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color="black",
                        on_click=on_back
                    ),
                    ft.Text("Checkout", size=20, weight="bold", color="black"),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=15, left=5, right=15, bottom=8)
            ),
            ft.Divider(height=1, color="grey300", thickness=1)
        ], spacing=0),
        bgcolor="white",
        padding=ft.padding.only(left=0, right=0, top=0, bottom=0)
    )

    payment_method_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Payment method", size=16, weight="bold", color='black'),
                ft.Text("Change", size=13, color="blue700"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=20, color="grey700"),
                    ft.Text("Cash", size=15, color="black"),
                ], spacing=8),
                ft.Text(f"₱{total:.2f}", size=15, weight="bold", color="black"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=8),
        bgcolor="white",
        border_radius=12,
        padding=16,
        margin=ft.margin.symmetric(vertical=16, horizontal=16),
        shadow=ft.BoxShadow(blur_radius=8, color="grey200")
    )

    # --- Order summary container ---
    order_summary_rows = []
    if cart_items:
        for item in cart_items:
            order_summary_rows.append(
                ft.Row([
                    ft.Column([
                        ft.Text(f"{item['quantity']}x {item['name']}", size=15, color="black"),
                        ft.Text(item.get("note", ""), size=11, color="grey600") if item.get("note") else ft.Container(),
                    ], spacing=0, expand=True),
                    ft.Text(f"₱{item['subtotal']:.2f}", size=15, color="black", weight="bold"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

    order_summary_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=20, color="grey700"),
                ft.Text("Order summary", size=16, weight="bold", color="black"),
            ], spacing=8),
            *order_summary_rows
        ], spacing=8),
        bgcolor="white",
        border_radius=12,
        padding=16,
        margin=ft.margin.symmetric(vertical=0, horizontal=16),
        shadow=ft.BoxShadow(blur_radius=8, color="grey200")
    )

    # --- Checkout button and total row at the very bottom ---
    checkout_footer = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Total", size=16, weight="bold", color="black"),
                ft.Text(f"₱{total:.2f}", size=18, weight="bold", color="black"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ElevatedButton(
                "Checkout",
                on_click=on_checkout,
                style=ft.ButtonStyle(
                    bgcolor="#FEB23F",
                    color="white"
                ),
                width=350,
                height=45
            )
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="white",
        padding=ft.padding.only(left=25, right=25, top=14, bottom=12), 
        shadow=ft.BoxShadow(blur_radius=10, color="grey300")
    )

    # --- Main layout: scrollable content + fixed footer ---
    return ft.Column([
        ft.Container(
            content=ft.Column([
                header,
                payment_method_container,
                order_summary_container,
            ], spacing=0),
            expand=True,
            bgcolor="grey100",
            padding=0,
            margin=0,
            # Optionally add scroll if you want the content to scroll
        ),
        checkout_footer
    ], expand=True, spacing=0)