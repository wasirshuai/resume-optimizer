# 简历优化助手

> 给求职者的 AI 简历诊断工具——上传简历和目标岗位 JD，精准告诉你差距在哪、怎么改。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
streamlit run app.py
```

### 3. 配置 API

在页面左侧侧边栏中：

1. 选择 API 提供商（推荐 DeepSeek，性价比最高）
2. 输入你的 API Key
3. 上传简历 PDF 或粘贴文字
4. 粘贴目标岗位 JD 文字
5. 点击「开始诊断」

## 项目结构

```
简历优化助手/
├── app.py              # 主应用（Streamlit 界面 + 业务逻辑）
├── prompts.py          # 核心提示词（简历解析 / JD解析 / 差距诊断）
├── requirements.txt    # Python 依赖
├── PRD_简历优化助手.md  # 产品需求文档
└── README.md           # 项目说明
```

## 功能说明

### V2.1 核心功能

- ✅ 上传简历 PDF（支持 OCR 回退）或粘贴文字
- ✅ 粘贴目标岗位 JD，生成四维差距诊断
  - 硬门槛匹配（学历 / 年限 / 证书等一票否决项）
  - 技能匹配度（已具备 / 部分具备 / 缺失）
  - 关键词覆盖度（ATS 关键词命中情况）
  - 表达优化建议（结构 / 量化 / 逻辑）
- ✅ 当前浏览器会话内保存诊断版本，支持同一 JD 下的 V1 → V2 → V3 分数变化对比
- ✅ 选择诊断建议后生成可编辑的简历草稿，并支持再次诊断
- ✅ 改写采用事实约束：不编造原简历未证实的经历、数据、技能、证书或成果

### 支持的 API 提供商

| 提供商 | Base URL | 推荐模型 | 获取 API Key |
|--------|----------|----------|-------------|
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat | https://platform.deepseek.com |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini | https://platform.openai.com |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus | https://dashscope.aliyun.com |
| 智谱 GLM | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash | https://open.bigmodel.cn |

## 隐私说明

- 简历、JD、诊断和改写草稿仅用于当前浏览器会话内的分析、改写和版本对比
- 不写入数据库或本地文件；刷新或关闭页面后会话数据自动清除
- 不保存 API Key，不做用户系统
- 所有 API 调用通过 HTTPS 加密传输

## 技术栈

- **前端**：Streamlit
- **PDF 解析**：pdfplumber
- **LLM 调用**：OpenAI 兼容 API（支持多家提供商）
- **部署**：本地运行 / Streamlit Cloud

---

> V2.1 | 2026-07-15
