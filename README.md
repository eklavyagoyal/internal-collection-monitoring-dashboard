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
| **Inline Status** | Fixed `Booked ↔ Completed` workflow with completion timestamps |
| **Platform & Model Tags** | Assign hardware platform + AI model version per participant |
| **Inline Notes** | Freeform notes field on every row, saved on blur |
| **Issue Workflow** | Flag participant issues, preview them inline, filter to exceptions only, and resolve them quickly |
| **Bulk Actions** | Select visible rows → bulk mark `Booked` / `Completed`, assign platform/model tags, or admin-delete selected rows |
| **Sorting** | Click column headers to sort by time or participant name |
| **Search** | Filter by name, email, platform, model tag, notes, or issue comment inside the current participant scope |
| **CSV Export** | Export `Current filters`, `Selected day`, or `All dates` with scope-aware filenames |

### Calendar Integration
| Feature | Detail |
|---|---|
| **Multi-Calendar Support** | Campaign forms keep a simple single-calendar path by default and can switch to Advanced mode for multiple calendar sources |
| **Keyword Filter** | Only import events whose title matches a keyword (e.g. "Worldcoin") |
| **Calendar Discovery** | Settings plus create/edit forms can list accessible calendars with one-click ID copy |
| **Booking Tool Support** | Calendly / Cal.com / Acuity events sync automatically via Google Calendar |

### Platform
| Feature | Detail |
|---|---|
| **Real-Time Multi-User** | 10-second auto-refresh via MongoDB, pushed to all clients over WebSocket |
| **Freshness Signals** | Navbar + campaign cards distinguish live refresh, stale syncs, failed attempts, and never-synced campaigns |
| **Date Navigation** | Visible `Previous / Today / Next` day context on dashboard and campaign detail pages |
| **Dark / Light Mode** | Toggle with a single click |
| **Configurable Labels** | Add/remove platforms and model tags from Settings with usage-aware safety checks — no redeploy needed |
| **Admin Safety Rails** | Admin PIN gates campaign/settings mutations and protected actions write lightweight audit events |

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
    │   ├── participant_row.py  # Participant row with bulk selection, issue actions, and notes
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

Every campaign now tracks:
- the **last attempted sync**
- the **last successful sync**
- the **last sync error** (if the most recent attempt failed)

That lets the UI keep failed campaigns red until a real successful refresh clears the error, instead of silently drifting back to a reassuring green state.

### Real-Time Multi-User
A background loop polls MongoDB every **10 seconds** and pushes fresh state to all connected clients via Reflex's WebSocket manager. **Redis** backs the state manager so every browser tab and device stays in sync instantly.

The navbar uses that refresh loop for a truthful live-status badge:
- **Live data** only appears after a recent successful refresh
- **Refresh delayed** appears when the live view is older than expected
- **Refresh error** appears when the last refresh attempt failed after the last known good refresh

### Design System
All colours, shadows, radii, and component helpers live in `components/design_tokens.py` — `glass_card()`, `section_header()`, `form_field()`, `progress_bar()`, `status_dot()` — used consistently across every page.

### Status Timestamps
- The live workflow uses two fixed statuses: **Booked** and **Completed**
- Marking a participant as **Completed** captures `end_time`
- Returning a participant to **Booked** clears completion timestamps

### Admin Safety
- Campaign creation, campaign editing, campaign deletion, bulk deletion, and settings mutation are gated behind admin mode
- Admin PINs are stored with PBKDF2 hashing instead of raw SHA-256
- Protected changes write lightweight audit events for visibility on the Settings page
- Settings now block deleting platforms or model tags that are still referenced by campaigns or participant rows

### Campaign Progress
- Overall campaign progress is based on **unique participants** across the full campaign
- Participants are deduplicated by normalised email when available
- Rows without an email fall back to their event ID, so blank-email bookings are never merged accidentally
- Daily tables still show appointment rows for the currently loaded date range/view

### Participant Operations
- The participant table now has an explicit scope: **Selected day only** or **All dates**
- One-day sync and **Selected day** export always use the visible selected date
- Bulk selection follows the current visible filtered view, so hidden rows are never changed by accident
- Row-level platform, model, status, notes, and issue updates save optimistically and show lightweight save feedback
- Issue comments are distinct from routine notes and stay included in CSV exports
- Changing the selected day clears old date-scoped sync banners so the page never looks fresher than the current view really is
- Create/edit forms keep single-calendar setup as the default path, with an Advanced multi-calendar mode when one campaign needs multiple sources
- Default platform and model-tag choices are constrained to the selected campaign platforms and their configured model tags

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `credentials.json not found` | Download OAuth Desktop-app credentials from Google Cloud Console |
| `No valid token.json` in Docker / headless mode | Run `python generate_token.py` on a machine with a browser, then retry the sync |
| Token refresh error | Delete `token.json` and re-run `python generate_token.py` |
| Calendar not found / 404 during sync | Check the campaign calendar ID and confirm the Google account can access it |
| Permission denied / 403 during sync | Re-authorize Google Calendar access and confirm the account can read the configured calendar |
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
