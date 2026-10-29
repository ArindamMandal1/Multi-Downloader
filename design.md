# Design Document: Immersive React & Three.js Multi-Part Downloader

## 1. Intent & Overview
The goal is to elevate the Local Multi-Part Game Downloader into a next-generation desktop web application featuring a stunning **React.js** interface powered by **Three.js** 3D visualizations and advanced animation frameworks (e.g., **Framer Motion** / **GSAP**). 

Running locally on `localhost:8000`, the app retains its robust Python FastAPI backend for bypassing Cloudflare (`cloudscraper`), handling multi-part downloads concurrently, and streaming real-time metrics, while delivering an immersive sci-fi/cyber-deck telemetry UI.

---

## 2. Goals, Non-Goals & Anti-Goals

### **Goals**
* **Immersive 3D Visuals:** A subtle, interactive Three.js particle mesh or node network in the background that reacts to active download speeds and states.
* **Buttery Smooth Animations:** Fluid page transitions, animated progress rings/bars, and interactive cards using Framer Motion.
* **Real-Time Telemetry:** Live streaming of download speed, ETA, downloaded bytes, and status via Server-Sent Events (SSE).
* **Seamless Local Integration:** Direct file streaming into the user's local `Downloads/<folder>` directory without browser popups.

### **Non-Goals**
* Cloud deployment or multi-user account authentication (remains a secure local tool).
* Heavy 3D rendering that consumes excessive GPU/CPU resources when idle.

### **Anti-Goals**
* Sacrificing download performance or reliability for visual flair.
* Complex build chains that complicate local setup.

---

## 3. Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│               React + Three.js Frontend                │
│            (Vite / Tailwind / Framer Motion)           │
│   ┌────────────────────────────────────────────────┐   │
│   │  • Interactive 3D Canvas Background (Three.js) │   │
│   │  • Glassmorphic Control & Queue Dashboard      │   │
│   │  • Real-time Animated Progress & Metric Cards  │   │
│   └───────▲────────────────────────────┬───────────┘   │
│           │                            │               │
│  HTTP POST│                            │ SSE Stream    │
│  (Queue)  │                            │ (Live Stats)  │
│           │                            ▼               │
┌───────────┴────────────────────────────┴───────────────┐
│                 Python FastAPI Backend                 │
│   • Queue Manager & Concurrency (asyncio)              │
│   • Cloudflare Bypass (`cloudscraper`)                 │
│   • Chunked File Streamer & Progress Broadcast         │
└──────────────────────────┬─────────────────────────────┘
                           ▼
             ┌───────────────────────────┐
             │   Local File System       │
             │   C:\Users\arind\Downloads│
             └───────────────────────────┘
```

### **Backend (`main.py`)**
* **Framework:** Python FastAPI + Uvicorn
* **Scraping:** `cloudscraper` for Cloudflare challenge resolution.
* **Communication:** `text/event-stream` SSE endpoint for pushing chunk progress and speeds to the frontend.

### **Frontend (`frontend/`)**
* **Framework:** React 18+ (bundled with Vite or loaded via ESM/CDN for zero-install complexity).
* **3D Engine:** Three.js for interactive particle/wave background.
* **Animation:** Framer Motion for UI entering/exiting animations and smooth number counters.
* **Styling:** Tailwind CSS for modern glassmorphism UI styling.

---

## 4. Key UI Components & 3D Features

1. **Three.js Background Canvas (`DownloadSpace.jsx`):**
   * A responsive 3D particle grid or data stream visualization.
   * Particles pulse and rotate faster when downloads are active.
   * Click/Hover interactivity for subtle parallax effect.

2. **Control & Batch Input Panel:**
   * Folder name input field.
   * Multi-line textarea for pasting batch download links.
   * Animated start/pause/cancel controls.

3. **Active Download Cards:**
   * Animated progress bars with gradient glows.
   * Live speed indicator (MB/s), elapsed time, and dynamic ETA.
   * Status badges (`Waiting`, `Downloading`, `Completed`, `Failed`).

---

## 5. Implementation Roadmap
1. **Phase 1:** Setup FastAPI backend with SSE progress streaming and cloudscraper download engine.
2. **Phase 2:** Initialize React frontend structure with Tailwind CSS and Framer Motion.
3. **Phase 3:** Integrate Three.js 3D background canvas reacting to state.
4. **Phase 4:** Connect frontend to backend SSE stream and test end-to-end multi-part downloads.
