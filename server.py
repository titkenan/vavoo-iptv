#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render.com Statik Sunucu
- Sadece M3U ve EPG dosyalarını sunar
- Hiçbir işlem yapmaz (hızlı ve stabil)
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vavoo Turkey - Static Server")

# CORS (her yerden erişim için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dosya yolları
M3U_FILE = "vavoo_turkiye.m3u"
EPG_FILE = "vavoo_epg.xml"

@app.get("/")
async def root():
    """Ana sayfa"""
    base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    return {
        "service": "Vavoo Turkey IPTV",
        "type": "Static M3U Server",
        "endpoints": {
            "playlist": f"{base_url}/playlist.m3u",
            "epg": f"{base_url}/epg.xml",
            "raw_m3u": f"{base_url}/vavoo_turkiye.m3u",
            "raw_epg": f"{base_url}/vavoo_epg.xml"
        },
        "note": "M3U updated every 4 hours via GitHub Actions"
    }

@app.get("/playlist.m3u")
async def playlist():
    """M3U Playlist"""
    if not os.path.exists(M3U_FILE):
        raise HTTPException(404, "M3U not found. Wait for GitHub Actions to generate it.")
    
    return FileResponse(
        M3U_FILE,
        media_type="application/x-mpegURL",
        filename="vavoo_turkiye.m3u"
    )

@app.get("/epg.xml")
async def epg():
    """EPG Guide"""
    if not os.path.exists(EPG_FILE):
        raise HTTPException(404, "EPG not found")
    
    return FileResponse(
        EPG_FILE,
        media_type="application/xml",
        filename="vavoo_epg.xml"
    )

@app.get("/vavoo_turkiye.m3u")
async def raw_m3u():
    """Raw M3U dosyası"""
    return await playlist()

@app.get("/vavoo_epg.xml")
async def raw_epg():
    """Raw EPG dosyası"""
    return await epg()

@app.get("/status")
async def status():
    """Durum kontrolü"""
    m3u_exists = os.path.exists(M3U_FILE)
    epg_exists = os.path.exists(EPG_FILE)
    
    m3u_size = os.path.getsize(M3U_FILE) if m3u_exists else 0
    epg_size = os.path.getsize(EPG_FILE) if epg_exists else 0
    
    m3u_modified = os.path.getmtime(M3U_FILE) if m3u_exists else 0
    
    return {
        "status": "ok" if m3u_exists else "waiting",
        "m3u_exists": m3u_exists,
        "m3u_size_bytes": m3u_size,
        "m3u_modified_utc": datetime.fromtimestamp(m3u_modified).isoformat() if m3u_modified else None,
        "epg_exists": epg_exists,
        "epg_size_bytes": epg_size
    }

@app.get("/health")
async def health():
    """Sağlık kontrolü"""
    return {"status": "healthy"}

# Import datetime for status endpoint
from datetime import datetime
