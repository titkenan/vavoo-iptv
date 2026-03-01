#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vavoo_resolver.py - TÜRKİYE KATEGORİ FİLTRELİ VERSİYON
+ Otomatik GitHub Gist Yükleme
"""

import sys
import requests
import json
import os
import re
import time

# ============ AYARLAR ============
GITHUB_USERNAME = "titkenan"
GIST_ID = "0956315177e258464a1545babe1e8ac9"

# GEÇİCİ TEST TOKEN - SADECE TEST İÇİN!
# Gerçek token'ınızı buraya yapıştırın, test ettikten sonra silin
TEST_TOKEN = ""  # Örnek: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

def get_github_token():
    """GitHub Actions veya ortam değişkeninden token al"""
    
    # 1. GEÇİCİ TEST TOKEN (eğer varsa)
    if TEST_TOKEN:
        print("[TOKEN] ⚠️  GEÇİCİ TEST TOKEN kullanılıyor!")
        print("[TOKEN] Güvenlik için test sonrası silmeyi unutmayın!")
        return TEST_TOKEN
    
    # 2. GitHub Actions ortamı (GIST_TOKEN)
    token = os.getenv("GIST_TOKEN")
    if token:
        print(f"[TOKEN] ✓ GIST_TOKEN bulundu: {token[:15]}...")
        return token
    
    # 3. GitHub Actions ortamı (GITHUB_TOKEN)
    token = os.getenv("GITHUB_TOKEN")
    if token:
        print(f"[TOKEN] ✓ GITHUB_TOKEN bulundu: {token[:15]}...")
        return token
    
    # 4. Lokal geliştirme için config.json
    config_paths = [
        'config.json',
        os.path.join(os.path.dirname(__file__), 'config.json'),
        os.path.expanduser('~/.vavoo/config.json')
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    token = config.get("github_token") or config.get("token") or config.get("gist_token")
                    if token:
                        print(f"[TOKEN] ✓ config.json'dan alındı: {token[:15]}...")
                        return token
            except:
                continue
    
    print("[TOKEN] ❌ Hiçbir token bulunamadı!")
    return None

def upload_to_gist(filename, content, description="Vavoo Turkey IPTV"):
    """Dosyayı GitHub Gist'e yükle"""
    token = get_github_token()
    if not token:
        print("[GIST] ❌ Token yok! İşlem iptal.")
        return None
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    
    headers = {
        "Authorization": f"token {token}",
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
        print(f"[GIST] API çağrısı yapılıyor...")
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        
        print(f"[GIST] Yanıt kodu: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            raw_url = result['files'][filename]['raw_url']
            
            print(f"\n{'='*60}")
            print("✅ GIST BAŞARILI GÜNCELLENDİ")
            print(f"{'='*60}")
            print(f"🔗 GitHub: {result['html_url']}")
            print(f"📄 Raw: {raw_url}")
            print(f"🌐 CDN: {raw_url.replace('gist.githubusercontent.com', 'gistcdn.githack.com')}")
            print(f"{'='*60}")
            return result
            
        elif resp.status_code == 401:
            print("[GIST] ❌ 401: Token geçersiz veya yetkisiz!")
            print("[GIST] GitHub'da token'ı kontrol edin: Settings > Developer settings > Personal access tokens")
            print("[GIST] Gerekli scope: gist (Create gists)")
            return None
            
        elif resp.status_code == 404:
            print("[GIST] ❌ 404: Gist bulunamadı!")
            print(f"[GIST] Gist ID: {GIST_ID}")
            return None
            
        else:
            print(f"[GIST] ❌ Hata {resp.status_code}: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"[GIST] ❌ İstek hatası: {e}")
        return None

def upload_m3u_to_gist(filename="vavoo_turkiye.m3u"):
    """M3U dosyasını Gist'e yükle"""
    print(f"\n[GIST] Yükleniyor: {filename}")
    
    if not os.path.exists(filename):
        print(f"[GIST] ❌ Dosya bulunamadı: {os.path.abspath(filename)}")
        return None
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"[GIST] Dosya boyutu: {len(content)} bytes")
        
        return upload_to_gist(
            filename=filename,
            content=content,
            description=f"Vavoo Turkey IPTV - {time.strftime('%Y-%m-%d %H:%M')}"
        )
        
    except Exception as e:
        print(f"[GIST] ❌ Dosya okuma hatası: {e}")
        return None

# ============ VAVOO API ============

class VavooAPI:
    def __init__(self):
        self.signature = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "okhttp/4.11.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
        })
    
    def get_auth(self):
        ping_data = {
            "token": "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g",
            "reason": "app-focus",
            "locale": "tr",
            "theme": "dark",
            "metadata": {
                "device": {
                    "type": "Handset",
                    "brand": "samsung",
                    "model": "SM-G991B",
                    "name": "s21",
                    "uniqueId": "d10e5d99ab665233"
                },
                "os": {
                    "name": "android",
                    "version": "13",
                    "abis": ["arm64-v8a"],
                    "host": "android"
                },
                "app": {
                    "platform": "android",
                    "version": "3.2.0",
                    "buildId": "3002000",
                    "engine": "hbc85",
                    "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],
                    "installer": "com.android.vending"
                },
                "version": {
                    "package": "tv.vavoo.app",
                    "binary": "3.2.0",
                    "js": "3.2.0"
                }
            },
            "appFocusTime": 0,
            "playerActive": False,
            "playDuration": 0,
            "devMode": False,
            "hasAddon": True,
            "castConnected": False,
            "package": "tv.vavoo.app",
            "version": "3.2.0",
            "process": "app",
            "firstAppStart": int(time.time() * 1000),
            "lastAppStart": int(time.time() * 1000),
            "ipLocation": "",
            "adblockEnabled": True,
            "proxy": {
                "supported": ["ss", "openvpn"],
                "engine": "ss",
                "ssVersion": 1,
                "enabled": True,
                "autoServer": True,
                "id": "tr-ist"
            },
            "iap": {"supported": False}
        }
        
        try:
            resp = self.session.post(
                "https://www.vavoo.tv/api/app/ping",
                json=ping_data,
                timeout=15
            )
            resp.raise_for_status()
            result = resp.json()
            self.signature = result.get("addonSig")
            
            if self.signature:
                print(f"[AUTH] ✓ Token: {self.signature[:30]}...")
                return True
            return False
                
        except Exception as e:
            print(f"[AUTH] ✗ Hata: {e}")
            return False
    
    def get_channels(self, country="Turkey"):
        if not self.signature and not self.get_auth():
            return []
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "mediahubmx-signature": self.signature
        }
        
        all_channels = []
        cursor = 0
        page = 1
        
        print(f"[API] {country} kanalları çekiliyor...")
        
        while True:
            data = {
                "language": "tr",
                "region": "TR",
                "catalogId": "iptv",
                "id": "iptv",
                "adult": False,
                "search": "",
                "sort": "name",
                "filter": {"group": country},
                "cursor": cursor,
                "clientVersion": "3.2.0"
            }
            
            try:
                resp = self.session.post(
                    "https://vavoo.to/mediahubmx-catalog.json",
                    headers=headers,
                    json=data,
                    timeout=15
                )
                
                if resp.status_code == 401:
                    if not self.get_auth():
                        break
                    headers["mediahubmx-signature"] = self.signature
                    continue
                
                resp.raise_for_status()
                result = resp.json()
                items = result.get("items", [])
                
                if not items:
                    break
                    
                print(f"  Sayfa {page}: {len(items)} kanal")
                all_channels.extend(items)
                
                cursor = result.get("nextCursor")
                if not cursor:
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"[API] Hata: {e}")
                break
        
        print(f"[API] Toplam: {len(all_channels)} kanal")
        return all_channels
    
    def get_stream_url(self, channel_data):
        direct_url = channel_data.get("url", "")
        
        if direct_url:
            if "vavoo-iptv" in direct_url:
                stream_url = direct_url.strip()
            else:
                stream_url = direct_url.replace("/play/", "/vavoo-iptv/play/").strip()
            
            return {
                "url": stream_url,
                "headers": {
                    "mediahubmx-signature": self.signature,
                    "User-Agent": "okhttp/4.11.0",
                    "Referer": "https://vavoo.to/",
                    "Origin": "https://vavoo.to"
                }
            }
        
        channel_id = None
        if isinstance(channel_data.get("ids"), dict):
            channel_id = channel_data["ids"].get("id")
        
        if channel_id and self.signature:
            return {
                "url": f"https://vavoo.to/vavoo-iptv/play/{channel_id}",
                "headers": {
                    "mediahubmx-signature": self.signature,
                    "User-Agent": "okhttp/4.11.0",
                    "Referer": "https://vavoo.to/",
                    "Origin": "https://vavoo.to"
                }
            }
        
        return None

