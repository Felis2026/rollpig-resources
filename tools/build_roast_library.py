from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PIG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SAFE_PLACEHOLDER_PATTERN = re.compile(r"\{\s*(k|v|origin|food)\s*\}", re.IGNORECASE)
PLACEHOLDER_PATTERN = re.compile(r"\{([^{}]*)\}")
SUSPICIOUS_ACCOUNT_PATTERN = re.compile(r"(?<!\d)\d{5,12}(?!\d)")
URL_PATTERN = re.compile(r"(?i)(?:https?://|www\.)")
NUMERIC_MENTION_PATTERN = re.compile(r"(?<!\w)@\s*\d{5,12}(?!\d)")
TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])(?=[A-Za-z0-9_-]{32,})(?=[A-Za-z0-9_-]*[A-Za-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+")
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

ROAST_LIBRARY_MAX_SIZE = 5 * 1024 * 1024
ROAST_MAX_ORIGINS = 1_000
ROAST_MAX_PAIRS = 20_000
ROAST_MAX_TEXTS = 30_000
ROAST_MAX_TEXTS_PER_PAIR = 20
ROAST_MAX_TEXT_LENGTH = 600
ROAST_LONG_TEXT_WARNING = 240


# ================================ 数据模型与通用工具 ================================ #


@dataclass(frozen=True)
class RejectedText:
    origin_id: str
    target_id: str
    text: str
    reason: str


@dataclass(frozen=True)
class ChangedText:
    origin_id: str
    target_id: str
    before: str
    after: str


@dataclass
class BuildReport:
    source_origins: int = 0
    source_pairs: int = 0
    source_texts: int = 0
    output_origins: int = 0
    output_pairs: int = 0
    output_texts: int = 0
    duplicate_texts: int = 0
    excluded_texts: int = 0
    rejected: list[RejectedText] = field(default_factory=list)
    changed: list[ChangedText] = field(default_factory=list)
    long_texts: list[dict[str, Any]] = field(default_factory=list)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def write_utf8_lf(path: Path, text: str) -> None:
    """以无 BOM UTF-8 和 LF 写入，保证资源包在不同平台上的哈希稳定。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_json(path: Path, expected_type: type) -> Any:
    raw = path.read_bytes()
    if len(raw) > ROAST_LIBRARY_MAX_SIZE:
        raise ValueError(f"JSON 文件超过 {ROAST_LIBRARY_MAX_SIZE} 字节上限: {path}")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"JSON 读取失败: {path}: {error}") from error
    if not isinstance(data, expected_type):
        raise ValueError(f"JSON 顶层必须是 {expected_type.__name__}: {path}")
    return data


def normalize_roast_text(text: str) -> str:
    """执行仅有唯一正确结果的安全清洗，不猜测修补残缺占位符。"""

    normalized = text.strip()
    quote_pairs = {('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")}
    if len(normalized) >= 2 and (normalized[0], normalized[-1]) in quote_pairs:
        normalized = normalized[1:-1].strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = SAFE_PLACEHOLDER_PATTERN.sub(lambda match: "{" + match.group(1).lower() + "}", normalized)
    return normalized


def roast_text_identity(text: str) -> str:
    """来源索引和长期排除表只保存标准化正文哈希，不复制公开或私有正文。"""

    return sha256_text(normalize_roast_text(text))


def _load_exclusion_hashes(path: Path) -> set[str]:
    data = read_json(path, dict)
    if data.get("schema_version") != 1:
        raise ValueError(f"排除表 schema_version 当前只能为 1: {path}")
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError(f"排除表 items 必须是 list: {path}")

    hashes: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"排除表第 {index + 1} 项必须是 object")
        value = item.get("sha256")
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"排除表第 {index + 1} 项 sha256 非法")
        if not isinstance(item.get("reason"), str) or not str(item["reason"]).strip():
            raise ValueError(f"排除表第 {index + 1} 项必须填写 reason")
        if not isinstance(item.get("excluded_at"), str) or not str(item["excluded_at"]).strip():
            raise ValueError(f"排除表第 {index + 1} 项必须填写 excluded_at")
        hashes.add(value)
    return hashes


# ================================ 文案清洗与安全校验 ================================ #


def _text_rejection_reason(text: str, *, is_pvp: bool) -> str | None:
    if not text:
        return "文案为空"
    if len(text) > ROAST_MAX_TEXT_LENGTH:
        return f"文案超过 {ROAST_MAX_TEXT_LENGTH} 字符"
    if "\ufffd" in text or CONTROL_PATTERN.search(text):
        return "包含乱码替换符或不可见控制字符"
    if SUSPICIOUS_ACCOUNT_PATTERN.search(text):
        return "包含疑似 5～12 位账号数字"
    if URL_PATTERN.search(text):
        return "包含 URL"
    if NUMERIC_MENTION_PATTERN.search(text):
        return "包含带数字的 @ 提及"
    if TOKEN_PATTERN.search(text):
        return "包含疑似访问 Token"
    if text.count("{") != text.count("}") or re.sub(PLACEHOLDER_PATTERN, "", text).find("{") >= 0:
        return "包含未闭合或嵌套花括号"
    if "}" in re.sub(PLACEHOLDER_PATTERN, "", text):
        return "包含未闭合或嵌套花括号"

    placeholders = {match.group(1) for match in PLACEHOLDER_PATTERN.finditer(text)}
    unknown_placeholders = placeholders - {"k", "v", "origin", "food"}
    if unknown_placeholders:
        return f"包含未知占位符: {', '.join(sorted(unknown_placeholders))}"
    if is_pvp and not {"k", "v"}.issubset(placeholders):
        return "PvP 文案必须同时包含 {k} 与 {v}"
    if not is_pvp and ({"k", "v"} & placeholders):
        return "普通烤猪文案不能包含 {k} 或 {v}"
    return None


def build_clean_library(
    source: dict[str, Any],
    *,
    exclusion_hashes: set[str],
) -> tuple[dict[str, dict[str, list[str]]], BuildReport]:
    """清洗本地 RollPig 文案库并返回可发布快照；私有 ID 只在对应资源包启用时可达。"""

    report = BuildReport(source_origins=len(source))
    report.source_pairs = sum(len(targets) for targets in source.values() if isinstance(targets, dict))
    report.source_texts = sum(
        len(texts)
        for targets in source.values()
        if isinstance(targets, dict)
        for texts in targets.values()
        if isinstance(texts, list)
    )
    output: dict[str, dict[str, list[str]]] = {}

    for raw_origin_id, raw_targets in source.items():
        origin_id = str(raw_origin_id)
        if not PIG_ID_PATTERN.fullmatch(origin_id):
            report.rejected.append(RejectedText(origin_id, "", "", "原始小猪 ID 非法"))
            continue
        if not isinstance(raw_targets, dict):
            report.rejected.append(RejectedText(origin_id, "", "", "第二层必须是 object"))
            continue

        for raw_target_id, raw_texts in raw_targets.items():
            target_id = str(raw_target_id)
            is_pvp = target_id.endswith("_pvp")
            food_id = target_id[:-4] if is_pvp else target_id
            if not PIG_ID_PATTERN.fullmatch(food_id):
                report.rejected.append(RejectedText(origin_id, target_id, "", "熟食小猪 ID 非法"))
                continue
            if not isinstance(raw_texts, list):
                report.rejected.append(RejectedText(origin_id, target_id, "", "文案集合必须是 list"))
                continue

            accepted: list[str] = []
            seen_texts: set[str] = set()
            for raw_text in raw_texts:
                if not isinstance(raw_text, str):
                    report.rejected.append(RejectedText(origin_id, target_id, repr(raw_text), "文案必须是字符串"))
                    continue

                normalized = normalize_roast_text(raw_text)
                if normalized != raw_text:
                    report.changed.append(ChangedText(origin_id, target_id, raw_text, normalized))
                rejection_reason = _text_rejection_reason(normalized, is_pvp=is_pvp)
                if rejection_reason is not None:
                    report.rejected.append(RejectedText(origin_id, target_id, raw_text, rejection_reason))
                    continue

                identity = roast_text_identity(normalized)
                if identity in exclusion_hashes:
                    report.excluded_texts += 1
                    continue
                if identity in seen_texts:
                    report.duplicate_texts += 1
                    continue
                if len(accepted) >= ROAST_MAX_TEXTS_PER_PAIR:
                    report.rejected.append(
                        RejectedText(
                            origin_id,
                            target_id,
                            raw_text,
                            f"同一组合超过 {ROAST_MAX_TEXTS_PER_PAIR} 条上限",
                        )
                    )
                    continue

                seen_texts.add(identity)
                accepted.append(normalized)
                if len(normalized) > ROAST_LONG_TEXT_WARNING:
                    report.long_texts.append(
                        {
                            "origin_id": origin_id,
                            "target_id": target_id,
                            "length": len(normalized),
                            "text": normalized,
                        }
                    )

            if accepted:
                output.setdefault(origin_id, {})[target_id] = accepted

    report.output_origins = len(output)
    report.output_pairs = sum(len(targets) for targets in output.values())
    report.output_texts = sum(len(texts) for targets in output.values() for texts in targets.values())
    if report.output_origins > ROAST_MAX_ORIGINS:
        raise ValueError(f"输出原始小猪数量超过上限: {report.output_origins}/{ROAST_MAX_ORIGINS}")
    if report.output_pairs > ROAST_MAX_PAIRS:
        raise ValueError(f"输出组合数量超过上限: {report.output_pairs}/{ROAST_MAX_PAIRS}")
    if report.output_texts > ROAST_MAX_TEXTS:
        raise ValueError(f"输出文案数量超过上限: {report.output_texts}/{ROAST_MAX_TEXTS}")
    return output, report


def validate_roast_library_data(data: Any) -> list[str]:
    """供仓库校验器和客户端测试复用，返回完整错误列表而不是首错即停。"""

    errors: list[str] = []
    if not isinstance(data, dict):
        return ["顶层必须是 object"]

    origin_count = len(data)
    pair_count = 0
    text_count = 0
    if origin_count > ROAST_MAX_ORIGINS:
        errors.append(f"原始小猪数量超过上限: {origin_count}/{ROAST_MAX_ORIGINS}")

    for origin_id, targets in data.items():
        if not isinstance(origin_id, str) or PIG_ID_PATTERN.fullmatch(origin_id) is None:
            errors.append(f"原始小猪 ID 非法: {origin_id!r}")
            continue
        if not isinstance(targets, dict):
            errors.append(f"{origin_id} 的第二层必须是 object")
            continue
        pair_count += len(targets)
        for target_id, texts in targets.items():
            if not isinstance(target_id, str):
                errors.append(f"{origin_id} 存在非字符串目标 ID")
                continue
            is_pvp = target_id.endswith("_pvp")
            food_id = target_id[:-4] if is_pvp else target_id
            if PIG_ID_PATTERN.fullmatch(food_id) is None:
                errors.append(f"目标小猪 ID 非法: {origin_id}/{target_id}")
                continue
            if not isinstance(texts, list):
                errors.append(f"{origin_id}/{target_id} 必须是 list")
                continue
            if len(texts) > ROAST_MAX_TEXTS_PER_PAIR:
                errors.append(
                    f"{origin_id}/{target_id} 文案数超过上限: {len(texts)}/{ROAST_MAX_TEXTS_PER_PAIR}"
                )
            seen: set[str] = set()
            text_count += len(texts)
            for index, text in enumerate(texts):
                if not isinstance(text, str):
                    errors.append(f"{origin_id}/{target_id}[{index}] 必须是字符串")
                    continue
                reason = _text_rejection_reason(text, is_pvp=is_pvp)
                if reason is not None:
                    errors.append(f"{origin_id}/{target_id}[{index}] {reason}")
                identity = roast_text_identity(text)
                if identity in seen:
                    errors.append(f"{origin_id}/{target_id}[{index}] 与前文重复")
                seen.add(identity)

    if pair_count > ROAST_MAX_PAIRS:
        errors.append(f"组合数量超过上限: {pair_count}/{ROAST_MAX_PAIRS}")
    if text_count > ROAST_MAX_TEXTS:
        errors.append(f"文案总数超过上限: {text_count}/{ROAST_MAX_TEXTS}")
    return errors


# ================================ 报告、清单与原子发布 ================================ #


def _report_payload(report: BuildReport) -> dict[str, Any]:
    return {
        "statistics": {
            "source_origins": report.source_origins,
            "source_pairs": report.source_pairs,
            "source_texts": report.source_texts,
            "output_origins": report.output_origins,
            "output_pairs": report.output_pairs,
            "output_texts": report.output_texts,
            "duplicate_texts": report.duplicate_texts,
            "excluded_texts": report.excluded_texts,
            "rejected_texts": len(report.rejected),
            "changed_texts": len(report.changed),
            "long_texts": len(report.long_texts),
        },
        "rejected": [item.__dict__ for item in report.rejected],
        "changed": [item.__dict__ for item in report.changed],
        "long_texts": report.long_texts,
    }


def _write_review_markdown(path: Path, report: BuildReport) -> None:
    lines = [
        "# 共享烤猪文案导出审核报告",
        "",
        f"- 来源文案：{report.source_texts}",
        f"- 输出文案：{report.output_texts}",
        f"- 自动规范化：{len(report.changed)}",
        f"- 稳定去重：{report.duplicate_texts}",
        f"- 长期排除：{report.excluded_texts}",
        f"- 硬拒绝：{len(report.rejected)}",
        f"- 超过 {ROAST_LONG_TEXT_WARNING} 字符待复核：{len(report.long_texts)}",
        "",
        "## 硬拒绝项",
        "",
    ]
    if not report.rejected:
        lines.append("- 无")
    else:
        for item in report.rejected:
            escaped = item.text.replace("\n", " ").replace("`", "ˋ")
            lines.append(f"- `{item.origin_id}/{item.target_id}`：{item.reason}；`{escaped}`")

    lines.extend(["", "## 自动规范化项", ""])
    if not report.changed:
        lines.append("- 无")
    else:
        for item in report.changed:
            before = item.before.replace("\n", " ").replace("`", "ˋ")
            after = item.after.replace("\n", " ").replace("`", "ˋ")
            lines.append(f"- `{item.origin_id}/{item.target_id}`：`{before}` → `{after}`")

    lines.extend(["", f"## 超过 {ROAST_LONG_TEXT_WARNING} 字符", ""])
    if not report.long_texts:
        lines.append("- 无")
    else:
        for item in report.long_texts:
            escaped = str(item["text"]).replace("\n", " ").replace("`", "ˋ")
            lines.append(
                f"- `{item['origin_id']}/{item['target_id']}`（{item['length']} 字符）：`{escaped}`"
            )
    write_utf8_lf(path, "\n".join(lines) + "\n")


def _build_candidate(
    candidate_dir: Path,
    *,
    library: dict[str, dict[str, list[str]]],
    version: str,
    min_plugin_version: str,
    created_at: str,
) -> None:
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True)

    library_path = candidate_dir / "roast_library.json"
    library_bytes = (json.dumps(library, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(library_bytes) > ROAST_LIBRARY_MAX_SIZE:
        raise ValueError(
            f"共享文案正文超过 {ROAST_LIBRARY_MAX_SIZE} 字节上限: {len(library_bytes)}"
        )
    library_path.write_bytes(library_bytes)

    statistics = {
        "origin_count": len(library),
        "pair_count": sum(len(targets) for targets in library.values()),
        "text_count": sum(len(texts) for targets in library.values() for texts in targets.values()),
    }
    manifest = {
        "schema_version": 1,
        "package_type": "roast_library",
        "resource_version": version,
        "min_plugin_version": min_plugin_version,
        "roast_library": {
            "path": "roast_library.json",
            "size": len(library_bytes),
            "sha256": sha256_bytes(library_bytes),
        },
        "statistics": statistics,
        "created_at": created_at,
    }
    write_utf8_lf(candidate_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def _activate_candidate(candidate_dir: Path, output_dir: Path, report_dir: Path) -> None:
    """在同一磁盘上用目录替换发布候选包，失败时恢复原目录。"""

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    previous_dir = report_dir / "previous-package"
    if previous_dir.exists():
        shutil.rmtree(previous_dir)
    if output_dir.exists():
        os.replace(output_dir, previous_dir)
    try:
        os.replace(candidate_dir, output_dir)
    except Exception:
        if previous_dir.exists() and not output_dir.exists():
            os.replace(previous_dir, output_dir)
        raise


def _parse_args() -> argparse.Namespace:
    default_repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build a reviewed RollPig shared roast text package")
    parser.add_argument("--source", required=True, help="local RollPig roast_library.json source path")
    parser.add_argument("--repo-root", default=str(default_repo_root), help="rollpig-resources repository root")
    parser.add_argument("--output", default="", help="output package directory; defaults to <repo>/rollpig-roasts")
    parser.add_argument("--version", required=True, help="resource version, e.g. roasts-2026-07-29.1")
    parser.add_argument("--min-plugin-version", default="0.10.0")
    parser.add_argument("--report-dir", required=True, help="temporary review report directory")
    parser.add_argument("--dry-run", action="store_true", help="build candidate and reports without replacing output")
    return parser.parse_args()


def main() -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    source_path = Path(args.source).resolve()
    output_dir = Path(args.output).resolve() if args.output else repo_root / "rollpig-roasts"
    report_dir = Path(args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    if not re.fullmatch(r"roasts-\d{4}-\d{2}-\d{2}\.\d+", args.version):
        raise ValueError("version 必须使用 roasts-YYYY-MM-DD.N 格式")

    source = read_json(source_path, dict)
    exclusion_hashes = _load_exclusion_hashes(repo_root / "tools" / "roast_library_exclusions.json")
    library, report = build_clean_library(
        source,
        exclusion_hashes=exclusion_hashes,
    )
    validation_errors = validate_roast_library_data(library)
    if validation_errors:
        raise ValueError("清洗结果仍不合法:\n- " + "\n- ".join(validation_errors[:50]))

    report_payload = _report_payload(report)
    write_utf8_lf(
        report_dir / "roast_library_report.json",
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n",
    )
    _write_review_markdown(report_dir / "roast_library_review.md", report)

    candidate_dir = report_dir / "candidate-package"
    _build_candidate(
        candidate_dir,
        library=library,
        version=args.version,
        min_plugin_version=args.min_plugin_version,
        created_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    )
    package_readme = output_dir / "README.md"
    if package_readme.is_file():
        # README 属于人工维护说明，不应在每次重建正文快照时被目录替换误删。
        shutil.copy2(package_readme, candidate_dir / package_readme.name)
    if not args.dry_run:
        _activate_candidate(candidate_dir, output_dir, report_dir)

    print(
        "built shared roast library: "
        f"version={args.version} source={report.source_texts} output={report.output_texts} "
        f"rejected={len(report.rejected)} normalized={len(report.changed)} "
        f"dry_run={args.dry_run} output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
