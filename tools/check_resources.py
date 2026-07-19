from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


PIG_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RULE_KEYS = (
    "food_pigs",
    "human_pigs",
    "eaten_pigs",
    "sold_pigs",
    "roast_excluded_pigs",
)
TEXT_FIELDS = ("name", "description", "analysis")

# 这些上限与 RollPig Plus 的下载和渲染保护保持一致。这里提前拒绝，
# 避免一个能合并、却必然被客户端拒绝或导致 GIF 解码峰值过高的资源包进入生产。
MANIFEST_MAX_SIZE = 1 * 1024 * 1024
PIG_JSON_MAX_SIZE = 2 * 1024 * 1024
RULES_JSON_MAX_SIZE = 256 * 1024
FILE_MAX_SIZE = 10 * 1024 * 1024
PACKAGE_MAX_SIZE = 128 * 1024 * 1024
PACKAGE_MAX_IMAGES = 500
PACKAGE_MAX_FILES = 700
GIF_MAX_SOURCE_FRAMES = 600
GIF_MAX_DECODE_WORK_PIXELS = 16_000_000
GIF_OUTPUT_FRAME_WARNING = 60


# ================================ 基础模型与问题报告 ================================ #


@dataclass(frozen=True)
class PackSpec:
    name: str
    overlay: bool
    allowed_image_suffixes: tuple[str, ...]


PACK_SPECS = (
    PackSpec("rollpig", False, (".png",)),
    PackSpec("rollpig-gif", True, (".gif", ".png")),
    PackSpec("rollpig-pjsk", True, (".gif", ".png")),
)


@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    message: str


@dataclass
class PackState:
    spec: PackSpec
    version: str = ""
    pig_ids: set[str] = field(default_factory=set)
    override_ids: set[str] = field(default_factory=set)
    image_count: int = 0
    gif_count: int = 0
    manifest_bytes: int = 0


class DuplicateJsonKeyError(ValueError):
    pass


class Reporter:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.issues: list[Issue] = []

    @property
    def error_count(self) -> int:
        return sum(issue.level == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.level == "warning" for issue in self.issues)

    def display_path(self, path: Path | str) -> str:
        if isinstance(path, str):
            return path.replace("\\", "/")
        try:
            return path.resolve().relative_to(self.repo_root).as_posix()
        except ValueError:
            return str(path)

    def error(self, path: Path | str, message: str) -> None:
        self.issues.append(Issue("error", self.display_path(path), message))

    def warning(self, path: Path | str, message: str) -> None:
        self.issues.append(Issue("warning", self.display_path(path), message))

    def emit(self) -> None:
        github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
        for issue in self.issues:
            if github_actions:
                message = issue.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                path = issue.path.replace("%", "%25").replace(",", "%2C")
                print(f"::{issue.level} file={path}::{message}")
            else:
                print(f"{issue.level.upper():7} {issue.path}: {issue.message}")


# ================================ JSON与业务数据校验 ================================ #


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"JSON 对象存在重复字段: {key}")
        result[key] = value
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(
    path: Path,
    reporter: Reporter,
    *,
    expected_type: type,
    required: bool = True,
    max_size: int | None = None,
) -> Any | None:
    """读取一个 UTF-8 JSON 文件，累计编码、重复键、类型和大小问题。"""

    if not path.is_file():
        if required:
            reporter.error(path, "文件不存在")
        return None
    if path.is_symlink():
        reporter.error(path, "资源 JSON 不能是符号链接")
        return None

    size = path.stat().st_size
    if max_size is not None and size > max_size:
        reporter.error(path, f"文件大小 {size} B 超过上限 {max_size} B")

    raw = path.read_bytes()
    if b"\r" in raw:
        # manifest 校验的是原始字节，而 GitHub Linux 检出遵循 .gitattributes 的 LF；
        # 本地若按 CRLF 生成清单，提交后大小和哈希会立刻失效。
        reporter.error(path, "资源 JSON 必须使用 LF 换行；请先规范化后重新生成 manifest")
    if raw.startswith(b"\xef\xbb\xbf"):
        # 客户端兼容 BOM，但仓库继续提示，避免其他 JSON 工具或构建脚本读取失败。
        reporter.warning(path, "文件包含 UTF-8 BOM，建议下次编辑时保存为无 BOM UTF-8")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        reporter.error(path, f"不是有效 UTF-8: {error}")
        return None
    if "\ufffd" in text:
        reporter.error(path, "文本包含 Unicode 替换字符，疑似发生过乱码损坏")
    try:
        data = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, DuplicateJsonKeyError) as error:
        reporter.error(path, f"JSON 解析失败: {error}")
        return None
    if not isinstance(data, expected_type):
        reporter.error(path, f"顶层类型必须是 {expected_type.__name__}，实际为 {type(data).__name__}")
        return None
    return data