# ============ KATEGORİ VE M3U ============

CATEGORY_ORDER = [
    "ulusal", "sinema", "spor", "belgesel", "haber", "cocuk", "muzik", "diger"
]

TARGET_CATEGORIES = {
    "ulusal": ["trt", "atv", "show", "star", "kanal d", "fox", "tv8", "beyaz", "teve2", "haberturk", "cnn", "ntv", "a2", "kanal 7", "360"],
    "sinema": ["sinema", "movie", "film", "dizi", "blu", "moviebox", "cinemax", "hbo"],
    "spor": ["spor", "bein", "s sport", "tivibu spor", "aspor", "trt spor", "fb tv", "gs tv", "bjk tv"],
    "belgesel": ["belgesel", "discovery", "nat geo", "history", "yaban", "bbc earth"],
    "haber": ["haber", "a haber", "cnn", "ntv", "haberturk", "tv100", "bloomberg", "trt haber"],
    "cocuk": ["cocuk", "cartoon", "disney", "nickelodeon", "trt cocuk", "minika", "baby"],
    "muzik": ["muzik", "kral", "powerturk", "power", "number one", "trt muzik", "dream"]
}

def categorize_channel(name):
    name_lower = name.lower()
    for category in CATEGORY_ORDER:
        if category == "diger":
            continue
        for keyword in TARGET_CATEGORIES.get(category, []):
            if keyword in name_lower:
                return category
    return "diger"

