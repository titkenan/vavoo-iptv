#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vavoo_resolver.py - TAM ÇALIŞAN VERSİYON (Proxy/Redirect Destekli)
Özellikler:
- Lokke App imzası ile authentication
- Her kanal için anlık URL çözümleme
- M3U'da proxy URL'leri (kendi sunucunuzda çalıştırmanız gerekir)
- Veya çözümlenmiş URL'lerle direkt oynatma
"""

import sys
import requests
import json
import os
import re
import time
import base64
import random
from urllib.parse import urlparse, parse_qs

# config/domains.json
config_path = os.path.join(os.path.dirname(__file__), 'config', 'domains.json')
if os.path.exists(config_path):
    with open(config_path, encoding='utf-8') as f:
        DOMAINS = json.load(f)
else:
    DOMAINS = {}

# Yeni çalışan domainler
VAVOO_DOMAIN = DOMAINS.get("vavoo", "vavoo.to")
VAVOO_TV_DOMAIN = "www.vavoo.tv"
LOKKE_DOMAIN = "www.lokke.app"

# KATEGORİ SIRALAMASI
CATEGORY_ORDER = [
    "ulusal", "sinema", "spor", "belgesel", "haber", "cocuk", "muzik", "diger"
]

TARGET_CATEGORIES = {
    "ulusal": ["trt", "atv", "show", "star", "kanal d", "fox", "tv8", "beyaz", "teve2", "haberturk", "cnn turk", "ntv", "tv100", "a2", "kanal 7", "360", "tlc"],
    "sinema": ["sinema", "movie", "film", "dizi", "blu", "moviebox", "cinemax", "hbo", "fox movies", "filmbox"],
    "spor": ["spor", "bein", "s sport", "tivibu spor", "aspor", "trt spor", "fb tv", "gs tv", "bjk tv", "eurosport", "sport"],
    "belgesel": ["belgesel", "discovery", "national geo", "nat geo", "history", "trt belgesel", "yaban", "bbc earth", "animal planet"],
    "haber": ["haber", "news", "cnn", "ntv", "haberturk", "tv100", "bloomberg", "trt haber", "ulke", "24"],
    "cocuk": ["cocuk", "çocuk", "cartoon", "disney", "nickelodeon", "trt çocuk", "minika", "baby", "kid"],
    "muzik": ["muzik", "müzik", "kral", "powerturk", "power", "number one", "trt müzik", "dream", "mtv"]
}

class VavooAuth:
    def __init__(self):
        self.signature = None
        self.last_update = 0
        
    def get_lokke_signature(self):
        """Lokke App imzası al"""
        # 4 dakikada bir yenile (güvenli taraf)
        if self.signature and (time.time() - self.last_update) < 240:
            return self.signature
            
        headers = {
            "user-agent": "okhttp/4.11.0",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8"
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
            result = resp.json()
            self.signature = result.get("addonSig")
            self.last_update = time.time()
            print(f"[AUTH] Lokke imzası alındı (expires: 5min)")
            return self.signature
        except Exception as e:
            print(f"[HATA] Lokke imzası alınamadı: {e}", file=sys.stderr)
            return None

# Global auth instance
vavoo_auth = VavooAuth()

def resolve_link(link):
    """MediaHubMX ile link çözümle - ANA FONKSİYON"""
    sig = vavoo_auth.get_lokke_signature()
    if not sig:
        print("[HATA] İmza alınamadı, link çözümlenemiyor", file=sys.stderr)
        return None
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig
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
            timeout=10
        )
        resp.raise_for_status()
        result = resp.json()
        if result and len(result) > 0:
            resolved = result[0].get("url")
            print(f"[RESOLVE] ✓ {link[:50]}... -> {resolved[:60]}...")
            return resolved
    except Exception as e:
        print(f"[HATA] Link çözümleme hatası: {e}", file=sys.stderr)
    
    return None

def get_all_turkey_channels():
    """Türkiye'deki tüm kanalları çeker"""
    sig = vavoo_auth.get_lokke_signature()
    if not sig:
        print("[HATA] Lokke imzası alınamadı!", file=sys.stderr)
        return []
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig
    }
    
    all_channels = []
    cursor = 0
    page = 1
    
    print("[INFO] Türkiye kanalları çekiliyor...")
    
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
            print(f"  Sayfa {page}: {len(items)} kanal")
            all_channels.extend(items)
            cursor = r.get("nextCursor")
            if not cursor:
                break
            page += 1
        except Exception as e:
            print(f"[HATA] Sayfa {page} hatası: {e}", file=sys.stderr)
            break
    
    print(f"[INFO] Toplam {len(all_channels)} kanal çekildi.")
    return all_channels

