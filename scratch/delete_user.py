import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
email = "sahanavibhute4@gmail.com"

try:
    user = db.query(User).filter(User.email_id == email).first()
    if user:
        db.delete(user)
        db.commit()
        print(f"Successfully deleted user with email {email}")
    else:
        print(f"User with email {email} not found")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
