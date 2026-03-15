#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys  # ← BU SATIRI EKLEYİN
import requests
import json
import re
import time
import os
from datetime import datetime

# -*- coding: utf-8 -*-
"""
GitHub Actions için M3U Oluşturucu
"""

import sys  # ← EKLENDİ!
import requests
import json
import re
import time
import os
from datetime import datetime

# Ayarlar
VAVOO_DOMAIN = "vavoo.to"
LOKKE_DOMAIN = "www.lokke.app"
M3U_FILE = "vavoo_turkiye.m3u"
EPG_FILE = "vavoo_epg.xml"

# Kategoriler
CATEGORIES = {
    "Ulusal": ["trt 1", "atv", "show", "star", "kanal d", "fox", "tv8", "beyaz", "teve2", "haberturk", "cnn turk", "ntv", "tv100", "a2", "kanal 7", "360", "tlc", "bloomberg ht"],
    "Spor": ["spor", "sport", "bein", "s sport", "tivibu", "aspor", "trt spor", "fb tv", "gs tv", "bjk tv", "eurosport"],
    "Belgesel": ["belgesel", "discovery", "nat geo", "national geo", "history", "trt belgesel", "yaban", "bbc earth", "animal planet", "da vinci"],
    "Sinema": ["sinema", "movie", "film", "dizi", "blu", "moviebox", "cinemax", "hbo", "fox movies", "filmbox", "fx", "salon"],
    "Haber": ["haber", "news", "cnn", "ntv", "a haber", "trt haber", "ulke", "tgrt", "24", "bloomberg"],
    "Çocuk": ["çocuk", "cocuk", "cartoon", "disney", "nickelodeon", "trt çocuk", "minika", "baby", "kid", "nick jr", "boomerang"],
    "Müzik": ["müzik", "muzik", "music", "kral", "powerturk", "power", "number one", "trt müzik", "dream", "mtv", "vh1"],
}

LOGOS = {
    "trt 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/trt-1-tr.png",
    "atv": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/atv-tr.png",
    "show tv": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/show-tv-tr.png",
    "star tv": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/star-tv-tr.png",
    "kanal d": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/kanal-d-tr.png",
    "fox": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/fox-tr.png",
    "tv8": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/tv8-tr.png",
    "beyaz tv": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/beyaz-tv-tr.png",
    "haberturk": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/haberturk-tr.png",
    "cnn turk": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/cnn-turk-tr.png",
    "ntv": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/ntv-tr.png",
    "trt spor": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/trt-spor-tr.png",
    "bein sports": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/bein-sports-1-tr.png",
    "a spor": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/a-spor-tr.png",
    "national geographic": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/national-geographic-tr.png",
    "discovery": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/discovery-channel-tr.png",
    "history": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/history-tr.png",
    "trt çocuk": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/trt-cocuk-tr.png",
    "cartoon network": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/cartoon-network-tr.png",
    "disney channel": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/turkey/disney-channel-tr.png",
}

def get_signature():
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
            "os": {"name": "linux", "version": "Ubuntu 20.04", "abis": ["x64"], "host": "github-actions"},
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
        resp = requests.post(f"https://{LOKKE_DOMAIN}/api/app/ping", json=data, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json().get("addonSig")
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return None

def resolve_url(hls_url, sig, retries=3):
    """URL çözümle"""
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
    
    for attempt in range(retries):
        try:
            resp = requests.post(
                f"https://{VAVOO_DOMAIN}/mediahubmx-resolve.json",
                json=data,
                headers=headers,
                timeout=20
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if result and len(result) > 0:
                    return result[0].get("url")
            elif resp.status_code == 500:
                print(f"  [RETRY {attempt+1}] Server 500, waiting...")
                time.sleep(3)
                continue
                
        except Exception as e:
            print(f"  [RETRY {attempt+1}] Error: {e}")
            time.sleep(2)
    
    return None

def get_all_channels():
    """Tüm kanalları çek"""
    sig = get_signature()
    if not sig:
        print("[ERROR] Could not get signature!")
        return []
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig,
    }
    
    all_channels = []
    cursor = 0
    page = 1
    
    print("[FETCH] Getting channels from Vavoo...")
    
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
                timeout=20
            )
            resp.raise_for_status()
            r = resp.json()
            items = r.get("items", [])
            
            if not items:
                break
                
            all_channels.extend(items)
            print(f"  Page {page}: +{len(items)} channels (total: {len(all_channels)})")
            
            cursor = r.get("nextCursor")
            if not cursor:
                break
            
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  [ERROR] Page {page}: {e}")
            break
    
    print(f"[FETCH] Total: {len(all_channels)} channels")
    return all_channels

