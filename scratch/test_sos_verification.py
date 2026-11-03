import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()
import asyncio
import re
from app.utils.email_utils import normalize_lat_lng, get_location_name
from app.utils.email_templates import get_sos_email_html

print("==================================================")
print(" 1. TESTING COORDINATE NORMALIZATION")
print("==================================================")
test_cases = [
    ("Normal Pune coords", 18.515893, 73.841160),
    ("Inverted Pune coords (previous bug)", 73.841160, 18.515893),
    ("Normal Mumbai coords", 19.0760, 72.8777),
    ("Inverted Mumbai coords", 72.8777, 19.0760),
    ("Normal Delhi coords", 28.6139, 77.2090),
    ("Inverted Delhi coords", 77.2090, 28.6139),
]

for label, lat, lng in test_cases:
    norm_lat, norm_lng = normalize_lat_lng(lat, lng)
    print(f"[{label}]\n  Input:  Lat={lat}, Lng={lng}\n  Output: Lat={norm_lat:.6f}, Lng={norm_lng:.6f}\n")

async def test_resolve():
    print("==================================================")
    print(" 2. TESTING REVERSE GEOCODING ON PREVIOUSLY FAILING COORDS")
    print("==================================================")
    # Even if bad inverted coords are passed:
    bad_lat, bad_lng = 73.841160, 18.515893
    print(f"Sending inverted coords ({bad_lat}, {bad_lng})...")
    loc = await get_location_name(bad_lat, bad_lng)
    print(f"-> Resolved Real Address:\n   {loc}")

    print("\n==================================================")
    print(" 3. TESTING EMAIL HTML GENERATION")
    print("==================================================")
    html = get_sos_email_html("Sanika Vibhute", bad_lat, bad_lng, loc)
    maps_links = re.findall(r'href="([^"]+)"', html)
    for link in maps_links:
        print(f"-> Link in Email: {link}")

asyncio.run(test_resolve())
