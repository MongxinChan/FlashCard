import os
import base64
import re
import datetime  # <--- 修复点：这里补上了缺失的库
import gradio as gr
from openai import OpenAI

# ================= 1. 配置区 =================
# ⚠️⚠️⚠️ 务必填入你的 Token ⚠️⚠️⚠️
os.environ["AI_STUDIO_API_KEY"] = "[REDACTED_API_KEY]"

# ================= 2. 核心 System Prompt =================
SYSTEM_PROMPT = """
你是一名资深 React 工程师。
任务：将 UI 线框图转换为单一 React 组件。
要求：
1. 必须导出一个名为 Page 的默认组件：export default function Page() {...}
2. 使用 Tailwind CSS (通过 className)。
3. 使用 Lucide React 图标或 FontAwesome。
4. 图片使用 https://placehold.co/600x400。
5. 不要包含 import React from 'react'。
6. 只输出代码，不要 Markdown 标记。
"""

# ================= 3. 辅助函数 =================

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def clean_code_output(content):
    pattern = r"```(?:tsx|jsx|javascript|react)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, content)
    if match:
        content = match.group(1)
    return content.strip()

def code_to_html(react_code):
    # 简单的 React 代码转 HTML 预览逻辑
    react_code = re.sub(r"import\s+.*?from\s+['\"].*?['\"];?", "", react_code)
    react_code = re.sub(r"export\s+default\s+function\s+\w+", "function Page", react_code)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-gray-100 p-4">
        <div id="root"></div>
        <script type="text/babel">
            {react_code}
            const root = ReactDOM.createRoot(document.getElementById('root'));
            try {{ root.render(<Page />); }} catch (e) {{
                document.getElementById('root').innerHTML = '<div class="text-red-500">渲染错误: ' + e.message + '</div>';
            }}
        </script>
    </body>
    </html>
    """
    return html_template

def sketch_to_code(image_path, prompt_text):
    print("🤖 AI 正在思考中...")
    base64_image = encode_image(image_path)
    user_requirement = f"需求描述：{prompt_text}" if prompt_text else "请还原这张设计图。"

    # 修复 MissingDateHeader 的核心逻辑
    current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    client = OpenAI(
        api_key=os.environ.get("AI_STUDIO_API_KEY"),
        base_url="https://aistudio.baidu.com/llm/lmapi/v3",
        default_headers={"x-bce-date": current_time}
    )

    try:
        response = client.chat.completions.create(
            model="ernie-4.5-vl-28b-a3b-thinking", # 如果4.0报错，改为 "ernie-bot"
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_requirement},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            temperature=0.1
        )
        raw_content = response.choices[0].message.content
        return clean_code_output(raw_content)
    except Exception as e:
        print(f"Error: {e}")
        return f"// 生成出错: {str(e)}"

# ================= 4. 界面逻辑 =================

def run_app(image, text):
    if not image: return "请上传图片", "", ""
    temp_path = "temp_sketch.jpg"
    image.save(temp_path)
    
    code = sketch_to_code(temp_path, text)
    preview_html = code_to_html(code)
    
    return "✅ 生成成功！", code, preview_html

# ================= 5. 启动 =================
# 移除了 theme 参数以兼容旧版 Gradio
# 移除了 share=True 以解决网络连接报错
with gr.Blocks(title="Sketch2UI Fixed") as demo:
    gr.Markdown("# 🎨 Sketch2UI: 修复版")
    
    with gr.Row():
        with gr.Column(scale=1):
            inp_img = gr.Image(type="pil", label="上传草图", height=400)
            inp_txt = gr.Textbox(label="补充需求")
            btn = gr.Button("🚀 生成", variant="primary")
            status = gr.Textbox(label="状态", interactive=False)
        
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("🖥️ 预览"):
                    out_html = gr.HTML(label="网页预览", min_height=600)
                with gr.TabItem("📝 代码"):
                    out_code = gr.Code(label="React 代码", language="javascript")
    
    btn.click(run_app, [inp_img, inp_txt], [status, out_code, out_html])

demo.launch()