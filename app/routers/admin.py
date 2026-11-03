from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timezone
from jose import jwt
import csv
import io
import os

from app.core.database import get_db
from app.core.security import (
    verify_password,
    hash_password,
    get_current_admin,
    require_super_admin,
    SECRET_KEY,
    ALGORITHM
)
from app.models.admin import Admin, SOSAlert
from app.models.user import User
from app.models.college import College
from app.models.carpool import CarpoolRide
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

# ── Schemas ──
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: int
    name: str
    email: str
    role: str
    college_id: Optional[int] = None
    college_name: Optional[str] = None

class CreateAdminRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "INSTITUTE_ADMIN"
    college_id: Optional[int] = None

class UpdateAlertStatusRequest(BaseModel):
    status: str  # ACKNOWLEDGED, RESOLVED, FALSE_ALARM
    resolution_notes: Optional[str] = None

class ToggleUserStatusRequest(BaseModel):
    is_active: bool

# ── Endpoints ──

@router.post("/auth/login", response_model=AdminLoginResponse)
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates an administrator (Super Admin or Institute Admin).
    """
    admin = db.query(Admin).filter(Admin.email == data.email.lower()).first()
    if not admin or not verify_password(data.password, admin.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative email or password"
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative account has been suspended"
        )

    token_data = {
        "admin_id": admin.admin_id,
        "role": admin.role,
        "college_id": admin.college_id,
        "scope": "admin"
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    college_name = admin.college.college_name if admin.college else None

    return AdminLoginResponse(
        access_token=token,
        admin_id=admin.admin_id,
        name=admin.name,
        email=admin.email,
        role=admin.role,
        college_id=admin.college_id,
        college_name=college_name
    )

@router.get("/me", response_model=AdminLoginResponse)
def get_admin_profile(admin: Admin = Depends(get_current_admin)):
    college_name = admin.college.college_name if admin.college else None
    return AdminLoginResponse(
        access_token="",
        admin_id=admin.admin_id,
        name=admin.name,
        email=admin.email,
        role=admin.role,
        college_id=admin.college_id,
        college_name=college_name
    )

@router.get("/dashboard-stats")
def get_dashboard_stats(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Returns analytics scoped by role (Global for Super Admin, Campus-specific for Institute Admin).
    """
    user_query = db.query(User)
    carpool_query = db.query(CarpoolRide)
    sos_query = db.query(SOSAlert)

    # Multi-tenancy filter
    if admin.role == "INSTITUTE_ADMIN" and admin.college_id:
        user_query = user_query.filter(User.college_id == admin.college_id)
        # Filter SOS to students belonging to this college
        sos_query = sos_query.join(User, SOSAlert.user_id == User.user_id).filter(User.college_id == admin.college_id)

    total_users = user_query.count()
    active_users = user_query.filter(User.is_active == True).count()
    verified_users = user_query.filter(User.is_verified == True).count()
    total_rides = carpool_query.count()
    
    active_sos = sos_query.filter(SOSAlert.status == "ACTIVE").count()
    total_sos = sos_query.count()

    total_colleges = db.query(College).count()

    return {
        "role": admin.role,
        "college_name": admin.college.college_name if admin.college else "All Platforms",
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "total_rides": total_rides,
        "active_sos": active_sos,
        "total_sos": total_sos,
        "total_colleges": total_colleges
    }

