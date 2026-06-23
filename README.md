# RollPig Resources

`rollpig-resources` 是 `nonebot-plugin-rollpig` 的小猪静态资源包仓库，用于独立维护小猪文案、图片、规则文件与发布清单。

这个仓库的目标是：让插件本体不用频繁发版，也能通过远端 `manifest.json` 同步新增小猪与图片资源。

## 目录结构

```text
rollpig-resources/
├─ rollpig/                 # 公有全量资源包
│  ├─ manifest.json          # 资源清单，包含版本号、文件大小与 sha256
│  ├─ pig.json               # 小猪基础数据
│  ├─ pig_rules.json         # 可选规则元数据
│  └─ images/                # 小猪图片，文件名与 pig id 对应
├─ rollpig-pjsk/             # Felis / PJSK Bot 专用外挂包
│  ├─ manifest.json
│  ├─ pig.json               # 只放外挂包新增小猪
│  ├─ pig_overrides.json     # 可选，覆盖公有小猪字段
│  ├─ pig_rules.json
│  └─ images/
└─ tools/                    # 构建与清单更新脚本
```

## 资源包说明

### 公有全量包：`rollpig/`

`rollpig/` 是默认发布给插件使用的完整资源包，包含当前可同步的小猪全集。

当前插件会把远端 `pig.json` 作为完整小猪列表读取，所以这个目录必须维护为**全量包**，不能只放新增资源。

### Bot 专用外挂包：`rollpig-pjsk/`

`rollpig-pjsk/` 是在公有全量包之上加载的 overlay，主要用于维护不准备进入公有包或上游基础版的 Bot 专属小猪。

推荐加载顺序：

```text
插件内置资源 < 公有云端资源包 < Bot 专用外挂包
```

外挂包约定：

- `pig.json` 只放新增专属小猪。
- `pig_overrides.json` 用于按 `id` 覆盖公有小猪字段。
- `pig_rules.json` 与公有规则做并集。
- 图片查找顺序为：外挂包图片 → 公有包图片 → 插件内置图片。

## 文件格式

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
- `pig.json` 保持基础格式，不写烤猪规则，方便兼容上游基础版。

### `pig_rules.json`

`pig_rules.json` 用来放插件增强玩法需要的规则元数据，例如：

- `food_pigs`：熟食类
- `human_pigs`：人类形态
- `eaten_pigs`：吃掉了
- `sold_pigs`：售罄
- `roast_excluded_pigs`：不进入普通烤猪池的形态

不支持这些规则的插件版本会忽略该文件；支持规则的 Felis 版会读取并合并内置规则、云端公有规则与外挂包规则。

### `manifest.json`

`manifest.json` 是资源同步入口，包含：

- `resource_version`
- `min_plugin_version`
- `pig_json`
- `optional_files`
- `images`
- 每个文件的 `size` 与 `sha256`

插件会根据 manifest 下载并校验资源，校验失败时回退旧缓存或插件内置资源。

## 发布地址

公有全量包：

```text
https://pig.felislab.cc/resources/rollpig/manifest.json
```

Bot 专用外挂包：

```text
https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
```

插件配置示例：

```env
ROLLPIG_RESOURCE_MANIFEST_URL=https://pig.felislab.cc/resources/rollpig/manifest.json
ROLLPIG_PRIVATE_RESOURCE_MANIFEST_URL=https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
```

当前静态资源包不需要私有 token；`ROLLPIG_PRIVATE_RESOURCE_TOKEN` 仅在自建带鉴权的资源服务时才需要。

## 构建与校验

更新公有包后，建议至少检查：

```powershell
python tools/build_rollpig_resource_pack.py `
  --base-resource-dir path/to/plugin/resource `
  --output-dir rollpig `
  --version 2026-06-15.2
```

更新 `rollpig-pjsk/` 后：

```powershell
python tools/update_private_manifest.py --version pjsk-2026-06-15.1
```

提交前建议确认：

- `pig.json` 没有重复 `id`
- 每个 `id` 都有对应图片
- `manifest.json` 中的 `sha256` 与实际文件一致
- 资源版本号已更新
- 公有包与外挂包的边界没有混淆

## 如何贡献 (Contributing)

如果你绘制了新的小猪并希望合并到本仓库，欢迎提交 Pull Request！请确保你的提交符合以下规范：

1. **图片规范**：
   - **尺寸**：强烈建议符合设定的尺寸比例（如 `240x240` 等设定）。
   - **格式与背景**：必须是 `.png` 格式，且**必须为透明背景**。
   - **命名**：图片文件名必须与 `pig.json` 中的 `id` 保持一致（例如 `id` 为 `mypig`，图片需命名为 `mypig.png`）。

2. **数据规范**：
   - 请在 `rollpig/pig.json` 的末尾追加你的小猪数据。
   - `id` 必须全网唯一，推荐使用简短的英文、数字或短横线/下划线。
   - 务必提供完整的 `name`、`description` 和 `analysis` 字段。

3. **版权要求**：
   - 提交的内容必须是你个人原创，或你已获得原作者授权允许以本仓库规则分发的素材。
   - 请在提交 PR 或 Issue 时简单备注图文的来源。对于来源不明的内容将无法合并。

## 来源说明

本仓库汇集了多方创作的 RollPig 资源，并非单一作者、单一授权的素材库。具体来源分为以下几类：

1. **原项目基础资源**  
   仓库中存在大量最初始的“小猪文案”与“小猪图片”，均来源于原作者项目 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。这部分内容需严格遵循原项目的许可要求与署名规范。

2. **原创扩展资源**  
   除了初始资源外，仓库中**绝大部分后续新增的图片均由本人创作或生成**。同时，有相当一部分新增小猪的**文案与图片均由本人完全原创**。

3. **社区图片与原创文案组合**  
   部分小猪图片使用了 [PigHub](https://pighub.top/) 用户上传分享的资源，但其对应的**小猪文案由本人重新构思与创作**。这部分图片的原始权利仍归属对应上传者或原作者。

如有任何资源存在来源错漏、侵权或不适合分发的情况，请通过 Issue 提出，我会在核实后第一时间补充说明、替换或移除相关内容。

## 使用边界

由于资源来源的复合性，**本仓库无法作为一套“统一授权”的通用素材包提供无限制分发或商用**。为了避免版权争议，建议遵循以下使用边界：

- **正常使用**：欢迎将本仓库用于 RollPig 插件部署、资源同步以及各社群 Bot 的非商业娱乐场景。
- **原作资源**：任何涉及上游原项目内容的提取或再利用，请继续遵守 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig) 的开源许可。
- **本人原创**：本人创作的图片与文案，允许在 RollPig 相关生态内免费使用和再分发。若在公开发布的二次修改版中使用，请保留本仓库来源说明；**谢绝用于任何直接的商业变现**。
- **社区资源**：本仓库无权对 PigHub 的社区图片进行二次授权。若需脱离 RollPig 玩法单独使用这些图片（如商用、再打包素材库或用于训练集），请自行确认原始来源与版权。

简单总结：在 RollPig 相关的个人/社群娱乐范围内可以放心使用；如果要提取素材做与此无关的其他用途，请务必先核实各项素材的具体来源。

## 相关项目

- 原作插件：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- Felis 版插件：[Felis2026/nonebot-plugin-rollpig](https://github.com/Felis2026/nonebot-plugin-rollpig)
- 云端存储服务：[Felis2026/rollpig-cloud](https://github.com/Felis2026/rollpig-cloud)
- PigHub：[pighub.top](https://pighub.top/)
