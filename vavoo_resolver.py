#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import random
import json
import base64
import time
import os
import sys
import re
from urllib.request import Request, urlopen
import ssl

# ============ AYARLAR ============
GIST_ID = "0956315177e258464a1545babe1e8ac9"  # Sizin Gist ID'niz
GIST_TOKEN = os.environ.get("GIST_TOKEN")     # GitHub Secrets'ten gelir
WORKER_URL = "https://sizin-worker.workers.dev"  # Cloudflare Worker adresiniz

CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache(key):
    path = os.path.join(CACHE_DIR, key)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return None

def set_cache(key, value):
    path = os.path.join(CACHE_DIR, key)
    with open(path, 'w') as f:
        f.write(value)

# ============ TOKEN ALMA ============
def get_veclist():
    veclist = get_cache('veclist')
    if not veclist:
        try:
            vlist = requests.get("http://mastaaa1987.github.io/repo/veclist.json", timeout=10).json()
            veclist = json.dumps(vlist['value'])
            set_cache('veclist', veclist)
        except:
            # Yedek liste (gerçek çalışmazsa güncelleyin)
            veclist = json.dumps([
                "7b2263726561746564223a313637363833303630313030302c22766563223a5b32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32345d7d"
            ])
    return json.loads(veclist)

def getWatchedSig():
    # Önce kayıtlı token var mı?
    key_file = os.path.join(CACHE_DIR, 'wsignkey')
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            return f.read().strip()

    veclist = get_veclist()
    sig = None
    for _ in range(10):
        vec = {"vec": random.choice(veclist)}
        try:
            req = requests.post('https://www.vavoo.tv/api/box/ping2', data=vec, timeout=10).json()
            if req.get('signed'):
                sig = req['signed']
                break
            elif req.get('data', {}).get('signed'):
                sig = req['data']['signed']
                break
            elif req.get('response', {}).get('signed'):
                sig = req['response']['signed']
                break
        except:
            continue

    if not sig:
        # Alternatif: lokke.app
        headers = {
            "user-agent": "okhttp/4.11.0",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip"
        }
        data = {
            "token": "", "reason": "boot", "locale": "de", "theme": "dark",
            "metadata": {
                "device": {"type": "desktop", "uniqueId": ""},
                "os": {"name": "win32", "version": "Windows 10 Education", "abis": ["x64"], "host": "DESKTOP-JN65HTI"},
                "app": {"platform": "electron"},
                "version": {"package": "app.lokke.main", "binary": "1.0.19", "js": "1.0.19"}
            },
            "appFocusTime": 173, "playerActive": False, "playDuration": 0,
            "devMode": True, "hasAddon": True, "castConnected": False,
            "package": "app.lokke.main", "version": "1.0.19", "process": "app",
            "firstAppStart": 1770751158625, "lastAppStart": 1770751158625,
            "ipLocation": 0, "adblockEnabled": True,
            "proxy": {"supported": ["ss"], "engine": "cu", "enabled": False, "autoServer": True, "id": 0},
            "iap": {"supported": False}
        }
        try:
            req = requests.post('https://www.lokke.app/api/app/ping', json=data, headers=headers, timeout=10).json()
            sig = req.get("addonSig")
        except:
            pass

    if sig:
        with open(key_file, 'w') as f:
            f.write(sig)
    return sig

# ============ KANAL LİSTESİ ÇEKME ============
def get_channels():
    channels = []
    # 1. live2/index?output=json (hızlı liste)
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        req = Request('https://www.vavoo.to/live2/index?output=json',
                      headers={'User-Agent': 'Mozilla/5.0'})
        resp = urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf8'))
        channels.extend(data)
    except Exception as e:
        print(f"live2 hatası: {e}")

    # 2. mediahubmx-catalog.json (tüm gruplar)
    sig = getWatchedSig()
    if sig:
        groups = ["Germany", "Turkey", "International", "Sport", "Kids", "Documentaries", "Entertainment", "News"]
        headers = {
            "accept-encoding": "gzip",
            "user-agent": "MediaHubMX/2",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "mediahubmx-signature": sig
        }
        for group in groups:
            cursor = 0
            while True:
                data = {
                    "language": "de",
                    "region": "AT",
                    "catalogId": "iptv",
                    "id": "iptv",
                    "adult": False,
                    "search": "",
                    "sort": "name",
                    "filter": {"group": group},
                    "cursor": cursor,
                    "clientVersion": "3.0.2"
                }
                try:
                    r = requests.post("https://vavoo.to/mediahubmx-catalog.json",
                                      json=data, headers=headers, timeout=15).json()
                    items = r.get("items", [])
                    for item in items:
                        if "LUXEMBOURG" not in item.get("name", ""):
                            channels.append(item)
                    next_cursor = r.get("nextCursor")
                    if not next_cursor:
                        break
                    cursor = next_cursor
                except Exception as e:
                    print(f"mediahubmx hatası ({group}): {e}")
                    break

    # Tekrarları temizle
    seen = set()
    unique = []
    for ch in channels:
        url = ch.get('url')
        if url and url not in seen:
            seen.add(url)
            unique.append(ch)
    return unique

# ============ M3U OLUŞTURMA ============
def generate_m3u8(channels, worker_url):
    lines = ["#EXTM3U"]
    for ch in channels:
        name = ch.get('name', '')
        logo = ch.get('logo', '')
        group = ch.get('group', 'Unknown')
        url = ch.get('url', '')
        if not url:
            continue
        # Kanal adını temizle
        clean_name = re.sub(r' (4K|HEVC|HD|FHD|UHD|AUSTRIA|AT|DE|\(.*?\)).*', '', name).strip()
        extinf = f'#EXTINF:-1 tvg-name="{clean_name}" group-title="{group}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f',{clean_name}'
        lines.append(extinf)
        # Worker üzerinden proxy'lenecek URL
        proxy_url = f"{worker_url}/play?url={requests.utils.quote(url)}"
        lines.append(proxy_url)
    return "\n".join(lines)

# ============ GIST YÜKLEME ============
def upload_to_gist(filename, content, description):
    if not GIST_TOKEN:
        print("GIST_TOKEN bulunamadı!")
        return False
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "description": description,
        "files": {
            filename: {"content": content}
        }
    }
    try:
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            print(f"✅ {filename} Gist'e yüklendi.")
            return True
        else:
            print(f"❌ Hata {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ İstek hatası: {e}")
        return False

# ============ ANA FONKSİYON ============
def main():
    print("[1] Token alınıyor...")
    sig = getWatchedSig()
    if not sig:
        print("❌ Token alınamadı!")
        sys.exit(1)
    print(f"✅ Token: {sig[:50]}...")

    print("[2] Kanal listesi çekiliyor...")
    channels = get_channels()
    print(f"✅ {len(channels)} kanal bulundu.")

    print("[3] M3U playlist oluşturuluyor...")
    m3u = generate_m3u8(channels, WORKER_URL)

    print("[4] Gist güncelleniyor...")
    upload_to_gist("vavoo_token.txt", sig, "Vavoo Token")
    upload_to_gist("vavoo_turkiye.m3u", m3u, "Vavoo Turkey Playlist")

    print("🎉 İşlem tamamlandı.")

if __name__ == "__main__":
    main()
