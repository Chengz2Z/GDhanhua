#!/usr/bin/env python3
"""
条目更新工具：将文件1的所有条目替换更新到文件2中。

最低支持 Python 版本: 3.7

用法: python update_entries.py <源文件> <目标文件>
示例: python update_entries.py text_zh1.txt text_zh2.txt

支持的文件格式:
  - 纯键值对格式: "key": "value",
  - JS对象格式: b_l10n_texts['zh'] = { ... };
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 7):
    sys.exit("错误: 本脚本需要 Python 3.7 或更高版本，当前版本: {}.{}".format(*sys.version_info[:2]))

import re
import sys
import os
from collections import OrderedDict


def parse_entries(filepath):
    """解析文件中的键值对，返回 OrderedDict {key: value}"""
    entries = OrderedDict()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*"([^"]+)"\s*:\s*"(.*?)"\s*,?\s*$', line)
            if m:
                entries[m.group(1)] = m.group(2)
    return entries


def update_file(src_path, dst_path):
    """将源文件的条目更新到目标文件中"""

    # 1. 解析源文件
    src_entries = parse_entries(src_path)
    if not src_entries:
        print(f"[错误] 源文件 {src_path} 未解析到任何条目")
        return False

    # 2. 读取目标文件
    with open(dst_path, 'r', encoding='utf-8') as f:
        dst_lines = f.readlines()

    # 3. 逐行匹配并更新
    updated = 0
    skipped = 0
    matched_keys = set()

    for i, line in enumerate(dst_lines):
        m = re.match(r'(\s*)"([^"]+)"\s*:\s*"(.*?)"\s*,?\s*$', line)
        if m:
            indent = m.group(1)
            key = m.group(2)
            old_val = m.group(3)

            if key in src_entries:
                matched_keys.add(key)
                new_val = src_entries[key]

                if old_val == new_val:
                    skipped += 1
                    continue

                # 保留原行的缩进和尾部逗号
                dst_lines[i] = f'{indent}"{key}": "{new_val}",\n'
                updated += 1

    # 4. 处理目标文件中不存在的新条目
    new_keys = set(src_entries.keys()) - matched_keys
    added = 0

    if new_keys:
        # 找到文件末尾的 "};"
        closing_idx = None
        for i in range(len(dst_lines) - 1, -1, -1):
            if dst_lines[i].strip().rstrip() in ('};', '}'):
                closing_idx = i
                break

        if closing_idx is not None:
            # 去掉 closing 前一行的尾部逗号
            for i in range(closing_idx - 1, -1, -1):
                stripped = dst_lines[i].strip()
                if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                    if stripped.endswith(','):
                        dst_lines[i] = dst_lines[i].rstrip().rstrip(',') + '\n'
                    break

            # 插入新条目
            insert_lines = [f'    "{k}": "{src_entries[k]}",\n' for k in sorted(new_keys)]
            dst_lines = dst_lines[:closing_idx] + insert_lines + dst_lines[closing_idx:]
            added = len(new_keys)
        else:
            # 纯键值对格式，追加到末尾
            insert_lines = [f'"{k}": "{src_entries[k]}",\n' for k in sorted(new_keys)]
            dst_lines.extend(insert_lines)
            added = len(new_keys)

    # 5. 写回目标文件
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.writelines(dst_lines)

    # 6. 输出统计
    print(f"源文件: {src_path} ({len(src_entries)} 条)")
    print(f"目标文件: {dst_path}")
    print(f"已更新: {updated} 条 (值不同)")
    print(f"已跳过: {skipped} 条 (值相同)")
    print(f"已新增: {added} 条 (目标文件中不存在)")
    print(f"未匹配: {len(src_entries) - len(matched_keys) - added} 条")

    return True


def main():
    if len(sys.argv) != 3:
        print("用法: python update_entries.py <源文件> <目标文件>")
        print("示例: python update_entries.py text_zh1.txt text_zh2.txt")
        sys.exit(1)

    src_path = sys.argv[1]
    dst_path = sys.argv[2]

    if not os.path.isfile(src_path):
        print(f"[错误] 源文件不存在: {src_path}")
        sys.exit(1)
    if not os.path.isfile(dst_path):
        print(f"[错误] 目标文件不存在: {dst_path}")
        sys.exit(1)

    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        print("[错误] 源文件和目标文件不能是同一个文件")
        sys.exit(1)

    success = update_file(src_path, dst_path)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
