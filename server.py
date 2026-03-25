#!/usr/bin/env python3
"""
Render.com Dinamik IPTV Proxy
- Tüm Vavoo kanallarını gerçek zamanlı resolve eder
- Cache ile performans optimize edildi
"""

import os
import time
import requests
import json
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Vavoo Dynamic Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import from vavoo_resolver (aynı klasörde)
import sys
sys.path.insert(0, os.path.dirname(__file__))

from vavoo_resolver import (
    get_lokke_signature,
    resolve_link,
    get_all_channels,
    categorize,
    get_logo,
    get_tvg_id,
    CATEGORY_ORDER
)

# Cache
CHANNELS_CACHE = []
CACHE_TIME = 0
CACHE_DURATION = 3600  # 1 saat

RESOLVED_CACHE = {}
RESOLVE_CACHE_DURATION = 900  # 15 dakika

def update_cache():
    """Kanal listesini güncelle"""
    global CHANNELS_CACHE, CACHE_TIME
    print("[CACHE] Updating channels...")
    CHANNELS_CACHE = get_all_channels()
    CACHE_TIME = time.time()
    print(f"[CACHE] Updated: {len(CHANNELS_CACHE)} channels")

def get_cached_channels():
    """Cache'den al veya güncelle"""
    if time.time() - CACHE_TIME > CACHE_DURATION or not CHANNELS_CACHE:
        update_cache()
    return CHANNELS_CACHE

def get_resolved_url(original_url):
    """Cache'li URL resolve"""
    cache_key = hashlib.md5(original_url.encode()).hexdigest()
    
    # Cache kontrol
    if cache_key in RESOLVED_CACHE:
        url, timestamp = RESOLVED_CACHE[cache_key]
        if time.time() - timestamp < RESOLVE_CACHE_DURATION:
            return url
    
    # Yeni resolve
    resolved = resolve_link(original_url)
    if resolved:
        RESOLVED_CACHE[cache_key] = (resolved, time.time())
        return resolved
    
    return original_url

@app.get("/")
def index():
    """Ana sayfa"""
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    return {
        "service": "Vavoo Dynamic IPTV Proxy",
        "status": "online",
        "cached_channels": len(CHANNELS_CACHE),
        "resolved_links": len(RESOLVED_CACHE),
        "endpoints": {
            "playlist": f"{base}/playlist.m3u",
            "epg": f"{base}/epg.xml",
            "stream": f"{base}/stream/CHANNEL_ID"
        },
        "usage": {
            "vavoo": f"{base}/playlist.m3u",
            "vlc": f"{base}/playlist.m3u"
        }
    }

@app.get("/playlist.m3u")
def playlist():
    """Dinamik M3U - Stream URL'ler proxy üzerinden"""
    channels = get_cached_channels()
    
    # Kategorilere ayır
    by_cat = {cat: [] for cat in CATEGORY_ORDER}
    
    for ch in channels:
        name = ch.get("name", "").strip()
        if not name:
            continue
        
        cat = categorize(name)
        ch["category"] = cat
        ch["tvg_id"] = get_tvg_id(name)
        ch["logo"] = get_logo(name)
        by_cat[cat].append(ch)
    
    # Sırala
    sorted_ch = []
    for cat in CATEGORY_ORDER:
        sorted_ch.extend(sorted(by_cat[cat], key=lambda x: x.get("name", "").upper()))
    
    # M3U oluştur
    base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    lines = [
        "#EXTM3U",
        f"# Vavoo Turkey - Dynamic Proxy",
        f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"# Source: {base_url}",
        f"# Total: {len(sorted_ch)} channels",
        ""
    ]
    
    current_cat = None
    
    for ch in sorted_ch:
        name = ch.get("name", "Unknown")
        ch_id = ch.get("id", "")
        
        if not ch_id:
            continue
        
        cat = ch["category"]
        tvg_id = ch["tvg_id"]
        logo = ch["logo"]
        
        if cat != current_cat:
            lines.append(f"\n# {cat} Channels")
            current_cat = cat
        
        # EXTINF
        extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f' group-title="{cat}",{name}'
        lines.append(extinf)
        
        # VLC options
        lines.append('#EXTVLCOPT:http-user-agent=VAVOO/2.6')
        lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/')
        
        # Proxy stream URL
        lines.append(f'{base_url}/stream/{ch_id}')
        lines.append("")
    
    return PlainTextResponse("\n".join(lines), media_type="audio/x-mpegurl")

@app.get("/stream/{channel_id}")
def stream(channel_id: str):
    """Dinamik stream - Gerçek zamanlı resolve"""
    channels = get_cached_channels()
    
    # Channel bul
    channel = next((c for c in channels if c.get("id") == channel_id), None)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    original_url = channel.get("url")
    if not original_url:
        raise HTTPException(status_code=404, detail="No stream URL")
    
    # Resolve et (cache'li)
    resolved_url = get_resolved_url(original_url)
    
    if resolved_url:
        return RedirectResponse(url=resolved_url, status_code=302)
    
    raise HTTPException(status_code=503, detail="Stream unavailable")

@app.get("/epg.xml")
def epg():
    """EPG guide"""
    channels = get_cached_channels()
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>\n']
    xml.append('<tv generator-info-name="Vavoo Dynamic Proxy">\n')
    
    for ch in channels:
        name = ch.get("name", "").strip()
        if not name:
            continue
        
        tvg_id = get_tvg_id(name)
        xml.append(f'  <channel id="{tvg_id}">\n')
        xml.append(f'    <display-name>{name}</display-name>\n')
        
        logo = get_logo(name)
        if logo:
            xml.append(f'    <icon src="{logo}"/>\n')
        
        xml.append('  </channel>\n')
    
    xml.append('</tv>')
    
    return PlainTextResponse("".join(xml), media_type="application/xml")

# İlk başlatmada cache'i doldur
@app.on_event("startup")
async def startup_event():
    update_cache()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
