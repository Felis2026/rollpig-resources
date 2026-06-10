from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_meta(path: Path, relative_path: str) -> dict[str, object]:
    return {
        "path": relative_path,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Update RollPig private overlay manifest")
    parser.add_argument(
        "--pack-dir",
        default="rollpig-pjsk",
        help="private overlay directory relative to repository root",
    )
    parser.add_argument(
        "--version",
        default="",
        help="resource version; default keeps existing manifest version",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    pack_dir = (repo_root / args.pack_dir).resolve()
    manifest_path = pack_dir / "manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}

    pig_json_path = pack_dir / "pig.json"
    pig_rules_path = pack_dir / "pig_rules.json"
    pig_overrides_path = pack_dir / "pig_overrides.json"
    images_dir = pack_dir / "images"
    pigs = read_json(pig_json_path)

    if not isinstance(pigs, list):
        raise ValueError(f"pig.json must be list: {pig_json_path}")

    # ================================ Manifest基础信息 ================================ #
    # 私有包必须声明 overlay=true，插件会据此拒绝误把全量包当私有包加载。
    resource_version = args.version or str(manifest.get("resource_version") or "")
    if not resource_version:
        resource_version = "pjsk-" + dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d.%H%M%S")

    manifest.update(
        {
            "schema_version": 1,
            "overlay": True,
            "overlay_name": manifest.get("overlay_name") or pack_dir.name,
            "resource_version": resource_version,
            "min_plugin_version": "0.6.2",
            "base_manifest_url": manifest.get("base_manifest_url")
            or "https://pig.felislab.cc/resources/rollpig/manifest.json",
            "allow_override": bool(manifest.get("allow_override", False)),
            "pig_json": file_meta(pig_json_path, "pig.json"),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    )

    # ================================ 可选规则文件 ================================ #
    optional_files: dict[str, object] = {}
    if pig_rules_path.exists():
        optional_files["pig_rules"] = file_meta(pig_rules_path, "pig_rules.json")
    if pig_overrides_path.exists():
        optional_files["pig_overrides"] = file_meta(pig_overrides_path, "pig_overrides.json")
    manifest["optional_files"] = optional_files

    # ================================ 图片清单 ================================ #
    image_items: list[dict[str, object]] = []
    for pig in pigs:
        if not isinstance(pig, dict):
            raise ValueError("pig.json contains invalid item")
        pig_id = str(pig.get("id") or "")
        image_path = images_dir / f"{pig_id}.png"
        if not image_path.exists():
            raise FileNotFoundError(f"missing private image: {image_path}")
        image_items.append(
            {
                "id": pig_id,
                "filename": image_path.name,
                **file_meta(image_path, f"images/{image_path.name}"),
            }
        )
    manifest["images"] = image_items

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated private manifest: {manifest_path} pigs={len(pigs)} version={resource_version}")


if __name__ == "__main__":
    main()
