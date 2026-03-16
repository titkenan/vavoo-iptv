#!/usr/bin/env python3
import requests

VAVOO_DOMAIN = "vavoo.to"
LOKKE_DOMAIN = "www.lokke.app"

def get_sig():
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
            "os": {"name": "win32", "version": "Windows 10", "abis": ["x64"], "host": "test"},
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
        "firstAppStart": 0,
        "lastAppStart": 0,
        "ipLocation": 0,
        "adblockEnabled": True,
        "proxy": {"supported": ["ss"], "engine": "cu", "enabled": False, "autoServer": True, "id": 0},
        "iap": {"supported": False}
    }
    try:
        r = requests.post(f"https://{LOKKE_DOMAIN}/api/app/ping", json=data, headers=headers, timeout=10)
        return r.json().get("addonSig")
    except:
        return None

def resolve(hls_url):
    sig = get_sig()
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
        r = requests.post(f"https://{VAVOO_DOMAIN}/mediahubmx-resolve.json", json=data, headers=headers, timeout=15)
        if r.status_code == 200:
            result = r.json()
            if result and len(result) > 0:
                return result[0].get("url")
    except:
        pass
    return None

# Test
hls = "https://vavoo.to/play/trt1"
resolved = resolve(hls)
print(f"HLS: {hls}")
print(f"Resolved: {resolved}")

# Test et
if resolved:
    headers = {"User-Agent": "VAVOO/2.6", "Referer": "https://vavoo.to/"}
    r = requests.head(resolved, headers=headers, timeout=10, allow_redirects=True)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
