#!/usr/bin/env python3
"""
跨平台构建脚本 — 替代 build.bat + prepare-build.ps1
纯 Python 实现，无需 Wine 或外部依赖。

最低支持 Python 版本: 3.7

用法:
    python build.py              # 默认: release 模式，打包所有版本
    python build.py release      # release 模式，打包所有版本
    python build.py with-desc    # 仅保留词缀简述打包
    python build.py no-desc      # 仅去除词缀简述打包
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
# 单次构建
# ---------------------------------------------------------------------------

def build_single(enable_desc: bool) -> None:
    """执行单次构建。"""
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


# ---------------------------------------------------------------------------
# Release 构建
# ---------------------------------------------------------------------------

def build_release() -> None:
    """执行 release 构建：打包所有版本文件和源文件用于发布。"""
    print("[INFO] 开始 release 构建...")

    # 1. 创建输出目录
    if not os.path.isdir(OUTPUT_DIR):
        print(f"[INFO] 输出目录不存在，正在创建: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 2. 检查 arc_tool.py
    if not os.path.isfile(ARC_TOOL):
        print(f"[ERROR] 未找到 arc_tool.py: {ARC_TOOL}")
        sys.exit(1)

    # Step 1: 带描述构建
    print("[INFO] 构建带描述版本...")
    arc_with_desc_dir = os.path.join(OUTPUT_DIR, "arc_有简述版")
    arc_with_desc_file = os.path.join(arc_with_desc_dir, "Text_ZH.arc")
    os.makedirs(arc_with_desc_dir, exist_ok=True)
    if os.path.exists(arc_with_desc_file):
        os.remove(arc_with_desc_file)
    run_archive_tool(["pack", arc_with_desc_file, SOURCE_DIR, "--level", "6"])
    print(f"[SUCCESS] 带描述归档: {arc_with_desc_file}")

    # Step 2: 拷贝源文件到 set_with_desc
    print("[INFO] 拷贝源文件到 set_with_desc...")
    set_with_desc_dir = os.path.join(OUTPUT_DIR, "set_有简述版", "Text_ZH")
    if os.path.isdir(set_with_desc_dir):
        shutil.rmtree(set_with_desc_dir)
    shutil.copytree(SOURCE_DIR, set_with_desc_dir)
    print(f"[SUCCESS] 源文件已拷贝: {set_with_desc_dir}")

    # Step 3: 无描述构建
    print("[INFO] 构建无描述版本...")
    arc_no_desc_dir = os.path.join(OUTPUT_DIR, "arc_无简述版")
    arc_no_desc_file = os.path.join(arc_no_desc_dir, "Text_ZH.arc")
    os.makedirs(arc_no_desc_dir, exist_ok=True)
    if os.path.exists(arc_no_desc_file):
        os.remove(arc_no_desc_file)

    # 准备去除简述的临时目录
    build_tmp = os.path.join(OUTPUT_DIR, "_build")
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)
    shutil.copytree(SOURCE_DIR, STRIPPED_SOURCE_DIR)
    strip_affix_notes(STRIPPED_SOURCE_DIR)

    run_archive_tool(["pack", arc_no_desc_file, STRIPPED_SOURCE_DIR, "--level", "6"])
    print(f"[SUCCESS] 无描述归档: {arc_no_desc_file}")

    # Step 4: 移动去除简述的源文件到 set_no_desc
    print("[INFO] 移动去除简述的源文件到 set_no_desc...")
    set_no_desc_dir = os.path.join(OUTPUT_DIR, "set_无简述版", "Text_ZH")
    if os.path.isdir(set_no_desc_dir):
        shutil.rmtree(set_no_desc_dir)
    shutil.move(STRIPPED_SOURCE_DIR, set_no_desc_dir)
    print(f"[SUCCESS] 源文件已移动: {set_no_desc_dir}")

    # Step 5: 清理临时目录
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)

    print("[INFO] Release 构建完成。")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GD 汉化补丁跨平台构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["release", "with-desc", "no-desc"],
        default="release",
        help="构建模式: release (默认), with-desc, no-desc",
    )
    args = parser.parse_args()

    if args.mode == "release":
        build_release()
    elif args.mode == "with-desc":
        build_single(enable_desc=True)
    elif args.mode == "no-desc":
        build_single(enable_desc=False)


if __name__ == "__main__":
    main()