def categorize_channel(channel_name):
    """Kanal adına göre kategori belirler"""
    name_lower = channel_name.lower()
    
    for category in CATEGORY_ORDER:
        if category == "diger":
            continue
        keywords = TARGET_CATEGORIES.get(category, [])
        for keyword in keywords:
            if keyword in name_lower:
                return category
    
    return "diger"

def filter_and_sort_channels(channels):
    """Kanalları kategorilere göre filtreler ve sıralar"""
    categorized = {cat: [] for cat in CATEGORY_ORDER}
    
    total = len(channels)
    for i, ch in enumerate(channels):
        name = ch.get("name", "").strip()
        if not name:
            continue
            
        category = categorize_channel(name)
        ch["category"] = category
        
        # HLS URL'sini sakla
        hls_url = ch.get("url")
        if hls_url:
            ch["hls_url"] = hls_url
            categorized[category].append(ch)
        
        if (i + 1) % 50 == 0:
            print(f"  İşleniyor: {i+1}/{total}...")
    
    # Her kategori içinde alfabetik sırala
    for cat in categorized:
        categorized[cat] = sorted(categorized[cat], key=lambda x: x.get("name", "").upper())
    
    # Özet göster
    print("\n" + "=" * 50)
    print("KATEGORİ ÖZETİ")
    print("=" * 50)
    for cat in CATEGORY_ORDER:
        count = len(categorized[cat])
        if count > 0:
            print(f"{cat.upper()}: {count} kanal")
    
    # Sıralı listeyi oluştur
    sorted_channels = []
    for cat in CATEGORY_ORDER:
        sorted_channels.extend(categorized[cat])
    
    return sorted_channels

def save_m3u_with_resolved_urls(channels, filename="vavoo_turkiye.m3u", max_channels=None):
    """
    ÇÖZÜMLENMİŞ DİREKT URL'LER ile M3U oluştur
    UYARI: Bu URL'ler geçicidir (genelde 4-6 saat geçerli)
    """
    if not channels:
        print("[HATA] Kaydedilecek kanal yok!", file=sys.stderr)
        return False
    
    # Test için sınırlı sayıda kanal
    if max_channels:
        channels = channels[:max_channels]
        print(f"[INFO] Test modu: İlk {max_channels} kanal çözümlenecek")
    
    print(f"[INFO] {len(channels)} kanal için URL çözümleniyor...")
    print("[UYARI] Bu işlem biraz zaman alabilir (her kanal ~1-2 saniye)")
    
    success_count = 0
    failed_channels = []
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"# Vavoo Turkey Playlist - Çözümlenmiş URL'ler\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# UYARI: Bu URL'ler geçicidir, kısa sürede expire olabilir!\n")
            f.write(f"# Toplam Kanal: {len(channels)}\n\n")
            
            current_category = None
            
            for i, ch in enumerate(channels):
                name = ch.get("name", "Bilinmeyen").strip()
                hls_url = ch.get("hls_url")
                
                if not hls_url:
                    continue
                
                category = ch.get("category", "diger").capitalize()
                
                # Linki çözümle
                print(f"[{i+1}/{len(channels)}] {name} çözümleniyor...")
                resolved_url = resolve_link(hls_url)
                
                if not resolved_url:
                    print(f"  ✗ BAŞARISIZ: {name}")
                    failed_channels.append(name)
                    continue
                
                print(f"  ✓ BAŞARILI")
                success_count += 1
                
                # Kategori değiştiğinde
                if category != current_category:
                    f.write(f"\n#EXTGRP:{category}\n")
                    current_category = category
                
                # EXTINF
                f.write(f'#EXTINF:-1 group-title="{category}",{name}\n')
                
                # ÖNEMLİ: Header'lar çok kritik!
                f.write('#EXTVLCOPT:http-user-agent=VAVOO/2.6\n')
                f.write('#EXTVLCOPT:http-referrer=https://vavoo.to/\n')
                f.write('#EXTVLCOPT:http-origin=https://vavoo.to\n')
                
                # Çözümlenmiş direkt URL
                f.write(f"{resolved_url}\n")
                
                # Rate limiting - çok hızlı istek atma
                time.sleep(0.5)
        
        print(f"\n{'=' * 50}")
        print(f"✅ M3U OLUŞTURULDU: {filename}")
        print(f"📊 Başarılı: {success_count}/{len(channels)}")
        print(f"📊 Başarısız: {len(failed_channels)}")
        if failed_channels[:5]:
            print(f"⚠️  Başarısız kanallar (ilk 5): {', '.join(failed_channels[:5])}")
        print(f"{'=' * 50}")
        
        return True
        
    except Exception as e:
        print(f"[HATA] Dosya yazma hatası: {e}", file=sys.stderr)
        return False

