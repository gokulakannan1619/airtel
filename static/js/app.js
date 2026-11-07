/**
 * Telecom Customer & Diwali Offers - Frontend Application Logic
 * Integrates directly with FastAPI backend and SQLite database.
 */

// Application State
const AppState = {
  sessionId: 'SES-' + Math.random().toString(36).substring(2, 10).toUpperCase(),
  locationStatus: 'not_requested', // 'resolved' | 'skipped' | 'denied'
  userLocation: {
    display_name: 'Location not available',
    city: null,
    state: null,
    location_id: null,
    coords: null
  },
  currentCustomer: null,
  isComparingAll: false,
  allOffers: [],
  dbInspectCache: {}
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  loadDemoCustomers();
  preloadBasePlans();
}

/* ==========================================================================
   STEP 1: MANDATORY LOCATION PERMISSION POPUP MODAL FLOW
   ========================================================================== */

function showLocationModal() {
  const modal = document.getElementById('locationPermissionModal');
  if (modal) {
    modal.style.display = 'flex';
  }
}

function closeLocationModal() {
  const modal = document.getElementById('locationPermissionModal');
  if (modal) {
    modal.style.display = 'none';
  }
  const mobileInput = document.getElementById('searchMobile');
  if (mobileInput) {
    mobileInput.focus();
  }
}

/**
 * Handle mandatory "Turn On Location" click from popup
 * First tries real browser GPS. Falls back instantly to network IP if denied/unavailable.
 * Always resolves — never hangs — location is silently stored in DB only.
 */
async function handleTurnOnLocation() {
  const turnBtn = document.getElementById('btnTurnOnLocation');
  const statusNote = document.getElementById('locationPopupStatus');
  if (turnBtn) {
    turnBtn.disabled = true;
    turnBtn.innerHTML = `<span>🛰️ Getting Your Location...</span>`;
  }
  if (statusNote) {
    statusNote.textContent = "Requesting device GPS... please allow when prompted.";
    statusNote.style.color = "#d9480f";
  }

  let locationSaved = false;

  async function storeAndUnlock(lat, lon, accuracy, source) {
    if (locationSaved) return;
    locationSaved = true;

    if (statusNote) {
      statusNote.textContent = source === 'gps'
        ? "GPS acquired! Storing location in database..."
        : "Network location detected. Storing in database...";
      statusNote.style.color = "#2b8a3e";
    }

    try {
      const response = await fetch('/api/location/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lon,
          accuracy: accuracy || 10,
          session_id: AppState.sessionId
        })
      });
      const data = await response.json();

      if (data.resolved) {
        AppState.locationStatus = 'resolved';
        AppState.userLocation.city = data.city;
        AppState.userLocation.state = data.state;
        AppState.userLocation.locality = data.locality;
        AppState.userLocation.exact_address = data.exact_address;
        AppState.userLocation.pincode = data.pincode;
        AppState.userLocation.location_id = data.location_id;
        AppState.userLocation.coords = { lat, lon, accuracy };
      } else {
        // Even if resolve fails, mark as resolved so user isn't stuck
        AppState.locationStatus = 'resolved';
        AppState.userLocation.coords = { lat, lon, accuracy };
      }
    } catch (err) {
      console.error("Location store error:", err);
      // Network error — still let the user through
      AppState.locationStatus = 'resolved';
      AppState.userLocation.coords = { lat, lon, accuracy };
    }

    // Always close the modal
    closeLocationModal();
  }

  async function fallbackToNetworkIP() {
    try {
      const fbRes = await fetch('/api/location/auto-ip');
      const fbData = await fbRes.json();
      if (fbData && fbData.latitude) {
        await storeAndUnlock(fbData.latitude, fbData.longitude, 500, 'network-ip');
        return;
      }
    } catch (e) {
      console.warn("Network IP lookup failed:", e);
    }
    // Last resort: use Chennai coords
    await storeAndUnlock(13.0827, 80.2707, 1000, 'default');
  }

  // 1. Try real browser Geolocation API
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        // SUCCESS — real GPS coordinates
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const accuracy = position.coords.accuracy ? Math.round(position.coords.accuracy) : 10;
        await storeAndUnlock(lat, lon, accuracy, 'gps');
      },
      async (error) => {
        // DENIED or UNAVAILABLE — show guide then instantly fall back to network IP
        console.warn("GPS denied/unavailable (code=" + error.code + "):", error.message);
        const guide = document.getElementById('locationPermissionGuide');
        if (guide && error.code === 1) {
          // code 1 = PERMISSION_DENIED — show instruction panel
          guide.style.display = 'block';
        }
        if (statusNote) {
          statusNote.textContent = error.code === 1
            ? "GPS blocked. Using network location automatically..."
            : "GPS unavailable — using network location...";
          statusNote.style.color = "#f76707";
        }
        await fallbackToNetworkIP();
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );

    // Hard timeout: if the browser permission prompt hangs beyond 10s, use fallback
    setTimeout(async () => {
      if (!locationSaved) {
        console.warn("Location permission prompt timed out — using network fallback");
        if (statusNote) {
          statusNote.textContent = "Timed out — switching to network location...";
          statusNote.style.color = "#f76707";
        }
        await fallbackToNetworkIP();
      }
    }, 10000);
  } else {
    // Browser doesn't support geolocation at all
    console.warn("Browser does not support navigator.geolocation");
    if (statusNote) {
      statusNote.textContent = "GPS not supported — using network location...";
    }
    await fallbackToNetworkIP();
  }
}

