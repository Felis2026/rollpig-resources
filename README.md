<div align="center">
  <img src="https://raw.githubusercontent.com/Felis2026/nonebot-plugin-rollpig-plus/refs/heads/main/docs/assets/logo.jpeg" width="180" alt="RollPig Logo">

  <h1>🐖 RollPig Resources 🐖</h1>

  <p>
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpig.felislab.cc%2Fresources%2Fstats.json%3Fv%3D1&amp;query=%24.pigs&amp;label=Pigs&amp;color=ff8fab&amp;cacheSeconds=300" alt="Pigs">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpig.felislab.cc%2Fresources%2Fstats.json%3Fv%3D1&amp;query=%24.ex_pigs&amp;label=Pigs%20with%20EX%20Variants&amp;color=b197fc&amp;cacheSeconds=300" alt="Pigs with EX Variants">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpig.felislab.cc%2Fresources%2Fstats.json%3Fv%3D1&amp;query=%24.gif_pigs&amp;label=GIF%20Pigs&amp;color=74c0fc&amp;cacheSeconds=300" alt="GIF Pigs">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpig.felislab.cc%2Fresources%2Fstats.json%3Fv%3D1&amp;query=%24.pjsk_pigs&amp;label=PJSK%20Pigs&amp;color=63e6be&amp;cacheSeconds=300" alt="PJSK Pigs">
    <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpig.felislab.cc%2Fresources%2Fstats.json%3Fv%3D1&amp;query=%24.roast_templates&amp;label=Roast%20Templates&amp;color=ffa94d&amp;cacheSeconds=300" alt="Roast Templates">
  </p>
</div>

<p align="center">
  <a href="https://github.com/Bearlele/nonebot-plugin-rollpig">上游原作</a> ·
  <a href="https://github.com/Felis2026/nonebot-plugin-rollpig-plus">Plus</a> ·
  <a href="https://github.com/Felis2026/rollpig-cloud">Cloud</a> ·
  <a href="https://github.com/Felis2026/rollpig-resources">Resources</a>
</p>

📦 RollPig Resources 是 RollPig 系列 Bot 插件的共享素材与数据分发源。
集中维护 200+ 基础图鉴小猪、EX 等级差分、GIF小猪 Overlay / PJSK 主题小猪扩展包 与 3900+ 条共享烤猪文案。支持协议的客户端无需发版，即可通过远端 CDN 静态清单（Manifest）自动拉取最新资源与热更新。

## 🧭 资源包定位

| 资源包 | 类型 | 使用方 | 更新节奏 | 推荐插件版本 | 是否需要手动配置 |
| --- | --- | --- | --- | --- | --- |
| `rollpig/` | 公有基础包 | 所有支持云端同步的 RollPig 插件 | 每月固定更新 | 支持云端同步即可 | 否，默认资源入口 |
| `rollpig-gif/` | GIF小猪 Overlay | RollPig Plus（默认）；原版与其它支持 Overlay 的客户端可配置接入 | 不定期更新 | 支持 GIF Overlay 云同步即可 | Plus 不需要，原版及其它实现自行配置 |
| `rollpig-pjsk/` | PJSK 主题小猪 Overlay | 所有支持云端同步的 RollPig 插件 | 不定期更新 | 支持云端同步即可 | 是，按需追加 |
| `rollpig-roasts/` | 共享烤猪文案包 | RollPig Plus | 不定期更新 | Plus `0.10.0+` | 否，默认地址可关闭或替换 |
| 公有基础包 EX 差分 | `rollpig/pig_ex_variants.json` 可选文件 | 支持 EX 等级差分的 RollPig 插件 | 随公有基础包定期更新 | Plus `0.10.0+` | 否，随基础包读取 |

本文中的 Overlay 指在公有基础包之上追加或覆盖内容的叠加资源包。**数据格式兼容不等于客户端已经实现了对应同步能力**：只实现 `pig.json` 和图片读取的客户端可以使用公有基础包内容，但不会自动获得 GIF小猪 Overlay、EX、共享文案或多 Overlay 功能。

## 🧩 平台兼容边界

下表区分“能读取基础数据”和“已经实现本仓库协议的同步能力”，不把社区移植项目列入本仓库已验证的适配范围。

