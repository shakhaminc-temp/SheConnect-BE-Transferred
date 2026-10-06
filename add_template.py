with open('app/utils/email_templates.py', 'a', encoding='utf-8') as f:
    f.write('''
def get_low_battery_email_html(user_name: str, lat: float, lng: float, location_name: str = "") -> str:
    maps_url = f"https://www.google.com/maps?q={lat},{lng}"
    location_display = f"<div style='font-size: 18px; font-weight: bold; color: #111827; margin-bottom: 10px;'>{location_name}</div>" if location_name and location_name != "Unknown Location" else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f9fafb; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; border-top: 5px solid #f59e0b; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h1 style="color: #f59e0b; margin-top: 0;">⚠️ LOW BATTERY ALERT</h1>
            <p style="font-size: 16px; color: #374151;">
                <strong>{user_name}</strong>'s phone battery is extremely low (below 5%) and may die soon.
            </p>
            <p style="font-size: 16px; color: #374151;">
                We are sending you this pre-emptive alert so you know their final known location before they potentially go offline.
            </p>
            <p style="font-size: 16px; color: #374151; margin-top: 20px;">
                Their last known location was:
            </p>
            {location_display}
            <p style="font-size: 14px; color: #6b7280; margin-top: 0;">
                Coordinates: {lat}, {lng}
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{maps_url}" style="background-color: #f59e0b; color: white; padding: 15px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 18px; display: inline-block;">
                    View Last Location on Google Maps
                </a>
            </div>
            <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
                This is an automated safety alert. If you cannot reach them soon, do not panic immediately, as their phone may have simply powered off.
            </p>
        </div>
    </body>
    </html>
    """
''')