// DEAD CODE BELOW (old implementation kept for reference — remove after testing)
async function _OLD_handleTurnOnLocation_UNUSED() {
  const turnBtn = document.getElementById('btnTurnOnLocation');
  const statusNote = document.getElementById('locationPopupStatus');
  if (turnBtn) {
    turnBtn.disabled = true;
    turnBtn.innerHTML = `<span>🛰️ Activating Location & Storing in DB...</span>`;
  }
  if (statusNote) {
    statusNote.textContent = "Connecting to device sensors and telecom database...";
    statusNote.style.color = "#d9480f";
  }

  let locationSaved = false;

  async function storeAndUnlock(lat, lon, accuracy) {
    if (locationSaved) return;
    locationSaved = true;

    try {
      const response = await fetch('/api/location/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          latitude: lat, 
          longitude: lon,
          accuracy: accuracy || 10,
          session_id: AppState.sessionId
        })
      });
      const data = await response.json();

      if (data.resolved) {
        AppState.locationStatus = 'resolved';
        AppState.userLocation.city = data.city;
        AppState.userLocation.state = data.state;
        AppState.userLocation.locality = data.locality;
        AppState.userLocation.exact_address = data.exact_address;
        AppState.userLocation.pincode = data.pincode;
        AppState.userLocation.location_id = data.location_id;
        AppState.userLocation.coords = { lat, lon, accuracy };
      }
    } catch (err) {
      console.error("Location store error:", err);
    }

    // Modal closes upon successful activation and storage
    closeLocationModal();
  }

  // 1. Try browser Geolocation API
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const accuracy = position.coords.accuracy ? Math.round(position.coords.accuracy) : 10;
        storeAndUnlock(lat, lon, accuracy);
      },
      async (error) => {
        console.warn("Browser GPS unavailable or timed out, using network location fallback:", error.message);
        // Fallback to real network IP location
        try {
          const fbRes = await fetch('/api/location/auto-ip');
          const fbData = await fbRes.json();
          if (fbData && fbData.latitude) {
            storeAndUnlock(fbData.latitude, fbData.longitude, 25);
            return;
          }
        } catch (e) {}
        storeAndUnlock(13.0827, 80.2707, 50);
      },
      { enableHighAccuracy: true, timeout: 6000, maximumAge: 60000 }
    );

    // Safety timeout in case browser prompt hangs
    setTimeout(async () => {
      if (!locationSaved) {
        try {
          const fbRes = await fetch('/api/location/auto-ip');
          const fbData = await fbRes.json();
          if (fbData && fbData.latitude) {
            storeAndUnlock(fbData.latitude, fbData.longitude, 25);
            return;
          }
        } catch (e) {}
        storeAndUnlock(13.0827, 80.2707, 50);
      }
    }, 6500);
  } else {
    // Geolocation not supported by browser
    try {
      const fbRes = await fetch('/api/location/auto-ip');
      const fbData = await fbRes.json();
      if (fbData && fbData.latitude) {
        storeAndUnlock(fbData.latitude, fbData.longitude, 25);
        return;
      }
    } catch (e) {}
    storeAndUnlock(13.0827, 80.2707, 50);
  }
}

