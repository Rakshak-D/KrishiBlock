# Team Bumblebee

KrishiBlock is Team Bumblebee's agri-commerce and traceability platform. The app combines farmer listings, buyer marketplace flows, escrow-backed ordering, public verification pages, and a simulated blockchain ledger into one workspace.

## Repository Layout

- `KrishiBlock/backend`: FastAPI API, data models, services, Alembic migrations, and tests
- `KrishiBlock/frontend`: React + Vite web app
- `KrishiBlock/docker-compose.yml`: local infrastructure for PostgreSQL and Redis

## Local Setup

1. Clone the repository and open the root folder.
2. Copy `KrishiBlock/backend/.env.example` to `KrishiBlock/backend/.env`.
3. Optionally copy `KrishiBlock/frontend/.env.example` to `KrishiBlock/frontend/.env` if you want a custom API URL.
4. Start infrastructure:
   - `cd KrishiBlock`
   - `docker compose up -d`
5. Start the backend:
   - `cd KrishiBlock/backend`
   - create and activate a virtual environment
   - `pip install -r requirements.txt`
   - `alembic upgrade head`
   - `uvicorn app.main:app --reload`
6. Start the frontend in a second terminal:
   - `cd KrishiBlock/frontend`
   - `npm install`
   - `npm run dev`

## Verification

- Backend tests: `cd KrishiBlock/backend && venv\Scripts\python -m pytest tests -v`
- Backend compile check: `cd KrishiBlock/backend && venv\Scripts\python -m compileall app`
- Frontend production build: `cd KrishiBlock/frontend && npm run build`

## Notes

- The blockchain layer is simulated for traceability demos.
- Wallet, escrow, and payout flows are application-managed demo flows.
- More detailed product and flow notes live in `KrishiBlock/README.md`.



