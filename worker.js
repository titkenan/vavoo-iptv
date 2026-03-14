if (url.pathname === "/play" && url.searchParams.has("url")) {
    const streamUrl = url.searchParams.get("url");
    const data = await getFromGist();
    const token = data.token;
    const response = await fetch(streamUrl, {
        headers: { "mediahubmx-signature": token, "User-Agent": "okhttp/4.11.0" }
    });
    return new Response(response.body, {
        headers: { "Content-Type": response.headers.get("content-type") || "video/mp2t" }
    });
}