/* ==========================================================================
   STEP 2: CUSTOMER SEARCH / LOGIN FLOW
   ========================================================================== */

/**
 * Handle Customer Search Form Submit
 */
async function handleCustomerSearch(e) {
  if (e) e.preventDefault();

  // Enforce mandatory location turn on
  if (AppState.locationStatus !== 'resolved') {
    showLocationModal();
    alert("Please turn on location first to proceed with telecom login.");
    return;
  }

  const mobileInput = document.getElementById('searchMobile');
  const custIdInput = document.getElementById('searchCustId');
  const nameInput = document.getElementById('searchName');
  const operatorSelect = document.getElementById('searchOperator');
  const submitBtn = document.getElementById('btnContinueSearch');

  const mobile = mobileInput.value.replace(/\D/g, '');
  if (mobile.length !== 10) {
    alert("Please enter a valid 10-digit Indian mobile number.");
    mobileInput.focus();
    return;
  }

  // Set loading state
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>Searching Database...</span>`;

  try {
    const payload = {
      mobile_number: mobile,
      customer_id: custIdInput ? custIdInput.value.trim() || null : null,
      name: nameInput.value.trim() || null,
      operator_hint: operatorSelect ? operatorSelect.value || null : null,
      session_id: AppState.sessionId,
      latitude: AppState.userLocation.coords ? AppState.userLocation.coords.lat : null,
      longitude: AppState.userLocation.coords ? AppState.userLocation.coords.lon : null,
      resolved_city: AppState.userLocation.city
    };

    let res = await fetch('/api/customer/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    let data = await res.json();

    // If not found in existing DB, automatically register this user into DB!
    if (!data.found) {
      console.log("Customer not found in DB. Auto-registering name, number, SIM type & GPS location into DB...");
      const regRes = await fetch('/api/customer/auto-register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      data = await regRes.json();
    }

    if (data.found && data.customer) {
      // Customer Loaded or Auto-Registered!
      AppState.currentCustomer = data.customer;

      // If user had not resolved GPS location, inherit the customer's registered circle!
      if (AppState.userLocation.display_name === 'Location not available' && data.customer.location_display) {
        AppState.userLocation.city = data.customer.city;
        AppState.userLocation.state = data.customer.state;
        AppState.userLocation.location_id = data.customer.location_id;
        AppState.userLocation.display_name = data.customer.location_display;
      }

      displayCustomerProfile(data.customer);
      await fetchAndRenderDiwaliOffers();
      
      // Hide search & not-found card
      document.getElementById('customerSearchCard').style.display = 'none';
      document.getElementById('customerNotFoundCard').style.display = 'none';
      
      // Scroll to profile
      document.getElementById('customerProfileCard').scrollIntoView({ behavior: 'smooth' });
    } else {
      // Customer NOT Found!
      handleCustomerNotFound(mobile, data.message);
    }
  } catch (err) {
    console.error("Search API Error:", err);
    alert("Unable to reach the customer database server. Please check backend connection.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Continue</span><span>➔</span>`;
  }
}

/**
 * Display Customer Profile Data
 */
function displayCustomerProfile(customer) {
  const profileCard = document.getElementById('customerProfileCard');
  
  document.getElementById('welcomeGreeting').textContent = `Welcome back, ${customer.name} 🪔`;
  document.getElementById('dispCustName').textContent = customer.name;
  document.getElementById('dispCustId').textContent = `ID: ${customer.customer_id}`;
  document.getElementById('dispCustMobile').textContent = customer.masked_mobile;
  document.getElementById('dispCurrentPlan').textContent = customer.plan_name;
  document.getElementById('dispValidity').textContent = customer.plan_validity;
  document.getElementById('dispDataRemaining').textContent = customer.data_remaining;

  // Set Operator badge
  const opBadge = document.getElementById('profileOperatorBadge');
  const badgeName = document.getElementById('badgeOpName');
  badgeName.textContent = customer.operator_name;

  opBadge.className = 'profile-op-badge';
  const opLower = customer.operator_name.toLowerCase();
  if (opLower.includes('jio')) opBadge.classList.add('jio');
  else if (opLower.includes('airtel')) opBadge.classList.add('airtel');
  else if (opLower.includes('vi')) opBadge.classList.add('vi');
  else if (opLower.includes('bsnl')) opBadge.classList.add('bsnl');

  profileCard.style.display = 'block';
}

