# ============ TOKEN GIST'E YAZMA ============

def upload_token_to_gist(token, gist_id="0956315177e258464a1545babe1e8ac9"):
    """Token'ı ayrı bir Gist dosyasına yaz"""
    token = get_github_token()
    if not token:
        return None
    
    url = f"https://api.github.com/gists/{gist_id}"
    
    headers = {
        "Authorization": f"token {token}",
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

# ============ ANA PROGRAM GÜNCELLEMESİ ============

if __name__ == "__main__":
    
    # Otomatik mod (GitHub Actions için)
    if "--auto" in sys.argv:
        print("=" * 60)
        print("VAVOO TÜRKİYE - OTOMATİK MOD")
        print("=" * 60)
        
        api = VavooAPI()
        
        # 1. Token al
        if not api.get_auth():
            print("❌ Token alınamadı!")
            sys.exit(1)
        
        # 2. Token'ı Gist'e yaz
        if not upload_token_to_gist(api.signature):
            print("⚠️ Token Gist'e yazılamadı, devam ediliyor...")
        
        # 3. Kanalları çek
        channels = api.get_channels()
        
        if not channels:
            print("❌ Kanal çekilemedi!")
            sys.exit(1)
        
        # 4. M3U oluştur
        if not create_m3u(channels, api, "vavoo_turkiye.m3u"):
            print("❌ M3U oluşturulamadı!")
            sys.exit(1)
        
        # 5. Playlist'i Gist'e yükle
        result = upload_m3u_to_gist("vavoo_turkiye.m3u")
        
        if result:
            print("\n" + "=" * 60)
            print("✅ TÜM İŞLEMLER BAŞARILI!")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ GIST YÜKLEME BAŞARISIZ!")
            print("=" * 60)
            sys.exit(1)