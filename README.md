# SatışBot

AI sales assistant for online stores: answers customers in Telegram and web chat in Azerbaijani and Russian, finds products in the catalog, collects orders, and hands complex cases over to a human operator.

## Problem

Small online stores in Baku sell mostly through Telegram and Instagram, and staff answer the same questions by hand all day: "Is size 42 available?", "How much is delivery?". Messages sent at night or during busy hours go unanswered, and the customer buys elsewhere. SatışBot answers instantly using the store's real catalog and passes discounts, complaints and uncertain cases to an operator.

## Planned features

- Product search in natural language with price, size and stock filters (RAG)
- Prices and stock always taken from the database, never invented
- Human handoff: discount requests, complaints and uncertain answers go to an operator panel
- Conversation memory and customer profile (size, city, preferences)
- Channels: Telegram, web chat; architecture ready for WhatsApp and Instagram
- Evaluation on a golden dataset and full tracing in LangSmith

## Tech stack

Python · FastAPI · LangGraph · LangChain · Claude · Qdrant · PostgreSQL · Redis · n8n · Streamlit · LangSmith · Docker · DigitalOcean

## Status

🚧 In development — Day 0: project skeleton

## Getting started

_Coming on Day 1: `docker compose up`._