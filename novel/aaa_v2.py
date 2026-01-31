import asyncio
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8900/v1",
    api_key="your-api-key-1"
)

MODEL = "gemini-3-pro-preview"
TOTAL = 1
CONCURRENCY = 5

# ===============================
# ✅统一文件路径：上下文 + 输出都用 aa.txt
# ===============================
TXT_PATH = Path(r"D:\Code\models\aa.txt")

# ===============================
# ✅SYSTEM_PROMPT 读取 aa.txt 全部内容
# ===============================
SYSTEM_PROMPT_origin = TXT_PATH.read_text(encoding="utf-8")
SYSTEM_PROMPT = "续写小说，详细描述做爱过程，比如鸡巴，小穴，乳头,菊花，改纯爱等并增加描述词，逐步推进小说剧情，" + SYSTEM_PROMPT_origin
print(SYSTEM_PROMPT)

# 用户续写指令
USER_PROMPT = "每次生成8000字，并在最后给出下一章节1条20字建议"

# ===============================
# ✅非流式调用（一次性返回）
# ===============================
def one_call(index: int) -> dict:
    print(f"\n========== 开始生成小说 #{index+1} ==========\n")

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        temperature=0.9,
        top_p=1,
        max_tokens=10000,
        stream=False   # ✅关闭流式输出
    )

    # ✅一次性取完整内容
    full_text = resp.choices[0].message.content

    print(full_text)
    print("\n========== 生成完成 ==========\n")

    return {"idx": index + 1, "story": full_text.strip()}

# ===============================
# worker
# ===============================
async def worker(sema: asyncio.Semaphore, index: int, progress: dict) -> dict:
    async with sema:
        try:
            result = await asyncio.to_thread(one_call, index)
            ok = True
        except Exception as e:
            print(f"\n[ERROR] 任务#{index+1} 失败：{e!r}")
            result = {"idx": index + 1, "error": str(e)}
            ok = False

    progress["done"] += 1
    done = progress["done"]
    total = progress["total"]
    succeeded = progress["succeeded"] + (1 if ok else 0)
    progress["succeeded"] = succeeded

    print(
        f"\r进度: {done}/{total}  成功: {succeeded}  失败: {done - succeeded}",
        end="",
        flush=True
    )

    return result

# ===============================
# main
# ===============================
async def main():
    TXT_PATH.parent.mkdir(parents=True, exist_ok=True)

    sema = asyncio.Semaphore(CONCURRENCY)
    progress = {"done": 0, "total": TOTAL, "succeeded": 0}

    tasks = [asyncio.create_task(worker(sema, i, progress)) for i in range(TOTAL)]
    results = await asyncio.gather(*tasks)

    print("\n全部完成，追加写入 aa.txt 中...")

    # ✅追加写入 aa.txt（不覆盖）
    with open(TXT_PATH, "a", encoding="utf-8") as f:
        for item in results:
            if "story" in item:
                f.write(f"\n========== 续写内容 #{item['idx']} ==========\n")
                f.write(item["story"])
                f.write("\n")

    print(f"已追加写入：{TXT_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
