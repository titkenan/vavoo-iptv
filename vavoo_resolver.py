#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vavoo_resolver.py - GITHUB ACTIONS UYUMLU
- Otomatik M3U güncelleme
- GitHub Pages için statik çıktı
"""

import sys
import requests
import json
import os
import re
import time
from datetime import datetime

# === KONFİGÜRASYON ===
CONFIG = {
    "m3u_filename": "vavoo_turkiye.m3u",
    "epg_filename": "vavoo_epg.xml",
    "max_retries": 3,
    "request_timeout": 15,
}

# Domain
VAVOO_DOMAIN = "vavoo.to"
LOKKE_DOMAIN = "www.lokke.app"

# Kategoriler
CATEGORY_ORDER = ["Ulusal", "Spor", "Belgesel", "Sinema", "Haber", "Çocuk", "Müzik", "Diger"]

TARGET_CATEGORIES = {
    "Ulusal": ["trt 1", "atv", "show", "star", "kanal d", "fox", "tv8", "beyaz", "teve2", "haberturk", "cnn turk", "ntv", "tv100", "a2", "kanal 7", "360", "tlc"],
    "Spor": ["spor", "sport", "bein", "s sport", "tivibu", "aspor", "trt spor", "fb tv", "gs tv", "bjk tv", "eurosport"],
    "Belgesel": ["belgesel", "discovery", "nat geo", "national geo", "history", "trt belgesel", "yaban", "bbc earth", "animal planet"],
    "Sinema": ["sinema", "movie", "film", "dizi", "blu", "moviebox", "cinemax", "hbo", "fox movies", "filmbox", "fx", "salon"],
    "Haber": ["haber", "news", "cnn", "ntv", "a haber", "trt haber", "ulke", "tgrt", "24"],
    "Çocuk": ["çocuk", "cocuk", "cartoon", "disney", "nickelodeon", "trt çocuk", "minika", "baby", "kid", "nick jr"],
    "Müzik": ["müzik", "muzik", "music", "kral", "powerturk", "power", "number one", "trt müzik", "dream", "mtv"],
}

# Logolar
LOGO_BASE = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/"
CHANNEL_LOGOS = {
    "trt 1": "trt-1-tr.png",
    "atv": "atv-tr.png",
    "show tv": "show-tv-tr.png",
    "star tv": "star-tv-tr.png",
    "kanal d": "kanal-d-tr.png",
    "fox": "fox-tr.png",
    "tv8": "tv8-tr.png",
    "beyaz tv": "beyaz-tv-tr.png",
    "haberturk": "haberturk-tr.png",
    "cnn turk": "cnn-turk-tr.png",
    "ntv": "ntv-tr.png",
    "trt spor": "trt-spor-tr.png",
    "bein sports haber": "bein-sports-haber-tr.png",
    "a spor": "a-spor-tr.png",
    "national geographic": "national-geographic-tr.png",
    "discovery": "discovery-channel-tr.png",
    "history": "history-tr.png",
    "trt çocuk": "trt-cocuk-tr.png",
    "cartoon network": "cartoon-network-tr.png",
    "disney channel": "disney-channel-tr.png",
}

def get_lokke_signature():
    """Lokke signature al"""
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
            "os": {"name": "win32", "version": "Windows 10", "abis": ["x64"], "host": "DESKTOP-USER"},
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
        return resp.json().get("addonSig")
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return None

def resolve_link(link, max_retries=3):
    """Link çözümle - retry'li"""
    for attempt in range(max_retries):
        sig = get_lokke_signature()
        if not sig:
            time.sleep(2)
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
                print(f"[RETRY {attempt+1}] Server error, waiting...")
                time.sleep(3 * (attempt + 1))
                continue
                
        except Exception as e:
            print(f"[RETRY {attempt+1}] Error: {e}")
            time.sleep(2)
    
    return None

