# RollPig GIF小猪 Overlay

这个目录是 RollPig Plus 固定加载的 GIF小猪 Overlay。

> RollPig Plus `0.8.2+` 会自动加载该包，用户不需要在私有资源配置中重复添加。

## 内容边界

- 只追加动态小猪，不覆盖公有资源包字段。
- 所有条目均为普通小猪，不写入熟食、售罄、人类或烤猪排除规则。
- 图片使用 `.gif`，文件名必须与 `pig.json` 中的 `id` 一致。

## 兼容性

该包需要配合支持 GIF小猪 Overlay 的 RollPig Plus 使用；上游原版不会自动加载该 Overlay。

## 资源入口

Overlay 入口文件为 `manifest.json`。
