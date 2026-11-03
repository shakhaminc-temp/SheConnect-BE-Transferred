from fastapi import APIRouter, Query, HTTPException
import httpx
import logging
from typing import Optional
from app.utils.transit_detector import detect_available_transit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geo", tags=["Geo"])

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=3)):
    # Photon by Komoot is built on OpenStreetMap and supports type-ahead
    url = "https://photon.komoot.io/api/"
    params = {
        "q": q,
        "limit": 5,
        "lang": "en"
    }
    
    headers = {"User-Agent": "SheConnect-Backend/1.0 (vedantgirjapure41@gmail.com)"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Photon geocoding error: {e}")
            raise HTTPException(status_code=503, detail="Geocoding service unavailable")

    features = data.get("features", [])
    if not features:
        return {"results": []}

    results = []
    for item in features:
        props = item.get("properties", {})
        geometry = item.get("geometry", {})
        
        name = props.get("name", "")
        city = props.get("city") or props.get("district") or props.get("county") or ""
        state = props.get("state", "")
        country = props.get("country", "")
        
        label_parts = [part for part in [name, city, state, country] if part]
        label = ", ".join(label_parts) if label_parts else "Unknown Location"
        
        coords = geometry.get("coordinates", [])
        if len(coords) >= 2:
            lng, lat = coords[0], coords[1]
            results.append({
                "place_id": props.get("osm_id"),
                "label": label,
                "city": city,
                "lat": float(lat),
                "lng": float(lng),
                "confidence": 0.9 
            })
            
    return {"results": results}

@router.get("/available-transit")
def get_available_transit(
    location: str = Query(..., description="Starting pickup location or city"),
    dest_location: Optional[str] = Query("", description="Destination location or city"),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    dest_lat: Optional[float] = Query(None),
    dest_lng: Optional[float] = Query(None)
):
    """
    Intelligently determines real-time transit options physically available at the given location.
    Prevents stranded travelers from waiting for non-existent modes (e.g. Metro in tier-3 towns).
    """
    return detect_available_transit(
        location_name=location,
        dest_name=dest_location,
        lat=lat,
        lng=lng,
        dest_lat=dest_lat,
        dest_lng=dest_lng
    )
