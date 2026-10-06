from fastapi import APIRouter, Query, HTTPException
import httpx
import logging

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
    
    # Photon does not strictly require the User-Agent, but it's good practice
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
        
        # Build a readable label (e.g. "Pune, Maharashtra, India")
        name = props.get("name", "")
        state = props.get("state", "")
        country = props.get("country", "")
        
        # Filter out empty strings and join with commas
        label_parts = [part for part in [name, state, country] if part]
        label = ", ".join(label_parts) if label_parts else "Unknown Location"
        
        coords = geometry.get("coordinates", [])
        if len(coords) >= 2:
            lng, lat = coords[0], coords[1]
            results.append({
                "place_id": props.get("osm_id"),
                "label": label,
                "lat": float(lat),
                "lng": float(lng),
                "confidence": 0.9 
            })
            
    return {"results": results}

