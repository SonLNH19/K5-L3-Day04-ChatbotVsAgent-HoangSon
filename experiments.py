"""Chạy hai thí nghiệm cuối README, lưu report riêng, không sửa cấu hình gốc.

    python experiments.py

Có gọi API: 5 câu medium bỏ schema ngày, rồi 5 câu hard với giới hạn 2 vòng.
"""
from pathlib import Path
import os
import sys

import agent
import evaluate


def main() -> None:
    root = Path(__file__).resolve().parent
    original_tools = agent.TOOLS
    original_limit = agent.MAX_ITERATIONS
    original_cwd = Path.cwd()
    original_argv = sys.argv
    scenarios = [
        ("without_date", "medium", [t for t in original_tools if t["name"] != "get_current_date"], original_limit),
        ("limit_2", "hard", original_tools, 2),
    ]
    try:
        for name, level, schemas, limit in scenarios:
            output = root / "experiments" / name
            output.mkdir(parents=True, exist_ok=True)
            agent.TOOLS, agent.MAX_ITERATIONS = schemas, limit
            os.chdir(output)
            sys.argv = ["evaluate.py", "--level", level]
            print(f"\nThí nghiệm: {name} → {output}", flush=True)
            evaluate.main()
    finally:
        agent.TOOLS, agent.MAX_ITERATIONS = original_tools, original_limit
        os.chdir(original_cwd)
        sys.argv = original_argv


if __name__ == "__main__":
    main()
