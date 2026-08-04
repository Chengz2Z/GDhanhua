#!/usr/bin/env python3
"""
跨平台构建脚本 — 替代 build.bat + prepare-build.ps1
纯 Python 实现，无需 Wine 或外部依赖。

最低支持 Python 版本: 3.7

用法:
    python build.py              # 默认: release 模式，打包所有版本
    python build.py release      # release 模式，打包所有版本
    python build.py with-desc    # 仅保留词缀简述打包
    python build.py no-desc      # 生成无简述版本，同时去除技能英文原名
    python build.py -h / --help  # 显示帮助
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 7):
    sys.exit("错误: 本脚本需要 Python 3.7 或更高版本，当前版本: {}.{}".format(*sys.version_info[:2]))

import argparse
import json
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
FILTER_CONFIG_FILE = os.path.join(SCRIPT_DIR, "scripts", "text-filters.json")


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


def load_filter_profiles(config_path: str) -> dict:
    """读取并校验有简述、无简述版本共用的文本过滤配置。"""
    with open(config_path, "r", encoding="utf-8-sig") as f:
        config = json.load(f)

    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("过滤配置缺少 profiles 对象")

    compiled_profiles = {}
    for profile_name in ("with_desc", "no_desc"):
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            raise ValueError("过滤配置缺少 {} 对象".format(profile_name))

        rules = profile.get("rules")
        if not isinstance(rules, list):
            raise ValueError("{}.rules 必须是数组".format(profile_name))

        compiled_rules = []
        for rule_index, rule in enumerate(rules):
            rule_label = "{}.rules[{}]".format(profile_name, rule_index)
            if not isinstance(rule, dict):
                raise ValueError("{} 必须是对象".format(rule_label))

            include = rule.get("include", [])
            pattern_strings = rule.get("remove_patterns", [])
            replace_configs = rule.get("replace_patterns", [])
            if not isinstance(include, list) or any(
                not isinstance(item, str) or not item for item in include
            ):
                raise ValueError("{}.include 必须是字符串数组".format(rule_label))
            if not isinstance(pattern_strings, list) or any(
                not isinstance(item, str) or not item for item in pattern_strings
            ):
                raise ValueError(
                    "{}.remove_patterns 必须是字符串数组".format(rule_label)
                )
            if not isinstance(replace_configs, list):
                raise ValueError(
                    "{}.replace_patterns 必须是数组".format(rule_label)
                )
            if len(include) != len(set(include)):
                raise ValueError("{}.include 不能包含重复项".format(rule_label))
            if len(pattern_strings) != len(set(pattern_strings)):
                raise ValueError(
                    "{}.remove_patterns 不能包含重复项".format(rule_label)
                )
            if (pattern_strings or replace_configs) and not include:
                raise ValueError(
                    "{} 配置了过滤操作时 include 不能为空".format(
                        rule_label
                    )
                )

            patterns = []
            for pattern_string in pattern_strings:
                try:
                    patterns.append(re.compile(pattern_string))
                except re.error as error:
                    raise ValueError(
                        "{}.remove_patterns 包含无效正则 {!r}: {}".format(
                            rule_label, pattern_string, error
                        )
                    ) from error

            replace_patterns = []
            for replace_index, replace_config in enumerate(replace_configs):
                replace_label = "{}.replace_patterns[{}]".format(
                    rule_label, replace_index
                )
                if not isinstance(replace_config, dict):
                    raise ValueError("{} 必须是对象".format(replace_label))
                replace_pattern_string = replace_config.get("pattern")
                keep_groups = replace_config.get("keep_groups")
                if not isinstance(replace_pattern_string, str) or not replace_pattern_string:
                    raise ValueError("{}.pattern 必须是非空字符串".format(replace_label))
                if not isinstance(keep_groups, list) or any(
                    not isinstance(group, int) or isinstance(group, bool) or group < 1
                    for group in keep_groups
                ):
                    raise ValueError(
                        "{}.keep_groups 必须是正整数数组".format(replace_label)
                    )
                try:
                    replace_pattern = re.compile(replace_pattern_string)
                except re.error as error:
                    raise ValueError(
                        "{}.pattern 包含无效正则 {!r}: {}".format(
                            replace_label, replace_pattern_string, error
                        )
                    ) from error
                if any(group > replace_pattern.groups for group in keep_groups):
                    raise ValueError(
                        "{}.keep_groups 超出正则捕获组数量 {}".format(
                            replace_label, replace_pattern.groups
                        )
                    )
                replace_patterns.append(
                    {
                        "pattern": replace_pattern,
                        "pattern_string": replace_pattern_string,
                        "keep_groups": keep_groups,
                    }
                )

            compiled_rules.append(
                {
                    "include": include,
                    "remove_patterns": patterns,
                    "remove_pattern_strings": pattern_strings,
                    "replace_patterns": replace_patterns,
                }
            )

        compiled_profiles[profile_name] = {"rules": compiled_rules}

    return compiled_profiles


def apply_text_filters(target_dir: str, profile_name: str, profile: dict) -> None:
    """按指定构建版本的配置过滤临时文本副本。"""
    changed_files = 0
    changed_fields = 0
    rules = profile["rules"]

    for root, _dirs, files in os.walk(target_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            relative_path = os.path.relpath(fpath, target_dir).replace(os.sep, "/")
            matching_rules = [
                rule
                for rule in rules
                if (rule["remove_patterns"] or rule["replace_patterns"])
                and any(
                    fnmatch(fname, include_pattern)
                    or fnmatch(relative_path, include_pattern)
                    for include_pattern in rule["include"]
                )
            ]
            if not matching_rules:
                continue

            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            updated = content
            replacements = 0
            for rule in matching_rules:
                for replace_config in rule["replace_patterns"]:
                    keep_groups = replace_config["keep_groups"]

                    def _keep_groups(match: re.Match, groups=keep_groups) -> str:
                        return "".join(match.group(group) or "" for group in groups)

                    updated, pattern_replacements = replace_config["pattern"].subn(
                        _keep_groups, updated
                    )
                    replacements += pattern_replacements
                for pattern in rule["remove_patterns"]:
                    updated, pattern_replacements = pattern.subn("", updated)
                    replacements += pattern_replacements
            if updated != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(updated)
                changed_files += 1
                changed_fields += replacements

    print(
        f"[INFO] 文本过滤完成 ({profile_name}): "
        f"{changed_files} 个文件, {changed_fields} 处匹配已处理。"
    )


def profile_has_text_filters(profile: dict) -> bool:
    return any(
        rule["remove_patterns"] or rule["replace_patterns"]
        for rule in profile["rules"]
    )


def fnmatch(name: str, pattern: str) -> bool:
    """简易 fnmatch 实现（仅支持 * 通配符）。"""
    regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
    return re.match(regex, name) is not None


# ---------------------------------------------------------------------------
# 单次构建
# ---------------------------------------------------------------------------

def build_single(enable_desc: bool, profile_name: str, profile: dict) -> None:
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
    has_text_filters = profile_has_text_filters(profile)
    if has_text_filters:
        source_dir = STRIPPED_SOURCE_DIR
        print("[INFO] 正在准备构建源副本...")

        # 清理旧的临时目录
        build_tmp = os.path.join(OUTPUT_DIR, "_build")
        if os.path.isdir(build_tmp):
            shutil.rmtree(build_tmp)

        # 复制 Text_ZH 到临时目录
        shutil.copytree(SOURCE_DIR, STRIPPED_SOURCE_DIR)

        apply_text_filters(STRIPPED_SOURCE_DIR, profile_name, profile)

    # 4. 检查 arc_tool.py
    if not os.path.isfile(ARC_TOOL):
        print(f"[ERROR] 未找到 arc_tool.py: {ARC_TOOL}")
        sys.exit(1)

    # 5. 调用 arc_tool.py 打包
    print("[INFO] 开始打包...")
    run_archive_tool(["pack", OUTPUT_FILE, source_dir, "--level", "6"])

    print(f'[INFO] ENABLE_DESC="{1 if enable_desc else 0}"')
    print(f'[INFO] FILTER_PROFILE="{profile_name}"')
    print(f"[SUCCESS] 构建完成。输出文件: {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Release 构建
# ---------------------------------------------------------------------------

def build_release(filter_profiles: dict) -> None:
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

    with_desc_name = "with_desc"
    no_desc_name = "no_desc"
    with_desc_profile = filter_profiles[with_desc_name]
    no_desc_profile = filter_profiles[no_desc_name]
    build_tmp = os.path.join(OUTPUT_DIR, "_build")
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)

    # Step 1: 带描述构建
    print("[INFO] 构建带描述版本...")
    with_desc_source_dir = SOURCE_DIR
    if profile_has_text_filters(with_desc_profile):
        shutil.copytree(SOURCE_DIR, STRIPPED_SOURCE_DIR)
        apply_text_filters(
            STRIPPED_SOURCE_DIR, with_desc_name, with_desc_profile
        )
        with_desc_source_dir = STRIPPED_SOURCE_DIR

    arc_with_desc_dir = os.path.join(OUTPUT_DIR, "arc_{}".format(with_desc_name))
    arc_with_desc_file = os.path.join(arc_with_desc_dir, "Text_ZH.arc")
    os.makedirs(arc_with_desc_dir, exist_ok=True)
    if os.path.exists(arc_with_desc_file):
        os.remove(arc_with_desc_file)
    run_archive_tool(
        ["pack", arc_with_desc_file, with_desc_source_dir, "--level", "6"]
    )
    print(f"[SUCCESS] 带描述归档: {arc_with_desc_file}")

    # Step 2: 拷贝源文件到 set_with_desc
    print("[INFO] 拷贝源文件到 set_{}...".format(with_desc_name))
    set_with_desc_dir = os.path.join(
        OUTPUT_DIR, "set_{}".format(with_desc_name), "Text_ZH"
    )
    if os.path.isdir(set_with_desc_dir):
        shutil.rmtree(set_with_desc_dir)
    shutil.copytree(with_desc_source_dir, set_with_desc_dir)
    print(f"[SUCCESS] 源文件已拷贝: {set_with_desc_dir}")

    # Step 3: 无描述构建
    print("[INFO] 构建无描述版本...")
    arc_no_desc_dir = os.path.join(OUTPUT_DIR, "arc_{}".format(no_desc_name))
    arc_no_desc_file = os.path.join(arc_no_desc_dir, "Text_ZH.arc")
    os.makedirs(arc_no_desc_dir, exist_ok=True)
    if os.path.exists(arc_no_desc_file):
        os.remove(arc_no_desc_file)

    # 准备 no_desc 配置使用的临时目录
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)
    shutil.copytree(SOURCE_DIR, STRIPPED_SOURCE_DIR)
    if profile_has_text_filters(no_desc_profile):
        apply_text_filters(STRIPPED_SOURCE_DIR, no_desc_name, no_desc_profile)

    run_archive_tool(["pack", arc_no_desc_file, STRIPPED_SOURCE_DIR, "--level", "6"])
    print(f"[SUCCESS] 无描述归档: {arc_no_desc_file}")

    # Step 4: 移动去除简述的源文件到 set_no_desc
    print("[INFO] 移动去除简述的源文件到 set_{}...".format(no_desc_name))
    set_no_desc_dir = os.path.join(
        OUTPUT_DIR, "set_{}".format(no_desc_name), "Text_ZH"
    )
    if os.path.isdir(set_no_desc_dir):
        shutil.rmtree(set_no_desc_dir)
    shutil.move(STRIPPED_SOURCE_DIR, set_no_desc_dir)
    print(f"[SUCCESS] 源文件已移动: {set_no_desc_dir}")

    # Step 5: 清理临时目录
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)

    print('[INFO] FILTER_CONFIG="{}"'.format(FILTER_CONFIG_FILE))
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
    filter_profiles = load_filter_profiles(FILTER_CONFIG_FILE)

    if args.mode == "release":
        build_release(filter_profiles)
    elif args.mode == "with-desc":
        build_single(
            enable_desc=True,
            profile_name="with_desc",
            profile=filter_profiles["with_desc"],
        )
    elif args.mode == "no-desc":
        build_single(
            enable_desc=False,
            profile_name="no_desc",
            profile=filter_profiles["no_desc"],
        )


if __name__ == "__main__":
    main()
