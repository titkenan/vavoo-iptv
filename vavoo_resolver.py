#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import json
import os
import re
import time

# ============ AYARLAR ============
GITHUB_USERNAME = "titkenan"
GIST_ID = "0956315177e258464a1545babe1e8ac9"
# ... devamı
def upload_to_gist(filename, content, description="Vavoo Turkey IPTV"):
    """Dosyayı GitHub Gist'e yükle - SADECE GIST_TOKEN ile"""
    
    token = get_github_token()
    if not token:
        print("[GIST] ❌ Token olmadan devam edilemez!")
        return None
    
    # DÜZELTME: Boşluk kaldırıldı
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
        print(f"[GIST] API çağrısı: PATCH {url}")
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        
        print(f"[GIST] HTTP {resp.status_code}")
        
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
            print("[GIST] ❌ 401: Yetkisiz - Token geçersiz veya gist scope'u yok!")
            return None
            
        elif resp.status_code == 404:
            print("[GIST] ❌ 404: Gist bulunamadı - ID yanlış olabilir")
            print(f"[GIST] Kontrol edilen ID: {GIST_ID}")
            return None
            
        else:
            print(f"[GIST] ❌ Hata: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"[GIST] ❌ İstek hatası: {e}")
        return None

def upload_token_to_gist(token, gist_id="0956315177e258464a1545babe1e8ac9"):
    """Token'ı ayrı bir Gist dosyasına yaz"""
    github_token = get_github_token()
    if not github_token:
        return None
    
    # DÜZELTME: Boşluk kaldırıldı
    url = f"https://api.github.com/gists/{gist_id}"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "description": f"Vavoo Token - {time.strftime('%Y-%m-%d %H:%M')}",
        "files": {
            "vavoo_token.txt": {
                "content": token
            }
        }
    }
    
    try:
        resp = requests.patch(url, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            print(f"[TOKEN] ✓ Token Gist'e yazıldı")
            return True
        else:
            print(f"[TOKEN] ✗ Hata: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[TOKEN] ✗ İstek hatası: {e}")
        return False

