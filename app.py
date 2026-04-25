import re
import sqlite3
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = Path("novo_real_estate_agent.db")

AGENCY = {
    "name": "Novo Demo Realty",
    "email": "bookings@novodemo.co.za",
    "phone": "+27 11 000 1234",
    "whatsapp": "+27 78 660 8755",
    "address": "Remote-first real estate operations desk",
}

DEFAULT_HUMAN_AGENT = {
    "name": "Alicia Mokoena",
    "title": "Senior Property Consultant",
    "email": "alicia.mokoena@novodemo.co.za",
    "phone": "+27 82 555 0148",
    "whatsapp": "+27 82 555 0148",
}

KNOWN_LOCATIONS = [
    "claremont",
    "rondebosch",
    "sandton",
    "bryanston",
    "hatfield",
    "midrand",
    "sea point",
    "bloemfontein",
    "cape town",
    "johannesburg",
    "pretoria",
    "durban",
]

PROPERTY_TYPES = ["apartment", "flat", "house", "townhouse"]

ORDINALS = {
    "first": 0,
    "1st": 0,
    "one": 0,
    "second": 1,
    "2nd": 1,
    "two": 1,
    "third": 2,
    "3rd": 2,
    "three": 2,
}


# ============================================================
# DATABASE HELPERS
# ============================================================

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql: str, params: Tuple[Any, ...] = ()) -> int:
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return int(last_id or 0)


