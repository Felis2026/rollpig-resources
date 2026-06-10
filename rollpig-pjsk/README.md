# PJSK Private RollPig Overlay

这个目录用于 Felis / PJSK bot 的私有小猪外挂包。

## 文件说明

- `pig.json`：只放私有新增猪，不放公有全量。
- `pig_overrides.json`：可选，按 `id` 覆盖公有猪字段。
- `pig_rules.json`：只放私有规则增量，与公有规则做并集。
- `images/`：私有新增或覆盖图片。
- `manifest.json`：私有包发布清单，由构建脚本生成或手动维护。

## 合并优先级

```text
插件内置 < 公有云包 < 私有外挂包
```

如果私有包和公有包出现同 ID：

- 默认不允许重复新增，防止误覆盖。
- 如确实要覆盖，放入 `pig_overrides.json`；插件会按 ID 更新公有猪字段。
