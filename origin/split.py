#!/usr/bin/env python3
"""
跨平台解包脚本 — 替代 origin/split.bat
纯 Python 实现，无需 Wine 或外部依赖。

用法:
    cd origin
    python split.py
"""

import glob
import os
import shutil
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARC_TOOL = os.path.join(SCRIPT_DIR, "..", "arc_tool.py")


def main() -> None:
    # 检查 arc_tool.py
    if not os.path.isfile(ARC_TOOL):
        print(f"[ERROR] 未找到 arc_tool.py: {ARC_TOOL}")
        sys.exit(1)

    # 收集 .arc 文件
    arc_files = glob.glob(os.path.join(SCRIPT_DIR, "*.arc"))
    if not arc_files:
        print(f"[ERROR] 未在目录中找到 .arc 文件: {SCRIPT_DIR}")
        sys.exit(1)

    # 清理旧的解包内容（保留 .bat、.py、.arc 文件）
    print("[INFO] 清理旧的解包内容...")
    keep_ext = {".bat", ".py", ".arc"}
    for entry in os.listdir(SCRIPT_DIR):
        full = os.path.join(SCRIPT_DIR, entry)
        if os.path.isdir(full):
            shutil.rmtree(full)
        elif os.path.splitext(entry)[1].lower() not in keep_ext:
            os.remove(full)

    # 逐个解包
    for arc_path in arc_files:
        arc_name = os.path.basename(arc_path)
        # 根据 .arc 文件名生成输出目录（小写，去掉扩展名）
        out_dir = os.path.join(SCRIPT_DIR, os.path.splitext(arc_name)[0].lower())
        print(f"[INFO] 正在解包: {arc_name} -> {out_dir}")
        cmd = [sys.executable, ARC_TOOL, "unpack", arc_path, out_dir]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"[ERROR] 解包失败: {arc_name}")
            sys.exit(1)

    print(f"[SUCCESS] 解包完成，输出目录: {SCRIPT_DIR}")


if __name__ == "__main__":
    main()
