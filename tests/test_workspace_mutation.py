from __future__ import annotations

import argparse
import io
import os
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from coding_tools_mcp import server as server_module
from coding_tools_mcp.server import (
    Runtime,
    WorkspaceMutationPolicy,
    build_parser,
    open_landlock_ruleset,
    run_stdio,
    runtime_policy_from_args,
    workspace_mutation_policy_from_args,
)
from tests.compliance.mcp_client import StdioMCPClient


def parse(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)


class WorkspaceMutationArgumentTests(unittest.TestCase):
    def test_the_default_is_unrestricted(self) -> None:
        policy = workspace_mutation_policy_from_args(parse([]))
        self.assertEqual(policy.mode, "unrestricted")
        self.assertFalse(policy.structured_only)
        self.assertEqual(policy.write_paths, ())

    def test_structured_only_collects_repeated_write_paths(self) -> None:
        policy = workspace_mutation_policy_from_args(
            parse(
                [
                    "--workspace-mutation",
                    "structured-only",
                    "--write-path",
                    "build",
                    "--write-path",
                    ".pytest_cache",
                ]
            )
        )
        self.assertTrue(policy.structured_only)
        self.assertEqual(policy.write_paths, ("build", ".pytest_cache"))

    def test_a_write_path_without_the_mode_is_a_startup_error(self) -> None:
        # Silently ignoring it would let an operator believe a directory is
        # exempt from a restriction that is not even on.
        with self.assertRaises(ValueError):
            workspace_mutation_policy_from_args(parse(["--write-path", "build"]))

    def test_an_unknown_mode_is_rejected(self) -> None:
        args = parse([])
        args.workspace_mutation = "read-only"
        with self.assertRaises(ValueError):
            workspace_mutation_policy_from_args(args)

    def test_the_runtime_policy_carries_the_mutation_policy(self) -> None:
        policy = runtime_policy_from_args(parse(["--workspace-mutation", "structured-only"]))
        self.assertTrue(policy.workspace_mutation.structured_only)