def fetchone(sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


def query_df(sql: str, params: Tuple[Any, ...] = ()) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT DEFAULT 'Demo Lead',
            email TEXT,
            phone TEXT,
            source TEXT DEFAULT 'streamlit_demo',
            intent TEXT,
            location TEXT,
            property_type TEXT,
            bedrooms INTEGER,
            budget REAL,
            timeline TEXT,
            selected_property_id INTEGER,
            lead_score INTEGER DEFAULT 0,
            lead_stage TEXT DEFAULT 'new',
            assigned_agent_name TEXT,
            assigned_agent_email TEXT,
            assigned_agent_phone TEXT,
            human_handoff_required INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            location TEXT,
            price REAL,
            property_type TEXT,
            listing_type TEXT,
            bedrooms INTEGER,
            bathrooms INTEGER,
            size_sqm INTEGER,
            availability_status TEXT,
            listing_url TEXT,
            viewing_address TEXT,
            agent_name TEXT,
            agent_email TEXT,
            agent_phone TEXT,
            agent_whatsapp TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            property_id INTEGER,
            requested_time TEXT,
            client_name TEXT,
            client_email TEXT,
            client_phone TEXT,
            assigned_agent_name TEXT,
            assigned_agent_email TEXT,
            assigned_agent_phone TEXT,
            status TEXT DEFAULT 'requested',
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            action_type TEXT,
            payload TEXT,
            status TEXT DEFAULT 'success',
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            appointment_id INTEGER,
            channel TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            status TEXT,
            provider_response TEXT,
            created_at TEXT
        )
        """
    )

    conn.commit()
    seed_properties(conn)
    conn.close()


def seed_properties(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS c FROM properties").fetchone()["c"]
    if existing > 0:
        return

    synthetic_properties = [
        {
            "id": 1,
            "title": "Modern 2 Bedroom Apartment in Claremont",
            "description": "Secure apartment near shops, schools and public transport. Ideal for young professionals.",
            "location": "Claremont",
            "price": 12500,
            "property_type": "apartment",
            "listing_type": "rent",
            "bedrooms": 2,
            "bathrooms": 1,
            "size_sqm": 74,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/claremont-2-bed-rental",
            "viewing_address": "12 Grove Avenue, Claremont, Cape Town",
        },
        {
            "id": 2,
            "title": "Spacious 2 Bedroom Apartment in Rondebosch",
            "description": "Bright apartment close to UCT and major routes, with secure parking.",
            "location": "Rondebosch",
            "price": 11800,
            "property_type": "apartment",
            "listing_type": "rent",
            "bedrooms": 2,
            "bathrooms": 1,
            "size_sqm": 69,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/rondebosch-2-bed-rental",
            "viewing_address": "8 Belmont Road, Rondebosch, Cape Town",
        },
        {
            "id": 3,
            "title": "Family 3 Bedroom House in Sandton",
            "description": "Well-positioned family home with garden, double garage and entertainment area.",
            "location": "Sandton",
            "price": 2450000,
            "property_type": "house",
            "listing_type": "buy",
            "bedrooms": 3,
            "bathrooms": 2,
            "size_sqm": 220,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/sandton-3-bed-house",
            "viewing_address": "24 Oak Lane, Sandton, Johannesburg",
        },
        {
            "id": 4,
            "title": "Luxury 4 Bedroom House in Bryanston",
            "description": "Executive home with pool, staff quarters, smart security and premium finishes.",
            "location": "Bryanston",
            "price": 4200000,
            "property_type": "house",
            "listing_type": "buy",
            "bedrooms": 4,
            "bathrooms": 3,
            "size_sqm": 390,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/bryanston-luxury-house",
            "viewing_address": "5 Cedar Close, Bryanston, Johannesburg",
        },
        {
            "id": 5,
            "title": "Affordable 1 Bedroom Flat in Hatfield",
            "description": "Student-friendly flat close to campus and Gautrain routes.",
            "location": "Hatfield",
            "price": 7200,
            "property_type": "flat",
            "listing_type": "rent",
            "bedrooms": 1,
            "bathrooms": 1,
            "size_sqm": 42,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/hatfield-1-bed-flat",
            "viewing_address": "16 Burnett Street, Hatfield, Pretoria",
        },
        {
            "id": 6,
            "title": "3 Bedroom Townhouse in Midrand",
            "description": "Pet-friendly townhouse in a secure estate with fibre and backup power.",
            "location": "Midrand",
            "price": 1750000,
            "property_type": "townhouse",
            "listing_type": "buy",
            "bedrooms": 3,
            "bathrooms": 2,
            "size_sqm": 148,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/midrand-townhouse",
            "viewing_address": "33 Maple Estate, Midrand, Johannesburg",
        },
        {
            "id": 7,
            "title": "Premium 2 Bedroom Apartment in Sea Point",
            "description": "Ocean-facing apartment with security, balcony and parking.",
            "location": "Sea Point",
            "price": 22500,
            "property_type": "apartment",
            "listing_type": "rent",
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqm": 88,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/sea-point-apartment",
            "viewing_address": "45 Beach Road, Sea Point, Cape Town",
        },
        {
            "id": 8,
            "title": "Starter 2 Bedroom House in Bloemfontein",
            "description": "Affordable family starter home near schools and shopping centres.",
            "location": "Bloemfontein",
            "price": 950000,
            "property_type": "house",
            "listing_type": "buy",
            "bedrooms": 2,
            "bathrooms": 1,
            "size_sqm": 140,
            "availability_status": "available",
            "listing_url": "https://demo.local/listings/bloemfontein-starter-home",
            "viewing_address": "9 Nelson Mandela Drive, Bloemfontein",
        },
    ]

    for prop in synthetic_properties:
        conn.execute(
            """
            INSERT INTO properties (
                id, title, description, location, price, property_type, listing_type,
                bedrooms, bathrooms, size_sqm, availability_status, listing_url,
                viewing_address, agent_name, agent_email, agent_phone, agent_whatsapp
            )
            VALUES (
                :id, :title, :description, :location, :price, :property_type, :listing_type,
                :bedrooms, :bathrooms, :size_sqm, :availability_status, :listing_url,
                :viewing_address, :agent_name, :agent_email, :agent_phone, :agent_whatsapp
            )
            """,
            {
                **prop,
                "agent_name": DEFAULT_HUMAN_AGENT["name"],
                "agent_email": DEFAULT_HUMAN_AGENT["email"],
                "agent_phone": DEFAULT_HUMAN_AGENT["phone"],
                "agent_whatsapp": DEFAULT_HUMAN_AGENT["whatsapp"],
            },
        )

    conn.commit()


def ensure_active_lead() -> int:
    lead_id = st.session_state.get("lead_id")

    if lead_id:
        row = fetchone("SELECT id FROM leads WHERE id = ?", (lead_id,))
        if row:
            return int(row["id"])

    new_id = execute(
        """
        INSERT INTO leads (
            full_name, email, phone, source,
            assigned_agent_name, assigned_agent_email, assigned_agent_phone,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Demo Lead",
            "",
            "",
            "streamlit_demo",
            DEFAULT_HUMAN_AGENT["name"],
            DEFAULT_HUMAN_AGENT["email"],
            DEFAULT_HUMAN_AGENT["phone"],
            now(),
            now(),
        ),
    )

    st.session_state["lead_id"] = new_id
    return new_id


def reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    init_db()


# ============================================================
# AGENT MEMORY AND CRM HELPERS
# ============================================================

