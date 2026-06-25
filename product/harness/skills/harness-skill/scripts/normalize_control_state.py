#!/usr/bin/env python3
"""控制态规范化 — 消除 control-state.md 中的重复 key 和 struktur 退化。

将重复出现的 - key: value 列表项归一化为 YAML list，消除 YAML
解析歧义（重复 key 在 YAML 规范中为 undefined behavior）。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/normalize_control_state.py \
    --input .servo/control-state.md \
    --output .servo/control-state.md \
    --dry-run

  # 实际写入:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/normalize_control_state.py \
    --input .servo/control-state.md
"""

import argparse
import re
import sys
from datetime import datetime, timezone, timedelta

# 需要在单 key 下聚合为 YAML list 的重复 key
LISTIFY_KEYS = {
    "latest_closed_worktrack_commit": "closed_worktrack_commits",
    "verified_at": "verified_at_history",
    "last_stop_reason": "stop_reason_history",
}

# 需要去重的单值 key（保留最后出现的值）
DEDUP_SINGLETONS = {
    "worktrack_scope",
    "recommended_next_route",
    "recommended_next_scope",
    "active_milestone_branch",
    "active_milestone_branch_head",
}


def parse_sections(content: str) -> dict[str, list[str]]:
    """将 markdown 按 ## 标题分割为节。返回 {section_name: [lines]}。"""
    sections = {}
    current_section = "_preamble"
    current_lines = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = current_lines
            current_section = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = current_lines

    return sections


def normalize_section(lines: list[str]) -> list[str]:
    """对单个节的各行进行去重和 listify 处理。"""
    result = []

    # 收集重复 key 的值
    listify_collectors: dict[str, list[str]] = {k: [] for k in LISTIFY_KEYS}
    dedup_cache: dict[str, int] = {}  # key → last_line_index (in result)

    for line in lines:
        # 匹配 "- key: value" 或 "- key:"（无值）
        m = re.match(r"^(- )(\S+):\s*(.*)", line)
        if m:
            indent = m.group(1)
            key = m.group(2)
            value = m.group(3).strip()

            if key in LISTIFY_KEYS:
                listify_collectors[key].append(value)
                continue  # 不输出，稍后聚合

            if key in DEDUP_SINGLETONS:
                if key in dedup_cache:
                    # 替换之前的值
                    result[dedup_cache[key]] = f"{indent}{key}: {value}"
                else:
                    idx = len(result)
                    result.append(line)
                    dedup_cache[key] = idx
                continue

        result.append(line)

    # 在节末尾追加聚合后的 list（如果该节有收集到的值）
    for orig_key, values in listify_collectors.items():
        if values:
            new_key = LISTIFY_KEYS[orig_key]
            # 如果有其他行，先加空行
            if result and result[-1] != "":
                result.append("")
            result.append(f"- {new_key}:")
            for v in values:
                result.append(f"  - {v}")

    return result


def recompute_pipeline_summary(sections: dict[str, list[str]]) -> dict[str, list[str]]:
    """可选：重算 milestone_pipeline_summary（需消费 milestone-backlog 数据）。
    当前版本不做自动重算，只标记需要手动检查。"""
    return sections


def write_sections(sections: dict[str, list[str]]) -> str:
    """将各节拼接回 markdown 文本。"""
    result = []

    # 序言（frontmatter + # 标题）
    if "_preamble" in sections:
        preamble = sections.pop("_preamble")
        result.extend(preamble)

    for name, lines in sections.items():
        result.extend(lines)

    return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(description="Norm the control state file")
    parser.add_argument("--input", default=".servo/control-state.md")
    parser.add_argument("--output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.output is None:
        args.output = args.input

    with open(args.input, "r") as f:
        content = f.read()

    sections = parse_sections(content)

    for name, lines in list(sections.items()):
        sections[name] = normalize_section(lines)

    normalized = write_sections(sections)

    # 报告变更
    orig_lines = len(content.split("\n"))
    new_lines = len(normalized.split("\n"))
    print(f"Lines: {orig_lines} → {new_lines} (delta: {new_lines - orig_lines})")

    # 统计去重
    for orig_key in LISTIFY_KEYS:
        pattern = f"- {orig_key}:"
        orig_count = content.count(pattern)
        # 计数结果中的 list 项
        new_key = LISTIFY_KEYS[orig_key]
        new_count = normalized.count(f"  - ")
        print(f"  {orig_key}: {orig_count} occurrences → aggregated as {new_key}")

    if args.dry_run:
        print("\n[Dry run — no file written]")
        print(normalized)
    else:
        with open(args.output, "w") as f:
            f.write(normalized)
        print(f"\nWritten to {args.output}")

        # 更新 updated 时间戳
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        print(f"  (remember to update frontmatter 'updated' to {now})")


if __name__ == "__main__":
    main()
