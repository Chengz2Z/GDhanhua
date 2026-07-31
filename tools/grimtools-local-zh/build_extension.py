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
DEFAULT_OUTPUT_DIRS = (
    TOOL_DIR / "extension" / "generated",
    TOOL_DIR / "extension-safari" / "generated",
)
MODE_STORAGE_KEY = "grimtools_local_zh_mode"
MODE_OFFICIAL = "official"
MODE_LOCAL = "local"


@dataclass(frozen=True)
class EntrySource:
    path: Path
    line_number: int
    value: str


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        config = json.load(handle)

    required = {"include"}
    missing = sorted(required.difference(config))
    if missing:
        raise ValueError("配置缺少字段: {}".format(", ".join(missing)))

    has_source_root = "source_root" in config
    has_source_roots = "source_roots" in config
    if has_source_root == has_source_roots:
        raise ValueError("配置必须且只能设置 source_root 或 source_roots")
    if has_source_root and (
        not isinstance(config["source_root"], str)
        or not config["source_root"].strip()
    ):
        raise ValueError("source_root 必须是非空字符串")
    if has_source_roots:
        source_roots = config["source_roots"]
        if not isinstance(source_roots, list) or not source_roots:
            raise ValueError("source_roots 必须是非空数组")
        if any(
            not isinstance(source_root, str) or not source_root.strip()
            for source_root in source_roots
        ):
            raise ValueError("source_roots 只能包含非空字符串")
        if len(source_roots) != len(set(source_roots)):
            raise ValueError("source_roots 不能包含重复项")
    if not isinstance(config["include"], list) or not config["include"]:
        raise ValueError("include 必须是非空数组")
    if config.get("duplicate_policy", "last") not in {"first", "last", "error"}:
        raise ValueError("duplicate_policy 只能是 first、last 或 error")
    remove_markers = config.get("remove_markers", [])
    if not isinstance(remove_markers, list):
        raise ValueError("remove_markers 必须是数组")
    if any(not isinstance(marker, str) or not marker for marker in remove_markers):
        raise ValueError("remove_markers 只能包含非空字符串")
    if len(remove_markers) != len(set(remove_markers)):
        raise ValueError("remove_markers 不能包含重复项")
    return config


def matches_any(path: Path, patterns: Sequence[str]) -> bool:
    normalized = path.as_posix()
    return any(path.match(pattern) or Path(normalized).match(pattern) for pattern in patterns)


def configured_source_roots(config: dict) -> List[str]:
    if "source_roots" in config:
        return config["source_roots"]
    return [config["source_root"]]


def discover_files(config_path: Path, config: dict) -> Tuple[Path, List[Path]]:
    excluded = config.get("exclude", [])
    attempts: List[Tuple[Path, str]] = []
    for configured_root in configured_source_roots(config):
        source_root = (config_path.parent / configured_root).resolve()
        if not source_root.is_dir():
            attempts.append((source_root, "目录不存在"))
            continue

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
        if files:
            return source_root, files
        attempts.append((source_root, "没有匹配白名单的文件"))

    details = "\n".join(
        "  - {} ({})".format(path, reason) for path, reason in attempts
    )
    raise FileNotFoundError("未找到可用的汉化目录:\n{}".format(details))


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


def normalize_web_value(value: str, remove_markers: Sequence[str]) -> str:
    """Remove game-only formatting markers unsupported by GrimTools."""
    for marker in remove_markers:
        value = value.replace(marker, "")
    return value


def count_removed_markers(value: str, remove_markers: Sequence[str]) -> int:
    """Count replacements using the same ordered process as normalization."""
    count = 0
    for marker in remove_markers:
        count += value.count(marker)
        value = value.replace(marker, "")
    return count


