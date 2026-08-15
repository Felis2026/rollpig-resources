from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACK_NAMES = ("rollpig", "rollpig-gif", "rollpig-pjsk", "rollpig-roasts")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取 JSON: {path}: {error}") from error


def _read_pig_count(pack_name: str) -> int:
    data = _read_json(REPOSITORY_ROOT / pack_name / "pig.json")
    if not isinstance(data, list):
        raise ValueError(f"{pack_name}/pig.json 顶层必须是数组")
    return len(data)


def _count_ex_variants() -> tuple[int, int, int]:
    data = _read_json(REPOSITORY_ROOT / "rollpig" / "pig_ex_variants.json")
    if not isinstance(data, dict) or not isinstance(data.get("pigs"), dict):
        raise ValueError("rollpig/pig_ex_variants.json 缺少 pigs object")

    ex_pigs = 0
    ex_levels = 0
    ex_variant_images = 0
    for pig_data in data["pigs"].values():
        if not isinstance(pig_data, dict) or not isinstance(pig_data.get("levels"), dict):
            raise ValueError("pig_ex_variants.json 中的 levels 必须是 object")
        levels = pig_data["levels"]
        if levels:
            ex_pigs += 1
        ex_levels += len(levels)
        ex_variant_images += sum(
            1
            for level_data in levels.values()
            if isinstance(level_data, dict) and level_data.get("image")
        )
    return ex_pigs, ex_levels, ex_variant_images


def _count_roast_library() -> tuple[int, int]:
    data = _read_json(REPOSITORY_ROOT / "rollpig-roasts" / "roast_library.json")
    if not isinstance(data, dict):
        raise ValueError("rollpig-roasts/roast_library.json 顶层必须是 object")

    pair_count = 0
    text_count = 0
    for targets in data.values():
        if not isinstance(targets, dict):
            raise ValueError("共享文案的第二层必须是 object")
        pair_count += len(targets)
        for texts in targets.values():
            if not isinstance(texts, list):
                raise ValueError("共享文案组合必须对应数组")
            text_count += len(texts)
    return pair_count, text_count


def _read_resource_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pack_name in PACK_NAMES:
        manifest = _read_json(REPOSITORY_ROOT / pack_name / "manifest.json")
        if not isinstance(manifest, dict) or not manifest.get("resource_version"):
            raise ValueError(f"{pack_name}/manifest.json 缺少 resource_version")
        versions[pack_name] = str(manifest["resource_version"])
    return versions


def build_stats() -> dict[str, Any]:
    base_pigs = _read_pig_count("rollpig")
    gif_pigs = _read_pig_count("rollpig-gif")
    pjsk_pigs = _read_pig_count("rollpig-pjsk")
    ex_pigs, ex_levels, ex_variant_images = _count_ex_variants()
    roast_pairs, roast_templates = _count_roast_library()

    image_count = 0
    for pack_name in PACK_NAMES[:3]:
        manifest = _read_json(REPOSITORY_ROOT / pack_name / "manifest.json")
        image_count += len(manifest.get("images") or [])
        image_count += len(manifest.get("variant_images") or [])

    return {
        "schema_version": 1,
        "resource_versions": _read_resource_versions(),
        "pigs": base_pigs,
        "ex_pigs": ex_pigs,
        "ex_levels": ex_levels,
        "ex_variant_images": ex_variant_images,
        "gif_pigs": gif_pigs,
        "pjsk_pigs": pjsk_pigs,
        "total_pigs": base_pigs + gif_pigs + pjsk_pigs,
        "total_images": image_count,
        "roast_pairs": roast_pairs,
        "roast_templates": roast_templates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RollPig resource statistics")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "stats.json",
        help="输出 JSON 路径，默认是仓库根目录 stats.json",
    )
    args = parser.parse_args()

    try:
        stats = build_stats()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except (OSError, ValueError) as error:
        print(f"resource stats generation failed: {error}", file=sys.stderr)
        return 1

    print(f"generated resource stats: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
