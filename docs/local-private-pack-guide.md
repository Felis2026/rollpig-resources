# RollPig 自建本地私有包指南

本文用于指导部署自己的小猪资源作为本地 overlay 叠加到公有包之上。

## 适合什么场景

- 只想给自己的 Bot 增加小猪，不想提交到公开资源仓库。
- 想在本机或服务器目录里维护小猪，不额外部署静态资源服务。
- 想同时使用公有包、官方 GIF 包、PJSK 包和自己的私有包。

## 推荐目录结构（参照仓库其他包即可）

```text
my-rollpig-pack/
├─ manifest.json
├─ pig.json
├─ pig_rules.json
├─ pig_overrides.json
└─ images/
   ├─ my-first-pig.png
   └─ my-gif-pig.gif
```

说明：

- `manifest.json` 是插件同步入口，记录文件路径、大小和 sha256。
- `pig.json` 只写你新增的小猪；新增 ID 不能和公有包、前序私有包重复。
- `pig_rules.json` 可选，用于标记熟食、人类、售罄、烤猪排除等规则。
- `pig_overrides.json` 可选；只有确实要覆盖已有猪字段时才使用。
- `images/` 内图片文件名必须和小猪 `id` 对齐，例如 `my-first-pig.png`。

## pig.json 示例

```json
[
  {
    "id": "my-first-pig",
    "name": "我的第一只猪",
    "description": "本地私有小猪",
    "analysis": "这只小猪只在你的 Bot 里出现。"
  }
]
```

## pig_rules.json 示例

```json
{
  "food_pigs": [],
  "human_pigs": [],
  "eaten_pigs": [],
  "sold_pigs": [],
  "roast_excluded_pigs": []
}
```

如果某只私有猪是熟食，就把它的 ID 写进 `food_pigs`：

```json
{
  "food_pigs": ["pork-rice-pig"]
}
```

## pig_overrides.json 示例

新增小猪时不需要这个文件。只有想覆盖公有包已有猪的文案或图片字段时才使用：

```json
[
  {
    "id": "pig",
    "description": "我本地改过的普通小猪文案"
  }
]
```

注意：`pig_overrides.json` 只能覆盖已存在 ID；不能用它新增小猪。

## 生成 manifest

在资源仓库根目录执行：

```powershell
python tools/update_private_manifest.py --pack D:\path\to\my-rollpig-pack --version my-pack-2026-07-10.1 --min-plugin-version 0.8.2
```

如果你的包放在 Linux 服务器上，命令类似：

```bash
python tools/update_private_manifest.py --pack /opt/rollpig/my-rollpig-pack --version my-pack-2026-07-10.1 --min-plugin-version 0.8.2
```

版本号建议自己维护，推荐格式：

```text
包名-YYYY-MM-DD.序号
```

例如：

```text
my-pack-2026-07-10.1
```

## 插件配置

把本地 `manifest.json` 路径写入 `rollpig_config.json`：

RollPig Plus `0.8.2+` 会在内部固定叠加官方 GIF 动态小猪包，用户自建本地包只需要填写自己的 overlay。

```json
{
  "rollpig": {
    "rollpig_private_resource_manifests": [
      {
        "name": "my-pack",
        "manifest_url": "D:/path/to/my-rollpig-pack/manifest.json"
      }
    ]
  }
}
```

Linux 示例：

```json
{
  "rollpig": {
    "rollpig_private_resource_manifests": [
      {
        "name": "my-pack",
        "manifest_url": "/opt/rollpig/my-rollpig-pack/manifest.json"
      }
    ]
  }
}
```

也可以使用 `file://` URL：

```json
{
  "rollpig": {
    "rollpig_private_resource_manifests": [
      {
        "name": "my-pack",
        "manifest_url": "file:///D:/path/to/my-rollpig-pack/manifest.json"
      }
    ]
  }
}
```

## 多私有包叠加顺序

`rollpig_private_resource_manifests` 会按列表顺序加载：

```text
公有包 -> 第 1 个私有包 -> 第 2 个私有包 -> 第 3 个私有包
```

约束：

- 后加载的私有包可以通过 `pig_overrides.json` 覆盖前面已有的猪。
- 后加载的私有包不能在 `pig.json` 里直接新增重复 ID。
- `name` 只用于缓存目录和日志展示，不是小猪 ID。
- 如果多个私有包用了同一个 `name`，插件会自动调整缓存目录名，避免缓存互相覆盖。

## 更新资源后怎么生效

1. 修改 `pig.json`、`pig_rules.json`、`pig_overrides.json` 或图片。
2. 重新执行 `tools/update_private_manifest.py`，并提升 `--version`。
3. 在 Bot 群里由 SUPERUSER 发送：

```text
同步小猪资源
```

如果只是想清理图鉴缓存，可发送：

```text
刷新小猪图鉴
```

## 常见问题

### 本地包需要 token 吗？

不需要。本地路径直接读取文件，`token` 只用于你自建了带鉴权的远端资源服务。

### 能不能只放 pig.json，不写 manifest？

不建议。插件的同步流程依赖 `manifest.json` 做大小和 sha256 校验，避免半包或坏包覆盖当前可用缓存。

### GIF 可以放进本地私有包吗？

可以。`nonebot-plugin-rollpig-plus >= 0.8.0` 支持 `.gif` 小猪图片；`0.8.2` 支持多个私有 overlay。

建议 GIF 保持透明背景、循环播放、无文字水印，输出帧数尽量控制在 60 帧以内。超过 60 帧时，RollPig Plus 会在完整动画周期内均匀取样到最多 60 帧；源文件仍不得超过客户端的帧数和像素帧硬上限。
