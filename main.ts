// @deno-types="https://deno.land/std@0.208.0/http/server.ts"
import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

// Cache (15 dakika)
const resolveCache = new Map<string, { url: string; timestamp: number }>();
const CACHE_DURATION = 15 * 60 * 1000;

// Lokke signature al
async function getLokkeSignature(): Promise<string | null> {
  const data = {
    token: "",
    reason: "boot",
    locale: "de",
    theme: "dark",
    metadata: {
      device: { type: "desktop", uniqueId: "" },
      os: { name: "linux", version: "Ubuntu", abis: ["x64"], host: "deno" },
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

    if (!response.ok) {
      console.error(`❌ Signature HTTP ${response.status}`);
      return null;
    }

    const result = await response.json();
    console.log('✅ Lokke signature obtained');
    return result.addonSig || null;
  } catch (error) {
    console.error('❌ Signature error:', error);
    return null;
  }
}

// Vavoo URL'i resolve et
async function resolveVavooUrl(hls_url: string): Promise<string | null> {
  // Cache kontrol
  const cached = resolveCache.get(hls_url);
  if (cached && (Date.now() - cached.timestamp < CACHE_DURATION)) {
    console.log('💾 Cache hit');
    return cached.url;
  }

  const sig = await getLokkeSignature();
  if (!sig) {
    console.error('❌ No signature');
    return null;
  }

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

    if (!response.ok) {
      console.error(`❌ Resolve HTTP ${response.status}`);
      return null;
    }

    const result = await response.json();
    if (result && result.length > 0 && result[0].url) {
      const resolvedUrl = result[0].url;
      resolveCache.set(hls_url, { url: resolvedUrl, timestamp: Date.now() });
      console.log('✅ Resolved successfully');
      return resolvedUrl;
    }
  } catch (error) {
    console.error('❌ Resolve error:', error);
  }

  return null;
}

// M3U'dan kanal bilgisi al
async function getChannelHlsUrl(channelId: string): Promise<string | null> {
  try {
    const response = await fetch('https://raw.githubusercontent.com/titkenan/vavoo-iptv/main/vavoo_turkiye.m3u');
    const content = await response.text();
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(`tvg-id="${channelId}"`)) {
        // Sonraki satırlarda http ile başlayanı bul
        for (let j = i + 1; j < lines.length && j < i + 10; j++) {
          const line = lines[j].trim();
          if (line.startsWith('http')) {
            return line;
          }
          if (line.startsWith('#EXTINF')) break; // Yeni kanal başladı
        }
      }
    }
  } catch (error) {
    console.error('❌ M3U fetch error:', error);
  }
  
  return null;
}

console.log("🚀 Vavoo IPTV Server starting...");

serve(async (req: Request) => {
  const url = new URL(req.url);
  
  console.log(`📥 ${req.method} ${url.pathname}`);

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { headers });
  }

  // Ana sayfa
  if (url.pathname === '/' || url.pathname === '') {
    const html = `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>Vavoo IPTV</title>
  <style>
    body { 
      font-family: 'Courier New', monospace; 
      padding: 40px; 
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff; 
      max-width: 800px;
      margin: 0 auto;
    }
    a { color: #4ade80; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code { 
      background: rgba(0,0,0,0.3); 
      padding: 15px; 
      display: block; 
      margin: 15px 0;
      border-radius: 8px;
      word-break: break-all;
    }
    .badge { 
      background: #22c55e; 
      padding: 5px 10px; 
      border-radius: 5px;
      font-size: 12px;
    }
    .stats { background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>🎬 Vavoo IPTV Server <span class="badge">LIVE</span></h1>
  
  <div class="stats">
    <p>💾 Cached resolves: ${resolveCache.size}</p>
    <p>🕐 Cache duration: 15 minutes</p>
  </div>
  
  <h2>📋 Vavoo Playlist URL:</h2>
  <code>${url.origin}/playlist.m3u</code>
  
  <h2>🧪 Test:</h2>
  <ul>
    <li><a href="/stream/trt.1.tr">/stream/trt.1.tr</a> - TRT 1 test</li>
    <li><a href="/stream/atv.tr">/stream/atv.tr</a> - ATV test</li>
    <li><a href="/health">/health</a> - Health check</li>
  </ul>
  
  <hr style="border: 1px solid rgba(255,255,255,0.2); margin: 30px 0;">
  <p><small>Powered by Deno Deploy 🦕 | Vavoo Resolver v2.0</small></p>
</body>
</html>`;
    
    return new Response(html, {
      headers: { ...headers, 'Content-Type': 'text/html; charset=utf-8' }
    });
  }

  // Health check
  if (url.pathname === '/health') {
    return new Response(JSON.stringify({
      status: 'healthy',
      cache_size: resolveCache.size,
      timestamp: new Date().toISOString()
    }), {
      headers: { ...headers, 'Content-Type': 'application/json' }
    });
  }

  // Playlist
  if (url.pathname === '/playlist.m3u') {
    try {
      const response = await fetch('https://raw.githubusercontent.com/titkenan/vavoo-iptv/main/vavoo_turkiye.m3u');
      const content = await response.text();
      const lines = content.split('\n');
      const output: string[] = [];
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        if (line.startsWith('#EXTINF')) {
          const match = line.match(/tvg-id="([^"]+)"/);
          output.push(line);
          
          // EXTVLCOPT satırlarını ekle
          let j = i + 1;
          while (j < lines.length && (lines[j].startsWith('#EXTVLCOPT') || lines[j].trim() === '')) {
            if (lines[j].startsWith('#EXTVLCOPT')) {
              output.push(lines[j]);
            }
            j++;
          }
          
          // Stream URL'i proxy endpoint'e çevir
          if (match) {
            output.push(`${url.origin}/stream/${match[1]}`);
            i = j;
          }
        } else if (!line.trim().startsWith('http')) {
          output.push(line);
        }
      }
      
      return new Response(output.join('\n'), {
        headers: { ...headers, 'Content-Type': 'audio/x-mpegurl; charset=utf-8' }
      });
    } catch (error) {
      console.error('❌ Playlist error:', error);
      return new Response(`Error: ${error}`, { status: 500, headers });
    }
  }

  // Stream endpoint
  if (url.pathname.startsWith('/stream/')) {
    const channelId = url.pathname.split('/stream/')[1];
    
    console.log(`📡 Stream request: ${channelId}`);
    
    // Kanal HLS URL'ini al
    const hls_url = await getChannelHlsUrl(channelId);
    
    if (!hls_url) {
      console.error(`❌ Channel not found: ${channelId}`);
      return new Response('Channel not found', { status: 404, headers });
    }
    
    console.log(`🔍 HLS: ${hls_url.substring(0, 60)}...`);
    
    // Resolve et
    const resolved = await resolveVavooUrl(hls_url);
    
    if (resolved) {
      console.log(`✅ Redirecting to resolved URL`);
      return 