def test_single_channel(channel_name):
    """Tek kanal test et"""
    print(f"[INFO] '{channel_name}' aranıyor...")
    channels = get_all_turkey_channels()
    
    wanted = channel_name.upper()
    found = None
    
    for ch in channels:
        if wanted in ch.get("name", "").upper():
            found = ch
            break
    
    if not found:
        print(f"[HATA] '{channel_name}' bulunamadı!", file=sys.stderr)
        return
    
    hls_url = found.get("url")
    print(f"\n{'='*60}")
    print(f"KANAL: {found.get('name')}")
    print(f"HLS URL: {hls_url}")
    print(f"{'='*60}")
    
    # Linki çözümle
    print("\n[1] Link çözümleniyor...")
    resolved = resolve_link(hls_url)
    
    if not resolved:
        print("[HATA] Link çözümlenemedi!")
        return
    
    print(f"[2] Çözümlenmiş URL: {resolved[:80]}...")
    
    # Stream test et
    print("[3] Stream test ediliyor...")
    try:
        headers = {
            "User-Agent": "VAVOO/2.6",
            "Referer": "https://vavoo.to/",
            "Origin": "https://vavoo.to"
        }
        resp = requests.head(resolved, headers=headers, timeout=10, allow_redirects=True)
        print(f"[4] HTTP Status: {resp.status_code}")
        print(f"[4] Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        
        if resp.status_code == 200:
            print("\n✅ Stream AKTİF görünüyor!")
            print("\nVLC'de test etmek için:")
            print(f"  1. VLC aç")
            print(f"  2. Ağ Akışı Aç (Ctrl+N)")
            print(f"  3. URL yapıştır: {resolved}")
        else:
            print(f"\n⚠️  Stream durumu belirsiz (HTTP {resp.status_code})")
            
    except Exception as e:
        print(f"\n⚠️  Stream test hatası: {e}")

# ====================== ANA KISIM ======================
if __name__ == "__main__":
    
    # === TEK KANAL TEST (ÖNERİLEN) ===
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        test_single_channel(sys.argv[1])
        sys.exit(0)
    
    # === TEST MODU (İlk 10 kanal) ===
    if "--test" in sys.argv:
        print("=" * 60)
        print("TEST MODU - İlk 10 kanal çözümlenecek")
        print("=" * 60)
        
        all_channels = get_all_turkey_channels()
        if not all_channels:
            sys.exit(1)
        
        sorted_channels = filter_and_sort_channels(all_channels)
        save_m3u_with_resolved_urls(sorted_channels, "vavoo_test.m3u", max_channels=10)
        sys.exit(0)
    
    # === TAM M3U (Tüm kanallar - UZUN SÜRER) ===
    if "--full-m3u" in sys.argv or len(sys.argv) == 1:
        print("=" * 60)
        print("VAVOO TÜRKİYE - ÇÖZÜMLENMİŞ URL VERSİYONU")
        print("=" * 60)
        print("UYARI: Bu işlem 10-15 dakika sürebilir!")
        print("Daha hızlı test için: python vavoo_resolver.py --test")
        print("Tek kanal test için: python vavoo_resolver.py 'TRT 1'")
        print("-" * 60)
        
        start_time = time.time()
        
        all_channels = get_all_turkey_channels()
        if not all_channels:
            sys.exit(1)
        
        sorted_channels = filter_and_sort_channels(all_channels)
        
        # Tüm kanalları çözümle (çok uzun sürer!)
        save_m3u_with_resolved_urls(sorted_channels, "vavoo_turkiye.m3u")
        
        elapsed = time.time() - start_time
        print(f"\n⏱️  Toplam süre: {elapsed/60:.1f} dakika")
        
        sys.exit(0)

    # === YARDIM ===
    print("Kullanım:", file=sys.stderr)
    print("  python vavoo_resolver.py --test           # İlk 10 kanalı test et (hızlı)", file=sys.stderr)
    print("  python vavoo_resolver.py --full-m3u       # Tüm kanalları çözümle (uzun)", file=sys.stderr)
    print("  python vavoo_resolver.py 'TRT 1'          # Tek kanal test et", file=sys.stderr)
    sys.exit(1)