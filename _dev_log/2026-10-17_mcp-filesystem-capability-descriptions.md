# MCP 文件访问能力描述校准

日期：2026-10-17（用户时区）。

## 用户诉求与边界

修正工作区之外实际可读、但模型根据描述宣布无权访问的能力声明。只改变元数据和描述，不放宽路径校验、系统 ACL、OAuth、执行权限或工作区写入策略。

## 仓库实现

- `Runtime.filesystem_policy_payload()` 读取有效的 `Workspace.unconfined`，独立于 safe/trusted/dangerous 模式；披露相对路径基准、工作区是否为边界、绝对路径、home 简写、工作区外软链接与系统权限约束。
- `tools/list` 为真正使用路径解析器的 7 个文件工具生成实例级说明；静态注册表保持中性，不污染共享 schema 或其他 Runtime。
- `server_info` 增加可选 `filesystem_policy` 结构及模型可读文本，保留原字段。
- 同步旧版 `initialize.instructions` 与新版 `discovery.instructions`；消除 ProjectContext 中写死的“仅限工作区”声明，并保留用户授权范围及项目指令。
- 规范字段真源在 `docs/runtime-contract-v0.3.md`，工具目录只链接，不复制长说明。

## 验证

1. 新增 8 项测试，先验证缺字段和握手矛盾能够失败，再实现并通过；含六组模式/范围组合、环境变量实际生效、实例描述隔离、真实绝对路径拒绝、真实 home/绝对路径读取、模型可读文本与 schema、握手与发现，以及真实 CLI stdio MCP 冷启动验证。
2. 针对性组合 44 项：11 项既有平台跳过，其余通过。命令：
   `python -m unittest tests.test_workspace_mutation tests.compliance.test_schema_drift tests.compliance.test_tool_golden tests.compliance.test_runtime_helpers.RuntimeHelperTests.test_server_info_and_check_exec_environment_expose_exec_state tests.compliance.test_runtime_helpers.RuntimeHelperTests.test_runtime_and_server_info_do_not_create_exec_dirs -q`
3. Ruff 检查通过；`git diff --check` 通过。
4. 微变异在独立副本将自报强制改为开放，触发 12 个断言/子用例失败，证明测试能识别假能力声明；原工作树未被变异。
5. 较广回归当前 284 项，基线 HEAD 276 项；两者均 15 failures、19 errors、87 skipped，具名失败集合相同，无新增失败。主要为 Windows 换行、平台环境、symlink 与进程清理等既有问题。本轮未宣称广泛回归全绿，也未越界修复这些问题。对照结果保存在被忽略的 `.agents/tmp/metadata-baseline-comparison.json`。

## MacBook 部署

- 现有安装位于 `/Users/fenglu/.local/share/uv/tools/coding-tools-mcp/lib/python3.12/site-packages/coding_tools_mcp/`，不是当前仓库的完整同版本副本；含两个额外业务文档工具，路径解析器既有实现已开放。
- 不覆盖整个包。通过 SSH 对 3 个文件作最小 AST/精确文本补丁，首先校验原始 SHA-256、编译候选、备份；校验所有路径处理方法的 AST 未改变。旧版 Workspace 仅增加反映既有开放行为的元数据属性。
- 修改 `server.py`、`tool_results.py`、`project_context.py`；保留额外工具、现有认证、运行模式和启动配置。
- 备份：`/Users/fenglu/.local/state/coding-tools-mcp/metadata-backups/20261017T041505Z/`。异常时脚本会恢复三份原件；需要人工回滚时可恢复该目录原件后重启相同 launchd 服务。
- 首次部署因已存在的自定义目录描述与预期文本不一致，匹配检查停止在写入前；核实原文后第二次成功。未盲目覆盖远端定制。
- 冷加载验证 20 个工具不变，9 个文件/业务文档工具描述均包含真实路径范围；握手、发现、结构化结果和文本一致。真实绝对桌面路径与 `~/Desktop` 均读取成功。
- 使用 `launchctl kickstart -k gui/501/com.user.codingmcp` 重启服务。
- 原 MCP 连接重启后返回 `ok=true`、`auth_enabled=true`、`permission_mode=trusted`、`dangerously_skip_all_permissions=false`，且新字段 `filesystem_policy.confinement=unconfined`；通过原连接读取 `~/Desktop` 成功。

## 保留的不确定性

服务端已部署并经原连接验证，但未直接操作网页版重新加载缓存工具列表。若网页版继续显示旧描述，需要刷新该 MCP 工具列表或重新连接；不能将服务端验证冒充网页版端到端验收。
