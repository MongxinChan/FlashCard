import os
import base64
import re
import gradio as gr
from openai import OpenAI

# ================= 配置区 =================
# ⚠️ 确保你的 Token 填在这里
os.environ["AI_STUDIO_API_KEY"] = "[REDACTED_API_KEY]"

client = OpenAI(
    api_key=os.environ.get("AI_STUDIO_API_KEY"),
    base_url="https://aistudio.baidu.com/llm/lmapi/v3"
)

# ================= 核心 System Prompt (你的神来之笔) =================
SYSTEM_PROMPT = """
你是一名资深 React + Tailwind 工程师，擅长将线框图或网页截图精准还原为可运行的前端代码。

【任务目标】
- 输出一个单一、完整、可直接运行的 React 组件（TSX），使用 Tailwind CSS 类名完成全部样式与布局。
- 组件在浏览器中打开即可预览，要求像素级还原参考图的主要视觉特征。
- 仅使用 CDN 引入 React 与 Tailwind，不依赖任何本地文件。

【识别与结构规范】
- 组件划分需语义清晰 (Navbar, Hero, Section, Grid, Footer)。
- 布局优先使用 Flex 和 Grid。
- 响应式：默认移动优先，md: 断点适配桌面。
- 字体：使用 Google Fonts (Inter)，使用 text-xs/sm/base/lg...。
- 颜色：优先 Tailwind 调色板，支持暗色模式。
- 图片：使用 https://placehold.co 占位，提供合理宽高。
- 图标：使用 Font Awesome (CDN)，如 <i className="fas fa-arrow-right" />。

【代码风格与约束】
- 使用函数式组件 + TypeScript；导出默认组件 export default function Page() {}。
- 禁止省略写法、禁止动态拼接类名。
- 所有交互元素（按钮、链接）必须具象化，不能留空。

【输出格式】
- 仅返回 TSX 代码。
- 不要输出任何说明、解释或 Markdown 标记（如 ```）。
- 代码需包含必要的 CDN 注释在头部。
"""

# ================= 辅助函数 =================

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def clean_code_output(content):
    """
    清洗模型输出：
    虽然 Prompt 要求不输出 markdown 标记，但模型有时很'客气'。
    这个函数用来强制提取代码块，防止渲染错误。
    """
    # 如果包含 markdown 代码块标记，去掉它们
    pattern = r"```(?:tsx|jsx|javascript|react)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return content

def sketch_to_code(image_path, prompt_text):
    print("🤖 正在调用 ERNIE-4.0 进行专业级代码生成...")
    base64_image = encode_image(image_path)
    
    # 组合用户需求
    user_requirement = f"需求描述：{prompt_text}" if prompt_text else "请还原这张设计图。"

    try:
        response = client.chat.completions.create(
            model="ernie-4.5-vl-28b-a3b-thinking", # 建议使用 4.0 以理解复杂指令
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_requirement},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            temperature=0.1, # 低温度保证代码严谨
            max_tokens=3000  # 保证代码不被截断
        )
        raw_content = response.choices[0].message.content
        return clean_code_output(raw_content)
        
    except Exception as e:
        return f"发生错误: {str(e)}"

# ================= 界面启动 =================

def run_app(image, text):
    if not image: return "请上传图片", ""
    temp_path = "temp_sketch.jpg"
    image.save(temp_path)
    
    code = sketch_to_code(temp_path, text)
    return "✅ 生成完毕！请复制下方代码到 CodeSandbox。", code

with gr.Blocks(title="Sketch2UI Pro") as demo:
    gr.Markdown("# 🎨 Sketch2UI: Professional Edition")
    gr.Markdown("上传线框图，生成像素级还原的 React + Tailwind 代码。")
    
    with gr.Row():
        with gr.Column(scale=1):
            inp_img = gr.Image(type="pil", label="设计稿 / 线框图")
            inp_txt = gr.Textbox(label="细节控制 (可选)", placeholder="例：主色调是深蓝色，Hero区域要做成全屏...")
            btn = gr.Button("✨ 生成代码", variant="primary")
        
        with gr.Column(scale=1):
            status = gr.Textbox(label="系统状态", interactive=False)
            out_code = gr.Code(label="React TSX 代码", language="javascript", interactive=True)
    
    btn.click(run_app, [inp_img, inp_txt], [status, out_code])

print("正在启动...")
demo.launch()