# ui/profile_view.py
import os
import flet as ft
from core.db import SessionLocal
from core.auth_service import hash_password, verify_password
from models.user import User

# Where profile images will be stored
UPLOAD_DIR = "assets/uploads/profiles"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def _is_allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

def profile_view(page: ft.Page):
    _ensure_upload_dir()
    db = SessionLocal()

    user_data = page.session.get("user")
    if not user_data:
        page.snack_bar = ft.SnackBar(ft.Text("Please log in to access your profile."), open=True)
        page.update()
        page.go("/login")
        return

    user = db.query(User).get(user_data["id"])
    if not user:
        page.snack_bar = ft.SnackBar(ft.Text("User not found."), open=True)
        page.update()
        page.go("/login")
        return

    page.title = "Profile - Pojangmacha"

    # Fields
    full_name = ft.TextField(label="Full Name", value=user.full_name or "", width=360)
    email_tf = ft.TextField(label="Email", value=user.email or "", disabled=True, width=360)
    phone = ft.TextField(label="Phone Number", value=user.phone or "", width=360)
    msg = ft.Text("", color="red")

    # Profile image display
    img_src = user.profile_image if user.profile_image else "assets/default-profile.png"
    profile_img = ft.Image(src=img_src, width=150, height=150, fit=ft.ImageFit.COVER, border_radius=8)

    # File picker
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    selected_image_path = {"path": user.profile_image or ""}

    def on_file_picked(e: ft.FilePickerResultEvent):
        # e.files is a list of picked files
        if not e.files:
            return
        f = e.files[0]
        # file properties: f.path, f.name, f.size (bytes)
        if f.size and f.size > MAX_FILE_SIZE:
            page.snack_bar = ft.SnackBar(ft.Text("File too large. Max 2 MB allowed."), open=True)
            page.update()
            return
        if not _is_allowed_file(f.name):
            page.snack_bar = ft.SnackBar(ft.Text("Invalid file type. Use PNG/JPG/JPEG."), open=True)
            page.update()
            return
        # copy file to uploads dir
        try:
            filename = os.path.basename(f.path)
            dest = os.path.join(UPLOAD_DIR, filename)
            # avoid clobbering by adding a numeric suffix if exists
            base, ext = os.path.splitext(dest)
            i = 1
            while os.path.exists(dest):
                dest = f"{base}_{i}{ext}"
                i += 1
            with open(f.path, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            # normalize path for src
            selected_image_path["path"] = dest.replace("\\", "/")
            profile_img.src = selected_image_path["path"]
            profile_img.update()
            page.snack_bar = ft.SnackBar(ft.Text("Image selected."), open=True)
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Upload failed: {ex}"), open=True)
            page.update()

    file_picker.on_result = on_file_picked

    upload_btn = ft.ElevatedButton("Choose Image", on_click=lambda e: file_picker.pick_files(allow_multiple=False))

    # Save profile
    def save_profile(e):
        if not full_name.value.strip():
            msg.value = "Full name cannot be empty."
            msg.color = "red"
            page.update()
            return
        try:
            user.full_name = full_name.value.strip()
            user.phone = phone.value.strip()
            if selected_image_path["path"]:
                user.profile_image = selected_image_path["path"]
            db.add(user)
            db.commit()
            # update session info
            page.session.set("user", {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})
            msg.value = "Profile updated successfully."
            msg.color = "green"
        except Exception as ex:
            db.rollback()
            msg.value = f"Error saving profile: {ex}"
            msg.color = "red"
        page.update()

    save_btn = ft.ElevatedButton("Save Changes", on_click=save_profile)

    # Change password fields
    current_pwd = ft.TextField(label="Current Password", password=True, can_reveal_password=True, width=360)
    new_pwd = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=360)
    confirm_pwd = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True, width=360)
    pwd_msg = ft.Text("", color="red")

    def change_password(e):
        # validations
        if not current_pwd.value or not new_pwd.value or not confirm_pwd.value:
            pwd_msg.value = "All fields are required."
            pwd_msg.color = "red"
            page.update(); return
        if not verify_password(current_pwd.value, user.password_hash):
            pwd_msg.value = "Current password is incorrect."
            pwd_msg.color = "red"
            page.update(); return
        if new_pwd.value != confirm_pwd.value:
            pwd_msg.value = "New passwords do not match."
            pwd_msg.color = "red"
            page.update(); return
        if len(new_pwd.value) < 6:
            pwd_msg.value = "New password must be at least 6 characters."
            pwd_msg.color = "red"
            page.update(); return
        # commit password
        try:
            user.password_hash = hash_password(new_pwd.value)
            db.add(user); db.commit()
            pwd_msg.value = "Password updated successfully."
            pwd_msg.color = "green"
            # clear inputs
            current_pwd.value = new_pwd.value = confirm_pwd.value = ""
        except Exception as ex:
            db.rollback()
            pwd_msg.value = f"Failed to update password: {ex}"
            pwd_msg.color = "red"
        page.update()

    change_pwd_btn = ft.ElevatedButton("Update Password", on_click=change_password)

    # Logout button - convenience
    def handle_logout(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.go("/login")

    logout_btn = ft.ElevatedButton("Logout", icon=ft.icons.LOGOUT, on_click=handle_logout, bgcolor=ft.Colors.RED_200)

    # Layout
    left_col = ft.Column([
        profile_img,
        ft.Row([upload_btn]),
        ft.Divider(),
        ft.Text("Account", weight="bold"),
        full_name, email_tf, phone, save_btn, msg,
        ft.Divider(),
        ft.Row([logout_btn])
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    right_col = ft.Column([
        ft.Text("Change Password", weight="bold"),
        current_pwd, new_pwd, confirm_pwd,
        change_pwd_btn, pwd_msg
    ], horizontal_alignment=ft.CrossAxisAlignment.START)

    page.clean()
    page.add(
        ft.Column([
            ft.Text("👤 Your Profile", size=24, weight="bold"),
            ft.Divider(),
            ft.Row([left_col, ft.VerticalDivider(width=20), right_col], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.ElevatedButton("Back to Home", on_click=lambda e: page.go("/home"))
        ], scroll=ft.ScrollMode.AUTO)
    )
    page.update()
