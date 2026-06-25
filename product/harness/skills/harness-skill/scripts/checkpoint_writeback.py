#!/usr/bin/env python3
"""
checkpoint_writeback.py — 将 checkpoint hash 写回到 control-state.md 的校验点写回工具。

Usage:
  python3 checkpoint_writeback.py --checkpoint-type observed
  python3 checkpoint_writeback.py --checkpoint-type doc-catch-up
  python3 checkpoint_writeback.py --checkpoint-type observed --control-state .servo/control-state.md

Checkpoint types:
  observed     → latest_observed_checkpoint
  doc-catch-up → last_doc_catch_up_checkpoint

Operations:
  1. 自动获取当前 HEAD hash（git rev-parse HEAD）
  2. 定位 control-state.md 的 ## Baseline Traceability 节
  3. Upsert 对应 key（存在则替换，不存在则追加）
  4. 追加 verified_at: <timestamp> 到 verified_at_history list
  5. 更新 frontmatter 的 updated 时间戳

Output (stdout):
  {"written": true, "checkpoint_type": "observed", "hash": "abc123",
   "previous_hash": "def456", "verified_at": "2026-06-25T12:34:56Z"}

Exit codes: 0 = 成功写入, 1 = 无法定位节或 key
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# ── 尝试复用已有工具函数 ──────────────────────────────────────────────
_GIT_UTILS_AVAILABLE = False
try:
    # 与脚本同目录的 _git_utils.py
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _script_dir)
    from _git_utils import git_rev_parse_head as _git_utils_get_head_hash
    _GIT_UTILS_AVAILABLE = True
except ImportError:
    pass


def get_head_hash():
    """获取当前 HEAD commit hash。优先使用 _git_utils，回退到 subprocess。"""
    if _GIT_UTILS_AVAILABLE:
        try:
            return _git_utils_get_head_hash()
        except Exception:
            pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        msg = f"git rev-parse HEAD failed: {exc}"
        if isinstance(exc, subprocess.CalledProcessError):
            msg = f"git rev-parse HEAD failed: {exc.stderr.strip()}"
        print(json.dumps({"written": False, "error": msg}), file=sys.stderr)
        sys.exit(1)


def read_file(path):
    """读取文件全文，文件不存在则 exit 1。"""
    if not os.path.isfile(path):
        print(
            json.dumps({"written": False, "error": f"file not found: {path}"}),
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_file(path, content):
    """原子写入文件。"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def find_section(lines, heading):
    """在 lines 中定位指定 ## heading 节的起止行号（0-based）。

    Returns (start, end) 其中 start 是 heading 所在行，end 是下一
    ## heading 的行号或 len(lines)。找不到则 raise ValueError。
    """
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            start = i
            break
    else:
        raise ValueError(f"## {heading} section not found")

    # 找下一个 ## 作为节结束边界
    next_heading = re.compile(r"^##\s")
    for i in range(start + 1, len(lines)):
        if next_heading.match(lines[i]):
            return start, i
    return start, len(lines)


def find_key_in_section(lines, section_start, section_end, key):
    """在节内查找 key 行。返回 (line_idx, current_value) 或 (None, None)。

    匹配两种格式（优先 dash 列表项，回退纯缩进）：
      - key: value
        key: value
    """
    # 优先匹配 dash 列表格式
    dash_pat = re.compile(rf"^\s*-\s+{re.escape(key)}:\s*(.*)$")
    for i in range(section_start + 1, section_end):
        m = dash_pat.match(lines[i])
        if m:
            return i, m.group(1).strip()
    # 回退：纯缩进格式
    indent_pat = re.compile(rf"^\s+{re.escape(key)}:\s*(.*)$")
    for i in range(section_start + 1, section_end):
        m = indent_pat.match(lines[i])
        if m:
            return i, m.group(1).strip()
    return None, None


def find_history_list(lines, section_start, section_end):
    """定位 verified_at_history 列表声明行。

    匹配格式：
      - verified_at_history:
        verified_at_history:
    """
    pattern = re.compile(r"^\s*(- )?verified_at_history\s*:")
    for i in range(section_start + 1, section_end):
        if pattern.match(lines[i]):
            return i
    return None


def update_frontmatter_updated(lines, new_timestamp):
    """原地更新 frontmatter 内的 updated: 字段。

    只扫描文件前 40 行（frontmatter 不应超出此范围）。
    保留原有引号风格（如 updated: "..."）。
    Returns True 如果找到并更新了该字段。
    """
    # 匹配 updated: "..." 或 updated: ...（有引号或无引号）
    pattern = re.compile(r"^(updated\s*:\s*)(['\"]?)(.*?)(['\"]?)\s*$")
    scan = min(len(lines), 40)
    for i in range(scan):
        m = pattern.match(lines[i])
        if m:
            prefix = m.group(1)       # "updated: "
            q_open = m.group(2) or ""
            q_close = m.group(4) or q_open
            if q_open:
                lines[i] = f"{prefix}{q_open}{new_timestamp}{q_close}"
            else:
                lines[i] = f"{prefix}{new_timestamp}"
            return True
    return False