def collect_entries(
    files: Sequence[Path],
    duplicate_policy: str,
    remove_markers: Sequence[str],
) -> Tuple[
    Dict[str, str],
    List[Tuple[str, EntrySource, EntrySource]],
    int,
]:
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
            entries[key] = normalize_web_value(value, remove_markers)
            sources[key] = current

    removed_marker_count = sum(
        count_removed_markers(source.value, remove_markers)
        for source in sources.values()
    )
    return entries, conflicts, removed_marker_count


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
  const MODE_STORAGE_KEY = "{mode_storage_key}";
  const MODE_OFFICIAL = "{mode_official}";
  const MODE_LOCAL = "{mode_local}";
  let mode = MODE_OFFICIAL;
  let remoteTexts = {{}};

  try {{
    mode =
      globalThis.localStorage &&
      globalThis.localStorage.getItem(MODE_STORAGE_KEY) === MODE_LOCAL
        ? MODE_LOCAL
        : MODE_OFFICIAL;
  }} catch (error) {{
    console.warn(
      "[GrimTools 本地汉化] 无法读取语言模式，将使用官方简体中文。",
      error
    );
  }}

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
    console.warn(
      mode === MODE_LOCAL
        ? "[GrimTools 本地汉化] 远程中文词典读取失败，将只使用本地 KEY。"
        : "[GrimTools 本地汉化] 远程中文词典读取失败，官方简体中文暂不可用。",
      error
    );
  }}

  const dictionaries =
    globalThis.{variable_name} && typeof globalThis.{variable_name} === "object"
      ? globalThis.{variable_name}
      : (globalThis.{variable_name} = {{}});

  if (mode === MODE_LOCAL) {{
    dictionaries.zh = Object.assign({{}}, remoteTexts, OVERRIDES);
    console.info(
      "[GrimTools 本地汉化] 当前模式: local；已覆盖 %d 个 KEY，远程回退 %d 个 KEY。",
      Object.keys(OVERRIDES).length,
      Object.keys(remoteTexts).length
    );
  }} else {{
    dictionaries.zh = Object.assign({{}}, remoteTexts);
    console.info(
      "[GrimTools 本地汉化] 当前模式: official；使用 GrimTools 官方简体中文。"
    );
  }}
}})();
""".format(
        variable_name=variable_name,
        remote_path=remote_path,
        overrides_json=overrides_json,
        mode_storage_key=MODE_STORAGE_KEY,
        mode_official=MODE_OFFICIAL,
        mode_local=MODE_LOCAL,
    )


def make_language_mode_selector() -> str:
    return """\
