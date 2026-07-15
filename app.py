# -*- coding: utf-8 -*-
"""
简历优化助手 - MVP 应用
基于 Streamlit 构建的 AI 简历诊断工具

运行方式：streamlit run app.py
"""

import json
import time
import io
import sys
import os
import tempfile

import streamlit as st
import pdfplumber
from openai import OpenAI

from prompts import RESUME_PARSE_PROMPT, JD_PARSE_PROMPT, DIAGNOSIS_PROMPT

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="简历优化助手",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 自定义样式
# ============================================================
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white !important;
        font-size: 2.2rem !important;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
        margin: 0;
    }
    .step-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .step-label {
        font-size: 1.1rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 0.5rem;
    }
    .score-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 1rem;
    }
    .score-number {
        font-size: 3rem;
        font-weight: bold;
        line-height: 1.2;
    }
    .privacy-note {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.85rem;
        color: #856404;
        margin-top: 0.5rem;
    }
    .suggestion-card {
        background: #f0f7ff;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 3px solid #4a90d9;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-weight: bold;
        width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #5a6fd6 0%, #6a3f92 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 工具函数
# ============================================================
def extract_pdf_text(uploaded_file):
    """从上传的 PDF 文件中提取文本，支持 OCR 回退"""
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # 重置文件指针，后续可能还需要读取

    # 第一步：尝试用 pdfplumber 直接提取文本
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            text = text.strip()

            if text and len(text) > 50:
                return text, "pdfplumber"
    except Exception as e:
        pass

    # 第二步：如果 pdfplumber 提取不到文字（图片型 PDF），使用 OCR
    st.info("📄 该 PDF 为图片型，正在使用 OCR 识别文字，请稍候...")

    try:
        import pypdfium2 as pdfium
        from rapidocr_onnxruntime import RapidOCR

        # 将 PDF 渲染为图片
        pdf = pdfium.PdfDocument(io.BytesIO(file_bytes))
        all_text = []

        # 创建临时目录存放图片
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RapidOCR()

            for i in range(len(pdf)):
                page = pdf[i]
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()

                # 保存到临时文件
                img_path = os.path.join(tmpdir, f"page_{i}.png")
                pil_image.save(img_path)

                # OCR 识别
                result, _ = engine(img_path)
                if result:
                    page_text = "\n".join([item[1] for item in result])
                    all_text.append(page_text)

        pdf.close()
        text = "\n".join(all_text).strip()

        if text:
            return text, "ocr"
        else:
            st.error("OCR 识别失败，未能提取到文字。请尝试直接粘贴简历文字。")
            return None, None

    except ImportError:
        st.error("OCR 模块未安装，无法处理图片型 PDF。请尝试直接粘贴简历文字。")
        return None, None
    except Exception as e:
        st.error(f"OCR 处理出错: {e}。请尝试直接粘贴简历文字。")
        return None, None


def call_llm(client, model, prompt, temperature=0.3):
    """调用大模型 API，返回文本响应"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位专业的简历分析师和招聘顾问。请严格按照要求的 JSON 格式输出，不要输出其他内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
        )

        # 检查返回类型是否正确
        if isinstance(response, str):
            st.error(f"API 返回了非预期的字符串，可能是 API 地址或模型名称配置错误。返回内容前200字: {response[:200]}")
            return None

        if not hasattr(response, 'choices') or not response.choices:
            st.error(f"API 返回了非预期的响应格式: {type(response)}")
            return None

        content = response.choices[0].message.content
        if not content:
            st.error("API 返回了空内容")
            return None

        return content

    except Exception as e:
        error_msg = str(e)
        # 提供更友好的错误提示
        if "401" in error_msg or "Unauthorized" in error_msg or "api key" in error_msg.lower():
            st.error("❌ API Key 无效或已过期，请检查侧边栏中的 API Key 是否正确。")
        elif "404" in error_msg or "Not Found" in error_msg or "model" in error_msg.lower():
            st.error(f"❌ 模型名称或 API 地址不正确。当前模型: {model}。请在侧边栏检查配置。")
        elif "Connection" in error_msg or "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            st.error("❌ 网络连接超时，请检查网络或更换 API 提供商。")
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            st.error("❌ API 调用频率超限，请稍后再试。")
        else:
            st.error(f"API 调用失败: {error_msg}")
        return None


def extract_json(text):
    """从 LLM 响应中提取 JSON（处理 markdown 代码块包裹的情况）"""
    if not text:
        return None
    text = text.strip()
    # 去除 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首尾的 ``` 行
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
    return None


def get_score_color(score):
    """根据分数返回颜色"""
    if score >= 85:
        return "#27ae60"  # 绿色 - 高度匹配
    elif score >= 75:
        return "#2ecc71"  # 浅绿 - 基本匹配
    elif score >= 60:
        return "#f39c12"  # 橙色 - 有差距
    else:
        return "#e74c3c"  # 红色 - 高风险


def get_score_label(score):
    """根据分数返回评级标签"""
    if score >= 85:
        return "高度匹配"
    elif score >= 75:
        return "基本匹配"
    elif score >= 60:
        return "有差距"
    else:
        return "高风险"


# ============================================================
# 侧边栏：API 配置
# ============================================================
st.sidebar.markdown("## ⚙️ API 配置")
st.sidebar.markdown("配置大模型 API 以驱动诊断功能")

# 预设 API 地址
api_presets = {
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    },
    "通义千问": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus"
    },
    "智谱 GLM": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash"
    },
    "自定义": {
        "base_url": "",
        "model": ""
    }
}

preset_choice = st.sidebar.selectbox(
    "选择 API 提供商",
    list(api_presets.keys()),
    index=0
)

preset = api_presets[preset_choice]

api_key = st.sidebar.text_input(
    "API Key",
    type="password",
    placeholder="输入你的 API Key"
)

base_url = st.sidebar.text_input(
    "API Base URL",
    value=preset["base_url"],
    placeholder="https://api.example.com/v1"
)

model_name = st.sidebar.text_input(
    "模型名称",
    value=preset["model"],
    placeholder="model-name"
)

st.sidebar.markdown("---")

# API 连接测试
if st.sidebar.button("🔌 测试 API 连接"):
    if not api_key:
        st.sidebar.error("请先填入 API Key")
    elif not base_url or not model_name:
        st.sidebar.error("请填写完整的 API 地址和模型名称")
    else:
        test_placeholder = st.sidebar.empty()
        test_placeholder.info("正在测试连接...")
        try:
            test_client = OpenAI(api_key=api_key, base_url=base_url)
            test_response = test_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "请回复「连接成功」四个字"}
                ],
                max_tokens=20,
                temperature=0,
            )
            test_placeholder.empty()

            if isinstance(test_response, str):
                st.sidebar.error(f"❌ API 返回异常（字符串）: {test_response[:100]}")
            elif hasattr(test_response, 'choices') and test_response.choices:
                reply = test_response.choices[0].message.content
                st.sidebar.success(f"✅ 连接成功！模型回复: {reply}")
            else:
                st.sidebar.error(f"❌ 响应格式异常: {type(test_response)}")
        except Exception as e:
            test_placeholder.empty()
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                st.sidebar.error("❌ API Key 无效，请检查")
            elif "404" in error_msg or "Not Found" in error_msg:
                st.sidebar.error(f"❌ 模型或地址不存在。模型: {model_name}")
            elif "Connection" in error_msg or "timeout" in error_msg.lower():
                st.sidebar.error("❌ 网络连接失败")
            else:
                st.sidebar.error(f"❌ 连接失败: {error_msg[:200]}")

st.sidebar.markdown("""
**使用说明：**
1. 选择 API 提供商并填入 Key
2. 点击「测试 API 连接」验证配置
3. 上传简历 PDF 或粘贴文字
4. 粘贴目标岗位 JD 文字
5. 点击「开始诊断」

**推荐使用 DeepSeek**（性价比最高）
""")

# ============================================================
# 主页面
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>📋 简历优化助手</h1>
    <p>上传简历 + 目标岗位 JD，AI 帮你精准诊断差距在哪、怎么改</p>
</div>
""", unsafe_allow_html=True)

