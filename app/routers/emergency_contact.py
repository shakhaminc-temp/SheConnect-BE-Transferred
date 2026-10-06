from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, EmergencyContact
from app.schemas.schemas import EmergencyContactSchema, EmergencyContactResponse

router = APIRouter(prefix="/emergency-contacts", tags=["Emergency Contacts"])

MAX_CONTACTS = 2

@router.post("/", response_model=EmergencyContactResponse, status_code=status.HTTP_201_CREATED)
def add_emergency_contact(
    contact_data: EmergencyContactSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adds a new emergency contact for the logged-in user.
    A user can have a maximum of 2 emergency contacts.
    """
    contact_count = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).count()
    if contact_count >= MAX_CONTACTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot add more than {MAX_CONTACTS} emergency contacts.")

    if current_user.phone_no == contact_data.phone_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot add yourself as an emergency contact.")

    existing_contact = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.phone_no == contact_data.phone_no,
        EmergencyContact.is_active == True
    ).first()
    if existing_contact:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This phone number is already registered as an emergency contact.")

    # We use model_dump but we excluded gender from schema, so it's safe.
    new_contact = EmergencyContact(user_id=current_user.user_id, **contact_data.model_dump())
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact

@router.get("/", response_model=List[EmergencyContactResponse])
def get_emergency_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all emergency contacts for the logged-in user.
    """
    return db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).all()

@router.put("/{contact_id}", response_model=EmergencyContactResponse)
def update_emergency_contact(
    contact_id: int,
    contact_data: EmergencyContactSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing emergency contact.
    """
    contact = db.query(EmergencyContact).filter(
        EmergencyContact.emergency_id == contact_id,
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found.")

    if contact_data.phone_no != contact.phone_no:
        existing_contact = db.query(EmergencyContact).filter(
            EmergencyContact.user_id == current_user.user_id,
            EmergencyContact.phone_no == contact_data.phone_no,
            EmergencyContact.is_active == True
        ).first()
        if existing_contact:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This phone number is already registered as an emergency contact.")

    for key, value in contact_data.model_dump().items():
        setattr(contact, key, value)
    
    db.commit()
    db.refresh(contact)
    return contact

@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_emergency_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes an emergency contact.
    """
    contact = db.query(EmergencyContact).filter(
        EmergencyContact.emergency_id == contact_id,
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found.")
    
    contact.is_active = False
    contact.deleted_at = datetime.now(timezone.utc)
    db.commit()

from app.schemas.schemas import SOSRequest
from app.utils.email_utils import send_sos_email, send_low_battery_email
from fastapi import BackgroundTasks

@router.post("/sos", status_code=status.HTTP_200_OK)
async def send_sos_alert(
    sos_data: SOSRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends an SOS alert with live location to all emergency contacts.
    """
    contacts = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).all()
    
    # Filter valid emails
    emails = [
        contact.email.strip() for contact in contacts 
        if contact.email and contact.email.strip() != ""
    ]
    
    if not emails:
        raise HTTPException(status_code=400, detail="No valid emergency contacts found with an email address. Please update your profile.")
    
    try:
        # Run async email sending in background
        background_tasks.add_task(
            send_sos_email, 
            emails, 
            current_user.name or "User", 
            sos_data.lat, 
            sos_data.lng,
            sos_data.location_name or ""
        )
        return {"message": "SOS alert sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue SOS alerts: {str(e)}")

@router.post("/low-battery", status_code=status.HTTP_200_OK)
async def send_low_battery_alert(
    location_data: SOSRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends a pre-emptive low battery alert with live location to all emergency contacts.
    """
    contacts = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.user_id,
        EmergencyContact.is_active == True
    ).all()
    
    # Filter valid emails
    emails = [
        contact.email.strip() for contact in contacts 
        if contact.email and contact.email.strip() != ""
    ]
    
    if not emails:
        raise HTTPException(status_code=400, detail="No valid emergency contacts found with an email address. Please update your profile.")
    
    try:
        # Run async email sending in background
        background_tasks.add_task(
            send_low_battery_email, 
            emails, 
            current_user.name or "User", 
            location_data.lat, 
            location_data.lng,
            location_data.location_name or ""
        )
        return {"message": "Low battery alert sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue low battery alerts: {str(e)}")