def _valid_pig_id(value: Any) -> bool:
    return isinstance(value, str) and PIG_ID_PATTERN.fullmatch(value) is not None


def _validate_pigs(path: Path, data: list[Any] | None, reporter: Reporter) -> set[str]:
    """校验 pig.json 的 ID 和必填文案，返回当前包可用的 ID 集合。"""

    ids: set[str] = set()
    if data is None:
        return ids
    for index, item in enumerate(data):
        label = f"第 {index + 1} 项"
        if not isinstance(item, dict):
            reporter.error(path, f"{label}必须是 JSON object")
            continue
        pig_id = item.get("id")
        if not _valid_pig_id(pig_id):
            reporter.error(path, f"{label}的 id 非法: {pig_id!r}")
            continue
        if pig_id in ids:
            reporter.error(path, f"存在重复小猪 ID: {pig_id}")
        ids.add(pig_id)

        for field_name in TEXT_FIELDS:
            value = item.get(field_name)
            if not isinstance(value, str) or not value.strip():
                reporter.error(path, f"小猪 {pig_id} 的 {field_name} 必须是非空字符串")
        unknown_fields = sorted(set(item) - {"id", *TEXT_FIELDS})
        if unknown_fields:
            reporter.warning(path, f"小猪 {pig_id} 含未登记字段: {', '.join(unknown_fields)}")
    return ids


def _validate_overrides(
    path: Path,
    data: list[Any] | None,
    reporter: Reporter,
    *,
    prior_ids: set[str],
) -> set[str]:
    """校验 Overlay 覆盖项，并返回合法覆盖目标 ID。"""

    ids: set[str] = set()
    if data is None:
        return ids
    for index, item in enumerate(data):
        label = f"第 {index + 1} 项"
        if not isinstance(item, dict):
            reporter.error(path, f"{label}必须是 JSON object")
            continue
        pig_id = item.get("id")
        if not _valid_pig_id(pig_id):
            reporter.error(path, f"{label}的 id 非法: {pig_id!r}")
            continue
        if pig_id in ids:
            reporter.error(path, f"存在重复覆盖 ID: {pig_id}")
        ids.add(pig_id)
        if pig_id not in prior_ids:
            reporter.error(path, f"覆盖目标在前序资源包中不存在: {pig_id}")
        if len(item) == 1:
            reporter.warning(path, f"覆盖项 {pig_id} 没有任何要修改的字段")
        for field_name in TEXT_FIELDS:
            if field_name in item and (not isinstance(item[field_name], str) or not item[field_name].strip()):
                reporter.error(path, f"覆盖项 {pig_id} 的 {field_name} 必须是非空字符串")
        unknown_fields = sorted(set(item) - {"id", *TEXT_FIELDS})
        if unknown_fields:
            reporter.warning(path, f"覆盖项 {pig_id} 含未登记字段: {', '.join(unknown_fields)}")
    return ids


def _validate_rules(
    path: Path,
    data: dict[str, Any] | None,
    reporter: Reporter,
    *,
    available_ids: set[str],
) -> None:
    """检查规则字段类型、重复值以及对当前有效小猪 ID 的引用。"""

    if data is None:
        return
    if "schema_version" in data and data["schema_version"] != 1:
        reporter.error(path, "schema_version 当前只能为 1")
    unknown_keys = sorted(set(data) - {"schema_version", *RULE_KEYS})
    if unknown_keys:
        reporter.warning(path, f"存在客户端未登记的规则字段: {', '.join(unknown_keys)}")

    for key in RULE_KEYS:
        values = data.get(key, [])
        if not isinstance(values, list):
            reporter.error(path, f"{key} 必须是 list")
            continue
        seen: set[str] = set()
        for value in values:
            if not _valid_pig_id(value):
                reporter.error(path, f"{key} 包含非法 ID: {value!r}")
                continue
            if value in seen:
                reporter.error(path, f"{key} 重复列出 ID: {value}")
            seen.add(value)
            if value not in available_ids:
                reporter.error(path, f"{key} 指向不存在的小猪 ID: {value}")


