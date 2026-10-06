import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.models.user import User
from app.models.chat import Chat
from app.models.request import Request
from sqlalchemy import or_
from datetime import datetime

db = SessionLocal()
try:
    current_user = db.query(User).filter(User.user_id==9).first()
    if not current_user:
        print("No users found.")
        sys.exit(0)
    print(f"Testing for user {current_user.user_id}")
    
    chats = db.query(Chat).filter(
        or_(Chat.sender_id == current_user.user_id, Chat.receiver_id == current_user.user_id),
        Chat.is_active == True
    ).all()
    
    from app.models.carpool import CarpoolChat
    carpool_chats = db.query(CarpoolChat).filter(
        or_(CarpoolChat.sender_id == current_user.user_id, CarpoolChat.receiver_id == current_user.user_id),
        CarpoolChat.is_active == True
    ).all()

    history = {} 
    for c in chats:
        key = (c.request_id, False)
        if key not in history or (c.created_at and (not history[key].created_at or c.created_at > history[key].created_at)):
            history[key] = c
            
    for c in carpool_chats:
        key = (c.request_id, True)
        if key not in history or (c.created_at and (not history[key].created_at or c.created_at > history[key].created_at)):
            history[key] = c
            
    request_ids = [k[0] for k in history.keys() if not k[1]]
    requests = db.query(Request).filter(Request.request_id.in_(request_ids)).all() if request_ids else []
    request_map = {r.request_id: r for r in requests}
    
    partner_ids = set()
    for msg in history.values():
        partner_ids.add(msg.sender_id if msg.sender_id != current_user.user_id else msg.receiver_id)
        
    users = db.query(User).filter(User.user_id.in_(list(partner_ids))).all()
    user_map = {u.user_id: u for u in users}

    result = []
    for (req_id, is_carpool), msg in history.items():
        partner_id = msg.sender_id if msg.sender_id != current_user.user_id else msg.receiver_id
        u = user_map.get(partner_id)
        if not u:
            continue
            
        is_anonymous = False
        if not is_carpool:
            req = request_map.get(req_id)
            if req:
                if req.sent_by == partner_id:
                    is_anonymous = (req.sender_privacy_mode == 'ANONYMOUS')
                else:
                    is_anonymous = (req.receiver_privacy_mode == 'ANONYMOUS')
                    
        result.append({
            "request_id": req_id,
            "partner_id": u.user_id,
            "partner_name": None if is_anonymous else u.name,
            "partner_college": None if is_anonymous else (u.college.name if u.college else None),
            "partner_anonymous_id": u.anonymous_id,
            "is_anonymous": is_anonymous,
            "last_message": msg.message,
            "last_message_time": msg.created_at,
            "is_read": msg.is_read if msg.receiver_id == current_user.user_id else True
        })
        
    print("Result:", result)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
