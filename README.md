# 🪔 Diwali Telecom Connect & Customer Portal

A professional, responsive, database-driven **Telecom Customer & Diwali Offers Web Application**.

Built with a relational **SQLite database (`telecom.db`)** as the single source of truth for customer information, telecom operator catalogues, base plans, circles, and targeted Diwali festive offers.

---

## 🚀 Quick Access

- **Live Application URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Direct Launcher**: Double-click `start.bat` or run `python run.py`

---

## 📋 Features & Implementation Highlights

### 1. Step 1 — Location Permission Flow
- Immediately displays **“📍 Turn on Location”** card with clear message:
  *“Allow location access to find telecom offers available for your area.”*
- Provides two clear actions:
  - **`Turn On Location`**:
    - Requests browser geolocation (`navigator.geolocation`).
    - Obtains `latitude` and `longitude`.
    - Sends coordinates to backend (`POST /api/location/resolve`).
    - Backend uses Haversine geodesic calculation against the `locations` table to map the user to the closest Indian telecom circle (e.g., Chennai, Delhi, Mumbai, Hyderabad, Bengaluru, etc.).
    - Updates UI status pill to e.g. `📍 Chennai, Tamil Nadu`.
  - **`Continue Without Location`**:
    - Does **not** block the application.
    - Does **not** repeatedly ask for location.
    - Continues directly to customer search/login.
    - Sets location strictly as **“Location not available”**.
    - All national and operator offers remain 100% accessible.

### 2. Step 2 — Customer Search / Login
- Displays **“Find Your Telecom Profile”**.
- Fields:
  - **Mobile Number** (10-digit, formatted with `+91`)
  - **Customer ID** *(Optional)*
  - **Name** *(Optional)*
- Primary button: **“Continue”**
- Secure database flow:
  $$\text{Mobile Number} \xrightarrow{\text{POST /api/customer/search}} \text{Backend API} \xrightarrow{\text{SQL Query}} \text{Database}$$
- **Zero trust for frontend input**: Profile details are strictly resolved from SQLite relational joins on `customers`, `telecom_operators`, and `plans`.

### 3. Step 3 — Customer Data Retrieval
- If the mobile number exists in the database:
  - Header: **“Welcome back, [Customer Name] 🪔”**
  - Displays:
    - **Customer Name**: e.g., `Arun Kumar`
    - **Mobile Number**: Masked for privacy (`98******56`)
    - **Telecom Operator**: Branded operator badge & color (Jio, Airtel, Vi, BSNL)
    - **Current Plan**: Base plan title e.g. `Jio 2 GB/day Super Pack`
    - **Plan Validity**: e.g. `18 days remaining`
    - **Data Remaining**: e.g. `1.4 GB / 2.0 GB left today`
    - **Location**: e.g. `Chennai, Tamil Nadu`
    - **Customer ID**: e.g. `CUST-JIO-101`

### 4. Step 4 — Customer Not Found Flow
- If mobile number does not exist:
  - Displays: **“We couldn't find an existing customer profile.”**
  - Two non-blocking options:
    1. **`Try Another Number`**: Clears search field and focuses.
    2. **`Create New Profile`**: Interactive modal form to register a new user in the database (`POST /api/customer/create`) with chosen operator, plan, and circle, then immediately loads the newly registered profile!
  - No database internals or stack traces are leaked.

### 5. Step 5 — Operator-Specific & Location-Targeted Diwali Offers
- Offers are dynamically queried from the database:
  $$\text{Customer} \to \text{Mobile} \to \text{Database} \to \text{Operator = Jio} \to \text{Location = Chennai} \to \text{Diwali Offers}$$
- **Strict Operator Isolation**:
  - If **Jio** $\implies$ Displays **only Jio** offers.
  - If **Airtel** $\implies$ Displays **only Airtel** offers.
  - If **Vi** $\implies$ Displays **only Vi** offers.
  - If **BSNL** $\implies$ Displays **only BSNL** offers.
- Irrelevant operator offers are **never shown** unless the user explicitly toggles **`Compare All Operators`**.
- **Location-Specific Highlighting**:
  - Regional circle specials (e.g. *Chennai Festive Deepavali Special*, *Delhi-NCR Capital Delight*, *Mumbai Local Express*, *Gujarat Shubh Deepavali*) are highlighted with green `📍 CIRCLE EXCLUSIVE` badges and sorted first, alongside national Pan-India offers.

### 6. Simulated Instant Recharge & Festival Rewards
- Clicking **“Recharge Now 🪔”** triggers `POST /api/recharge`:
  - Records a transaction in `recharge_transactions` table.
  - Extends validity (+28 days) and restores customer data quota in database.
  - Issues a digital receipt modal with Transaction ID, timestamp, and exclusive Diwali sweets gift coupon.

---

## 🗄️ Database Architecture

The application uses **SQLite (`backend/telecom.db`)** with the following tables:

1. **`telecom_operators`**
   - `operator_id`, `operator_name`, `logo`, `brand_color`, `website`, `support_number`, `status`
2. **`locations`**
   - `location_id`, `city`, `district`, `state`, `pincode`, `latitude`, `longitude`
3. **`plans`**
   - `plan_id`, `operator_id`, `plan_name`, `price`, `validity`, `daily_data`, `total_data`, `voice`, `sms`, `ott_benefit`, `status`
4. **`customers`**
   - `customer_id`, `name`, `mobile_number`, `email`, `operator_id`, `plan_id`, `city`, `district`, `state`, `pincode`, `latitude`, `longitude`, `validity_days_remaining`, `data_remaining`, `created_at`
5. **`diwali_offers`**
   - `offer_id`, `operator_id`, `location_id`, `offer_name`, `price`, `validity`, `data`, `voice`, `sms`, `bonus`, `discount`, `start_date`, `end_date`, `badge`, `status`
6. **`recharge_transactions`**
   - `transaction_id`, `customer_id`, `mobile_number`, `offer_id`, `amount`, `payment_method`, `status`, `created_at`
7. **`user_locations` (Turn On Location Audit Log)**
   - `location_log_id`, `session_id`, `customer_id`, `mobile_number`, `latitude`, `longitude`, `resolved_city`, `resolved_district`, `resolved_state`, `resolved_pincode`, `distance_km`, `status`, `created_at`

---

## 🧪 Pre-Seeded Demo Profiles for Quick Testing

You can click any demo profile chip on the web page or test these numbers directly:

| Operator | Customer Name | Mobile Number | Location Circle | Plan |
|---|---|---|---|---|
| **Jio** | Arun Kumar | `9840123456` | Chennai, Tamil Nadu | 2 GB/day Pack (18 days left) |
| **Airtel** | Priya Sharma | `9811234567` | Delhi, NCR | 2 GB/day Pack (7 days left) |
| **Vi** | Rajesh Verma | `9820345678` | Mumbai, Maharashtra | 1.5 GB/day Pack (24 days left) |
| **BSNL** | Sneha Patel | `9426456789` | Ahmedabad, Gujarat | 2 GB/day Pack (2 days left) |
| *Unregistered* | *None* | `9999900000` | *N/A* | Triggers "Profile Not Found" |
