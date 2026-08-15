# RollPig 资源协议

本文定义 `rollpig-resources` 当前公开使用的静态资源协议。当前协议版本为 `schema_version: 1`；文档只解释已经存在的字段，不新增字段，也不改变现有资源包地址。

本文使用以下规范用词：**必须**表示客户端或资源包不能省略的要求，**应该**表示生产环境推荐实现，**可以**表示可选能力。客户端不需要一次实现全部扩展，但不能把未实现的扩展能力宣传为已支持。

## 1. 协议范围

资源包分为三类：

| 类型 | 目录示例 | 作用 |
| --- | --- | --- |
| 公有基础包 | `rollpig/` | 提供完整的基础小猪、基础图片和可选规则/EX 差分 |
| Overlay 叠加包 | `rollpig-gif/`、`rollpig-pjsk/` 或自建包 | 在公有基础包之上追加小猪，必要时按协议覆盖已有字段 |
| 共享文案包 | `rollpig-roasts/` | 提供共享烤猪模板，不包含图片和用户数据 |

公有基础包是最小兼容目标。客户端只要能读取公有基础包的 `pig.json` 和 `images/`，就可以使用基础小猪；Overlay、EX 和共享文案属于可选能力，客户端可以明确不实现。

不同包类型的 manifest 约束不完全相同：

| 字段或能力 | 公有基础包 | Overlay | 共享文案包 |
| --- | --- | --- | --- |
| `schema_version`、`resource_version` | 必须 | 必须 | 必须 |
| `min_plugin_version` | 可选兼容提示 | 可选兼容提示 | 可选兼容提示 |
| `overlay=true`、`overlay_name`、`base_manifest_url`、`allow_override` | 不适用 | 必须 | 不适用 |
| `package_type=roast_library` | 不适用 | 不适用 | 必须 |
| `pig_json`、图片清单 | 必须 | 按包内容决定 | 不适用 |
| `roast_library` | 不适用 | 不适用 | 必须 |

本仓库当前发布的清单仍会填写 `min_plugin_version`，用于给客户端提供兼容性提示；协议并不要求自建基础包或每一种客户端都必须依赖这个字段。未声明时应直接省略该字段，不要写成 `null`。客户端未声明或无法解析该提示时，应依据自身能力选择跳过对应扩展包，不能把 Overlay 当成公有基础包加载。

## 2. 通用规则

- 所有 JSON 使用 UTF-8、无 BOM 和 LF 换行。
- manifest 中的 `path` 是相对于**当前 `manifest.json` 所在目录**的 POSIX 路径，只允许指向包内文件；不得使用绝对路径、`..`、反斜杠或符号链接。通过 HTTP 获取时，将该路径拼接到 manifest 的资源包基址，而不是拼接到用户输入的任意 URL。
- 每个被 manifest 引用的文件都必须同时提供 `size` 和小写十六进制 `sha256`。
- 客户端应该先把文件下载到独立的 staging 版本目录，再在所有文件通过大小、哈希、JSON 和图片检查后切换 active。
- 下载失败、校验失败或重新加载失败时，必须保留旧 active；首次同步失败时使用插件内置公有基础包或其它仍然有效的包。
- `resource_version` 是包内快照标识，不要求客户端按语义化版本解析，也不能通过字符串大小比较新旧。资源内容发生变化时，维护者必须提升该值；客户端应该使用 manifest 摘要、HTTP `ETag` 或 `Last-Modified` 判断是否需要重新下载。
- `min_plugin_version` 只是包级兼容性提示，不是所有包的公共必填字段。存在且无法满足时，客户端应跳过该包；不能把它当作公有基础包强行加载。

SHA256 只保证“下载到的文件与该 manifest 声明的内容一致”，不提供发布者身份认证。生产客户端应该使用 HTTPS、限制允许的资源域名，并在需要防篡改发布者身份时增加签名 manifest 或等价的信任机制。

## 3. 公有基础包

### 3.1 目录结构

```text
rollpig/
├─ manifest.json
├─ pig.json
├─ pig_rules.json             # 可选
├─ pig_ex_variants.json       # 可选，Plus EX 差分
└─ images/
   ├─ <pig-id>.png
   └─ <pig-id>_ex<level>.png  # 仅在 pig_ex_variants.json 引用时存在
```

公有基础包是**全量快照**，不是只包含最近新增内容的增量包。新的公有基础包 manifest 被激活后，客户端应以它重建基础资源快照；不要把旧版本中已经删除的 ID 继续当作当前可抽取小猪。

### 3.2 `pig.json`

文件根值是数组，每项至少包含以下字段：

```json
[
  {
    "id": "pig",
    "name": "猪",
    "description": "普通小猪",
    "analysis": "你性格温和，喜欢简单的生活。"
  }
]
```

字段约束：

- `id` 使用小写英文、数字、短横线或下划线，并在包内唯一。
- 公有基础包中每个 ID 都必须有基础图片；基础图片的文件名通常为 `<id>.<suffix>`。
- `name`、`description`、`analysis` 是基础小猪的完整展示字段，不能为空。
- `pig.json` 不承担熟食、人类形态、售罄等玩法规则；这些信息写入可选的 `pig_rules.json`。

