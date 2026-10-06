from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timedelta, timezone
from app.core.security import hash_password, verify_password, get_current_user_from_refresh_token, get_current_user
from app.core.database import get_db
from app.models import User, College, EmergencyContact
from app.schemas.schemas import UserSignup, Login, VerifyOTPRequest, ResetPasswordRequest, ResendOTPRequest, ForgotPasswordRequest, UserProfile
from app.utils.email_utils import send_otp_email
from app.utils.auth_utils import (
    validate_password,
    generate_otp,
    create_jwt_token,
    create_refresh_token,
    create_otp_token,
    verify_otp_token
)

router = APIRouter(prefix="/auth", tags=["Auth"])
@router.get("/home")
async def home():
    return {"message": "Welcome to SheConnect API"}

@router.get("/me", response_model=UserProfile)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user



# ================= SIGNUP =================
@router.post("/signup")
async def signup(
    user: UserSignup,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user.email_id = user.email_id.lower()
    existing_user = db.query(User).filter(
        User.email_id == user.email_id.lower()
    ).first()

    if not existing_user:
        raise HTTPException(status_code=403, detail="Email not allowed")

    if existing_user.is_active:
        raise HTTPException(status_code=400, detail="User already registered")


    if user.phone_no:
        phone_exists = db.query(User).filter(User.phone_no == user.phone_no).first()
        if phone_exists and phone_exists.user_id != existing_user.user_id:
            raise HTTPException(status_code=400, detail="Phone number already registered by another user.")

    
    if user.emergency_contacts:
        if len(user.emergency_contacts) > 2:
            raise HTTPException(status_code=400, detail="Cannot add more than 2 emergency contacts.")
        e_numbers = [contact.phone_no for contact in user.emergency_contacts]
        if len(e_numbers) != len(set(e_numbers)):
            raise HTTPException(status_code=400, detail="Emergency contact numbers cannot be duplicates.")
        
    is_valid, message = validate_password(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    anonymous_id = str(uuid.uuid4())[:5]
    existing_user.name = user.name
    existing_user.phone_no = user.phone_no
    existing_user.password = hash_password(user.password)
    existing_user.is_verified = False
    existing_user.is_active = True
    existing_user.college_id = user.college_id
    existing_user.anonymous_id = anonymous_id

    # Clear existing emergency contacts to prevent duplicates on re-attempted signup
    db.query(EmergencyContact).filter(EmergencyContact.user_id == existing_user.user_id).delete(synchronize_session=False)

    # Create and add emergency contacts to the session
    for contact_data in user.emergency_contacts:
        new_contact = EmergencyContact(
            user_id=existing_user.user_id,
            emergency_name=contact_data.emergency_name,
            phone_no=contact_data.phone_no,
            email=contact_data.email
        )
        db.add(new_contact)

    otp = generate_otp()
    otp_token = create_otp_token(existing_user.email_id, otp, "signup")

    existing_user.last_otp_sent_at = datetime.now()
    db.commit()
    db.refresh(existing_user)

    background_tasks.add_task(send_otp_email, existing_user.email_id, otp)

    return {
        "message": "Signup successful. OTP sent.",
        "anonymous_id": anonymous_id,
        "otp_token": otp_token
    }

# ================= VERIFY SIGNUP OTP =================
@router.post("/verify-otp")
def verify_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    email = request.email.lower()
    payload = verify_otp_token(request.otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "signup":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}

# ================= LOGIN =================
@router.post("/login")
async def login(
    user: Login,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(
        User.email_id == user.email_id.lower()
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

   
    if not db_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Please complete signup first"
        )


    if not db_user.password:
        raise HTTPException(
            status_code=400,
            detail="User has not set password"
        )


    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")


    if not db_user.is_verified:
        otp = generate_otp()
        otp_token = create_otp_token(db_user.email_id, otp, "signup")

        db_user.last_otp_sent_at = datetime.now()
        db.commit()

        background_tasks.add_task(send_otp_email, db_user.email_id, otp)

        return {
            "message": "Email not verified. OTP sent.",
            "otp_token": otp_token,
            "first_login": True
        }


    access_token = create_jwt_token(db_user.user_id)
    refresh_token = create_refresh_token(db_user.user_id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "first_login": False
    }

@router.post("/refresh-token")
async def refresh_token(current_user: User = Depends(get_current_user_from_refresh_token)):
    """
    Generates a new access token from a valid refresh token.
    """
    new_access_token = create_jwt_token(current_user.user_id)
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


# ================= FORGOT PASSWORD =================
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = request.email.lower()
    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Please complete signup first")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    otp = generate_otp()
    otp_token = create_otp_token(email, otp, "forgot")

    user.last_otp_sent_at = datetime.now()
    db.commit()

    background_tasks.add_task(send_otp_email, email, otp)

    return {
        "message": "OTP sent to email",
        "otp_token": otp_token
    }


# ================= VERIFY FORGOT OTP =================
@router.post("/verify-forgot-otp")
def verify_forgot_otp(
    request: VerifyOTPRequest
):
    email = request.email.lower()
    payload = verify_otp_token(request.otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "forgot":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    return {"message": "OTP verified successfully"}


# ================= RESET PASSWORD =================
@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    email = request.email.lower()
    payload = verify_otp_token(request.otp_token)

    if payload["sub"] != email:
        raise HTTPException(status_code=400, detail="Email mismatch")

    if payload["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if payload["purpose"] != "forgot":
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")

    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_valid, message = validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    user.password = hash_password(request.new_password)
    db.commit()

    return {"message": "Password reset successful"}


# ================= RESEND OTP =================
@router.post("/resend-otp")
async def resend_otp(
    request: ResendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = request.email.lower()
    user = db.query(User).filter(User.email_id == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.purpose not in ["signup", "forgot"]:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    if request.purpose == "signup" and user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    if user.last_otp_sent_at and datetime.now() < user.last_otp_sent_at + timedelta(seconds=60):
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before resending OTP")

    otp = generate_otp()
    otp_token = create_otp_token(email, otp, request.purpose)

    user.last_otp_sent_at = datetime.now()
    db.commit()

    background_tasks.add_task(send_otp_email, email, otp)

    return {
        "message": "OTP resent successfully",
        "otp_token": otp_token
    }

@router.get("/colleges")
def get_colleges(db: Session = Depends(get_db)):
    colleges = db.query(College).all()
    return colleges