import asyncio
import os
import json
import time
from typing import List
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import download_parts

app = FastAPI(title="Multi-Part Downloader 3D")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active download status and queue state
download_state = {
    "folder": "",
    "total": 0,
    "completed": 0,
    "active": 0,
    "failed": 0,
    "cancelled": 0,
    "items": []
}

# Control flag for cancellation
cancel_requested = False

class DownloadRequest(BaseModel):
    folder_name: str
    links: List[str]

@app.get("/", response_class=HTMLResponse)
async def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found</h1>"

async def background_downloader(folder_name: str, links: List[str]):
    global cancel_requested
    cancel_requested = False

    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads_dir):
        downloads_dir = os.getcwd()
    dest_dir = os.path.join(downloads_dir, folder_name)
    os.makedirs(dest_dir, exist_ok=True)

    download_state["folder"] = folder_name
    download_state["total"] = len(links)
    download_state["completed"] = 0
    download_state["active"] = len(links)
    download_state["failed"] = 0
    download_state["cancelled"] = 0

    items = []
    for i, url in enumerate(links):
        fallback_name = download_parts.get_filename_from_url(url, i)
        items.append({
            "id": i + 1,
            "url": url,
            "name": fallback_name,
            "pct": 0.0,
            "status": "waiting",
            "speed": 0.0
        })
    download_state["items"] = items

    for i, item in enumerate(items):
        if cancel_requested:
            item["status"] = "cancelled"
            download_state["cancelled"] += 1
            continue

        item["status"] = "downloading"
        url = item["url"]
        dest_path = ""
        try:
            # Resolve URL using cloudscraper
            real_url, fname_hint = await asyncio.to_thread(download_parts.resolve_download_url, url)
            if cancel_requested:
                item["status"] = "cancelled"
                download_state["cancelled"] += 1
                continue

            if fname_hint:
                item["name"] = fname_hint

            dest_path = os.path.join(dest_dir, item["name"])
            base, ext = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = f"{base}_{counter}{ext}"
                counter += 1

            import urllib.request
            start_time = time.time()
            downloaded = 0

            req = urllib.request.Request(real_url)
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', -1))
                block_size = 8192
                with open(dest_path, 'wb') as out_file:
                    while True:
                        if cancel_requested:
                            break
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        out_file.write(buffer)
                        downloaded += len(buffer)

                        elapsed = time.time() - start_time
                        if total_size > 0:
                            downloaded_clamped = min(downloaded, total_size)
                            item["pct"] = (downloaded_clamped / total_size) * 100
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        item["speed"] = speed / (1024 * 1024) # MB/s

            if cancel_requested:
                item["status"] = "cancelled"
                download_state["cancelled"] += 1
                if dest_path and os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
            else:
                item["pct"] = 100.0
                item["status"] = "done"
                download_state["completed"] += 1
        except Exception:
            if cancel_requested:
                item["status"] = "cancelled"
                download_state["cancelled"] += 1
                if dest_path and os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
            else:
                item["status"] = "failed"
                item["pct"] = 0.0
                download_state["failed"] += 1
        finally:
            item["speed"] = 0.0

    # Recalculate active count
    download_state["active"] = sum(1 for it in download_state["items"] if it["status"] == "downloading")

@app.post("/api/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    global cancel_requested
    cancel_requested = False
    links = [l.strip() for l in req.links if l.strip()]
    if not links:
        return {"status": "error", "message": "No links provided"}

    background_tasks.add_task(background_downloader, req.folder_name, links)
    return {"status": "started", "total": len(links)}

@app.post("/api/cancel")
async def cancel_downloads():
    global cancel_requested
    cancel_requested = True

    # Immediately mark all waiting and currently downloading items as cancelled
    active_count = 0
    for item in download_state["items"]:
        if item["status"] in ["waiting", "downloading"]:
            item["status"] = "cancelled"
            download_state["cancelled"] += 1
        elif item["status"] == "downloading":
            active_count += 1
    download_state["active"] = 0
    return {"status": "cancelling"}

@app.get("/api/progress")
async def progress_stream():
    async def event_generator():
        while True:
            # Keep active count accurate
            download_state["active"] = sum(1 for it in download_state["items"] if it["status"] == "downloading")
            yield f"data: {json.dumps(download_state)}\n\n"
            await asyncio.sleep(0.3)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
