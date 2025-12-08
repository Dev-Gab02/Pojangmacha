import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
APP_NAME = os.getenv("APP_NAME", "Pojangmacha")

# Store verification codes temporarily (in production, use Redis or database)
verification_codes = {}
password_reset_codes = {}  # For password reset

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return str(random.randint(100000, 999999))

def send_verification_email(to_email: str, verification_code: str) -> bool:
    """
    Send verification code to user's email
    Returns True if successful, False otherwise
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("Email configuration missing in .env file")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{APP_NAME} - Email Verification"
        message["From"] = f"{APP_NAME} <{SMTP_EMAIL}>"
        message["To"] = to_email

        # HTML email body
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                <div style="text-align: center; max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Welcome to {APP_NAME}!</h2>
                    <p style="color: #666; font-size: 16px;">Thank you for signing up! Please verify your email address to complete your registration.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                        <p style="color: #666; margin-bottom: 10px;">Your verification code is:</p>
                        <h1 style="color: #007bff; font-size: 36px; letter-spacing: 5px; margin: 10px 0;">{verification_code}</h1>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">This code will expire in <strong>10 minutes</strong>.</p>
                    <p style="color: #666; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        This is an automated message from {APP_NAME}. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """

        # Attach HTML content
        part = MIMEText(html, "html")
        message.attach(part)

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure connection
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(message)
        
        print(f"Verification email sent to {to_email}")
        return True
    
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_password_reset_email(to_email: str, reset_code: str) -> bool:
    """
    Send password reset code to user's email
    Returns True if successful, False otherwise
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("Email configuration missing in .env file")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{APP_NAME} - Password Reset Code"
        message["From"] = f"{APP_NAME} <{SMTP_EMAIL}>"
        message["To"] = to_email

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                <div style="text-align: center; max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">Password Reset Request</h2>
                    <p style="color: #666; font-size: 16px;">We received a request to reset your password. Use the code below to proceed.</p>
                    
                    <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; border: 2px solid #ffc107;">
                        <p style="color: #856404; margin-bottom: 10px; font-weight: bold;">Your password reset code is:</p>
                        <h1 style="color: #dc3545; font-size: 36px; letter-spacing: 5px; margin: 10px 0;">{reset_code}</h1>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">This code will expire in <strong>10 minutes</strong>.</p>
                    <p style="color: #dc3545; font-size: 14px; font-weight: bold;">If you didn't request this, please secure your account immediately.</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        This is an automated message from {APP_NAME}. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """

        part = MIMEText(html, "html")
        message.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(message)
        
        print(f"Password reset email sent to {to_email}")
        return True
    
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False

def store_verification_code(email: str, code: str):
    """Store verification code with timestamp"""
    import time
    verification_codes[email] = {
        "code": code,
        "timestamp": time.time()
    }

def store_password_reset_code(email: str, code: str):
    """Store password reset code with timestamp"""
    import time
    password_reset_codes[email] = {
        "code": code,
        "timestamp": time.time()
    }

def verify_code(email: str, entered_code: str) -> bool:
    """
    Verify if the entered code matches and is not expired (10 minutes)
    Returns True if valid, False otherwise
    """
    import time
    
    if email not in verification_codes:
        return False
    
    stored_data = verification_codes[email]
    stored_code = stored_data["code"]
    timestamp = stored_data["timestamp"]
    
    # Check if expired (10 minutes = 600 seconds)
    if time.time() - timestamp > 600:
        del verification_codes[email]
        return False
    
    # Check if code matches
    if entered_code == stored_code:
        del verification_codes[email]  # Remove after successful verification
        return True
    
    return False

def verify_password_reset_code(email: str, entered_code: str) -> bool:
    """
    Verify password reset code
    Returns True if valid, False otherwise
    """
    import time
    
    if email not in password_reset_codes:
        return False
    
    stored_data = password_reset_codes[email]
    stored_code = stored_data["code"]
    timestamp = stored_data["timestamp"]
    
    # Check if expired (10 minutes = 600 seconds)
    if time.time() - timestamp > 600:
        del password_reset_codes[email]
        return False
    
    # Check if code matches
    if entered_code == stored_code:
        del password_reset_codes[email]  # Remove after successful verification
        return True
    
    return False

def resend_verification_code(email: str) -> bool:
    """Generate and send a new verification code"""
    code = generate_verification_code()
    if send_verification_email(email, code):
        store_verification_code(email, code)
        return True
    return False

def resend_password_reset_code(email: str) -> bool:
    """Generate and send a new password reset code"""
    code = generate_verification_code()
    if send_password_reset_email(email, code):
        store_password_reset_code(email, code)
        return True
    return False