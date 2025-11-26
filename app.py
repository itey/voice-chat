# 👇 找到这个函数，替换整个函数内容
def generate_audio(text):
    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {MY_FISH_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "reference_id": MY_MODEL_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
        "latency": "normal" 
    }
    
    filename = f"speech_{int(time.time())}.mp3"
    filepath = os.path.join("static", filename)

    proxies = None
    if USE_PROXY:
        proxies = {"http": PROXY_URL, "https": PROXY_URL}

    try:
        # ⚠️ 关键优化 1: stream=True (开启流式模式)
        response = requests.post(url, json=data, headers=headers, timeout=60, proxies=proxies, stream=True)
        
        if response.status_code == 200:
            # ⚠️ 关键优化 2: 分块写入，内存占用极低
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return filename
        else:
            print(f"Fish Audio Error: {response.status_code}")
            return None
    except Exception as e:
        print("System Error:", e)
        return None
