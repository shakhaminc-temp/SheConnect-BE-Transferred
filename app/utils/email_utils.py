from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import csv
import os
import logging

logger = logging.getLogger(__name__)

from app.utils.email_templates import get_otp_email_html, get_sos_email_html, get_low_battery_email_html

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email: str, otp: str):
    html_body = get_otp_email_html(otp)

    message = MessageSchema(
        subject="Your OTP for SheConnect",
        recipients=[email],
        cc=["vedantgirjapure41@gmail.com"],
        body=html_body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

import httpx

async def get_location_name(lat: float, lng: float) -> str:
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}"
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "SheConnectApp/1.0 (Emergency Alert System)"}
            response = await client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", "")
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
    return ""

async def send_sos_email(emails: list[str], user_name: str, lat: float, lng: float, location_name: str = ""):
    if not emails:
        return
        
    if not location_name:
        location_name = await get_location_name(lat, lng)
        
    html_body = get_sos_email_html(user_name, lat, lng, location_name)
    message = MessageSchema(
        subject=f"SOS ALERT: {user_name} needs immediate help!",
        recipients=emails,
        body=html_body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


def load_allowed_emails(file_path="app/scripts/female_emails.csv"):
    allowed = set()

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return allowed

    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        if "email" not in reader.fieldnames:
            logger.warning(f"CSV header must have 'email'. Found: {reader.fieldnames}")
            return allowed

        for row in reader:
            allowed.add(row["email"].strip().lower())

    return allowed

async def send_low_battery_email(emails: list[str], user_name: str, lat: float, lng: float, location_name: str = ""):
    if not emails:
        return
        
    if not location_name:
        location_name = await get_location_name(lat, lng)
        
    html_body = get_low_battery_email_html(user_name, lat, lng, location_name)
    message = MessageSchema(
        subject=f"⚠️ LOW BATTERY ALERT: {user_name}'s phone is dying!",
        recipients=emails,
        body=html_body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
