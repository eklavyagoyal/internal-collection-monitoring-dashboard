# Nexus-Track

> Production-grade, real-time participant tracking dashboard for data-collection campaigns.

Built with **Reflex** (Python → React + FastAPI), **MongoDB** (async via Motor), **Redis** (multi-tab state sync), and the **Google Calendar API**. Syncs appointments from any Google Calendar, lets researchers track participant status live across every connected browser, and gives ops teams a single pane of glass across all active campaigns.

---

## Features

### Campaign Management
| Feature | Detail |
|---|---|
| **Multi-Campaign Dashboard** | Grid of campaign cards with live progress bars, active / paused / archived status |
| **Campaign Search & Filter** | Real-time search across names + toggle to show/hide archived campaigns |
| **Archive / Unarchive** | Soft-delete campaigns without losing any data |
| **External Links** | Attach Notion, Linear, and booking-page URLs per campaign |

### Participant Tracking
| Feature | Detail |
|---|---|
| **Google Calendar Sync** | Upserts by Event ID — manual edits are never overwritten on re-sync |
| **Manual Add** | Add participants without a calendar event |
| **Inline Status** | `Pending → In-Progress → Completed` with automatic `start_time` / `end_time` stamps |
| **Platform & Model Tags** | Assign hardware platform + AI model version per participant |
| **Inline Notes** | Freeform notes field on every row, saved on blur |
| **Bulk Actions** | Select multiple rows → bulk set status / platform / model tag |
| **Sorting** | Click any column header to sort asc/desc (time, name, status) |
| **Search** | Filter by name, email, platform, or model tag |
| **CSV Export** | Download all participants for a campaign / date |

### Calendar Integration
| Feature | Detail |
|---|---|
| **Multi-Calendar Support** | Each campaign targets its own Calendar ID |
| **Keyword Filter** | Only import events whose title matches a keyword (e.g. "Worldcoin") |
| **Calendar Discovery** | Settings page lists all accessible calendars with one-click ID copy |
| **Booking Tool Support** | Calendly / Cal.com / Acuity events sync automatically via Google Calendar |

### Platform
| Feature | Detail |
|---|---|
| **Real-Time Multi-User** | 10-second auto-refresh via MongoDB, pushed to all clients over WebSocket |
| **Date Navigation** | Step forward/back by day to review historical data |
| **Dark / Light Mode** | Toggle with a single click |
| **Configurable Labels** | Add/remove platforms, model tags, and statuses from Settings — no redeploy needed |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Browser Clients                    │
│   (laptops, tablets — all stay in sync)         │
└──────────────────┬──────────────────────────────┘
                   │  WebSocket (Reflex)
┌──────────────────▼──────────────────────────────┐
│         Reflex App  (Python 3.11)               │
│  nexus_track/state.py   ← global reactive state │
│  nexus_track/backend/   ← Mongo + GCal modules  │
│  nexus_track/pages/     ← 5 page components     │
│  nexus_track/components/← reusable UI + tokens  │
├──────────────────┬───────────┬──────────────────┤
│    MongoDB 7     │  Redis 7  │ Google Calendar   │
│  (persistence)   │  (state)  │      API v3       │
└──────────────────┴───────────┴──────────────────┘
```

---

## Prerequisites

- **Docker** & **Docker Compose** v2+
- A **Google Cloud** project with the **Calendar API** enabled

---

## Google Calendar Setup

1. Open [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Enable the **Google Calendar API** on your project.
3. **Create Credentials → OAuth 2.0 Client ID → Desktop app**.
4. Download the JSON and save it as **`credentials.json`** in the `v1/` directory.
5. Generate `token.json` locally before the first Docker run:

```bash
pip install google-api-python-client google-auth-oauthlib
python generate_token.py
```

> The browser OAuth consent flow runs once, then `token.json` is written and reused on every subsequent launch.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/eklavyagoyal/internal-collection-monitoring-dashboard.git
cd internal-collection-monitoring-dashboard

# 2. Copy env template and fill in values
cp .env.example .env

# 3. Place credentials.json and token.json here (see above)

# 4. Build and start all services
docker compose up --build

# 5. Open the dashboard
open http://localhost:3100
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3100 |
| Backend API / WebSocket | http://localhost:8100 |

---

## Local Development (no Docker)

```bash
# Start MongoDB and Redis locally first
brew services start mongodb-community
brew services start redis