def add_message(lead_id: int, role: str, content: str) -> None:
    execute(
        """
        INSERT INTO messages (lead_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (lead_id, role, content, now()),
    )


def log_action(
    lead_id: int,
    action_type: str,
    payload: str,
    status: str = "success",
) -> None:
    execute(
        """
        INSERT INTO agent_actions (lead_id, action_type, payload, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (lead_id, action_type, payload, status, now()),
    )


def get_current_lead(lead_id: int) -> sqlite3.Row:
    row = fetchone("SELECT * FROM leads WHERE id = ?", (lead_id,))
    if row is None:
        raise RuntimeError("Lead not found")
    return row


def get_latest_appointment(lead_id: int) -> Optional[sqlite3.Row]:
    return fetchone(
        """
        SELECT * FROM appointments
        WHERE lead_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (lead_id,),
    )


# ============================================================
# EXTRACTION TOOLS
# ============================================================

def extract_contact_details(message: str) -> Dict[str, str]:
    data: Dict[str, str] = {}

    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message)
    if email_match:
        data["email"] = email_match.group(0).strip()

    phone_match = re.search(r"(\+?\d[\d\s\-]{7,}\d)", message)
    if phone_match:
        data["phone"] = phone_match.group(1).strip()

    name_match = re.search(
        r"(?:my name is|i am|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        message,
        flags=re.IGNORECASE,
    )
    if name_match:
        data["full_name"] = name_match.group(1).strip().title()

    return data


def extract_lead_preferences(message: str) -> Dict[str, Any]:
    """
    Deterministic extractor for a free public demo.
    In production, replace this with LLM structured output.
    """
    text = message.lower()
    data: Dict[str, Any] = {}

    if any(word in text for word in ["rent", "rental", "lease"]):
        data["intent"] = "rent"
    elif any(word in text for word in ["buy", "purchase", "own"]):
        data["intent"] = "buy"
    elif any(word in text for word in ["sell", "valuation", "list my property"]):
        data["intent"] = "sell"

    for location in KNOWN_LOCATIONS:
        if location in text:
            data["location"] = location.title()

    for property_type in PROPERTY_TYPES:
        if property_type in text:
            data["property_type"] = property_type

    bedroom_match = re.search(r"(\d+)\s*[- ]?(bed|bedroom)", text)
    if bedroom_match:
        data["bedrooms"] = int(bedroom_match.group(1))

    million_match = re.search(r"(r?\s?\d+(\.\d+)?)\s*(million|m)\b", text)
    if million_match:
        value = million_match.group(1).replace("r", "").strip()
        data["budget"] = float(value) * 1_000_000
    else:
        money_match = re.search(r"r?\s?(\d{1,3}(,\d{3})+|\d{4,7})", text)
        if money_match:
            data["budget"] = float(money_match.group(1).replace(",", ""))

    if any(
        word in text
        for word in ["today", "tomorrow", "this week", "weekend", "urgent", "as soon as possible"]
    ):
        data["timeline"] = "urgent"
    elif any(word in text for word in ["month", "next month", "soon"]):
        data["timeline"] = "within_30_days"

    data.update(extract_contact_details(message))
    return data


def extract_time_phrase(message: str) -> str:
    text = message.lower()
    parts = []

    if "tomorrow" in text:
        parts.append("tomorrow")
    elif "today" in text:
        parts.append("today")
    elif "weekend" in text:
        parts.append("this weekend")
    elif "this week" in text:
        parts.append("this week")

    if "morning" in text:
        parts.append("morning")
    elif "afternoon" in text:
        parts.append("afternoon")
    elif "evening" in text:
        parts.append("evening")

    return " ".join(parts) if parts else "time to be confirmed"


# ============================================================
# LEAD SCORING AND MATCHING
# ============================================================

def calculate_lead_score(lead: sqlite3.Row) -> int:
    score = 0

    if lead["intent"]:
        score += 15
    if lead["location"]:
        score += 15
    if lead["property_type"]:
        score += 10
    if lead["bedrooms"]:
        score += 10
    if lead["budget"]:
        score += 20
    if lead["timeline"]:
        score += 15
    if lead["email"] or lead["phone"]:
        score += 15

    return min(score, 100)


def determine_stage(score: int) -> str:
    if score >= 80:
        return "hot_lead"
    if score >= 55:
        return "qualified"
    if score >= 25:
        return "nurture"
    return "new"


def update_lead_from_extraction(lead_id: int, extracted: Dict[str, Any]) -> None:
    allowed_fields = [
        "full_name",
        "email",
        "phone",
        "intent",
        "location",
        "property_type",
        "bedrooms",
        "budget",
        "timeline",
    ]

    for key, value in extracted.items():
        if key in allowed_fields and value not in [None, ""]:
            execute(
                f"UPDATE leads SET {key} = ?, updated_at = ? WHERE id = ?",
                (value, now(), lead_id),
            )

    lead = get_current_lead(lead_id)
    score = calculate_lead_score(lead)
    stage = determine_stage(score)
    handoff_required = 1 if score >= 85 else 0

    execute(
        """
        UPDATE leads
        SET lead_score = ?, lead_stage = ?, human_handoff_required = ?, updated_at = ?
        WHERE id = ?
        """,
        (score, stage, handoff_required, now(), lead_id),
    )


def search_matching_properties(lead: sqlite3.Row, limit: int = 3) -> pd.DataFrame:
    sql = "SELECT * FROM properties WHERE availability_status = 'available'"
    params: List[Any] = []

    if lead["intent"] in ["rent", "buy"]:
        sql += " AND listing_type = ?"
        params.append(lead["intent"])

    if lead["location"]:
        sql += " AND LOWER(location) LIKE ?"
        params.append(f"%{lead['location'].lower()}%")

    if lead["property_type"]:
        sql += " AND LOWER(property_type) LIKE ?"
        params.append(f"%{lead['property_type'].lower()}%")

    if lead["bedrooms"]:
        sql += " AND bedrooms >= ?"
        params.append(lead["bedrooms"])

    if lead["budget"]:
        sql += " AND price <= ?"
        params.append(float(lead["budget"]) * 1.15)

    sql += " ORDER BY price ASC LIMIT ?"
    params.append(limit)

    return query_df(sql, tuple(params))


def fallback_recommendations(lead: sqlite3.Row, limit: int = 3) -> pd.DataFrame:
    sql = "SELECT * FROM properties WHERE availability_status = 'available'"
    params: List[Any] = []

    if lead["intent"] in ["rent", "buy"]:
        sql += " AND listing_type = ?"
        params.append(lead["intent"])

    if lead["bedrooms"]:
        sql += " AND bedrooms >= ?"
        params.append(lead["bedrooms"])

    budget = float(lead["budget"] or 1000000)

    sql += " ORDER BY ABS(price - ?) ASC LIMIT ?"
    params.extend([budget, limit])

    return query_df(sql, tuple(params))


def missing_fields(lead: sqlite3.Row) -> List[str]:
    missing = []

    if not lead["intent"]:
        missing.append("whether you want to rent or buy")
    if not lead["location"]:
        missing.append("your preferred area")
    if not lead["budget"]:
        missing.append("your budget")
    if not lead["bedrooms"]:
        missing.append("how many bedrooms you need")
    if not lead["property_type"]:
        missing.append("the property type, such as apartment, flat, house or townhouse")
    if not lead["email"] and not lead["phone"]:
        missing.append("your email or phone number for viewing confirmation")

    return missing


def build_missing_info_question(lead: sqlite3.Row) -> str:
    missing = missing_fields(lead)

    if not missing:
        return "I have enough information to recommend suitable listings. Would you like me to show the best matches?"

    return "To help you properly, please share " + " and ".join(missing[:2]) + "."


def build_property_recommendation(
    lead: sqlite3.Row,
    matches: pd.DataFrame,
    fallback_used: bool = False,
) -> str:
    if matches.empty:
        return (
            "I could not find an exact available listing for your current requirements. "
            "Would you like me to broaden the area, increase the budget slightly, or show nearby alternatives?"
        )

    if fallback_used:
        intro = "I could not find a perfect match, but I found the closest available alternatives"
    else:
        intro = "I found the best available options for you"

    lines = [intro + ":\n"]

    for i, (_, prop) in enumerate(matches.iterrows(), start=1):
        lines.append(
            f"{i}. {prop['title']}\n"
            f"   Price: R{prop['price']:,.0f} | {prop['bedrooms']} bed | "
            f"{prop['bathrooms']} bath | {prop['size_sqm']} sqm\n"
            f"   Location: {prop['location']}\n"
            f"   Summary: {prop['description']}\n"
            f"   Listing: {prop['listing_url']}\n"
        )

    lines.append(
        "You can say: 'book the first one tomorrow afternoon' or "
        "'send me the details by email and WhatsApp'."
    )

    return "\n".join(lines)


# ============================================================
# INTENT AND CONTEXT MANAGEMENT
# ============================================================

def message_indicates_booking(message: str) -> bool:
    text = message.lower()
    return any(
        phrase in text
        for phrase in [
            "book",
            "viewing",
            "schedule",
            "appointment",
            "visit",
            "see the property",
            "view the",
        ]
    )


def message_requests_notification(message: str) -> bool:
    text = message.lower()
    return any(
        phrase in text
        for phrase in [
            "email",
            "whatsapp",
            "send me",
            "message me",
            "notify",
            "details",
        ]
    )


def message_is_ambiguous_reference(message: str) -> bool:
    text = message.lower().strip()

    if text in [
        "yes",
        "ok",
        "okay",
        "sure",
        "that one",
        "the one",
        "first one",
        "second one",
        "third one",
    ]:
        return True

    return any(
        phrase in text
        for phrase in [
            "what about it",
            "what about that",
            "what about the first",
            "what about the second",
            "what about the third",
        ]
    )


def select_property_from_message(
    lead_id: int,
    message: str,
    matches: pd.DataFrame,
) -> Optional[int]:
    text = message.lower()

    id_match = re.search(r"(?:property|listing)\s*(\d+)", text)
    if id_match:
        return int(id_match.group(1))

    for word, idx in ORDINALS.items():
        if word in text and not matches.empty and idx < len(matches):
            return int(matches.iloc[idx]["id"])

    lead = get_current_lead(lead_id)

    if lead["selected_property_id"]:
        return int(lead["selected_property_id"])

    if not matches.empty:
        return int(matches.iloc[0]["id"])

    return None


# ============================================================
# BOOKING, EMAIL AND WHATSAPP TOOLS
# ============================================================

def create_appointment(
    lead_id: int,
    property_id: Optional[int],
    requested_time: str,
) -> int:
    lead = get_current_lead(lead_id)
    prop = fetchone("SELECT * FROM properties WHERE id = ?", (property_id,)) if property_id else None

    appointment_id = execute(
        """
        INSERT INTO appointments (
            lead_id, property_id, requested_time,
            client_name, client_email, client_phone,
            assigned_agent_name, assigned_agent_email, assigned_agent_phone,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            property_id,
            requested_time,
            lead["full_name"],
            lead["email"],
            lead["phone"],
            prop["agent_name"] if prop else DEFAULT_HUMAN_AGENT["name"],
            prop["agent_email"] if prop else DEFAULT_HUMAN_AGENT["email"],
            prop["agent_phone"] if prop else DEFAULT_HUMAN_AGENT["phone"],
            "requested",
            now(),
        ),
    )

    if property_id:
        execute(
            "UPDATE leads SET selected_property_id = ?, updated_at = ? WHERE id = ?",
            (property_id, now(), lead_id),
        )

    return appointment_id


def get_appointment_bundle(
    appointment_id: int,
) -> Tuple[sqlite3.Row, sqlite3.Row, sqlite3.Row]:
    appointment = fetchone("SELECT * FROM appointments WHERE id = ?", (appointment_id,))

    if appointment is None:
        raise RuntimeError("Appointment not found")

    lead = fetchone("SELECT * FROM leads WHERE id = ?", (appointment["lead_id"],))
    prop = fetchone("SELECT * FROM properties WHERE id = ?", (appointment["property_id"],))

    if lead is None or prop is None:
        raise RuntimeError("Appointment bundle is incomplete")

    return appointment, lead, prop


def build_email_body(appointment_id: int) -> Tuple[str, str, str]:
    appointment, lead, prop = get_appointment_bundle(appointment_id)

    recipient = lead["email"] or "missing-client-email@example.com"
    subject = f"Viewing Request: {prop['title']}"

    body = f"""Good day {lead['full_name'] or 'there'},

Thank you for your interest in {prop['title']}.

Your viewing request has been captured with the following details:

Property: {prop['title']}
Location: {prop['location']}
Viewing address: {prop['viewing_address']}
Price: R{prop['price']:,.0f}
Requested time: {appointment['requested_time']}
Status: {appointment['status']}

Your property consultant:
Name: {prop['agent_name']}
Email: {prop['agent_email']}
Phone: {prop['agent_phone']}
WhatsApp: {prop['agent_whatsapp']}

Please reply to confirm your preferred exact time, or contact the consultant directly.

Kind regards,
{AGENCY['name']}
{AGENCY['email']}
{AGENCY['phone']}
"""

    return recipient, subject, body


def save_outbox(
    lead_id: int,
    appointment_id: Optional[int],
    channel: str,
    recipient: str,
    subject: str,
    body: str,
    status: str,
    provider_response: str,
) -> int:
    return execute(
        """
        INSERT INTO outbox (
            lead_id, appointment_id, channel, recipient, subject,
            body, status, provider_response, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            appointment_id,
            channel,
            recipient,
            subject,
            body,
            status,
            provider_response,
            now(),
        ),
    )


def get_secret_value(name: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def send_real_email_if_enabled(
    recipient: str,
    subject: str,
    body: str,
) -> Tuple[str, str]:
    """
    Safe by default.

    To actually send email, add Streamlit secrets:
    SMTP_HOST
    SMTP_PORT
    SMTP_USER
    SMTP_PASSWORD
    SMTP_FROM
    ENABLE_REAL_EMAIL = true
    """
    enabled = bool(get_secret_value("ENABLE_REAL_EMAIL", False))

    if not enabled:
        return "drafted", "Real email sending is disabled. Message saved to outbox."

    smtp_host = get_secret_value("SMTP_HOST")
    smtp_port = int(get_secret_value("SMTP_PORT", 587))
    smtp_user = get_secret_value("SMTP_USER")
    smtp_password = get_secret_value("SMTP_PASSWORD")
    smtp_from = get_secret_value("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
        return "drafted", "SMTP secrets are incomplete. Message saved to outbox."

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return "sent", "Email sent through configured SMTP."

    except Exception as exc:
        return "failed", f"SMTP failed: {exc}"


def create_email_notification(lead_id: int, appointment_id: int) -> str:
    recipient, subject, body = build_email_body(appointment_id)
    status, provider_response = send_real_email_if_enabled(recipient, subject, body)

    save_outbox(
        lead_id=lead_id,
        appointment_id=appointment_id,
        channel="email",
        recipient=recipient,
        subject=subject,
        body=body,
        status=status,
        provider_response=provider_response,
    )

    log_action(
        lead_id,
        "email_notification_created",
        f"recipient={recipient}; status={status}",
        status,
    )

    return f"Email notification {status}. Recipient: {recipient}. {provider_response}"


def create_whatsapp_notification(lead_id: int, appointment_id: int) -> str:
    appointment, lead, prop = get_appointment_bundle(appointment_id)

    recipient = lead["phone"] or prop["agent_whatsapp"]

    body = (
        f"Good day {lead['full_name'] or 'there'}, your viewing request for "
        f"{prop['title']} has been captured. "
        f"Address: {prop['viewing_address']}. "
        f"Requested time: {appointment['requested_time']}. "
        f"Consultant: {prop['agent_name']}, {prop['agent_phone']}."
    )

    clean_number = re.sub(r"\D", "", recipient)
    whatsapp_link = "https://wa.me/" + clean_number + "?text=" + quote_plus(body)

    full_body = body + f"\n\nWhatsApp click-to-send link: {whatsapp_link}"

    save_outbox(
        lead_id=lead_id,
        appointment_id=appointment_id,
        channel="whatsapp",
        recipient=recipient,
        subject="Viewing request WhatsApp message",
        body=full_body,
        status="drafted",
        provider_response="WhatsApp Business API not configured. Click-to-send link generated.",
    )

    log_action(
        lead_id,
        "whatsapp_notification_created",
        f"recipient={recipient}",
        "drafted",
    )

    return (
        f"WhatsApp message drafted. Recipient: {recipient}. "
        "A click-to-send link is available in the Outbox tab."
    )


# ============================================================
# AUTONOMOUS AGENT ORCHESTRATOR
# ============================================================

def agent_orchestrator(lead_id: int, message: str) -> str:
    """
    Main autonomous workflow:

    1. Save user message.
    2. Extract structured lead information.
    3. Update SQLite CRM.
    4. Score the lead.
    5. Search matching listings.
    6. Handle ambiguity using stored context.
    7. Recommend properties.
    8. Book viewing requests.
    9. Draft email and WhatsApp notifications.
    10. Log actions.
    """
    add_message(lead_id, "user", message)

    extracted = extract_lead_preferences(message)
    update_lead_from_extraction(lead_id, extracted)

    lead = get_current_lead(lead_id)

    matches = search_matching_properties(lead)
    fallback_used = False

    if matches.empty and (lead["intent"] or lead["bedrooms"] or lead["budget"]):
        matches = fallback_recommendations(lead)
        fallback_used = True

    log_action(
        lead_id,
        "context_updated",
        f"extracted={extracted}; score={lead['lead_score']}; stage={lead['lead_stage']}",
    )

    response = ""

    if message_is_ambiguous_reference(message) and lead["selected_property_id"]:
        prop = fetchone(
            "SELECT * FROM properties WHERE id = ?",
            (lead["selected_property_id"],),
        )

        if prop:
            response = (
                f"Do you mean {prop['title']} in {prop['location']}? "
                f"It is available at R{prop['price']:,.0f}. "
                "You can say 'book it tomorrow afternoon' or ask for more details."
            )
        else:
            response = "I remember you referred to a previous listing, but I cannot find it now. Please choose a listing again."

    elif message_requests_notification(message):
        appointment = get_latest_appointment(lead_id)

        if appointment:
            parts = []
            lower = message.lower()

            if "email" in lower or "send me" in lower or "details" in lower:
                parts.append(create_email_notification(lead_id, appointment["id"]))

            if "whatsapp" in lower or "message" in lower or "send me" in lower:
                parts.append(create_whatsapp_notification(lead_id, appointment["id"]))

            response = "\n".join(parts)

        else:
            response = (
                "I can send the booking details, but first I need to create a viewing request. "
                "Please say which property you want to view and your preferred time."
            )

    elif message_indicates_booking(message):
        lead = get_current_lead(lead_id)

        if not lead["email"] and not lead["phone"]:
            response = (
                "I can request the viewing, but I need your email or phone number first "
                "so the booking details can be sent to you."
            )
        else:
            property_id = select_property_from_message(lead_id, message, matches)

            if property_id is None:
                response = (
                    "I can request a viewing, but I need to know which listing you mean. "
                    "Please say 'first one', 'second one', or give the listing number."
                )
            else:
                requested_time = extract_time_phrase(message)
                appointment_id = create_appointment(lead_id, property_id, requested_time)

                prop = fetchone("SELECT * FROM properties WHERE id = ?", (property_id,))
                lead = get_current_lead(lead_id)

                email_status = (
                    create_email_notification(lead_id, appointment_id)
                    if lead["email"]
                    else "No email address captured."
                )

                whatsapp_status = (
                    create_whatsapp_notification(lead_id, appointment_id)
                    if lead["phone"]
                    else "No phone number captured."
                )

                response = (
                    f"Viewing request created for {prop['title']}.\n\n"
                    f"Requested time: {requested_time}\n"
                    f"Viewing address: {prop['viewing_address']}\n\n"
                    f"Assigned consultant:\n"
                    f"{prop['agent_name']} | {prop['agent_email']} | {prop['agent_phone']}\n\n"
                    f"{email_status}\n"
                    f"{whatsapp_status}"
                )

    elif not matches.empty and lead["lead_score"] >= 55:
        selected_id = int(matches.iloc[0]["id"])

        execute(
            "UPDATE leads SET selected_property_id = ?, updated_at = ? WHERE id = ?",
            (selected_id, now(), lead_id),
        )

        response = build_property_recommendation(
            lead,
            matches,
            fallback_used=fallback_used,
        )

    else:
        response = build_missing_info_question(lead)

    lead = get_current_lead(lead_id)

    if lead["human_handoff_required"]:
        response += (
            "\n\nI have also flagged this as a high-priority lead for the assigned property consultant, "
            f"{lead['assigned_agent_name']}."
        )

    add_message(lead_id, "assistant", response)
    return response


# ============================================================
# STREAMLIT UI
# ============================================================

def page_setup() -> None:
    st.set_page_config(
        page_title="Novo Autonomous Real Estate Agent",
        page_icon="🏡",
        layout="wide",
    )

    st.markdown(
        """
        <style>
            .big-title {
                font-size: 42px;
                font-weight: 850;
                margin-bottom: 0;
            }
            .subtitle {
                font-size: 18px;
                color: #5B6475;
                margin-top: 4px;
            }
            .pill {
                display: inline-block;
                padding: 6px 12px;
                border-radius: 999px;
                background: #EEF2FF;
                color: #3444C5;
                font-weight: 700;
                margin-right: 8px;
                margin-bottom: 8px;
            }
            .warning-box {
                background: #fff7ed;
                border: 1px solid #fed7aa;
                padding: 12px;
                border-radius: 12px;
                color: #7c2d12;
            }
        </style>

        <p class="big-title">🏡 Autonomous Real Estate Operations Agent</p>
        <p class="subtitle">
            SQLite-backed Streamlit demo for lead qualification, context memory,
            listing recommendation, viewing booking, email/WhatsApp notifications,
            CRM updates and business metrics.
        </p>

        <span class="pill">SQLite Persistence</span>
        <span class="pill">Context Management</span>
        <span class="pill">Autonomous Booking</span>
        <span class="pill">Email Outbox</span>
        <span class="pill">WhatsApp Drafts</span>
        <span class="pill">CRM Workflow</span>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(lead_id: int) -> None:
    lead = get_current_lead(lead_id)

    appointments = query_df(
        "SELECT * FROM appointments WHERE lead_id = ?",
        (lead_id,),
    )

    outbox = query_df(
        "SELECT * FROM outbox WHERE lead_id = ?",
        (lead_id,),
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Lead Score", f"{lead['lead_score']}/100")
    c2.metric("Lead Stage", lead["lead_stage"])
    c3.metric("Viewings", len(appointments))
    c4.metric("Messages", len(outbox))
    c5.metric("Handoff", "Yes" if lead["human_handoff_required"] else "No")
    c6.metric("Selected Listing", lead["selected_property_id"] or "None")


def render_chat(lead_id: int) -> None:
    st.subheader("💬 Autonomous Agent Conversation")

    e1, e2, e3, e4 = st.columns(4)

    examples = [
        (
            "Rental lead",
            "My name is James and my email is james@example.com. "
            "I want to rent a 2-bedroom apartment in Claremont. "
            "My budget is R12,000 and I need it this week.",
        ),
        (
            "Buyer lead",
            "I want to buy a 3-bedroom house in Sandton. "
            "Budget around R2.5 million. My phone is +27821234567.",
        ),
        (
            "Book viewing",
            "Can I view the first one tomorrow afternoon?",
        ),
        (
            "Notify client",
            "Send me the booking details by email and WhatsApp.",
        ),
    ]

    for col, (label, prompt) in zip([e1, e2, e3, e4], examples):
        with col:
            if st.button(label, use_container_width=True):
                agent_orchestrator(lead_id, prompt)
                st.rerun()

    messages = query_df(
        """
        SELECT role, content
        FROM messages
        WHERE lead_id = ?
        ORDER BY id ASC
        """,
        (lead_id,),
    )

    if messages.empty:
        greeting = (
            "Good day. I am the autonomous property assistant. "
            "I can qualify your needs, recommend listings, request viewings, "
            "and prepare email/WhatsApp booking details. "
            "Please tell me what you are looking for."
        )
        add_message(lead_id, "assistant", greeting)
        st.rerun()

    for _, msg in messages.iterrows():
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_message = st.chat_input("Tell the agent what you need, or ask to book/send details.")

    if user_message:
        agent_orchestrator(lead_id, user_message)
        st.rerun()


def render_crm(lead_id: int) -> None:
    st.subheader("📇 SQLite CRM Lead Record")

    lead_df = query_df(
        "SELECT * FROM leads WHERE id = ?",
        (lead_id,),
    )

    st.dataframe(
        lead_df.T.rename(columns={0: "Value"}),
        use_container_width=True,
    )

    lead = get_current_lead(lead_id)

    score_df = pd.DataFrame(
        {
            "Metric": ["Lead Score"],
            "Score": [lead["lead_score"]],
        }
    )

    fig = px.bar(
        score_df,
        x="Metric",
        y="Score",
        range_y=[0, 100],
        title="Lead Qualification Score",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_listings(lead_id: int) -> None:
    st.subheader("🏘️ Available Listings")

    properties = query_df(
        """
        SELECT
            id, title, location, price, property_type, listing_type,
            bedrooms, bathrooms, size_sqm, availability_status,
            viewing_address, agent_name, agent_phone
        FROM properties
        ORDER BY location
        """
    )

    st.dataframe(
        properties,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🎯 Current Best Matches")

    lead = get_current_lead(lead_id)
    matches = search_matching_properties(lead)

    if matches.empty:
        matches = fallback_recommendations(lead)

    if matches.empty:
        st.info("No matches yet. Complete the lead requirements in the chat.")
        return

    for i, (_, prop) in enumerate(matches.iterrows(), start=1):
        with st.container(border=True):
            st.markdown(f"### {i}. {prop['title']}")
            st.write(prop["description"])

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Location", prop["location"])
            c2.metric("Price", f"R{prop['price']:,.0f}")
            c3.metric("Beds", int(prop["bedrooms"]))
            c4.metric("Size", f"{int(prop['size_sqm'])} sqm")

            st.caption(f"Viewing address: {prop['viewing_address']}")
            st.caption(
                f"Agent: {prop['agent_name']} | {prop['agent_email']} | {prop['agent_phone']}"
            )


def render_bookings_and_outbox(lead_id: int) -> None:
    st.subheader("📅 Viewing Bookings")

    appointments = query_df(
        """
        SELECT *
        FROM appointments
        WHERE lead_id = ?
        ORDER BY id DESC
        """,
        (lead_id,),
    )

    if appointments.empty:
        st.info("No booking yet.")
    else:
        st.dataframe(
            appointments,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("📨 Email / WhatsApp Outbox")

    outbox = query_df(
        """
        SELECT *
        FROM outbox
        WHERE lead_id = ?
        ORDER BY id DESC
        """,
        (lead_id,),
    )

    if outbox.empty:
        st.info("No email or WhatsApp message drafted yet.")
        return

    st.dataframe(
        outbox[
            [
                "id",
                "channel",
                "recipient",
                "subject",
                "status",
                "provider_response",
                "created_at",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    selected_id = st.selectbox(
        "Open outbox message",
        outbox["id"].tolist(),
    )

    selected = outbox[outbox["id"] == selected_id].iloc[0]

    st.text_area(
        "Message body",
        selected["body"],
        height=280,
    )

    if selected["channel"] == "whatsapp" and "https://wa.me/" in selected["body"]:
        link = re.search(r"https://wa\.me/[^\s]+", selected["body"])
        if link:
            st.link_button(
                "Open WhatsApp click-to-send",
                link.group(0),
            )


def render_actions(lead_id: int) -> None:
    st.subheader("🧠 Agent Action")

    actions = query_df(
        """
        SELECT *
        FROM agent_actions
        WHERE lead_id = ?
        ORDER BY id DESC
        """,
        (lead_id,),
    )

    if actions.empty:
        st.info("No actions logged yet.")
    else:
        st.dataframe(
            actions,
            use_container_width=True,
            hide_index=True,
        )




    st.markdown(
        """
        <div class="warning-box">
        This demo automates front-office real estate operations, but a production system should still include
        human oversight for legal contracts, final price negotiation, identity checks, regulatory disclosures,
        physical property access and signed lease or offer-to-purchase agreements.
        </div>
        """,
        unsafe_allow_html=True,
    )




# ============================================================
# MAIN APP
# ============================================================

def main() -> None:
    init_db()
    lead_id = ensure_active_lead()

    page_setup()

    with st.sidebar:
        st.header("Demo Controls")
        st.write(f"Active Lead ID: {lead_id}")

        if st.button("Reset SQLite demo", use_container_width=True):
            reset_database()
            st.rerun()

        st.markdown("---")
        st.subheader("Agency Contact")
        st.write(f"**{AGENCY['name']}**")
        st.write(AGENCY["email"])
        st.write(AGENCY["phone"])
        st.write(f"WhatsApp: {AGENCY['whatsapp']}")

        st.markdown("---")
        st.subheader("What this assistant does")
        st.write(
            """
            - Captures lead details
            - Handles ambiguous follow-ups
            - Recommends listings
            - Books viewing requests
            - Drafts email/WhatsApp details
            - Logs all actions
            - Stores everything in SQLite
            - Remembers context
            """
        )

        st.markdown("---")
        st.info(
            "Email and WhatsApp are safely drafted. "
        )

    render_metrics(lead_id)

    tab1, tab2, tab3, tab4, tab5= st.tabs(
        [
            "Agent Chat",
            "CRM & Score",
            "Listings & Matches",
            "Bookings & Outbox",
            "Agent Actions"
        ]
    )

    with tab1:
        render_chat(lead_id)

    with tab2:
        render_crm(lead_id)

    with tab3:
        render_listings(lead_id)

    with tab4:
        render_bookings_and_outbox(lead_id)

    with tab5:
        render_actions(lead_id)




if __name__ == "__main__":
    main()
