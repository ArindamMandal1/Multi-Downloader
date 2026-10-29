# Architecture & Tech Stack: Local Multi-Part Game Downloader Web App

## 1. Overview
A lightweight, local web application running entirely on your machine (`localhost`). It provides a modern browser-based dashboard to paste multi-part download links (from sites like FitGirl repacks / fuckingfast.co), bypasses Cloudflare automatically, manages download queues with real-time progress bars, and saves files directly into your local `Downloads/<folder>` directory without any browser popups.

---

## 2. Tech Stack

### **Backend**
* **Language:** Python 3.11+
* **Framework:** **FastAPI** (High performance, modern, asynchronous support, built-in docs)
* **ASGI Server:** **Uvicorn** (Lightning-fast server to run FastAPI)
* **Scraping / Bypass:** `cloudscraper` (Handles Cloudflare JS challenges)
* **Concurrency:** Python `asyncio` + `concurrent.futures` (Allows downloading multiple parts simultaneously or sequentially with non-blocking UI updates)

### **Frontend**
* **Structure:** Single HTML file (`index.html`)
* **Styling:** **Tailwind CSS** (via CDN for sleek, modern dark-mode UI)
* **Icons:** **Lucide Icons** (Clean, modern iconography)
* **Real-time Updates:** **Server-Sent Events (SSE)** or **WebSockets** (Pushes download progress, speed, ETA, and status from Python backend to browser in real time)

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                      Web Browser                       │
│              (http://localhost:8000)                   │
│   ┌────────────────────────────────────────────────┐   │
│   │               Frontend Dashboard               │   │
│   │  • Folder Name Input                           │   │
│   │  • Multi-line Link Textarea                    │   │
│   │  • Live Progress Bars / Speed / ETA Cards      │   │
│   └───────────────▲────────────────────────┬─────────┘   │
│                   │                        │             │
│        HTTP POST  │                        │ SSE / WS    │
│       (Start Job) │                        │ (Live Stats)│
│                   │                        ▼             │
┌───────────────────┴────────────────────────────────────┐
│                    Python FastAPI Backend              │
│   ┌────────────────────────────────────────────────┐   │
│   │                API Endpoints                   │   │
│   │  • POST /api/download (Queue manager)          │   │
│   │  • GET  /api/progress (Event stream)           │   │
│   └────────────────────────┬───────────────────────┘   │
│                            │                           │
│                            ▼                           │
│   ┌────────────────────────────────────────────────┐   │
│   │                Download Engine                 │   │
│   │  1. cloudscraper (Bypass Cloudflare)           │   │
│   │  2. POST /go (Resolve Hx-Redirect CDN URL)     │   │
│   │  3. Stream chunks & track progress             │   │
│   └────────────────────────┬───────────────────────┘   │
└────────────────────────────┼───────────────────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │   Local File System           │
             │   C:\Users\arind\Downloads\   │
             │   └── <Folder Name>\          │
             │       ├── part01.rar          │
             │       └── part02.rar          │
             └───────────────────────────────┘
```

---

## 4. Component Breakdown

### **A. Backend (`main.py`)**
1. **Queue & State Manager:** Tracks overall progress (Completed / Failed / In Progress), current speed, and active threads.
2. **Cloudflare Resolver:** Reuses the proven `cloudscraper` + `Hx-Redirect` logic from our current script.
3. **Streamer & Progress Broadcaster:** Downloads files in buffered chunks, calculating speed and ETA, and pushes updates to connected browser clients.

### **B. Frontend (`static/index.html`)**
1. **Control Panel:** Input fields for folder name and batch link pasting.
2. **Dashboard Grid / List:** Real-time status cards for each file showing:
   * Filename
   * Visual progress bar (`%` complete)
   * Downloaded size / Total size
   * Current speed (MB/s) and ETA
   * Status badge (`Waiting`, `Downloading`, `Completed`, `Failed`)

---

## 5. Security & Isolation
* **Local-only binding:** Server runs exclusively on `127.0.0.1` (inaccessible from the outside internet).
* **Direct File IO:** Files write straight to the user's Downloads folder without temp-dir overhead or browser restrictions.