col_intro1, col_intro2, col_intro3 = st.columns(3)
with col_intro1:
    st.markdown("#### 🔍 差距诊断")
    st.markdown("不只是润色表达，而是告诉你和岗位差在哪")
with col_intro2:
    st.markdown("#### 🎯 四维分析")
    st.markdown("硬门槛 + 技能匹配 + 关键词覆盖 + 表达优化")
with col_intro3:
    st.markdown("#### 🔒 隐私保护")
    st.markdown("简历用完即删，不做任何存储")

st.markdown("---")

# ============================================================
# Step 1: 简历输入
# ============================================================
st.markdown("""
<div class="step-container">
    <div class="step-label">Step 1：输入简历</div>
</div>
""", unsafe_allow_html=True)

input_method = st.radio(
    "选择简历输入方式",
    ["上传 PDF 文件", "粘贴简历文字"],
    horizontal=True
)

resume_text = ""

if input_method == "上传 PDF 文件":
    uploaded_file = st.file_uploader(
        "上传简历 PDF",
        type=["pdf"],
        label_visibility="collapsed"
    )
    if uploaded_file is not None:
        resume_text, method = extract_pdf_text(uploaded_file)
        if resume_text:
            method_label = "OCR 识别" if method == "ocr" else "文本提取"
            st.success(f"✅ 简历{method_label}成功（{len(resume_text)} 字符）")
            with st.expander("查看提取的简历文本"):
                st.text(resume_text[:2000] + ("..." if len(resume_text) > 2000 else ""))
