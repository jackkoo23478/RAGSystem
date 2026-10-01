import sys
from app.db.session import SessionLocal
from app.features.auth.repository import get_user_by_email

def create_admin_user(email: str):
    db = SessionLocal()
    try :
        user = get_user_by_email(db, email)
        if user is None :
            print(f"No user found with email {email}. Please register the user first.")
            return 
        
        user.role = "admin"
        db.commit()
        print(f"User with email {email} has been promoted to admin.")
    finally:
        db.close()
        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    create_admin_user(email)