# ================================ Manifest与图片校验 ================================ #


def _validate_manifest_header(
    path: Path,
    manifest: dict[str, Any] | None,
    reporter: Reporter,
    spec: PackSpec,
    *,
    has_overrides: bool,
) -> str:
    """校验 manifest 的包类型、版本和时间等头部字段，返回资源版本。"""

    if manifest is None:
        return ""
    if manifest.get("schema_version") != 1:
        reporter.error(path, "schema_version 当前只能为 1")

    version = manifest.get("resource_version")
    if not isinstance(version, str) or not version.strip():
        reporter.error(path, "resource_version 必须是非空字符串")
        version = ""

    min_plugin_version = manifest.get("min_plugin_version")
    if not isinstance(min_plugin_version, str) or not min_plugin_version.strip():
        reporter.error(path, "min_plugin_version 必须是非空字符串")

    created_at = manifest.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        reporter.error(path, "created_at 必须是带时区的 ISO 8601 时间")
    else:
        try:
            parsed = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                reporter.error(path, "created_at 必须包含时区")
        except ValueError:
            reporter.error(path, f"created_at 不是有效 ISO 8601 时间: {created_at}")

    if spec.overlay:
        if manifest.get("overlay") is not True:
            reporter.error(path, "Overlay 包必须声明 overlay=true")
        if manifest.get("overlay_name") != spec.name:
            reporter.error(path, f"overlay_name 必须为 {spec.name!r}")
        base_url = manifest.get("base_manifest_url")
        if not isinstance(base_url, str) or not base_url.startswith("https://"):
            reporter.error(path, "base_manifest_url 必须是 HTTPS URL")
        allow_override = manifest.get("allow_override")
        if not isinstance(allow_override, bool):
            reporter.error(path, "allow_override 必须是 boolean")
        elif has_overrides and not allow_override:
            reporter.error(path, "存在 pig_overrides.json 覆盖项时必须声明 allow_override=true")
    elif "overlay" in manifest and manifest.get("overlay") is not False:
        reporter.error(path, "公有全量包不能声明为 Overlay")
    return str(version or "")


def _safe_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if "\\" in value or value.startswith("/"):
        return None
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        return None
    return pure_path.as_posix()


def _validate_file_meta(
    *,
    pack_dir: Path,
    manifest_path: Path,
    meta: Any,
    label: str,
    expected_path: str,
    reporter: Reporter,
    referenced_paths: set[str],
    max_size: int,
) -> tuple[Path | None, int]:
    """核对一个 manifest 文件条目的安全路径、大小和 SHA256。"""

    if not isinstance(meta, dict):
        reporter.error(manifest_path, f"{label} 必须是 JSON object")
        return None, 0
    relative_path = _safe_manifest_path(meta.get("path"))
    if relative_path is None:
        reporter.error(manifest_path, f"{label}.path 非法: {meta.get('path')!r}")
        return None, 0
    if relative_path != expected_path:
        reporter.error(manifest_path, f"{label}.path 应为 {expected_path!r}，实际为 {relative_path!r}")
    if relative_path in referenced_paths:
        reporter.error(manifest_path, f"manifest 重复引用路径: {relative_path}")
    referenced_paths.add(relative_path)

    size = meta.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        reporter.error(manifest_path, f"{label}.size 必须是非负整数")
        expected_size = 0
    else:
        expected_size = size
        if size > max_size:
            reporter.error(manifest_path, f"{label} 声明大小 {size} B 超过单文件上限 {max_size} B")

    expected_hash = meta.get("sha256")
    if not isinstance(expected_hash, str) or SHA256_PATTERN.fullmatch(expected_hash) is None:
        reporter.error(manifest_path, f"{label}.sha256 必须是 64 位小写十六进制")
        expected_hash = ""

    file_path = pack_dir.joinpath(*PurePosixPath(relative_path).parts)
    if not file_path.is_file():
        reporter.error(file_path, f"manifest 引用的文件不存在（{label}）")
        return None, expected_size
    if file_path.is_symlink():
        reporter.error(file_path, "manifest 不能引用符号链接")
        return None, expected_size

    actual_size = file_path.stat().st_size
    if isinstance(size, int) and not isinstance(size, bool) and actual_size != size:
        reporter.error(file_path, f"文件大小与 manifest 不符: manifest={size}, actual={actual_size}")
    actual_hash = _sha256_file(file_path)
    if expected_hash and actual_hash != expected_hash:
        reporter.error(file_path, f"SHA256 与 manifest 不符: manifest={expected_hash}, actual={actual_hash}")
    return file_path, actual_size


