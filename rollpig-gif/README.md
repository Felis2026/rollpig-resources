# RollPig GIF小猪 Overlay

这个目录是 RollPig Plus 固定加载的 GIF小猪 Overlay。

> RollPig Plus `0.8.2+` 会自动加载该包，用户不需要在私有资源配置中重复添加。

## 内容边界

- 只追加动态小猪，不覆盖公有资源包字段。
- 所有条目均为普通小猪，不写入熟食、售罄、人类或烤猪排除规则。
- 图片使用 `.gif`，文件名必须与 `pig.json` 中的 `id` 一致。

## 兼容性

- **RollPig Plus**：`0.8.2+` 默认自动加载该 Overlay，无需手动配置。
- **RollPig 原版**：现已支持在 `ROLLPIG_PRIVATE_RESOURCE_MANIFESTS` 中配置本包 `manifest.json` 按需加载。
- **其它客户端**：需自行实现 Overlay 同步与 GIF 卡片渲染。

## 资源入口

Overlay 入口文件为 `manifest.json`。
