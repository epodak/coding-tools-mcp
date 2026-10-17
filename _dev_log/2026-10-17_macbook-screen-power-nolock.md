# 2026-10-17 MacBook 屏幕功耗调控与免锁屏静默守护方案落地

## 1. 需求与核心目标

用户需求：
1. MacBook Betty 长时间无人操作时，屏幕仅降低至最低亮度或完全黑屏（关闭背光省电、防烧屏防刺眼）；
2. **严禁进入锁屏状态**：用户重新触碰触摸板或按下任意键时，屏幕瞬间点亮恢复原亮度，无需输入任何登录密码；
3. **后台业务绝对不休眠**：SSH、MCP 服务、Python/Node 任务在黑屏期间保持 100% 算力与网络在线；
4. **工具体系能力嫁接**：分析并实现现有工具栈（CLI、LaunchAgent 守护进程、MCP 工具服务）如何将该能力标准化接入。

---

## 2. macOS 底层原理与技术选型

### 2.1 系统级免锁屏（Zero-Password Unlock）
macOS 默认在屏幕休眠或屏保启动后要求密码，由 `com.apple.screensaver` 控制。
通过配置用户域和 CurrentHost 域彻底关闭密码锁：
```bash
defaults write com.apple.screensaver askForPassword -int 0
defaults -currentHost write com.apple.screensaver askForPassword -int 0
defaults write com.apple.screensaver askForPasswordDelay -int 2147483647
```
经实测，唤醒时系统直达当前桌面上次工作状态，零弹窗、零锁屏界面。

### 2.2 原生无 root 背光调控
macOS 系统命令 `pmset -a displaysleep` 需要 root 权限，但调用 CoreGraphics 私有 C 接口 `DisplayServicesSetBrightness` 无需任何 sudo 权限，直接在用户 Aqua WindowServer 会话中生效：
- `DisplayServicesGetBrightness(CGMainDisplayID(), &b)`：获取物理屏幕当前真实亮度（0.0 ~ 1.0）；
- `DisplayServicesSetBrightness(CGMainDisplayID(), 0.0)`：将背光完全拉低至 0.0（纯黑屏，硬件级关背光，几乎等同屏幕断电）；
- `pmset displaysleepnow`：触发 Display Sleep，系统同样执行免密码瞬醒。

### 2.3 物理输入闲置探测
利用 CoreGraphics 原生 C 函数：
`CGEventSourceSecondsSinceLastEventType(1, 0xFFFFFFFF)`
以 0 CPU 负担实时获取距离用户上一次物理移动鼠标或按键的秒数。

---

## 3. 三层架构落地实施

### 第一层：原生编译型控制工具 `mac-screen`
- **语言**：Swift 原生编译（约 59 KB x86_64 二进制）
- **路径**：`/Users/fenglu/.local/bin/mac-screen`
- **核心命令**：
  - `mac-screen status`：输出当前亮度与百分比 JSON。
  - `mac-screen black` / `off`：平滑渐变至 0.0 黑屏。
  - `mac-screen wake` / `on`：恢复至预存亮度或指定亮度。
  - `mac-screen dim`：降至微光（0.01）。
  - `mac-screen set <0.0-1.0>`：精准设置亮度。
  - `mac-screen nolock`：一键加固关闭锁屏密码。

### 第二层：自动闲置感知常驻守护进程 `com.user.macscreen`
- **脚本**：`/Users/fenglu/.local/bin/screen_idle_daemon.py`
- **机制**：
  1. 派生 `caffeinate -s -i -m`，彻底抑制系统睡眠和磁盘断电；
  2. 循环轮询用户物理输入空闲时间；
  3. 当闲置达到 300 秒（5分钟）时，自动记录当前亮度并平滑将背光渐隐至 0.0；
  4. 当检测到物理输入恢复（`idle < 3.0`），瞬间点亮并平滑恢复至原亮度；
  5. 期间后台 MCP 服务、网络连接与正在运行的脚本无任何中断。
- **配置**：`~/Library/LaunchAgents/com.user.macscreen.plist`，由 macOS `launchd` 托管，开机自启并自动保活。

### 第三层：固化至 MCP 服务端 `coding_tools_mcp`
- **新增工具**：`manage_screen_power`
- **参数契约**：
  - `action`: `status` | `black` | `dim` | `wake` | `on` | `set` | `nolock`
  - `brightness`: 可选浮点数 `0.0` ~ `1.0`
- **部署状态**：已部署至 MacBook Betty 的 `coding-tools-mcp` 服务中（`launchctl kickstart -k gui/501/com.user.codingmcp`），已由 pytest 全量验证通过。

### 第四层：Windows 终端跨端穿透
- **真源脚本**：`C:\Users\root\diy_py_script\mac_screen.py`
- **双子包装器**：`D:\Tool\DIY\mac-screen` 与 `D:\Tool\DIY\mac-screen.cmd`
- **体验**：在 Windows CMD / PowerShell / Git Bash 中敲击 `mac-screen status`、`mac-screen black`、`mac-screen wake` 直通 MacBook 控制。

---

## 4. 实测验证数据

1. **亮度与状态读数**：
   ```json
   {"brightness": 0.6425781, "percentage": "64.3%"}
   ```
2. **密码锁屏禁用**：
   ```json
   {"action": "disable_lock_screen", "success": true, "message": "Lock screen password requirement disabled. Screen will dim/black without locking."}
   ```
3. **守护进程运行状态**：
   - PID `20029`: `screen_idle_daemon.py` 存活。
   - PID `20035`: `caffeinate -s -i -m` 存活。
   - PID `20066`: `coding-tools-mcp` (端口 42180) 存活。
4. **单测验收**：
   - `tests/test_workspace_mutation.py` 23/23 全部通过（包含 schema 严格验证）。
