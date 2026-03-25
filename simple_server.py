#!/usr/bin/env python3
"""
Basit test sunucusu - GitHub Actions bitene kadar
"""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, HTMLResponse

app = FastAPI(title="Vavoo IPTV - Simple Server")

@app.get("/")
def index():
    return HTMLResponse("""
    <html>
    <body style="font-family: monospace; padding: 20px;">
        <h1>🎬 Vavoo IPTV Server</h1>
        <p>✅ Server online!</p>
        <p>⏳ GitHub Actions güncelleme yapıyor...</p>
        <hr>
        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/playlist.m3u">/playlist.m3u</a> - M3U Playlist</li>
            <li><a href="/epg.xml">/epg.xml</a> - EPG Guide</li>
        </ul>
    </body>
    </html>
    """)

@app.get("/playlist.m3u")
def playlist():
    # GitHub Actions'ın oluşturduğu dosyayı servis et
    if os.path.exists("vavoo_turkiye_proxy.m3u"):
        return FileResponse("vavoo_turkiye_proxy.m3u", media_type="audio/x-mpegurl")
    elif os.path.exists("vavoo_turkiye.m3u"):
        return FileResponse("vavoo_turkiye.m3u", media_type="audio/x-mpegurl")
    else:
        return PlainTextResponse("#EXTM3U\n# Waiting for GitHub Actions...\n", media_type="audio/x-mpegurl")

@app.get("/epg.xml")
def epg():
    if os.path.exists("vavoo_epg.xml"):
        return FileResponse("vavoo_epg.xml", media_type="application/xml")
    else:
        return PlainTextResponse('<?xml version="1.0"?>\n<tv></tv>', media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
