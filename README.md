# NovoStyle Real Estate Agentic AI - Streamlit Demo

A complete Streamlit demo for an Agentic AI Architect job application.

This project showcases a production-style real estate operations agent that can:

- qualify buyer/renter leads
- extract structured requirements
- calculate a lead score
- search synthetic property listings
- recommend matching properties
- request a property viewing
- update a CRM-style lead record
- show business metrics
- show agent action logs

## Why synthetic listings?

This demo uses synthetic property listings rather than scraping live property websites. For a real client deployment, connect the same architecture to an authorised agency database, CRM, MLS-style feed, or official property listing API.

## Run locally

```bash
cd novo_streamlit_real_estate_agent
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Mac/Linux

```bash
source .venv/bin/activate
```

Then install and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Suggested demo prompts

```text
I want to rent a 2-bedroom apartment in Claremont. My budget is R12,000 and I need it this week.
```

```text
I want to buy a 3-bedroom house in Sandton. Budget around R2.5 million. I want to view tomorrow.
```

```text
Can I book a viewing tomorrow afternoon?
```

## How to explain this project

I built a Streamlit-based real estate agentic AI demo that simulates a production workflow for real estate agencies. The agent qualifies leads, extracts structured property requirements, scores the lead, searches synthetic listings, recommends matching properties, requests viewings, updates a CRM-style record, and reports business metrics. The project is intentionally designed as an operations system, not a simple chatbot.