// 此文件由 build_extension.py 自动生成，请勿手工修改。
(() => {
  "use strict";

  const MODE_STORAGE_KEY = "grimtools_local_zh_mode";
  const MODE_OFFICIAL = "official";
  const MODE_LOCAL = "local";
  const LOCAL_OPTION_LABEL = "简体中文-本地化";
  const POPUP_SELECTOR = ".language-selector-popup";
  const LOCAL_OPTION_ATTRIBUTE = "data-grimtools-local-zh-option";
  const OFFICIAL_BOUND_ATTRIBUTE = "data-grimtools-local-zh-official-bound";

  function readMode() {
    try {
      const storedMode = window.localStorage.getItem(MODE_STORAGE_KEY);
      if (storedMode === MODE_LOCAL || storedMode === MODE_OFFICIAL) {
        return storedMode;
      }
      window.localStorage.setItem(MODE_STORAGE_KEY, MODE_OFFICIAL);
    } catch (error) {
      console.warn(
        "[GrimTools 本地汉化] 无法读取语言模式，默认使用官方简体中文。",
        error
      );
    }
    return MODE_OFFICIAL;
  }

  function switchMode(mode, event) {
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      window.localStorage.setItem(MODE_STORAGE_KEY, mode);
      window.localStorage.setItem("app_locale", "zh");
    } catch (error) {
      console.error("[GrimTools 本地汉化] 无法保存语言模式。", error);
      return;
    }
    window.location.reload();
  }

  function isOfficialChineseLink(link) {
    if (link.hasAttribute(LOCAL_OPTION_ATTRIBUTE)) {
      return false;
    }
    try {
      const path = new URL(link.getAttribute("href") || "", window.location.href)
        .pathname.replace(/\\/+$/, "");
      return path.endsWith("/zh");
    } catch (error) {
      return false;
    }
  }

  function setLocalOptionLabel(link) {
    const flag = link.querySelector(".flag");
    const flagClone = flag ? flag.cloneNode(true) : null;
    link.replaceChildren();
    if (flagClone) {
      link.appendChild(flagClone);
    }
    link.appendChild(document.createTextNode(LOCAL_OPTION_LABEL));
  }

  function setCurrentState(link, selected) {
    if (selected) {
      link.setAttribute("aria-current", "true");
    } else {
      link.removeAttribute("aria-current");
    }
  }

  function installOptions(popup) {
    const officialLink = Array.from(popup.querySelectorAll("a")).find(
      isOfficialChineseLink
    );
    if (!officialLink) {
      return;
    }

    if (!officialLink.hasAttribute(OFFICIAL_BOUND_ATTRIBUTE)) {
      officialLink.setAttribute(OFFICIAL_BOUND_ATTRIBUTE, "true");
      officialLink.addEventListener(
        "click",
        (event) => switchMode(MODE_OFFICIAL, event),
        true
      );
    }

    let localLink = popup.querySelector(`[${LOCAL_OPTION_ATTRIBUTE}]`);
    if (!localLink) {
      localLink = officialLink.cloneNode(true);
      localLink.removeAttribute(OFFICIAL_BOUND_ATTRIBUTE);
      localLink.setAttribute(LOCAL_OPTION_ATTRIBUTE, "true");
      setLocalOptionLabel(localLink);
      localLink.addEventListener(
        "click",
        (event) => switchMode(MODE_LOCAL, event),
        true
      );
      officialLink.insertAdjacentElement("afterend", localLink);
    }

    const mode = readMode();
    setCurrentState(officialLink, mode === MODE_OFFICIAL);
    setCurrentState(localLink, mode === MODE_LOCAL);
  }

  function start() {
    const popup = document.querySelector(POPUP_SELECTOR);
    if (!popup) {
      window.setTimeout(start, 100);
      return;
    }

    installOptions(popup);
    new MutationObserver(() => installOptions(popup)).observe(popup, {
      childList: true,
    });
  }

  start();
})();
"""


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


def build(config_path: Path, output_dirs: Sequence[Path]) -> int:
    config = load_config(config_path)
    source_root, files = discover_files(config_path, config)
    duplicate_policy = config.get("duplicate_policy", "last")
    remove_markers = config.get("remove_markers", [])
    entries, conflicts, removed_marker_count = collect_entries(
        files, duplicate_policy, remove_markers
    )

    generated_files = (
        (
            "db-zh.js",
            make_loader(
                "db_l10n_texts",
                "/db/itemdb/l10n/zh.js",
                entries,
            ),
        ),
        (
            "editor-zh.js",
            make_loader(
                "b_l10n_texts",
                "/editor/js/l10n/zh.js",
                entries,
            ),
        ),
        (
            "language-mode-selector.js",
            make_language_mode_selector(),
        ),
    )
    changed_count = 0
    for output_dir in output_dirs:
        for filename, content in generated_files:
            changed_count += int(write_if_changed(output_dir / filename, content))

    print("[完成] 汉化目录: {}".format(source_root))
    print("[完成] 白名单文件: {} 个".format(len(files)))
    for path in files:
        print("  - {}".format(relative_label(path, source_root)))
    print("[完成] 本地 KEY: {} 个".format(len(entries)))
    marker_label = json.dumps(remove_markers, ensure_ascii=False)
    print("[完成] 配置移除标记: {}".format(marker_label))
    print("[完成] 移除标记出现次数: {} 个".format(removed_marker_count))
    print("[完成] 扩展目标: {} 个".format(len(output_dirs)))
    for output_dir in output_dirs:
        print("  - {}".format(output_dir))
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
        action="append",
        help=(
            "自定义生成目录；可重复指定。"
            "省略时同时生成 Chromium 和 Safari 扩展资源"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output_dirs = (
            [path.resolve() for path in args.output_dir]
            if args.output_dir
            else list(DEFAULT_OUTPUT_DIRS)
        )
        return build(args.config.resolve(), output_dirs)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("[错误] {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
