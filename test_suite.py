import requests
import json
import sys

# Set stdout encoding if possible
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE = "http://127.0.0.1:8000"

def test_suite():
    print("==================================================")
    print("RUNNING TELECOM & DIWALI OFFERS TEST SUITE")
    print("==================================================")

    # 1. Health check with user_locations count
    r = requests.get(f"{BASE}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health = r.json()
    print("[PASS] 1. Database Health Check:")
    print("       Table records:", json.dumps(health['records'], indent=2))
    assert "user_locations" in health['records']

    # 2. Geolocation resolve & store exact location in database
    session_test_id = "EXACT-GPS-SESSION-001"
    r = requests.post(f"{BASE}/api/location/resolve", json={
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy": 8.5,
        "session_id": session_test_id
    })
    assert r.status_code == 200, f"Location resolve error: {r.text}"
    loc = r.json()
    assert loc.get("stored_in_db") is True
    assert loc.get("exact_address") is not None
    print(f"[PASS] 2. Exact Geolocation Resolve & Stored in Database (Log ID #{loc['location_log_id']}):")
    print(f"       Exact Locality : {loc['locality']}")
    print(f"       Exact Address  : {loc['exact_address']}")
    print(f"       GPS Coordinates: {loc['latitude']} N, {loc['longitude']} E (Accuracy: +/-{loc['accuracy_meters']}m)")
    print(f"       Circle Matched : {loc['matched_circle']}")

    # 3. Verify user_locations table in SQLite has exact address & accuracy
    r = requests.get(f"{BASE}/api/location/logs")
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) > 0
    matched_log = next((l for l in logs if l.get("session_id") == session_test_id), None)
    assert matched_log is not None, "Stored location log not found in user_locations table"
    assert "exact_address" in matched_log
    assert "accuracy_meters" in matched_log
    print(f"[PASS] 3. Verified user_locations Table in SQLite:")
    print(f"       Found Log #{matched_log['location_log_id']} | Address: {matched_log['exact_address'][:60]}... | Accuracy: {matched_log['accuracy_meters']}m")

    # 4. Customer Search & Link Exact Location (Arun Kumar - Jio)
    r = requests.post(f"{BASE}/api/customer/search", json={
        "mobile_number": "9840123456",
        "session_id": session_test_id,
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy": 8.5,
        "exact_address": loc["exact_address"],
        "locality": loc["locality"]
    })
    assert r.status_code == 200
    cust_data = r.json()
    assert cust_data["found"] is True
    cust = cust_data["customer"]
    print("[PASS] 4. Customer Search & Exact Location Linked to Profile:")
    print(f"       Name: {cust['name']}")
    print(f"       Masked Mobile: {cust['masked_mobile']}")
    print(f"       Operator: {cust['operator_name']}")
    print(f"       Exact Address: {cust.get('exact_address')}")
    print(f"       GPS Linked: {cust.get('latitude')}, {cust.get('longitude')}")

    # 5. Customer Auto-Register (Seamless creation on search with Name, SIM Type, and Google Maps Link)
    test_num = "9789342932"
    r = requests.post(f"{BASE}/api/customer/search", json={
        "mobile_number": test_num,
        "name": "Gokul Kannan",
        "operator_hint": "2", # Airtel
        "session_id": "TEST-SES-AUTO-REG"
    })
    assert r.status_code == 200
    auto_reg = r.json()
    assert auto_reg["found"] is True, "Expected auto-registration to find/create customer profile"
    auto_cust = auto_reg["customer"]
    assert auto_cust["name"] == "Gokul Kannan"
    assert auto_cust["operator_name"] == "Airtel"
    assert "https://www.google.com/maps?q=" in auto_cust.get("google_maps_link", "")
    print("[PASS] 5. Customer Auto-Registration directly on Search:")
    print(f"       Name: {auto_cust['name']} | Op: {auto_cust['operator_name']} | Mobile: {auto_cust['raw_mobile']}")
    print(f"       Google Maps Link: {auto_cust['google_maps_link']}")

    # 6. Customer Creation (Registering new profile)
    new_user_payload = {
        "name": "Kavita Rao",
        "mobile_number": "9911223344",
        "email": "kavita.rao@test.com",
        "operator_id": 2, # Airtel
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001"
    }
    r = requests.post(f"{BASE}/api/customer/create", json=new_user_payload)
    if r.status_code == 200:
        new_cust = r.json()["customer"]
        print("[PASS] 6. Customer Registration (New Profile Created):")
        print(f"       Created ID: {new_cust['customer_id']} | Name: {new_cust['name']} | Op: {new_cust['operator_name']}")
    elif r.status_code == 400 and "already registered" in r.text:
        print("[PASS] 6. Customer Registration (Already registered validation passed)")

    # 7. Dynamic Offers for Jio in Chennai (strictly Jio only!)
    r = requests.get(f"{BASE}/api/offers?operator_id=1&city=Chennai")
    assert r.status_code == 200
    offers = r.json()["offers"]
    assert len(offers) > 0
    for o in offers:
        assert o["operator_name"] == "Jio", f"Expected only Jio offers, got {o['operator_name']}"
    print(f"[PASS] 7. Dynamic Offers for Jio in Chennai ({len(offers)} offers, strict operator filter):")
    for o in offers:
        loc_tag = f"[Circle: {o['offer_city']}]" if o['offer_city'] else "[Pan-India]"
        print(f"       - {o['offer_name']} | Rs. {o['price']} | {o['validity']} | {loc_tag}")

    # 8. Dynamic Offers for Airtel in Delhi (strictly Airtel only!)
    r = requests.get(f"{BASE}/api/offers?operator_id=2&city=Delhi")
    assert r.status_code == 200
    airtel_offers = r.json()["offers"]
    for o in airtel_offers:
        assert o["operator_name"] == "Airtel"
    print(f"[PASS] 8. Dynamic Offers for Airtel in Delhi ({len(airtel_offers)} offers, strict operator filter):")
    for o in airtel_offers:
        loc_tag = f"[Circle: {o['offer_city']}]" if o['offer_city'] else "[Pan-India]"
        print(f"       - {o['offer_name']} | Rs. {o['price']} | {o['validity']} | {loc_tag}")

    # 9. Simulated Recharge Transaction
    recharge_payload = {
        "customer_id": "CUST-JIO-101",
        "mobile_number": "9840123456",
        "offer_id": 1,
        "amount": 349.0
    }
    r = requests.post(f"{BASE}/api/recharge", json=recharge_payload)
    assert r.status_code == 200
    tx = r.json()
    assert tx["success"] is True
    print("[PASS] 9. Simulated Recharge Transaction:")
    print(f"       TXN ID: {tx['transaction_id']}")
    print(f"       Offer: {tx['offer_name']}")
    print(f"       Festive Reward Coupon: {tx['festive_coupon']}")

    # 10. Frontend Index HTML
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200
    assert "Diwali Telecom Connect" in r.text
    print(f"[PASS] 10. Frontend Static Serving: Status 200, Content: {len(r.text)} bytes")

    print("==================================================")
    print("ALL 10 TEST CASES COMPLETED WITH EXACT LOCATION!")
    print("==================================================")

if __name__ == "__main__":
    test_suite()
