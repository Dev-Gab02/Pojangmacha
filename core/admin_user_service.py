from sqlalchemy.orm import Session
from models.user import User
from core.auth_service import hash_password
from core.email_service import generate_verification_code, send_verification_email, store_verification_code, verify_code

def create_user_by_admin(db: Session, full_name: str, email: str, password: str, role: str = "customer") -> User:
    """
    Create a new user by admin (bypasses some normal signup checks)
    """
    hashed_password = hash_password(password)
    
    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed_password,
        phone="",  # Admin-created users don't need phone initially
        role=role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

def update_user_by_admin(db: Session, user_id: int, full_name: str = None, email: str = None, role: str = None, new_password: str = None) -> tuple:
    """
    Update user by admin
    Returns (success: bool, message: str)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False, "User not found"
    
    try:
        if full_name:
            user.full_name = full_name
        
        if email and email != user.email:
            # Check if email already exists
            existing = db.query(User).filter(User.email == email, User.id != user_id).first()
            if existing:
                return False, "Email already in use"
            user.email = email
        
        if role and role in ["admin", "customer"]:
            user.role = role
        
        if new_password:
            user.password_hash = hash_password(new_password)
        
        db.commit()
        return True, "User updated successfully"
    
    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}"

def delete_user_by_admin(db: Session, user_id: int) -> tuple:
    """
    Delete user by admin
    Returns (success: bool, message: str)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False, "User not found"
    
    try:
        db.delete(user)
        db.commit()
        return True, f"User {user.email} deleted successfully"
    
    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}"

def get_all_users(db: Session):
    """Get all users"""
    return db.query(User).all()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()
