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
    """
    parts = []

    # 1. Pre Prompt
    if pre_hidden_freecreate_prompt:
        parts.append(pre_hidden_freecreate_prompt)

    # 2. Free Prompt
    if freecreate_prompt:
        parts.append(freecreate_prompt)

    # 3. Context
    if context:
        parts.append(context)

    # 4. User Prompt (Optional integration into system)
    if user_prompt:
        parts.append(user_prompt)

    # 5. Post Prompt
    if post_hidden_freecreate_prompt:
        parts.append(post_hidden_freecreate_prompt)

    system_content = "\n\n".join(parts)

    messages = []
    messages.append({"role": "system", "content": system_content})

    if not user_prompt:
        messages.append({"role": "user", "content": "每次生成8000字，并在最后给出下一章节3条20字建议。"})

    # 这里的逻辑主要是如果 user_prompt 拼到了 system 中，user role 怎么填？
    # 原代码逻辑：如果 user_prompt 存在，已经拼到 system 里了。这里原代码并没有再加 user role 吗？
    # 回看原代码 line 46: if not user_prompt: messages.append...
    # 也就是说如果 user_prompt 存在，它被拼到了 system 中，而 messages 列表里没有 user message？
    # 这在某些 API 中可能不合法（必须有 user message）。
    # 但原代码逻辑确实如此。为了保持原行为，我们照搬。
    # 实际上，如果 user_prompt 不为空，messages 只有 system role。
    # 这在 OpenAI API 中是允许的（有时），或者原作者意图如此。

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