def build_entry(key, value):
    """构造 checkpoint 条目行（dash 列表格式，与现有条目风格一致）。"""
    return f"- {key}: {value}"


def build_verified_entry(timestamp):
    """构造 verified_at_history 列表条目（裸时间戳，与现有条目风格一致）。"""
    return f"  - {timestamp}"


# ── checkpoint type → key mapping ─────────────────────────────────────
KEY_MAP = {
    "observed": "latest_observed_checkpoint",
    "doc-catch-up": "last_doc_catch_up_checkpoint",
}


def main():
    parser = argparse.ArgumentParser(
        description="Write checkpoint hash to control-state.md",
    )
    parser.add_argument(
        "--checkpoint-type",
        required=True,
        choices=list(KEY_MAP),
        help="Type of checkpoint to write",
    )
    parser.add_argument(
        "--control-state",
        default=".servo/control-state.md",
        help="Path to control-state.md (default: .servo/control-state.md)",
    )
    args = parser.parse_args()

    key_name = KEY_MAP[args.checkpoint_type]

    # ── 获取 HEAD hash ──────────────────────────────────────────────
    head_hash = get_head_hash()

    # ── 读取 control-state.md ───────────────────────────────────────
    original = read_file(args.control_state)
    lines = original.split("\n")

    # ── 定位 Baseline Traceability 节 ───────────────────────────────
    try:
        sec_start, sec_end = find_section(lines, "Baseline Traceability")
    except ValueError as exc:
        print(
            json.dumps({"written": False, "error": str(exc)}),
            file=sys.stderr,
        )
        sys.exit(1)

    # ── 查找已有 key 值 ─────────────────────────────────────────────
    key_line_idx, previous_hash = find_key_in_section(
        lines, sec_start, sec_end, key_name,
    )

    # ── 生成时间戳 ──────────────────────────────────────────────────
    verified_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Upsert checkpoint key ───────────────────────────────────────
    if key_line_idx is not None:
        # 替换已有行
        lines[key_line_idx] = build_entry(key_name, head_hash)
    else:
        # 插入：放在其他 checkpoint key 之后、verified_at_history 之前
        hist_idx = find_history_list(lines, sec_start, sec_end)
        insert_pos = sec_start + 1

        if hist_idx is not None:
            # 从 verified_at_history 往前扫，找最后一个 checkpoint-style key
            cp_pattern = re.compile(
                r"^\s*-?\s*(latest_observed_checkpoint|last_doc_catch_up_checkpoint):"
            )
            for i in range(hist_idx - 1, sec_start, -1):
                if cp_pattern.match(lines[i]):
                    insert_pos = i + 1
                    break
            else:
                insert_pos = hist_idx  # 没有现有 checkpoint key，插在 history 之前
        else:
            # 无 verified_at_history：放在 section body 末尾附近
            # 找到最后一个非空行作为锚点
            for i in range(sec_end - 1, sec_start, -1):
                if lines[i].strip():
                    insert_pos = i + 1
                    break

        lines.insert(insert_pos, build_entry(key_name, head_hash))
        # 插入后所有后续索引外移 1
        sec_end += 1
        # hist_idx 不用修正，下面会重新定位

    # ── 追加 verified_at history ────────────────────────────────────
    hist_idx = find_history_list(lines, sec_start, sec_end)
    verified_line = build_verified_entry(verified_at)

    if hist_idx is not None:
        # 找到列表已有最后一个 entry 之后插入（格式：  - 2026-...）
        entry_pattern = re.compile(r"^\s*- \d{4}-\d{2}-\d{2}")
        insert_after = hist_idx
        for i in range(hist_idx + 1, sec_end):
            if entry_pattern.match(lines[i]):
                insert_after = i
            else:
                break
        lines.insert(insert_after + 1, verified_line)
    else:
        # 创建新 verified_at_history 块
        lines.insert(sec_end, f"  verified_at_history:")
        lines.insert(sec_end + 1, verified_line)

    # ── 更新 frontmatter updated ────────────────────────────────────
    update_frontmatter_updated(lines, verified_at)

    # ── 写回 ────────────────────────────────────────────────────────
    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"
    write_file(args.control_state, content)

    # ── 输出结果 JSON ───────────────────────────────────────────────
    result = {
        "written": True,
        "checkpoint_type": args.checkpoint_type,
        "hash": head_hash,
        "previous_hash": previous_hash if previous_hash else None,
        "verified_at": verified_at,
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
