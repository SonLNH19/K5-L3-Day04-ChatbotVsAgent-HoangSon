"""ReAct agent viết từ đầu: vòng lặp Thought → Action → Observation (slide 22, 27).

Chạy:
    python agent.py "Ngày mai ở Đà Nẵng nên mặc gì?"
    python agent.py                      # hỏi nhiều câu, gõ exit để thoát
"""
from __future__ import annotations

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, run_tool

load_dotenv()
_router_key = os.getenv("OPENROUTER_API_KEY", "").strip()
PROVIDER = os.getenv(
    "LLM_PROVIDER", "openrouter" if _router_key and not _router_key.endswith("...") else "anthropic"
).strip().lower()
MODEL = os.getenv("MODEL") or (
    "anthropic/claude-haiku-5.5" if PROVIDER == "openrouter" else "claude-opus-5-5"
)
MAX_ITERATIONS = 6          # safeguard: không bao giờ lặp quá số vòng này (slide 30)

# System prompt (slide 28), thêm 1 dòng để model viết "Thought" trước mỗi lần gọi tool
SYSTEM_PROMPT = """You are a Vietnamese travel assistant.

Your job:
- Break the user goal into smaller steps
- Use tools when fresh information is required
- Stop when you have enough evidence to answer

Rules:
- Before each tool call, write ONE short sentence explaining what you need next.
- Never invent tool results.
- For date-dependent questions, resolve 'today' and 'tomorrow' with get_current_date first.
- Retrieve weather with get_weather even if asked to guess. The weather data is simulated
  for this exercise; do not present it as a real forecast.
- For clothing or rain gear, call recommend_outfit using the weather tool's exact values.
  If the user supplies temperature and rain probability, use them directly without looking up weather.
  Convert percentages to probabilities (70% = 0.7); display rain probabilities as percentages.
- Only give clothing/gear advice when requested. Follow the items returned by recommend_outfit;
  do not add extra umbrella/raincoat suggestions "just in case". For this exercise, rain gear
  is needed only when rain_probability > 0.5; at 0.5 or below, say it is not needed if asked.
- For comparisons, fetch every requested city/date before comparing. Request independent
  weather lookups together in one turn to stay within the iteration limit.
- If a tool returns an ERROR, read it, fix the arguments and try once more only if the
  correction is unambiguous. Never substitute a city or invent a replacement date.
  For unsupported cities, say 'không có dữ liệu'; for invalid dates, say 'ngày không hợp lệ'
  and ask for a valid date. Do not invent weather or weather-based outfit recommendations.
- Do not call tools for greetings, thanks, creative writing, or listing supported cities.
- Final answer: short, in Vietnamese.
"""

_client: anthropic.Anthropic | None = None


def call_model(messages: list[dict]):
    """Gọi model 1 lần. Trả về response có .content (danh sách block) và .stop_reason."""
    global _client
    if _client is None:
        if PROVIDER not in {"anthropic", "openrouter"}:
            sys.exit("LLM_PROVIDER phải là anthropic hoặc openrouter.")
        key_name = "OPENROUTER_API_KEY" if PROVIDER == "openrouter" else "ANTHROPIC_API_KEY"
        key = os.getenv(key_name, "").strip()
        if not key or key.endswith("..."):
            sys.exit(f"Chưa có {key_name}. Mở file .env và điền key của bạn (copy từ .env.example nếu chưa có).")
        if PROVIDER == "openrouter":
            _client = anthropic.Anthropic(
                auth_token=key,
                base_url="https://openrouter.ai/api",
                timeout=60.0,
                max_retries=1,
            )
        else:
            _client = anthropic.Anthropic(api_key=key, timeout=60.0, max_retries=1)
    print(f"Đang chờ phản hồi từ {PROVIDER}... (Ctrl+C để dừng)", flush=True)
    return _client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )


def run_agent(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    # TODO 3: viết vòng lặp agent theo pseudocode slide 27.
    #
    #   for step in range(1, MAX_ITERATIONS + 1):
    #       1. response = call_model(messages)
    #       2. Thêm lượt của model vào lịch sử:
    #              messages.append({"role": "assistant", "content": response.content})
    #       3. Lấy text của model: nối b.text của các block có b.type == "text"
    #       4. Nếu response.stop_reason != "tool_use": model đã trả lời xong -> return text
    #       5. Ngược lại, in "Thought {step}: {text}", rồi với MỖI block có b.type == "tool_use":
    #              - in "Action {step}: {b.name}({b.input})"
    #              - result = run_tool(b.name, b.input)
    #              - in "Observation {step}: {result}"
    #              - gom lại: {"type": "tool_result", "tool_use_id": b.id, "content": result}
    #       6. Gửi TẤT CẢ kết quả tool về cho model trong MỘT lượt:
    #              messages.append({"role": "user", "content": <danh sách tool_result>})
    #
    #   Hết vòng for mà chưa return (chạm MAX_ITERATIONS) -> return 1 câu xin lỗi, báo agent đã dừng.
    for step in range(1, MAX_ITERATIONS + 1):
        response = call_model(messages)
        messages.append({"role": "assistant", "content": response.content})
        text = "\n".join(block.text for block in response.content if block.type == "text")
        if response.stop_reason != "tool_use":
            return text

        print(f"Thought {step}: {text}")
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"Action {step}: {block.name}({json.dumps(block.input, ensure_ascii=False)})")
            result = run_tool(block.name, block.input)
            print(f"Observation {step}: {result}")
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
                "is_error": result.startswith("ERROR:"),
            })
        messages.append({"role": "user", "content": results})

    return f"Xin lỗi, agent đã dừng vì đạt giới hạn {MAX_ITERATIONS} vòng lặp. Bạn hãy thu hẹp câu hỏi và thử lại."


def main() -> None:
    try:
        if len(sys.argv) > 1:
            print("Final Answer:", run_agent(" ".join(sys.argv[1:])))
            return
        while (q := input("\nBạn> ").strip()).lower() not in {"exit", "quit", ""}:
            print("Final Answer:", run_agent(q))
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình theo yêu cầu.", file=sys.stderr)
        raise SystemExit(130) from None
    except anthropic.AuthenticationError:
        key_name = "OPENROUTER_API_KEY" if PROVIDER == "openrouter" else "ANTHROPIC_API_KEY"
        sys.exit(f"API key không hợp lệ. Kiểm tra lại {key_name} trong file .env.")
    except anthropic.APIError as e:
        sys.exit(f"Lỗi khi gọi API: {e}")


if __name__ == "__main__":
    main()
