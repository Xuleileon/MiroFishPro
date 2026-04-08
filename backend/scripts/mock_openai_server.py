#!/usr/bin/env python3
"""
Mock OpenAI 兼容服务器
======================
用于本地测试模拟流程，避免消耗真实 LLM Token。

该服务器实现了 OpenAI 的 `/v1/chat/completions` 和 `/v1/embeddings` 接口，
能够根据请求内容智能识别调用阶段并返回对应的模拟数据。

使用方式：
    python scripts/mock_openai_server.py [--port 5099]

    然后在 .env 中设置：
        USE_MOCK_LLM=true
    或者启动后端时：
        USE_MOCK_LLM=true python run.py
"""

import json
import os
import random
import time
import uuid
import argparse
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============== 全局统计 ==============
stats = {
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "by_stage": {}  # stage_name -> {requests, prompt_tokens, completion_tokens}
}


def _update_stats(stage: str, prompt_tokens: int, completion_tokens: int):
    """更新统计信息"""
    stats["total_requests"] += 1
    stats["total_prompt_tokens"] += prompt_tokens
    stats["total_completion_tokens"] += completion_tokens

    if stage not in stats["by_stage"]:
        stats["by_stage"][stage] = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0}
    stats["by_stage"][stage]["requests"] += 1
    stats["by_stage"][stage]["prompt_tokens"] += prompt_tokens
    stats["by_stage"][stage]["completion_tokens"] += completion_tokens


