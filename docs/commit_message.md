# Conventional Commits - 约定式提交

Conventional Commits（约定式提交），它脱胎于 Angular 提交规范，现在被大量开源项目和企业团队采用。

### 📌 核心格式

```text
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**：提交类型，必填。
- **scope**：影响范围，可选，比如模块名、文件名。
- **subject**：简短描述，必填。
- **body**：详细说明，可选。
- **footer**：破坏性变更、关联 Issue，可选。

### 🏷️ 常用 type

| type       | 含义                                 |
| :--------- | :----------------------------------- |
| `feat`     | 新功能                               |
| `fix`      | 修复 bug                             |
| `docs`     | 只改文档                             |
| `style`    | 格式调整，不影响逻辑（空格、分号等） |
| `refactor` | 重构，不是新功能也不是修 bug         |
| `perf`     | 性能优化                             |
| `test`     | 增加或修改测试                       |
| `build`    | 构建系统或依赖变更                   |
| `ci`       | CI 配置变更                          |
| `chore`    | 杂项，不修改 src 或 test             |
| `revert`   | 回滚某个提交                         |

### ✅ 好的示例

```text
feat(auth): 支持微信扫码登录
fix(api): 修复分页参数越界导致 500 的问题
docs(readme): 补充本地启动步骤
refactor(user): 抽离用户校验逻辑到独立函数
perf(query): 为订单列表增加复合索引
```

带正文和脚注的完整示例：

```text
fix(order): 修复优惠券重复抵扣问题

订单结算时，同一张优惠券可能被多次应用。
现在在应用优惠券前增加已使用校验。

Closes #123
```

破坏性变更：

```text
feat(api)!: 移除 v1 用户接口

BREAKING CHANGE: /api/v1/user 已删除，请迁移到 /api/v2/user。
```

### ✍️ 主题行（subject）的写法建议

- 用**祈使句、现在时**：`修复登录超时`，而不是 `修复了登录超时`。
- 首字母小写或大写看团队习惯，中文无所谓。
- **结尾不加句号**。
- 长度尽量控制在 **50 个字符以内**，最多不超过 72。
- 说清楚“做了什么”，不要写 `update`、`fix bug`、`修改` 这种无意义描述。

### 📄 正文（body）写什么

- 空一行后开始。
- 解释 **为什么改**、**改了什么**，而不是“怎么改”。
- 每行建议 72 字符换行。
- 如果改动简单，可以省略正文。

### 🔗 脚注（footer）常用

- `Closes #123`：关闭 Issue。
- `Fixes #456`：修复 Issue。
- `BREAKING CHANGE: ...`：破坏性变更，必须大写。

### 🚫 常见反例

```text
update
fix bug
修改
提交
111
```

这些提交信息在 review、回滚、生成 CHANGELOG 时基本没有价值。

### 🛠️ 工具推荐

- **commitizen**：交互式生成规范提交信息。
- **commitlint**：配合 husky，在 commit 时校验格式。
- **standard-version / semantic-release**：根据提交自动生成 CHANGELOG 和版本号。
- **VS Code 插件**：`Conventional Commits` 可以帮你快速选择 type。

### 💡 团队落地建议

1. 个人项目：至少做到 `type: 简短描述`。
2. 团队项目：用 Conventional Commits + commitlint 强制校验。
3. 如果团队习惯中文，type 保持英文，subject 和 body 用中文完全没问题。
4. 一个提交只做一件事，尽量原子化，方便回滚和 cherry-pick。

一句话总结：**用 `type(scope): subject` 开头，说清楚改了什么和为什么，别写“update”这种废话。**