def get_all_channels():
    """Tüm kanalları çek"""
    sig = get_lokke_signature()
    if not sig:
        return []
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig,
    }
    
    all_channels = []
    cursor = 0
    
    print("[INFO] Fetching channels...")
    
    while True:
        data = {
            "language": "de",
            "region": "AT",
            "catalogId": "iptv",
            "id": "iptv",
            "adult": False,
            "search": "",
            "sort": "name",
            "filter": {"group": "Turkey"},
            "cursor": cursor,
            "clientVersion": "3.0.2"
        }
        
        try:
            resp = requests.post(
                f"https://{VAVOO_DOMAIN}/mediahubmx-catalog.json",
                json=data,
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            r = resp.json()
            items = r.get("items", [])
            all_channels.extend(items)
            cursor = r.get("nextCursor")
            if not cursor:
                break
        except Exception as e:
            print(f"[FETCH ERROR] {e}")
            break
    
    print(f"[INFO] Total channels: {len(all_channels)}")
    return all_channels

def categorize(name):
    name_lower = name.lower()
    for cat in CATEGORY_ORDER:
        if cat == "Diger":
            continue
        for keyword in TARGET_CATEGORIES.get(cat, []):
            if keyword in name_lower:
                return cat
    return "Diger"

def get_logo(name):
    name_lower = name.lower()
    for ch_name, logo_file in CHANNEL_LOGOS.items():
        if ch_name in name_lower:
            return f"{LOGO_BASE}{logo_file}"
    return ""

def get_tvg_id(name):
    clean = re.sub(r'[^\w\s]', '', name).strip().lower().replace(' ', '.')
    return f"{clean}.tr"

def generate_m3u(channels):
    """M3U oluştur"""
    print(f"[M3U] Generating playlist...")
    
    # Kategorilere ayır
    categorized = {cat: [] for cat in CATEGORY_ORDER}
    for ch in channels:
        name = ch.get("name", "").strip()
        if not name:
            continue
        cat = categorize(name)
        ch["category"] = cat
        ch["tvg_id"] = get_tvg_id(name)
        ch["logo"] = get_logo(name)
        categorized[cat].append(ch)
    
    # Sırala
    sorted_ch = []
    for cat in CATEGORY_ORDER:
        sorted_ch.extend(sorted(categorized[cat], key=lambda x: x.get("name", "").upper()))
    
    # M3U yaz
    with open(CONFIG["m3u_filename"], "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Vavoo Turkey Playlist\n")
        f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"# Source: https://github.com/titkenan/vavoo-iptv\n")
        f.write(f"# Total: {len(sorted_ch)} channels\n\n")
        
        current_cat = None
        
        for i, ch in enumerate(sorted_ch):
            name = ch.get("name", "Unknown")
            hls = ch.get("url")
            if not hls:
                continue
            
            cat = ch["category"]
            tvg_id = ch["tvg_id"]
            logo = ch["logo"]
            
            if cat != current_cat:
                f.write(f"\n# {cat} Channels\n")
                current_cat = cat
            
            # EXTINF
            extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}"'
            if logo:
                extinf += f' tvg-logo="{logo}"'
            extinf += f' group-title="{cat}",{name}\n'
            f.write(extinf)
            
            # VLC options
            f.write('#EXTVLCOPT:http-user-agent=VAVOO/2.6\n')
            f.write('#EXTVLCOPT:http-referrer=https://vavoo.to/\n')
            
            # Resolve URL
            print(f"[{i+1}/{len(sorted_ch)}] Resolving {name}...", end=" ", flush=True)
            resolved = resolve_link(hls)
            if resolved:
                print("✓")
                f.write(f"{resolved}\n")
            else:
                print("✗ (using original)")
                f.write(f"{hls}\n")
            
            time.sleep(0.3)  # Rate limit
    
    print(f"[M3U] Saved: {CONFIG['m3u_filename']} ({len(sorted_ch)} channels)")
    return True

def generate_epg(channels):
    """Basit EPG oluştur"""
    xml = ['<?xml version="1.0" encoding="UTF-8"?>\n']
    xml.append('<tv generator-info-name="Vavoo Resolver">\n')
    
    for ch in channels:
        name = ch.get("name", "").strip()
        tvg_id = get_tvg_id(name)
        xml.append(f'  <channel id="{tvg_id}">\n')
        xml.append(f'    <display-name>{name}</display-name>\n')
        logo = get_logo(name)
        if logo:
            xml.append(f'    <icon src="{logo}"/>\n')
        xml.append('  </channel>\n')
    
    xml.append('</tv>')
    
    with open(CONFIG["epg_filename"], "w", encoding="utf-8") as f:
        f.write("".join(xml))
    
    print(f"[EPG] Saved: {CONFIG['epg_filename']}")
    return True

def main():
    print("="*60)
    print("VAVOO RESOLVER - GitHub Actions Edition")
    print("="*60)
    
    channels = get_all_channels()
    if not channels:
        print("[ERROR] No channels fetched!")
        sys.exit(1)
    
    generate_m3u(channels)
    generate_epg(channels)
    
    print("\n✅ Done! Files updated:")
    print(f"  - {CONFIG['m3u_filename']}")
    print(f"  - {CONFIG['epg_filename']}")

if __name__ == "__main__":
    if "--generate-only" in sys.argv:
        main()
    else:
        main()