def _estimate_prompt_tokens(messages: list) -> int:
    """粗略估算 prompt tokens（按字符数/4）"""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return max(10, total_chars // 4)


def _detect_stage(messages: list) -> str:
    """
    根据消息内容智能检测当前属于哪个 LLM 调用阶段

    阶段:
      - profile_generation: 人设生成
      - time_config: 时间配置生成
      - event_config: 事件配置生成
      - agent_config: Agent 活动配置生成
      - report_outline: 报告大纲生成
      - report_section: 报告章节生成
      - oasis_simulation: OASIS 模拟中 Agent 行为决策
      - general: 其他
    """
    all_text = " ".join(m.get("content", "") for m in messages).lower()

    # OASIS 模拟行为决策 (camel-ai) - 优先判断，避免被 bio/persona 等背景信息误导
    # 增加更宽泛的模拟指令匹配，涵盖 "perform social media actions" 等常用短句
    sim_keywords = [
        "action_type", "create_post", "like_post", "repost", "do_nothing", 
        "action:", "thought:", "action input:", "perform social media actions",
        "social media environment", "social media actions", "your social media environment"
    ]
    if any(kw in all_text for kw in sim_keywords):
        return "oasis_simulation"


    # 人设生成
    if any(kw in all_text for kw in ["人设", "persona", "社交媒体用户画像", "user_char", "bio"]):
        if "机构" in all_text or "群体" in all_text or "official account" in all_text:
            return "profile_generation_group"
        return "profile_generation_individual"

    # 时间配置
    if any(kw in all_text for kw in ["时间配置", "time_config", "total_simulation_hours", "minutes_per_round"]):
        return "time_config"

    # 事件配置
    if any(kw in all_text for kw in ["事件配置", "hot_topics", "initial_posts", "舆论分析"]):
        return "event_config"

    # Agent 活动配置
    if any(kw in all_text for kw in ["activity_level", "posts_per_hour", "agent活动配置", "agent配置"]):
        return "agent_config"

    # 报告大纲
    if any(kw in all_text for kw in ["报告大纲", "report outline", "目录结构", "章节规划"]):
        return "report_outline"

    # 报告分析：生成章节内容
    if any(kw in all_text for kw in ["生成章节", "section content", "react", "tool_call"]):
        return "report_section"

    # --- 新增：深度检索子问题生成 ---
    if any(kw in all_text for kw in ["分析的子问题", "sub-queries", "检索子问题"]):
        return "sub_query_gen"

    # --- 新增：实体聚类/去重 ---
    if any(kw in all_text for kw in ["实体对齐", "聚类识别", "canonical name"]):
        return "entity_clustering"

    # --- 新增：图谱抽取 ---
    if any(kw in all_text for kw in ["信息抽取器", "entities", "relations", "entity_types"]):
        if "抽取" in all_text or "extraction" in all_text:
            return "graph_extraction"

    # --- 新增：本体设计 ---
    if any(kw in all_text for kw in ["本体设计", "ontology", "图谱主体", "entity_types"]):
        if "设计" in all_text or "schema" in all_text:
            return "ontology_gen"

    # --- 新增：环境摘要 ---
    if any(kw in all_text for kw in ["社交媒体历史动态", "环境摘要", "总结内容"]):
        return "context_summary"

    # --- 新增：动态标签识别 (改造 3) ---
    if any(kw in all_text for kw in ["活跃社交媒体账号", "标签清单", "各数组", "individual", "group"]):
        if "模拟目标" in all_text or "判定" in all_text:
            return "active_type_discovery"

    return "general"



# ============== 模拟数据生成器 ==============

def _mock_profile_individual(messages: list) -> str:
    """生成模拟个人人设"""
    # 尝试从 prompt 中提取实体名
    all_text = " ".join(m.get("content", "") for m in messages)
    name_match = re.search(r"实体名称:\s*(.+?)[\n\r]", all_text)
    entity_name = name_match.group(1).strip() if name_match else "模拟用户"

    type_match = re.search(r"实体类型:\s*(.+?)[\n\r]", all_text)
    entity_type = type_match.group(1).strip() if type_match else "Person"

    mbti = random.choice(["INTJ", "ENFP", "ISTJ", "ENTP", "INFJ", "ESTP", "ISFJ", "ENTJ"])
    gender = random.choice(["male", "female"])
    age = random.randint(20, 55)

    profile = {
        "bio": f"[MOCK] {entity_name} 的社交媒体简介。{entity_type}类型实体，活跃于网络社区。",
        "persona": (
            f"【社交面具】：[MOCK] 基于 {mbti} 性格的{entity_type}专家。\n"
            f"【利益/情感锚点】：致力于在模拟中展示{entity_name}的核心立场，关注社会公平与技术对齐。\n"
            f"【立场律令】：必做：凡是看到争议话题，必须发表中立但深刻的见解；绝不做：绝不参与无端谩骂或人身攻击。\n"
            f"【语言指纹】：爱用“正如...”、常带 Emoji 🧐、喜欢在文末用括号补充内心戏(对吧？)。\n"
            f"【核心记忆】：曾经在{entity_type}领域有10年深耕经验，这是我所有言论的逻辑起点。"
        ),
        "age": age,
        "gender": gender,
        "mbti": mbti,
        "country": "中国",
        "profession": entity_type,
        "interested_topics": ["社会热点", "时事政治", "科技发展", "文化教育"]
    }
    return json.dumps(profile, ensure_ascii=False)


def _mock_profile_group(messages: list) -> str:
    """生成模拟机构/群体人设"""
    all_text = " ".join(m.get("content", "") for m in messages)
    name_match = re.search(r"实体名称:\s*(.+?)[\n\r]", all_text)
    entity_name = name_match.group(1).strip() if name_match else "模拟机构"

    type_match = re.search(r"实体类型:\s*(.+?)[\n\r]", all_text)
    entity_type = type_match.group(1).strip() if type_match else "Organization"

    profile = {
        "bio": f"[MOCK] {entity_name}官方账号。发布权威信息和动态更新。",
        "persona": (
            f"[MOCK] {entity_name} 是一个{entity_type}类型的机构/组织。"
            f"该账号代表机构发声，发布官方声明和政策解读。"
            f"发言风格严谨专业，措辞审慎，注重信息的准确性和权威性。"
            f"在重大事件中起到引导和稳定舆论的作用。"
        ),
        "age": 30,
        "gender": "other",
        "mbti": "ISTJ",
        "country": "中国",
        "profession": entity_type,
        "interested_topics": ["官方政策", "公共事务", "行业动态", "公共服务"]
    }
    return json.dumps(profile, ensure_ascii=False)


def _mock_time_config() -> str:
    """生成模拟时间配置"""
    config = {
        "total_simulation_hours": 48,
        "minutes_per_round": 60,
        "agents_per_hour_min": 3,
        "agents_per_hour_max": 15,
        "peak_hours": [19, 20, 21, 22],
        "off_peak_hours": [0, 1, 2, 3, 4, 5],
        "morning_hours": [6, 7, 8],
        "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "reasoning": "[MOCK] 使用模拟时间配置，48小时模拟周期，每轮1小时"
    }
    return json.dumps(config, ensure_ascii=False)


def _mock_event_config(messages: list) -> str:
    """生成模拟事件配置"""
    config = {
        "hot_topics": ["模拟话题A", "测试事件B", "社会热点C"],
        "narrative_direction": "[MOCK] 舆论从初始关注逐步扩散，经过讨论后趋于理性",
        "initial_posts": [
            {
                "content": "[MOCK] 这是一条模拟初始帖子，用于测试系统流程。大家怎么看这个事件？",
                "poster_type": "Person"
            },
            {
                "content": "[MOCK] 关注此事件的最新进展，持续为大家报道。",
                "poster_type": "MediaOutlet"
            },
            {
                "content": "[MOCK] 针对此事件，我们将认真调查处理。",
                "poster_type": "Organization"
            }
        ],
        "reasoning": "[MOCK] 模拟事件配置，包含3条初始帖子"
    }
    return json.dumps(config, ensure_ascii=False)


def _mock_agent_config(messages: list) -> str:
    """生成模拟 Agent 活动配置"""
    all_text = " ".join(m.get("content", "") for m in messages)

    # 尝试解析有多少个实体需要配置
    agents = []
    # 搜索实体描述
    entity_pattern = re.findall(r"(\d+)\.\s*(.+?)\s*\((\w+)\)", all_text)

    if entity_pattern:
        for idx_str, name, etype in entity_pattern[:20]:
            idx = int(idx_str) - 1
            agents.append({
                "agent_id": idx,
                "entity_name": name.strip(),
                "entity_type": etype.strip(),
                "activity_level": round(random.uniform(0.3, 0.9), 2),
                "posts_per_hour": round(random.uniform(0.5, 3.0), 1),
                "comments_per_hour": round(random.uniform(1.0, 5.0), 1),
                "active_hours": list(range(8, 23)),
                "response_delay_min": random.randint(5, 15),
                "response_delay_max": random.randint(30, 90),
                "sentiment_bias": round(random.uniform(-0.5, 0.5), 2),
                "stance": random.choice(["supportive", "opposing", "neutral", "observer"]),
                "influence_weight": round(random.uniform(0.5, 2.0), 2)
            })

    if not agents:
        # 默认生成5个
        for i in range(5):
            agents.append({
                "agent_id": i,
                "entity_name": f"MockAgent_{i}",
                "entity_type": "Person",
                "activity_level": round(random.uniform(0.3, 0.9), 2),
                "posts_per_hour": round(random.uniform(0.5, 3.0), 1),
                "comments_per_hour": round(random.uniform(1.0, 5.0), 1),
                "active_hours": list(range(8, 23)),
                "response_delay_min": 5,
                "response_delay_max": 60,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            })

    result = {
        "agents": agents,
        "reasoning": f"[MOCK] 为 {len(agents)} 个Agent生成了活动配置"
    }
    return json.dumps(result, ensure_ascii=False)


def _mock_oasis_action(messages: list) -> str:
    """生成 OASIS 模拟中的 Agent 行为决策 (ReAct 格式)"""
    # camel-ai / OASIS 期望的格式通常包含 Thought 和 Action
    all_text = " ".join(m.get("content", "") for m in messages).lower()

    if "reddit" in all_text:
        actions = ["create_post", "create_comment", "like_post", "dislike_post",
                    "search_posts", "do_nothing", "trend", "refresh"]
        # 为 Reddit 随机选择一个动作，避免 NameError
        chosen_action = random.choice(actions)
    else:
        # Twitter/Reddit: CREATE_POST, LIKE_POST, REPOST, FOLLOW, DO_NOTHING
        actions = ["create_post", "like_post", "repost", "do_nothing"]
        # 调试模式：增加发帖概率，以便在前端看到效果
        if random.random() < 0.8:
            chosen_action = "create_post"
        else:
            chosen_action = random.choice(actions)



    thought = f"I want to {chosen_action.lower()} to interact with the social media community and share my perspective."
    
    # 获取当前时间戳用于区分不同帖子
    now_str = datetime.now().strftime('%H:%M:%S')

    import json as py_json
    
    if chosen_action == "create_post":
        content_txt = f"[MOCK] 模拟生成的测试动态。当前时间: {now_str}。这是一个关于当前局势的立场模拟，用于流量验证。"
        action_args = {"content": content_txt}
    elif chosen_action == "create_comment":
        content_txt = "[MOCK] 这是一个很有趣的观点，我也这么认为。"
        action_args = {"post_id": 1, "content": content_txt}
    elif chosen_action == "do_nothing":
        action_args = {}
    elif chosen_action in ["like_post", "dislike_post", "repost", "quote_post"]:
        target_id = random.randint(1, 10)
        action_args = {"post_id": target_id}
        if chosen_action == "quote_post":
            action_args["content"] = "[MOCK] 引用评论：这是一个非常深刻的见解。"
    elif chosen_action in ["search_posts", "trend", "refresh"]:
        action_args = {}
    else:
        chosen_action = "do_nothing"
        action_args = {}
        
    response_text = (
        f"Thought: {thought}\n"
        f"Action: {chosen_action}\n"
        f"Action Input: {py_json.dumps(action_args)}"
    )

    # 兼容 Function Calling 模式
    import uuid
    tool_calls = [{
        "id": f"call_mock_{uuid.uuid4().hex[:8]}",
        "type": "function",
        "function": {
            "name": chosen_action,
            "arguments": py_json.dumps(action_args)
        }
    }]

    return response_text, tool_calls



def _mock_report_outline() -> str:
    """生成模拟报告大纲"""
    outline = {
        "title": "[MOCK] 模拟分析报告",
        "summary": "这是一份由 Mock 服务器生成的模拟报告大纲，用于测试流程。",
        "sections": [
            {
                "title": "事件概述",
                "description": "事件的基本情况和背景介绍",
                "subsections": []
            },
            {
                "title": "舆情分析",
                "description": "各方反应和舆论发展趋势",
                "subsections": [
                    {"title": "主要观点分析", "description": "各类群体的主要观点"},
                    {"title": "情感走向", "description": "舆论情感的变化趋势"}
                ]
            },
            {
                "title": "结论与建议",
                "description": "总结分析和应对建议",
                "subsections": []
            }
        ]
    }
    return json.dumps(outline, ensure_ascii=False)


def _mock_report_section() -> str:
    """生成模拟报告章节内容"""
    return (
        "[MOCK] 这是一段由模拟服务器生成的报告章节内容。\n\n"
        "## 分析要点\n\n"
        "1. 该事件引起了广泛的社会关注和讨论\n"
        "2. 各方利益相关者表达了不同的立场和诉求\n"
        "3. 舆论发展呈现出从初始爆发到逐步平稳的趋势\n\n"
        "## 数据支撑\n\n"
        "根据模拟结果显示，该事件在48小时内产生了大量的讨论和互动。"
    )


def _mock_general() -> str:
    """通用模拟响应"""
    return "[MOCK] 这是 Mock OpenAI 服务器的模拟响应。系统正在测试模式下运行。"


# ============== API 端点 ==============

@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/chat/completions', methods=['POST'])
def chat_completions():

    """兼容 OpenAI Chat Completions API"""
    data = request.get_json() or {}
    messages = data.get("messages", [])
    model = data.get("model", "mock-model")
    response_format = data.get("response_format", {})

    # 检测阶段
    stage = _detect_stage(messages)

    tool_calls = None
    # 根据阶段生成响应
    if stage == "profile_generation_individual":
        content = _mock_profile_individual(messages)
    elif stage == "profile_generation_group":
        content = _mock_profile_group(messages)
    elif stage == "time_config":
        content = _mock_time_config()
    elif stage == "event_config":
        content = _mock_event_config(messages)
    elif stage == "agent_config":
        content = _mock_agent_config(messages)
    elif stage == "report_outline":
        content = _mock_report_outline()
    elif stage == "report_section":
        content = _mock_report_section()
    elif stage == "oasis_simulation":
        content, tool_calls = _mock_oasis_action(messages)
    elif stage == "ontology_gen":
        content = _mock_ontology_gen()
    elif stage == "graph_extraction":
        content = _mock_graph_extraction()
    elif stage == "entity_clustering":
        content = _mock_entity_clustering()
    elif stage == "sub_query_gen":
        content = _mock_sub_query_gen()
    elif stage == "context_summary":
        content = _mock_context_summary()
    elif stage == "active_type_discovery":
        content = _mock_active_type_discovery()
    else:
        content = _mock_general()

    # 计算模拟 token 用量
    prompt_tokens = _estimate_prompt_tokens(messages)
    completion_tokens = max(10, len(content) // 4)
    total_tokens = prompt_tokens + completion_tokens

    # 更新统计
    _update_stats(stage, prompt_tokens, completion_tokens)

    # 打印日志
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color_code = "\033[94m" # Blue for oasis simulation
    if stage != "oasis_simulation":
        color_code = "\033[92m" # Green for others
    
    print(f"{color_code}[{ts}] [MOCK] Stage: {stage} | Req #{stats['total_requests']} | {total_tokens} tokens\033[0m")
    
    # 如果是检测阶段不明或模拟阶段，打印前100个字符辅助调试
    if stage == "oasis_simulation" or stage == "general":
        preview = str(messages[-1].get("content", ""))[:150].replace("\n", " ")
        print(f"       \033[90m预览: {preview}...\033[0m")
        # --- DUMP REQUEST FOR DEBUGGING ---
        if stage == "oasis_simulation":
            import json as py_json
            debug_path = "/tmp/oasis_request.json"
            if not os.path.exists(debug_path):
                with open(debug_path, "w", encoding="utf-8") as f:
                    py_json.dump(request.get_json(), f, ensure_ascii=False, indent=2)

    # 如果是模拟阶段，额外打印具体的动作决策，方便控制台观察
    if stage == "oasis_simulation":
        # 尝试从 content 中提取 Action
        action_match = re.search(r"Action:\s*(.+?)[\n\r]", content)
        act_name = action_match.group(1).strip() if action_match else "UNKNOWN"
        print(f"       \033[93m┕决策: {act_name}\033[0m")



    # 构造 OpenAI 格式的响应
    message_dict = {
        "role": "assistant",
        "content": content
    }
    
    # 只有当请求明确声明了 tools 并且产生了 tool_calls 才会注入 tool_calls
    # 这样就能完美兼容依靠 function calling 解析的 OASIS Agents
    has_tools = "tools" in data and bool(data["tools"])
    if tool_calls and has_tools:
        message_dict["tool_calls"] = tool_calls

    response = {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message_dict,
                "finish_reason": "tool_calls" if (tool_calls and has_tools) else "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }

    return jsonify(response)


@app.route('/v1/embeddings', methods=['POST'])
@app.route('/embeddings', methods=['POST'])
def embeddings():

    """兼容 OpenAI Embeddings API"""
    data = request.get_json() or {}
    input_texts = data.get("input", [])
    model = data.get("model", "mock-embedding")

    if isinstance(input_texts, str):
        input_texts = [input_texts]

    # 生成随机 embedding 向量（维度 1536，与 text-embedding-3-small 一致）
    embeddings_data = []
    for i, text in enumerate(input_texts):
        # 生成伪 embedding：基于文本哈希的确定性随机向量
        random.seed(hash(text) % (2**32))
        vector = [round(random.uniform(-1, 1), 6) for _ in range(2560)]
        random.seed()  # 重置随机种子

        embeddings_data.append({
            "object": "embedding",
            "index": i,
            "embedding": vector
        })

    prompt_tokens = sum(max(1, len(t) // 4) for t in input_texts)
    _update_stats("embedding", prompt_tokens, 0)

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [embedding] {len(input_texts)} 条文本 | {prompt_tokens} tokens")

    return jsonify({
        "object": "list",
        "data": embeddings_data,
        "model": model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "total_tokens": prompt_tokens
        }
    })


@app.route('/v1/models', methods=['GET'])
@app.route('/models', methods=['GET'])
def list_models():

    """列出可用模型（兼容性）"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "mock-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock-server"
            }
        ]
    })


@app.route('/mock/stats', methods=['GET'])
def get_stats():
    """获取统计信息（非 OpenAI 标准接口，用于调试）"""
    return jsonify(stats)


@app.route('/mock/reset', methods=['POST'])
def reset_stats():
    """重置统计"""
    stats["total_requests"] = 0
    stats["total_prompt_tokens"] = 0
    stats["total_completion_tokens"] = 0
    stats["by_stage"] = {}
    return jsonify({"success": True, "message": "统计已重置"})


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "mode": "mock"})


# ============== 启动 ==============


def _mock_ontology_gen() -> str:
    """模拟本体生成 (Ontology)"""
    # 必须正好返回10个实体类型，且包含 Person 和 Organization
    result = {
        "entity_types": [
            {"name": "University", "description": "Academic institutions", "attributes": [{"name": "location", "type": "text", "description": "where it is"}], "examples": ["Tsinghua", "PKU"]},
            {"name": "Student", "description": "Individuals enrolled in school", "attributes": [], "examples": ["Alice", "Bob"]},
            {"name": "Professor", "description": "Academic teaching staff", "attributes": [], "examples": ["Dr. Smith"]},
            {"name": "Company", "description": "Business entities", "attributes": [], "examples": ["Google"]},
            {"name": "NewsOutlet", "description": "Media organizations", "attributes": [], "examples": ["CNN"]},
            {"name": "GovernmentAgency", "description": "Public sector bodies", "attributes": [], "examples": ["MoE"]},
            {"name": "Celebrity", "description": "Famous public figures", "attributes": [], "examples": ["Taylor Swift"]},
            {"name": "NGO", "description": "Non-governmental organizations", "attributes": [], "examples": ["Greenpeace"]},
            {"name": "Person", "description": "Default human type", "attributes": [], "examples": ["User123"]},
            {"name": "Organization", "description": "Default organization type", "attributes": [], "examples": ["Org456"]}
        ],
        "edge_types": [
            {"name": "WORKS_FOR", "description": "Employment relationship", "source_targets": [{"source": "Person", "target": "Organization"}]},
            {"name": "STUDIES_AT", "description": "Enrollment relationship", "source_targets": [{"source": "Student", "target": "University"}]},
            {"name": "COMMENTS_ON", "description": "Social media interaction", "source_targets": [{"source": "Person", "target": "Person"}]}
        ],
        "analysis_summary": "[MOCK] 根据文档分析生成的本体建议。"
    }
    return json.dumps(result, ensure_ascii=False)


def _mock_graph_extraction() -> str:
    """模拟图谱抽取 (Entity/Relation Extraction)"""
    # 抽取随机实体和关系
    result = {
        "entities": [
            {"name": "张三", "type": "Student", "summary": "一名北京大学的学生", "attributes": {"major": "Computer Science"}},
            {"name": "北京大学", "type": "University", "summary": "著名的综合性大学", "attributes": {"location": "北京"}}
        ],
        "relations": [
            {
                "source": "张三", "source_type": "Student",
                "target": "北京大学", "target_type": "University",
                "relation": "STUDIES_AT", "fact": "张三正在北京大学学习。",
                "attributes": {"start_year": "2021"}
            }
        ]
    }
    return json.dumps(result, ensure_ascii=False)


def _mock_entity_clustering() -> str:
    """模拟实体聚类识别"""
    # 返回聚类逻辑，确保满足 LLMClient.chat_json 的期望
    result = {
        "Donald Trump": ["特朗普", "Trump", "唐纳德·特朗普"],
        "Joe Biden": ["拜登", "Biden", "乔·拜登"]
    }
    return json.dumps(result, ensure_ascii=False)


def _mock_sub_query_gen() -> str:
    """模拟深度检索子问题生成"""
    # InsightForge 期望返回子问题列表
    sub_queries = [
        "事件的起因是什么？",
        "目前各方的核心争议点在哪里？",
        "未来的舆论演变趋势如何？"
    ]
    return json.dumps(sub_queries, ensure_ascii=False)


def _mock_context_summary() -> str:
    """模拟环境动态摘要"""
    return "[MOCK] 近期社交媒体动态总结：舆论焦点集中在学术诚信与公平竞争上，各方 Agent 表达了从怀疑到反讽等多种情绪，整体讨论热度持续上升。"


def _mock_active_type_discovery() -> str:
    """模拟动态标签识别 (Transformation 3)"""
    # 返回符合后端 identify_relevant_types 期望的 JSON 格式
    result = {
        "individual": ["student", "professor", "publicfigure", "expert", "official", "journalist", "person"],
        "group": ["university", "organization", "mediaoutlet", "governmentagency", "company"]
    }
    return json.dumps(result, ensure_ascii=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mock OpenAI API Server')
    parser.add_argument('--port', type=int, default=5099, help='监听端口 (默认 5099)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认 0.0.0.0)')
    args = parser.parse_args()

    print("=" * 60)
    print("  Mock OpenAI API Server")
    print("=" * 60)
    print(f"  端口: {args.port}")
    print(f"  地址: http://localhost:{args.port}/v1")
    print()
    print("  支持的端点:")
    print("    POST /v1/chat/completions")
    print("    POST /v1/embeddings")
    print("    GET  /v1/models")
    print("    GET  /mock/stats     (查看统计)")
    print("    POST /mock/reset     (重置统计)")
    print()
    print("  使用方式:")
    print("    .env 中设置 USE_MOCK_LLM=true")
    print("    或: USE_MOCK_LLM=true python run.py")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=False)
