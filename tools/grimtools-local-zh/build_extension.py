#!/usr/bin/env python3
"""Build the GrimTools local Chinese localization browser extension."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = TOOL_DIR / "config.json"
DEFAULT_OUTPUT_DIR = TOOL_DIR / "extension" / "generated"


@dataclass(frozen=True)
class EntrySource:
    path: Path
    line_number: int
    value: str


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        config = json.load(handle)

    required = {"source_root", "include"}
    missing = sorted(required.difference(config))
    if missing:
        raise ValueError("配置缺少字段: {}".format(", ".join(missing)))

    if not isinstance(config["include"], list) or not config["include"]:
        raise ValueError("include 必须是非空数组")
    if config.get("duplicate_policy", "last") not in {"first", "last", "error"}:
        raise ValueError("duplicate_policy 只能是 first、last 或 error")
    return config


def matches_any(path: Path, patterns: Sequence[str]) -> bool:
    normalized = path.as_posix()
    return any(path.match(pattern) or Path(normalized).match(pattern) for pattern in patterns)


def discover_files(config_path: Path, config: dict) -> Tuple[Path, List[Path]]:
    source_root = (config_path.parent / config["source_root"]).resolve()
    if not source_root.is_dir():
        raise FileNotFoundError("汉化目录不存在: {}".format(source_root))

    excluded = config.get("exclude", [])
    discovered: Dict[str, Path] = {}
    for pattern in config["include"]:
        for path in source_root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(source_root)
            if matches_any(relative, excluded):
                continue
            discovered[relative.as_posix().casefold()] = path

    files = [discovered[key] for key in sorted(discovered)]
    if not files:
        raise FileNotFoundError("白名单没有匹配到任何汉化文件")
    return source_root, files


def iter_entries(path: Path) -> Iterable[Tuple[int, str, str]]:
    with path.open("r", encoding="utf-8-sig", newline=None) as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            raw_key, value = line.split("=", 1)
            key = raw_key.strip()
            if key:
                yield line_number, key, value


def collect_entries(
    files: Sequence[Path], duplicate_policy: str
) -> Tuple[Dict[str, str], List[Tuple[str, EntrySource, EntrySource]]]:
    entries: Dict[str, str] = {}
    sources: Dict[str, EntrySource] = {}
    conflicts: List[Tuple[str, EntrySource, EntrySource]] = []

    for path in files:
        for line_number, key, value in iter_entries(path):
            current = EntrySource(path, line_number, value)
            previous = sources.get(key)
            if previous is not None:
                if previous.value != value:
                    conflicts.append((key, previous, current))
                if duplicate_policy == "error":
                    raise ValueError(
                        "发现重复 KEY: {} ({}:{}, {}:{})".format(
                            key,
                            previous.path,
                            previous.line_number,
                            path,
                            line_number,
                        )
                    )
                if duplicate_policy == "first":
                    continue
            entries[key] = value
            sources[key] = current

    return entries, conflicts


def make_loader(variable_name: str, remote_path: str, entries: Dict[str, str]) -> str:
    overrides_json = json.dumps(
        entries,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return """\
// 此文件由 build_extension.py 自动生成，请勿手工修改。
(() => {{
  "use strict";

  const REMOTE_URL = "https://www.grimtools.com{remote_path}?grim-local-zh-bypass=1";
  const OVERRIDES = {overrides_json};
  let remoteTexts = {{}};

  try {{
    const request = new XMLHttpRequest();
    request.open("GET", REMOTE_URL, false);
    request.overrideMimeType("text/plain; charset=utf-8");
    request.send(null);
    if (request.status < 200 || request.status >= 300) {{
      throw new Error(`HTTP ${{request.status}}`);
    }}

    const source = request.responseText;
    const objectStart = source.indexOf("{{");
    const objectEnd = source.lastIndexOf("}}");
    if (objectStart < 0 || objectEnd <= objectStart) {{
      throw new Error("无法识别远程语言文件格式");
    }}
    remoteTexts = JSON.parse(source.slice(objectStart, objectEnd + 1));
  }} catch (error) {{
    console.warn("[GrimTools 本地汉化] 远程中文词典读取失败，将只使用本地 KEY。", error);
  }}

  const dictionaries =
    globalThis.{variable_name} && typeof globalThis.{variable_name} === "object"
      ? globalThis.{variable_name}
      : (globalThis.{variable_name} = {{}});

  dictionaries.zh = Object.assign({{}}, remoteTexts, OVERRIDES);
  console.info(
    "[GrimTools 本地汉化] 已覆盖 %d 个 KEY，远程回退 %d 个 KEY。",
    Object.keys(OVERRIDES).length,
    Object.keys(remoteTexts).length
  );
}})();
""".format(
        variable_name=variable_name,
        remote_path=remote_path,
        overrides_json=overrides_json,
    )


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


def relative_label(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def build(config_path: Path, output_dir: Path) -> int:
    config = load_config(config_path)
    source_root, files = discover_files(config_path, config)
    duplicate_policy = config.get("duplicate_policy", "last")
    entries, conflicts = collect_entries(files, duplicate_policy)

    targets = (
        (
            output_dir / "db-zh.js",
            "db_l10n_texts",
            "/db/itemdb/l10n/zh.js",
        ),
        (
            output_dir / "editor-zh.js",
            "b_l10n_texts",
            "/editor/js/l10n/zh.js",
        ),
    )
    changed_count = 0
    for output_path, variable_name, remote_path in targets:
        content = make_loader(variable_name, remote_path, entries)
        changed_count += int(write_if_changed(output_path, content))

    print("[完成] 汉化目录: {}".format(source_root))
    print("[完成] 白名单文件: {} 个".format(len(files)))
    for path in files:
        print("  - {}".format(relative_label(path, source_root)))
    print("[完成] 本地 KEY: {} 个".format(len(entries)))
    print("[完成] 生成文件更新: {} 个".format(changed_count))

    if conflicts:
        print(
            "[提示] {} 个重复 KEY 的值不同，已按 {} 策略处理:".format(
                len(conflicts), duplicate_policy
            )
        )
        for key, previous, current in conflicts:
            print(
                "  - {}: {}:{} -> {}:{}".format(
                    key,
                    relative_label(previous.path, source_root),
                    previous.line_number,
                    relative_label(current.path, source_root),
                    current.line_number,
                )
            )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 Text_ZH 白名单文件生成 GrimTools 本地汉化扩展资源"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="配置文件路径（默认: %(default)s）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="生成目录（默认: %(default)s）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return build(args.config.resolve(), args.output_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("[错误] {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
