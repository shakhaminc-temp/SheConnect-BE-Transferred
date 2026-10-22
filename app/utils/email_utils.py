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
        actual_lat, actual_lng = float(lat), float(lng)
        # If coordinates are swapped (e.g. Pune lat 18.51, lng 73.84 was given as lat 73.84, lng 18.51)
        if (abs(actual_lat) > 50 and abs(actual_lng) <= 50) or (abs(actual_lat) > 90 and abs(actual_lng) <= 90):
            actual_lat, actual_lng = actual_lng, actual_lat
    except (ValueError, TypeError):
        return ""

    # 1. Try OpenStreetMap Nominatim
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={actual_lat}&lon={actual_lng}&zoom=18&addressdetails=1"
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "SheConnectApp/1.0 (Emergency Alert System; support@sheconnect.app)"}
            response = await client.get(url, headers=headers, timeout=6.0)
            if response.status_code == 200:
                data = response.json()
                display_name = data.get("display_name", "").strip()
                if display_name:
                    return display_name
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed: {e}")

    # 2. Fallback to BigDataCloud client reverse API
    try:
        bdc_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={actual_lat}&longitude={actual_lng}&localityLanguage=en"
        async with httpx.AsyncClient() as client:
            response = await client.get(bdc_url, timeout=6.0)
            if response.status_code == 200:
                data = response.json()
                parts = [
                    data.get("locality"),
                    data.get("city"),
                    data.get("principalSubdivision"),
                    data.get("countryName")
                ]
                clean = [p for p in parts if p]
                if clean:
                    return ", ".join(clean)
    except Exception as e:
        logger.warning(f"BigDataCloud geocoding failed: {e}")

    # 3. Fallback to Photon by Komoot reverse
    try:
        photon_url = f"https://photon.komoot.io/reverse?lat={actual_lat}&lon={actual_lng}"
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "SheConnectApp/1.0"}
            response = await client.get(photon_url, headers=headers, timeout=6.0)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    parts = [
                        props.get("name"),
                        props.get("street"),
                        props.get("district"),
                        props.get("city"),
                        props.get("state"),
                        props.get("country")
                    ]
                    clean_parts = [p for p in parts if p]
                    if clean_parts:
                        return ", ".join(clean_parts)
    except Exception as e:
        logger.warning(f"Photon reverse geocoding failed: {e}")

    return ""

async def send_sos_email(emails: list[str], user_name: str, lat: float, lng: float, location_name: str = ""):
    if not emails:
        logger.warning("send_sos_email called with empty emails list")
        return
        
    try:
        actual_lat = float(lat)
        actual_lng = float(lng)
        # In India / standard coords: lat is ~8 to ~37, lng is ~68 to ~98.
        # If lat > 60 and lng < 40, they are inverted (lng was put as lat).
        if (abs(actual_lat) > 50 and abs(actual_lng) <= 50) or (abs(actual_lat) > 90 and abs(actual_lng) <= 90):
            actual_lat, actual_lng = actual_lng, actual_lat

        # If location_name is empty or was previously resolved to Norway / ocean, re-resolve with corrected coords
        if not location_name or "Norway" in location_name or "Ocean" in location_name or location_name == "Unknown Location":
            location_name = await get_location_name(actual_lat, actual_lng)
            
        html_body = get_sos_email_html(user_name, actual_lat, actual_lng, location_name)
        message = MessageSchema(
            subject=f"🚨 SOS ALERT: {user_name} needs immediate help!",
            recipients=emails,
            body=html_body,
            subtype="html"
        )
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"SOS email successfully sent to {emails}")
    except Exception as e:
        logger.error(f"Failed to send SOS email to {emails}: {e}")


def load_allowed_emails(file_path="app/scripts/female_emails.csv"):
    allowed = set()

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return allowed

    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        reader.fieldnames = fieldnames
        if "email" not in fieldnames:
            logger.warning(f"CSV header must have 'email'. Found: {fieldnames}")
            return allowed

        for row in reader:
            val = (row.get("email") or "").strip().lower()
            if val:
                allowed.add(val)

    return allowed


def load_colleges_from_csv(file_path="app/scripts/female_emails.csv"):
    colleges = set()

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return colleges

    with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        reader.fieldnames = fieldnames

        college_col = None
        for col in ["college_name", "college", "colleges"]:
            if col in fieldnames:
                college_col = col
                break

        if not college_col:
            logger.warning(f"No college column found in CSV. Found: {fieldnames}")
            return colleges

        for row in reader:
            val = (row.get(college_col) or "").strip()
            if val:
                colleges.add(val)

    return colleges


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