def _validate_image_content(path: Path, reporter: Reporter) -> tuple[bool, int]:
    """逐帧解码图片并检查格式、尺寸、透明度和 GIF 工作量预算。"""

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        reporter.error("tools/check_resources.py", "缺少 Pillow，无法解码校验图片；请先安装 Pillow>=12,<13")
        return False, 0

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as probe:
                probe.verify()
            with Image.open(path) as image:
                detected_format = str(image.format or "").upper()
                width, height = image.size
                frame_count = int(getattr(image, "n_frames", 1) or 1)
                has_transparency = "A" in image.getbands() or "transparency" in image.info
                pixel_frames = 0
                total_duration = 0
                for frame_index in range(frame_count):
                    image.seek(frame_index)
                    image.load()
                    pixel_frames += image.width * image.height
                    duration = image.info.get("duration", 0)
                    if isinstance(duration, (int, float)) and duration > 0:
                        total_duration += int(duration)
    except (
        EOFError,
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        reporter.error(path, f"图片无法完整解码: {error}")
        return False, 0

    suffix_format = {".png": "PNG", ".gif": "GIF"}.get(path.suffix.lower(), "")
    if detected_format != suffix_format:
        # 现有仓库有一个历史 WEBP 文件使用 .png 后缀，Pillow 客户端可读取；先警告，
        # 不让新增 CI 因历史素材立即失效。后续替换素材时应一并规范格式。
        reporter.warning(path, f"文件内容格式为 {detected_format or '未知'}，与后缀 {path.suffix.lower()} 不一致")
    if (width, height) != (240, 240):
        reporter.warning(path, f"图片尺寸为 {width}x{height}，推荐使用 240x240")
    if not has_transparency:
        reporter.warning(path, "图片未检测到透明通道")

    is_gif = path.suffix.lower() == ".gif"
    if not is_gif and frame_count > 1:
        reporter.error(path, f"PNG 含 {frame_count} 帧；动态资源必须放在 GIF Overlay 并使用 .gif")
    if is_gif:
        if frame_count > GIF_MAX_SOURCE_FRAMES:
            reporter.error(path, f"GIF 源帧数 {frame_count} 超过硬上限 {GIF_MAX_SOURCE_FRAMES}")
        elif frame_count > GIF_OUTPUT_FRAME_WARNING:
            reporter.warning(path, f"GIF 含 {frame_count} 帧，客户端会在完整周期内均匀压缩到最多 60 帧")
        if pixel_frames > GIF_MAX_DECODE_WORK_PIXELS:
            reporter.error(
                path,
                f"GIF 解码预算 {pixel_frames} 像素帧超过上限 {GIF_MAX_DECODE_WORK_PIXELS}",
            )
        if frame_count > 1 and total_duration <= 0:
            reporter.warning(path, "GIF 未检测到有效帧时长，客户端可能按默认时长播放")
    return is_gif, frame_count


# ================================ 单包与跨包校验 ================================ #


def _validate_pack_tree(pack_dir: Path, reporter: Reporter) -> None:
    """拒绝符号链接和资源包根目录中的未登记文件。"""

    if not pack_dir.is_dir():
        reporter.error(pack_dir, "资源包目录不存在")
        return
    allowed_root_names = {
        "manifest.json",
        "pig.json",
        "pig_rules.json",
        "pig_overrides.json",
        "README.md",
        "images",
    }
    for path in pack_dir.rglob("*"):
        if path.is_symlink():
            reporter.error(path, "资源包中禁止使用符号链接")
    for path in pack_dir.iterdir():
        if path.name not in allowed_root_names:
            reporter.error(path, "资源包根目录含未登记文件或目录")


def _validate_manifest_files(
    *,
    state: PackState,
    pack_dir: Path,
    manifest: dict[str, Any] | None,
    reporter: Reporter,
    decode_images: bool,
) -> None:
    """核对 manifest 引用与实体文件的一一对应关系和下载预算。"""

    if manifest is None:
        return
    manifest_path = pack_dir / "manifest.json"
    referenced_paths: set[str] = set()
    total_bytes = 0
    total_files = 0

    _, actual_size = _validate_file_meta(
        pack_dir=pack_dir,
        manifest_path=manifest_path,
        meta=manifest.get("pig_json"),
        label="pig_json",
        expected_path="pig.json",
        reporter=reporter,
        referenced_paths=referenced_paths,
        max_size=PIG_JSON_MAX_SIZE,
    )
    total_bytes += actual_size
    total_files += 1

    optional_files = manifest.get("optional_files", {})
    if not isinstance(optional_files, dict):
        reporter.error(manifest_path, "optional_files 必须是 JSON object")
        optional_files = {}
    unknown_optional = sorted(set(optional_files) - {"pig_rules", "pig_overrides"})
    if unknown_optional:
        reporter.error(manifest_path, f"optional_files 含未支持条目: {', '.join(unknown_optional)}")

    for key, filename in (("pig_rules", "pig_rules.json"), ("pig_overrides", "pig_overrides.json")):
        file_path = pack_dir / filename
        meta = optional_files.get(key)
        if meta is None:
            if file_path.exists():
                reporter.error(manifest_path, f"{filename} 存在但未写入 optional_files.{key}")
            continue
        if key == "pig_overrides" and not state.spec.overlay:
            reporter.error(manifest_path, "公有包不能声明 pig_overrides")
        _, actual_size = _validate_file_meta(
            pack_dir=pack_dir,
            manifest_path=manifest_path,
            meta=meta,
            label=f"optional_files.{key}",
            expected_path=filename,
            reporter=reporter,
            referenced_paths=referenced_paths,
            max_size=RULES_JSON_MAX_SIZE,
        )
        total_bytes += actual_size
        total_files += 1

    image_items = manifest.get("images")
    if not isinstance(image_items, list):
        reporter.error(manifest_path, "images 必须是 list")
        image_items = []
    if len(image_items) > PACKAGE_MAX_IMAGES:
        reporter.error(manifest_path, f"images 条目数 {len(image_items)} 超过上限 {PACKAGE_MAX_IMAGES}")

    manifest_image_ids: set[str] = set()
    manifest_image_paths: set[str] = set()
    allowed_image_ids = state.pig_ids | state.override_ids
    for index, item in enumerate(image_items):
        label = f"images[{index}]"
        if not isinstance(item, dict):
            reporter.error(manifest_path, f"{label} 必须是 JSON object")
            continue
        pig_id = item.get("id")
        filename = item.get("filename")
        if not _valid_pig_id(pig_id):
            reporter.error(manifest_path, f"{label}.id 非法: {pig_id!r}")
            continue
        if pig_id in manifest_image_ids:
            reporter.error(manifest_path, f"images 重复列出 ID: {pig_id}")
        manifest_image_ids.add(pig_id)
        if pig_id not in allowed_image_ids:
            reporter.error(manifest_path, f"图片 {pig_id} 不属于 pig.json 或 pig_overrides.json")

        if not isinstance(filename, str) or Path(filename).name != filename:
            reporter.error(manifest_path, f"{label}.filename 必须是单个文件名")
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in state.spec.allowed_image_suffixes:
            reporter.error(manifest_path, f"{label} 使用了不支持的图片后缀: {suffix or '(空)'}")
        if Path(filename).stem != pig_id:
            reporter.error(manifest_path, f"{label}.filename 必须与 id 对应: {pig_id}")
        expected_path = f"images/{filename}"
        image_path, actual_size = _validate_file_meta(
            pack_dir=pack_dir,
            manifest_path=manifest_path,
            meta=item,
            label=label,
            expected_path=expected_path,
            reporter=reporter,
            referenced_paths=referenced_paths,
            max_size=FILE_MAX_SIZE,
        )
        manifest_image_paths.add(expected_path)
        total_bytes += actual_size
        total_files += 1
        if suffix == ".gif":
            state.gif_count += 1
        if image_path is not None and decode_images:
            _validate_image_content(image_path, reporter)

    missing_images = sorted(state.pig_ids - manifest_image_ids)
    if missing_images:
        reporter.error(manifest_path, f"以下小猪没有 manifest 图片条目: {', '.join(missing_images[:20])}")

    images_dir = pack_dir / "images"
    physical_image_paths: set[str] = set()
    if not images_dir.is_dir():
        reporter.error(images_dir, "images 目录不存在")
    else:
        for path in images_dir.rglob("*"):
            relative_path = path.relative_to(pack_dir).as_posix()
            if path.is_dir():
                if path != images_dir:
                    reporter.error(path, "images 目录不允许再嵌套子目录")
                continue
            physical_image_paths.add(relative_path)
            if path.suffix.lower() not in state.spec.allowed_image_suffixes:
                reporter.error(path, f"图片后缀不受该资源包支持: {path.suffix or '(空)'}")

    for extra_path in sorted(physical_image_paths - manifest_image_paths):
        reporter.error(pack_dir / extra_path, "图片文件存在但未写入 manifest")
    for missing_path in sorted(manifest_image_paths - physical_image_paths):
        reporter.error(pack_dir / missing_path, "manifest 图片条目没有对应实体文件")

    state.image_count = len(image_items)
    state.manifest_bytes = total_bytes
    if total_files > PACKAGE_MAX_FILES:
        reporter.error(manifest_path, f"资源文件数 {total_files} 超过上限 {PACKAGE_MAX_FILES}")
    if total_bytes > PACKAGE_MAX_SIZE:
        reporter.error(manifest_path, f"资源包总大小 {total_bytes} B 超过上限 {PACKAGE_MAX_SIZE} B")


def _validate_pack(
    repo_root: Path,
    reporter: Reporter,
    spec: PackSpec,
    *,
    prior_ids: set[str],
    decode_images: bool,
) -> PackState:
    """按真实加载顺序校验一个资源包，并生成供后续包引用的状态。"""

    pack_dir = repo_root / spec.name
    state = PackState(spec=spec)
    _validate_pack_tree(pack_dir, reporter)

    pig_path = pack_dir / "pig.json"
    rules_path = pack_dir / "pig_rules.json"
    overrides_path = pack_dir / "pig_overrides.json"
    manifest_path = pack_dir / "manifest.json"

    pigs = _read_json(pig_path, reporter, expected_type=list, max_size=PIG_JSON_MAX_SIZE)
    state.pig_ids = _validate_pigs(pig_path, pigs, reporter)
    duplicate_ids = sorted(state.pig_ids & prior_ids)
    if duplicate_ids:
        reporter.error(pig_path, f"与前序资源包重复 ID: {', '.join(duplicate_ids[:20])}")

    if spec.overlay:
        overrides = _read_json(overrides_path, reporter, expected_type=list, required=False, max_size=RULES_JSON_MAX_SIZE)
        state.override_ids = _validate_overrides(overrides_path, overrides, reporter, prior_ids=prior_ids)
    elif overrides_path.exists():
        reporter.error(overrides_path, "公有全量包不能包含 pig_overrides.json")

    rules = _read_json(rules_path, reporter, expected_type=dict, required=False, max_size=RULES_JSON_MAX_SIZE)
    _validate_rules(rules_path, rules, reporter, available_ids=prior_ids | state.pig_ids)

    manifest = _read_json(manifest_path, reporter, expected_type=dict, max_size=MANIFEST_MAX_SIZE)
    state.version = _validate_manifest_header(
        manifest_path,
        manifest,
        reporter,
        spec,
        has_overrides=bool(state.override_ids),
    )
    _validate_manifest_files(
        state=state,
        pack_dir=pack_dir,
        manifest=manifest,
        reporter=reporter,
        decode_images=decode_images,
    )
    return state


# ================================ Git历史兼容性 ================================ #


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=127,
            stdout=b"",
            stderr=b"git executable not found",
        )


