#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sketch2UI 后端服务
作用：提供API接口，并直接托管前端网页
"""

import os
import base64
import json
import requests
import re
# 核心修改：引入 send_file 用于发送网页文件
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 配置
MODEL = os.getenv("MODEL_NAME", "ernie-4.5-vl-28b-a3b-thinking")
API_KEY = os.getenv("API_KEY", "") 
BASE_URL = "https://aistudio.baidu.com/llm/lmapi/v3/chat/completions"

SYSTEM_PROMPT = """
你是一名资深 React 工程师。
任务：将 UI 线框图转换为单一 React 组件。
要求：
1. 必须导出一个名为 Page 的默认组件：export default function Page() {...}
2. 使用 Tailwind CSS (通过 className)。
3. 使用 FontAwesome 图标。
4. 图片使用 https://placehold.co/600x400。
5. 不要包含 import React from 'react'。
6. 只输出代码，不要 Markdown 标记。
"""

def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_code(content):
    pattern = r"```(javascript|react|jsx|tsx)?(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(2).strip()
    return content.strip()

def call_baidu_vlm(image_base64, prompt=""):
    if not API_KEY:
        return {"success": False, "error": "未配置 API_KEY"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"请根据图片生成代码。{prompt}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ]
        }
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "stream": False
    }

    try:
        print(f"📡 正在调用模型: {MODEL}...")
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            return {"success": False, "error": f"API调用失败 ({response.status_code}): {response.text}"}

        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return {"success": True, "code": extract_code(content)}
        else:
            return {"success": False, "error": f"API返回格式异常"}

    except Exception as e:
        return {"success": False, "error": f"请求异常: {str(e)}"}

# --- 关键路由修改 ---

@app.route('/')
def index():
    """
    当访问根路径 [http://127.0.0.1:5000/](http://127.0.0.1:5000/) 时，
    不再返回 JSON，而是直接发送 index.html 网页文件。
    """
    try:
        # 确保 index.html 和 app.py 在同一个文件夹下
        return send_file('index.html')
    except Exception as e:
        return f"<h1>启动错误</h1><p>无法找到 index.html 文件。<br>请确保它和 app.py 在同一个文件夹中。</p><p>详情: {e}</p>"

@app.route('/generate-code', methods=['POST'])
def generate_code():
    if 'image' not in request.files:
        return jsonify({"error": "没有上传图片"}), 400
    
    file = request.files['image']
    user_prompt = request.form.get('prompt', '')

    try:
        image = Image.open(file.stream)
        image_base64 = encode_image(image)
        result = call_baidu_vlm(image_base64, user_prompt)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    print("-" * 50)
    print(f"🚀 服务器已启动！")
    print(f"👉 请在浏览器访问: [http://127.0.0.1:5000](http://127.0.0.1:5000)")
    print(f"🔑 当前模型: {MODEL}")
    print("-" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)