/**
 * Handle Customer Not Found State
 */
function handleCustomerNotFound(mobile, msg) {
  AppState.currentCustomer = null;
  document.getElementById('customerProfileCard').style.display = 'none';
  document.getElementById('diwaliOffersSection').style.display = 'none';

  const notFoundCard = document.getElementById('customerNotFoundCard');
  const notFoundMsg = document.getElementById('notFoundMsg');
  
  notFoundMsg.textContent = msg || `No customer profile was found matching mobile number +91 ${mobile} in our telecom database.`;
  notFoundCard.style.display = 'block';

  // Store entered mobile into modal for easy quick registration
  document.getElementById('newMobile').value = mobile;
}

/**
 * Reset search input and focus
 */
function resetSearchInput() {
  document.getElementById('customerNotFoundCard').style.display = 'none';
  document.getElementById('customerSearchCard').style.display = 'block';
  const input = document.getElementById('searchMobile');
  input.value = '';
  input.focus();
}

/**
 * Switch customer / search another
 */
function switchCustomer() {
  AppState.currentCustomer = null;
  AppState.isComparingAll = false;
  document.getElementById('customerProfileCard').style.display = 'none';
  document.getElementById('diwaliOffersSection').style.display = 'none';
  document.getElementById('customerNotFoundCard').style.display = 'none';
  
  const searchCard = document.getElementById('customerSearchCard');
  searchCard.style.display = 'block';
  searchCard.scrollIntoView({ behavior: 'smooth' });
}

/* ==========================================================================
   STEP 3: TELECOM OPERATOR-BASED & LOCATION-BASED OFFERS
   ========================================================================== */

/**
 * Fetch offers from database dynamically
 * Rule: Show only the customer's operator offers unless user explicitly compares!
 */
async function fetchAndRenderDiwaliOffers() {
  if (!AppState.currentCustomer) return;

  const section = document.getElementById('diwaliOffersSection');
  const title = document.getElementById('offersTitle');
  const subtitle = document.getElementById('offersSubtitle');
  const grid = document.getElementById('offersGridContainer');
  const compareBtn = document.getElementById('btnToggleCompare');
  const compareText = document.getElementById('compareToggleText');

  grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #7c1a06;">
    <div style="font-size: 32px; animation: pulseDiya 1.5s infinite;">🪔</div>
    <p style="margin-top: 10px; font-weight: 700;">Querying active Diwali offers from database...</p>
  </div>`;
  section.style.display = 'block';

  const operatorId = AppState.currentCustomer.operator_id;
  const operatorName = AppState.currentCustomer.operator_name;
  const city = AppState.userLocation.city || AppState.currentCustomer.city;
  const locationId = AppState.userLocation.location_id || AppState.currentCustomer.location_id;

  let url = `/api/offers?compare_all=${AppState.isComparingAll}`;
  if (!AppState.isComparingAll) {
    url += `&operator_id=${operatorId}`;
  }
  if (locationId) {
    url += `&location_id=${locationId}`;
  } else if (city && city.toLowerCase() !== 'location not available') {
    url += `&city=${encodeURIComponent(city)}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();
    AppState.allOffers = data.offers || [];

    // Header texts
    if (AppState.isComparingAll) {
      title.innerHTML = `✨ All Telecom Operators Diwali Comparison ✨`;
      subtitle.textContent = `Comparing festive plans across Jio, Airtel, Vi, and BSNL based on live database tariffs.`;
      compareBtn.classList.add('active');
      compareText.textContent = `Show Only My Operator (${operatorName})`;
    } else {
      title.innerHTML = `✨ Recommended ${operatorName} Diwali Offers for You`;
      subtitle.textContent = `Exclusively filtered for ${operatorName} subscribers based on your account profile.`;
      compareBtn.classList.remove('active');
      compareText.textContent = `Compare All Operators`;
    }

    renderOfferCards(AppState.allOffers);
  } catch (err) {
    console.error("Offers Fetch Error:", err);
    grid.innerHTML = `<p style="grid-column: 1/-1; color: red; text-align: center;">Failed to load offers from database.</p>`;
  }
}

/**
 * Toggle Compare All Operators
 */
function toggleCompareOperators() {
  AppState.isComparingAll = !AppState.isComparingAll;
  fetchAndRenderDiwaliOffers();
}

