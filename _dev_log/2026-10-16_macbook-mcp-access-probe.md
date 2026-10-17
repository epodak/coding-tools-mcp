# macbook-betty MCP 访问能力与元数据一致性核验

日期：2026-10-16（用户时区）。

## 范围与结果

- 通过连接器核对设备身份与 server_info，远端为 macOS、coding-tools-mcp 0.5.0，permission_mode=trusted。
- 对用户指定项目递归列举：50 文件、5 子目录，清单未截断；分析 9 份正式工作簿共 57 工作表、13 PDF 共 45 页、6 份正式 Word。未将商业文件或细节复制进仓库。
- 分别调用 list_dir 检查远端桌面绝对路径、home 简写以及小写目录拼写，均 ok=true；每次主动限制 3 条，截断只因 entry limit。
- server_info 返回的 permission_mode 与路径 confinement 不能混同；本地 Workspace.resolve_existing 将 unconfined 单独处理，与 trusted 模式并非同一个配置轴。
- 已查看当前工具描述与本地源码：list_dir/read_file 的描述仍称 inside the configured workspace。当前实际访问行为与这句话的潜在解释存在落差。

## 判断与建议（未实施）

1. 本次不能复现真实桌面权限拒绝，但不能由现在的成功倒推网页版历史调用一定成功；需对应原始工具参数、结构化错误、实例及配置。
2. 建议 server_info 显式返回有效文件访问策略（confined/unconfined、路径语法、默认基准目录），工具描述随有效策略匹配，并保留系统 ACL 限制。
3. 对用户已指定读取的路径，应先做小范围只读探测；返回拒绝时报告实际错误，而非凭 workspace 字段宣布无权。
4. 不建议因此扩大 workspace 到整盘、禁用鉴权或打开 dangerous；本轮未更改任何运行权限或服务配置。

## 排障与验证边界

- 一次 max_depth=30 请求在连接器 schema 校验失败，改为上限 20 后成功；这是调用参数错误，不是主机权限错误。
- 远端缺少文档解析依赖，使用 uv 临时缓存提供只读提取；原始文件不覆盖、不重算。临时提取文件位于 MCP 的 runtime tmp。
- 扫描 PDF 用渲染核对，不把无可抽取文本视为无内容。
- 未进入 SSH、未改代码、未声称网页版端到端已修复。缺少原始网页拒绝日志。
- 官方文档确认工具描述影响选择且应准确匹配行为：https://developers.openai.com/plugins/plan/tools ，https://developers.openai.com/plugins/plugin-guidelines 。

## 隐私与交付

商业目录清单与分析另存到当前聊天的本地输出目录，不包含邮箱口令或银行账号。认知记录保存在项目 .agents/（遵循仓库现有忽略策略），本日志仅保留技术核验事实。