pip install -r requirements.txt
reflex init
reflex run
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://mongo:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `nexus_track` | Database name |
| `REDIS_URL` | `redis://redis:6379` | Redis for Reflex multi-tab state |
| `API_URL` | `http://localhost:8000` | Backend API / WebSocket URL |

---

## Project Structure

```
├── docker-compose.yml          # App + MongoDB + Redis
├── Dockerfile                  # Python 3.11-slim + Node 20
├── requirements.txt
├── rxconfig.py
├── .env.example
├── credentials.json            # (you provide) Google OAuth credentials
├── token.json                  # (auto-generated) Google OAuth token
│
└── nexus_track/
    ├── nexus_track.py          # Route registration + global CSS
    ├── state.py                # NexusState — all reactive state & event handlers
    │
    ├── backend/
    │   ├── mongo_client.py     # Motor async CRUD for campaigns & participants
    │   └── gcal_sync.py        # Google Calendar fetch + upsert logic
    │
    ├── components/
    │   ├── design_tokens.py    # Centralised design system (colors, radii, helpers)
    │   ├── navbar.py           # Sticky top bar with breadcrumb support
    │   ├── campaign_card.py    # Dashboard campaign card with gradient stripe
    │   ├── participant_row.py  # Participant row with checkbox & inline notes
    │   └── stat_card.py        # KPI stat card (fixed 96px height)
    │
    └── pages/
        ├── dashboard.py        # /  — Campaign grid + global stats
        ├── campaign_detail.py  # /campaign/[id] — Participants + bulk actions
        ├── new_campaign.py     # /new — Create campaign form
        ├── edit_campaign.py    # /campaign/[id]/edit — Edit campaign form
        └── settings.py        # /settings — Labels + calendar discovery
```

---

## How It Works

### Calendar Sync
Each **Sync** call runs as a `@rx.event(background=True)` handler, offloading the Google API call via `asyncio.to_thread` to avoid blocking the event loop. Events are upserted with `$set` (calendar fields) + `$setOnInsert` (manual fields), keyed on `google_event_id` — so editing notes or status is always safe across re-syncs.

### Real-Time Multi-User
A background loop polls MongoDB every **10 seconds** and pushes fresh state to all connected clients via Reflex's WebSocket manager. **Redis** backs the state manager so every browser tab and device stays in sync instantly.

### Design System
All colours, shadows, radii, and component helpers live in `components/design_tokens.py` — `glass_card()`, `section_header()`, `form_field()`, `progress_bar()`, `status_dot()` — used consistently across every page.

### Status Timestamps
- Transitioning to **In-Progress** captures `start_time`
- Transitioning to **Completed** captures `end_time`
- Resetting to **Pending** clears both timestamps

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `credentials.json not found` | Download OAuth Desktop-app credentials from Google Cloud Console |
| Token refresh error | Delete `token.json` and re-run `python generate_token.py` |
| MongoDB connection timeout | Verify Mongo container is healthy and `MONGO_URI` is correct in `.env` |
| Empty participant list | Click **Sync Calendar** on the campaign detail page |
| Changes not visible on another device | Confirm Redis is running and `REDIS_URL` is set |
| Port already in use | Change `3100:3000` / `8100:8000` in `docker-compose.yml` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Reflex (Python → React / Next.js) |
| Backend | Reflex (Python FastAPI + WebSocket) |
| Database | MongoDB 7 via Motor (async) |
| State sync | Redis 7 Alpine |
| Calendar | Google Calendar API v3, OAuth2 Desktop flow |
| Container | Docker Compose, Python 3.11-slim + Node 20 |
| Design | Inter font, Radix UI primitives, indigo-violet design token system |

---

## License

MIT
