# RollPig Resources

RollPig 小猪资源包仓库。

本仓库采用“公有全量包 + 私有外挂包”的目录结构：

- `rollpig/`：公有全量资源包，可给普通插件实例或上游兼容版本使用。
- `rollpig-pjsk/`：Felis / PJSK bot 专用私有外挂包，只放私有新增或覆盖内容。
- `tools/`：资源包构建、校验、发布辅助脚本。

## 公有全量包

`rollpig/` 是当前可直接发布的完整资源包，包含：

- `manifest.json`
- `pig.json`
- `pig_rules.json`
- `images/*.png`

当前插件同步逻辑会把远端 `pig.json` 当作完整小猪列表，因此公有包必须是全量包，而不是增量包。

## 私有外挂包

`rollpig-pjsk/` 设计为 overlay，不直接替代公有包。

推荐语义：

1. 先加载公有全量包。
2. 再加载私有外挂包。
3. 私有 `pig.json` 只放新增私有猪。
4. 私有 `pig_overrides.json` 可选，用于覆盖公有猪的文案或图片。
5. 私有 `pig_rules.json` 与公有规则做并集。
6. 图片查找顺序为：私有图片 → 公有图片 → 插件内置图片。

注意：当前插件还没有实现 overlay 合并逻辑；现在只是先把资源仓库结构准备好。

## 建议发布路径

公有：

```text
https://pig.felislab.cc/resources/rollpig/manifest.json
```

私有：

```text
https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
```

后续插件建议增加配置：

```env
ROLLPIG_RESOURCE_MANIFEST_URL=https://pig.felislab.cc/resources/rollpig/manifest.json
ROLLPIG_PRIVATE_RESOURCE_MANIFEST_URL=https://pig.felislab.cc/resources/rollpig-pjsk/manifest.json
ROLLPIG_PRIVATE_RESOURCE_TOKEN=可选
```
