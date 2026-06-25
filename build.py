#!/usr/bin/env python3
"""
跨平台构建脚本 — 替代 build.bat + prepare-build.ps1
纯 Python 实现，无需 Wine 或外部依赖。

最低支持 Python 版本: 3.7

用法:
    python build.py              # 默认保留词缀简述
    python build.py with-desc    # 保留词缀简述
    python build.py no-desc      # 去除词缀简述
    python build.py -h / --help  # 显示帮助
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 7):
    sys.exit("错误: 本脚本需要 Python 3.7 或更高版本，当前版本: {}.{}".format(*sys.version_info[:2]))

import argparse
import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "out")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Text_ZH.arc")
SOURCE_DIR = os.path.join(SCRIPT_DIR, "Text_ZH")
STRIPPED_SOURCE_DIR = os.path.join(OUTPUT_DIR, "_build", "Text_ZH")

# 词缀行正则（与 prepare-build.ps1 保持一致）
ENTRY_PATTERN = re.compile(
    r"(?m)^(tag(?:GDX\d+)?(?:Prefix|Suffix)[^=\r\n]*=)(.*)$"
)
VALUE_PATTERN = re.compile(
    r"^(?P<label>.*)\((?P<summary>[^()\r\n]*)\)(?P<tail>\s*\u00B7?\s*)$"
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

ARC_TOOL = os.path.join(SCRIPT_DIR, "arc_tool.py")


def run_archive_tool(args: list[str]) -> None:
    """调用 arc_tool.py（纯 Python 实现，跨平台）"""
    cmd = [sys.executable, ARC_TOOL] + args
    print(f"[INFO] 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[ERROR] arc_tool 执行失败，请检查上方输出。")
        sys.exit(1)


def strip_affix_notes(target_dir: str) -> None:
    """去除 tagPrefix/tagSuffix 条目末尾括号中的属性简述。"""
    changed_files = 0
    changed_lines = 0

    for root, _dirs, files in os.walk(target_dir):
        for fname in files:
            if not fnmatch(fname, "tags*items.txt"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            def _replace(m: re.Match) -> str:
                nonlocal changed_lines
                prefix = m.group(1)
                value = m.group(2)
                vm = VALUE_PATTERN.match(value)
                if not vm:
                    return m.group(0)
                changed_lines += 1
                return prefix + vm.group("label") + vm.group("tail")

            updated = ENTRY_PATTERN.sub(_replace, content)
            if updated != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(updated)
                changed_files += 1

    print(f"[INFO] 词缀简述处理完成: {changed_files} 个文件, {changed_lines} 行已去除。")


def fnmatch(name: str, pattern: str) -> bool:
    """简易 fnmatch 实现（仅支持 * 通配符）。"""
    regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
    return re.match(regex, name) is not None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GD 汉化补丁跨平台构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "with_desc",
        nargs="?",
        choices=["with-desc"],
        help="保留词缀属性简述（默认）",
    )
    group.add_argument(
        "no_desc",
        nargs="?",
        choices=["no-desc"],
        help="去除词缀属性简述",
    )
    args = parser.parse_args()

    # 确定是否去除简述
    enable_desc = True
    if args.no_desc == "no-desc":
        enable_desc = False
    # 如果没有传参数，保持默认 True

    # 1. 创建输出目录
    if not os.path.isdir(OUTPUT_DIR):
        print(f"[INFO] 输出目录不存在，正在创建: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 2. 删除旧输出文件
    if os.path.exists(OUTPUT_FILE):
        print(f"[INFO] 删除旧输出文件: {OUTPUT_FILE}")
        os.remove(OUTPUT_FILE)

    # 3. 确定构建源目录
    source_dir = SOURCE_DIR
    if not enable_desc:
        source_dir = STRIPPED_SOURCE_DIR
        print("[INFO] 正在准备去除词缀简述的构建源...")

        # 清理旧的临时目录
        build_tmp = os.path.join(OUTPUT_DIR, "_build")
        if os.path.isdir(build_tmp):
            shutil.rmtree(build_tmp)

        # 复制 Text_ZH 到临时目录
        shutil.copytree(SOURCE_DIR, STRIPPED_SOURCE_DIR)

        # 去除词缀简述
        strip_affix_notes(STRIPPED_SOURCE_DIR)

    # 4. 检查 arc_tool.py
    if not os.path.isfile(ARC_TOOL):
        print(f"[ERROR] 未找到 arc_tool.py: {ARC_TOOL}")
        sys.exit(1)

    # 5. 调用 arc_tool.py 打包
    print("[INFO] 开始打包...")
    run_archive_tool(["pack", OUTPUT_FILE, source_dir, "--level", "6"])

    print(f'[INFO] ENABLE_DESC="{1 if enable_desc else 0}"')
    print(f"[SUCCESS] 构建完成。输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
