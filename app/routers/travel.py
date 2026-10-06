from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Travel, User, TravelRoute, Request
from app.models.chat import Chat
from app.schemas.schemas import TravelCreate, TravelResponse, TripRequestCreate, RequestUpdate, RequestResponse
from geoalchemy2 import Geography
from sqlalchemy import func, desc, text, or_
import httpx
from datetime import datetime, timezone, timedelta
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/travel", tags=["Travel"])

def _serialize_trip(travel: Travel, db: Session) -> dict:
    """Helper to extract lat/lng from PostGIS points and return a TravelResponse-compatible dict."""
    row = db.execute(
        text(
            "SELECT ST_Y(start_point::geometry), ST_X(start_point::geometry), "
            "ST_Y(end_point::geometry), ST_X(end_point::geometry) "
            "FROM travels WHERE travel_id = :id"
        ),
        {"id": travel.travel_id}
    ).fetchone()

    start_lat, start_lng, end_lat, end_lng = (row if row else (None, None, None, None))

    return {
        "travel_id": travel.travel_id,
        "start_label": travel.start_label,
        "end_label": travel.end_label,
        "start_lat": start_lat,
        "start_lng": start_lng,
        "end_lat": end_lat,
        "end_lng": end_lng,
        "travel_date": travel.travel_date,
        "mode_of_transport": travel.mode_of_transport,
        "time_flex_minutes": travel.time_flex_minutes,
        "status": travel.status,
        "created_at": travel.created_at,
    }


@router.get("/trips", response_model=List[TravelResponse])  # Returns all trips created by the logged-in user.
def get_my_trips(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Travel).filter(Travel.user_id == current_user.user_id)
    if active_only:
        query = query.filter(Travel.is_active == True)
    trips = query.order_by(desc(Travel.created_at)).offset(offset).limit(limit).all()
    return [_serialize_trip(t, db) for t in trips]


