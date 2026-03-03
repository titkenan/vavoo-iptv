export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Cache-Control': 'public, max-age=60'
    };

    if (!globalThis.cache) {
      globalThis.cache = {
        token: null,
        playlist: null,
        expiresAt: 0
      };
    }

    async function getFromGist() {
      const now = Date.now();
      
      if (globalThis.cache.token && (now - globalThis.cache.expiresAt) < 300000) {
        return globalThis.cache;
      }

      try {
        const tokenResponse = await fetch(
          "https://gist.githubusercontent.com/titkenan/0956315177e258464a1545babe1e8ac9/raw/vavoo_token.txt",
          { cf: { cacheTtl: 300 } }
        );
        
        if (!tokenResponse.ok) throw new Error("Token fetch failed");
        const token = await tokenResponse.text();
        
        const playlistResponse = await fetch(
          "https://gist.githubusercontent.com/titkenan/0956315177e258464a1545babe1e8ac9/raw/vavoo_turkiye.m3u",
          { cf: { cacheTtl: 300 } }
        );
        
        if (!playlistResponse.ok) throw new Error("Playlist fetch failed");
        let playlist = await playlistResponse.text();

        playlist = playlist.replace(
          /https:\/\/vavoo\.to\/vavoo-iptv\/play\//g,
          url.origin + "/play/"
        );

        globalThis.cache = {
          token: token.trim(),
          playlist: playlist,
          expiresAt: now
        };

        return globalThis.cache;
      } catch (error) {
        console.error("Gist error:", error);
        return globalThis.cache;
      }
    }

    if (url.pathname === "/" || url.pathname === "/playlist.m3u" || url.pathname === "/liste") {
      const data = await getFromGist();
      
      if (!data.playlist) {
        return new Response(JSON.stringify({
          error: "Playlist not available"
        }), {
          status: 503,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      return new Response(data.playlist, {
        headers: {
          ...corsHeaders,
          "Content-Type": "application/vnd.apple.mpegurl",
          "Content-Disposition": "inline; filename=\"vavoo_turkiye.m3u\""
        }
      });
    }

    if (url.pathname.startsWith("/play/")) {
      const streamId = url.pathname.split("/")[2];
      
      if (!streamId) {
        return new Response("Stream ID gerekli", { status: 400 });
      }

      const data = await getFromGist();
      
      if (!data.token) {
        return new Response(JSON.stringify({
          error: "Token not available"
        }), {
          status: 503,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      try {
        const vavooUrl = `https://vavoo.to/vavoo-iptv/play/${streamId}`;
        
        const response = await fetch(vavooUrl, {
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
        return new Response(JSON.stringify({
          error: "Stream failed",
          message: error.message
        }), {
          status: 502,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
    }

    if (url.pathname === "/status") {
      const data = await getFromGist();
      return new Response(JSON.stringify({
        status: "ok",
        service: "Vavoo Proxy (Gist Edition)",
        token_valid: !!data.token,
        token_age: data.token ? Math.floor((Date.now() - data.expiresAt) / 1000) + "s" : "none",
        playlist_available: !!data.playlist,
        endpoints: {
          playlist: url.origin + "/playlist.m3u",
          status: url.origin + "/status"
        },
        timestamp: new Date().toISOString()
      }, null, 2), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    return new Response("Not Found", { 
      status: 404,
      headers: corsHeaders
    });
  }
};
