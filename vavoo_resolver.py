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

# ============ AYARLAR ============
GIST_ID = "0956315177e258464a1545babe1e8ac9"
GIST_TOKEN = os.environ.get("GIST_TOKEN")
WORKER_URL = "https://sizin-worker.workers.dev"  # Worker adresiniz

# ============ TOKEN ALMA (API'deki utils.vavoo.getAuthSignature benzeri) ============
def get_auth_signature():
    """Vavoo için auth token üretir (veclist'i GitHub'dan çeker)"""
    # Önce veclist'i cache'den veya GitHub'dan al
    veclist = None
    try:
        vlist = requests.get("http://mastaaa1987.github.io/repo/veclist.json", timeout=10).json()
        veclist = vlist['value']
    except:
        # Yedek veclist (örnek)
        veclist = [
            "7b2263726561746564223a313637363833303630313030302c22766563223a5b32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32345d7d"
        ]

    sig = None
    for _ in range(10):  # 10 kez dene
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
    return sig

# ============ KANAL LİSTESİ ÇEKME ============
def get_channels():
    """Vavoo'dan kanal listesini JSON olarak alır (iki kaynaktan birleştirir)"""
    channels = []
    
    # 1. Kaynak: live2/index?output=json
    try:
        resp = requests.get('https://www.vavoo.to/live2/index?output=json', 
                            headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            channels.extend(resp.json())
    except:
        pass

    # 2. Kaynak: mediahubmx-catalog.json (token gerekli)
    sig = get_auth_signature()
    if sig:
        headers = {
            "accept-encoding": "gzip",
            "user-agent": "MediaHubMX/2",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "mediahubmx-signature": sig
        }
        # Olası gruplar (API'deki gibi)
        groups = ["Germany", "Turkey", "International", "Sport", "Kids", "Documentaries"]
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
                        # Filtreleme (LUXEMBOURG vb.)
                        if "LUXEMBOURG" not in item["name"]:
                            channels.append(item)
                    next_cursor = r.get("nextCursor")
                    if not next_cursor:
                        break
                    cursor = next_cursor
                except:
                    break

    # Tekrarlananları temizle (url'ye göre)
    seen = set()
    unique = []
    for ch in channels:
        url = ch.get('url') or ch.get('URL') or ''
        if url and url not in seen:
            seen.add(url)
            unique.append(ch)
    return unique

# ============ M3U OLUŞTURMA ============
def generate_m3u8(channels, worker_url):
    """Kanal listesinden M3U playlist oluşturur (worker proxy'si ile)"""
    lines = ["#EXTM3U"]
    
    for ch in channels:
        name = ch.get('name', '')
        logo = ch.get('logo', '')
        group = ch.get('group', 'Unknown')
        url = ch.get('url') or ch.get('URL') or ''
        
        # Kanal adını temizle
        clean_name = re.sub(r' (4K|HEVC|HD|FHD|UHD|AUSTRIA|AT|DE|\(.*?\)).*', '', name).strip()
        
        # EXTINF
        extinf = f'#EXTINF:-1 tvg-name="{clean_name}" group-title="{group}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f',{clean_name}'
        lines.append(extinf)
        
        # Proxy URL (worker üzerinden)
        if url:
            # Worker'da /play?url=... şeklinde bir endpoint olduğunu varsayıyoruz
            proxy_url = f"{worker_url}/play?url={requests.utils.quote(url)}"
            lines.append(proxy_url)
        else:
            lines.append("# yayın yok")
    
    return "\n".join(lines)

# ============ GIST'E YÜKLEME ============
def upload_to_gist(filename, content, description):
    if not GIST_TOKEN:
        print("[HATA] GIST_TOKEN eksik")
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
        return resp.status_code == 200
    except:
        return False

# ============ ANA FONKSİYON ============
def main():
    print("[1] Token alınıyor...")
    sig = get_auth_signature()
    if not sig:
        print("[✗] Token alınamadı!")
        sys.exit(1)
    print(f"[✓] Token alındı: {sig[:50]}...")
    
    print("[2] Kanal listesi çekiliyor...")
    channels = get_channels()
    print(f"[✓] {len(channels)} kanal bulundu.")
    
    print("[3] M3U playlist oluşturuluyor...")
    m3u = generate_m3u8(channels, WORKER_URL)
    
    print("[4] Gist güncelleniyor...")
    ok1 = upload_to_gist("vavoo_token.txt", sig, "Vavoo Token")
    ok2 = upload_to_gist("vavoo_turkiye.m3u", m3u, "Vavoo Turkey Playlist")
    
    if ok1 and ok2:
        print("[✓] Başarılı!")
    else:
        print("[✗] Gist güncellemesi başarısız!")

if __name__ == "__main__":
    main()