else:
    resume_text = st.text_area(
        "粘贴简历文字",
        height=200,
        placeholder="在此粘贴你的简历全文...",
        label_visibility="collapsed"
    )

# ============================================================
# Step 2: JD 输入
# ============================================================
st.markdown("""
<div class="step-container">
    <div class="step-label">Step 2：输入目标岗位 JD</div>
</div>
""", unsafe_allow_html=True)

jd_text = st.text_area(
    "粘贴岗位描述（JD）文字",
    height=200,
    placeholder="在此粘贴目标岗位的 JD 全文...",
    label_visibility="collapsed"
)

st.markdown("""
<div class="privacy-note">
    🔒 隐私说明：你的简历和 JD 仅用于本次诊断分析，不会被存储或用于其他用途。诊断完成后数据即销毁。
</div>
""", unsafe_allow_html=True)

# ============================================================
# Step 3: 诊断
# ============================================================
st.markdown("---")

can_diagnose = bool(resume_text and jd_text and api_key)

if not can_diagnose:
    missing = []
    if not resume_text:
        missing.append("简历")
    if not jd_text:
        missing.append("JD")
    if not api_key:
        missing.append("API Key")
    st.info(f"📋 请补充以下内容后开始诊断：{ '、'.join(missing) }")

if st.button("🚀 开始诊断", disabled=not can_diagnose):
    # 初始化 API 客户端
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        st.error(f"API 客户端初始化失败: {e}")
        st.stop()

    # 进度展示
    progress = st.progress(0)
    status = st.empty()

    # Step A: 解析简历
    status.markdown("📝 正在解析简历...")
    progress.progress(15)

    resume_prompt = RESUME_PARSE_PROMPT.replace("{resume_text}", resume_text)
    resume_result = call_llm(client, model_name, resume_prompt)
    resume_json = extract_json(resume_result)

    if not resume_json:
        st.error("简历解析失败，请检查 API 配置或简历内容")
        st.stop()

    progress.progress(35)

    # Step B: 解析 JD
    status.markdown("📋 正在解析岗位要求...")
    jd_prompt = JD_PARSE_PROMPT.replace("{jd_text}", jd_text)
    jd_result = call_llm(client, model_name, jd_prompt)
    jd_json = extract_json(jd_result)

    if not jd_json:
        st.error("JD 解析失败，请检查 API 配置或 JD 内容")
        st.stop()

    progress.progress(55)

    # Step C: 差距诊断
    status.markdown("🔍 正在生成差距诊断报告...")
    diagnosis_prompt = DIAGNOSIS_PROMPT.replace(
        "{resume_json}", json.dumps(resume_json, ensure_ascii=False, indent=2)
    ).replace(
        "{jd_json}", json.dumps(jd_json, ensure_ascii=False, indent=2)
    )
    diagnosis_result = call_llm(client, model_name, diagnosis_prompt, temperature=0.2)
    diagnosis = extract_json(diagnosis_result)

    if not diagnosis:
        st.error("诊断报告生成失败，请重试")
        st.stop()

    progress.progress(90)
    status.markdown("✅ 诊断完成！")
    progress.progress(100)
    time.sleep(0.3)
    progress.empty()
    status.empty()

    # ============================================================
    # Step 4: 展示诊断报告
    # ============================================================
    st.markdown("---")
    st.markdown("## 📊 诊断报告")

    # 总分卡片
    overall_score = diagnosis.get("overall_match_score", 0)
    score_color = get_score_color(overall_score)
    score_label = get_score_label(overall_score)

    col_score, col_summary = st.columns([1, 2])

    with col_score:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-number" style="color: {score_color};">{overall_score}</div>
            <div style="color: {score_color}; font-size: 1.2rem; font-weight: bold;">{score_label}</div>
            <div style="color: #999; font-size: 0.85rem; margin-top: 0.3rem;">综合匹配度</div>
        </div>
        """, unsafe_allow_html=True)

    with col_summary:
        st.markdown("#### 总体评估")
        st.markdown(f"> {diagnosis.get('summary', '暂无概述')}")

        # 各维度得分
        dims = diagnosis.get("dimensions", {})
        if dims:
            dim_cols = st.columns(len(dims))
            for i, (key, dim) in enumerate(dims.items()):
                dim_score = dim.get("score", 0)
                dim_color = get_score_color(dim_score)
                with dim_cols[i]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.8rem; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: {dim_color};">{dim_score}</div>
                        <div style="font-size: 0.85rem; color: #666;">{dim.get('title', key)}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")

    # 维度零：硬门槛匹配（最先展示，因为是一票否决项）
    hard_threshold = dims.get("hard_threshold", {})
    if hard_threshold:
        st.markdown("### 🚦 硬门槛匹配")
        st.markdown(f"> {hard_threshold.get('summary', '')}")

        # 检查是否有硬门槛不通过
        has_blocking_failure = hard_threshold.get("has_blocking_failure", False)
        blocking_count = hard_threshold.get("blocking_count", 0)

        if has_blocking_failure:
            st.markdown(f"""
            <div style="background: #fff5f5; border: 2px solid #e74c3c; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                <strong style="color: #e74c3c;">⚠️ 硬门槛不通过</strong>
                <br><span style="color: #666; font-size: 0.9rem;">有 {blocking_count} 项硬性要求不满足，可能直接影响简历通过率</span>
            </div>
            """, unsafe_allow_html=True)

        details = hard_threshold.get("details", [])
        if details:
            for d in details:
                status = d.get("candidate_status", "unclear")
                is_blocking = d.get("is_blocking", False)

                if status == "met":
                    icon = "✅"
                    color = "#27ae60"
                    status_text = "满足"
                elif status == "unmet":
                    icon = "❌"
                    color = "#e74c3c"
                    status_text = "不满足"
                else:
                    icon = "❓"
                    color = "#95a5a6"
                    status_text = "无法判断"

                blocking_tag = ' <span style="background:#e74c3c;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;">一票否决</span>' if is_blocking else ''

                st.markdown(f"""
                <div class="suggestion-card" style="border-left-color: {color};">
                    <strong>{icon} {d.get('threshold_name', '')} {blocking_tag}</strong>
                    <span style="float: right; color: {color}; font-weight: bold;">{status_text}</span>
                    <br><span style="color: #666; font-size: 0.9rem;">岗位要求：{d.get('requirement', '未明确')}</span>
                    <br><span style="color: #666; font-size: 0.9rem;">你的情况：{d.get('candidate_detail', '未提及')}</span>
                </div>
                """, unsafe_allow_html=True)

                if d.get("gap"):
                    st.markdown(f"📊 **差距**：{d['gap']}")
                if d.get("suggestion"):
                    st.markdown(f"💡 **建议**：{d['suggestion']}")
                st.markdown("")

    # 维度一：技能匹配度
    skill_match = dims.get("skill_match", {})
    if skill_match:
        st.markdown("### 🛠️ 技能匹配度")
        st.markdown(f"> {skill_match.get('summary', '')}")

        details = skill_match.get("details", [])
        if details:
            # 状态统计
            matched_count = sum(1 for d in details if d.get("status") == "matched")
            partial_count = sum(1 for d in details if d.get("status") == "partial")
            missing_count = sum(1 for d in details if d.get("status") == "missing")

            col_m, col_p, col_x = st.columns(3)
            col_m.metric("✅ 已具备", f"{matched_count} 项")
            col_p.metric("🟡 部分具备", f"{partial_count} 项")
            col_x.metric("❌ 缺失", f"{missing_count} 项")

            st.markdown("")
            for d in details:
                status = d.get("status", "unknown")
                if status == "matched":
                    icon = "✅"
                    color = "#27ae60"
                elif status == "partial":
                    icon = "🟡"
                    color = "#f39c12"
                else:
                    icon = "❌"
                    color = "#e74c3c"

                st.markdown(f"""
                <div class="suggestion-card" style="border-left-color: {color};">
                    <strong>{icon} {d.get('skill', '')}</strong>
                    <br><span style="color: #666; font-size: 0.9rem;">依据：{d.get('evidence', '未找到')}</span>
                </div>
                """, unsafe_allow_html=True)

                if d.get("suggestion"):
                    st.markdown(f"💡 **建议**：{d['suggestion']}")
                st.markdown("")

    # 维度二：关键词覆盖度
    keyword_cov = dims.get("keyword_coverage", {})
    if keyword_cov:
        st.markdown("### 📎 关键词覆盖度")
        st.markdown(f"> {keyword_cov.get('summary', '')}")

        matched_kw = keyword_cov.get("matched_keywords", [])
        missing_kw = keyword_cov.get("missing_keywords", [])

        col_mk, col_ms = st.columns(2)
        with col_mk:
            st.markdown("**✅ 命中关键词**")
            if matched_kw:
                for kw in matched_kw:
                    st.markdown(f"- {kw}")
            else:
                st.markdown("*暂无*")

        with col_ms:
            st.markdown("**❌ 缺失关键词**")
            if missing_kw:
                for kw in missing_kw:
                    st.markdown(f"- {kw}")
            else:
                st.markdown("*无缺失*")

        if keyword_cov.get("suggestion"):
            st.markdown(f"💡 **改进建议**：{keyword_cov['suggestion']}")

        st.markdown("")

    # 维度三：表达优化建议
    expr_quality = dims.get("expression_quality", {})
    if expr_quality:
        st.markdown("### ✍️ 表达优化建议")
        st.markdown(f"> {expr_quality.get('summary', '')}")

        details = expr_quality.get("details", [])
        for i, d in enumerate(details, 1):
            with st.expander(f"{i}. {d.get('issue', '问题')}"):
                st.markdown(f"**为什么重要**：{d.get('why_it_matters', '')}")
                st.markdown(f"**改进建议**：{d.get('suggestion', '')}")
                if d.get("example_before") or d.get("example_after"):
                    col_b, col_a = st.columns(2)
                    with col_b:
                        st.markdown("**修改前**")
                        st.markdown(f"> {d.get('example_before', '—')}")
                    with col_a:
                        st.markdown("**修改后**")
                        st.markdown(f"> {d.get('example_after', '—')}")

    # 优先改进事项
    top_priorities = diagnosis.get("top_priorities", [])
    if top_priorities:
        st.markdown("---")
        st.markdown("### 🎯 优先改进事项")
        st.markdown("以下是最需要优先改进的事项，按重要性排序：")
        for i, p in enumerate(top_priorities, 1):
            st.markdown(f"**{i}.** {p}")

    st.markdown("---")
    st.markdown("💡 *本报告由 AI 生成，仅供参考。建议结合实际情况判断和调整。*")

# ============================================================
# 页脚
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.85rem; padding: 1rem 0;">
    简历优化助手 v2.0 | 基于 AI 的简历差距诊断工具 | 四维诊断：硬门槛 + 技能 + 关键词 + 表达 | 你的简历不会被存储
</div>
""", unsafe_allow_html=True)