/**
 * Render offer cards into grid
 */
function renderOfferCards(offers) {
  const grid = document.getElementById('offersGridContainer');
  grid.innerHTML = '';

  if (!offers || offers.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; background: white; border-radius: 16px;">
        <h3>No active Diwali offers found for the selected criteria.</h3>
        <p style="color: #666; margin-top: 8px;">Check back soon as new festival packs are constantly added to the database.</p>
      </div>
    `;
    return;
  }

  offers.forEach(offer => {
    const isLocExclusive = offer.is_location_exclusive;
    const badgeText = isLocExclusive 
      ? '🌟 FESTIVE BONUS PACK' 
      : (offer.badge || 'DIWALI SPECIAL');

    const card = document.createElement('article');
    card.className = `offer-card ${isLocExclusive ? 'exclusive' : ''}`;

    card.innerHTML = `
      <span class="offer-badge ${isLocExclusive ? 'loc-badge' : ''}">${badgeText}</span>
      
      <div class="offer-operator-row">
        <span class="op-dot ${offer.operator_name.toLowerCase()}"></span>
        <span class="offer-op-tag">${offer.operator_name}</span>
      </div>

      <h3 class="offer-title">${offer.offer_name}</h3>

      <div class="offer-price-row">
        <span class="offer-price">₹${Math.round(offer.price)}</span>
        <span class="offer-validity">⏱️ ${offer.validity}</span>
      </div>

      <ul class="offer-benefits-list">
        <li><span class="benefit-bullet">✓</span> <strong>Data:</strong> ${offer.data}</li>
        <li><span class="benefit-bullet">✓</span> <strong>Voice:</strong> ${offer.voice}</li>
        <li><span class="benefit-bullet">✓</span> <strong>SMS:</strong> ${offer.sms}</li>
        ${offer.discount ? `<li><span class="benefit-bullet">🏷️</span> <span style="color:#d9480f; font-weight:700;">${offer.discount}</span></li>` : ''}
      </ul>

      <div class="offer-bonus-box">
        <div class="bonus-label">🪔 Diwali Bonus Perks:</div>
        <div class="bonus-text">${offer.bonus}</div>
      </div>

      <button type="button" class="btn-recharge" onclick="triggerRecharge(${offer.offer_id}, ${offer.price}, '${escapeJsString(offer.offer_name)}')">
        <span>Recharge Now 🪔</span>
      </button>
    `;

    grid.appendChild(card);
  });
}

function escapeJsString(str) {
  return str.replace(/'/g, "\\'");
}

/* ==========================================================================
   STEP 4: INSTANT RECHARGE & FESTIVE REWARD SIMULATION
   ========================================================================== */

async function triggerRecharge(offerId, amount, offerName) {
  if (!AppState.currentCustomer) {
    alert("Please search your customer profile first.");
    return;
  }

  const confirmRecharge = confirm(`Confirm Diwali recharge of ₹${amount} for ${AppState.currentCustomer.name} (${AppState.currentCustomer.masked_mobile})?\n\nPlan: ${offerName}`);
  if (!confirmRecharge) return;

  try {
    const payload = {
      customer_id: AppState.currentCustomer.customer_id,
      mobile_number: AppState.currentCustomer.raw_mobile,
      offer_id: offerId,
      amount: amount,
      payment_method: 'UPI / Festive Gateway'
    };

    const res = await fetch('/api/recharge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const receipt = await res.json();

    if (receipt.success) {
      // Show receipt modal
      const box = document.getElementById('receiptBoxContent');
      box.innerHTML = `
        <div class="receipt-row">
          <span>Transaction ID:</span>
          <span style="font-family: monospace; color:#d9480f;">${receipt.transaction_id}</span>
        </div>
        <div class="receipt-row">
          <span>Customer:</span>
          <span>${AppState.currentCustomer.name}</span>
        </div>
        <div class="receipt-row">
          <span>Mobile Number:</span>
          <span>${AppState.currentCustomer.masked_mobile}</span>
        </div>
        <div class="receipt-row">
          <span>Telecom Operator:</span>
          <span>${receipt.operator_name}</span>
        </div>
        <div class="receipt-row">
          <span>Offer Applied:</span>
          <span>${receipt.offer_name}</span>
        </div>
        <div class="receipt-row">
          <span>Amount Paid:</span>
          <span style="font-size:16px; color:#2b8a3e;">₹${receipt.recharge_amount}</span>
        </div>
        <div class="receipt-row">
          <span>Validity Added:</span>
          <span>${receipt.validity}</span>
        </div>
        <div class="receipt-row">
          <span>Data Benefit:</span>
          <span>${receipt.data_benefit}</span>
        </div>
        <div class="receipt-row">
          <span>Bonus Perks:</span>
          <span style="font-size:12px; max-width:240px; text-align:right;">${receipt.bonus_perks}</span>
        </div>
        <div class="receipt-row">
          <span>Date & Time:</span>
          <span>${receipt.timestamp}</span>
        </div>
      `;

      document.getElementById('dispCouponCode').textContent = receipt.festive_coupon;
      document.getElementById('rechargeSuccessModal').style.display = 'flex';

      // Refresh customer data from database
      const custRes = await fetch('/api/customer/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mobile_number: AppState.currentCustomer.raw_mobile })
      });
      const custData = await custRes.json();
      if (custData.found) {
        AppState.currentCustomer = custData.customer;
        displayCustomerProfile(custData.customer);
      }
    } else {
      alert("Recharge simulation failed.");
    }
  } catch (err) {
    console.error("Recharge error:", err);
    alert("Recharge processing failed. Please check backend connection.");
  }
}

function closeRechargeModal() {
  document.getElementById('rechargeSuccessModal').style.display = 'none';
}

/* ==========================================================================
   MODAL: CREATE NEW CUSTOMER PROFILE
   ========================================================================== */

function openCreateCustomerModal() {
  document.getElementById('createProfileModal').style.display = 'flex';
}

function closeCreateCustomerModal() {
  document.getElementById('createProfileModal').style.display = 'none';
}

async function handleCreateCustomerSubmit(e) {
  e.preventDefault();

  const name = document.getElementById('newName').value.trim();
  const mobile = document.getElementById('newMobile').value.trim().replace(/\D/g, '');
  const email = document.getElementById('newEmail').value.trim();
  const operatorId = parseInt(document.getElementById('newOperator').value);
  const city = document.getElementById('newCity').value;
  const planId = parseInt(document.getElementById('newBasePlan').value) || null;

  if (mobile.length !== 10) {
    alert("Mobile number must be 10 digits.");
    return;
  }

  const payload = {
    name,
    mobile_number: mobile,
    email: email || `${name.toLowerCase().replace(/\s+/g, '')}@example.com`,
    operator_id: operatorId,
    city,
    district: city,
    state: getStateForCity(city),
    pincode: '600001',
    plan_id: planId
  };

  try {
    const res = await fetch('/api/customer/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Failed to create customer profile.");
      return;
    }

    closeCreateCustomerModal();
    alert(`🎉 Customer Profile Created Successfully in Telecom Database!\n\nCustomer ID: ${data.customer.customer_id}`);

    // Load new profile immediately
    AppState.currentCustomer = data.customer;
    displayCustomerProfile(data.customer);
    await fetchAndRenderDiwaliOffers();

    document.getElementById('customerSearchCard').style.display = 'none';
    document.getElementById('customerNotFoundCard').style.display = 'none';
    document.getElementById('customerProfileCard').scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    console.error("Create profile error:", err);
    alert("Failed to submit profile to backend.");
  }
}

function getStateForCity(city) {
  const map = {
    'Chennai': 'Tamil Nadu',
    'Delhi': 'Delhi',
    'Mumbai': 'Maharashtra',
    'Bengaluru': 'Karnataka',
    'Hyderabad': 'Telangana',
    'Kolkata': 'West Bengal',
    'Ahmedabad': 'Gujarat',
    'Pune': 'Maharashtra'
  };
  return map[city] || 'India';
}

async function loadOperatorPlans(operatorId) {
  if (!operatorId) return;
  const select = document.getElementById('newBasePlan');
  select.innerHTML = '<option>Loading plans from database...</option>';

  try {
    const res = await fetch(`/api/plans?operator_id=${operatorId}`);
    const plans = await res.json();
    select.innerHTML = '';
    plans.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.plan_id;
      opt.textContent = `${p.plan_name} (₹${p.price} / ${p.validity} - ${p.daily_data})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Plans fetch error:", err);
  }
}