def create_m3u(channels, api, filename="vavoo_turkiye.m3u"):
    if not channels:
        return False
    
    categorized = {cat: [] for cat in CATEGORY_ORDER}
    
    for ch in channels:
        name = ch.get("name", "").strip()
        if not name:
            continue
            
        stream_info = api.get_stream_url(ch)
        if not stream_info:
            continue
        
        category = categorize_channel(name)
        ch["category"] = category
        ch["stream"] = stream_info
        categorized[category].append(ch)
    
    for cat in categorized:
        categorized[cat] = sorted(categorized[cat], key=lambda x: x["name"].upper())
    
    print("\n" + "=" * 50)
    print("KATEGORİ ÖZETİ")
    print("=" * 50)
    
    for cat in CATEGORY_ORDER:
        count = len(categorized[cat])
        if count > 0:
            print(f"\n{cat.upper()}: {count} kanal")
            for ch in categorized[cat][:3]:
                print(f"  • {ch['name']}")
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#EXTM3U url-tvg=\"\" tvg-shift=0\n")
            f.write(f"# Vavoo Turkey - {time.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"# Total: {sum(len(v) for v in categorized.values())} channels\n\n")
            
            current_category = None
            
            for cat in CATEGORY_ORDER:
                for ch in categorized.get(cat, []):
                    name = ch["name"]
                    stream = ch["stream"]
                    cat_cap = cat.capitalize()
                    
                    if cat_cap != current_category:
                        f.write(f"\n#EXTGRP:{cat_cap}\n")
                        current_category = cat_cap
                    
                    f.write(f'#EXTINF:-1 group-title="{cat_cap}",{name}\n')
                    f.write(f'#EXTVLCOPT:http-user-agent=okhttp/4.11.0\n')
                    f.write(f'#EXTVLCOPT:http-referrer=https://vavoo.to/\n')
                    f.write(f"{stream['url']}\n")
        
        total = sum(len(v) for v in categorized.values())
        print(f"\n✅ {filename} oluşturuldu ({total} kanal)")
        return True
        
    except Exception as e:
        print(f"[M3U] ❌ Hata: {e}")
        return False

# ============ ANA PROGRAM ============

if __name__ == "__main__":
    
    # Otomatik mod (GitHub Actions için)
    if "--auto" in sys.argv:
        print("=" * 60)
        print("VAVOO TÜRKİYE - OTOMATİK MOD")
        print("=" * 60)
        
        api = VavooAPI()
        channels = api.get_channels()
        
        if not channels:
            print("❌ Kanal çekilemedi!")
            sys.exit(1)
        
        if not create_m3u(channels, api, "vavoo_turkiye.m3u"):
            print("❌ M3U oluşturulamadı!")
            sys.exit(1)
        
        result = upload_m3u_to_gist("vavoo_turkiye.m3u")
        
        if result:
            print("\n✅ BAŞARILI!")
            sys.exit(0)
        else:
            print("\n❌ GIST BAŞARISIZ!")
            sys.exit(1)
    
    # Manuel mod
    if len(sys.argv) == 1 or "--full" in sys.argv:
        print("=" * 60)
        print("VAVOO TÜRKİYE M3U OLUŞTURUCU")
        print("=" * 60)
        
        api = VavooAPI()
        channels = api.get_channels()
        
        if channels and create_m3u(channels, api):
            print("\nGist yüklemek için: --gist")
            if "--gist" in sys.argv:
                upload_m3u_to_gist()
        
        sys.exit(0)
    
    # Sadece Gist yükleme
    if "--gist" in sys.argv or "--upload" in sys.argv:
        upload_m3u_to_gist()
        sys.exit(0)
    
    # Yardım
    print("Kullanım:")
    print("  python vavoo_resolver.py           # Manuel oluştur")
    print("  python vavoo_resolver.py --auto    # Otomatik (GitHub Actions)")
    print("  python vavoo_resolver.py --gist    # Gist'e yükle")