#!/bin/sh
set -eu

umask 022

archive_path="${1:-}"
revision="${2:-}"
expected_archive_sha256="${3:-}"
project_dir_input="${4:-}"
public_base_url="${5:-https://pig.felislab.cc/resources}"
packages="rollpig rollpig-gif rollpig-pjsk rollpig-roasts"
stats_file="stats.json"

# ================================ 输入与归档校验 ================================ #

case "$revision" in
    *[!0-9a-f]*|'')
        echo "invalid deployment revision: $revision" >&2
        exit 2
        ;;
esac
case "$expected_archive_sha256" in
    *[!0-9a-f]*|'')
        echo "invalid archive sha256" >&2
        exit 2
        ;;
esac

if [ "${#revision}" -ne 40 ] || [ "${#expected_archive_sha256}" -ne 64 ] || [ ! -f "$archive_path" ]; then
    echo "deployment package missing or checksum/revision length is invalid" >&2
    exit 2
fi
if [ ! -d "$project_dir_input/static/resources" ]; then
    echo "Cloud resource root does not exist: $project_dir_input/static/resources" >&2
    exit 2
fi
case "$public_base_url" in
    http://*|https://*) ;;
    *)
        echo "public resource base URL must use HTTP or HTTPS" >&2
        exit 2
        ;;
esac

for command_name in sha256sum tar find curl cmp sort awk python3; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "required deployment command is missing: $command_name" >&2
        exit 2
    fi
done

actual_archive_sha256=$(sha256sum "$archive_path" | awk '{print $1}')
if [ "$actual_archive_sha256" != "$expected_archive_sha256" ]; then
    echo "deployment package sha256 mismatch" >&2
    exit 2
fi

project_dir=$(CDPATH='' cd -- "$project_dir_input" && pwd -P)
resource_root="$project_dir/static/resources"
deploy_root="$project_dir/.deploy/resources"
staging_root="$deploy_root/staging"
backup_root="$deploy_root/backup"
staging_dir="$staging_root/$revision"
backup_dir="$backup_root/$revision"
archive_list="$deploy_root/archive-$revision.list"

mkdir -p "$staging_root" "$backup_root"
rm -rf "$staging_dir" "$backup_dir"
mkdir -p "$staging_dir" "$backup_dir"

if ! tar -tzf "$archive_path" > "$archive_list"; then
    echo "deployment package is not a readable tar.gz archive" >&2
    exit 2
fi
if grep -Eq '(^/|(^|/)\.\.(/|$)|\\)' "$archive_list"; then
    echo "deployment package contains unsafe path" >&2
    exit 2
fi
if grep -Ev '^(stats\.json|(rollpig|rollpig-gif|rollpig-pjsk|rollpig-roasts)(/.*)?)$' "$archive_list" >/dev/null; then
    echo "deployment package contains an unexpected top-level path" >&2
    exit 2
fi

tar --no-same-owner --no-same-permissions -xzf "$archive_path" -C "$staging_dir"
if [ -n "$(find "$staging_dir" -type l -print -quit)" ]; then
    echo "deployment package must not contain symbolic links" >&2
    exit 2
fi
for package in $packages; do
    if [ "$package" = "rollpig-roasts" ]; then
        required_paths="manifest.json roast_library.json"
    else
        required_paths="manifest.json pig.json images"
    fi
    for required_path in $required_paths; do
        if [ ! -e "$staging_dir/$package/$required_path" ]; then
            echo "deployment package missing: $package/$required_path" >&2
            exit 2
        fi
    done
done
if [ ! -f "$staging_dir/$stats_file" ]; then
    echo "deployment package missing: $stats_file" >&2
    exit 2
fi

# 资源目录由 Cloud 容器只读挂载；切换前统一权限，避免发布后宿主机可见、容器不可读。
chmod -R u=rwX,go=rX "$staging_dir"

# ================================ 原子切换与失败回滚 ================================ #

switched_packages=""
switched_stats=0

rollback_resources() {
    echo "resource deployment failed, rolling back: revision=$revision" >&2
    if [ "$switched_stats" -eq 1 ]; then
        rm -f "${resource_root:?}/$stats_file"
        if [ -e "$backup_dir/$stats_file" ]; then
            mv "$backup_dir/$stats_file" "$resource_root/$stats_file"
        fi
    fi
    for package in $switched_packages; do
        rm -rf "${resource_root:?}/$package"
        if [ -e "$backup_dir/$package" ]; then
            mv "$backup_dir/$package" "$resource_root/$package"
        fi
    done
}

# static/resources 自身是 Docker bind mount，不能整体替换；逐个原子替换其子目录，
# 容器才能立即看到新资源，同时每个 manifest 永远只对应一套完整文件。
for package in $packages; do
    if [ -e "$resource_root/$package" ]; then
        if ! mv "$resource_root/$package" "$backup_dir/$package"; then
            rollback_resources
            exit 1
        fi
    fi
    if ! mv "$staging_dir/$package" "$resource_root/$package"; then
        if [ -e "$backup_dir/$package" ]; then
            mv "$backup_dir/$package" "$resource_root/$package"
        fi
        rollback_resources
        exit 1
    fi
    switched_packages="$package $switched_packages"
