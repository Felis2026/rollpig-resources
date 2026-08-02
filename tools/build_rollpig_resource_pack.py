from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


PIG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
EX_LEVEL_KEYS = {str(level) for level in range(1, 6)}
EX_VARIANT_SUFFIXES = {".png", ".gif"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_utf8_lf(path: Path, text: str) -> None:
    """以无 BOM UTF-8 和 LF 写入文本，保证 manifest 字节哈希跨平台稳定。"""

    path.write_text(text, encoding="utf-8", newline="\n")


def read_pigs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"pig json must be a list: {path}")
    return data


def validate_pigs(pigs: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for pig in pigs:
        pig_id = str(pig.get("id") or "")
        if not PIG_ID_PATTERN.match(pig_id):
            raise ValueError(f"invalid pig id: {pig_id}")
        if pig_id in seen_ids:
            raise ValueError(f"duplicated pig id: {pig_id}")
        if not pig.get("name"):
            raise ValueError(f"missing pig name: {pig_id}")
        seen_ids.add(pig_id)


def merge_pigs(base_json: Path, extra_json_paths: list[Path]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for source in [base_json, *extra_json_paths]:
        for pig in read_pigs(source):
            pig_id = str(pig["id"])
            if pig_id in seen_ids:
                raise ValueError(f"duplicated pig id while merging: {pig_id}")
            merged.append(pig)
            seen_ids.add(pig_id)
    validate_pigs(merged)
    return merged


def copy_images(pigs: list[dict[str, Any]], image_dirs: list[Path], output_image_dir: Path) -> list[dict[str, Any]]:
    output_image_dir.mkdir(parents=True, exist_ok=True)
    image_items: list[dict[str, Any]] = []
    for pig in pigs:
        pig_id = str(pig["id"])
        filename = f"{pig_id}.png"
        source = next((image_dir / filename for image_dir in image_dirs if (image_dir / filename).exists()), None)
        if source is None:
            raise FileNotFoundError(f"missing image for pig: {pig_id}")
        target = output_image_dir / filename
        shutil.copy2(source, target)
        image_items.append(
            {
                "id": pig_id,
                "filename": filename,
                "path": f"images/{filename}",
                "size": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )
    return image_items


def copy_optional_rules(source_rules: Path | None, output_dir: Path) -> dict[str, Any]:
    if source_rules is None or not source_rules.exists():
        return {}
    target = output_dir / "pig_rules.json"
    # JSON 会进入 manifest 的字节校验；复制时统一编码与换行，不能沿用来源平台格式。
    write_utf8_lf(target, source_rules.read_text(encoding="utf-8-sig"))
    return {
        "pig_rules": {
            "path": "pig_rules.json",
            "size": target.stat().st_size,
            "sha256": sha256_file(target),
        }
    }


# ================================ EX等级差分构建 ================================ #
# 差分不是新猪，只复制增量 JSON 与图片；基础 pig.json/images 继续供旧客户端使用。


def read_ex_variants(
    path: Path,
    *,
    pig_order: list[str],
) -> tuple[dict[str, Any], list[tuple[str, int, str]]]:
    """读取并规范化 EX 差分，返回稳定排序的 JSON 和图片引用。"""

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("pig_ex_variants.json must be a schema_version=1 object")
    if set(data) - {"schema_version", "pigs"}:
        raise ValueError("pig_ex_variants.json contains unsupported root fields")
    raw_pigs = data.get("pigs")
    if not isinstance(raw_pigs, dict):
        raise ValueError("pig_ex_variants.pigs must be an object")

    pig_ids = set(pig_order)
    normalized_pigs: dict[str, Any] = {}
    image_refs: list[tuple[str, int, str]] = []
    for pig_id in pig_order:
        if pig_id not in raw_pigs:
            continue
        raw_pig = raw_pigs[pig_id]
        if not isinstance(raw_pig, dict) or set(raw_pig) != {"levels"}:
            raise ValueError(f"invalid EX variant pig entry: {pig_id}")
        raw_levels = raw_pig.get("levels")
        if not isinstance(raw_levels, dict) or not raw_levels:
            raise ValueError(f"EX variant levels must be a non-empty object: {pig_id}")

        normalized_levels: dict[str, Any] = {}
        for level_key in sorted(raw_levels, key=lambda value: int(value) if str(value).isdigit() else 999):
            if not isinstance(level_key, str) or level_key not in EX_LEVEL_KEYS:
                raise ValueError(f"invalid EX variant level: {pig_id}/{level_key}")
            raw_variant = raw_levels[level_key]
            if not isinstance(raw_variant, dict):
                raise ValueError(f"EX variant entry must be an object: {pig_id}/EX{level_key}")
            if set(raw_variant) - {"image", "description", "analysis"}:
                raise ValueError(f"EX variant contains unsupported fields: {pig_id}/EX{level_key}")
            if not set(raw_variant) & {"image", "description", "analysis"}:
                raise ValueError(
                    f"EX variant requires image, description, or analysis: {pig_id}/EX{level_key}"
                )

            level = int(level_key)
            normalized_variant: dict[str, str] = {}
            if "image" in raw_variant:
                filename = raw_variant.get("image")
                if not isinstance(filename, str) or Path(filename).name != filename or "\\" in filename:
                    raise ValueError(f"invalid EX variant image filename: {pig_id}/EX{level}")
                suffix = Path(filename).suffix
                if suffix not in EX_VARIANT_SUFFIXES or Path(filename).stem != f"{pig_id}_ex{level}":
                    raise ValueError(f"EX variant image must be named {pig_id}_ex{level}.png or .gif")
                normalized_variant["image"] = filename
                image_refs.append((pig_id, level, filename))
            for field in ("description", "analysis"):
                if field not in raw_variant:
                    continue
                value = raw_variant[field]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"EX variant {field} must be a non-empty string: {pig_id}/EX{level}")
                normalized_variant[field] = value
            normalized_levels[level_key] = normalized_variant
        normalized_pigs[pig_id] = {"levels": normalized_levels}

    unknown_pig_ids = sorted(set(raw_pigs) - pig_ids)
    if unknown_pig_ids:
        raise ValueError(f"EX variants reference unknown pig ids: {', '.join(unknown_pig_ids[:10])}")
    return {"schema_version": 1, "pigs": normalized_pigs}, image_refs


def copy_ex_variants(
    source_json: Path | None,
    *,
    pigs: list[dict[str, Any]],
    image_dirs: list[Path],
    output_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    """复制可选差分 JSON 与图片，并生成 manifest 的两组增量字段。"""

    if source_json is None:
        return {}, [], 0
    if not source_json.is_file():
        raise FileNotFoundError(f"missing EX variants json: {source_json}")

    pig_order = [str(pig["id"]) for pig in pigs]
    variants, image_refs = read_ex_variants(source_json, pig_order=pig_order)
    target_json = output_dir / "pig_ex_variants.json"
    write_utf8_lf(target_json, json.dumps(variants, ensure_ascii=False, indent=2))

    image_items: list[dict[str, Any]] = []
    output_image_dir = output_dir / "images"
    for pig_id, level, filename in image_refs:
        source = next((image_dir / filename for image_dir in image_dirs if (image_dir / filename).is_file()), None)
        if source is None:
            raise FileNotFoundError(f"missing EX variant image: {filename}")
        target = output_image_dir / filename
        if target.exists():
            raise ValueError(f"EX variant image collides with a base image: {filename}")
        shutil.copy2(source, target)
        image_items.append(
            {
                "pig_id": pig_id,
                "level": level,
                "filename": filename,
                "path": f"images/{filename}",
                "size": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )

    optional_file = {
        "pig_ex_variants": {
            "path": "pig_ex_variants.json",
            "size": target_json.stat().st_size,
            "sha256": sha256_file(target_json),
        }
    }
    variant_count = sum(len(pig["levels"]) for pig in variants["pigs"].values())
    return optional_file, image_items, variant_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RollPig static resource pack")
    parser.add_argument("--base-resource-dir", required=True, help="plugin resource directory containing pig.json/image/")
    parser.add_argument("--extra-pig-json", action="append", default=[], help="extra pig json to append")
    parser.add_argument("--extra-image-dir", action="append", default=[], help="extra image directory")
    parser.add_argument("--ex-variants-json", default="", help="optional pig_ex_variants.json to include")
    parser.add_argument("--output-dir", required=True, help="output static resource directory")
    parser.add_argument("--version", default="", help="resource version, default UTC timestamp")
    args = parser.parse_args()

    base_resource_dir = Path(args.base_resource_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    version = args.version or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d.%H%M%S")
    extra_json_paths = [Path(path).resolve() for path in args.extra_pig_json]
    image_dirs = [base_resource_dir / "image", *[Path(path).resolve() for path in args.extra_image_dir]]

    pigs = merge_pigs(base_resource_dir / "pig.json", extra_json_paths)
    pig_json_path = output_dir / "pig.json"
    write_utf8_lf(pig_json_path, json.dumps(pigs, ensure_ascii=False, indent=4))

    image_items = copy_images(pigs, image_dirs, output_dir / "images")
    optional_files = copy_optional_rules(base_resource_dir / "pig_rules.json", output_dir)
    ex_variants_json = Path(args.ex_variants_json).resolve() if args.ex_variants_json else None
    variant_optional_files, variant_image_items, variant_count = copy_ex_variants(
        ex_variants_json,
        pigs=pigs,
        image_dirs=image_dirs,
        output_dir=output_dir,
    )
    optional_files.update(variant_optional_files)

    manifest = {
        "schema_version": 1,
        "resource_version": version,
        "min_plugin_version": "0.2.0",
        "pig_json": {
            "path": "pig.json",
            "size": pig_json_path.stat().st_size,
            "sha256": sha256_file(pig_json_path),
        },
        "images": image_items,
        "optional_files": optional_files,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if ex_variants_json is not None:
        manifest["variant_images"] = variant_image_items
    write_utf8_lf(output_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(
        f"built rollpig resource pack: version={version} pigs={len(pigs)} "
        f"variants={variant_count} variant_images={len(variant_image_items)} output={output_dir}"
    )


if __name__ == "__main__":
    main()
