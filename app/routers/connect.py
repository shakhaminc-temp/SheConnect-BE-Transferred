from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Request, College
from app.schemas.schemas import ConnectionActionRequest, ShareInfoRequest

router = APIRouter(prefix="/connect", tags=["Connection & Privacy"])

@router.post("/anonymous")
def anonymous_connection(
    payload: ConnectionActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    connection = db.query(Request).filter(
        Request.request_id == payload.connection_id,
        Request.status == "accepted",
        Request.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found or not accepted")

    if connection.sent_by != current_user.user_id and connection.sent_to != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this connection")

    if connection.sent_by == current_user.user_id:
        connection.sender_privacy_mode = "ANONYMOUS"
    else:
        connection.receiver_privacy_mode = "ANONYMOUS"

    db.commit()

    return {
        "message": "Privacy mode updated to Anonymous",
        "privacyMode": "ANONYMOUS",
        "connectionId": connection.request_id
    }

@router.post("/share-info")
def share_info_connection(
    payload: ShareInfoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    connection = db.query(Request).filter(
        Request.request_id == payload.connection_id,
        Request.status == "accepted",
        Request.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found or not accepted")

    if connection.sent_by != current_user.user_id and connection.sent_to != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this connection")

    is_sender = connection.sent_by == current_user.user_id

    # Set YOUR privacy mode to LIMITED (you're choosing to share your own info)
    if is_sender:
        connection.sender_privacy_mode = "LIMITED"
    else:
        connection.receiver_privacy_mode = "LIMITED"

    db.commit()

    # Determine partner's privacy choice (what THEY previously chose to share)
    partner_id = connection.sent_to if is_sender else connection.sent_by
    partner_privacy = connection.receiver_privacy_mode if is_sender else connection.sender_privacy_mode

    response_data = {
        "message": "Privacy mode updated to Limited",
        "privacyMode": "LIMITED",
        "connectionId": connection.request_id
    }

    # Return partner's info only if THEY also chose LIMITED
    if partner_privacy == "LIMITED":
        partner = db.query(User).filter(User.user_id == partner_id).first()
        if partner:
            partner_college = db.query(College).filter(College.college_id == partner.college_id).first()
            # Partner's info is returned based on what the PARTNER chose to share (not the caller's prefs)
            response_data["sharedInfo"] = {
                "firstName": partner.name.split()[0] if partner.name else "Partner",
                "collegeName": partner_college.college_name if partner_college else "Unknown College"
            }
    else:
        response_data["sharedInfo"] = None
        response_data["notice"] = "Partner has not shared details yet."

    return response_data
