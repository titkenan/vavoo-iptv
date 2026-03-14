// worker.js içinde /play endpoint'ini güncelle
if (url.pathname === "/play") {
  const streamUrl = url.searchParams.get("url");
  if (!streamUrl) {
    return new Response("url parametresi gerekli", { status: 400 });
  }
  const data = await getFromGist();
  if (!data.token) {
    return new Response("Token yok", { status: 503 });
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
        "Access-Control-Allow-Origin": "*",
        "Content-Type": contentType,
        "Cache-Control": "no-cache"
      }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 502,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
    });
  }
}
