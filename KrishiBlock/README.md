# KrishiBlock

KrishiBlock is now the merged product workspace for the code in this repository: the original backend and traceability system, the stronger buyer/farmer dashboard ideas from `kisanlink`, and the bot-first flow concepts from `farm_bot`.

The current build gives you one webapp with:
- web registration and OTP login
- local and global agricultural marketplaces
- farmer listing, dispatch, and payout operations
- buyer ordering, escrow, and delivery confirmation
- bot simulator using the conversation engine
- QR verification and public traceability pages
- mandi-based pricing guidance for listings

## Stack

- Backend: FastAPI, async SQLAlchemy, PostgreSQL, Redis, APScheduler
- Frontend: React, Vite, React Query, Zustand
- Messaging: Twilio WhatsApp sandbox when configured
- Verification: QR codes plus simulated SHA-256 transaction tracing

## What You Need To Fill

Update only the environment files before running:
- `backend/.env.example` -> copy to `backend/.env`
- `frontend/.env.example` -> copy to `frontend/.env` if you want a custom API URL

## Local Setup

1. Start services:
   - `cd "C:\RAKSHAK\MY CODE\team-bumblebee\KrishiBlock"`
   - `docker compose up -d`
2. Start the backend:
   - `cd "C:\RAKSHAK\MY CODE\team-bumblebee\KrishiBlock\backend"`
   - create and activate a virtual environment
   - `pip install -r requirements.txt`
   - `alembic upgrade head`
   - `uvicorn app.main:app --reload`
3. Start the frontend:
   - `cd "C:\RAKSHAK\MY CODE\team-bumblebee\KrishiBlock\frontend"`
   - `npm install`
   - `npm run dev`

## Local URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- Bot simulator: `http://localhost:5173/bot`

## Primary Flows

### Web onboarding

1. Open `http://localhost:5173/login`
2. Create a new farmer or buyer account directly on the web
3. Use OTP login for returning users
4. Open `/dashboard` for the merged workspace

### Farmer flow

1. Create an account as a farmer
2. Open `/dashboard`
3. Publish or edit listings
4. Monitor incoming orders and mark them dispatched
5. Share the release key with the buyer at handoff

### Buyer flow

1. Create an account as a buyer
2. Add funds in the wallet tab
3. Browse `/market` or `/global`
4. Place an order from a listing page
5. Confirm delivery in `/dashboard` using the release key

### Bot flow

1. Open `/bot`
2. Use a test phone number
3. Send `HI` or `MENU`
4. Walk through registration, wallet, or ordering flows

### Verification flow

1. Open `/listing/:id` for the commercial detail page
2. Open `/verify/:id` for the public proof page
3. Scan or share the QR from any listing

## Verification Commands

From `backend`:
- `venv\Scripts\python -m pytest tests -v`
- `venv\Scripts\python -m compileall app`

From `frontend`:
- `npm run build`

## Honesty Notes

- Wallet balances, top-ups, withdrawals, and escrow are simulated in the database.
- The blockchain layer is a simulated SHA-256 hash chain, not a public blockchain.
- QR verification pages display app-managed traceability data, not third-party certification.
- Mandi pricing uses the government API when available and falls back to cached defaults on failure.
- Twilio and ngrok are optional for local development because the bot simulator and development OTP fallback still work.


