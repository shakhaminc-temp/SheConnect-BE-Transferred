import math

# Major Indian Metropolitan Regions with Active Metro Rail Lines
METRO_CORRIDORS = [
    # Pune Metro (PCMC to Swargate, Vanaz to Ramwadi, Deccan, Kothrud, Hinjewadi)
    {"name": "Pune Metro", "lat": 18.5204, "lng": 73.8567, "radius_km": 30.0},
    # Mumbai Metro & MMRDA (Andheri, Ghatkopar, Dahisar, BKC, Navi Mumbai Metro)
    {"name": "Mumbai Metro", "lat": 19.0760, "lng": 72.8777, "radius_km": 45.0},
    # Delhi-NCR Metro (DMRC, Noida Aqua Line, Gurgaon Rapid Metro)
    {"name": "Delhi NCR Metro", "lat": 28.6139, "lng": 77.2090, "radius_km": 55.0},
    # Bengaluru Namma Metro (Purple, Green Line)
    {"name": "Namma Metro Bengaluru", "lat": 12.9716, "lng": 77.5946, "radius_km": 35.0},
    # Hyderabad Metro (Red, Blue, Green Line)
    {"name": "Hyderabad Metro", "lat": 17.3850, "lng": 78.4867, "radius_km": 30.0},
    # Chennai Metro (Blue, Green Line)
    {"name": "Chennai Metro", "lat": 13.0827, "lng": 80.2707, "radius_km": 30.0},
    # Kolkata Metro (East-West Underwater, North-South, Purple)
    {"name": "Kolkata Metro", "lat": 22.5726, "lng": 88.3639, "radius_km": 30.0},
    # Ahmedabad / Gandhinagar Metro
    {"name": "Ahmedabad Metro", "lat": 23.0225, "lng": 72.5714, "radius_km": 25.0},
    # Nagpur Metro (Maha Metro)
    {"name": "Nagpur Metro", "lat": 21.1458, "lng": 79.0882, "radius_km": 20.0},
    # Jaipur Metro
    {"name": "Jaipur Metro", "lat": 26.9124, "lng": 75.7873, "radius_km": 20.0},
    # Kochi Metro
    {"name": "Kochi Metro", "lat": 9.9312, "lng": 76.2673, "radius_km": 25.0},
    # Lucknow Metro
    {"name": "Lucknow Metro", "lat": 26.8467, "lng": 80.9462, "radius_km": 20.0},
    # Kanpur Metro
    {"name": "Kanpur Metro", "lat": 26.4499, "lng": 80.3319, "radius_km": 18.0}
]

# Major Urban Agglomerations with App-based Cabs (Uber, Ola, Rapido)
CAB_CORRIDORS = [
    {"name": "Pune & PCMC", "lat": 18.5204, "lng": 73.8567, "radius_km": 40.0},
    {"name": "Mumbai Metropolitan Region", "lat": 19.0760, "lng": 72.8777, "radius_km": 60.0},
    {"name": "Delhi NCR", "lat": 28.6139, "lng": 77.2090, "radius_km": 70.0},
    {"name": "Bengaluru Urban", "lat": 12.9716, "lng": 77.5946, "radius_km": 45.0},
    {"name": "Hyderabad Urban", "lat": 17.3850, "lng": 78.4867, "radius_km": 40.0},
    {"name": "Chennai Urban", "lat": 13.0827, "lng": 80.2707, "radius_km": 40.0},
    {"name": "Kolkata Urban", "lat": 22.5726, "lng": 88.3639, "radius_km": 40.0},
    {"name": "Ahmedabad-Gandhinagar", "lat": 23.0225, "lng": 72.5714, "radius_km": 35.0},
    {"name": "Nashik", "lat": 19.9975, "lng": 73.7898, "radius_km": 25.0},
    {"name": "Chhatrapati Sambhajinagar (Aurangabad)", "lat": 19.8762, "lng": 75.3433, "radius_km": 25.0},
    {"name": "Nagpur", "lat": 21.1458, "lng": 79.0882, "radius_km": 25.0},
    {"name": "Indore", "lat": 22.7196, "lng": 75.8577, "radius_km": 25.0},
    {"name": "Jaipur", "lat": 26.9124, "lng": 75.7873, "radius_km": 25.0},
    {"name": "Chandigarh Tri-city", "lat": 30.7333, "lng": 76.7794, "radius_km": 30.0}
]

