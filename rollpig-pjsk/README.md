# RollPig PJSK Overlay

这个目录是 Felis PJSK Bot 使用的专用小猪 Overlay，在公有全量包之上追加或覆盖 PJSK 专属内容。

> 该包需要配合支持多 Overlay 的 RollPig Plus 使用，并由 Bot 管理者手动追加到私有资源配置。

## 文件说明

- `pig.json`：只放专属新增小猪，不重复存放公有全量数据。
- `pig_overrides.json`：可选，按 `id` 覆盖公有小猪字段。
- `pig_rules.json`：只放专属规则增量，与公有规则做并集。
- `images/`：专属新增或覆盖图片。
- `manifest.json`：Overlay 发布清单，由构建脚本生成或手动维护。

## 加载与覆盖规则

```text
插件内置资源 < 公有全量包 < PJSK 专用 Overlay
```

如果 Overlay 和公有包出现相同 ID：

- 默认不允许在 `pig.json` 中重复新增，防止意外覆盖。
- 确实需要覆盖时，必须写入 `pig_overrides.json`；插件会按 ID 更新公有小猪字段。

## 资源入口

Overlay 入口文件为 `manifest.json`。