def _json_from_git(repo_root: Path, revision: str, relative_path: str) -> Any | None:
    result = _git(repo_root, ["show", f"{revision}:{relative_path}"])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout.decode("utf-8-sig"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJsonKeyError):
        return None


def _validate_history(
    repo_root: Path,
    reporter: Reporter,
    states: list[PackState],
    base_ref: str,
) -> None:
    """对比已发布 Git 基线，阻止 ID 删除、迁移和漏升资源版本。"""

    resolved = _git(repo_root, ["rev-parse", "--verify", f"{base_ref}^{{commit}}"])
    if resolved.returncode != 0:
        detail = resolved.stderr.decode("utf-8", errors="replace").strip()
        reporter.error("git", f"无法解析对比基线 {base_ref!r}: {detail}")
        return
    revision = resolved.stdout.decode("ascii").strip()

    for state in states:
        pig_relative = f"{state.spec.name}/pig.json"
        old_pigs = _json_from_git(repo_root, revision, pig_relative)
        if old_pigs is not None:
            if not isinstance(old_pigs, list):
                reporter.error(pig_relative, f"基线 {base_ref} 的 pig.json 顶层不是 list，无法检查 ID 兼容性")
            else:
                old_ids = {
                    item.get("id")
                    for item in old_pigs
                    if isinstance(item, dict) and _valid_pig_id(item.get("id"))
                }
                removed_ids = sorted(old_ids - state.pig_ids)
                if removed_ids:
                    reporter.error(
                        pig_relative,
                        f"相对 {base_ref} 删除或迁移了已发布 ID: {', '.join(removed_ids[:20])}；已发布 ID 必须留在原包",
                    )

        manifest_relative = f"{state.spec.name}/manifest.json"
        old_manifest = _json_from_git(repo_root, revision, manifest_relative)
        diff = _git(repo_root, ["diff", "--name-only", "--no-renames", revision, "--", state.spec.name])
        if diff.returncode != 0:
            reporter.error(manifest_relative, f"无法读取相对 {base_ref} 的资源差异")
            continue
        changed_paths = {
            line.strip()
            for line in diff.stdout.decode("utf-8", errors="replace").splitlines()
            if line.strip() and line.strip() != f"{state.spec.name}/README.md"
        }
        if changed_paths and isinstance(old_manifest, dict):
            old_version = old_manifest.get("resource_version")
            if isinstance(old_version, str) and old_version == state.version:
                samples = ", ".join(sorted(changed_paths)[:5])
                reporter.error(
                    manifest_relative,
                    f"资源内容已变化但 resource_version 仍为 {state.version!r}: {samples}",
                )


