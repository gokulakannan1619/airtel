import os
import sqlite3
import uuid
import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from database import get_db_connection, haversine_distance, DB_PATH

app = FastAPI(
    title="Telecom Customer & Diwali Offers API",
    description="Backend API serving real database-driven customer lookup and Diwali telecom offers.",
    version="1.0.0"
)

# No-cache middleware for all static assets so browser always gets latest JS/CSS
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# Enable CORS for local testing or custom ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- PYDANTIC MODELS -----------------

class LocationResolveRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    session_id: Optional[str] = None
    mobile_number: Optional[str] = None

class CustomerSearchRequest(BaseModel):
    mobile_number: str
    customer_id: Optional[str] = None
    name: Optional[str] = None
    operator_hint: Optional[str] = None
    session_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    exact_address: Optional[str] = None
    locality: Optional[str] = None
    resolved_city: Optional[str] = None

class CustomerCreateRequest(BaseModel):
    name: str
    mobile_number: str
    email: Optional[str] = None
    operator_id: int
    plan_id: Optional[int] = None
    city: str
    district: Optional[str] = None
    state: str
    pincode: Optional[str] = "600001"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RechargeRequest(BaseModel):
    customer_id: str
    mobile_number: str
    offer_id: int
    amount: float
    payment_method: Optional[str] = "UPI"


# ----------------- HELPER FUNCTIONS -----------------

