#!/usr/bin/env python3
"""
条目对比工具：对比两个文件的键值对差异。

最低支持 Python 版本: 3.7

用法: python diff_entries.py [选项] <文件1> <文件2>

选项:
  -info  统计概要模式，仅显示统计摘要
  -all   详细模式，显示所有差异内容（默认）

示例:
  python diff_entries.py Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt
  python diff_entries.py -info Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt
  python diff_entries.py -all Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt

输出内容:
  1. 文件1多的条目（文件2中不存在）
  2. 文件2多的条目（文件1中不存在）
  3. 两个文件都存在但值不同的条目

支持的文件格式:
  - key=value 格式 (如 tags_ui.txt, tags_items.txt)
  - "key": "value", 格式 (JSON风格)
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 7):
    sys.exit("错误: 本脚本需要 Python 3.7 或更高版本，当前版本: {}.{}".format(*sys.version_info[:2]))

import argparse
import re
import os
from collections import OrderedDict


def parse_entries(filepath):
    """解析文件中的键值对，返回 OrderedDict {key: (value, line_number)}

    支持两种格式:
    - key=value 格式 (如 tags_ui.txt)
    - "key": "value", 格式 (JSON风格)
    """
    entries = OrderedDict()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # 跳过空行和注释
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue

            # 尝试 key=value 格式
            m = re.match(r'^([^=\r\n]+)=(.*)$', line.rstrip('\r\n'))
            if m:
                entries[m.group(1).strip()] = (m.group(2), line_num)
                continue

            # 尝试 "key": "value", 格式
            m = re.match(r'\s*"([^"]+)"\s*:\s*"(.*?)"\s*,?\s*$', line)
            if m:
                entries[m.group(1)] = (m.group(2), line_num)
    return entries


def diff_files(file1_path, file2_path, verbose=True):
    """对比两个文件的键值对差异

    Args:
        file1_path: 文件1路径
        file2_path: 文件2路径
        verbose: True=详细模式, False=简略模式

    Returns:
        True if files are identical, False otherwise
    """

    # 1. 解析两个文件
    entries1 = parse_entries(file1_path)
    entries2 = parse_entries(file2_path)

    if not entries1:
        print(f"[警告] 文件1 {file1_path} 未解析到任何条目")
    if not entries2:
        print(f"[警告] 文件2 {file2_path} 未解析到任何条目")

    keys1 = set(entries1.keys())
    keys2 = set(entries2.keys())

    # 2. 计算差异
    only_in_file1 = keys1 - keys2
    only_in_file2 = keys2 - keys1
    common_keys = keys1 & keys2

    # 3. 找出值不同的条目
    diff_entries = []
    for key in sorted(common_keys):
        val1, line1 = entries1[key]
        val2, line2 = entries2[key]
        if val1 != val2:
            diff_entries.append((key, val1, line1, val2, line2))

    # 4. 输出结果
    is_identical = len(only_in_file1) == 0 and len(only_in_file2) == 0 and len(diff_entries) == 0

    if verbose:
        # 详细模式
        print("=" * 60)
        print(f"文件1: {file1_path} ({len(entries1)} 条)")
        print(f"文件2: {file2_path} ({len(entries2)} 条)")
        print("=" * 60)

        # 4.1 文件1多的条目
        print(f"\n[1] 文件1多的条目 (文件2中不存在): {len(only_in_file1)} 条")
        print("-" * 40)
        if only_in_file1:
            for key in sorted(only_in_file1):
                val, line_num = entries1[key]
                print(f"  行 {line_num:>5}: \"{key}\": \"{val}\"")
        else:
            print("  (无)")

        # 4.2 文件2多的条目
        print(f"\n[2] 文件2多的条目 (文件1中不存在): {len(only_in_file2)} 条")
        print("-" * 40)
        if only_in_file2:
            for key in sorted(only_in_file2):
                val, line_num = entries2[key]
                print(f"  行 {line_num:>5}: \"{key}\": \"{val}\"")
        else:
            print("  (无)")

        # 4.3 值不同的条目
        print(f"\n[3] 值不同的条目: {len(diff_entries)} 条")
        print("-" * 40)
        if diff_entries:
            for key, val1, line1, val2, line2 in diff_entries:
                print(f"  \"{key}\"")
                print(f"    文件1 (行 {line1}): \"{val1}\"")
                print(f"    文件2 (行 {line2}): \"{val2}\"")
        else:
            print("  (无)")

        # 5. 统计摘要
        print("\n" + "=" * 60)
        print("统计摘要:")
        print(f"  文件1 独有: {len(only_in_file1)} 条")
        print(f"  文件2 独有: {len(only_in_file2)} 条")
        print(f"  值不同:    {len(diff_entries)} 条")
        print(f"  相同:      {len(common_keys) - len(diff_entries)} 条")
        print("=" * 60)
    else:
        # 简略模式
        print(f"文件1: {file1_path} ({len(entries1)} 条)")
        print(f"文件2: {file2_path} ({len(entries2)} 条)")
        print("-" * 40)
        print(f"文件1 独有: {len(only_in_file1)} 条")
        print(f"文件2 独有: {len(only_in_file2)} 条")
        print(f"值不同:    {len(diff_entries)} 条")
        print(f"相同:      {len(common_keys) - len(diff_entries)} 条")

        if is_identical:
            print("\n[结果] 两个文件完全相同")
        else:
            print(f"\n[结果] 存在 {len(only_in_file1) + len(only_in_file2) + len(diff_entries)} 处差异")

    return is_identical


def main():
    parser = argparse.ArgumentParser(
        description="条目对比工具：对比两个文件的键值对差异",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python diff_entries.py Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt
  python diff_entries.py -info Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt
  python diff_entries.py -all Text_ZH/tags_ui.txt origin/text_zh/tags_ui.txt""",
    )
    parser.add_argument(
        "-info",
        action="store_true",
        help="统计概要模式，仅显示统计摘要",
    )
    parser.add_argument(
        "-all",
        action="store_true",
        help="详细模式，显示所有差异内容（默认）",
    )
    parser.add_argument(
        "file1",
        help="文件1路径",
    )
    parser.add_argument(
        "file2",
        help="文件2路径",
    )

    args = parser.parse_args()

    # 确定输出模式
    verbose = not args.info  # 默认详细，除非指定 -info

    # 验证文件存在
    if not os.path.isfile(args.file1):
        print(f"[错误] 文件1不存在: {args.file1}")
        sys.exit(1)
    if not os.path.isfile(args.file2):
        print(f"[错误] 文件2不存在: {args.file2}")
        sys.exit(1)

    if os.path.abspath(args.file1) == os.path.abspath(args.file2):
        print("[信息] 两个文件完全相同")
        sys.exit(0)

    is_identical = diff_files(args.file1, args.file2, verbose)
    sys.exit(0 if is_identical else 1)


if __name__ == '__main__':
    main()
