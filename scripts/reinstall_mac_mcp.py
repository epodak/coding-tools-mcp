"""一次性 Mac 安装维护：默认帮助，preflight/ install/ callback 分阶段执行。

真源路径：D:/_AI/10_DOING/2026-10-17_coding-tools-mcp/scripts/reinstall_mac_mcp.py
Wrap 命令：无；通过 Mac 已有 Python 直接调用，不注册全局入口。
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HOME = pathlib.Path.home()
UV = HOME / '.local/bin/uv'
PLIST = HOME / 'Library/LaunchAgents/com.user.codingmcp.plist'
INSTALL = HOME / '.local/share/uv/tools/coding-tools-mcp'
CANDIDATE = pathlib.Path('/tmp/mac-mcp-upgrade-candidate')


def run(args: list[str], **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=120, **kwargs)


def stdio_check(python: pathlib.Path, *, extended=False):
    """无 Mock：真实启动候选 CLI，经 JSON-RPC 调用文件与命令工具。"""
    calls = [
        ('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'mac-upgrade-preflight', 'version': '1'}}),
        ('tools/list', {}),
        ('tools/call', {'name': 'server_info', 'arguments': {}}),
        ('tools/call', {'name': 'list_dir', 'arguments': {'path': '~/Desktop'}}),
        ('tools/call', {'name': 'read_project_document', 'arguments': {'path': '~/AGENTS.md', 'end_line': 2}}),
        ('tools/call', {'name': 'exec_command', 'arguments': {'cmd': 'hostname; uname -s', 'workdir': str(HOME / 'Desktop'), 'yield_time_ms': 10000}}),
    ]
    if extended:
        calls.extend([
            ('tools/call', {'name': 'list_dir', 'arguments': {'path': '~/Documents', 'max_entries': 1}}),
            ('tools/call', {'name': 'list_dir', 'arguments': {'path': '~/Downloads', 'max_entries': 1}}),
            ('tools/call', {'name': 'list_project_tree', 'arguments': {'max_depth': 1, 'max_entries': 1}}),
            ('tools/call', {'name': 'show_desktop_tip', 'arguments': {'title': 'Mac MCP 更新验证', 'message': '新版文件访问与桌面提示工具已加载。', 'duration_seconds': 5, 'sound': False}}),
        ])
    wire = ''.join(json.dumps({'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params}) + '\n' for i, (method, params) in enumerate(calls, 1))
    env = dict(os.environ, DO_NOT_TRACK='1', CODING_TOOLS_MCP_DANGEROUSLY_FAKE_READONLY_ANNOTATIONS='0')
    proc = run([str(python), '-m', 'coding_tools_mcp', '--stdio', '--workspace', str(HOME / 'mcp-workspace'), '--unconfined', '--permission-mode', 'trusted'], input=wire, env=env)
    replies = {obj['id']: obj for line in proc.stdout.splitlines() if line.strip() for obj in [json.loads(line)] if 'id' in obj}
    assert len(replies) == len(calls), f'缺少真实协议响应：{list(replies)}'
    for number, reply in replies.items():
        assert 'error' not in reply, (number, reply)
        assert not reply['result'].get('isError'), (number, reply['result'])
    tools = {tool['name'] for tool in replies[2]['result']['tools']}
    assert {'show_desktop_tip', 'list_project_tree', 'read_project_document', 'server_info'} <= tools
    info = replies[3]['result']['structuredContent']
    assert info['filesystem_policy']['confinement'] == 'unconfined'
    assert info['permission_mode'] == 'trusted'
    assert info['annotation_override'] is None
    assert replies[6]['result']['structuredContent']['exit_code'] == 0
    if extended:
        assert replies[10]['result']['structuredContent']['displayed'] is True
    print(json.dumps({'tools': len(tools), 'new_tools': sorted(tools & {'show_desktop_tip', 'list_project_tree', 'read_project_document'}), 'confinement': 'unconfined', 'desktop_list': True, 'home_document_read': True, 'absolute_exec_workdir': True}, ensure_ascii=False))


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {'preflight', 'install', 'callback', 'probe'}:
        print('用法：preflight <wheel> <sha256>；install <wheel> <sha256>；callback <ChatGPT回调URL>；probe 扩展验收。')
        return
    mode = sys.argv[1]
    if mode == 'probe':
        stdio_check(INSTALL / 'bin/python', extended=True)
        print('文档、下载、默认项目树与桌面提示启动验证通过。')
        return
    if mode == 'callback':
        callback = sys.argv[2]
        assert callback.startswith('https://chatgpt.com/connector/oauth/')
        with PLIST.open('rb') as stream:
            config = plistlib.load(stream)
        config['EnvironmentVariables']['CODING_TOOLS_MCP_OAUTH_REDIRECT_URIS'] = callback
        with PLIST.open('wb') as stream:
            plistlib.dump(config, stream)
        PLIST.chmod(0o600)
        run(['launchctl', 'kickstart', '-k', 'gui/501/com.user.codingmcp'])
        print('专属回调已更新，认证凭据未更换。')
        return
    wheel = pathlib.Path(sys.argv[2])
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == sys.argv[3], '安装包 SHA256 不匹配'
    if mode == 'preflight':
        if not (CANDIDATE / 'bin/python').exists():
            run([str(UV), 'venv', '--python', '3.12', str(CANDIDATE)])
        run([str(UV), 'pip', 'install', '--offline', '--python', str(CANDIDATE / 'bin/python'), str(wheel)])
        stdio_check(CANDIDATE / 'bin/python')
        return
    # 写入前先确认待安装完整版本通过真实协议测试，旧混装包留存用于回滚。
    stdio_check(CANDIDATE / 'bin/python')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = HOME / '.local/state/coding-tools-mcp/reinstall-backups' / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copytree(INSTALL, backup / 'tool', symlinks=True)
    shutil.copy2(PLIST, backup / PLIST.name)
    (backup / PLIST.name).chmod(0o600)
    with PLIST.open('rb') as stream:
        config = plistlib.load(stream)
    args = config['ProgramArguments']
    if '--unconfined' not in args:
        args.append('--unconfined')
    env = config.setdefault('EnvironmentVariables', {})
    env['CODING_TOOLS_MCP_UNCONFINED'] = '1'
    env['CODING_TOOLS_MCP_TELEMETRY'] = 'off'
    env['CODING_TOOLS_MCP_DANGEROUSLY_FAKE_READONLY_ANNOTATIONS'] = '0'
    run(['launchctl', 'unload', str(PLIST)])
    try:
        run([str(UV), 'tool', 'uninstall', 'coding-tools-mcp'])
        run([str(UV), 'tool', 'install', '--offline', '--python', '3.12', str(wheel)])
        with PLIST.open('wb') as stream:
            plistlib.dump(config, stream)
        PLIST.chmod(0o600)
        stdio_check(INSTALL / 'bin/python')
        run(['launchctl', 'load', str(PLIST)])
    except BaseException:
        # 回滚到完整备份，不在故障后继续叠加零散补丁。
        if INSTALL.exists():
            INSTALL.rename(backup / 'failed-install')
        shutil.copytree(backup / 'tool', INSTALL, symlinks=True)
        shutil.copy2(backup / PLIST.name, PLIST)
        entry = HOME / '.local/bin/coding-tools-mcp'
        if not entry.exists():
            if entry.is_symlink():
                entry.unlink()
            entry.symlink_to(INSTALL / 'bin/coding-tools-mcp')
        run(['launchctl', 'load', str(PLIST)])
        raise
    print(json.dumps({'installed': True, 'backup': str(backup), 'wheel_sha256': sys.argv[3]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
