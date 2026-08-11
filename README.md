<div align="center">
  <img src="https://raw.githubusercontent.com/Felis2026/nonebot-plugin-rollpig-plus/refs/heads/main/docs/assets/logo.jpeg" width="180" alt="RollPig Logo">

  <h1>🐖 RollPig Resources 🐖</h1>

  <p><strong>RollPig 系列的小猪资源仓库</strong></p>
  <p>独立维护上游原版和 RollPig Plus 使用的小猪文案、图片、规则文件与发布清单。</p>

  <p>
    <img src="https://img.shields.io/badge/Packages-Public%20%2B%20Overlay-ff69b4" alt="Public and Overlay packages">
    <img src="https://img.shields.io/badge/Integrity-SHA256-blue" alt="SHA256 integrity verification">
    <img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen" alt="Contributions welcome">
  </p>
</div>

<p align="center">
  <a href="https://github.com/Bearlele/nonebot-plugin-rollpig">上游原作</a> ·
  <a href="https://github.com/Felis2026/nonebot-plugin-rollpig-plus">Plus</a> ·
  <a href="https://github.com/Felis2026/rollpig-cloud">Cloud</a> ·
  <a href="https://github.com/Felis2026/rollpig-resources">Resources</a>
</p>

这个仓库让 RollPig 系列插件无需频繁发版，也能通过远端 `manifest.json` 同步新增小猪与图片资源。

## 🧭 资源包定位

| 资源包 | 类型 | 使用方 | 推荐插件版本 | 是否需要手动配置 |
| --- | --- | --- | --- | --- |
| `rollpig/` | 公有全量包 | RollPig原版、RollPig Plus | 原版/Plus `0.2.0+` | 否，默认资源入口 |
| `rollpig-gif/` | 官方 GIF Overlay | RollPig原版、RollPig Plus | Plus `0.8.2+` | 否，由 Plus 固定加载 |
| `rollpig-pjsk/` | PJSK 专用 Overlay | RollPig Plus | Plus `0.8.2+` | 是，按需追加 |
| `rollpig-roasts/` | 共享烤猪文案 | RollPig Plus | Plus `0.10.0+` | 否，随资源同步加载 |
| 公有包 EX 差分 | `rollpig/pig_ex_variants.json` 可选文件 | RollPig Plus | Plus `0.10.0+` | 否，随公有包读取 |

本文中的 Overlay 指在公有全量包之上追加或覆盖内容的叠加资源包。公有包保持上游兼容，GIF 与 PJSK 等增强能力主要由 RollPig Plus 使用。

## 📁 目录结构

```text
rollpig-resources/
├─ rollpig/                 # 公有全量资源包
│  ├─ manifest.json          # 资源清单，包含版本号、文件大小与 sha256
│  ├─ pig.json               # 小猪基础数据
│  ├─ pig_rules.json         # 可选规则元数据
│  ├─ pig_ex_variants.json   # 可选，EX 等级立绘与文案差分
│  └─ images/                # 基础图片与可选等级差分图片
├─ rollpig-pjsk/             # PJSK Bot 专用 Overlay
│  ├─ manifest.json
│  ├─ pig.json               # 只放 Overlay 新增小猪
│  ├─ pig_overrides.json     # 可选，覆盖公有小猪字段
│  ├─ pig_rules.json
│  └─ images/
├─ rollpig-gif/              # 官方 GIF 动态小猪 Overlay
│  ├─ manifest.json
│  ├─ pig.json
│  ├─ pig_overrides.json
│  ├─ pig_rules.json
│  └─ images/
├─ rollpig-roasts/           # 经清洗审核的共享烤猪文案
│  ├─ manifest.json
│  └─ roast_library.json
├─ deploy/                    # 服务器原子发布与失败回滚脚本
├─ docs/                     # 自建私有包、资源维护等说明文档
└─ tools/                    # 资源校验、文案清洗与清单更新脚本
```

## 📦 资源包说明

### 公有全量包：`rollpig/`

`rollpig/` 是默认发布给插件使用的完整资源包，包含当前可同步的小猪全集。

当前插件会把远端 `pig.json` 作为完整小猪列表读取，所以这个目录必须维护为**全量包**，不能只放新增资源。

### PJSK 专用 Overlay：`rollpig-pjsk/`

`rollpig-pjsk/` 在公有全量包之上加载，主要维护不准备进入公有包的 PJSK Bot 专属小猪。

推荐加载顺序：

```text
插件内置资源 < 公有云端资源包 < PJSK 专用 Overlay
```

Overlay 约定：

- `pig.json` 只放新增专属小猪。
- `pig_overrides.json` 用于按 `id` 覆盖公有小猪字段。
- `pig_rules.json` 与公有规则做并集。
- 图片查找顺序为：Overlay 图片 → 公有包图片 → 插件内置图片。

### 官方 GIF Overlay：`rollpig-gif/`

