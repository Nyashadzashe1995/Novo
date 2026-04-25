import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st


# -------------------------------------------------------------------
# Data models
# -------------------------------------------------------------------

@dataclass
class Lead:
    id: int
    full_name: str = "Demo Website Lead"
    email: str = "lead@example.com"
    phone: str = "+27 82 000 0000"
    source: str = "website_demo"
    intent: Optional[str] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    budget: Optional[float] = None
    timeline: Optional[str] = None
    lead_score: int = 0
    lead_stage: str = "new"
    assigned_agent: str = "Unassigned"
    human_handoff_required: bool = False
    created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Appointment:
    id: int
    lead_id: int
    property_id: Optional[int]
    requested_time: str
    status: str = "requested"
    created_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------------
# Synthetic database
# -------------------------------------------------------------------

def load_synthetic_properties() -> pd.DataFrame:
    return pd.DataFrame(
        [
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
            },
        ]
    )


# -------------------------------------------------------------------
# Agent tools
# -------------------------------------------------------------------

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


def extract_lead_preferences(message: str) -> Dict[str, Any]:
    """
    Deterministic extraction for demo reliability.
    In production, this can be replaced with LLM structured output.
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

    if any(word in text for word in ["today", "tomorrow", "this week", "weekend", "urgent", "as soon as possible"]):
        data["timeline"] = "urgent"
    elif any(word in text for word in ["month", "next month", "soon"]):
        data["timeline"] = "within_30_days"

    return data


def calculate_lead_score(lead: Lead) -> int:
    score = 0

    if lead.intent:
        score += 15
    if lead.location:
        score += 15
    if lead.property_type:
        score += 10
    if lead.bedrooms:
        score += 10
    if lead.budget:
        score += 20
    if lead.timeline:
        score += 15
    if lead.email or lead.phone:
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


def search_matching_properties(properties: pd.DataFrame, lead: Lead, limit: int = 3) -> pd.DataFrame:
    results = properties.copy()

    results = results[results["availability_status"] == "available"]

    if lead.intent in ["rent", "buy"]:
        results = results[results["listing_type"] == lead.intent]

    if lead.location:
        results = results[results["location"].str.lower().str.contains(lead.location.lower(), na=False)]

    if lead.property_type:
        results = results[results["property_type"].str.lower().str.contains(lead.property_type.lower(), na=False)]

    if lead.bedrooms:
        results = results[results["bedrooms"] >= lead.bedrooms]

    if lead.budget:
        results = results[results["price"] <= lead.budget * 1.15]

    return results.sort_values("price", ascending=True).head(limit)


def message_indicates_booking(message: str) -> bool:
    text = message.lower()
    return any(word in text for word in ["book", "viewing", "schedule", "appointment", "visit", "see the property"])


def extract_time_phrase(message: str) -> str:
    text = message.lower()
    if "tomorrow" in text:
        return "tomorrow"
    if "today" in text:
        return "today"
    if "weekend" in text:
        return "this weekend"
    if "this week" in text:
        return "this week"
    if "afternoon" in text:
        return "afternoon, time to be confirmed"
    return "time to be confirmed"


def update_lead_from_extraction(lead: Lead, extracted: Dict[str, Any]) -> Lead:
    for key, value in extracted.items():
        if hasattr(lead, key) and value is not None:
            setattr(lead, key, value)

    lead.lead_score = calculate_lead_score(lead)
    lead.lead_stage = determine_stage(lead.lead_score)
    lead.human_handoff_required = lead.lead_score >= 85
    return lead


def ask_missing_info(lead: Lead) -> str:
    missing = []

    if not lead.intent:
        missing.append("whether you want to rent or buy")
    if not lead.location:
        missing.append("your preferred area")
    if not lead.budget:
        missing.append("your budget")
    if not lead.bedrooms:
        missing.append("how many bedrooms you need")
    if not lead.property_type:
        missing.append("the property type, such as apartment, house or townhouse")

    if not missing:
        return "Thank you. I have captured your details. Would you like me to look for matching properties?"

    return (
        "I can help you find the right property. To qualify your request properly, "
        f"please share {', '.join(missing[:2])}."
    )


def build_property_recommendation(lead: Lead, matches: pd.DataFrame) -> str:
    intro = (
        f"Thanks. Based on your requirements"
        f"{' for ' + lead.location if lead.location else ''}, "
        f"I found {len(matches)} suitable option(s):\n\n"
    )

    lines = []
    for _, p in matches.iterrows():
        lines.append(
            f"• {p['title']}\n"
            f"  Price: R{p['price']:,.0f} | {p['bedrooms']} bed | "
            f"{p['bathrooms']} bath | {p['size_sqm']} sqm\n"
            f"  {p['description']}"
        )

    close = "\n\nWould you like me to request a viewing for one of these properties?"
    return intro + "\n\n".join(lines) + close


def create_viewing_request(lead: Lead, matches: pd.DataFrame, message: str) -> Appointment:
    next_id = len(st.session_state.appointments) + 1
    property_id = int(matches.iloc[0]["id"]) if not matches.empty else None
    appointment = Appointment(
        id=next_id,
        lead_id=lead.id,
        property_id=property_id,
        requested_time=extract_time_phrase(message),
    )
    st.session_state.appointments.append(appointment)
    return appointment


def log_action(action_type: str, payload: Dict[str, Any]) -> None:
    st.session_state.agent_actions.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action_type": action_type,
            "payload": payload,
            "status": "success",
        }
    )


def agent_orchestrator(message: str) -> str:
    """
    Main agent workflow:
    1. Extract lead preferences.
    2. Update CRM-style lead record.
    3. Score lead.
    4. Search matching listings.
    5. Decide whether to ask questions, recommend, book, or hand off.
    """
    lead: Lead = st.session_state.lead
    properties: pd.DataFrame = st.session_state.properties

    extracted = extract_lead_preferences(message)
    lead = update_lead_from_extraction(lead, extracted)
    st.session_state.lead = lead

    matches = search_matching_properties(properties, lead)
    st.session_state.latest_matches = matches

    log_action(
        "lead_profile_updated",
        {
            "extracted": extracted,
            "lead_score": lead.lead_score,
            "lead_stage": lead.lead_stage,
        },
    )

    if message_indicates_booking(message):
        appointment = create_viewing_request(lead, matches, message)
        log_action(
            "appointment_requested",
            {
                "appointment_id": appointment.id,
                "property_id": appointment.property_id,
                "requested_time": appointment.requested_time,
            },
        )
        response = (
            "Great — I have created a viewing request. "
            "A human property consultant can confirm the exact time and availability."
        )

    elif not matches.empty and lead.lead_score >= 55:
        log_action(
            "property_recommendation_generated",
            {
                "matched_property_ids": matches["id"].tolist(),
                "count": len(matches),
            },
        )
        response = build_property_recommendation(lead, matches)

    else:
        log_action("qualification_question_asked", {"missing_fields_checked": True})
        response = ask_missing_info(lead)

    if lead.human_handoff_required:
        log_action(
            "human_handoff_triggered",
            {
                "reason": "High-value or high-intent lead",
                "lead_score": lead.lead_score,
            },
        )
        response += (
            "\n\nThis looks like a strong lead, so I am also flagging it for a human agent "
            "to follow up personally."
        )

    return response


# -------------------------------------------------------------------
# Streamlit state
# -------------------------------------------------------------------

def init_state() -> None:
    if "properties" not in st.session_state:
        st.session_state.properties = load_synthetic_properties()

    if "lead" not in st.session_state:
        st.session_state.lead = Lead(id=1)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Good day. I am NovoStyle AI, a real estate operations assistant. "
                    "Tell me what property you are looking for, including area, budget and bedrooms."
                ),
            }
        ]

    if "appointments" not in st.session_state:
        st.session_state.appointments: List[Appointment] = []

    if "agent_actions" not in st.session_state:
        st.session_state.agent_actions: List[Dict[str, Any]] = []

    if "latest_matches" not in st.session_state:
        st.session_state.latest_matches = pd.DataFrame()


def reset_demo() -> None:
    st.session_state.lead = Lead(id=1)
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Demo reset. Tell me what property you are looking for, including area, budget and bedrooms."
            ),
        }
    ]
    st.session_state.appointments = []
    st.session_state.agent_actions = []
    st.session_state.latest_matches = pd.DataFrame()


# -------------------------------------------------------------------
# UI components
# -------------------------------------------------------------------

def render_header() -> None:
    st.set_page_config(
        page_title="NovoStyle Real Estate Agent",
        page_icon="🏡",
        layout="wide",
    )

    st.markdown(
        """
        <style>
            .main-title {
                font-size: 44px;
                font-weight: 800;
                margin-bottom: 0;
            }
            .subtitle {
                font-size: 18px;
                color: #5B6475;
                margin-top: 6px;
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
            .small-note {
                color: #6B7280;
                font-size: 14px;
            }
        </style>
        <p class="main-title">🏡 Real Estate Agentic AI Assistant</p>
        <p class="subtitle">
            Streamlit showcase for NovoAgent-style lead qualification, property matching,
            CRM updates, viewing requests and business metrics.
        </p>
        <span class="pill">Agentic Workflow</span>
        <span class="pill">Lead Scoring</span>
        <span class="pill">Synthetic Listings</span>
        <span class="pill">Human Handoff</span>
        <span class="pill">Business Metrics</span>
        """,
        unsafe_allow_html=True,
    )


def render_metrics() -> None:
    lead: Lead = st.session_state.lead
    appointments = st.session_state.appointments

    total_leads = 1
    qualified_leads = 1 if lead.lead_stage in ["qualified", "hot_lead"] else 0
    hot_leads = 1 if lead.lead_stage == "hot_lead" else 0
    handoffs = 1 if lead.human_handoff_required else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Leads", total_leads)
    col2.metric("Qualified Leads", qualified_leads)
    col3.metric("Hot Leads", hot_leads)
    col4.metric("Viewings Requested", len(appointments))
    col5.metric("Human Handoffs", handoffs)


def render_chat() -> None:
    st.subheader("💬 Agent Conversation")

    example_col1, example_col2, example_col3 = st.columns(3)

    with example_col1:
        if st.button("Try rental lead", use_container_width=True):
            run_user_message(
                "I want to rent a 2-bedroom apartment in Claremont. My budget is R12,000 and I need it this week."
            )

    with example_col2:
        if st.button("Try buyer lead + booking", use_container_width=True):
            run_user_message(
                "I want to buy a 3-bedroom house in Sandton. Budget around R2.5 million. I want to view tomorrow."
            )

    with example_col3:
        if st.button("Book viewing", use_container_width=True):
            run_user_message("Can I book a viewing tomorrow afternoon?")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_message = st.chat_input(
        "Example: I want to rent a 2-bedroom apartment in Claremont, budget R12,000"
    )

    if user_message:
        run_user_message(user_message)


def run_user_message(message: str) -> None:
    st.session_state.messages.append({"role": "user", "content": message})
    response = agent_orchestrator(message)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()


def render_crm_record() -> None:
    lead: Lead = st.session_state.lead

    st.subheader("📇 CRM Lead Record")

    lead_df = pd.DataFrame(
        [
            {
                "Field": "Lead ID",
                "Value": lead.id,
            },
            {
                "Field": "Full Name",
                "Value": lead.full_name,
            },
            {
                "Field": "Email",
                "Value": lead.email,
            },
            {
                "Field": "Phone",
                "Value": lead.phone,
            },
            {
                "Field": "Source",
                "Value": lead.source,
            },
            {
                "Field": "Intent",
                "Value": lead.intent or "Unknown",
            },
            {
                "Field": "Location",
                "Value": lead.location or "Unknown",
            },
            {
                "Field": "Property Type",
                "Value": lead.property_type or "Unknown",
            },
            {
                "Field": "Bedrooms",
                "Value": lead.bedrooms or "Unknown",
            },
            {
                "Field": "Budget",
                "Value": f"R{lead.budget:,.0f}" if lead.budget else "Unknown",
            },
            {
                "Field": "Timeline",
                "Value": lead.timeline or "Unknown",
            },
            {
                "Field": "Lead Score",
                "Value": f"{lead.lead_score}/100",
            },
            {
                "Field": "Lead Stage",
                "Value": lead.lead_stage,
            },
            {
                "Field": "Human Handoff",
                "Value": "Required" if lead.human_handoff_required else "No",
            },
        ]
    )

    st.dataframe(lead_df, use_container_width=True, hide_index=True)

    score_df = pd.DataFrame(
        {
            "Metric": ["Lead Score"],
            "Score": [lead.lead_score],
        }
    )
    fig = px.bar(score_df, x="Metric", y="Score", range_y=[0, 100], title="Lead Qualification Score")
    st.plotly_chart(fig, use_container_width=True)


def render_properties() -> None:
    st.subheader("🏘️ Novo Agent Synthetic Property Listings")
    st.caption("Novo Agent")

    properties = st.session_state.properties.copy()
    st.dataframe(
        properties[
            [
                "id",
                "title",
                "location",
                "price",
                "property_type",
                "listing_type",
                "bedrooms",
                "bathrooms",
                "size_sqm",
                "availability_status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_latest_matches() -> None:
    st.subheader("🎯 Latest Matching Properties")

    matches: pd.DataFrame = st.session_state.latest_matches

    if matches.empty:
        st.info("No property match yet. Send a qualified lead message first.")
        return

    for _, p in matches.iterrows():
        with st.container(border=True):
            st.markdown(f"### {p['title']}")
            st.write(p["description"])
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Location", p["location"])
            col2.metric("Price", f"R{p['price']:,.0f}")
            col3.metric("Bedrooms", int(p["bedrooms"]))
            col4.metric("Size", f"{int(p['size_sqm'])} sqm")
            st.caption(f"Demo listing URL: {p['listing_url']}")


def render_appointments() -> None:
    st.subheader("📅 Viewing Requests")

    if not st.session_state.appointments:
        st.info("No viewing request yet.")
        return

    appointment_rows = [asdict(appt) for appt in st.session_state.appointments]
    st.dataframe(pd.DataFrame(appointment_rows), use_container_width=True, hide_index=True)


def render_agent_actions() -> None:
    st.subheader("🧠 Agent Action Log")

    if not st.session_state.agent_actions:
        st.info("No agent actions logged yet.")
        return

    actions = pd.DataFrame(st.session_state.agent_actions)
    st.dataframe(actions, use_container_width=True, hide_index=True)


def render_architecture() -> None:
    st.subheader("🏗️ System Design")

    st.markdown(
        """
        ```text
        Streamlit UI
            |
            v
        Agent Orchestrator
            |
            |-- Lead Preference Extraction Tool
            |-- Lead Scoring Tool
            |-- Property Search Tool
            |-- Viewing Request Tool
            |-- Human Handoff Rule
            |-- Agent Action Logger
            |
            v
        Synthetic CRM + Property Database
            |
            v
        Business Metrics Dashboard
        ```
        """
    )

    st.markdown(
        """
        **Production upgrade path:**

        - Replace synthetic listings with an authorised agency database or official listing API.
        - Replace deterministic extraction with LLM structured output.
        - Add PostgreSQL for persistent storage.
        - Add FastAPI backend for API access.
        - Add calendar integration for confirmed viewing appointments.
        - Add WhatsApp, email or CRM integration.
        - Add LangGraph for stateful multi-step agent workflows.
        - Add observability for latency, tool success rate and conversion rate.
        """
    )


# -------------------------------------------------------------------
# Main app
# -------------------------------------------------------------------

def main() -> None:
    init_state()
    render_header()

    with st.sidebar:
        st.header("Demo Controls")
        if st.button("Reset demo", use_container_width=True):
            reset_demo()
            st.rerun()

        st.markdown("---")
        st.subheader("What this showcases")
        st.write(
            """
            - Real estate lead qualification
            - Structured information extraction
            - CRM-style record updates
            - Lead scoring
            - Property matching
            - Viewing request workflow
            - Human handoff logic
            - Business outcome metrics
            """
        )

        st.markdown("---")
        st.subheader("Best interview message")
        st.info(
            "This is an operations-focused agent. It demonstrates how an agency can automate lead qualification, property recommendation and viewing requests."
        )

    render_metrics()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Agent Chat",
            "CRM & Score",
            "Listings & Matches",
            "Appointments & Actions",
            "Architecture",
        ]
    )

    with tab1:
        render_chat()

    with tab2:
        render_crm_record()

    with tab3:
        render_properties()
        render_latest_matches()

    with tab4:
        render_appointments()
        render_agent_actions()

    with tab5:
        render_architecture()


if __name__ == "__main__":
    main()