class WorkspaceMutationRuntimeTests(unittest.TestCase):
    def runtime(self, workspace: Path, **fields: object) -> Runtime:
        return Runtime(workspace, workspace_mutation=WorkspaceMutationPolicy(**fields))

    def test_the_default_policy_is_disclosed_as_unrestricted(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp))
            try:
                payload = runtime.server_info_payload()["workspace_mutation_policy"]
                self.assertEqual(payload["mode"], "unrestricted")
                self.assertIs(payload["enforced"], True)
                self.assertIn("apply_changes", payload["structured_write_tools"])
            finally:
                runtime.close()

    def test_write_paths_are_resolved_inside_the_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").mkdir()
            runtime = self.runtime(workspace, mode="structured-only", write_paths=("build",))
            try:
                self.assertEqual(runtime.workspace_write_paths(), [(workspace / "build").resolve()])
                self.assertIn(
                    (workspace / "build").resolve(), runtime.landlock_write_roots()
                )
            finally:
                runtime.close()

    def test_reporting_a_missing_write_path_does_not_create_it(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            runtime = self.runtime(
                workspace,
                mode="structured-only",
                write_paths=("generated/nested",),
            )
            try:
                payload = runtime.workspace_mutation_payload()
                expected = (workspace / "generated" / "nested").resolve()
                self.assertFalse(expected.exists())
                self.assertEqual(runtime.workspace_write_paths(), [expected])
                self.assertEqual(payload["write_paths"], ["generated/nested"])
                runtime.server_info_payload()
                runtime.check_exec_environment({})
                self.assertFalse(expected.exists())
            finally:
                runtime.close()

    def test_landlock_initialization_creates_a_missing_write_path(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            expected = workspace / "generated" / "nested"
            runtime = self.runtime(
                workspace,
                mode="structured-only",
                write_paths=("generated/nested",),
            )
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertTrue(expected.is_dir())
                self.assertIn(expected.resolve(), ruleset.call_args.kwargs["write_roots"])
            finally:
                runtime.close()

    def test_a_write_path_that_is_a_file_is_a_clean_cli_error(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").write_text("not a directory", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                status = run_stdio(
                    parse(
                        [
                            "--stdio",
                            "--workspace",
                            str(workspace),
                            "--workspace-mutation",
                            "structured-only",
                            "--write-path",
                            "build",
                        ]
                    )
                )
        self.assertEqual(status, 2)
        self.assertIn("INVALID_ARGUMENT", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_a_write_path_outside_the_workspace_is_dropped(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only", write_paths=("../elsewhere", "/etc"))
            try:
                self.assertEqual(runtime.workspace_write_paths(), [])
            finally:
                runtime.close()

    def test_an_unenforceable_policy_says_so_instead_of_promising(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only")
            try:
                with patch.object(runtime, "landlock_enabled", return_value=False):
                    payload = runtime.workspace_mutation_payload()
                    self.assertEqual(payload["mode"], "structured-only")
                    self.assertIs(payload["enforced"], False)
                    warnings = runtime.check_exec_environment({})["warnings"]
                self.assertTrue(
                    any("structured-only is not enforced" in item for item in warnings), warnings
                )
            finally:
                runtime.close()

    def test_landlock_before_abi_three_does_not_claim_truncate_enforcement(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp), mode="structured-only")
            try:
                with patch.object(
                    server_module,
                    "landlock_status_payload",
                    return_value={"available": True, "abi_version": 2},
                ):
                    payload = runtime.workspace_mutation_payload()
                    checked = runtime.check_exec_environment({})
            finally:
                runtime.close()
        self.assertIs(payload["enforced"], False)
        self.assertEqual(payload["enforced_by"], "none")
        self.assertTrue(any("cannot deny file truncation" in item for item in payload["warnings"]))
        self.assertTrue(any("cannot deny file truncation" in item for item in checked["warnings"]))

    def test_structured_only_asks_landlock_for_a_read_only_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "build").mkdir()
            runtime = self.runtime(workspace, mode="structured-only", write_paths=("build",))
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertIs(ruleset.call_args.kwargs["workspace_writable"], False)
                self.assertIn((workspace / "build").resolve(), ruleset.call_args.kwargs["write_roots"])
            finally:
                runtime.close()

    def test_unrestricted_leaves_the_workspace_writable_for_commands(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp))
            try:
                with patch.object(runtime, "landlock_enabled", return_value=True), patch(
                    f"{open_landlock_ruleset.__module__}.open_landlock_ruleset"
                ) as ruleset:
                    ruleset.side_effect = RuntimeError("stop after the ruleset is described")
                    with self.assertRaises(RuntimeError):
                        runtime.exec_command({"cmd": "true"})
                self.assertIs(ruleset.call_args.kwargs["workspace_writable"], True)
            finally:
                runtime.close()


class FilesystemCapabilityMetadataTests(unittest.TestCase):
    PATH_TOOLS = (
        "read_file", "list_dir", "list_files", "search_text", "view_image",
        "apply_patch", "apply_changes",
    )

    def test_effective_path_scope_is_independent_of_permission_mode(self) -> None:
        # trusted/dangerous 不等于开放路径；自报必须取实际 Workspace 配置。
        for mode in ("safe", "trusted", "dangerous"):
            for unconfined in (False, True):
                with self.subTest(mode=mode, unconfined=unconfined), TemporaryDirectory() as tmp:
                    runtime = Runtime(Path(tmp), permission_mode=mode, unconfined=unconfined)
                    try:
                        policy = runtime.server_info_payload()["filesystem_policy"]
                        self.assertEqual(policy["confinement"], "unconfined" if unconfined else "workspace")
                        self.assertEqual(policy["relative_path_base"], str(Path(tmp).resolve()))
                        self.assertIs(policy["workspace_is_access_boundary"], not unconfined)
                        for key in ("absolute_paths_allowed", "home_paths_allowed", "symlinks_outside_workspace_allowed"):
                            self.assertIs(policy[key], unconfined)
                        self.assertIs(policy["os_permissions_apply"], True)
                        self.assertEqual(runtime.permission_mode, mode)
                    finally:
                        runtime.close()

    def test_environment_enabled_scope_is_reported_from_the_effective_workspace(self) -> None:
        with TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODING_TOOLS_MCP_UNCONFINED": "1"}):
            runtime = Runtime(Path(tmp), unconfined=False)
            try:
                self.assertEqual(runtime.server_info_payload()["filesystem_policy"]["confinement"], "unconfined")
            finally:
                runtime.close()

    def test_tool_catalog_matches_scope_and_does_not_leak_between_runtimes(self) -> None:
        with TemporaryDirectory() as tmp:
            confined = Runtime(Path(tmp), permission_mode="trusted", enable_view_image=True)
            opened = Runtime(Path(tmp), permission_mode="safe", unconfined=True, enable_view_image=True)
            try:
                first = confined.list_tools()
                for runtime, phrase in ((confined, "confined to the workspace"), (opened, "outside the workspace are allowed")):
                    catalog = {tool["name"]: tool for tool in runtime.list_tools()["tools"]}
                    policy = runtime.server_info_payload()["filesystem_policy"]
                    for name in self.PATH_TOOLS:
                        with self.subTest(name=name, scope=policy["confinement"]):
                            self.assertIn(phrase, catalog[name]["description"])
                            self.assertIn(policy["description"], catalog[name]["description"])
                            self.assertEqual(catalog[name]["inputSchema"], server_module.input_schemas()[name])
                            self.assertEqual(catalog[name]["annotations"], server_module.tool_annotations(name))
                self.assertEqual(confined.list_tools(), first)
                self.assertNotIn("outside the workspace are allowed", server_module.tool_definition("read_file")["description"])
            finally:
                confined.close()
                opened.close()

    def test_confined_metadata_does_not_weaken_real_absolute_or_parent_path_denial(self) -> None:
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            workspace = parent / "workspace"
            workspace.mkdir()
            (parent / "outside.txt").write_text("outside", encoding="utf-8")
            runtime = Runtime(workspace, permission_mode="dangerous")
            try:
                self.assertFalse(runtime.server_info_payload()["filesystem_policy"]["absolute_paths_allowed"])
                for path, code in ((str(parent / "outside.txt"), "ABSOLUTE_PATH_DENIED"), ("../outside.txt", "PATH_OUTSIDE_WORKSPACE")):
                    result = runtime.call_tool("read_file", {"path": path})
                    self.assertTrue(result["isError"])
                    self.assertEqual(result["structuredContent"]["error"]["code"], code)
            finally:
                runtime.close()

    def test_open_scope_reads_real_absolute_and_home_paths_without_changing_mode(self) -> None:
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            workspace = parent / "workspace"
            workspace.mkdir()
            (parent / "outside.txt").write_text("真实文件", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": str(parent), "USERPROFILE": str(parent)}):
                runtime = Runtime(workspace, permission_mode="safe", unconfined=True)
                try:
                    self.assertTrue(runtime.server_info_payload()["filesystem_policy"]["home_paths_allowed"])
                    for path in (str(parent / "outside.txt"), "~/outside.txt"):
                        result = runtime.call_tool("read_file", {"path": path})
                        self.assertFalse(result["isError"], result)
                        self.assertEqual(result["structuredContent"]["content"], "真实文件")
                    self.assertEqual(runtime.permission_mode, "safe")
                finally:
                    runtime.close()

    def test_model_facing_server_info_includes_the_same_policy_as_structured_content(self) -> None:
        for unconfined in (False, True):
            with self.subTest(unconfined=unconfined), TemporaryDirectory() as tmp:
                runtime = Runtime(Path(tmp), unconfined=unconfined)
                try:
                    result = runtime.call_tool("server_info", {})
                    self.assertFalse(result["isError"])
                    description = result["structuredContent"]["filesystem_policy"]["description"]
                    text = "\n".join(item.get("text", "") for item in result["content"])
                    self.assertIn(description, text)
                    schema = server_module.tool_output_schema("server_info")["properties"]
                    self.assertIn("filesystem_policy", schema)
                finally:
                    runtime.close()


    def test_handshake_and_discovery_do_not_contradict_the_effective_scope(self) -> None:
        for unconfined in (False, True):
            with self.subTest(unconfined=unconfined), TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                (workspace / "AGENTS.md").write_text("保留项目指令", encoding="utf-8")
                runtime = Runtime(workspace, unconfined=unconfined)
                try:
                    description = runtime.server_info_payload()["filesystem_policy"]["description"]
                    for payload in (runtime.initialize_result(), runtime.discover_payload()):
                        self.assertIn(description, payload["instructions"])
                        self.assertIn("保留项目指令", payload["instructions"])
                        self.assertNotIn("Use these tools only for coding operations inside", payload["instructions"])
                finally:
                    runtime.close()

    def test_fresh_stdio_clients_observe_the_actual_path_boundary(self) -> None:
        # 启动真实 CLI 进程并通过 MCP 协议读文件，防止只有内部元数据单测通过。
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            workspace = parent / "workspace"
            workspace.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("protocol evidence", encoding="utf-8")
            for unconfined in (False, True):
                args = ["--permission-mode", "trusted"] + (["--unconfined"] if unconfined else [])
                with self.subTest(unconfined=unconfined), StdioMCPClient(workspace, extra_args=args) as client:
                    result = client.call_tool("server_info", {})
                    self.assertFalse(result["isError"])
                    policy = result["structuredContent"]["filesystem_policy"]
                    self.assertIs(policy["absolute_paths_allowed"], unconfined)
                    catalog = {t["name"]: t for t in client.rpc("tools/list")["tools"]}
                    self.assertIn(policy["description"], catalog["read_file"]["description"])
                    read = client.call_tool("read_file", {"path": str(outside)})
                    if unconfined:
                        self.assertFalse(read["isError"], read)
                        self.assertEqual(read["structuredContent"]["content"], "protocol evidence")
                    else:
                        self.assertTrue(read["isError"])
                        self.assertEqual(read["structuredContent"]["error"]["code"], "ABSOLUTE_PATH_DENIED")


if __name__ == "__main__":
    unittest.main()
