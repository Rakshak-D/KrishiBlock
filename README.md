# Hackathon Project

Team Name: Bumblebee

## Problem Statement
Small farmers and buyers still struggle with fragmented agri-commerce workflows. Listing produce, discovering verified supply, handling payments safely, confirming delivery, and proving product authenticity often happen across disconnected tools or informal channels. That creates low trust, weak traceability, and a poor experience for both users and judges evaluating the solution.

## Solution
AgriChain is a unified agri-commerce platform that brings farmer listing management, buyer marketplace discovery, escrow-backed order handling, public product verification, and a visible blockchain trust ledger into one web application. Farmers can publish and manage crop listings, buyers can discover supply and place orders, deliveries can be confirmed through a clear delivery-code flow, and judges can open the trust ledger to see how listing hashes and chained wallet events provide traceability and tamper visibility.

## Tech Stack
- Frontend: React, Vite, React Router, TanStack Query, Zustand, CSS
- Backend: FastAPI, SQLAlchemy, Pydantic, Uvicorn, Redis-backed session/rate limiting
- Database: PostgreSQL for primary app data storage, with SQLite support for local testing

## How to Run
1. Clone the repository and open the project root.
2. Create and fill the required environment files:
   - `agrichain/backend/.env`
   - `agrichain/frontend/.env`
3. Start the backend:
   - `cd agrichain/backend`
   - activate your virtual environment
   - `uvicorn app.main:app --reload`
4. Start the frontend in a new terminal:
   - `cd agrichain/frontend`
   - `npm install`
   - `npm run dev`
5. Open the app in your browser at `http://localhost:5173`.
