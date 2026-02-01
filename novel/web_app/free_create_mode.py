from typing import List, Dict

def build_generate_messages(
    freecreate_prompt: str,
    pre_hidden_freecreate_prompt: str,
    post_hidden_freecreate_prompt: str,
    context: str,
    user_prompt: str
) -> List[Dict[str, str]]:
    """
    构建自由创作模式下的生成消息列表
    逻辑：
    1. Pre Prompt (前缀): 仅在 context 为空（第一次生成）时拼入。
    2. Free Prompt: 始终拼入。
    3. Context: 小说内容。
    4. User Prompt: 如果有输入，拼接到 System 中间。
    5. Post Prompt (后缀): 始终拼接到 System 最后。
    """
    parts = []

    # 1. Pre Prompt (仅第一次/无上下文时)
    if not context and pre_hidden_freecreate_prompt:
        parts.append(pre_hidden_freecreate_prompt)

    # 2. Free Prompt
    if freecreate_prompt:
        parts.append(freecreate_prompt)

    # 3. Context
    if context:
        parts.append(context)

    # 4. User Prompt
    if user_prompt:
        parts.append(user_prompt)

    # 5. Post Prompt (后缀，始终放在最后)
    if post_hidden_freecreate_prompt:
        parts.append(post_hidden_freecreate_prompt)

    system_content = "\n\n".join(parts)

    messages = []
    messages.append({"role": "system", "content": system_content})

    if not user_prompt:
        # 用户没输入：User 填入默认 Prompt
        messages.append({"role": "user", "content": "每次生成8000字，并在最后给出下一章节3条20字建议。"})

    return messages

def build_outline_messages(
    freecreate_prompt: str,
    pre_hidden_freecreate_prompt: str,
    post_hidden_freecreate_prompt: str,
    outline_requirements: str
) -> List[Dict[str, str]]:
    """
    构建自由创作模式下的大纲生成消息列表
    """
    parts = []

    # 大纲生成通常视为“第一次”，所以包含前缀
    if pre_hidden_freecreate_prompt:
        parts.append(pre_hidden_freecreate_prompt)

    if freecreate_prompt:
        parts.append(freecreate_prompt)

    if outline_requirements:
        parts.append(outline_requirements)

    if post_hidden_freecreate_prompt:
        parts.append(post_hidden_freecreate_prompt)

    final_system = "\n\n".join(parts)

    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": "请根据上述设定开始生成。"}
    ]
    return messages