@router.post("/trips")  # Creates a new trip.
async def create_trip(
    travel: TravelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    start_time = travel.start_time
    # If the provided time is naive, assume it's in UTC for comparison.
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if start_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Trip start time cannot be in the past.")
    
    if start_time > datetime.now(timezone.utc) + timedelta(days=60):
        raise HTTPException(status_code=400, detail="Trip cannot be scheduled more than 60 days in advance.")

    if not (0 <= travel.time_flex_minutes <= 120):
        raise HTTPException(status_code=400, detail="Time flexibility must be between 0 and 120 minutes.")

    if not (-90 <= travel.start.lat <= 90) or not (-180 <= travel.start.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid start coordinates")
    
    if not (-90 <= travel.end.lat <= 90) or not (-180 <= travel.end.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid end coordinates")

    if travel.start.lat == travel.end.lat and travel.start.lng == travel.end.lng:
        raise HTTPException(status_code=400, detail="Start and end points cannot be identical")

    new_travel = Travel(
        user_id=current_user.user_id,
        start_label=travel.start.label,
        end_label=travel.end.label,
        start_point=func.ST_SetSRID(func.ST_MakePoint(travel.start.lng, travel.start.lat), 4326),
        end_point=func.ST_SetSRID(func.ST_MakePoint(travel.end.lng, travel.end.lat), 4326),
        travel_date=travel.start_time,
        mode_of_transport=travel.transport_mode.value,
        time_flex_minutes=travel.time_flex_minutes,
        vehicle_no=travel.vehicle_no,
        status="SEARCHING"
    )

    db.add(new_travel)
    db.flush()  # Sends INSERT to DB within current transaction so travel_id is assigned

    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{travel.start.lng},{travel.start.lat};{travel.end.lng},{travel.end.lat}?overview=full&geometries=geojson"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(osrm_url)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            if response.status_code == 200:
                data = response.json()
                if not data.get("routes"):
                    raise ValueError("No route found between the specified points.")

                route_data = data["routes"][0]
                geometry_json = json.dumps(route_data["geometry"])
                
                new_route = TravelRoute(
                    travel_id=new_travel.travel_id,
                    route_geom=func.ST_SetSRID(func.ST_GeomFromGeoJSON(geometry_json), 4326),
                    distance_meters=route_data["distance"],
                    duration_seconds=route_data["duration"]
                )
                db.add(new_route)
                db.commit()  # Atomically commits both the trip and its route
                db.refresh(new_travel)
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
        db.rollback()
        logger.error(f"OSRM/Route error [{type(e).__name__}]: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not generate a valid route for the given locations. Error: [{type(e).__name__}] {e}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected trip creation error [{type(e).__name__}]: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred during trip creation. [{type(e).__name__}]: {e}"
        )

    return {"message": "Trip created successfully", "trip_id": new_travel.travel_id}


@router.get("/trips/{trip_id}", response_model=TravelResponse)  # Returns a single trip's full details.
def get_trip_detail(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    trip = db.query(Travel).filter(
        Travel.travel_id == trip_id,
        Travel.user_id == current_user.user_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return _serialize_trip(trip, db)


@router.get("/trips/{trip_id}/route")  # Returns the stored OSRM route as GeoJSON for MapLibre to paint.
def get_trip_route(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify the trip belongs to the current user
    trip = db.query(Travel).filter(
        Travel.travel_id == trip_id,
        Travel.user_id == current_user.user_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    route = db.query(TravelRoute).filter(TravelRoute.travel_id == trip_id).first()

    if not route:
        raise HTTPException(status_code=404, detail="No route has been generated for this trip yet")

    # Convert PostGIS geometry back to GeoJSON using ST_AsGeoJSON
    geojson_str = db.execute(
        text("SELECT ST_AsGeoJSON(route_geom) FROM travel_routes WHERE travel_id = :id"),
        {"id": trip_id}
    ).scalar()

    if not geojson_str:
        raise HTTPException(status_code=404, detail="Route geometry is unavailable")

    # Return as a GeoJSON Feature — the exact shape MapLibre expects for addSource/addLayer
    return {
        "type": "Feature",
        "geometry": json.loads(geojson_str),
        "properties": {
            "trip_id": trip_id,
            "distance_meters": route.distance_meters,
            "duration_seconds": route.duration_seconds
        }
    }


@router.get("/trips/{trip_id}/matches")  # Finds matching trips for a given trip.
def get_trip_matches(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    my_trip = db.query(Travel).filter(
        Travel.travel_id == trip_id,
        Travel.user_id == current_user.user_id,
        Travel.is_active == True
    ).first()

    if not my_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    my_route = db.query(TravelRoute).filter(TravelRoute.travel_id == trip_id).first()
    
    if not my_route:
        return {"matches_found": 0, "matches": [], "message": "Route not generated for this trip yet"}

    # Calculate the current user's travel time window
    my_trip_earliest = my_trip.travel_date - timedelta(minutes=my_trip.time_flex_minutes)
    my_trip_latest = my_trip.travel_date + timedelta(minutes=my_trip.time_flex_minutes)

    # Fetch my_trip's raw coordinates from DB (needed to build proper SQL geography literals)
    coords = db.execute(
        text(
            "SELECT ST_Y(start_point::geometry), ST_X(start_point::geometry), "
            "ST_Y(end_point::geometry), ST_X(end_point::geometry) "
            "FROM travels WHERE travel_id = :id"
        ),
        {"id": trip_id}
    ).fetchone()

    if not coords:
        return {"matches_found": 0, "matches": [], "message": "Could not retrieve trip coordinates"}

    my_start_lat, my_start_lng, my_end_lat, my_end_lng = coords

    # Build proper SQL geography points for my_trip
    my_start_geo = func.ST_SetSRID(func.ST_MakePoint(my_start_lng, my_start_lat), 4326).cast(Geography(geometry_type='POINT', srid=4326))
    my_end_geo   = func.ST_SetSRID(func.ST_MakePoint(my_end_lng,   my_end_lat),   4326).cast(Geography(geometry_type='POINT', srid=4326))

    # Cast Geography→Geometry for ST_Intersection/ST_Length (PostGIS requirement)
    other_geom = func.ST_GeomFromWKB(func.ST_AsBinary(TravelRoute.route_geom))
    my_geom    = func.ST_GeomFromWKB(func.ST_AsBinary(my_route.route_geom))

    overlap_ratio  = (func.ST_Length(func.ST_Intersection(other_geom, my_geom)) / func.ST_Length(my_geom)).label("overlap_score")
    start_distance = func.ST_Distance(Travel.start_point, my_start_geo).label("start_dist")
    end_distance   = func.ST_Distance(Travel.end_point,   my_end_geo).label("end_dist")

    results = db.query(Travel, User, overlap_ratio, start_distance, end_distance).join(
        TravelRoute, Travel.travel_id == TravelRoute.travel_id
    ).join(
        User, Travel.user_id == User.user_id
    ).filter(
        Travel.user_id != my_trip.user_id,
        Travel.status == "SEARCHING",
        Travel.is_active == True,
        # Spatial Filter: Start and End within 2km (2000 meters)
        func.ST_DWithin(Travel.start_point, my_start_geo, 2000),
        func.ST_DWithin(Travel.end_point,   my_end_geo,   2000),
        # Time Window Overlap Filter
        my_trip_earliest <= (Travel.travel_date + func.make_interval(0, 0, 0, 0, 0, Travel.time_flex_minutes, 0)),
        (Travel.travel_date - func.make_interval(0, 0, 0, 0, 0, Travel.time_flex_minutes, 0)) <= my_trip_latest
    ).order_by(desc("overlap_score")).limit(10).all()

    return {
        "matches_found": len(results),
        "matches": [
            {
                "match_id": str(travel.travel_id),
                "anonymous_id": user.anonymous_id,
                "start_location": travel.start_label,
                "end_location": travel.end_label,
                "mode_of_transport": travel.mode_of_transport,
                "rating": round(4.0 + (user.user_id % 10) / 10.0, 1),
                "route_overlap": round(overlap, 2) if overlap else 0,
                "start_distance_m": round(start_dist, 2) if start_dist else 0,
                "end_distance_m": round(end_dist, 2) if end_dist else 0
            }
            for travel, user, overlap, start_dist, end_dist in results
        ]
    }


@router.post("/request", response_model=RequestResponse)  # Sends a travel request to another user.
def send_trip_request(
    request_data: TripRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate sender's trip
    sender_trip = db.query(Travel).filter(
        Travel.travel_id == request_data.sender_trip_id,
        Travel.user_id == current_user.user_id,
        Travel.is_active == True,
        Travel.status == "SEARCHING"
    ).first()
    if not sender_trip:
        raise HTTPException(status_code=404, detail="Your trip was not found, is not active, or you are not the owner.")

    # Validate receiver's trip
    target_trip = db.query(Travel).filter(
        Travel.travel_id == request_data.receiver_trip_id,
        Travel.is_active == True,
        Travel.status == "SEARCHING"
    ).first()
    if not target_trip:
        raise HTTPException(status_code=404, detail="The requested trip is not available for matching.")

    if target_trip.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    # Check for existing pending requests between these two trips (in either direction)
    existing_request = db.query(Request).filter(
        or_(
            (Request.sender_travel_id == request_data.sender_trip_id) & (Request.receiver_travel_id == request_data.receiver_trip_id),
            (Request.sender_travel_id == request_data.receiver_trip_id) & (Request.receiver_travel_id == request_data.sender_trip_id)
        ),
        Request.status == "pending",
        Request.is_active == True
    ).first()

    if existing_request:
        raise HTTPException(status_code=400, detail="A request between these two trips is already pending.")

    new_request = Request(
        sender_travel_id=request_data.sender_trip_id,
        receiver_travel_id=request_data.receiver_trip_id,
        sent_by=current_user.user_id,
        sent_to=target_trip.user_id,
        status="pending",
        sender_privacy_mode=request_data.privacy_mode.upper() if request_data.privacy_mode else "ANONYMOUS"
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request


@router.get("/requests", response_model=dict[str, List[RequestResponse]])  # Requests you received / Requests you sent
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import joinedload
    
    base_query = db.query(Request).options(
        joinedload(Request.sender).joinedload(User.college),
        joinedload(Request.receiver).joinedload(User.college),
        joinedload(Request.sender_travel),
        joinedload(Request.receiver_travel)
    ).filter(
        Request.is_active == True,
        Request.status.in_(["pending", "accepted"])
    )

    received_reqs = base_query.filter(Request.sent_to == current_user.user_id).all()
    sent_reqs = base_query.filter(Request.sent_by == current_user.user_id).all()

    def enrich_request(req, is_received):
        partner_user = req.sender if is_received else req.receiver
        partner_travel = req.sender_travel if is_received else req.receiver_travel
        
        partner_college = partner_user.college.college_name if partner_user and partner_user.college else None
        
        is_anonymous = False
        if is_received:
            is_anonymous = (req.sender_privacy_mode == 'ANONYMOUS')
        else:
            is_anonymous = (req.receiver_privacy_mode == 'ANONYMOUS' or req.receiver_privacy_mode is None)

        return {
            "request_id": req.request_id,
            "sender_travel_id": req.sender_travel_id,
            "receiver_travel_id": req.receiver_travel_id,
            "sent_by": req.sent_by,
            "sent_to": req.sent_to,
            "status": req.status,
            "created_at": req.created_at,
            "sender_privacy_mode": req.sender_privacy_mode,
            "receiver_privacy_mode": req.receiver_privacy_mode,
            "partner_name": None if is_anonymous else (partner_user.name if partner_user else None),
            "partner_college": None if is_anonymous else partner_college,
            "partner_phone": None if is_anonymous else (partner_user.phone_no if partner_user else None),
            "partner_anonymous_id": partner_user.anonymous_id if partner_user else None,
            "partner_rating": round(4.0 + ((partner_user.user_id if partner_user else 0) % 10) / 10.0, 1),
            "partner_start": partner_travel.start_label if partner_travel else None,
            "partner_end": partner_travel.end_label if partner_travel else None,
        }
    
    return {
        "received": [enrich_request(r, True) for r in received_reqs],
        "sent": [enrich_request(r, False) for r in sent_reqs]
    }


@router.put("/request/{request_id}")  # Accepts, rejects, or cancels a request.
def respond_to_request(
    request_id: int,
    update_data: RequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = db.query(Request).filter(Request.request_id == request_id, Request.is_active == True).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status != "pending":
        raise HTTPException(status_code=400, detail="This request has already been resolved")

    status_lower = update_data.status.lower()

    if status_lower in ["cancelled", "canceled"]:
        if current_user.user_id not in [req.sent_by, req.sent_to]:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
        req.status = "cancelled"
        req.is_active = False
    elif status_lower in ["rejected", "declined"]:
        if current_user.user_id not in [req.sent_by, req.sent_to]:
            raise HTTPException(status_code=403, detail="Not authorized to decline this request")
        req.status = "rejected"
        req.is_active = False
    elif status_lower == "accepted":
        if req.sent_to != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to accept this request")
        req.status = "accepted"
        if update_data.privacy_mode:
            req.receiver_privacy_mode = update_data.privacy_mode.upper()
    else:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'accepted', 'rejected', or 'cancelled'")
        
    db.commit()
    
    return {"message": f"Request {req.status}"}


@router.post("/end")
def end_trip(
    trip_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Travel).filter(
        Travel.user_id == current_user.user_id,
        Travel.status != "completed",
        Travel.is_active == True
    )
    if trip_id:
        query = query.filter(Travel.travel_id == trip_id)
    trip = query.first()

    if not trip:
        raise HTTPException(status_code=404, detail="No active trip found to end")

    trip.status = "completed"
    trip.is_active = False

    # Only close requests linked to THIS specific trip
    accepted_requests = db.query(Request).filter(
        or_(
            Request.sender_travel_id == trip.travel_id,
            Request.receiver_travel_id == trip.travel_id
        ),
        Request.status == "accepted",
        Request.is_active == True
    ).all()
    
    accepted_req_ids = []
    for req in accepted_requests:
        req.status = "completed"
        accepted_req_ids.append(req.request_id)

    # Removed hard-delete of chat messages so they can appear in chat history
    # if accepted_req_ids:
    #     db.query(Chat).filter(Chat.request_id.in_(accepted_req_ids)).delete(synchronize_session=False)

    # Also resolve any pending requests so they don't remain stuck
    pending_requests = db.query(Request).filter(
        or_(
            Request.sender_travel_id == trip.travel_id,
            Request.receiver_travel_id == trip.travel_id
        ),
        Request.status == "pending",
        Request.is_active == True
    ).all()
    
    for req in pending_requests:
        req.status = "rejected"
        req.is_active = False

    db.commit()

    return {"message": "Trip ended successfully", "redirectTo": "/dashboard"}