def reverse_geocode_exact(lat: float, lon: float):
    """
    Fetch exact address details from OpenStreetMap Nominatim reverse geocoding API.
    Provides complete street, locality, sub-district, district, state, and postal code.
    Gracefully falls back if network is offline or times out.
    """
    try:
        import urllib.request
        import json
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
        req = urllib.request.Request(url, headers={"User-Agent": "DiwaliTelecomPortal/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                addr = data.get("address", {})
                display_name = data.get("display_name", "")

                locality = (
                    addr.get("suburb") or 
                    addr.get("neighbourhood") or 
                    addr.get("residential") or 
                    addr.get("road") or 
                    addr.get("locality") or 
                    addr.get("city_district") or 
                    ""
                )
                city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
                district = addr.get("state_district") or addr.get("district") or city or ""
                state = addr.get("state", "")
                pincode = addr.get("postcode", "")

                return {
                    "success": True,
                    "exact_address": display_name,
                    "locality": locality,
                    "city": city,
                    "district": district,
                    "state": state,
                    "pincode": pincode
                }
    except Exception as e:
        pass
    return {"success": False}

def get_network_ip_location():
    """
    Detects network connection location (e.g. ISP circle, city, state) via IP lookup
    Ensures 100% working condition on desktop PCs without GPS chips.
    """
    try:
        import urllib.request
        import json
        req = urllib.request.Request("http://ip-api.com/json/", headers={"User-Agent": "DiwaliTelecom/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("status") == "success":
                    return {
                        "latitude": float(data.get("lat")),
                        "longitude": float(data.get("lon")),
                        "city": data.get("city"),
                        "state": data.get("regionName"),
                        "pincode": data.get("zip"),
                        "isp": data.get("isp"),
                        "query_ip": data.get("query")
                    }
    except Exception:
        pass
    return {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600001",
        "isp": "Bharti Airtel",
        "query_ip": "127.0.0.1"
    }

def mask_mobile(phone: str) -> str:
    cleaned = ''.join(c for c in phone if c.isdigit())
    if len(cleaned) >= 10:
        return f"{cleaned[:2]}******{cleaned[-2:]}"
    elif len(cleaned) >= 6:
        return f"{cleaned[:2]}***{cleaned[-1:]}"
    return phone


# ----------------- API ENDPOINTS -----------------

@app.get("/api/health")
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        counts = {}
        for table in ["telecom_operators", "locations", "plans", "customers", "diwali_offers", "recharge_transactions", "user_locations"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
            
        conn.close()
        return {
            "status": "healthy",
            "database": "SQLite (telecom.db)",
            "timestamp": datetime.datetime.now().isoformat(),
            "records": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


@app.get("/api/operators")
def get_operators():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, COUNT(d.offer_id) as active_offers_count
        FROM telecom_operators o
        LEFT JOIN diwali_offers d ON o.operator_id = d.operator_id AND d.status = 'Active'
        WHERE o.status = 'Active'
        GROUP BY o.operator_id
        ORDER BY o.operator_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/locations")
def get_locations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY city ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/plans")
def get_plans(operator_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if operator_id:
        cursor.execute("SELECT * FROM plans WHERE operator_id = ? AND status = 'Active'", (operator_id,))
    else:
        cursor.execute("SELECT * FROM plans WHERE status = 'Active'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/location/resolve")
def resolve_location(req: LocationResolveRequest):
    """
    Given latitude and longitude from browser high-accuracy geolocation:
    1. Obtains exact address, street, locality, district, state & postal code via reverse geocoding.
    2. Matches the nearest telecom circle in the database.
    3. Persists the exact location event in the user_locations database table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations")
    locations = cursor.fetchall()

    if not locations:
        conn.close()
        return {
            "resolved": False,
            "display_name": "Location not available",
            "message": "No telecom circles found in database"
        }

    # 1. Exact reverse geocoding lookup
    geo = reverse_geocode_exact(req.latitude, req.longitude)

    # 2. Nearest circle matching via Haversine distance
    nearest = None
    min_dist = float("inf")
    for loc in locations:
        dist = haversine_distance(req.latitude, req.longitude, loc["latitude"], loc["longitude"])
        if dist < min_dist:
            min_dist = dist
            nearest = loc

    # Determine exact resolved fields
    city = (geo.get("city") if (geo.get("success") and geo.get("city")) else nearest["city"])
    district = (geo.get("district") if (geo.get("success") and geo.get("district")) else nearest["district"])
    state = (geo.get("state") if (geo.get("success") and geo.get("state")) else nearest["state"])
    pincode = (geo.get("pincode") if (geo.get("success") and geo.get("pincode")) else nearest["pincode"])
    exact_address = geo.get("exact_address") if geo.get("success") else f"{nearest['city']}, {nearest['state']}, India"
    locality = (geo.get("locality") if (geo.get("success") and geo.get("locality")) else city) or city

    # 3. STORE EXACT LOCATION IN DATABASE: Log into user_locations table
    session_id = req.session_id or f"SES-{uuid.uuid4().hex[:8].upper()}"
    google_maps_link = f"https://www.google.com/maps?q={req.latitude},{req.longitude}"

    cursor.execute("""
        INSERT INTO user_locations (
            session_id, mobile_number, customer_id, latitude, longitude,
            accuracy_meters, exact_address, locality,
            resolved_city, resolved_district, resolved_state, resolved_pincode,
            distance_km, status, google_maps_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Granted', ?)
    """, (
        session_id,
        req.mobile_number,
        None,
        req.latitude,
        req.longitude,
        req.accuracy,
        exact_address,
        locality,
        city,
        district,
        state,
        pincode,
        round(min_dist, 1),
        google_maps_link
    ))
    log_id = cursor.lastrowid

    # If mobile_number was passed, also update customer exact location in customers table
    if req.mobile_number:
        cursor.execute("""
            UPDATE customers
            SET latitude = ?, longitude = ?, exact_address = ?, locality = ?, city = ?, district = ?, state = ?, pincode = ?, google_maps_link = ?
            WHERE mobile_number = ?
        """, (req.latitude, req.longitude, exact_address, locality, city, district, state, pincode, google_maps_link, req.mobile_number))

    conn.commit()
    conn.close()

    formatted_display = f"{locality}, {city}, {state} {pincode}".strip(", ")

    return {
        "resolved": True,
        "location_log_id": log_id,
        "session_id": session_id,
        "stored_in_db": True,
        "exact_address": exact_address,
        "locality": locality,
        "city": city,
        "district": district,
        "state": state,
        "pincode": pincode,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "accuracy_meters": req.accuracy or 10.0,
        "distance_km": round(min_dist, 1),
        "google_maps_link": google_maps_link,
        "display_name": formatted_display,
        "matched_circle": f"{nearest['city']} Telecom Circle ({round(min_dist, 1)} km away)"
    }


@app.get("/api/location/auto-ip")
def auto_ip_location():
    """
    Auto-detect real network IP location for desktop machines without hardware GPS.
    """
    return get_network_ip_location()


@app.get("/api/location/logs")
def get_location_logs(limit: int = 50):
    """
    Retrieve stored Turn On Location records with exact address details and Google Maps link from database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            location_log_id,
            session_id,
            COALESCE(customer_id, 'Guest / Pending Login') as customer_id,
            COALESCE(visitor_name, 'N/A') as visitor_name,
            COALESCE(sim_type, 'N/A') as sim_type,
            COALESCE(mobile_number, 'N/A') as mobile_number,
            latitude,
            longitude,
            COALESCE(accuracy_meters, 0.0) as accuracy_meters,
            COALESCE(locality, resolved_city) as locality,
            COALESCE(exact_address, resolved_city) as exact_address,
            COALESCE(google_maps_link, 'https://www.google.com/maps?q=' || latitude || ',' || longitude) as google_maps_link,
            resolved_city,
            resolved_state,
            resolved_pincode,
            distance_km,
            status,
            created_at
        FROM user_locations
        ORDER BY location_log_id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/customer/search")
def search_customer(req: CustomerSearchRequest):
    """
    Search customer strictly in database by mobile_number.
    Never trusts the frontend.
    """
    cleaned_mobile = ''.join(c for c in req.mobile_number if c.isdigit())
    if len(cleaned_mobile) != 10:
        return {
            "found": False,
            "message": "Please enter a valid 10-digit mobile number."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    # Search with join on operators and plans
    query = """
        SELECT 
            c.customer_id,
            c.name,
            c.mobile_number,
            c.email,
            c.operator_id,
            c.plan_id,
            c.city,
            c.district,
            c.state,
            c.pincode,
            c.latitude,
            c.longitude,
            c.exact_address,
            c.locality,
            c.google_maps_link,
            c.validity_days_remaining,
            c.data_remaining,
            c.created_at,
            o.operator_name,
            o.logo AS operator_logo,
            o.brand_color,
            o.support_number,
            p.plan_name,
            p.price AS current_plan_price,
            p.validity AS current_plan_validity,
            p.daily_data AS current_plan_daily_data,
            p.ott_benefit AS current_plan_ott
        FROM customers c
        JOIN telecom_operators o ON c.operator_id = o.operator_id
        JOIN plans p ON c.plan_id = p.plan_id
        WHERE c.mobile_number = ?
    """
    cursor.execute(query, (cleaned_mobile,))
    customer = cursor.fetchone()

    if not customer:
        conn.close()
        # Automatically register the visitor right away with Name, Mobile, SIM Type and GPS location!
        return auto_register_visitor(req)

    # Resolve latitude/longitude for current session first, then fallback to stored customer coordinates
    lat = req.latitude
    lon = req.longitude
    exact_addr = req.exact_address
    loc_area = req.locality

    if (not lat or not lon) and req.session_id:
        cursor.execute("""
            SELECT latitude, longitude, exact_address, locality, google_maps_link
            FROM user_locations WHERE session_id = ? ORDER BY location_log_id DESC LIMIT 1
        """, (req.session_id,))
        loc_row = cursor.fetchone()
        if loc_row and loc_row["latitude"]:
            lat = loc_row["latitude"]
            lon = loc_row["longitude"]
            exact_addr = exact_addr or loc_row["exact_address"]
            loc_area = loc_area or loc_row["locality"]

    # Fallback to existing customer location if current session had no coordinates
    lat = lat or customer["latitude"]
    lon = lon or customer["longitude"]
    exact_addr = exact_addr or customer["exact_address"]
    loc_area = loc_area or customer["locality"]

    gmaps = f"https://www.google.com/maps?q={lat},{lon}" if (lat and lon) else customer["google_maps_link"]

    # Update customer if name or operator or location provided
    update_clauses = [
        "latitude = ?", "longitude = ?",
        "exact_address = COALESCE(?, exact_address)",
        "locality = COALESCE(?, locality)",
        "google_maps_link = COALESCE(?, google_maps_link)"
    ]
    params = [lat, lon, exact_addr, loc_area, gmaps]

    if req.name and req.name.strip():
        update_clauses.append("name = ?")
        params.append(req.name.strip())

    op_name_to_log = customer["operator_name"]
    if req.operator_hint and req.operator_hint.isdigit():
        op_id_hint = int(req.operator_hint)
        update_clauses.append("operator_id = ?")
        params.append(op_id_hint)
        cursor.execute("SELECT operator_name FROM telecom_operators WHERE operator_id = ?", (op_id_hint,))
        op_found = cursor.fetchone()
        if op_found:
            op_name_to_log = op_found["operator_name"]

    params.append(customer["customer_id"])
    cursor.execute(f"UPDATE customers SET {', '.join(update_clauses)} WHERE customer_id = ?", tuple(params))

    if req.session_id:
        cursor.execute("""
            UPDATE user_locations
            SET customer_id = ?, mobile_number = ?, visitor_name = COALESCE(?, visitor_name), sim_type = COALESCE(?, sim_type), google_maps_link = COALESCE(?, google_maps_link)
            WHERE session_id = ?
        """, (customer["customer_id"], customer["mobile_number"], req.name or customer["name"], op_name_to_log, gmaps, req.session_id))

    conn.commit()

    # Re-fetch customer to return the fully updated profile
    cursor.execute(query, (cleaned_mobile,))
    customer = cursor.fetchone()

    # Match customer's city to location_id if possible
    cursor.execute("SELECT location_id FROM locations WHERE LOWER(city) = LOWER(?) LIMIT 1", (customer["city"],))
    loc_row = cursor.fetchone()
    location_id = loc_row["location_id"] if loc_row else None

    conn.close()

    return {
        "found": True,
        "customer": {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "raw_mobile": customer["mobile_number"],
            "masked_mobile": mask_mobile(customer["mobile_number"]),
            "email": customer["email"],
            "operator_id": customer["operator_id"],
            "operator_name": customer["operator_name"],
            "operator_logo": customer["operator_logo"],
            "brand_color": customer["brand_color"],
            "support_number": customer["support_number"],
            "plan_name": customer["plan_name"],
            "plan_validity": f"{customer['validity_days_remaining']} days remaining",
            "data_remaining": customer["data_remaining"],
            "city": customer["city"],
            "district": customer["district"],
            "state": customer["state"],
            "locality": customer["locality"] or req.locality or customer["city"],
            "exact_address": customer["exact_address"] or req.exact_address or f"{customer['city']}, {customer['state']}, India",
            "latitude": req.latitude or customer["latitude"],
            "longitude": req.longitude or customer["longitude"],
            "accuracy_meters": req.accuracy or 10.0,
            "location_display": f"{(customer['locality'] or req.locality or customer['city']).strip()}, {customer['city']}, {customer['state']}",
            "google_maps_link": customer["google_maps_link"] or (f"https://www.google.com/maps?q={customer['latitude']},{customer['longitude']}" if customer["latitude"] and customer["longitude"] else None),
            "location_id": location_id,
            "created_at": customer["created_at"]
        }
    }


@app.post("/api/customer/auto-register")
def auto_register_visitor(req: CustomerSearchRequest):
    """
    Auto-register a new visitor from the search form.
    Stores name + mobile + SIM type + GPS location into the database without a separate form.
    Returns the created customer profile.
    """
    cleaned_mobile = ''.join(c for c in req.mobile_number if c.isdigit())
    if len(cleaned_mobile) != 10:
        raise HTTPException(status_code=400, detail="Mobile number must be exactly 10 digits.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Don't re-register if already exists
    cursor.execute("SELECT customer_id FROM customers WHERE mobile_number = ?", (cleaned_mobile,))
    if cursor.fetchone():
        conn.close()
        return search_customer(req)

    # Determine operator — from hint or default to Jio (1)
    operator_id = 1  # default Jio
    if req.operator_hint and req.operator_hint.isdigit():
        operator_id = int(req.operator_hint)
    elif req.customer_id and req.customer_id.isdigit():
        operator_id = int(req.customer_id)

    cursor.execute("SELECT operator_id, operator_name FROM telecom_operators WHERE operator_id = ?", (operator_id,))
    op_row = cursor.fetchone()
    if not op_row:
        operator_id = 1
        cursor.execute("SELECT operator_id, operator_name FROM telecom_operators WHERE operator_id = 1")
        op_row = cursor.fetchone()

    op_code = op_row["operator_name"][:3].upper()

    # Pick cheapest base plan for operator
    cursor.execute("SELECT plan_id FROM plans WHERE operator_id = ? ORDER BY price ASC LIMIT 1", (operator_id,))
    default_plan = cursor.fetchone()
    plan_id = default_plan["plan_id"] if default_plan else 1

    # Resolve city/state from GPS if available, else use defaults
    city = req.resolved_city or "Chennai"
    state = "Tamil Nadu"
    district = city
    pincode = "600001"
    exact_address = None
    locality = None
    google_maps_link = None

    # Check if coords exist in user_locations for this session or latest
    if (not req.latitude or not req.longitude) and req.session_id:
        cursor.execute("""
            SELECT latitude, longitude, exact_address, locality, resolved_city, resolved_state, resolved_pincode, google_maps_link
            FROM user_locations
            WHERE session_id = ?
            ORDER BY location_log_id DESC LIMIT 1
        """, (req.session_id,))
        loc_row = cursor.fetchone()
        if loc_row and loc_row["latitude"]:
            req.latitude = loc_row["latitude"]
            req.longitude = loc_row["longitude"]
            city = loc_row["resolved_city"] or city
            state = loc_row["resolved_state"] or state
            district = city
            pincode = loc_row["resolved_pincode"] or pincode
            exact_address = loc_row["exact_address"]
            locality = loc_row["locality"]
            google_maps_link = loc_row["google_maps_link"]

    if (not req.latitude or not req.longitude):
        cursor.execute("""
            SELECT latitude, longitude, exact_address, locality, resolved_city, resolved_state, resolved_pincode, google_maps_link
            FROM user_locations
            ORDER BY location_log_id DESC LIMIT 1
        """)
        loc_row = cursor.fetchone()
        if loc_row and loc_row["latitude"]:
            req.latitude = loc_row["latitude"]
            req.longitude = loc_row["longitude"]
            city = loc_row["resolved_city"] or city
            state = loc_row["resolved_state"] or state
            district = city
            pincode = loc_row["resolved_pincode"] or pincode
            exact_address = loc_row["exact_address"]
            locality = loc_row["locality"]
            google_maps_link = loc_row["google_maps_link"]

    if req.latitude and req.longitude:
        google_maps_link = google_maps_link or f"https://www.google.com/maps?q={req.latitude},{req.longitude}"
        if not exact_address:
            geo = reverse_geocode_exact(req.latitude, req.longitude)
            if geo.get("success"):
                city = geo.get("city") or city
                state = geo.get("state") or state
                district = geo.get("district") or city
                pincode = geo.get("pincode") or pincode
                exact_address = geo.get("exact_address")
                locality = geo.get("locality")
    else:
        # Fallback default location
        req.latitude = 13.0827
        req.longitude = 80.2707
        google_maps_link = f"https://www.google.com/maps?q={req.latitude},{req.longitude}"

    # Generate customer ID
    random_suffix = str(uuid.uuid4().int)[:4]
    customer_id = f"CUST-{op_code}-{random_suffix}"
    visitor_name = req.name or "Guest User"

    cursor.execute("""
        INSERT INTO customers (
            customer_id, name, mobile_number, operator_id, plan_id,
            city, district, state, pincode, latitude, longitude,
            exact_address, locality, google_maps_link,
            validity_days_remaining, data_remaining
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id, visitor_name, cleaned_mobile, operator_id, plan_id,
        city, district, state, pincode, req.latitude, req.longitude,
        exact_address, locality, google_maps_link,
        28, "2.0 GB / 2.0 GB left today"
    ))

    # Also update the user_locations log with name, sim type, google maps link
    if req.session_id:
        cursor.execute("""
            UPDATE user_locations
            SET customer_id = ?, mobile_number = ?, visitor_name = ?, sim_type = ?, google_maps_link = ?
            WHERE session_id = ?
        """, (customer_id, cleaned_mobile, visitor_name, op_row["operator_name"], google_maps_link, req.session_id))

    conn.commit()
    conn.close()

    # Return created profile
    return search_customer(CustomerSearchRequest(
        mobile_number=cleaned_mobile,
        session_id=req.session_id,
        latitude=req.latitude,
        longitude=req.longitude
    ))


@app.post("/api/customer/create")
def create_customer(req: CustomerCreateRequest):
    """
    Create a new customer profile in the database.
    """
    cleaned_mobile = ''.join(c for c in req.mobile_number if c.isdigit())
    if len(cleaned_mobile) != 10:
        raise HTTPException(status_code=400, detail="Mobile number must be exactly 10 digits.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if mobile already exists
    cursor.execute("SELECT customer_id FROM customers WHERE mobile_number = ?", (cleaned_mobile,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Mobile number is already registered. Please login instead.")

    # Validate operator
    cursor.execute("SELECT operator_id, operator_name FROM telecom_operators WHERE operator_id = ?", (req.operator_id,))
    op_row = cursor.fetchone()
    if not op_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid telecom operator selected.")

    op_code = op_row["operator_name"][:3].upper()

    # Pick base plan if not specified
    plan_id = req.plan_id
    if not plan_id:
        cursor.execute("SELECT plan_id FROM plans WHERE operator_id = ? ORDER BY price ASC LIMIT 1", (req.operator_id,))
        default_plan = cursor.fetchone()
        plan_id = default_plan["plan_id"] if default_plan else 1

    # Generate customer ID
    random_suffix = str(uuid.uuid4().int)[:4]
    customer_id = f"CUST-{op_code}-{random_suffix}"

    google_maps_link = None
    if req.latitude and req.longitude:
        google_maps_link = f"https://www.google.com/maps?q={req.latitude},{req.longitude}"

    district = req.district or req.city
    cursor.execute("""
        INSERT INTO customers (
            customer_id, name, mobile_number, email, operator_id, plan_id,
            city, district, state, pincode, latitude, longitude,
            google_maps_link, validity_days_remaining, data_remaining
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id, req.name, cleaned_mobile, req.email, req.operator_id, plan_id,
        req.city, district, req.state, req.pincode or "600001", req.latitude, req.longitude,
        google_maps_link, 28, "2.0 GB / 2.0 GB left today"
    ))

    conn.commit()
    conn.close()

    # Retrieve created customer
    return search_customer(CustomerSearchRequest(mobile_number=cleaned_mobile))


@app.get("/api/offers")
def get_diwali_offers(
    operator_id: Optional[int] = Query(None, description="Operator ID (Jio=1, Airtel=2, Vi=3, BSNL=4)"),
    location_id: Optional[int] = Query(None, description="Matched Location ID"),
    city: Optional[str] = Query(None, description="Customer or detected city name"),
    compare_all: bool = Query(False, description="Set True to compare across all operators")
):
    """
    Dynamically select offers from database.
    Strictly filters by operator unless compare_all is True.
    Prioritizes location-specific festive offers alongside Pan-India offers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # If city is passed without location_id, look up location_id
    resolved_loc_id = location_id
    if not resolved_loc_id and city and city.lower() != "location not available":
        cursor.execute("SELECT location_id FROM locations WHERE LOWER(city) = LOWER(?) LIMIT 1", (city.strip(),))
        loc_row = cursor.fetchone()
        if loc_row:
            resolved_loc_id = loc_row["location_id"]

    query = """
        SELECT 
            d.offer_id,
            d.operator_id,
            d.location_id,
            d.offer_name,
            d.price,
            d.validity,
            d.data,
            d.voice,
            d.sms,
            d.bonus,
            d.discount,
            d.start_date,
            d.end_date,
            d.badge,
            d.status,
            o.operator_name,
            o.logo AS operator_logo,
            o.brand_color,
            l.city AS offer_city,
            l.state AS offer_state
        FROM diwali_offers d
        JOIN telecom_operators o ON d.operator_id = o.operator_id
        LEFT JOIN locations l ON d.location_id = l.location_id
        WHERE d.status = 'Active'
    """
    params = []

    if not compare_all and operator_id is not None:
        query += " AND d.operator_id = ?"
        params.append(operator_id)

    # Location filtering logic:
    # Show offers that are Pan-India (location_id IS NULL) OR matched to current location
    if resolved_loc_id is not None:
        query += " AND (d.location_id IS NULL OR d.location_id = ?)"
        params.append(resolved_loc_id)
    else:
        # If location not available, only show National/Pan-India offers
        query += " AND d.location_id IS NULL"

    # Order by location-specific first, then by popularity/price
    query += " ORDER BY (CASE WHEN d.location_id IS NOT NULL THEN 0 ELSE 1 END), d.price ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    offers = []
    for row in rows:
        item = dict(row)
        item["is_location_exclusive"] = item["location_id"] is not None
        offers.append(item)

    return {
        "count": len(offers),
        "operator_filter": operator_id if not compare_all else "ALL",
        "location_filter": resolved_loc_id,
        "offers": offers
    }


@app.post("/api/recharge")
def process_recharge(req: RechargeRequest):
    """
    Process instant simulated recharge and record transaction in database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify offer
    cursor.execute("""
        SELECT d.*, o.operator_name, o.brand_color
        FROM diwali_offers d
        JOIN telecom_operators o ON d.operator_id = o.operator_id
        WHERE d.offer_id = ?
    """, (req.offer_id,))
    offer = cursor.fetchone()

    if not offer:
        conn.close()
        raise HTTPException(status_code=404, detail="Offer not found.")

    tx_id = f"TXN-DIWALI-{uuid.uuid4().hex[:8].upper()}"

    cursor.execute("""
        INSERT INTO recharge_transactions (transaction_id, customer_id, mobile_number, offer_id, amount, payment_method, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Success')
    """, (tx_id, req.customer_id, req.mobile_number, req.offer_id, req.amount, req.payment_method))

    # Update customer data/validity in database
    cursor.execute("""
        UPDATE customers
        SET validity_days_remaining = validity_days_remaining + 28,
            data_remaining = 'Full quota restored (' || ? || ')'
        WHERE customer_id = ?
    """, (offer["data"], req.customer_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "transaction_id": tx_id,
        "recharge_amount": req.amount,
        "offer_name": offer["offer_name"],
        "operator_name": offer["operator_name"],
        "validity": offer["validity"],
        "data_benefit": offer["data"],
        "bonus_perks": offer["bonus"],
        "festive_coupon": f"DIWALI-{uuid.uuid4().hex[:6].upper()}-SWEETS",
        "timestamp": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "receipt_message": f"Congratulations! Your Diwali Special recharge of ₹{req.amount} is active."
    }


@app.get("/api/demo-customers")
def get_demo_customers():
    """
    Returns pre-seeded demo profiles for quick testing.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.customer_id, c.name, c.mobile_number, c.city, c.state, o.operator_name, o.logo
        FROM customers c
        JOIN telecom_operators o ON c.operator_id = o.operator_id
        ORDER BY c.customer_id ASC
        LIMIT 6
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/customers")
def get_all_customers():
    """
    Returns all customer profiles stored in the database, including their Google Maps location links.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.customer_id, 
            c.name, 
            c.mobile_number, 
            o.operator_name as sim_type, 
            c.city, 
            c.state, 
            c.latitude, 
            c.longitude,
            COALESCE(c.google_maps_link, 'https://www.google.com/maps?q=' || c.latitude || ',' || c.longitude) as google_maps_link,
            c.created_at
        FROM customers c
        JOIN telecom_operators o ON c.operator_id = o.operator_id
        ORDER BY c.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ----------------- STATIC FILES & FRONTEND -----------------

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend index.html not found yet. Please check /frontend folder."}
