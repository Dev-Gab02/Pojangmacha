"""
Shared utility functions for admin panel
"""
import re

def is_valid_email(email_str: str) -> bool:
    """Check if email format is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email_str) is not None

def close_dialog(page, dialog):
    """Close a dialog and update the page"""
    dialog.open = False
    page.update()