@router.get("/sos-alerts")
def get_sos_alerts(
    status_filter: Optional[str] = None,
    limit: int = 50,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Real-time and historic SOS alert logs with user details & coordinates.
    """
    query = db.query(SOSAlert).join(User, SOSAlert.user_id == User.user_id)

    if admin.role == "INSTITUTE_ADMIN" and admin.college_id:
        query = query.filter(User.college_id == admin.college_id)

    if status_filter:
        query = query.filter(SOSAlert.status == status_filter.upper())

    alerts = query.order_by(desc(SOSAlert.created_at)).limit(limit).all()

    results = []
    for a in alerts:
        results.append({
            "alert_id": a.alert_id,
            "user_id": a.user_id,
            "user_name": a.user_name or a.user.name or "Anonymous",
            "user_phone": a.user.phone_no,
            "user_email": a.user.email_id,
            "college": a.user.college.college_name if a.user.college else "General",
            "lat": a.lat,
            "lng": a.lng,
            "location_name": a.location_name,
            "accuracy": a.accuracy,
            "source": a.source,
            "status": a.status,
            "resolution_notes": a.resolution_notes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None
        })
    return results

@router.patch("/sos-alerts/{alert_id}/status")
def update_sos_alert_status(
    alert_id: int,
    data: UpdateAlertStatusRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Acknowledge, resolve, or mark an SOS alert as false alarm with resolution notes.
    """
    alert = db.query(SOSAlert).filter(SOSAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert record not found")

    alert.status = data.status.upper()
    alert.resolved_by = admin.admin_id
    alert.resolution_notes = data.resolution_notes
    if data.status.upper() in ["RESOLVED", "FALSE_ALARM"]:
        alert.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return {"message": f"Alert #{alert_id} status updated to {alert.status}", "status": alert.status}

@router.get("/users")
def get_users_list(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Lists users with multi-tenant filtering and search by name, phone, or email.
    """
    query = db.query(User)

    if admin.role == "INSTITUTE_ADMIN" and admin.college_id:
        query = query.filter(User.college_id == admin.college_id)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (User.name.ilike(search_term)) |
            (User.email_id.ilike(search_term)) |
            (User.phone_no.ilike(search_term))
        )

    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()

    return [
        {
            "user_id": u.user_id,
            "name": u.name or "Pending Verification",
            "email_id": u.email_id,
            "phone_no": u.phone_no,
            "college": u.college.college_name if u.college else "Independent",
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "is_aadhaar_verified": u.is_aadhaar_verified,
            "rating": u.rating,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

@router.patch("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    data: ToggleUserStatusRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Platform Kill-switch: Instant ban or activate user account.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Scope check for Institute Admin
    if admin.role == "INSTITUTE_ADMIN" and user.college_id != admin.college_id:
        raise HTTPException(status_code=403, detail="You can only manage students of your own institute")

    user.is_active = data.is_active
    db.commit()
    action = "activated" if data.is_active else "suspended"
    return {"message": f"User {user.email_id} has been {action}", "is_active": user.is_active}

@router.get("/colleges")
def get_colleges_list(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    List colleges and student counts.
    """
    colleges = db.query(College).all()
    results = []
    for c in colleges:
        count = db.query(User).filter(User.college_id == c.college_id).count()
        results.append({
            "college_id": c.college_id,
            "college_name": c.college_name,
            "total_students": count
        })
    return results

@router.post("/colleges", dependencies=[Depends(require_super_admin)])
def create_college(name: str, db: Session = Depends(get_db)):
    """
    Super Admin endpoint to onboard a new College / University.
    """
    clean_name = name.strip()
    existing = db.query(College).filter(College.college_name.ilike(clean_name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="College already exists")

    new_c = College(college_name=clean_name)
    db.add(new_c)
    db.commit()
    db.refresh(new_c)
    return {"message": f"College {clean_name} registered successfully", "college_id": new_c.college_id}

@router.post("/create-admin", dependencies=[Depends(require_super_admin)])
def create_new_admin(data: CreateAdminRequest, db: Session = Depends(get_db)):
    """
    Super Admin endpoint to issue new administrative access (e.g. for a college security head).
    """
    existing = db.query(Admin).filter(Admin.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin with this email already exists")

    new_admin = Admin(
        name=data.name.strip(),
        email=data.email.lower().strip(),
        password=hash_password(data.password),
        role=data.role.upper(),
        college_id=data.college_id if data.role.upper() == "INSTITUTE_ADMIN" else None,
        is_active=True
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"message": f"Admin {new_admin.name} ({new_admin.role}) created successfully!"}

