import os
import base64
import re
import gradio as gr
from openai import OpenAI
import datetime

# ================= 1. 配置区 =================
# ⚠️⚠️⚠️ 务必填入你的 Token ⚠️⚠️⚠️
os.environ["AI_STUDIO_API_KEY"] = "[REDACTED_API_KEY]"

client = OpenAI(
    api_key=os.environ.get("AI_STUDIO_API_KEY"),
    base_url="https://aistudio.baidu.com/llm/lmapi/v3"
)

# ================= 2. 核心 Prompt =================
SYSTEM_PROMPT = """
你是一名资深 React 工程师。
任务：将 UI 线框图转换为单一 React 组件。
要求：
1. 必须导出一个名为 Page 的默认组件：export default function Page() {...}
2. 使用 Tailwind CSS (通过 className)。
3. 使用 Lucide React 图标或 FontAwesome。
4. 图片使用 https://placehold.co/600x400。
5. 不要包含 import React from 'react' (环境已预置)。
6. 只输出代码，不要 Markdown 标记。
"""

# ================= 3. 辅助函数 =================

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def clean_code_output(content):
    """清洗代码，移除 markdown 标记"""
    pattern = r"```(?:tsx|jsx|javascript|react)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, content)
    if match:
        content = match.group(1)
    return content.strip()

def code_to_html(react_code):
    """
    Magic Function: 将 React 代码封装为可直接运行的 HTML
    使用了 Babel Standalone 进行浏览器端编译
    """
    # 1. 移除 import 语句 (浏览器环境不需要 import React)
    react_code = re.sub(r"import\s+.*?from\s+['\"].*?['\"];?", "", react_code)
    
    # 2. 确保组件名为 Page 且移除 export default (方便挂载)
    # 将 "export default function X" 替换为 "function Page"
    react_code = re.sub(r"export\s+default\s+function\s+\w+", "function Page", react_code)
    
    # 3. 构造 HTML 模板
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-gray-100 p-4">
        <div id="root"></div>
        
        <script type="text/babel">
            // 你的 React 代码注入在这里
            {react_code}

            // 渲染组件
            const root = ReactDOM.createRoot(document.getElementById('root'));
            try {{
                root.render(<Page />);
            }} catch (e) {{
                document.getElementById('root').innerHTML = '<div class="text-red-500 font-bold">渲染错误: ' + e.message + '</div>';
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

    # -------------------------------------------------------------
    # 🔴 核心修复：在这里初始化 Client 并注入 x-bce-date 头
    # -------------------------------------------------------------
    # 获取当前 UTC 时间，格式为 ISO 8601 (百度要求)
    current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    client = OpenAI(
        api_key=os.environ.get("AI_STUDIO_API_KEY"),
        base_url="https://aistudio.baidu.com/llm/lmapi/v3",
        # 👇 强制注入日期头，解决 404 MissingDateHeader 问题
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
    
    # 1. 保存图片
    temp_path = "temp_sketch.jpg"
    image.save(temp_path)
    
    # 2. 生成代码
    code = sketch_to_code(temp_path, text)
    
    # 3. 转换为预览 HTML
    preview_html = code_to_html(code)
    
    return "✅ 生成成功！向下滚动查看预览", code, preview_html

# ================= 5. Gradio 布局 =================
with gr.Blocks(title="Sketch2UI 实时预览版") as demo:
    gr.Markdown("# 🎨 Sketch2UI: 手绘 -> 代码 -> 实时预览")
    
    with gr.Row():
        # 左侧输入
        with gr.Column(scale=1):
            inp_img = gr.Image(type="pil", label="上传草图 / 截图", height=400)
            inp_txt = gr.Textbox(label="补充需求", placeholder="例如：把按钮变成圆角的，主色调是红色...")
            btn = gr.Button("🚀 生成代码 & 预览", variant="primary")
            status = gr.Textbox(label="状态", interactive=False)
        
        # 右侧输出
        with gr.Column(scale=1):
            # Tab页切换代码和预览
            with gr.Tabs():
                with gr.TabItem("🖥️ 实时预览"):
                    # 这里的 iframe 高度可以自己调
                    out_html = gr.HTML(label="网页预览", min_height=600)
                with gr.TabItem("📝 源代码"):
                    out_code = gr.Code(label="React 代码", language="javascript", interactive=True)
    
    btn.click(run_app, [inp_img, inp_txt], [status, out_code, out_html])

# 启动 (关闭 share 防止网络报错)
print("正在启动服务...")
demo.launch()