async function preloadBasePlans() {
  loadOperatorPlans(1); // default Jio
}

/* ==========================================================================
   DEMO HELPERS & DATABASE INSPECTOR
   ========================================================================== */

function fillDemoCustomer(mobile) {
  const input = document.getElementById('searchMobile');
  const operatorSel = document.getElementById('searchOperator');
  const nameInput = document.getElementById('searchName');
  if (input) {
    input.value = mobile;
    // Reset optional fields
    if (operatorSel) operatorSel.value = '';
    if (nameInput) nameInput.value = '';
    handleCustomerSearch();
  }
}

async function loadDemoCustomers() {
  try {
    const res = await fetch('/api/demo-customers');
    const list = await res.json();
    const container = document.getElementById('demoChipsContainer');
    if (!container || !list || list.length === 0) return;

    container.innerHTML = '';
    list.forEach(c => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip-btn';
      btn.onclick = () => fillDemoCustomer(c.mobile_number);

      const opClass = c.operator_name.toLowerCase();
      btn.innerHTML = `<span class="op-dot ${opClass}"></span> <strong>${c.operator_name}:</strong> ${c.name} (${c.city})`;
      container.appendChild(btn);
    });

    // Add unregistered test number chip
    const unregBtn = document.createElement('button');
    unregBtn.type = 'button';
    unregBtn.className = 'chip-btn unregistered';
    unregBtn.onclick = () => fillDemoCustomer('9999900000');
    unregBtn.innerHTML = `<span>❓</span> <em>Test Unregistered Number</em>`;
    container.appendChild(unregBtn);
  } catch (err) {
    console.warn("Could not load dynamic demo customers:", err);
  }
}

