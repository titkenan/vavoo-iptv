// Deno Deploy için basit server
Deno.serve(async (req: Request) => {
  const url = new URL(req.url);

  // CORS
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { headers });
  }

  // Ana sayfa
  if (url.pathname === "/") {
    const html = `<!DOCTYPE html>
<html>
<body style="font-family:monospace;padding:20px;background:#1a1a1a;color:#fff;">
  <h1>🎬 Vavoo IPTV</h1>
  <p>✅ Online</p>
  <hr>
  <h2>Test:</h2>
  <p><a href="/test" style="color:#4CAF50;">/test</a></p>
</body>
</html>`;
    return new Response(html, { 
      headers: { ...headers, 'Content-Type': 'text/html' }
    });
  }

  // Test endpoint
  if (url.pathname === "/test") {
    return new Response("Server works!", { headers });
  }

  return new Response("Not found", { status: 404, headers });
});