| 客户端 | 公有基础包数据 | manifest 云端同步 | GIF小猪 / 多 Overlay | EX / 共享文案 | 说明 |
| --- | --- | --- | --- | --- | --- |
| NoneBot RollPig 原版 | ✅ | ✅ 公有基础包；带缓存、SHA256、staging 与原子激活 | ✅ 已支持（需在私有包列表中配置） | ❌ | 已合并 PR #12，支持 Pillow GIF 渲染与多私有 Overlay；不包含 EX 差分与共享文案 |
| NoneBot RollPig Plus | ✅ | ✅ 公有基础包、Overlay 与共享文案 | ✅ 默认内置拉取 GIF，支持多私有 Overlay | ✅ | 本仓库当前完整验证对象；支持 GIF小猪、PJSK、多私有 Overlay、EX 与共享文案 |
| AstrBot 社区原移植 | ✅ `pig.json` / `image` 数据结构可对接 | ❌ 当前未纳入本仓库的 manifest 同步验证 | ❌ | ❌ | 以 [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig) 当前实现为准，需由移植方自行适配 |
| 其它框架或自建客户端 | 视实现而定 | 视实现而定 | 视实现而定 | 视实现而定 | 可参考 [资源协议](docs/resource-protocol.md) 接入公有基础包，不代表已通过本仓库验证 |

因此，README 中的“RollPig 原版可用”默认指公有基础包基础资源；原版如需使用 GIF小猪 Overlay 或多个私有包，可通过 `ROLLPIG_PRIVATE_RESOURCE_MANIFESTS` 自行配置拉取；想使用 EX 等级差分或共享烤猪文案，请使用已完整支持这些特性的 RollPig Plus。

## 📁 目录结构

```text
rollpig-resources/
├─ rollpig/                 # 每月固定更新的公有基础包
│  ├─ manifest.json          # 资源清单，包含版本号、文件大小与 sha256
│  ├─ pig.json               # 小猪基础数据
│  ├─ pig_rules.json         # 可选规则元数据
│  ├─ pig_ex_variants.json   # 可选，Plus 使用的 EX 等级立绘与文案差分
│  └─ images/                # 基础图片与可选等级差分图片
├─ rollpig-pjsk/             # PJSK 主题小猪 Overlay
│  ├─ manifest.json
│  ├─ pig.json               # 只放 Overlay 新增小猪
│  ├─ pig_overrides.json     # 可选，覆盖公有小猪字段
│  ├─ pig_rules.json
│  └─ images/
├─ rollpig-gif/              # Plus 固定加载的 GIF小猪 Overlay
│  ├─ manifest.json
│  ├─ pig.json
│  ├─ pig_overrides.json
│  ├─ pig_rules.json
│  └─ images/
├─ rollpig-roasts/           # 经清洗审核的共享烤猪文案
│  ├─ manifest.json
│  └─ roast_library.json
├─ deploy/                    # 服务器原子发布与失败回滚脚本
├─ docs/                     # 协议、接入、私有包与发布说明
└─ tools/                    # 资源校验、文案清洗与清单更新脚本
```

## 📦 资源包说明

### 公有基础包：`rollpig/`

`rollpig/` 是每月固定更新、默认发布给插件使用的完整资源包，包含当前可同步的小猪全集。面向一切已经支持云端资源同步的 RollPig 插件；插件即使暂不支持 GIF小猪、EX 或其它扩展，也可以继续同步并使用其中的基础小猪。

当前插件会把远端 `pig.json` 作为完整小猪列表读取，所以这个目录必须维护为**全量包**，不能只放新增资源。今后公有基础包还会定期更新不同 EX Level 的差分图片与文案；支持 EX 等级的插件可参照 [`pig_ex_variants.json`](rollpig/pig_ex_variants.json) 格式接入，暂不支持的插件会忽略，并继续使用基础资源。

### PJSK 主题小猪 Overlay：`rollpig-pjsk/`

`rollpig-pjsk/` 在公有基础包之上加载，维护不准备进入基础包的 PJSK 等音游相关主题小猪。它不是公有基础包的一部分，也不会被只同步基础包的客户端自动加载。该包不定期更新。

推荐加载顺序：

```text
插件内置资源 < 公有云端基础包 < PJSK 主题 Overlay
```

Overlay 约定：

- `pig.json` 只放新增专属小猪。
- `pig_overrides.json` 用于按 `id` 覆盖公有小猪字段。
- `pig_rules.json` 与公有规则做并集。
- 图片查找顺序为：Overlay 图片 → 公有包图片 → 插件内置图片。

### GIF小猪 Overlay：`rollpig-gif/`

`rollpig-gif/` 是 RollPig Plus 原生固定拉取的 GIF小猪 Overlay，只追加普通小猪，不覆盖公有基础包字段，也不写入熟食等特殊规则。该包不定期更新，原版 RollPig 默认只同步公有基础包，不会自动拉取它：