`rollpig-gif/` 是 RollPig Plus 固定加载的官方动态小猪 Overlay，只追加普通小猪，不覆盖公有包字段，也不写入熟食等特殊规则。

GIF Overlay 约定：

- `pig.json` 只放 GIF 包新增小猪。
- 图片文件使用 `.gif`，文件名与 `id` 对应。
- 需要配合支持 GIF 资源的 RollPig Plus 使用。

### 共享烤猪文案：`rollpig-roasts/`

`rollpig-roasts/` 是供 RollPig Plus 0.10.0 及以上版本使用的官方共享文案包。保持默认配置并开启资源同步后，插件会自动检查和下载更新，不需要手动安装，也不需要配置 AI Key。

- 没有配置 AI 时，烤猪和烤群友可以直接使用共享文案。
- 已配置 AI 时，共享文案会与本机生成的文案共同使用，不占本机每个组合 5 条 AI 文案的积累额度。
- 更新共享包不会覆盖或删除用户自己生成、编写的本地文案。
- 不想使用时，将 `rollpig_roast_library_manifest_url` 显式设为 `""` 或 `null` 即可关闭。

共享包只包含带 `{k}`、`{v}` 等占位符的模板正文。真实用户 ID、昵称、群记录、Token 和 AI 请求日志不会上传到本仓库；昵称只会在你的 Bot 本地发送消息时临时填入。

部分文案可能对应 PJSK 或其他可选资源包中的小猪。没有加载对应小猪时，这些文案不会被抽到，也不会影响其他功能。

## 🧩 文件格式

### `pig.json`

每只小猪至少包含：

```json
{
  "id": "pig",
  "name": "猪",
  "description": "普通小猪",
  "analysis": "你性格温和，喜欢简单的生活，容易满足。"
}
```

约定：

- `id` 使用小写英文、数字、短横线或下划线。
- 图片文件名与 `id` 对应，例如 `pig` 对应 `images/pig.png`。
- `pig.json` 保持基础格式，不写烤猪规则，方便兼容上游原作。

### `pig_rules.json`

`pig_rules.json` 用来放插件增强玩法需要的规则元数据，例如：

- `food_pigs`：熟食类
- `human_pigs`：人类形态
- `eaten_pigs`：吃掉了
- `sold_pigs`：售罄
- `roast_excluded_pigs`：不进入普通烤猪池的形态

不支持这些规则的插件版本会忽略该文件；RollPig Plus 会读取并合并内置规则、云端公有规则与 Overlay 规则。

### `pig_ex_variants.json`

`pig_ex_variants.json` 为 RollPig Plus `0.10.0+` 提供同一只猪的 EX 等级立绘与文案差分。差分不会新增图鉴条目，也不会修改小猪 ID、名称、抽取规则或用户数据。

```json
{
  "schema_version": 1,
  "pigs": {
    "coder-pig": {
      "levels": {
        "2": {
          "image": "coder-pig_ex2.png",
          "description": "开始熟练维护猪联网。"
        },
        "5": {
          "description": "已经能从容处理整套猪联网。",
          "analysis": "服务稳定了，咖啡终于也能趁热喝完。"
        }
      }
    }
  }
}
```

- `schema_version` 当前固定为 `1`，用于标识这份差分文件遵循第一版结构。
- 等级键只允许字符串 `"1"`～`"5"`；每档必须至少提供 `image`、`description`、`analysis` 之一，空差分会被拒绝。
- 图片和两类文案分别按等级继承：当前档缺少某字段时，使用较低等级最近一次提供的值，仍未提供时才使用基础 `pig.json` 或基础图片。
- 只有声明图片的等级才写入 `variant_images`；图片必须命名为 `<pig_id>_ex<level>.png` 或 `.gif`，并与清单中的大小和 SHA256 一一对应。
- 首版只允许公有 `rollpig/` 全量包提供差分，私有 Overlay 暂不提供差分覆盖。
- 基础 `pig.json` 和基础图片必须继续保留。旧 Plus 与原版 RollPig 会忽略新字段并正常同步基础资源。

### `manifest.json`

`manifest.json` 是资源同步入口，包含：

- `resource_version`
- `min_plugin_version`
- `pig_json`
- `optional_files`
- `images`
- 可选的 `variant_images`
- 每个文件的 `size` 与 `sha256`

插件会根据 manifest 下载并校验资源，校验失败时回退旧缓存或插件内置资源。

## 🌐 发布地址

公有全量包：

```text
https://pig.felislab.cc/resources/rollpig/manifest.json
```

PJSK 专用 Overlay：

```text
https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
```

官方 GIF Overlay：

```text
https://pig.felislab.cc/resources/rollpig-gif/manifest.json
```

共享烤猪文案：

```text
https://pig.felislab.cc/resources/rollpig-roasts/manifest.json
```

RollPig Plus `0.8.2+` 推荐配置示例：

