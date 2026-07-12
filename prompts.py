# -*- coding: utf-8 -*-
"""
简历优化助手 - 核心提示词模块

本模块定义了产品的三大核心提示词：
1. 简历解析 Prompt - 将非结构化简历文本提取为结构化 JSON
2. JD 解析 Prompt - 将非结构化 JD 文本提取为结构化 JSON
3. 差距诊断 Prompt - 对比简历与 JD，生成三维诊断报告
"""

# ============================================================
# Prompt 1: 简历解析
# ============================================================
RESUME_PARSE_PROMPT = """你是一位专业的简历分析师。请将以下简历文本解析为结构化的 JSON 数据。

要求：
1. 仔细阅读简历全文，提取所有关键信息
2. 按照下方 JSON 格式输出，不要输出任何其他内容
3. 如果某个字段在简历中找不到，设为空字符串或空数组
4. 保持原始信息准确，不要编造

输出格式：
```json
{
  "basic_info": {
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "education_level": "最高学历（如：本科、硕士）",
    "years_of_experience": "工作年限（应届生填0）"
  },
  "education": [
    {
      "school": "学校名称",
      "degree": "学位",
      "major": "专业",
      "period": "时间段（如：2022.09-至今）",
      "gpa": "绩点（如有）",
      "courses": "相关课程（如有）"
    }
  ],
  "work_experience": [
    {
      "company": "公司名称",
      "position": "职位",
      "period": "时间段",
      "responsibilities": ["工作职责1", "工作职责2"],
      "achievements": ["成果1", "成果2"]
    }
  ],
  "projects": [
    {
      "name": "项目名称",
      "role": "角色",
      "period": "时间段",
      "description": "项目描述",
      "achievements": ["成果1", "成果2"]
    }
  ],
  "skills": {
    "technical_skills": ["技能1", "技能2"],
    "tools": ["工具1", "工具2"],
    "languages": ["语言1"],
    "certificates": ["证书1"],
    "other": ["其他技能"]
  },
  "self_evaluation": "自我评价原文"
}
```

简历文本：
{resume_text}"""

# ============================================================
# Prompt 2: JD 解析
# ============================================================
JD_PARSE_PROMPT = """你是一位专业的招聘分析师。请将以下岗位描述（JD）解析为结构化的 JSON 数据。

要求：
1. 仔细阅读 JD 全文，提取所有关键信息
2. 按照下方 JSON 格式输出，不要输出任何其他内容
3. 如果某个字段找不到，设为空字符串或空数组
4. 将要求按"必须具备"和"加分项"分类

输出格式：
```json
{
  "job_title": "岗位名称",
  "company": "公司名称（如有）",
  "department": "部门（如有）",
  "job_summary": "岗位概述",
  "requirements": {
    "must_have": [
      {
        "category": "类别（如：学历、经验、技能、证书）",
        "requirement": "具体要求",
        "keyword": "核心关键词"
      }
    ],
    "nice_to_have": [
      {
        "category": "类别",
        "requirement": "具体要求",
        "keyword": "核心关键词"
      }
    ]
  },
  "responsibilities": ["职责1", "职责2"],
  "keywords": ["关键词1", "关键词2"],
  "hard_thresholds": {
    "education": "学历要求",
    "experience_years": "工作年限要求",
    "certificates": ["必要证书"]
  }
}
```

JD 文本：
{jd_text}"""

# ============================================================
# Prompt 3: 差距诊断（核心）
# ============================================================
DIAGNOSIS_PROMPT = """你是一位资深的招聘顾问和简历专家。请对比候选人的简历与目标岗位要求，生成一份详细的差距诊断报告。

## 简历结构化数据：
{resume_json}

## 岗位要求结构化数据：
{jd_json}

## 诊断要求：

请从以下三个维度进行诊断，严格按照指定的 JSON 格式输出。

### 维度一：技能匹配度
- 将 JD 中的每项技能要求与简历内容进行语义匹配（不限于字面匹配）
- 标注：matched（已具备）/ partial（部分具备）/ missing（缺失）
- 对部分具备和缺失的技能，给出具体建议

### 维度二：关键词覆盖度
- 检查简历中是否包含 JD 中的核心关键词
- 这些关键词会影响 ATS（简历筛选系统）的通过率
- 列出命中和缺失的关键词

### 维度三：表达优化建议
- 针对简历的结构、量化程度、逻辑性、专业性给出改进建议
- 每条建议要具体、可执行

## 输出格式：
```json
{
  "overall_match_score": 75,
  "summary": "一句话总结匹配情况",
  "dimensions": {
    "skill_match": {
      "title": "技能匹配度",
      "score": 70,
      "summary": "本维度概述",
      "details": [
        {
          "skill": "技能名称",
          "status": "matched",
          "evidence": "简历中的依据",
          "suggestion": "改进建议（matched的可以为空）"
        }
      ]
    },
    "keyword_coverage": {
      "title": "关键词覆盖度",
      "score": 65,
      "summary": "本维度概述",
      "matched_keywords": ["命中的关键词1", "命中的关键词2"],
      "missing_keywords": ["缺失的关键词1", "缺失的关键词2"],
      "suggestion": "针对缺失关键词的改进建议"
    },
    "expression_quality": {
      "title": "表达优化建议",
      "score": 80,
      "summary": "本维度概述",
      "details": [
        {
          "issue": "问题描述",
          "why_it_matters": "为什么重要",
          "suggestion": "怎么改",
          "example_before": "修改前示例",
          "example_after": "修改后示例"
        }
      ]
    }
  },
  "top_priorities": [
    "最需要优先改进的3-5个点，按重要性排序"
  ]
}
```

注意：
1. overall_match_score 是三个维度得分的加权综合分（技能匹配40%，关键词覆盖30%，表达质量30%）
2. 分数范围 0-100，60以下为高风险，60-75为有差距，75-85为基本匹配，85以上为高度匹配
3. 只输出 JSON，不要输出其他任何文字说明"""