- **NoneBot RollPig Plus**：原生固定拉取，开箱即用，无需配置。
- **NoneBot RollPig 原版**：现已支持 Pillow GIF 卡片渲染与多 Overlay 同步。用户只需在配置项 `ROLLPIG_PRIVATE_RESOURCE_MANIFESTS` 中添加本包的 `manifest.json` 即可直接拉取使用。
- **其它第三方移植版**：需由移植方自行实现 Overlay 同步与 GIF 渲染能力。

GIF小猪 Overlay 约定：

- `pig.json` 只放 GIF小猪 Overlay 新增小猪。
- 图片文件使用 `.gif`，文件名与 `id` 对应。
- Plus 版本默认内置加载；原版支持通过私有包配置加载；其它移植版需自行实现 Overlay 下载、缓存、校验和渲染。

### 共享烤猪文案：`rollpig-roasts/`

`rollpig-roasts/` 是供 RollPig Plus 0.10.0 及以上版本使用的共享烤猪文案包。保持默认配置并开启资源同步后，插件会自动检查和下载更新，不需要手动安装，也不需要配置 AI Key。

- 没有配置 AI 时，烤猪和烤群友可以直接使用共享文案。
- 已配置 AI 时，共享文案会与本机生成的文案共同使用，不占本机每个组合 5 条 AI 文案的积累额度。
- 更新共享包不会覆盖或删除用户自己生成、编写的本地文案。
- 不想使用时，将 `rollpig_roast_library_manifest_url` 显式设为 `""` 或 `null` 即可关闭。

共享包只包含模板正文和允许的占位符（例如 `{k}`、`{v}`）。真实用户 ID、昵称、群记录、Token 和 AI 请求日志不会上传到本仓库；占位符只会在你的 Bot 本地发送消息时填入。

部分文案可能对应 PJSK 或其他可选资源包中的小猪。没有加载对应小猪时，这些文案不会被抽到，也不会影响其他功能。

## 🧩 文件格式

### `pig.json`

每只小猪至少包含：

