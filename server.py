@app.get("/playlist.m3u")
async def playlist():
    """Tüm kanalları çek ve M3U oluştur"""
    from datetime import datetime
    
    # Vavoo'dan tüm kanalları çek
    sig = get_lokke_signature()
    if not sig:
        return PlainTextResponse("#EXTM3U\n# Error: Auth failed", status_code=503)
    
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig,
    }
    
    all_channels = []
    cursor = 0
    
    # Tüm kanalları çek (pagination)
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
            r = resp.json()
            items = r.get("items", [])
            all_channels.extend(items)
            cursor = r.get("nextCursor")
            if not cursor:
                break
        except:
            break
    
    # M3U oluştur
    m3u = ["#EXTM3U"]
    base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    for ch in all_channels:
        name = ch.get("name", "Unknown")
        ch_id = None
        
        if isinstance(ch.get("ids"), dict):
            ch_id = ch["ids"].get("id")
        if not ch_id:
            match = re.search(r'/play/(\d+)', ch.get("url", ""))
            if match:
                ch_id = match.group(1)
        
        if ch_id:
            m3u.append(f'#EXTINF:-1,{name}')
            m3u.append(f'{base_url}/channel/{ch_id}')
    
    return PlainTextResponse("\n".join(m3u), media_type="application/x-mpegURL")
