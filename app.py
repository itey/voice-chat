import os
import time
import requests
from flask import Flask, render_template, request, jsonify
from zhipuai import ZhipuAI
from dotenv import load_dotenv  # 导入环境变量库

# 1. 加载 .env 文件 (本地运行时读取保险箱)
load_dotenv()

# ================= 安全配置区域 =================
# 👇 现在这里是安全的，因为它们只是在读取环境变量
MY_FISH_API_KEY = os.environ.get("FISH_API_KEY")
MY_MODEL_ID = os.environ.get("FISH_MODEL_ID")
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")

# 检查是否读取成功 (调试用，正式上线可删掉)
if not MY_FISH_API_KEY or not ZHIPU_API_KEY:
    print("⚠️ 警告：未检测到 API Key，请检查 .env 文件或 Render 环境变量设置！")

# 2. 模型版本
GLM_MODEL_CODE = "glm-4.6"

# 3. AI 人设
SYSTEM_PROMPT = "你是一个幽默风趣的语音助手。请用口语化的风格交谈，回复尽量简短（控制在50字以内），不要使用复杂的列表或代码符号。"

# 4. 网络代理 (本地开发开VPN用，上线Render时设为False)
# 技巧：也可以把这个开关放到 .env 里，更加灵活
USE_PROXY = False 
PROXY_URL = "http://127.0.0.1:7890"
# ===============================================

app = Flask(__name__)

client = ZhipuAI(api_key=ZHIPU_API_KEY)

conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

def get_ai_response(user_text):
    try:
        conversation_history.append({"role": "user", "content": user_text})
        
        response = client.chat.completions.create(
            model=GLM_MODEL_CODE,  
            messages=conversation_history,
            stream=False
        )
        
        ai_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_reply})
        return ai_reply
    
    except Exception as e:
        print(f"GLM API Error: {e}")
        return "大脑连接超时，请检查大模型 API Key。"

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_text = data.get('text')
    if not user_text: return jsonify({"error": "No text"}), 400

    ai_text = get_ai_response(user_text)
    audio_filename = generate_audio(ai_text)
    
    return jsonify({
        "reply": ai_text,
        "audio_url": f"/static/{audio_filename}" if audio_filename else None
    })

@app.route('/reset', methods=['POST'])
def reset_chat():
    global conversation_history
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"status": "success"})

if __name__ == '__main__':
    if not os.path.exists('static'): os.makedirs('static')
    # Render 部署时不需要 debug=True
    app.run(host='0.0.0.0', port=5000)
