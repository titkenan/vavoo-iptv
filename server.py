#!/usr/bin/env python3
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vavoo Turkey - Static Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

M3U_FILE = "vavoo_turkiye.m3u"
EPG_FILE = "vavoo_epg.xml"

@app.get("/")
async def root():
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    return {
        "service": "Vavoo Turkey IPTV",
        "endpoints": {
            "playlist": f"{base}/playlist.m3u",
            "epg": f"{base}/epg.xml"
        }
    }

@app.get("/playlist.m3u")
async def playlist():
    if not os.path.exists(M3U_FILE):
        raise HTTPException(404, "M3U not found")
    return FileResponse(M3U_FILE, media_type="application/x-mpegURL")

@app.get("/epg.xml")
async def epg():
    if not os.path.exists(EPG_FILE):
        raise HTTPException(404, "EPG not found")
    return FileResponse(EPG_FILE, media_type="application/xml")

@app.get("/status")
async def status():
    from datetime import datetime
    m3u_exists = os.path.exists(M3U_FILE)
    return {
        "status": "ok" if m3u_exists else "waiting",
        "m3u_exists": m3u_exists,
        "m3u_size": os.path.getsize(M3U_FILE) if m3u_exists else 0
    }