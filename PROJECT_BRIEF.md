# Project Brief

## Project title

Real Estate Agentic AI Assistant for Lead Qualification and Viewing Requests

## Business problem

Real estate agencies often lose revenue because leads are not contacted, qualified or routed quickly enough. This demo shows how an agentic AI system can automate the first layer of real estate operations by qualifying leads, recommending suitable listings and requesting viewings.

## Solution

The application simulates an AI operations assistant that:

1. receives a lead message
2. extracts structured property requirements
3. updates a CRM-style lead record
4. calculates a lead score
5. searches a synthetic property listing database
6. recommends suitable listings
7. creates a viewing request
8. flags high-value leads for human handoff
9. displays business metrics and action logs

## Why this is relevant to NovoAgent

NovoAgent builds autonomous AI agents for real estate operations. This demo is aligned with that work because it focuses on operational workflows, measurable outcomes, lead qualification, prospect engagement and reusable agent patterns.

## Technical design

The demo uses Streamlit for fast presentation, but the architecture maps directly to a production backend:

- UI layer: Streamlit now, React/Next.js in production
- Agent orchestrator: workflow controller
- Tools: extraction, scoring, property search, appointment request, handoff
- Data layer: synthetic in-memory data now, PostgreSQL in production
- Integration layer: CRM, calendar, email/WhatsApp in production
- Observability: action logs and metrics

## Production improvements

- FastAPI backend
- PostgreSQL database
- pgvector or vector database for RAG
- LangGraph workflow orchestration
- LLM structured output validation
- CRM integration
- Google Calendar or Calendly integration
- WhatsApp Business API
- Authentication and role-based access
- Docker deployment
- CI/CD pipeline
- Monitoring and analytics
