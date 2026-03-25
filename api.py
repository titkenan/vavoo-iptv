#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api.py - Vavoo IPTV API (Render.com Edition)
- Database'den kanal servisi
- Dinamik resolve + cache
- M3U playlist endpoint
"""

import os, sys, asyncio, time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from multiprocessing import Process
from uvicorn import Server, Config
import hashlib

import utils.common as common
from utils.common import Logger as Logger
import utils.vavoo as vavoo

cachepath = common.cp
listpath = common.lp
con1 = common.con1

common.check()

# CACHE (15 dakika)
RESOLVE_CACHE = {}
CACHE_DURATION = 900

def get_cached_resolve(hls_url):
    """Cache'li resolve"""
    cache_key = hashlib.md5(hls_url.encode()).hexdigest()
    
    if cache_key in RESOLVE_CACHE:
        url, timestamp = RESOLVE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            Logger(1, f"Cache HIT: {hls_url[:50]}")
            return url
    
    # Yeni resolve
    resolved = vavoo.resolve_link(hls_url)
    if resolved:
        RESOLVE_CACHE[cache_key] = (resolved, time.time())
        Logger(1, f"Cache MISS (resolved): {hls_url[:50]}")
        return resolved
    
    return None

class UvicornServer(Process):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
    def stop(self): self.terminate()
    def run(self, *args, **kwargs):
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        server = Server(config=self.config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try: loop.run_until_complete(server.serve())
        except: pass
        finally: loop.close()

app = FastAPI(title="Vavoo IPTV API")

@app.get("/")
async def root():
    """Ana sayfa"""
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    # Kanal sayısı
    cur = con1.cursor()
    cur.execute('SELECT COUNT(*) as total FROM channel')
    total = cur.fetchone()['total']
    
    return HTMLResponse(f"""
    <html>
    <head><title>Vavoo IPTV API</title></head>
    <body style="font-family: monospace; padding: 20px;">
        <h1>🎬 Vavoo IPTV API</h1>
        <p>✅ Server online</p>
        <p>📺 Total channels: {total}</p>
        <p>🔗 Cached resolves: {len(RESOLVE_CACHE)}</p>
        <hr>
        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/playlist.m3u">/playlist.m3u</a> - Full M3U playlist</li>
            <li><a href="/epg.xml">/epg.xml</a> - EPG guide</li>
            <li>/channel/CHANNEL_ID - Stream proxy</li>
        </ul>
        <hr>
        <p><strong>M3U Link (Vavoo için):</strong></p>
        <code style="background: #f0f0f0; padding: 10px; display: block;">
        {base}/playlist.m3u
        </code>
    </body>
    </html>
    """)

@app.get("/playlist.m3u")
async def playlist():
    """Dinamik M3U playlist"""
    base = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    cur = con1.cursor()
    cur.execute('SELECT * FROM channel ORDER BY name ASC')
    channels = cur.fetchall()
    
    lines = [
        "#EXTM3U",
        f"# Vavoo Turkey - Database Edition",
        f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"# Total: {len(channels)} channels",
        ""
    ]
    
    for ch in channels:
        name = ch['name']
        ch_id = ch['id']
        logo = ch.get('logo', '')
        group = ch.get('group', 'Ulusal')
        
        # EXTINF
        extinf = f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f' group-title="{group}",{name}'
        lines.append(extinf)
        
        # VLC options
        lines.append('#EXTVLCOPT:http-user-agent=VAVOO/2.6')
        lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/')
        
        # Proxy URL
        lines.append(f'{base}/channel/{ch_id}')
        lines.append("")
    
    return PlainTextResponse("\n".join(lines), media_type="audio/x-mpegurl")

@app.get("/epg.xml")
async def epg():
    """EPG guide"""
    cur = con1.cursor()
    cur.execute('SELECT * FROM channel')
    channels = cur.fetchall()
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>\n']
    xml.append('<tv generator-info-name="Vavoo IPTV API">\n')
    
    for ch in channels:
        name = ch['name']
        ch_id = ch['id']
        logo = ch.get('logo', '')
        
        xml.append(f'  <channel id="{ch_id}">\n')
        xml.append(f'    <display-name>{name}</display-name>\n')
        if logo:
            xml.append(f'    <icon src="{logo}"/>\n')
        xml.append('  </channel>\n')
    
    xml.append('</tv>')
    
    return PlainTextResponse("".join(xml), media_type="application/xml")

@app.get("/{m3u8}.m3u8")
async def m3u8(m3u8: str):
    """Statik M3U8 dosyaları"""
    f = os.path.join(listpath, m3u8+'.m3u8')
    if os.path.exists(f):
        return FileResponse(f, media_type="application/x-mpegURL; charset=utf-8")
    raise HTTPException(status_code=404, detail="Liste yok.")

@app.get("/channel/{sid}")
async def channel(sid: str):
    """Dinamik stream endpoint - CACHE'Lİ RESOLVE"""
    cur = con1.cursor()
    cur.execute('SELECT * FROM channel WHERE id=?', (sid,))
    data = cur.fetchone()
    
    if not data:
        raise HTTPException(status_code=404, detail="Kanal yok")

    # YÖNTEM 1: HLS + Lokke Signature (Cache'li)
    if data['hls']:
        hls_link = data['hls']
        Logger(1, f"Resolving: {data['name']}")
        
        resolved_url = get_cached_resolve(hls_link)
        if resolved_url:
            return RedirectResponse(url=resolved_url, status_code=302)
    
    # YÖNTEM 2: Standart Token (Yedek)
    Logger(1, f"Fallback to token: {data['name']}")
    sig = vavoo.getAuthSignature()
    if sig:
        base_url = str(data['url'])
        separator = '&' if '?' in base_url else '?'
        final_link = base_url + separator + 'n=1&b=5&vavoo_auth=' + sig
        return RedirectResponse(url=final_link, status_code=302)
    
    raise HTTPException(status_code=503, detail="Stream unavailable")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    config = Config(app=app, host="0.0.0.0", port=port, log_level="info")
    server = UvicornServer(config=config)
    server.start()