# ================================ 命令行入口 ================================ #


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate all official RollPig resource packs")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="rollpig-resources repository root",
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help="Git revision used to reject released ID deletion and unchanged resource versions",
    )
    parser.add_argument(
        "--skip-image-decode",
        action="store_true",
        help="skip Pillow decode checks; intended only for constrained deployment hosts",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="return failure when any advisory warning exists",
    )
    return parser.parse_args()


def main() -> int:
    """运行全部包校验、输出 GitHub 注解，并以退出码表达是否可发布。"""

    # Windows 的重定向输出可能继承 GBK；统一为 UTF-8，避免本地校验日志里的中文被误解码。
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    reporter = Reporter(repo_root)
    if args.base_ref and not (repo_root / ".git").exists():
        reporter.error(repo_root, "使用 --base-ref 时 repo root 必须包含 .git")

    decode_images = not args.skip_image_decode
    if decode_images:
        try:
            import PIL  # noqa: F401
        except ImportError:
            reporter.error("tools/check_resources.py", "缺少 Pillow，无法解码校验图片；请先安装 Pillow>=12,<13")
            decode_images = False

    states: list[PackState] = []
    cumulative_ids: set[str] = set()
    for spec in PACK_SPECS:
        state = _validate_pack(
            repo_root,
            reporter,
            spec,
            prior_ids=set(cumulative_ids),
            decode_images=decode_images,
        )
        states.append(state)
        cumulative_ids.update(state.pig_ids)

    if args.base_ref:
        _validate_history(repo_root, reporter, states, args.base_ref)

    for state in states:
        print(
            f"checked {state.spec.name}: version={state.version or '(invalid)'} "
            f"pigs={len(state.pig_ids)} images={state.image_count} gifs={state.gif_count} "
            f"payload={state.manifest_bytes}B"
        )
    reporter.emit()
    print(
        f"resource validation finished: packs={len(states)} pigs={len(cumulative_ids)} "
        f"errors={reporter.error_count} warnings={reporter.warning_count}"
    )
    if reporter.error_count or (args.strict_warnings and reporter.warning_count):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
