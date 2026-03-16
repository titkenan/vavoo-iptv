@app.get("/test-endpoints")
def test_endpoints():
    """Farklı endpoint'leri test et"""
    results = {}
    
    sig = get_lokke_sig()
    
    # Test 1: Eski resolve
    try:
        r = requests.post("https://vavoo.to/mediahubmx-resolve.json",
                         data=json.dumps({"language":"de","region":"AT","url":"https://vavoo.to/play/trt1","clientVersion":"3.0.2"}),
                         headers={"user-agent":"MediaHubMX/2","accept":"application/json","content-type":"application/json; charset=utf-8","mediahubmx-signature":sig or ""},
                         timeout=10)
        results["resolve_vavoo_to"] = {"status": r.status_code, "response": r.text[:100]}
    except Exception as e:
        results["resolve_vavoo_to"] = {"error": str(e)}
    
    # Test 2: www.vavoo.to
    try:
        r = requests.post("https://www.vavoo.to/mediahubmx-resolve.json",
                         data=json.dumps({"language":"de","region":"AT","url":"https://www.vavoo.to/play/trt1","clientVersion":"3.0.2"}),
                         headers={"user-agent":"MediaHubMX/2","accept":"application/json","content-type":"application/json; charset=utf-8","mediahubmx-signature":sig or ""},
                         timeout=10)
        results["resolve_www_vavoo_to"] = {"status": r.status_code, "response": r.text[:100]}
    except Exception as e:
        results["resolve_www_vavoo_to"] = {"error": str(e)}
    
    # Test 3: vavoo.tv
    try:
        r = requests.post("https://vavoo.tv/mediahubmx-resolve.json",
                         data=json.dumps({"language":"de","region":"AT","url":"https://vavoo.tv/play/trt1","clientVersion":"3.0.2"}),
                         headers={"user-agent":"MediaHubMX/2","accept":"application/json","content-type":"application/json; charset=utf-8","mediahubmx-signature":sig or ""},
                         timeout=10)
        results["resolve_vavoo_tv"] = {"status": r.status_code, "response": r.text[:100]}
    except Exception as e:
        results["resolve_vavoo_tv"] = {"error": str(e)}
    
    # Test 4: Direkt play URL formatları
    formats = [
        "https://vavoo.to/play/trt1",
        "https://vavoo.to/play3/trt1",
        "https://vavoo.to/stream/trt1",
        "https://vavoo.to/live/trt1",
    ]
    
    for fmt in formats:
        try:
            r = requests.head(fmt, headers={"User-Agent":"VAVOO/2.6"}, timeout=5, allow_redirects=True)
            results[f"head_{fmt.split('/')[-2]}"] = {"status": r.status_code, "final_url": str(r.url)[:80]}
        except Exception as e:
            results[f"head_{fmt.split('/')[-2]}"] = {"error": str(e)}
    
    return JSONResponse(results)
