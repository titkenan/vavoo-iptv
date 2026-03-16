#!/usr/bin/env python3
"""
Render.com Test Sunucu
- Vavoo bağlantı testi
- Her istekte canlı URL çözümleme (eğer çalışırsa)
"""

import os
import time
import requests
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vavoo Test Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VAVOO_DOMAIN = "vavoo.to"
VAVOO_TV_DOMAIN = "www.vavoo.tv"
LOKKE_DOMAIN = "www.lokke.app"

# Popüler kanallar (ID'ler)
CHANNELS = {
    "trt1": "TRT 1",
    "atv": "ATV",
    "show": "Show TV",
    "star": "Star TV",
    "kanald": "Kanal D",
    "fox": "Fox",
    "tv8": "TV8",
    "beyaz": "Beyaz TV",
    "haberturk": "Habertürk",
    "cnnturk": "CNN Türk",
    "ntv": "NTV",
    "trtspor": "TRT Spor",
}

# ========== TEST FONKSİYONLARI ==========

def get_lokke_sig():
    """Lokke imzası al"""
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
            "os": {"name": "linux", "version": "Ubuntu", "abis": ["x64"], "host": "render"},
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
        r = requests.post(f'https://{LOKKE_DOMAIN}/api/app/ping', json=data, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("addonSig")
    except:
        pass
    return None

def get_vavoo_token():
    """Standart Vavoo token al (ping2)"""
    headers = {'User-Agent': 'VAVOO/2.6', 'Accept': 'application/json'}
    try:
        # Vec listesi
        r = requests.get("http://mastaaa1987.github.io/repo/veclist.json", headers=headers, timeout=10)
        veclist = r.json()['value']
        
        for _ in range(3):
            vec = {"vec": random.choice(veclist)}
            resp = requests.post(f'https://{VAVOO_TV_DOMAIN}/api/box/ping2', data=vec, headers=headers, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if result.get('signed'):
                    return result['signed']
    except:
        pass
    return None

def resolve_with_lokke(hls_url):
    """Lokke imzası ile çözümle"""
    sig = get_lokke_sig()
    if not sig:
        return None
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig,
    }
    data = {
        "language": "de",
        "region": "AT",
        "url": hls_url,
        "clientVersion": "3.0.2"
    }
    try:
        r = requests.post(f"https://{VAVOO_DOMAIN}/mediahubmx-resolve.json", 
                       data=json.dumps(data), headers=headers, timeout=10)
        if r.status_code == 200:
            result = r.json()
            if result and len(result) > 0:
                return result[0].get("url")
    except:
        pass
    return None

# ========== API ENDPOINTS ==========

@app.get("/")
def root():
    """Ana sayfa"""
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    return {
        "service": "Vavoo Test Server",
        "endpoints": {
            "test": f"{base}/test-vavoo",
            "playlist": f"{base}/playlist.m3u",
            "live": f"{base}/live/{{channel_id}}"
        }
    }

@app.get("/test-vavoo")
def test_vavoo():
    """Vavoo bağlantı testi - TÜM TESTLER"""
    results = {}
    
    # Test 1: Lokke imzası
    try:
        sig = get_lokke_sig()
        results["lokke_signature"] = {
            "status": "OK" if sig else "FAIL",
            "preview": sig[:40] + "..." if sig else None
        }
    except Exception as e:
        results["lokke_signature"] = {"status": "ERROR", "error": str(e)}
    
    # Test 2: Vavoo token (ping2)
    try:
        token = get_vavoo_token()
        results["vavoo_token_ping2"] = {
            "status": "OK" if token else "FAIL",
            "preview": token[:40] + "..." if token else None
        }
    except Exception as e:
        results["vavoo_token_ping2"] = {"status": "ERROR", "error": str(e)}
    
    # Test 3: vavoo.to erişim
    try:
        r = requests.get(f"https://{VAVOO_DOMAIN}/live2/index?output=json",
                        headers={'User-Agent': 'VAVOO/2.6'}, timeout=10)
        results["vavoo_to_access"] = {
            "status": r.status_code,
            "channels_count": len(r.json()) if r.status_code == 200 else 0
        }
    except Exception as e:
        results["vavoo_to_access"] = {"status": "ERROR", "error": str(e)}
    
    # Test 4: Resolve test (eğer imza varsa)
    if sig:
        try:
            test_url = f"https://{VAVOO_DOMAIN}/play/trt1"
            resolved = resolve_with_lokke(test_url)
            results["resolve_test"] = {
                "status": "OK" if resolved else "FAIL",
                "url_preview": resolved[:60] + "..." if resolved else None
            }
        except Exception as e:
            results["resolve_test"] = {"status": "ERROR", "error": str(e)}
    else:
        results["resolve_test"] = {"status": "SKIP", "reason": "No signature"}
    
    # Test 5: IP bilgisi
    try:
        r = requests.get("https://httpbin.org/ip", timeout=5)
        results["server_ip"] = r.json().get("origin", "unknown")
    except:
        results["server_ip"] = "unknown"
    
    return JSONResponse(results)

@app.get("/playlist.m3u")
def playlist():
    """M3U playlist - proxy URL'ler ile"""
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    lines = ["#EXTM3U", "# Vavoo Live Proxy", ""]
    
    for ch_id, name in CHANNELS.items():
        lines.append(f'#EXTINF:-1 group-title="Ulusal",{name}')
        lines.append('#EXTVLCOPT:http-user-agent=VAVOO/2.6')
        lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/')
        lines.append(f'{base}/live/{ch_id}')
        lines.append("")
    
    return PlainTextResponse("\n".join(lines), media_type="application/x-mpegURL")

@app.get("/live/{channel_id}")
def live(channel_id: str):
    """Canlı yayın - HER İSTEKTE YENİ ÇÖZÜMLE"""
    if channel_id not in CHANNELS:
        raise HTTPException(404, "Channel not found")
    
    # HLS URL
    hls = f"https://{VAVOO_DOMAIN}/play/{channel_id}"
    
    # Çözümle (önce Lokke dene)
    resolved = resolve_with_lokke(hls)
    
    # Olmazsa token ile dene
    if not resolved:
        token = get_vavoo_token()
        if token:
            resolved = f"{hls}?n=1&b=5&vavoo_auth={token}"
    
    if resolved:
        return RedirectResponse(url=resolved, status_code=302)
    
    raise HTTPException(503, "Stream unavailable")

@app.get("/test-channel/{channel_id}")
def test_channel(channel_id: str):
    """Tek kanal detaylı test"""
    hls = f"https://{VAVOO_DOMAIN}/play/{channel_id}"
    
    # Lokke ile dene
    sig = get_lokke_sig()
    resolved_lokke = None
    if sig:
        resolved_lokke = resolve_with_lokke(hls)
    
    # Token ile dene
    token = get_vavoo_token()
    resolved_token = None
    if token:
        resolved_token = f"{hls}?n=1&b=5&vavoo_auth={token}"
    
    return {
        "channel_id": channel_id,
        "hls_url": hls,
        "lokke": {
            "signature": "OK" if sig else "FAIL",
            "resolved_url": resolved_lokke[:80] + "..." if resolved_lokke else None
        },
        "token": {
            "token": "OK" if token else "FAIL",
            "url": resolved_token[:80] + "..." if resolved_token else None
        }
    }
