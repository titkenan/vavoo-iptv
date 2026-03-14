#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import random
import json
import base64
import time
import sys
import os
import re

# ============ AYARLAR ============
GIST_ID = "0956315177e258464a1545babe1e8ac9"  # Sizin Gist ID'niz
GIST_TOKEN = os.environ.get("GIST_TOKEN")     # GitHub Actions'tan gelir
WORKER_URL = "https://sizin-worker.workers.dev"  # Worker adresiniz

# ============ TOKEN ALMA ============
def get_watched_sig():
    """Vavoo için mediahubmx-signature üretir"""
    veclist = [
        "7b2263726561746564223a313637363833303630313030302c22766563223a5b32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32342c32345d7d",
        # Buraya daha fazla vec değeri eklenebilir. Basitlik için tek bir örnek yeterli değil,
        # ama orijinal betikteki "veclist" GitHub'dan çekiliyor. Aşağıda onu da ekleyeceğiz.
    ]
    
    # Eğer veclist yoksa GitHub'dan al
    if len(veclist) == 1:
        try:
            vlist = requests.get("http://mastaaa1987.github.io/repo/veclist.json", timeout=10).json()
            veclist = vlist['value']
        except:
            pass

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
    
    # 1. Kaynak: live2/index?output=json (eski tip, ama hala çalışıyor)
    try:
        resp = requests.get('https://www.vavoo.to/live2/index?output=json', 
                            headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            channels.extend(resp.json())
    except:
        pass

    # 2. Kaynak: mediahubmx-catalog.json (daha güncel, tüm grupları tarar)
    groups = ["Germany", "Turkey", "International", "Sport", "Kids", "Documentaries"]  # Olası gruplar
    sig = get_watched_sig()
    if sig:
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
                        # Gereksiz kanalları filtrele (LUXEMBOURG vb.)
                        if "LUXEMBOURG" not in item["name"]:
                            channels.append(item)
                    next_cursor = r.get("nextCursor")
                    if not next_cursor:
                        break
                    cursor = next_cursor
                except:
                    break

    # Tekrarlanan kanalları temizle (url'ye göre)
    seen = set()
    unique_channels = []
    for ch in channels:
        url = ch.get('url', '')
        if url not in seen:
            seen.add(url)
            unique_channels.append(ch)
    return unique_channels

# ============ M3U OLUŞTURMA ============
def generate_m3u8(channels, worker_url):
    """Kanal listesinden M3U playlist oluşturur (worker proxy'si ile)"""
    m3u_lines = ["#EXTM3U"]
    
    for ch in channels:
        name = ch.get('name', '')
        logo = ch.get('logo', '')
        group = ch.get('group', 'Unknown')
        url = ch.get('url', '')
        
        # Kanal adını temizle (gereksiz ekleri kaldır)
        clean_name = re.sub(r' (4K|HEVC|HD|FHD|UHD|AUSTRIA|AT|DE|\(.*?\)).*', '', name).strip()
        
        # EXTINF satırı
        extinf = f'#EXTINF:-1 tvg-name="{clean_name}" group-title="{group}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f',{clean_name}'
        m3u_lines.append(extinf)
        
        # URL: worker üzerinden proxy'lenecek şekilde düzenle
        # Varsayalım ki worker'da /play/ endpoint'i var ve kanal ID'si veya URL parametresi alıyor.
        # Burada basit bir yöntem: kanalın Vavoo URL'sini worker'a parametre olarak verelim.
        # Worker, bu URL'yi token ile çağırıp akışı proxy'leyecek.
        if url:
            # Örnek: https://worker.workers.dev/play?url=https://vavoo.to/...
            # worker.js'inizi buna göre ayarlamanız gerekebilir.
            proxy_url = f"{worker_url}/play?url={requests.utils.quote(url)}"
            m3u_lines.append(proxy_url)
        else:
            m3u_lines.append("# yayın yok")
    
    return "\n".join(m3u_lines)

# ============ GIST'E YÜKLEME ============
def upload_to_gist(filename, content, description="Vavoo Turkey IPTV"):
    """Dosyayı GitHub Gist'e yükler"""
    if not GIST_TOKEN:
        print("[HATA] GIST_TOKEN environment variable bulunamadı!")
        return False
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = {
        "description": description,
        "files": {
            filename: {
                "content": content
            }
        }
    }
    
    try:
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            print(f"[✓] {filename} Gist'e yüklendi.")
            return True
        else:
            print(f"[✗] Hata {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[✗] İstek hatası: {e}")
        return False

# ============ ANA FONKSİYON ============
def main():
    print("[1] Token alınıyor...")
    sig = get_watched_sig()
    if not sig:
        print("[✗] Token alınamadı!")
        sys.exit(1)
    print(f"[✓] Token: {sig[:50]}...")
    
    print("[2] Kanal listesi çekiliyor...")
    channels = get_channels()
    print(f"[✓] {len(channels)} kanal bulundu.")
    
    print("[3] M3U playlist oluşturuluyor...")
    m3u_content = generate_m3u8(channels, WORKER_URL)
    
    print("[4] Gist güncelleniyor...")
    # Token'ı ayrı bir dosyaya kaydet (worker'ın okuması için)
    upload_to_gist("vavoo_token.txt", sig, "Vavoo Token")
    # Playlist'i kaydet
    upload_to_gist("vavoo_turkiye.m3u", m3u_content, "Vavoo Turkey Playlist")
    
    print("[✓] İşlem tamamlandı.")

if __name__ == "__main__":
    main()
