import re
import sys

# Cloudflare Worker URL'in
WORKER_URL = "https://vavoo-iptv.efda302cd88170229cb0d3156b1406e7.workers.dev"

def add_proxy_to_m3u(input_file, output_file):
    """M3U dosyasındaki stream URL'lerine proxy ekler"""
    
    try:
        # Dosyayı oku
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        url_count = 0
        
        for line in lines:
            # Boş satırları atla
            if not line.strip():
                new_lines.append(line)
                continue
            
            # HTTP/HTTPS ile başlayan satırları yakala (stream URL'leri)
            if line.strip().startswith('http://') or line.strip().startswith('https://'):
                original_url = line.strip()
                # Proxy'li URL oluştur
                proxied_url = f"{WORKER_URL}/?url={original_url}\n"
                new_lines.append(proxied_url)
                url_count += 1
            else:
                # Diğer satırları olduğu gibi ekle (#EXTINF, #EXTVLCOPT vb.)
                new_lines.append(line)
        
        # Yeni dosyayı yaz
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"✅ İşlem başarılı!")
        print(f"📥 Giriş dosyası: {input_file}")
        print(f"📤 Çıkış dosyası: {output_file}")
        print(f"🔗 Toplam {url_count} stream URL'sine proxy eklendi")
        print(f"\n🚀 Yeni m3u linkin:")
        print(f"https://raw.githubusercontent.com/titkenan/vavoo-iptv/main/{output_file}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Hata: {input_file} dosyası bulunamadı!")
        return False
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        return False

if __name__ == "__main__":
    # M3U dosyalarını işle
    input_file = "vavoo_turkiye.m3u"
    output_file = "vavoo_turkiye_proxy.m3u"
    
    print("🔄 Cloudflare Proxy ekleniyor...")
    print(f"🌐 Worker URL: {WORKER_URL}\n")
    
    success = add_proxy_to_m3u(input_file, output_file)
    
    if success:
        print("\n✨ Artık GitHub'a push edebilirsin:")
        print("   git add vavoo_turkiye_proxy.m3u")
        print("   git commit -m '🚀 Cloudflare proxy eklendi'")
        print("   git push")
    else:
        sys.exit(1)