def categorize(name):
    """Kategori belirle"""
    name_lower = name.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in name_lower:
                return cat
    return "Diger"

def get_logo(name):
    """Logo URL'si"""
    name_lower = name.lower()
    for ch_name, url in LOGOS.items():
        if ch_name in name_lower:
            return url
    return ""

def get_tvg_id(name):
    """TVG ID oluştur"""
    clean = re.sub(r'[^\w\s]', '', name).strip().lower().replace(' ', '.')
    return f"{clean}.tr"

def generate_m3u(channels):
    """M3U oluştur"""
    print(f"\n[M3U] Resolving {len(channels)} channels...")
    
    # Kategorilere ayır
    by_cat = {cat: [] for cat in list(CATEGORIES.keys()) + ["Diger"]}
    
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
    order = list(CATEGORIES.keys()) + ["Diger"]
    sorted_ch = []
    for cat in order:
        sorted_ch.extend(sorted(by_cat[cat], key=lambda x: x.get("name", "").upper()))
    
    # M3U yaz
    m3u_lines = [
        "#EXTM3U",
        f"# Vavoo Turkey - Auto Generated",
        f"# Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"# Source: https://github.com/titkenan/vavoo-iptv",
        f"# Total: {len(sorted_ch)} channels",
        f"# Auto-refresh: Every 4 hours",
        ""
    ]
    
    # Yeni signature al
    sig = get_signature()
    if not sig:
        print("[ERROR] No signature for resolving!")
        return False
    
    current_cat = None
    success = 0
    failed = 0
    
    for i, ch in enumerate(sorted_ch):
        name = ch.get("name", "Unknown")
        hls = ch.get("url")
        
        if not hls:
            continue
        
        cat = ch["category"]
        
        if cat != current_cat:
            m3u_lines.append(f"\n# {cat} Channels")
            current_cat = cat
        
        print(f"[{i+1}/{len(sorted_ch)}] {name}...", end=" ", flush=True)
        
        # URL çözümle
        resolved = resolve_url(hls, sig)
        
        if resolved:
            print("OK")
            success += 1
            
            extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{name}"'
            if ch["logo"]:
                extinf += f' tvg-logo="{ch["logo"]}"'
            extinf += f' group-title="{cat}",{name}'
            m3u_lines.append(extinf)
            
            m3u_lines.append('#EXTVLCOPT:http-user-agent=VAVOO/2.6')
            m3u_lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/')
            m3u_lines.append('#EXTVLCOPT:http-origin=https://vavoo.to')
            m3u_lines.append(resolved)
            m3u_lines.append("")
        else:
            print("FAIL")
            failed += 1
        
        # Her 20 kanalda bir yeni signature
        if (i + 1) % 20 == 0:
            new_sig = get_signature()
            if new_sig:
                sig = new_sig
                print(f"  [REFRESH] New signature")
        
        time.sleep(0.3)
    
    # Kaydet
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    
    print(f"\n[M3U] Saved: {M3U_FILE}")
    print(f"  Success: {success}/{len(sorted_ch)}")
    print(f"  Failed: {failed}/{len(sorted_ch)}")
    
    return True

def generate_epg(channels):
    """Basit EPG oluştur"""
    xml = ['<?xml version="1.0" encoding="UTF-8"?>\n']
    xml.append('<tv generator-info-name="Vavoo Resolver">\n')
    
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
    
    with open(EPG_FILE, "w", encoding="utf-8") as f:
        f.write("".join(xml))
    
    print(f"[EPG] Saved: {EPG_FILE}")
    return True

def main():
    print("="*60)
    print("VAVOO M3U GENERATOR - GitHub Actions")
    print("="*60)
    
    channels = get_all_channels()
    if not channels:
        print("[FATAL] No channels fetched!")
        return False
    
    if not generate_m3u(channels):
        return False
    
    generate_epg(channels)
    
    print("\n" + "="*60)
    print("SUCCESS!")
    print(f"Files generated:")
    print(f"  - {M3U_FILE}")
    print(f"  - {EPG_FILE}")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
