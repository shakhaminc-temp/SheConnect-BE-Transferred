def get_otp_email_html(otp: str) -> str:
    """
    Returns a beautifully formatted HTML email string for OTP verification.
    Features a responsive design with a clean, professional pink theme.
    """
    
    brand_color = "#E91E63"  # A vibrant, professional pink
    bg_color = "#f9fafb"
    container_bg = "#ffffff"
    text_color = "#374151"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your OTP Code</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: {bg_color};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: {text_color};
                line-height: 1.6;
            }}
            .email-wrapper {{
                width: 100%;
                background-color: {bg_color};
                padding: 40px 20px;
                box-sizing: border-box;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: {container_bg};
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }}
            .header {{
                background-color: {brand_color};
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            .content {{
                padding: 40px 30px;
                text-align: center;
            }}
            .content h2 {{
                color: #111827;
                font-size: 22px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .content p {{
                font-size: 16px;
                margin-bottom: 30px;
                color: {text_color};
            }}
            .otp-box {{
                background-color: #fce4ec;
                border: 2px dashed {brand_color};
                border-radius: 12px;
                padding: 25px 20px;
                margin: 0 auto 10px auto;
                max-width: 300px;
                /* Enables easy single-click/long-press selection in supported mail clients */
                user-select: all;
                -webkit-user-select: all;
                cursor: pointer;
            }}
            .otp-code {{
                font-size: 42px;
                font-weight: 700;
                color: {brand_color};
                letter-spacing: 12px;
                margin: 0;
                padding-left: 12px; /* balances out the letter-spacing offset on the last digit */
            }}
            .copy-hint {{
                font-size: 13px;
                color: #9ca3af;
                margin-top: 0;
                margin-bottom: 30px;
                font-style: italic;
            }}
            .footer {{
                background-color: #f3f4f6;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                font-size: 13px;
                color: #6b7280;
                margin: 0;
            }}
            .disclaimer {{
                margin-top: 10px;
                font-size: 12px;
                color: #9ca3af;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="email-container">
                <!-- Header -->
                <div class="header">
                    <h1>SheConnect</h1>
                </div>
                
                <!-- Content -->
                <div class="content">
                    <h2>Verify your email address</h2>
                    <p>Thank you for signing up for SheConnect! Please use the following One-Time Password (OTP) to complete your registration process.</p>
                    
                    <div class="otp-box" title="Double-click to select all">
                        <p class="otp-code">{otp}</p>
                    </div>
                    <p class="copy-hint">Double-click or long-press the code above to easily copy it.</p>
                    
                    <p>This code is only valid for a short period of time.<br>If you did not attempt to sign up, please ignore this email.</p>
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <p>Need help? Contact our support team.</p>
                    <p class="disclaimer">&copy; 2024 SheConnect. All rights reserved.<br>This is an automated message, please do not reply.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def get_sos_email_html(user_name: str, lat: float, lng: float, location_name: str = "") -> str:
    maps_url = f"https://www.google.com/maps?q={lat},{lng}"
    clean_location = location_name.strip() if location_name and location_name.strip() != "Unknown Location" else "Location coordinates available below"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; padding: 24px; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 16px; border-top: 6px solid #dc2626; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="background-color: #fee2e2; color: #dc2626; font-size: 14px; font-weight: 800; padding: 6px 14px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.1em; display: inline-block;">
                    🚨 Emergency SOS Alert
                </span>
                <h1 style="color: #111827; font-size: 24px; font-weight: 900; margin-top: 14px; margin-bottom: 8px;">
                    {user_name} Needs Immediate Help!
                </h1>
                <p style="font-size: 15px; color: #4b5563; margin: 0;">
                    This is an automated SOS emergency notification sent to you as a designated emergency contact.
                </p>
            </div>

            <!-- Prominent Location Card -->
            <div style="background-color: #fef2f2; border: 1.5px solid #fecaca; border-radius: 14px; padding: 20px; margin: 24px 0;">
                <div style="font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.15em; color: #991b1b; margin-bottom: 8px;">
                    📍 Current Location / Address
                </div>
                <div style="font-size: 17px; font-weight: 800; color: #1f2937; line-height: 1.5; margin-bottom: 12px;">
                    {clean_location}
                </div>
                <div style="font-size: 13px; color: #6b7280; font-family: monospace;">
                    <strong>GPS Coordinates:</strong> {lat}, {lng}
                </div>
            </div>

            <!-- View on Map Button -->
            <div style="text-align: center; margin: 28px 0;">
                <a href="{maps_url}" style="background-color: #dc2626; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 12px; font-weight: 800; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(220,38,38,0.4);">
                    🗺️ Open Live Location on Google Maps
                </a>
            </div>

            <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 28px; text-align: center;">
                <p style="font-size: 13px; color: #4b5563; line-height: 1.6; margin: 0 0 10px 0;">
                    <strong>Recommended Actions:</strong><br>
                    1. Call <strong>{user_name}</strong> immediately.<br>
                    2. Check the live map above for their real-time location.<br>
                    3. If unreachable, alert local police or emergency rescue services immediately.
                </p>
                <p style="font-size: 11px; color: #9ca3af; margin: 0;">
                    SheConnect Safety & Emergency Response System
                </p>
            </div>
        </div>
    </body>
    </html>
    """

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
