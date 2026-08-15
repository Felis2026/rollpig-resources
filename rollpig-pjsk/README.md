# RollPig PJSK 主题 Overlay

这个目录是在公有基础包之上追加或覆盖 PJSK 主题内容的独立 Overlay 资源包。

> 支持 manifest 云同步、私有资源配置和**单个 Overlay 叠加**的客户端即可使用本包，不要求支持多个 Overlay。RollPig Plus 可以继续将本包与 GIF小猪 Overlay 及用户自建 Overlay 按顺序叠加；仅支持公有基础包同步的客户端不会自动加载本包。

## 文件说明

- `pig.json`：只放主题新增小猪，不重复存放公有基础包数据。
- `pig_overrides.json`：可选，按 `id` 覆盖公有小猪字段。
- `pig_rules.json`：只放主题规则增量，与公有规则做并集。
- `images/`：主题新增或覆盖图片。
- `manifest.json`：Overlay 发布清单，由构建脚本生成或手动维护。

## 加载与覆盖规则

```text
插件内置资源 < 公有基础包 < PJSK 主题 Overlay
```

如果 Overlay 和公有包出现相同 ID：

- 默认不允许在 `pig.json` 中重复新增，防止意外覆盖。
- 确实需要覆盖时，必须写入 `pig_overrides.json`；插件会按 ID 更新公有小猪字段。

## 资源入口

Overlay 入口文件为 `manifest.json`。
