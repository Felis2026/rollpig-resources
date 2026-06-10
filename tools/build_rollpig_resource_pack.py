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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_pigs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
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
    shutil.copy2(source_rules, target)
    return {
        "pig_rules": {
            "path": "pig_rules.json",
            "size": target.stat().st_size,
            "sha256": sha256_file(target),
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RollPig static resource pack")
    parser.add_argument("--base-resource-dir", required=True, help="plugin resource directory containing pig.json/image/")
    parser.add_argument("--extra-pig-json", action="append", default=[], help="extra pig json to append")
    parser.add_argument("--extra-image-dir", action="append", default=[], help="extra image directory")
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
    pig_json_path.write_text(json.dumps(pigs, ensure_ascii=False, indent=4), encoding="utf-8")

    image_items = copy_images(pigs, image_dirs, output_dir / "images")
    optional_files = copy_optional_rules(base_resource_dir / "pig_rules.json", output_dir)

    manifest = {
        "schema_version": 1,
        "resource_version": version,
        "min_plugin_version": "0.6.1",
        "pig_json": {
            "path": "pig.json",
            "size": pig_json_path.stat().st_size,
            "sha256": sha256_file(pig_json_path),
        },
        "images": image_items,
        "optional_files": optional_files,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"built rollpig resource pack: version={version} pigs={len(pigs)} output={output_dir}")


if __name__ == "__main__":
    main()
