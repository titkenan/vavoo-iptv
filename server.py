#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render.com Proxy Sunucu
- Her istekte canlı URL çözümleme
- 7/24 online
"""

import os
import sys
import time
import requests
import json
import re
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse, PlainTextResponse

app = FastAPI(title="Vavoo Turkey Proxy")

# Domain ayarları
VAVOO_DOMAIN = os.getenv("VAVOO_DOMAIN", "vavoo.to")
LOKKE_DOMAIN = "www.lokke.app"

# Cache (bellekte) - signature için
cache = {
    "signature": None,
    "signature_time": 0,
    "channels": {},  # channel_id -> hls_url cache
}

def get_lokke_signature():
    """Signature al - 3 dakika cache"""
    now = time.time()
    if cache["signature"] and (now - cache["signature_time"]) < 180:
        return cache["signature"]
    
    headers = {
        "user-agent": "okhttp/4.11.0",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
    }
    
    data = {
        "token": "",
        "reason": "boot",
        "locale": "de",
        "theme": "dark",
        "metadata": {
            "device": {"type": "desktop", "uniqueId": ""},
            "os": {"name": "linux", "version": "Ubuntu 20.04", "abis": ["x64"], "host": "render"},
            "app": {"platform": "electron"},
            "version": {"package": "app.lokke.main", "binary": "1.0.19", "js": "1.0.19"}
        },
        "appFocusTime": 173,
        "playerActive": False,
        "playDuration": 0,
        "devMode": True,
        "hasAddon": True,
        "castConnected": False,
        "package": "app.lokke.main",
        "version": "1.0.19",
        "process": "app",
        "firstAppStart": int(time.time() * 1000) - 10000,
        "lastAppStart": int(time.time() * 1000) - 10000,
        "ipLocation": 0,
        "adblockEnabled": True,
        "proxy": {"supported": ["ss"], "engine": "cu", "enabled": False, "autoServer": True, "id": 0},
        "iap": {"supported": False}
    }
    
    try:
        resp = requests.post(
            f"https://{LOKKE_DOMAIN}/api/app/ping",
            json=data,
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        sig = resp.json().get("addonSig")
        if sig:
            cache["signature"] = sig
            cache["signature_time"] = now
            return sig
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
    
    return cache["signature"]  # Eski signature'ı dene

def resolve_link(link, retries=3):
    """Link çözümle - retry'li"""
    for attempt in range(retries):
        sig = get_lokke_signature()
        if not sig:
            time.sleep(1)
            continue
        
        headers = {
            "user-agent": "MediaHubMX/2",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "mediahubmx-signature": sig,
        }
        
        data = {
            "language": "de",
            "region": "AT",
            "url": link,
            "clientVersion": "3.0.2"
        }
        
        try:
            resp = requests.post(
                f"https://{VAVOO_DOMAIN}/mediahubmx-resolve.json",
                json=data,
                headers=headers,
                timeout=15
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if result and len(result) > 0:
                    return result[0].get("url")
            elif resp.status_code == 500:
                time.sleep(2 * (attempt + 1))
                continue
                
        except Exception as e:
            print(f"[RESOLVE ERROR] {e}")
            time.sleep(1)
    
    return None

def get_channel_hls(channel_id):
    """Channel ID'den HLS URL'si oluştur"""
    return f"https://{VAVOO_DOMAIN}/play/{channel_id}"

# === API ENDPOINTS ===

@app.get("/")
async def root():
    """Ana sayfa - basit bilgi"""
    return {
        "service": "Vavoo Turkey Proxy",
        "status": "online",
        "endpoints": {
            "playlist": "/playlist.m3u",
            "channel": "/channel/{id}",
            "epg": "/epg.xml"
        }
    }

@app.get("/playlist.m3u")
async def playlist():
    """Dinamik M3U playlist - her istekte güncel"""
    from datetime import datetime
    
    # Kanal listesini çek (basit versiyon - sadece popüler kanallar)
    # Gerçek uygulamada bunu cache'leyebilirsiniz
    channels = [
        {"id": "trt1", "name": "TRT 1", "group": "Ulusal"},
        {"id": "atv", "name": "ATV", "group": "Ulusal"},
        {"id": "show", "name": "Show TV", "group": "Ulusal"},
        {"id": "startv", "name": "Star TV", "group": "Ulusal"},
        {"id": "kanald", "name": "Kanal D", "group": "Ulusal"},
        {"id": "fox", "name": "Fox", "group": "Ulusal"},
        {"id": "tv8", "name": "TV8", "group": "Ulusal"},
        {"id": "beyaz", "name": "Beyaz TV", "group": "Ulusal"},
        {"id": "haberturk", "name": "Habertürk", "group": "Haber"},
        {"id": "cnnturk", "name": "CNN Türk", "group": "Haber"},
        {"id": "ntv", "name": "NTV", "group": "Haber"},
        {"id": "trtspor", "name": "TRT Spor", "group": "Spor"},
        {"id": "trtbelgesel", "name": "TRT Belgesel", "group": "Belgesel"},
    ]
    
    m3u_lines = ["#EXTM3U"]
    m3u_lines.append(f"# Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    m3u_lines.append(f"# Source: Render Proxy")
    m3u_lines.append("")
    
    for ch in channels:
        m3u_lines.append(f'#EXTINF:-1 group-title="{ch["group"]}",{ch["name"]}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=VAVOO/2.6')
        m3u_lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/')
        # Proxy URL - kendi sunucumuz üzerinden
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
        m3u_lines.append(f'{base_url}/channel/{ch["id"]}')
        m3u_lines.append("")
    
    content = "\n".join(m3u_lines)
    return PlainTextResponse(content, media_type="application/x-mpegURL")

@app.get("/channel/{channel_id}")
async def channel(channel_id: str):
    """Kanal yayını - her istekte canlı URL çözümleme"""
    # Önce cache'de var mı kontrol et (5 dakika cache)
    now = time.time()
    cache_key = f"resolved_{channel_id}"
    
    if cache_key in cache:
        cached_url, cached_time = cache[cache_key]
        if (now - cached_time) < 300:  # 5 dakika
            return RedirectResponse(url=cached_url)
    
    # HLS URL'sini oluştur
    hls_url = get_channel_hls(channel_id)
    
    # Çözümle
    resolved = resolve_link(hls_url)
    
    if not resolved:
        raise HTTPException(status_code=503, detail="Stream unavailable")
    
    # Cache'e al
    cache[cache_key] = (resolved, now)
    
    # Redirect yap
    return RedirectResponse(url=resolved)

@app.get("/epg.xml")
async def epg():
    """Basit EPG"""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="trt1"><display-name>TRT 1</display-name></channel>
  <channel id="atv"><display-name>ATV</display-name></channel>
  <channel id="show"><display-name>Show TV</display-name></channel>
</tv>"""
    return PlainTextResponse(xml, media_type="application/xml")

@app.get("/health")
async def health():
    """Sağlık kontrolü"""
    sig = get_lokke_signature()
    return {
        "status": "healthy" if sig else "auth_failed",
        "signature": "valid" if sig else "invalid",
        "timestamp": time.time()
    }
