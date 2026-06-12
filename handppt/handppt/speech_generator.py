"""
演讲稿生成器
调用 DeepSeek API（兼容 OpenAI SDK）为每页 PPT 生成口语化演讲稿

用法:
    text = generate_speech(["项目背景", "数字媒体技术"], 1, "sk-xxx")
"""

import re
from openai import OpenAI


def generate_speech(texts: list[str], page_num: int, api_key: str,
                    model: str = "deepseek-chat",
                    max_tokens: int = 500,
                    temperature: float = 0.7) -> str | None:
    """
    调用 DeepSeek API 为指定页生成口语化演讲稿

    Args:
        texts: 当前页的所有文字块列表
        page_num: 页码（1-based）
        api_key: DeepSeek API Key
        model: 模型名称
        max_tokens: 最大输出 token 数
        temperature: 创意程度 (0=严谨, 1=创意)

    Returns:
        生成的演讲稿文本，失败返回 None
    """
    if not api_key:
        return "[错误] 未设置 DeepSeek API Key，请在设置面板中填入"

    if not texts:
        return f"（第 {page_num} 页无文字内容，无需演讲稿）"

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        slide_content = "\n".join(texts)

        prompt = f"""你是一位专业的演讲教练。请根据以下PPT幻灯片内容，生成一段自然、口语化的演讲稿（中文）。

当前是第 {page_num} 页。

幻灯片内容：
{slide_content}

要求：
1. 使用第一人称"我"或"我们"
2. 口语化，自然流畅，不要照搬原文
3. 结构：引入话题 → 展开要点 → 过渡
4. 控制在 100-200 字
5. 不要使用"尊敬的"、"大家好"等开场套话，直接进入内容
6. 如果幻灯片是标题页（只有标题），只需简短介绍即可"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=30
        )

        result = response.choices[0].message.content.strip()
        return result

    except Exception as e:
        error_msg = str(e)
        # 隐藏 API Key
        error_msg = re.sub(r'sk-[a-zA-Z0-9]+', 'sk-***', error_msg)
        print(f"[演讲稿] 第 {page_num} 页生成失败: {error_msg}")
        return f"（第 {page_num} 页生成失败: {error_msg[:50]}...）"


def generate_batch(texts_by_page: dict[int, list[str]],
                   api_key: str,
                   model: str = "deepseek-chat",
                   max_tokens: int = 500,
                   temperature: float = 0.7,
                   progress_callback=None) -> dict[int, str]:
    """
    批量生成所有页的演讲稿

    Args:
        texts_by_page: {页码(0-based): [文字块列表]}
        api_key: DeepSeek API Key
        model: 模型名称
        max_tokens: 最大输出 token 数
        temperature: 创意程度
        progress_callback: 回调函数(page_num, total, success_or_fail_msg)

    Returns:
        {页码(0-based): 演讲稿文本}
    """
    speech_notes: dict[int, str] = {}
    total = len(texts_by_page)

    for i, (page_idx, texts) in enumerate(sorted(texts_by_page.items())):
        page_num = page_idx + 1  # 1-based for display

        if progress_callback:
            progress_callback(page_num, total, f"正在生成第 {page_num}/{total} 页...")

        result = generate_speech(
            texts=texts,
            page_num=page_num,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        speech_notes[page_idx] = result or f"（第 {page_num} 页无可用演讲稿）"

        if progress_callback:
            status = "✓" if result and "失败" not in result else "✗"
            progress_callback(page_num, total, f"第 {page_num}/{total} 页 {status}")

    return speech_notes