import random
import hashlib
from sqlalchemy.orm import Session
from models.user import User
from core.email_service import send_verification_email, store_verification_code, verify_code

# Store 2FA codes temporarily (email → code)
two_fa_codes = {}

def generate_2fa_code():
    """Generate a 6-digit 2FA code"""
    return str(random.randint(100000, 999999))

def generate_backup_codes(count=8):
    """Generate backup codes for account recovery"""
    codes = []
    for _ in range(count):
        code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        # Format as XXXX-XXXX
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes

def hash_backup_code(code: str) -> str:
    """Hash a backup code for secure storage"""
    return hashlib.sha256(code.encode()).hexdigest()

def store_backup_codes(user: User, codes: list):
    """Store hashed backup codes in database"""
    hashed_codes = [hash_backup_code(code) for code in codes]
    user.two_fa_backup_codes = ','.join(hashed_codes)

def verify_backup_code(user: User, entered_code: str) -> bool:
    """Verify a backup code and remove it after use"""
    if not user.two_fa_backup_codes:
        return False
    
    hashed_entered = hash_backup_code(entered_code)
    stored_codes = user.two_fa_backup_codes.split(',')
    
    if hashed_entered in stored_codes:
        # Remove used code
        stored_codes.remove(hashed_entered)
        user.two_fa_backup_codes = ','.join(stored_codes)
        return True
    
    return False

def send_2fa_code(email: str) -> bool:
    """Generate and send 2FA code via email"""
    import time
    
    code = generate_2fa_code()
    
    # Create custom email for 2FA
    from core.email_service import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, APP_NAME
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("❌ Email configuration missing")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{APP_NAME} - Two-Factor Authentication"
        message["From"] = f"{APP_NAME} <{SMTP_EMAIL}>"
        message["To"] = email

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; text-align: center;">🔐 Two-Factor Authentication</h2>
                    <p style="color: #666; font-size: 16px;">A login attempt requires verification.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                        <p style="color: #666; margin-bottom: 10px;">Your authentication code is:</p>
                        <h1 style="color: #28a745; font-size: 36px; letter-spacing: 5px; margin: 10px 0;">{code}</h1>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">This code will expire in <strong>5 minutes</strong>.</p>
                    <p style="color: #999; font-size: 12px;">If you didn't attempt to login, please secure your account immediately.</p>
                    
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
        
        # Store code with timestamp
        two_fa_codes[email] = {
            "code": code,
            "timestamp": time.time()
        }
        
        print(f"✅ 2FA code sent to {email}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to send 2FA email: {e}")
        return False

def verify_2fa_code(email: str, entered_code: str) -> bool:
    """Verify 2FA code (5 minute expiry)"""
    import time
    
    if email not in two_fa_codes:
        return False
    
    stored_data = two_fa_codes[email]
    stored_code = stored_data["code"]
    timestamp = stored_data["timestamp"]
    
    # Check if expired (5 minutes = 300 seconds)
    if time.time() - timestamp > 300:
        del two_fa_codes[email]
        return False
    
    # Check if code matches
    if entered_code == stored_code:
        del two_fa_codes[email]  # Remove after successful verification
        return True
    
    return False

def enable_2fa(db: Session, user_id: int) -> list:
    """Enable 2FA for user and return backup codes"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    
    # Store hashed backup codes
    store_backup_codes(user, backup_codes)
    
    # Enable 2FA
    user.two_fa_enabled = True
    db.commit()
    
    print(f"✅ 2FA enabled for {user.email}")
    return backup_codes

def disable_2fa(db: Session, user_id: int) -> bool:
    """Disable 2FA for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.two_fa_enabled = False
    user.two_fa_backup_codes = None
    db.commit()
    
    print(f"✅ 2FA disabled for {user.email}")
    return True

def is_2fa_enabled(db: Session, email: str) -> bool:
    """Check if user has 2FA enabled"""
    user = db.query(User).filter(User.email == email).first()
    return user.two_fa_enabled if user else False