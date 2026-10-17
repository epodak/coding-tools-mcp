# Mac MCP 完整重装与 ChatGPT 工具更新

- 日期：2026-10-17（用户时区）。
- 调度任务：task-mvbws49s-708328b8，服务与账户重装均已完成。
- 指定真源：D:/_AI/10_DOING/2026-10-17_coding-tools-mcp，开始时 Git HEAD=0e5760c，原工作树干净。

## 检查事实与根因

- Mac：FengdeMacBook-Pro.local，macOS 11.7.10；入口 ~/.local/bin/coding-tools-mcp，端口 42180。
- 旧安装已存在 --unconfined 能力与三个新工具代码，但多个模块并非同版本。
- 当前会话直接调用 server_info 失败：SessionTelemetry.record_tool_call() got an unexpected keyword argument 'already_applied'。
- 核实远端 telemetry.py 的方法确实没有该参数；指定仓库中的版本包含该参数，说明不能继续只覆盖 server.py。
- ChatGPT 旧插件 list_dir 缓存说明仍声称工作区外路径被拒绝，与更新后的真实能力矛盾。

## 实际变更

- 新增维护脚本 scripts/reinstall_mac_mcp.py：preflight、install、callback、probe 四阶段，默认仅帮助。
- 从完整指定仓库构建纯 Python wheel：coding_tools_mcp-0.5.0-py3-none-any.whl。
- SHA256：26c0b15638fd3a95f3e0dff8e60d7696d068273336cdcc8ea6a73b6d5c69f88d；Mac 写入前核对相同哈希。
- /tmp/mac-mcp-upgrade-candidate 独立环境离线安装并真实运行 JSON-RPC。
- 备份旧工具环境与 LaunchAgent：/Users/fenglu/.local/state/coding-tools-mcp/reinstall-backups/20261017T044601Z。
- 实际执行 uv tool uninstall coding-tools-mcp，再离线安装已校验的完整 wheel，不是仅修改缓存描述。
- 保留既有 OAuth 凭据、签名密钥与回调；命令权限 trusted，禁用假只读，显式配置 unconfined；关闭产品遥测。保留现有原生 desktop_tip 二进制、业务文件与软链接。
- 服务重新加载后 PID 19538；通过原连接 server_info 已真实成功，不再触发 telemetry 参数错误。
- 旧 ChatGPT 插件 plugin_asdk_app_6ad22ee928ec81919c9bf22ee50c8c32 已由专用卸载工具返回 uninstalled。只卸载 macbook-betty，没有操作 winmcp。

## 验收证据

- 候选安装与正式安装均通过真实 stdio CLI 冷启动：initialize、tools/list、server_info、list_dir、read_project_document、exec_command。
- 实际工具总数为 **21**，不是历史日志声称的 22；包含 list_project_tree、read_project_document、show_desktop_tip。
- filesystem_policy.confinement=unconfined，workspace_is_access_boundary=false，absolute_paths_allowed=true，home_paths_allowed=true。
- 实际读取桌面目录、工作区外 ~/AGENTS.md，且通过绝对 Desktop 工作目录执行 hostname/uname，返回成功。
- 扩展探测通过：~/Documents、~/Downloads、默认项目树与五秒静音桌面提示启动；没有读取业务文档正文。
- 原生提示只验证工具返回 displayed=true 与成功启动，未在 Mac 屏幕上独立截图，因此不把它表述为已视觉验收。
- 本地针对性测试 42 项：30 通过、11 平台跳过、1 既有文档目录漂移失败（三个新增工具尚未写入 docs/tools-and-schemas.md）。未修改业务源码或刷掉该失败；未宣称全绿。
- 维护脚本编译通过；环境未安装 Ruff，未宣称通过 Ruff；git diff --check 通过。

## 账户阶段（等待确认时的阶段记录）

- 用户已请求卸旧装新；由于新版扩大 ChatGPT 对 Mac 的访问范围，已在实际重装时请求一次明确确认。
- 截至本记录，确认尚未回复，故没有擅自重新授予账户访问权限。
- Chrome 已打开原自定义插件页面，显示“安装插件”，待确认后继续安装、OAuth 授权及“刷新工具”，同步 21 个工具的新说明。
- 服务端已完成，不代表账户重装已完成；当前任务不标记 done。
- 安全边界：unconfined 是路径策略放开，不是绕过 macOS TCC/ACL；Mac 无 Linux Landlock，不能声称命令具有完整 OS 文件系统沙盒。
- 不复制 OAuth 密码、令牌或业务文件内容至 Git；备份含敏感启动配置，仅留在 Mac 用户私有目录。

## 用户确认后的账户重装验收

- 用户明确回答“确认，卸载旧连接并安装新版”，允许 Mac 当前用户有权访问的工作区外目录及新增桌面提示能力。
- 点击原专属插件的“安装插件”，使用新打开的 OAuth 授权标签页完成现有 Mac 客户端认证；未创建重复同名插件，保留原插件身份与链接。
- 管理页确认已连接账户 Primary，关联日期 2026年10月17日，URL 仍为 https://betty-mcp.daduiot.com/mcp，认证方式 OAuth。
- 点击“刷新工具”后完成扫描；详情工具面板显示 Write 5、Read 16，合计 21。三个新增工具均在列表。
- 直接读取 ChatGPT 工具面板确认 list_dir/read_file/list_files/search_text 等描述包含：工作区不是访问边界、绝对路径和 home 简写及工作区外软链接允许。旧的“仅限工作区”缓存描述已在网页版完成替换，不再仅靠服务端旁路证明。
- 新连接继续采用“允许低风险操作”的默认确认偏好，没有为了免确认发信/修改文件而设置全部允许。
- 安全扫描显示“警告”，未伪装为无风险；安装状态及工具目录可用。新增 HUD 在目录中归为 Read，但 html_content 会写报告文件，这一源代码注解边界需另行审查，本次没有擅改用户新增工具实现。
- 当前这条 Codex 聊天在卸载/重装后保留了旧的工具路由：两次本会话直接调用返回 Unknown tool，而不是源站的遥测报错。不继续重复调用；本次未将旧路由错误冒充新版连接调用成功。
- 验证边界：正式安装前/后真实 MCP 协议及跨目录读取已通过，重新安装后 OAuth 与网页版新工具目录已验证；本会话重新加载后的直接工具调用留待下一个工具快照验证。
- 用户无需再输入端点或创建第二个连接。原 Mac 插件地址不变：https://chatgpt.com/plugins/plugin_asdk_app_6ad22ee928ec81919c9bf22ee50c8c32 。Windows winmcp 未卸载、未更新配置。