/**
 * Live Database Inspector Modal
 */
let currentDbTab = 'customers';

function openDatabaseInspector() {
  document.getElementById('databaseInspectorModal').style.display = 'flex';
  switchDbTab(currentDbTab);
}

function closeDatabaseInspector() {
  document.getElementById('databaseInspectorModal').style.display = 'none';
}

async function switchDbTab(tabName) {
  currentDbTab = tabName;
  
  // Highlight active tab
  document.querySelectorAll('.db-tab-btn').forEach(b => {
    b.classList.remove('active');
    if (b.textContent.toLowerCase().includes(tabName.replace('_', ' '))) {
      b.classList.add('active');
    }
  });

  const wrapper = document.getElementById('dbTableWrapper');
  wrapper.innerHTML = `<div style="padding: 24px; text-align: center; color: #888;">Fetching live records from table <code>${tabName}</code>...</div>`;

  try {
    let endpoint = '';
    if (tabName === 'customers') endpoint = '/api/customers';
    else if (tabName === 'user_locations') endpoint = '/api/location/logs';
    else if (tabName === 'diwali_offers') endpoint = '/api/offers?compare_all=true';
    else if (tabName === 'telecom_operators') endpoint = '/api/operators';
    else if (tabName === 'plans') endpoint = '/api/plans';
    else if (tabName === 'locations') endpoint = '/api/locations';

    const res = await fetch(endpoint);
    const data = await res.json();
    const rows = Array.isArray(data) ? data : (data.offers || []);

    if (!rows || rows.length === 0) {
      wrapper.innerHTML = `<div style="padding: 20px;">No records found in table.</div>`;
      return;
    }

    const keys = Object.keys(rows[0]);
    let html = `<table class="db-table"><thead><tr>`;
    keys.forEach(k => { html += `<th>${k.replace('_', ' ')}</th>`; });
    html += `</tr></thead><tbody>`;

    rows.forEach(r => {
      html += `<tr>`;
      keys.forEach(k => {
        let val = r[k];
        if (k === 'google_maps_link' && val) {
          html += `<td><a href="${val}" target="_blank" rel="noopener noreferrer" style="color:#d9480f; font-weight:700; text-decoration:underline;">📍 View on Google Maps</a></td>`;
        } else {
          if (typeof val === 'string' && val.length > 50) val = val.substring(0, 48) + '...';
          html += `<td>${val !== null && val !== undefined ? val : '<em>NULL</em>'}</td>`;
        }
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;

    wrapper.innerHTML = html;
  } catch (err) {
    wrapper.innerHTML = `<div style="padding: 20px; color: red;">Failed to inspect table: ${err.message}</div>`;
  }
}
