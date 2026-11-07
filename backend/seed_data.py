import sqlite3
import os
from database import get_db_connection, init_db

def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data to allow fresh re-seeding
    cursor.execute("DELETE FROM recharge_transactions;")
    cursor.execute("DELETE FROM user_locations;")
    cursor.execute("DELETE FROM diwali_offers;")
    cursor.execute("DELETE FROM customers;")
    cursor.execute("DELETE FROM plans;")
    cursor.execute("DELETE FROM locations;")
    cursor.execute("DELETE FROM telecom_operators;")

    # Reset SQLite autoincrement sequences
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('telecom_operators', 'locations', 'plans', 'diwali_offers');")

    # 1. Seed telecom_operators
    operators = [
        (1, "Jio", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Reliance_Jio_Logo_%28October_2015%29.svg/200px-Reliance_Jio_Logo_%28October_2015%29.svg.png", "#0a2885", "https://www.jio.com", "198 / 199", "Active"),
        (2, "Airtel", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Airtel_logo.svg/200px-Airtel_logo.svg.png", "#e60000", "https://www.airtel.in", "121 / 198", "Active"),
        (3, "Vi", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Vodafone_Idea_Logo.svg/200px-Vodafone_Idea_Logo.svg.png", "#d91638", "https://www.myvi.in", "199", "Active"),
        (4, "BSNL", "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Bharat_Sanchar_Nigam_Limited_Logo.svg/200px-Bharat_Sanchar_Nigam_Limited_Logo.svg.png", "#194383", "https://www.bsnl.co.in", "1503 / 1800-180-1503", "Active")
    ]
    cursor.executemany("""
        INSERT INTO telecom_operators (operator_id, operator_name, logo, brand_color, website, support_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, operators)

    # 2. Seed locations (Major Indian telecom circles)
    locations = [
        (1, "Chennai", "Chennai", "Tamil Nadu", "600001", 13.0827, 80.2707),
        (2, "Delhi", "New Delhi", "Delhi", "110001", 28.6139, 77.2090),
        (3, "Mumbai", "Mumbai Suburban", "Maharashtra", "400001", 19.0760, 72.8777),
        (4, "Bengaluru", "Bengaluru Urban", "Karnataka", "560001", 12.9716, 77.5946),
        (5, "Hyderabad", "Hyderabad", "Telangana", "500001", 17.3850, 78.4867),
        (6, "Kolkata", "Kolkata", "West Bengal", "700001", 22.5726, 88.3639),
        (7, "Ahmedabad", "Ahmedabad", "Gujarat", "380001", 23.0225, 72.5714),
        (8, "Pune", "Pune", "Maharashtra", "411001", 18.5204, 73.8567)
    ]
    cursor.executemany("""
        INSERT INTO locations (location_id, city, district, state, pincode, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, locations)

    # 3. Seed plans (standard base plans for each operator)
    plans = [
        # Jio Base Plans
        (1, 1, "Jio True 5G Daily Saver", 299.0, "28 days", "1.5 GB/day", "42 GB", "Unlimited", "100 SMS/day", "JioTV, JioCinema, JioCloud", "Active"),
        (2, 1, "Jio 2 GB/day Super Pack", 349.0, "28 days", "2.0 GB/day", "56 GB", "Unlimited", "100 SMS/day", "Unlimited 5G Data, JioCinema, JioTV", "Active"),
        (3, 1, "Jio Hero Quarterly", 899.0, "90 days", "2.0 GB/day", "180 GB", "Unlimited", "100 SMS/day", "Unlimited 5G Data, JioCinema", "Active"),
        (4, 1, "Jio Annual Powerhouse", 3599.0, "365 days", "2.5 GB/day", "912.5 GB", "Unlimited", "100 SMS/day", "Unlimited 5G, 1-Year FanCode", "Active"),

        # Airtel Base Plans
        (5, 2, "Airtel Smart Recharge", 299.0, "28 days", "1.5 GB/day", "42 GB", "Unlimited", "100 SMS/day", "Wynk Music, Free Hellotunes", "Active"),
        (6, 2, "Airtel Unlimited 5G Daily", 349.0, "28 days", "2.0 GB/day", "56 GB", "Unlimited", "100 SMS/day", "Unlimited 5G, Airtel Xstream Play", "Active"),
        (7, 2, "Airtel Creator Pack", 979.0, "84 days", "2.0 GB/day", "168 GB", "Unlimited", "100 SMS/day", "Unlimited 5G, Adobe Express Premium", "Active"),
        (8, 2, "Airtel Mega Annual Plan", 3599.0, "365 days", "2.0 GB/day", "730 GB", "Unlimited", "100 SMS/day", "Unlimited 5G, Apollo 24|7 Circle 1-Year", "Active"),

        # Vi Base Plans
        (9, 3, "Vi Binge All Night", 299.0, "28 days", "1.5 GB/day", "42 GB", "Unlimited", "100 SMS/day", "12 AM - 6 AM Unlimited Data, Weekend Rollover", "Active"),
        (10, 3, "Vi Hero Unlimited", 349.0, "28 days", "2.0 GB/day", "56 GB", "Unlimited", "100 SMS/day", "Vi Movies & TV, Data Delights (2GB backup)", "Active"),
        (11, 3, "Vi Super Combo", 719.0, "84 days", "1.5 GB/day", "126 GB", "Unlimited", "100 SMS/day", "Binge All Night, Weekend Rollover", "Active"),
        (12, 3, "Vi Annual Celebration", 3199.0, "365 days", "2.0 GB/day", "730 GB", "Unlimited", "100 SMS/day", "Sony LIV 1-year, Binge All Night", "Active"),

        # BSNL Base Plans
        (13, 4, "BSNL Swadeshi Connect", 199.0, "30 days", "2.0 GB/day", "60 GB", "Unlimited", "100 SMS/day", "Free National Roaming, Zing Music", "Active"),
        (14, 4, "BSNL Student & Pro Combo", 399.0, "70 days", "1.0 GB/day", "70 GB", "Unlimited", "100 SMS/day", "National Roaming including MTNL Delhi & Mumbai", "Active"),
        (15, 4, "BSNL Long Validity Combo", 797.0, "300 days", "2.0 GB/day (first 60 days)", "120 GB", "Unlimited", "100 SMS/day", "Bi-yearly standby connectivity", "Active"),
        (16, 4, "BSNL Bharat Samriddhi Annual", 1999.0, "365 days", "3.0 GB/day", "1095 GB", "Unlimited", "100 SMS/day", "Unlimited National Calls, PRBT Tunes", "Active")
    ]
    cursor.executemany("""
        INSERT INTO plans (plan_id, operator_id, plan_name, price, validity, daily_data, total_data, voice, sms, ott_benefit, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, plans)

    # 4. Seed customers (with varying operators, locations, and data balances)
    customers = [
        ("CUST-JIO-101", "Arun Kumar", "9840123456", "arun.kumar@gmail.com", 1, 2, "Chennai", "Chennai", "Tamil Nadu", "600001", 13.0827, 80.2707, 18, "1.4 GB / 2.0 GB left today"),
        ("CUST-AIR-102", "Priya Sharma", "9811234567", "priya.sharma@yahoo.co.in", 2, 6, "Delhi", "New Delhi", "Delhi", "110001", 28.6139, 77.2090, 7, "0.8 GB / 2.0 GB left today"),
        ("CUST-VI-103", "Rajesh Verma", "9820345678", "rajesh.verma@outlook.com", 3, 9, "Mumbai", "Mumbai Suburban", "Maharashtra", "400001", 19.0760, 72.8777, 24, "1.2 GB / 1.5 GB left today"),
        ("CUST-BSNL-104", "Sneha Patel", "9426456789", "sneha.patel@rediffmail.com", 4, 13, "Ahmedabad", "Ahmedabad", "Gujarat", "380001", 23.0225, 72.5714, 2, "1.9 GB / 2.0 GB left today"),
        ("CUST-JIO-105", "Karthik Raman", "9841567890", "karthik.raman@gmail.com", 1, 3, "Chennai", "Chennai", "Tamil Nadu", "600028", 13.0244, 80.2588, 45, "1.8 GB / 2.0 GB left today"),
        ("CUST-AIR-106", "Ananya Deshmukh", "9821678901", "ananya.d@gmail.com", 2, 7, "Pune", "Pune", "Maharashtra", "411001", 18.5204, 73.8567, 12, "1.6 GB / 2.0 GB left today"),
        ("CUST-VI-107", "Vikram Malhotra", "9830789012", "vikram.m@gmail.com", 3, 10, "Kolkata", "Kolkata", "West Bengal", "700001", 22.5726, 88.3639, 5, "0.4 GB / 2.0 GB left today"),
        ("CUST-JIO-108", "Divya Reddy", "9849890123", "divya.reddy@gmail.com", 1, 2, "Hyderabad", "Hyderabad", "Telangana", "500001", 17.3850, 78.4867, 21, "1.7 GB / 2.0 GB left today"),
        ("CUST-AIR-109", "Suresh Nair", "9847123987", "suresh.nair@gmail.com", 2, 5, "Bengaluru", "Bengaluru Urban", "Karnataka", "560001", 12.9716, 77.5946, 14, "1.1 GB / 1.5 GB left today")
    ]
    cursor.executemany("""
        INSERT INTO customers (customer_id, name, mobile_number, email, operator_id, plan_id, city, district, state, pincode, latitude, longitude, validity_days_remaining, data_remaining)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, customers)

    # 5. Seed diwali_offers
    # (location_id: NULL means Pan-India offer for that operator; specific location_id means circle/city exclusive)
    diwali_offers = [
        # ----------------- JIO DIWALI OFFERS -----------------
        (1, 1, None, "Jio Diwali Dhamaka 5G Unlimited", 349.0, "28 days", "2 GB/day + 50 GB Bonus", "Unlimited Calls", "100 SMS/day", "50 GB Extra High-Speed Data + JioCinema Premium (3 Months) + ₹50 Swiggy Voucher", "Flat ₹50 Festival Discount applied", "2026-10-15", "2026-11-25", "DIWALI DHAMAKA", "Active"),
        (2, 1, 1, "Jio Chennai & TN Festive Deepavali Special", 449.0, "35 days", "3 GB/day + 25 GB Bonus", "Unlimited Calls", "100 SMS/day", "Tamil SunNXT OTT + ₹500 Ajio Deepavali Shopping Coupon + Unlimited 5G", "15% Extra Festive Validity (35 days instead of 28)", "2026-10-15", "2026-11-25", "CHENNAI EXCLUSIVE", "Active"),
        (3, 1, 5, "Jio Hyderabad Deccan Festive Delight", 449.0, "35 days", "3 GB/day + 30 GB Bonus", "Unlimited Calls", "100 SMS/day", "Aha Video VIP (Telugu) + ₹300 Zomato Sweets Coupon + Unlimited 5G", "Diwali Sweets & Streaming Pack", "2026-10-15", "2026-11-25", "HYDERABAD EXCLUSIVE", "Active"),
        (4, 1, None, "Jio Shubh Deepavali Quarterly Bonanza", 899.0, "90 days", "2 GB/day + 20 GB Bonus", "Unlimited Calls", "100 SMS/day", "True 5G Unlimited + ₹100 Reliance Digital Diya Voucher + JioTV VIP", "Bonus 20 GB lumpsum high speed", "2026-10-15", "2026-11-25", "BESTSELLER", "Active"),
        (5, 1, None, "Jio Shubh Labh Annual 5G Mega", 3599.0, "365 days", "2.5 GB/day + 100 GB Bonus", "Unlimited Calls", "100 SMS/day", "1-Year FanCode + EaseMyTrip ₹1,500 Festive Flight Discount + Swiggy One Lite", "Save ₹400 + 100 GB Festive Data Bank", "2026-10-15", "2026-11-25", "ANNUAL BUMPER", "Active"),

        # ----------------- AIRTEL DIWALI OFFERS -----------------
        (6, 2, None, "Airtel Diwali Sparkle 5G Plus", 349.0, "28 days", "2 GB/day + 30 GB Extra", "Unlimited Calls", "100 SMS/day", "30 GB Extra Festive Data + Wynk Music Pro + ₹100 Titan Festive Watch Voucher", "Includes ₹50 Festival Cashback via Airtel Payments Bank", "2026-10-15", "2026-11-25", "DIWALI DHAMAKA", "Active"),
        (7, 2, 2, "Airtel Delhi-NCR Capital Diwali Delight", 499.0, "42 days", "2.5 GB/day + 40 GB Bonus", "Unlimited Calls", "100 SMS/day", "Airtel Xstream Play (22+ OTTs including SonyLIV, Lionsgate) + ₹250 Haldiram Sweets Voucher", "Extra 14 Days Free Validity bonus", "2026-10-15", "2026-11-25", "DELHI-NCR EXCLUSIVE", "Active"),
        (8, 2, 1, "Airtel Chennai Deepavali Kondattam", 549.0, "56 days", "2 GB/day + 50 GB Bonus", "Unlimited Calls", "100 SMS/day", "SunNXT & Aha Tamil Subscription + Free Sim Delivery + ₹500 Pothys Voucher", "Festive Double Data & Southern Streaming", "2026-10-15", "2026-11-25", "CHENNAI EXCLUSIVE", "Active"),
        (9, 2, None, "Airtel Festival Hero Combo", 979.0, "84 days", "2 GB/day + Unlimited 5G", "Unlimited Calls", "100 SMS/day", "Adobe Express Premium (Free 1-Yr) + Apollo 24|7 Circle + Free HelloTunes", "Festival Special OTT & Wellness Gift", "2026-10-15", "2026-11-25", "POPULAR CHOICE", "Active"),
        (10, 2, None, "Airtel Infinity Diwali Grand Annual", 3599.0, "365 days", "2.5 GB/day + 150 GB Extra", "Unlimited Calls", "100 SMS/day", "Disney+ Hotstar 1-Year Mobile + ₹2,000 MakeMyTrip Diwali Holiday Coupon + Apollo 24|7", "Mega ₹600 Annual Savings", "2026-10-15", "2026-11-25", "ANNUAL BUMPER", "Active"),

        # ----------------- VI DIWALI OFFERS -----------------
        (11, 3, None, "Vi Diwali Binge & Sparkle", 299.0, "28 days", "1.5 GB/day + 20 GB Bonus", "Unlimited Calls", "100 SMS/day", "Free 12 AM to 6 AM Unlimited Night Data + Weekend Rollover + ₹30 Vi Store Voucher", "Extra 20 GB Free Diwali Data Coupon in Vi App", "2026-10-15", "2026-11-25", "DIWALI DHAMAKA", "Active"),
        (12, 3, 3, "Vi Mumbai Diwali Local Express", 449.0, "35 days", "3 GB/day + 50 GB Extra", "Unlimited Calls", "100 SMS/day", "Vi Movies & TV VIP (17+ OTTs) + Swiggy One 3 Months Free + ₹200 Reliance Smart Bazaar Coupon", "Mumbai Festival Special 35-Day Extended Validity", "2026-10-15", "2026-11-25", "MUMBAI EXCLUSIVE", "Active"),
        (13, 3, 8, "Vi Pune Shubh Deepotsav Pack", 449.0, "35 days", "3 GB/day + 40 GB Extra", "Unlimited Calls", "100 SMS/day", "Chitale Bandhu Sweets ₹150 Voucher + Vi Movies & TV + Binge All Night", "Pune Cultural Festive Pack", "2026-10-15", "2026-11-25", "PUNE EXCLUSIVE", "Active"),
        (14, 3, None, "Vi Festive Hero Pack", 488.0, "56 days", "2 GB/day + 60 GB Data Bank", "Unlimited Calls", "100 SMS/day", "Data Delights (Up to 2GB backup every month) + Hungama Music Pro + Binge All Night", "Double Data Festive Bonanza", "2026-10-15", "2026-11-25", "SUPER VALUE", "Active"),
        (15, 3, None, "Vi Mahotsav Annual Celebration", 3199.0, "365 days", "2 GB/day + 75 GB Bonus", "Unlimited Calls", "100 SMS/day", "Sony LIV 1-Year Premium + Binge All Night (Unlimited 12AM-6AM) + Weekend Rollover", "Save ₹800 vs monthly recharges", "2026-10-15", "2026-11-25", "ANNUAL BUMPER", "Active"),

        # ----------------- BSNL DIWALI OFFERS -----------------
        (16, 4, None, "BSNL Diwali Amrit Mahotsav", 199.0, "30 days", "2 GB/day + 15 GB Extra", "Unlimited Calls", "100 SMS/day", "100% Free National Roaming (including Delhi/Mumbai) + ₹25 Free Extra Talktime + Zing Music", "Budget Champion Festive Price", "2026-10-15", "2026-11-25", "DIWALI DHAMAKA", "Active"),
        (17, 4, 7, "BSNL Gujarat Shubh Deepavali", 397.0, "60 days", "2 GB/day + 30 GB Extra", "Unlimited Calls", "100 SMS/day", "Zing Music VIP + Lok-Sangeet Caller Tune + Free PRBT + Sweet Box discount voucher", "2 Months Long Validity Festival Saver", "2026-10-15", "2026-11-25", "GUJARAT EXCLUSIVE", "Active"),
        (18, 4, 1, "BSNL Tamil Nadu Deepavali Tiruvizha", 485.0, "70 days", "1.5 GB/day + 25 GB Extra", "Unlimited Calls", "100 SMS/day", "BSNL Tunes + Hardy Games + 70 Days Full Connectivity", "70 Days extended festive cycle", "2026-10-15", "2026-11-25", "TAMIL NADU EXCLUSIVE", "Active"),
        (19, 4, None, "BSNL Super Diwali Combo 84", 599.0, "84 days", "3 GB/day High Speed", "Unlimited Calls", "100 SMS/day", "Massive 252 GB Total Data + Zing Subscription + Free PRBT + Full National Roaming", "High Data User Diwali Recommendation", "2026-10-15", "2026-11-25", "HIGH DATA", "Active"),
        (20, 4, None, "BSNL Bharat Ratna Diwali Maha Pack", 1999.0, "395 days (365 + 30 Extra)", "600 GB Lumpsum + 100 SMS/day", "Unlimited Calls", "100 SMS/day", "30 Days Extra Festive Validity Free (Total 395 Days) + BSNL Live TV + Free Roaming", "Special 30 Days Free Bonus Validity", "2026-10-15", "2026-11-25", "ANNUAL BUMPER", "Active")
    ]
    cursor.executemany("""
        INSERT INTO diwali_offers (offer_id, operator_id, location_id, offer_name, price, validity, data, voice, sms, bonus, discount, start_date, end_date, badge, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, diwali_offers)

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic telecom operators, circles, plans, customers, and Diwali offers!")

if __name__ == "__main__":
    seed_database()