# Keywords that indicate Pune, Mumbai, or other metro localities even if city name isn't typed
LOCALITY_METRO_KEYWORDS = {
    # Pune Metro local station/neighborhood keywords
    "deccan", "kothrud", "karve", "shivajinagar", "swargate", "vanaz", "ramwadi",
    "yerawada", "kalyani nagar", "bund garden", "mangwar peth", "civil court",
    "pcmc", "bhosari", "kasarwadi", "dapodi", "bopodi", "khadki", "hinjewadi",
    "kharadi", "viman nagar", "aundh", "baner", "wakad", "hadapsar", "katraj",
    # Mumbai Metro local station/neighborhood keywords
    "andheri", "ghatkopar", "versova", "borivali", "kandivali", "malad", "goregaon",
    "jogeshwari", "bandra", "dadar", "kurla", "chembur", "bkc", "vashi", "nerul",
    "belapur", "kharghar", "panvel", "colaba", "cst", "lower parel",
    # General Metro/Train Keywords
    "metro", "railway", "station", "junction", "terminal"
}

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geodesic distance in kilometers between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def is_within_metro_corridor(lat: float, lng: float, text: str) -> bool:
    """Checks if coordinates or location text fall inside a live metro corridor."""
    t = text.lower()
    if any(kw in t for kw in LOCALITY_METRO_KEYWORDS):
        return True

    if lat and lng:
        try:
            for corridor in METRO_CORRIDORS:
                dist = calculate_haversine_distance(float(lat), float(lng), corridor["lat"], corridor["lng"])
                if dist <= corridor["radius_km"]:
                    return True
        except (ValueError, TypeError):
            pass
    return False


def is_within_cab_corridor(lat: float, lng: float, text: str) -> bool:
    """Checks if coordinates or location text fall inside an app-cab serviceable city."""
    t = text.lower()
    if any(kw in t for kw in LOCALITY_METRO_KEYWORDS):
        return True

    if lat and lng:
        try:
            for corridor in CAB_CORRIDORS:
                dist = calculate_haversine_distance(float(lat), float(lng), corridor["lat"], corridor["lng"])
                if dist <= corridor["radius_km"]:
                    return True
        except (ValueError, TypeError):
            pass
    return False


def detect_available_transit(
    location_name: str,
    dest_name: str = "",
    lat: float = None,
    lng: float = None,
    dest_lat: float = None,
    dest_lng: float = None
) -> dict:
    """
    Intelligently determines active transportation modes available at the given location.
    Combines Geofencing (GPS coordinates) + Suburb/Locality intelligence so that:
    1. Deccan Gymkhana to Karve Nagar accurately surfaces Pune Metro, Two-Wheeler, Car, Bus, Auto, Cab.
    2. Mumbai to Pune accurately surfaces Railway / Express Train, Carpool, Bus, Cabs.
    """
    full_text = f"{location_name} {dest_name}".lower()

    # Calculate trip distance
    distance_km = 0.0
    if lat and lng and dest_lat and dest_lng:
        try:
            distance_km = calculate_haversine_distance(float(lat), float(lng), float(dest_lat), float(dest_lng))
        except (ValueError, TypeError):
            distance_km = 0.0

    # 1. Base Universal Modes (Available everywhere for female commuters)
    modes = [
        {
            "id": "two-wheeler",
            "name": "Two-Wheeler / Scooter / Bike",
            "badge": "Bike Pool",
            "icon": "Bike",
            "description": "Female commuter scooter or bike sharing"
        },
        {
            "id": "car",
            "name": "Personal Car / Carpool",
            "badge": "Shared Ride",
            "icon": "Car",
            "description": "Travel together in a verified personal car"
        },
        {
            "id": "bus",
            "name": "Public / State Bus",
            "badge": "Transit",
            "icon": "Bus",
            "description": "City buses & MSRTC / State transport routes"
        },
        {
            "id": "auto-rickshaw",
            "name": "Auto Rickshaw",
            "badge": "First/Last Mile",
            "icon": "Auto",
            "description": "Shared or meter auto rickshaw"
        }
    ]

    # 2. App-Based Ride Hailing (Uber / Ola / Rapido)
    has_app_cabs = is_within_cab_corridor(lat, lng, full_text)
    if has_app_cabs:
        modes.append({
            "id": "uber/cab",
            "name": "Uber / Ola / App Cab",
            "badge": "On-Demand",
            "icon": "Cab",
            "description": "App-based private or shared taxi"
        })

    # 3. Metro Rail Transit
    has_metro = is_within_metro_corridor(lat, lng, full_text)
    if has_metro:
        modes.append({
            "id": "metro",
            "name": "Metro Rail",
            "badge": "High-Speed Rail",
            "icon": "Metro",
            "description": "Urban rapid transit metro line"
        })

# Railway mode removed as requested - not needed for commuter trips

    # Region label display
    detected_city = "Local Region"
    if "pune" in full_text or any(kw in full_text for kw in ["deccan", "kothrud", "karve", "pcmc", "hinjewadi", "hadapsar"]):
        detected_city = "Pune Metropolitan"
    elif "mumbai" in full_text or any(kw in full_text for kw in ["andheri", "dadar", "bandra", "borivali", "thane", "vashi"]):
        detected_city = "Mumbai Metropolitan"
    elif "delhi" in full_text or "noida" in full_text or "gurgaon" in full_text:
        detected_city = "Delhi-NCR"
    elif "bengaluru" in full_text or "bangalore" in full_text:
        detected_city = "Bengaluru Urban"

    return {
        "location": location_name,
        "destination": dest_name,
        "detected_city": detected_city,
        "distance_km": distance_km,
        "has_metro": has_metro,
        "has_app_cabs": has_app_cabs,
        "available_modes": modes
    }
