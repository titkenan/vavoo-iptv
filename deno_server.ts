/// <reference lib="deno.ns" />

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

// Basit cache (15 dakika)
const cache = new Map<string, { url: string; timestamp: number }>();
const CACHE_DURATION = 15 * 60 * 1000; // 15 dakika

// Lokke signature alma
async function getLokkeSignature(): Promise<string | null> {
  const data = {
    token: "",
    reason: "boot",
    locale: "de",
    theme: "dark",
    metadata: {
      device: { type: "desktop", uniqueId: "" },
      os: { name: "linux", version: "Ubuntu", abis: ["x64"], host: "deno-deploy" },
      app: { platform: "electron" },
      version: { package: "app.lokke.main", binary: "1.0.19", js: "1.0.19" }
    },
    appFocusTime: 173,
    playerActive: false,
    playDuration: 0,
    devMode: true,
    hasAddon: true,
    castConnected: false,
    package: "app.lokke.main",
    version: "1.0.19",
    process: "app",
    firstAppStart: Date.now() - 10000,
    lastAppStart: Date.now() - 10000,
    ipLocation: 0,
    adblockEnabled: true,
    proxy: { supported: ["ss"], engine: "cu", enabled: false, autoServer: true, id: 0 },
    iap: { supported: false }
  };

  try {
    const response = await fetch('https://www.lokke.app/api/app/ping', {
      method: 'POST',
      headers: {
        'User-Agent': 'okhttp/4.11.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();
    console.log('✅ Lokke signature obtained');
    return result.addonSig || null;
  } catch (error) {
    console.error('❌ Signature error:', error);
    return null;
  }
}

// Vavoo URL resolve
async function resolveVavooUrl(hls_url: string): Promise<string | null> {
  // Cache kontrol
  const cached = cache.get(hls_url);
  if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
    console.log('💾 Cache hit:', hls_url.substring(0, 50));
    return cached.url;
  }

  const sig = await getLokkeSignature();
  if (!sig) return null;

  const data = {
    language: "de",
    region: "AT",
    url: hls_url,
    clientVersion: "3.0.2"
  };

  try {
    const response = await fetch('https://vavoo.to/mediahubmx-resolve.json', {
      method: 'POST',
      headers: {
        'User-Agent': 'MediaHubMX/2',
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
        'mediahubmx-signature': sig,
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result && result.length > 0 && result[0].url) {
      const resolvedUrl = result[0].url;
      // Cache'e kaydet
      cache.set(hls_url, { url: resolvedUrl, timestamp: Date.now() });
      console.log('✅ Resolved:', hls_url.substring(0, 50));
      return resolvedUrl;
    }
  } catch (error) {
    console.error('❌ Resolve error:', error);
  }

  return null;
}

// Kanal ID'den HLS URL'i al
async function getChannelHlsUrl(channelId: string): Promise<string | null> {
  // GitHub'daki M3U dosyasından kanal bilgisini çek
  try {
    const response = await fetch('https://raw.githubusercontent.com/titkenan/vavoo-iptv/main/vavoo_turkiye.m3u');
    const content = await response.text();
    const lines = content.split('\n');
    
    // Basit parse: channelId ile eşleşen satırı bul
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(`tvg-id="${channelId}"`)) {
        // Bir sonraki http satırını bul
        for (let j = i + 1; j < lines.length; j++) {
          if (lines[j].trim().startsWith('http')) {
            return lines[j].trim();
          }
        }
      }
    }
  } catch (error) {
    console.error('❌ M3U fetch error:', error);
  }
  
  return null;
}

serve(async (req: Request) => {
  const url = new URL(req.url);

  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { headers });
  }

  // Ana sayfa
  if (url.pathname === "/") {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Vavoo IPTV - Deno Deploy</title>
        <style>
          body { font-family: monospace; padding: 20px; background: #1a1a1a; color: #fff; }
          a { color: #4CAF50; text-decoration: none; }
          code { background: #333; padding: 10px; display: block; margin: 10px 0; }
        </style>
      </head>
      <body>
        <h1>🎬 Vavoo IPTV - Deno Deploy</h1>
        <p>✅ Server online!</p>
        <p>💾 Cached resolves: ${cache.size}</p>
        <hr>
        <h2>📋 Endpoints:</h2>
        <ul>
          <li><a href="/playlist.m3u">/playlist.m3u</a> - Dinamik M3U playlist</li>
          <li>/stream/CHANNEL_ID - Stream proxy</li>
        </ul>
        <hr>
        <h2>🔗 Vavoo İçin Link:</h2>
        <code>${url.origin}/playlist.m3u</code>
        <hr>
        <p><small>Powered by Deno Deploy</small></p>
      </body>
      </html>
    `;
    return new Response(html, { 
      headers: { ...headers, "Content-Type": "text/html; charset=utf-8" }
    });
  }

  // M3U Playlist
  if (url.pathname === "/playlist.m3u") {
    try {
      const response = await fetch('https://raw.githubusercontent.com/titkenan/vavoo-iptv/main/vavoo_turkiye.m3u');
      let m3uContent = await response.text();
      
      // GitHub'daki stream URL'lerini Deno endpoint'e çevir
      const baseUrl = url.origin;
      const lines = m3uContent.split('\n');
      const newLines: string[] = [];
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        // EXTINF satırından tvg-id çıkar
        if (line.startsWith('#EXTINF')) {
          const match = line.match(/tvg-id="([^"]+)"/);
          if (match) {
            const tvgId = match[1];
            newLines.push(line);
            
            // Sonraki satırlardaki EXTVLCOPT'ları atla, http'yi bul
            let j = i + 1;
            while (j < lines.length && (lines[j].startsWith('#EXTVLCOPT') || lines[j].trim() === '')) {
              if (lines[j].startsWith('#EXTVLCOPT')) {
                newLines.push(lines[j]);
              }
              j++;
            }
            
            // Stream URL'i Deno endpoint'e çevir
            if (j < lines.length && lines[j].trim().startsWith('http')) {
              newLines.push(`${baseUrl}/stream/${tvgId}`);
              i = j;
            }
          } else {
            newLines.push(line);
          }
        } else if (!line.trim().startsWith('http')) {
          newLines.push(line);
        }
      }
      
      return new Response(newLines.join('\n'), {
        headers: { ...headers, "Content-Type": "audio/x-mpegurl; charset=utf-8" }
      });
    } catch (error) {
      return new Response(`Error: ${error}`, { status: 500, headers });
    }
  }

  // Stream endpoint
  if (url.pathname.startsWith("/stream/")) {
    const channelId = url.pathname.split("/stream/")[1];
    
    console.log(`📡 Stream request: ${channelId}`);
    
    // Kanal HLS URL'ini al
    const hls_url = await getChannelHlsUrl(channelId);
    
    if (!hls_url) {
      return new Response("Channel not found", { status: 404, headers });
    }
    
    console.log(`🔍 HLS URL: ${hls_url.substring(0, 50)}...`);
    
    // Resolve et
    const resolved = await resolveVavooUrl(hls_url);
    
    if (resolved) {
      console.log(`✅ Redirecting to resolved URL`);
      return Response.redirect(resolved, 302);
    }
    
    return new Response("Stream unavailable", { status: 503, headers });
  }

  return new Response("Not found", { status: 404, headers });
});
