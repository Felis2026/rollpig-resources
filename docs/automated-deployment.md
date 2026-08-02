# RollPig 资源自动校验与发布

`.github/workflows/validate-and-deploy.yml` 负责从 GitHub 到生产资源目录的完整发布链路：

```text
Pull Request / push
        ↓
校验 JSON、ID、规则、图片、GIF 预算、manifest 哈希与版本兼容性
        ↓（仅 main，含手动运行 main）
生成归档并计算 SHA256 → 通过已知主机密钥校验的 SSH 上传
        ↓
逐个原子替换四个资源包 → 公网 manifest 与 EX 差分抽样比对 → 成功或自动回滚
```

## 触发规则

- Pull Request：只运行校验，不读取生产 Secrets，也不部署。
- 推送到 `main`：校验通过后自动部署。
- `workflow_dispatch`：可在 Actions 页面手动重新发布当前 `main`。
- 生产切换始终串行执行，正在切换的版本不会被新任务中断；连续多次推送时，以 GitHub 最终保留的待发布任务为准。

## 首次配置

在 `Felis2026/rollpig-resources` 的 `Settings → Environments` 新建或打开 `production`。

添加以下 Environment Secrets：

```text
ROLLPIG_DEPLOY_HOST
ROLLPIG_DEPLOY_PORT
ROLLPIG_DEPLOY_USER
ROLLPIG_DEPLOY_ROOT
ROLLPIG_DEPLOY_SSH_KEY
ROLLPIG_DEPLOY_KNOWN_HOSTS
```

这些名称与 `rollpig-cloud` 的生产部署一致，可以使用同一台服务器的现有值；但 GitHub Environment Secrets 属于具体仓库，仍需在 `rollpig-resources` 仓库中单独配置一次。任何真实 IP、用户名、私钥或主机密钥都不能提交到本仓库。

可选添加 Environment Variable：

```text
ROLLPIG_RESOURCE_PUBLIC_BASE_URL=https://pig.felislab.cc/resources
```

不设置时工作流使用上面的默认地址。`ROLLPIG_DEPLOY_ROOT` 应指向 Cloud 项目根目录；其下必须已经存在 `static/resources/`。服务器还需具备 `tar`、`sha256sum`、`curl`、`cmp`、`find`、`sort`、`awk` 和 `python3`。

建议在 `production` Environment 中只允许 `main` 部署；如希望每次发布前人工确认，可再启用 Required reviewers。

## 校验内容

会阻止发布的错误包括：

- JSON 无法解析、重复字段、字段类型错误、使用非 LF 换行或包含乱码替换字符。
- 小猪 ID 非法、包内或包间重复、已发布 ID 被删除或迁移到其他包。
- 文案必填字段为空，规则或覆盖项指向不存在的 ID。
- 图片缺失、损坏、未登记、manifest 大小或 SHA256 不一致。
- EX 差分 schema、等级、文件名、JSON / manifest / 实体图片对应关系或 Overlay 使用范围不符合协议。
- 共享烤猪文案的结构、占位符、隐私扫描、统计、长期排除表或正文 SHA256 不一致。
- 资源包超过 RollPig Plus 的文件数、字节数、单文件或 GIF 解码预算。
- 资源内容改变但 `resource_version` 没有提升。

尺寸不是 `240x240`、没有透明通道、历史图片实际格式与后缀不一致，以及 GIF 超过 60 帧但仍在安全预算内，只会给出警告。超过 60 帧的 GIF 会由客户端在完整动画周期内均匀压缩到最多 60 帧。

## 本地校验

安装 Pillow 后，在仓库根目录执行：

```powershell
python tools/check_resources.py --base-ref origin/main
```

只检查当前文件、不做已发布版本对比：

```powershell
python tools/check_resources.py
```

警告也需要作为失败处理时使用：

```powershell
python tools/check_resources.py --strict-warnings
```

## 共享文案包维护

`tools/build_roast_library.py` 是公开的离线构建与审核工具，供维护者或投稿者从自己的 `roast_library.json` 生成候选共享包。它只读取命令行指定的本地文件，不会连接 RollPig Cloud、上传文案或读取任何 Token。

生成候选包时必须将审核报告输出到仓库外的临时目录：

```powershell
python tools/build_roast_library.py `
  --source "路径\roast_library.json" `
  --repo-root . `
  --version "roasts-YYYY-MM-DD.1" `
  --min-plugin-version "0.10.0" `
  --report-dir "路径\review-report" `
  --dry-run
```

`--dry-run` 会在 `<review-report>/candidate-package/` 生成候选包，不会替换仓库中的正式资源。任何人都可以用它整理自己的文案，但生成候选包不代表拥有官方资源发布权限；合入本仓库前仍需人工检查拒绝项、隐私扫描结果和文案质量。

## 发布与回滚边界

部署包只包含 `rollpig/`、`rollpig-gif/`、`rollpig-pjsk/` 和 `rollpig-roasts/`，不会上传 Cloud 代码、Compose、数据库文件或任何私密手册。

服务器不会替换 `static/resources` 挂载根目录，而是逐个原子替换它下面的四个资源包。切换后会带本次 commit SHA 请求公网 manifest，并与服务器新文件逐字节比较；若公有包带 EX 差分，还会校验差分 JSON 以及首、中、末抽样图片的 SHA256。任一步失败都会恢复本次发布前的四个目录。GitHub Runner 随后再从独立网络重复核对 manifest 与差分抽样；成功后保留最近 5 个回滚点：

```text
<ROLLPIG_DEPLOY_ROOT>/.deploy/resources/backup/<commit SHA>/
```

资源是静态只读挂载，正常发布不需要 build，也不需要重启 `rollpig-cloud`。
