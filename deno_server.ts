import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

// Vavoo signature alma
async function getLokkeSignature() {
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
    return result.addonSig;
  } catch (error) {
    console.error('Signature error:', error);
    return null;
  }
}

// URL resolve
async function resolveVavooUrl(hls_url: string) {
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
    if (result && result.length > 0) {
      return result[0].url;
    }
  } catch (error) {
    console.error('Resolve error:', error);
  }

  return null;
}

serve(async (req) => {
  const url = new URL(req.url);

  // Ana sayfa
  if (url.pathname === "/") {
    return new Response(`
      <html>
      <body style="font-family: monospace; padding: 20px;">
        <h1>🎬 Vavoo IPTV - Deno Deploy</h1>
        <p>✅ Server online</p>
        <hr>
        <h2>Endpoints:</h2>
        <ul>
          <li><a href="/playlist.m3u">/playlist.m3u</a></li>
          <li>/stream/CHANNEL_ID</li>
        </ul>
      </body>
      </html>
    `, {
      headers: { "Content-Type": "text/html" }
    });
  }

  // M3U Playlist
  if (url.pathname === "/playlist.m3u") {
    const m3uUrl = "https://titkenan.github.io/vavoo-iptv/vavoo_turkiye.m3u";
    const response = await fetch(m3uUrl);
    const m3uContent = await response.text();
    
    // GitHub Pages linklerini Deno Deploy linklerine çevir
    const baseUrl = `${url.protocol}//${url.host}`;
    const modified = m3uContent.replace(
      /https:\/\/titkenan\.github\.io\/vavoo-iptv\/stream\//g,
      `${baseUrl}/stream/`
    );

    return new Response(modified, {
      headers: { "Content-Type": "audio/x-mpegurl" }
    });
  }

  // Stream endpoint
  if (url.pathname.startsWith("/stream/")) {
    const channelId = url.pathname.split("/stream/")[1];
    
    // GitHub'dan kanal bilgisini çek (basitleştirilmiş)
    // Gerçekte database'den çekersin
    const hls_url = `https://vavoo.to/play/${channelId}`;
    
    console.log(`Resolving: ${channelId}`);
    const resolved = await resolveVavooUrl(hls_url);
    
    if (resolved) {
      return Response.redirect(resolved, 302);
    }
    
    return new Response("Stream unavailable", { status: 503 });
  }

  return new Response("Not found", { status: 404 });
});