done

if [ -e "$resource_root/$stats_file" ]; then
    if ! mv "$resource_root/$stats_file" "$backup_dir/$stats_file"; then
        rollback_resources
        exit 1
    fi
fi
if ! mv "$staging_dir/$stats_file" "$resource_root/$stats_file"; then
    if [ -e "$backup_dir/$stats_file" ]; then
        mv "$backup_dir/$stats_file" "$resource_root/$stats_file"
    fi
    rollback_resources
    exit 1
fi
switched_stats=1

# 查询参数用于绕开代理缓存；公网返回必须与刚切换的 manifest 字节完全一致。
for package in $packages; do
    verified_manifest="$deploy_root/verified-$revision-$package.json"
    if ! curl --fail --silent --show-error --location \
        --max-time 20 --retry 3 --retry-delay 2 \
        "${public_base_url%/}/$package/manifest.json?revision=$revision" \
        -o "$verified_manifest"; then
        rollback_resources
        exit 1
    fi
    if ! cmp -s "$resource_root/$package/manifest.json" "$verified_manifest"; then
        echo "public manifest does not match deployed file: $package" >&2
        rollback_resources
        exit 1
    fi
    rm -f "$verified_manifest"
done

verified_stats="$deploy_root/verified-$revision-$stats_file"
if ! curl --fail --silent --show-error --location \
    --max-time 20 --retry 3 --retry-delay 2 \
    "${public_base_url%/}/$stats_file?revision=$revision" \
    -o "$verified_stats"; then
    rollback_resources
    exit 1
fi
if ! cmp -s "$resource_root/$stats_file" "$verified_stats"; then
    echo "public stats file does not match deployed file" >&2
    rm -f "$verified_stats"
    rollback_resources
    exit 1
fi
rm -f "$verified_stats"

# ================================ EX差分公网抽样 ================================ #
# manifest 本身一致仍不足以证明新增静态文件可访问；在备份清理前校验差分 JSON，
# 并固定抽取首、中、末三张差分图，失败时沿用同一回滚路径。
variant_checks="$deploy_root/variant-checks-$revision.txt"
if ! python3 - "$resource_root/rollpig/manifest.json" > "$variant_checks" <<'PY'
import json
import re
import sys
from pathlib import Path, PurePosixPath


manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
optional_files = manifest.get("optional_files") or {}
variants_meta = optional_files.get("pig_ex_variants") if isinstance(optional_files, dict) else None


def emit(meta: object) -> None:
    if not isinstance(meta, dict):
        raise ValueError("EX variant manifest entry must be an object")
    relative_path = meta.get("path")
    sha256 = meta.get("sha256")
    if not isinstance(relative_path, str) or not relative_path or any(char.isspace() for char in relative_path):
        raise ValueError("EX variant path is invalid")
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ValueError("EX variant path is unsafe")
    if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        raise ValueError("EX variant sha256 is invalid")
    print(relative_path, sha256)


if variants_meta is not None:
    emit(variants_meta)
    variant_images = manifest.get("variant_images") or []
    if not isinstance(variant_images, list):
        raise ValueError("variant_images must be a list")
    if len(variant_images) <= 3:
        samples = variant_images
    else:
        samples = [variant_images[0], variant_images[len(variant_images) // 2], variant_images[-1]]
    for item in samples:
        emit(item)
PY
then
    rollback_resources
    exit 1
fi

sample_number=0
while read -r relative_path expected_sha256; do
    if [ -z "$relative_path" ]; then
        continue
    fi
    sample_number=$((sample_number + 1))
    verified_asset="$deploy_root/verified-$revision-variant-$sample_number"
    if ! curl --fail --silent --show-error --location \
        --max-time 20 --retry 3 --retry-delay 2 \
        "${public_base_url%/}/rollpig/$relative_path?revision=$revision" \
        -o "$verified_asset"; then
        rollback_resources
        exit 1
    fi
    actual_sha256=$(sha256sum "$verified_asset" | awk '{print $1}')
    if [ "$actual_sha256" != "$expected_sha256" ]; then
        echo "public EX variant asset checksum mismatch: $relative_path" >&2
        rm -f "$verified_asset"
        rollback_resources
        exit 1
    fi
    rm -f "$verified_asset"
done < "$variant_checks"
rm -f "$variant_checks"

# ================================ 成功清理与备份保留 ================================ #

rm -rf "$staging_dir"
rm -f "$archive_path" "$archive_list"

# 资源包更新频率较高，只保留最近 5 个完整回滚点；目录名在删除前再次校验为 commit SHA。
backup_number=0
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %f\n' |
    sort -rn |
    awk '{print $2}' |
    while IFS= read -r backup_name; do
        backup_number=$((backup_number + 1))
        if [ "$backup_number" -le 5 ]; then
            continue
        fi
        case "$backup_name" in
            *[!0-9a-f]*|'') continue ;;
        esac
        if [ "${#backup_name}" -eq 40 ]; then
            rm -rf "${backup_root:?}/$backup_name"
        fi
    done

echo "rollpig resources deployed: revision=$revision packages=$packages"
