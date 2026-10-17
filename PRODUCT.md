# Coding Tools MCP (自主可控定制版)

## Platform

CLI / MCP Server (HTTP & Stdio)

## Users

- 远程/本地使用 ChatGPT、Claude、Claude Code、Cursor、Antigravity 的 AI 开发者与智能体。
- 需要远程操控受控终端、执行文件分析、代码重构、桌面资料分类与本地工具链调用的开发团队。

## Product Purpose

提供一套高性能、自包含、支持全盘路径穿透（Unconfined）的通用编程工具 MCP 服务。突破上游强制沙箱限制，让授权的远程智能体能够跨目录、跨磁盘读写文件，执行命令，查看图片，同时保留原生 OAuth 2.1 与 Cloudflare 远程通道。

## Positioning

- **对比官方 xyTom/coding-tools-mcp**：官方版本强制把 workspace 限定在狭窄目录，彻底禁止 `~`、`/`、跨盘符绝对路径与软链接，在真实研发、跨项目协作中频繁报 `PATH_OUTSIDE_WORKSPACE`。本项目引入 `--unconfined` 与 `CODING_TOOLS_MCP_UNCONFINED=1`，一键解锁全盘控制。
- **对比传统 SSH / 执行终端**：提供结构化 MCP 协议，支持原子补丁（`apply_patch`）、行级修改（`apply_changes`）、图片分析（`view_image`）、结构化目录树与命令状态生命周期。

## Operating Context

- **本地模式**：`coding-tools-mcp --stdio` 作为本地 IDE 的后端。
- **远程长常驻模式**：配合 LaunchAgent / Cloudflare Tunnel / Ngrok，在远程服务器或 MacBook 上通过 HTTP + OAuth 2.1 暴露 `/mcp`，由官方 ChatGPT / Claude 移动端或网页端远程连接。

## Capabilities

1. **文件与目录操作**：`read_file`, `write_file`, `list_dir`, `list_files`, `search_text`, `view_image`。
2. **精准代码变更**：`apply_patch` (V4A envelope), `apply_changes`。
3. **安全命令执行**：`exec_command`, `stream_command_output`, `send_command_input`, `kill_command`, `check_exec_environment`。
4. **Git 全流程**：`git_status`, `git_diff`, `git_log`, `git_show`。
5. **服务元数据**：`server_info`。
6. **全盘穿透模式**：`--unconfined` 开关与环境变量支持。
