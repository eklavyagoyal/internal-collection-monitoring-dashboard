# Role: Senior Full-Stack Python Engineer (Reflex & NoSQL Expert)
# Project: "Nexus-Track" - Real-Time Multi-User Participant Dashboard

## 1. Project Context
I need to build a high-reliability, real-time internal dashboard to track participant data collections.
- **The Workflow:** Sync appointments from a Google Calendar booking page, assign devices (Android/iOS), and "cross off" participants as they finish.
- **The Core Tech:** Use **Reflex** (for the frontend/state management) and **MongoDB** (for data persistence).
- **Multi-User Sync:** Since multiple researchers will be using this simultaneously on different devices (Android/iOS/Laptops), use Reflex's global state to ensure real-time updates across all clients.

## 2. Technology Stack (Containerized)
- **Frontend/Backend:** Reflex (Python-based React/FastAPI wrapper).
- **Database:** MongoDB (using `motor` for asynchronous I/O).
- **Orchestration:** Docker Compose (App + MongoDB + Redis for Reflex state).
- **APIs:** Google Calendar API (v3).

## 3. Feature Specifications

### A. Google Calendar Integration
- Fetch today's appointments from a Google Workspace Calendar.
- Extract: Name, Email, and Appointment Time.
- **Logic:** Use an 'Upsert' (update or insert) strategy using the Google Event ID as the unique key in MongoDB to ensure calendar refreshes don't overwrite manual device assignments.

### B. The Participant Grid (Real-Time UI)
- **Progress Header:** A real-time progress bar ($X/N$ participants) and a "Live" status indicator.
- **Device Assignment:** Dropdowns for 'Platform' (Android, iOS) and 'Model Tag' (Generic strings).
- **Status Flow:** Three states: `Pending` -> `In-Progress` -> `Completed`.
- **Visual Feedback:** - `In-Progress`: Highlight the row or add a "Working" badge.
  - `Completed`: Strikethrough the name and dim the row opacity.

### C. Data & Concurrency
- **Timestamps:** Automatically capture `start_time` and `end_time` when statuses change.
- **No Data Loss:** Every state change must be awaited and persisted to MongoDB immediately.

## 4. Implementation Deliverables
Please provide a complete, production-ready directory structure:
1. **`docker-compose.yml`:** Setup for the Reflex app, a MongoDB container, and a Redis container (required for Reflex multi-tab state).
2. **`rxconfig.py`:** Standard Reflex configuration.
3. **`nexus_track/state.py`:** The `rx.State` class managing the participant list and MongoDB mutations.
4. **`nexus_track/nexus_track.py`:** The UI layout logic (optimized for mobile/tablet viewing).
5. **`nexus_track/backend/`:** Modules for `mongo_client.py` and `gcal_sync.py`.
6. **`requirements.txt`:** Include `reflex`, `motor`, `google-api-python-client`, and `google-auth-oauthlib`.

## 5. Setup Instructions
- Provide a `README.md` detailing how to set up the Google Cloud `credentials.json`.
- Explain how to run `docker-compose up`.
- Ensure the MongoDB data is stored in a Docker Volume for local persistence.

## 6. Thinking Guidance
Use Adaptive Thinking to handle the Reflex "Background Task" for the Google Calendar sync. It should run periodically or via a "Sync Now" button without blocking the UI for researchers.
