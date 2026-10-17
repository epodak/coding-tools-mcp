# 2026-10-17 实现日志：固化 AppKit 原生 HUD 悬浮提示与自动化网页报告能力至 MCP 服务端

## 1. 任务背景与核心诉求
用户在使用 ChatGPT 连接 MacBook Betty 上的 `coding-tools-mcp` 对桌面项目 `01_Evenswiss (当前新工作项目)` 进行文件治理时，ChatGPT 临时生成了一个 AppKit 原生悬浮提示程序（`evenswiss_tip`），在屏幕右上角弹出了毛玻璃卡片，并带有“查看网页版详情 ↗”按钮，点击可在系统默认浏览器中打开 HTML 离线审计报告。
用户非常认可这一物理交互体验，提出需求：**将该 AppKit 原生悬浮气泡能力作为标准 MCP 工具固化进服务中**，使任何调用 MCP 的 AI（ChatGPT、Claude、Antigravity 等）在完成批处理或阶段性任务后，都能随手弹出 HUD 提示，并联动生成/打开网页报告。

同时，排查了 ChatGPT 在执行 `Plasma_261006` 子目录文件重命名时误报“权限受限（blocked: 2）”的根因。

---

## 2. 根因排查与问题定位

### 2.1 "权限受限"的物理真因
- **现象**：ChatGPT 重命名了 21 个文件，但在 `Plasma_261006/2. MSDS-outer cap.pdf` 等 2 个文件处触发 `PermissionError`，导致重命名停止。
- **真相**：检查 `/Users/fenglu/Desktop/01_Evenswiss (当前新工作项目)/收到的资料/Plasma_261006` 目录权限，发现其权限模式为 `dr-xr-xr-x`（只读，无 `w` 写权限，源于解压或归档包的默认属性）。在 POSIX 文件系统中，重命名目录内的文件需要对父目录具有写权限（修改目录项）。这与 MCP 本身的权限策略无关，纯属宿主系统目录属性。
- **修复**：对项目目录执行 `chmod -R u+w '/Users/fenglu/Desktop/01_Evenswiss (当前新工作项目)'`，写权限完全恢复（`drwxr-xr-x`）。

### 2.2 CLI 复杂参数跨环境转义死穴
- 在 Windows PowerShell ➔ SSH ➔ macOS zsh 链路下，JSON 字符串中的双引号极易被剥除或转义失效（如变成 `{\ title\: ...}`），导致 Swift 的 `JSONDecoder` 解析失败回退到默认参数。
- **方案**：Swift 客户端增加 `--json-base64 <b64>` 支持，Python 端直接对 JSON 进行 UTF-8 编码并 Base64 转换，彻底杜绝转义与特殊字符问题。

---

## 3. 具体实现与架构落地

### 3.1 原生 Swift AppKit HUD 程序 (`desktop_tip.swift`)
- 源码落盘于 `coding_tools_mcp/desktop_tip.swift`。
- 使用 `/usr/bin/swiftc -O` 编译为 94 KB 静态二进制，安装到 `/Users/fenglu/.local/bin/desktop_tip`。
- **视觉遵循 Oceanic Crisp 冰川瓷白与 Apple Design 规范**：
  - `NSPanel` 浮动层级（`.floating`），右上角微悬浮（`width: 416, height: 176, radius: 16`）；
  - `NSVisualEffectView(.popover)` 纯净毛玻璃质感，0.5px `separatorColor` 细腻边框；
  - 5px 左侧高亮色条，支持 `teal`（冰川青蓝）、`green`（成功绿）、`orange`（告警橙）、`blue`、`purple`；
  - 主动播放 macOS 原生 `Glass` 提示音；
  - 自动淡出定时器（支持自定义 `duration_seconds`，默认 45 秒，淡出动画 0.35s 后自动优雅退出，避免长期常驻占用内存）；
  - 双模输入支持：`--json-base64`（推荐）、`--json-file` 与位置参数兼容。

### 3.2 MCP 服务端工具抽象 (`show_desktop_tip`)
在 `coding_tools_mcp/server.py` 中完整接入：
1. **`TOOL_REGISTRY` 注册**：
   - 标题：`Show desktop tip`
   - 说明：在用户桌面展示 AppKit 悬浮卡片并支持打开浏览器报告。
2. **输入 Schema (`input_schemas`)**：
   - `title`: 标题（必填）
   - `message`: 正文摘要（必填）
   - `action_url`: 浏览器打开的 URL 或本地 HTML 路径（可选）
   - `action_label`: 按钮文本（默认 `查看网页版详情 ↗`）
   - `html_content`: **一键落盘报告**——直接传入 HTML 正文，工具自动在 `reports/` 下生成 `.html` 并关联到按钮！
   - `report_name`: 可选报告文件名
   - `duration_seconds`: 停留时间（5~300秒，默认45）
   - `style`: 主题色（`teal`/`green`/`orange`/`blue`/`purple`）
   - `sound`: 是否播放提示音（默认 True）
3. **输出 Schema (`output_schemas`)**：
   - 返回 `status` ("displayed"), `action_url`, `report_path`, `displayed` (True), `pid`。
4. **运行时方法 (`Runtime.show_desktop_tip`)**：
   - 自动解析工作区路径 `self.workspace.root`；
   - 自动将相对路径转换为 `file://...` URI；
   - 跨进程使用 `start_new_session=True` 与 `subprocess.DEVNULL`，脱壳运行，不阻断 MCP 的 JSON-RPC 请求。

### 3.3 工具生态对齐
同步补齐了此前由 ChatGPT 提议的专有文件工具：
- **`list_project_tree`**：预设 `01_Evenswiss (当前新工作项目)`，递归深度 10；
- **`read_project_document`**：大文本安全切片读取。

---

## 4. 验证结果与数字

| 验证项 | 预期 | 实际结果 | 状态 |
|---|---|---|---|
| `desktop_tip.swift` 编译 | 成功生成 x86_64 二进制 | 生成 94,032 字节可执行文件 | ✅ 通过 |
| `--json-base64` 命令行测试 | 成功解析中文多行并自动退出 | 退出码 0，精确定时平滑淡出 | ✅ 通过 |
| `Runtime.show_desktop_tip` Python 调用 | 返回 displayed 字典且拉起 HUD | 返回 PID 19394, `displayed: True` | ✅ 通过 |
| `launchd` 服务热重载 | com.user.codingmcp 正常运行 | PID 19401, 端口 42180 正常监听 | ✅ 通过 |
| `epodak/coding-tools-mcp` Git 仓库 | 代码提交并同步推送到 GitHub | Commit `3f11366` 已推送至 main | ✅ 通过 |
| `Plasma_261006` 目录写权限 | 恢复用户写权限 | `drwxr-xr-x`，可进行文件重命名 | ✅ 通过 |

---

## 5. 后续与留痕
- LaunchAgent 服务端已全面支持 22 个工具；
- `AGENTS.md` 已为后续连接的所有智能体更新了提示词与交互契约。
