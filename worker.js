export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Cache-Control': 'public, max-age=60'
    };

    // Global cache (worker hafızasında)
    if (!globalThis.cache) {
      globalThis.cache = { token: null, playlist: null, expiresAt: 0 };
    }

    async function getFromGist() {
      const now = Date.now();
      if (globalThis.cache.token && (now - globalThis.cache.expiresAt) < 300000) {
        return globalThis.cache;
      }
      try {
        const tokenResp = await fetch(
          "https://gist.githubusercontent.com/titkenan/0956315177e258464a1545babe1e8ac9/raw/vavoo_token.txt",
          { cf: { cacheTtl: 300 } }
        );
        if (!tokenResp.ok) throw new Error("Token fetch failed");
        const token = await tokenResp.text();

        const playlistResp = await fetch(
          "https://gist.githubusercontent.com/titkenan/0956315177e258464a1545babe1e8ac9/raw/vavoo_turkiye.m3u",
          { cf: { cacheTtl: 300 } }
        );
        if (!playlistResp.ok) throw new Error("Playlist fetch failed");
        let playlist = await playlistResp.text();

        // Worker üzerinden proxy'lenecek şekilde URL'leri güncelle (gerekirse)
        // playlist = playlist.replace(/https:\/\/vavoo\.to\/[^"]+/g, match => url.origin + "/play?url=" + encodeURIComponent(match));

        globalThis.cache = { token: token.trim(), playlist, expiresAt: now };
        return globalThis.cache;
      } catch (error) {
        console.error("Gist error:", error);
        return globalThis.cache;
      }
    }

    // Playlist endpoint
    if (url.pathname === "/" || url.pathname === "/playlist.m3u" || url.pathname === "/liste") {
      const data = await getFromGist();
      if (!data.playlist) {
        return new Response("Playlist not available", { status: 503, headers: corsHeaders });
      }
      return new Response(data.playlist, {
        headers: {
          ...corsHeaders,
          "Content-Type": "application/vnd.apple.mpegurl",
          "Content-Disposition": "inline; filename=\"vavoo_turkiye.m3u\""
        }
      });
    }

    // Stream proxy endpoint (yeni: ?url= parametresi ile)
    if (url.pathname === "/play") {
      const streamUrl = url.searchParams.get("url");
      if (!streamUrl) {
        return new Response("url parametresi gerekli", { status: 400, headers: corsHeaders });
      }

      const data = await getFromGist();
      if (!data.token) {
        return new Response("Token not available", { status: 503, headers: corsHeaders });
      }

      try {
        const response = await fetch(streamUrl, {
          headers: {
            "User-Agent": "okhttp/4.11.0",
            "Accept": "*/*",
            "mediahubmx-signature": data.token,
            "Referer": "https://vavoo.to/",
            "Origin": "https://vavoo.to"
          },
          redirect: "follow"
        });

        if (!response.ok) {
          throw new Error("Stream error: " + response.status);
        }

        const contentType = response.headers.get("content-type") || "video/mp2t";
        return new Response(response.body, {
          headers: {
            ...corsHeaders,
            "Content-Type": contentType,
            "Cache-Control": "no-cache"
          }
        });

      } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 502,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
    }

    // Status endpoint
    if (url.pathname === "/status") {
      const data = await getFromGist();
      return new Response(JSON.stringify({
        status: "ok",
        token_valid: !!data.token,
        playlist_available: !!data.playlist,
        timestamp: new Date().toISOString()
      }, null, 2), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  }
};