```json
{
  "rollpig": {
    "rollpig_resource_manifest_url": "https://pig.felislab.cc/resources/rollpig/manifest.json",
    "rollpig_private_resource_manifests": [
      {
        "name": "pjsk",
        "manifest_url": "https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json"
      }
    ]
  }
}
```

`rollpig-gif` 是 RollPig Plus `0.8.2+` 固定使用的官方 GIF Overlay，Plus 用户不需要在配置里手动填写。

当前静态资源包不需要私有 token；`ROLLPIG_PRIVATE_RESOURCE_TOKEN` 仅在自建带鉴权的资源服务时才需要。

如果你想维护自己的本地私有小猪包，请参考 [自建本地私有包指南](docs/local-private-pack-guide.md)。

## ✅ 自动校验与发布

本地提交前可以运行：

```powershell
python tools/check_resources.py --base-ref origin/main
```

仓库工作流会在 Pull Request 中只做校验；推送到 `main` 后，校验通过才会把四个资源包原子发布到 Cloud 静态目录，并额外核对差分 JSON 与抽样图片。发布失败或公网 manifest 与本次文件不一致时会自动恢复旧资源，Cloud 服务无需重启。

首次启用所需的 GitHub Environment、Secrets 和服务器条件见 [资源自动校验与发布](docs/automated-deployment.md)。

## 🤝 如何贡献

如果你绘制了新的小猪并希望合并到本仓库，欢迎提交 Pull Request！请先确认内容应进入 `rollpig/` 公有包、`rollpig-gif/` 官方 GIF 包、`rollpig-pjsk/` PJSK 包还是其它资源包，再确保提交符合以下规范：

1. **图片规范**：
   - **尺寸**：强烈建议符合设定的尺寸比例（如 `240x240` 等设定）。
   - **格式与背景**：必须是 `.png` 格式，且**必须为透明背景**。
   - **GIF 例外**：仅 `rollpig-gif/` 这类动态 Overlay 允许使用 `.gif`。
   - **命名**：图片文件名必须与 `pig.json` 中的 `id` 保持一致（例如 `id` 为 `mypig`，图片需命名为 `mypig.png`）。

2. **数据规范**：
   - 请在 `rollpig/pig.json` 的末尾追加你的小猪数据。
   - `id` 必须全网唯一，推荐使用简短的英文、数字或短横线/下划线。
   - 务必提供完整的 `name`、`description` 和 `analysis` 字段。

3. **版权要求**：
   - 提交的内容必须是你个人原创，或你已获得原作者授权允许以本仓库规则分发的素材。
   - 请在提交 PR 或 Issue 时简单备注图文的来源。对于来源不明的内容将无法合并。

## 🧾 来源说明

本仓库汇集了多方创作的 RollPig 资源，并非单一作者、单一授权的素材库。具体来源分为以下几类：

1. **原项目基础资源**  
   仓库中存在大量最初始的“小猪文案”与“小猪图片”，均来源于原作者项目 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。这部分内容需严格遵循原项目的许可要求与署名规范。

2. **原创扩展资源**  
   除了初始资源外，仓库中**绝大部分后续新增的图片均由本人创作或生成**。同时，有相当一部分新增小猪的**文案与图片均由本人完全原创**。

3. **社区图片与原创文案组合**  
   部分小猪图片使用了 [PigHub](https://pighub.top/) 用户上传分享的资源，但其对应的**小猪文案由本人重新构思与创作**。这部分图片的原始权利仍归属对应上传者或原作者。

如有任何资源存在来源错漏、侵权或不适合分发的情况，请通过 Issue 提出，我会在核实后第一时间补充说明、替换或移除相关内容。

## ⚖️ 使用边界

由于资源来源的复合性，**本仓库无法作为一套“统一授权”的通用素材包提供无限制分发或商用**。为了避免版权争议，建议遵循以下使用边界：

- **正常使用**：欢迎将本仓库用于 RollPig 插件部署、资源同步以及各社群 Bot 的非商业娱乐场景。
- **原作资源**：任何涉及上游原项目内容的提取或再利用，请继续遵守 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig) 的开源许可。
- **本人原创**：本人创作的图片与文案，允许在 RollPig 相关生态内免费使用和再分发。若在公开发布的二次修改版中使用，请保留本仓库来源说明；**谢绝用于任何直接的商业变现**。
- **社区资源**：本仓库无权对 PigHub 的社区图片进行二次授权。若需脱离 RollPig 玩法单独使用这些图片（如商用、再打包素材库或用于训练集），请自行确认原始来源与版权。

简单总结：在 RollPig 相关的个人/社群娱乐范围内可以放心使用；如果要提取素材做与此无关的其他用途，请务必先核实各项素材的具体来源。

## 🔗 相关项目

- 上游原作：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- RollPig Plus：[Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)
- 云端存储服务：[Felis2026/rollpig-cloud](https://github.com/Felis2026/rollpig-cloud)
- PigHub：[pighub.top](https://pighub.top/)
