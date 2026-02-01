from typing import List, Dict

def build_generate_messages(
    freecreate_prompt: str,
    context: str,
    user_prompt: str
) -> List[Dict[str, str]]:
    """
    构建自由创作模式下的生成消息列表
    逻辑：freecreate_prompt + context + user_prompt (添加到 system 最后)
    """
    # 构造 system prompt
    system_content = f"{freecreate_prompt}\n\n{context}"

    # 用户输入也添加到 system 最后
    if user_prompt:
        system_content += f"\n\n{user_prompt}"

    messages = [
        {"role": "system", "content": system_content},
        # User 消息保留，作为触发或强调
        {"role": "user", "content": user_prompt if user_prompt else "请继续创作。"}
    ]
    return messages

def build_outline_messages(
    freecreate_prompt: str,
    outline_requirements: str
) -> List[Dict[str, str]]:
    """
    构建自由创作模式下的大纲生成消息列表
    逻辑：采用 freecreate_prompt 创作大纲
    """
    final_system = f"{freecreate_prompt}\n\n{outline_requirements}"

    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": "请根据上述设定开始生成。"}
    ]
    return messages