### 3.3 `pig_rules.json`

规则文件的根值是对象，当前支持的键为：

```json
{
  "schema_version": 1,
  "food_pigs": [],
  "human_pigs": [],
  "eaten_pigs": [],
  "sold_pigs": [],
  "roast_excluded_pigs": []
}
```

每个数组只填写已存在的猪 ID。客户端可以忽略未知规则键，但不能把规则文件中的 ID 当作新的猪条目。

### 3.4 EX 差分

`pig_ex_variants.json` 只改变同一只猪在 EX Lv.1～5 的展示，不新增图鉴条目，也不改变猪 ID、抽取规则或历史用户数据。

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
          "analysis": "已经能从容处理整套猪联网。"
        }
      }
    }
  }
}
```

规则如下：

- 等级键只能是字符串 `"1"` 到 `"5"`。
- 每档至少提供 `image`、`description`、`analysis` 中的一项；三项都没有的空差分无效。
- 三类字段独立继承：当前等级缺少某字段时，使用较低等级最近一次提供的值，仍没有时使用基础 `pig.json` 或基础图片。继承只向较低等级和基础资源回退，不向更高等级查找。
- 客户端可以按以下等价算法解析每个字段：从当前等级递减到 `1`，找到该字段的第一个非空值就停止；所有差分等级都没有该字段时使用基础值。省略字段表示继续继承，`null` 不是通用的清空或删除指令，应视为无效差分并报告。
- `image` 只填写文件名，图片实际放在 `images/` 下，并命名为 `<pig-id>_ex<level>.png` 或 `.gif`。
- 只有差分声明了图片时，才在公有基础包 manifest 的 `variant_images` 中登记该图片；`variant_images` 必须与差分 JSON 和实体文件一一对应。
- 基础图片必须继续保留。只支持基础字段的旧客户端会忽略整个差分文件，仍可正常使用基础资源。
- 当前协议只允许公有基础包提供 `pig_ex_variants.json`；首版私有 Overlay 不提供 EX 差分覆盖。资源仓库会随公有基础包的定期更新继续补充不同 EX Level 的差分图片与文案，支持该能力的插件可按本节格式接入。

公有基础包 manifest 的 EX 相关字段示意：

```json
{
  "optional_files": {
    "pig_ex_variants": {
      "path": "pig_ex_variants.json",
      "size": 7235,
      "sha256": "<64 位小写 sha256>"
    }
  },
  "variant_images": [
    {
      "pig_id": "coder-pig",
      "level": 2,
      "filename": "coder-pig_ex2.png",
      "path": "images/coder-pig_ex2.png",
      "size": 135730,
      "sha256": "<64 位小写 sha256>"
    }
  ]
}
```

## 4. Overlay 叠加包

### 4.1 manifest 头部

Overlay manifest 除了通用字段，至少必须声明以下 Overlay 字段：

```json
{
  "schema_version": 1,
  "overlay": true,
  "overlay_name": "my-pack",
  "resource_version": "my-pack-2026-08-20.1",
  "min_plugin_version": "0.8.2",
  "base_manifest_url": "https://example.com/resources/rollpig/manifest.json",
  "allow_override": false
}
```

- `overlay_name` 是包的稳定名称，客户端可用它区分缓存目录和日志。
- `base_manifest_url` 必须是 HTTPS URL，用于说明该 Overlay 叠加在哪个公有基础包 manifest 之上；它是兼容性和审计信息，不等于客户端可以跳过本地校验。
- `allow_override` 为 `false` 时，包只能追加新 ID；此时不能提供 `pig_overrides.json`，`pig.json` 也不能与低层资源产生 ID 冲突。
- `allow_override` 为 `true` 时，只有 `pig_overrides.json` 可以覆盖低层资源中已经存在的同 ID 条目；覆盖条目不能借此新增 ID，也不能删除 ID。
- 覆盖对象中省略的字段继承低层资源，`image`、`description`、`analysis` 分别独立判断；`null` 不表示删除，当前协议中应拒绝或跳过该字段。
- Overlay 的 `pig.json` 只写新增小猪；同一 ID 不能直接重复出现在 `pig.json` 中。
- Overlay 可以带 `pig_rules.json`，其中的规则按客户端实现与包顺序合并。
- Overlay 可以带 `pig_overrides.json`，但只能覆盖已存在的 ID，不能借此新增猪。
- `pig_overrides.json` 和 `variant_images` 在当前协议中不能同时提供 EX 差分能力；首版私有 Overlay 不声明 `variant_images`。

### 4.2 加载顺序与冲突

客户端应明确记录包顺序，并在重新加载时从头构建快照。推荐顺序为：

```text
插件内置资源 < 公有基础包 < 本仓库维护的 Overlay < 用户私有 Overlay（按配置顺序）
```

后加载的包优先级更高，但只允许在 manifest 明确允许覆盖时覆盖已有字段。Overlay 应在完整校验通过后整体激活；如果存在非法覆盖、缺失目标 ID 或哈希错误，应跳过整个 Overlay，而不是激活半个包。一个 Overlay 下载失败时，应隔离该 Overlay，不应让其它已经可用的包失效。

本仓库维护的 `rollpig-gif` 和 `rollpig-pjsk` 当前均不覆盖公有基础包字段；用户自建包如果要覆盖，必须自行承担字段冲突和内容维护责任。

## 5. 共享烤猪文案包

共享文案包不是图片 Overlay，使用独立的 manifest 结构：

```json
{
  "schema_version": 1,
  "package_type": "roast_library",
  "resource_version": "roasts-2026-07-30.1",
  "min_plugin_version": "0.10.0",
  "roast_library": {
    "path": "roast_library.json",
    "size": 655843,
    "sha256": "<64 位小写 sha256>"
  },
  "statistics": {
    "origin_count": 173,
    "pair_count": 2723,
    "text_count": 3912
  }
}
```

`roast_library.json` 是“原始猪 ID → 目标/场景 → 文案数组”的对象。占位符采用白名单：

| 占位符 | 使用规则 |
| --- | --- |
| `{k}`、`{v}` | 仅用于 PvP/烤群友模板，必须同时出现；普通烤猪模板不得使用 |
| `{origin}`、`{food}` | 构建工具允许使用，由客户端按当前烤猪上下文填充 |
| 其它占位符 | 构建阶段拒绝，客户端也不得原样发送 |

客户端发送前必须填充当前模板所需的全部占位符；缺少值时跳过该模板并记录原因，不应把 `{k}`、`{v}` 等原文发送给用户。占位符只用于运行时替换，不能把真实用户 ID、昵称或群记录写回资源包。

共享包只保存模板正文和统计信息，不保存用户 ID、昵称、群记录、Token、AI 请求日志或实例本地文案。客户端应把它作为独立来源合并，不能让一次共享文案下载失败阻断图片资源同步。

## 6. manifest 文件清单

### 公有基础包与 Overlay 的共同条目

图片或 JSON 条目的形式都是：

```json
{
  "path": "images/pig.png",
  "size": 10494,
  "sha256": "e22a426d88caeab56a0cb21e507dc74828143bc4f9bd35b26c56b686b5f37e4e"
}
```

`images` 数组额外记录 `id`、`filename`；`variant_images` 额外记录 `pig_id` 和 `level`。文件实体、manifest 路径、大小、SHA256 必须完全一致，不能只更新其中一项。

不同类型的文件清单不能互相冒充：基础包的 `pig_json` 和图片清单描述全量基础快照，Overlay 的 `pig_json` 描述新增条目，`pig_overrides` 只描述覆盖项，共享文案包只使用 `roast_library`。客户端遇到包类型不匹配时应拒绝该包。

### 包类型对 optional files 的限制

| 条目 | 公有基础包 | Overlay | 共享文案 |
| --- | --- | --- | --- |
| `pig_rules` | 可选 | 可选 | 不适用 |
| `pig_overrides` | 禁止 | 可选 | 不适用 |
| `pig_ex_variants` | 可选 | 禁止 | 不适用 |
| `variant_images` | 可选，需配合 EX JSON | 禁止 | 不适用 |
| `roast_library` | 不适用 | 不适用 | 必填 |

## 7. 客户端能力分级与要求

实现方可以按能力分级，不需要一次实现所有扩展。每一级只对声明支持该能力的客户端提出要求：

1. **公有基础包读取**：必须能读取 `pig.json` 与基础图片；不支持云端同步的客户端也可以把它作为随插件发布的静态资源。
2. **完整校验同步**：应该实现 manifest、大小/SHA256、下载预算、暂存、原子激活与旧缓存回退。
3. **Overlay 叠加**：必须实现 Overlay 顺序、`allow_override` 覆盖规则、整包激活和失败隔离，才能宣称支持 Overlay。
4. **EX 差分**：必须按字段独立执行最近低等级继承，并在差分图片损坏时回退基础图片，才能宣称支持 EX。
5. **共享烤猪文案**：必须实现独立同步、占位符填充、来源隔离和失败保留，才能宣称支持共享文案。
6. **GIF小猪**：必须按自身资源和渲染预算解码 GIF，并处理坏图、无帧和超限情况，才能宣称支持 GIF小猪。

生产环境应该额外提供资源版本、已激活 Overlay、跳过包原因和回退状态的可观测信息。只实现第一级的客户端仍然可以正常使用公有基础包，但不应在文档或 UI 中宣称支持云端同步或 Plus 扩展。

## 8. 维护与校验

资源维护者应使用仓库工具生成清单并运行：

```powershell
python tools/check_resources.py
```

修改资源内容时还应提供新的 `resource_version`。不要手工编辑一长串图片哈希；请使用 `tools/build_rollpig_resource_pack.py` 或 `tools/update_private_manifest.py` 生成对应 manifest。