```json
[
  {
    "id": "pig",
    "name": "猪",
    "description": "普通小猪",
    "analysis": "你性格温和，喜欢简单的生活，容易满足。"
  }
]
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

`manifest.json` 是资源同步入口。公有基础包、Overlay 和共享文案包不是同一种清单结构，完整字段约束见 [资源协议](docs/resource-protocol.md)。通常情况下：

- 所有包都应声明 `schema_version`、`resource_version`，并为每个文件提供 `size` 与 `sha256`。
- 公有基础包使用 `pig_json`、`images` 和可选的 `optional_files` / `variant_images`。
- Overlay 使用 `overlay`、`overlay_name`、`base_manifest_url`、`allow_override` 以及自身的新增资源。
- 共享文案包使用 `package_type: "roast_library"` 和 `roast_library`。
- `min_plugin_version` 是可选的包级兼容提示，不是所有客户端或资源包的统一必填字段。

支持协议的客户端应根据 manifest 下载并校验资源，校验失败时保留旧缓存或插件内置资源，不应让半包覆盖当前可用资源。接入流程见 [客户端接入指南](docs/integration-guide.md)。

## 🌐 发布地址

公有基础包：

```text
https://pig.felislab.cc/resources/rollpig/manifest.json
```

PJSK 主题小猪 Overlay：

```text
https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
```

GIF小猪 Overlay：

```text
https://pig.felislab.cc/resources/rollpig-gif/manifest.json
```

共享烤猪文案：

```text
https://pig.felislab.cc/resources/rollpig-roasts/manifest.json
```

资源统计清单：

```text
https://pig.felislab.cc/resources/stats.json
```

该文件由发布流程根据资源包 JSON 和 manifest 自动生成，供首页动态徽章读取；它不是 RollPig 插件必须同步的资源文件。

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

`rollpig-gif` 是 RollPig Plus `0.8.2+` 固定拉取的 GIF小猪 Overlay，Plus 用户不需要在配置里手动填写。

当前静态资源包不需要私有 token；`ROLLPIG_PRIVATE_RESOURCE_TOKEN` 仅在自建带鉴权的资源服务时才需要。

如果你想维护自己的本地私有小猪包，请参考 [自建本地私有包指南](docs/local-private-pack-guide.md)；这份指南主要面向已经支持 Overlay 的 RollPig Plus。

## ✅ 自动校验与发布

本地提交前可以运行：

```powershell
python tools/check_resources.py --base-ref origin/main
```

仓库工作流会在 Pull Request 中只做校验；推送到 `main` 后，校验通过才会把四个资源包原子发布到 Cloud 静态目录，并额外核对差分 JSON 与抽样图片。发布失败或公网 manifest 与本次文件不一致时会自动恢复旧资源，Cloud 服务无需重启。

首次启用所需的 GitHub Environment、Secrets 和服务器条件见 [资源自动校验与发布](docs/automated-deployment.md)。

## 🤝 如何贡献

如果你绘制了新的小猪并希望合并到本仓库，欢迎提交 Pull Request！请先确认内容应进入 `rollpig/` 公有基础包、`rollpig-gif/` GIF小猪 Overlay、`rollpig-pjsk/` PJSK 主题 Overlay 还是其它资源包，再确保提交符合以下规范。提交前请使用仓库工具生成或更新 manifest，不要手工填写文件哈希：

1. **图片规范**：
   - **尺寸**：强烈建议符合设定的尺寸比例（如 `240x240` 等设定）。
   - **格式与背景**：公有基础包的基础图片使用 `.png`，且**建议为透明背景**；Overlay 可根据客户端能力使用 `.png` 或 `.gif`。
   - **EX 差分例外**：`pig_ex_variants.json` 声明的差分图片可使用 `.png` 或 `.gif`，文件名为 `<pig_id>_ex<level>`。
   - **基础图片命名**：图片文件名必须与 `pig.json` 中的 `id` 保持一致（例如 `id` 为 `mypig`，图片需命名为 `mypig.png`）。

2. **数据规范**：
   - 公有基础包的小猪追加到 `rollpig/pig.json`；Overlay 只写新增 ID，覆盖已有 ID 时必须使用协议允许的 `pig_overrides.json`。
   - `id` 必须全网唯一，推荐使用简短的英文、数字或短横线/下划线。
   - 基础小猪务必提供完整的 `name`、`description` 和 `analysis` 字段；EX 差分可以只提供 `image`、`description`、`analysis` 中至少一项。
   - 资源版本必须随资源内容变化递增，并通过 `python tools/check_resources.py` 校验。

3. **版权相关**：
   - 提交的内容必须是你个人原创，或你已获得原作者授权允许以本仓库规则分发的素材。
   - 请在提交 PR 或 Issue 时简单备注图文的来源、作者及授权情况。
   - 对于最终合入的资源，本仓库会根据已知信息在对应资源包说明、来源说明或关联 PR 中注明作者与原始来源；不会因整理文件名、格式或清单而改变作者归属。
   - 如需使用特定署名、补充授权信息或更正来源，请在 PR 或 Issue 中明确说明。来源不明、授权无法确认或不适合公开分发的内容将不会合入。

## 🧾 来源说明

本仓库汇集了多方创作的 RollPig 资源，并非单一作者、单一授权的素材库。具体来源分为以下几类：

1. **原项目基础资源**  
   仓库中存在大量最初始的“小猪文案”与“小猪图片”，均来源于原作者项目 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。这部分内容需严格遵循原项目的许可要求与署名规范。

2. **原创扩展资源**  
   除了初始资源外，仓库中**绝大部分后续新增的图片均由本人创作或生成**。同时，有相当一部分新增小猪的**文案与图片均由本人完全原创**。

3. **社区图片与原创文案组合**  
   部分小猪图片使用了 [PigHub](https://pighub.top/) 用户上传分享的资源，但其对应的**小猪文案由本人重新构思与创作**。这部分图片的原始权利仍归属对应上传者或原作者。

如有任何资源存在来源错漏、侵权或不适合分发的情况，请通过 Issue 提出，本仓库会在核实后第一时间补充说明、替换或移除相关内容。

## ⚖️ 使用规范速查

> 📌 正常部署 RollPig / RollPig Plus 插件、通过本仓库公开资源链接获取资源并在自己的 Bot 中缓存使用：**直接用，不需要额外申请或联系我们。**

### 可以做

- 用于 RollPig、RollPig Plus 或其他相关项目的个人、群聊和非商业部署。
- 直接从本仓库或资源服务读取资源，并在自己的 Bot 中缓存使用。
- 在保留来源说明的前提下，修改资源或随插件一起分发。

### 需要另行授权

- 把资源另建 CDN、API、资源站或素材包，面向其他人独立提供下载。
- 直接售卖图片、文案或以资源本身收费。
- 删除、隐藏或伪造作者与来源信息，或把第三方图片冒充为自己的作品。
- 将 PigHub、社区投稿或其他第三方素材脱离 RollPig 单独商用、再打包或用于训练集。

上游和第三方素材仍按其原有授权执行，完整条款见 [`LICENSE`](./LICENSE)、[`RESOURCES-LICENSE.md`](./RESOURCES-LICENSE.md)、[`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。

## 🔗 相关项目

- 上游原作：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- RollPig Plus：[Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)
- 云端存储服务：[Felis2026/rollpig-cloud](https://github.com/Felis2026/rollpig-cloud)
- PigHub：[pighub.top](https://pighub.top/)
