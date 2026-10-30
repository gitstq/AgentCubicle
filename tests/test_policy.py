"""策略引擎与审计链的单元测试。

Unit tests for the policy engine and the audit chain.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentcubicle.audit import (  # noqa: E402
    GENESIS_HASH,
    AuditLog,
    compute_hash,
    summarize,
)
from agentcubicle.paths import (  # noqa: E402
    PathEscapeError,
    command_matches,
    host_matches,
    match_any,
    normalize_command,
    normalize_relative,
    readable_size,
    split_host_port,
)
from agentcubicle.policy import (  # noqa: E402
    DEFAULT_POLICY,
    Decision,
    Policy,
    PolicyError,
    merge_policy,
    validate_policy,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PathUtilsTest(unittest.TestCase):
    """路径归一化与匹配。"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cubicle-paths-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_relative_path_normalized(self):
        rel, absolute = normalize_relative("a/b.txt", self.root)
        self.assertEqual(rel, "a/b.txt")
        self.assertTrue(str(absolute).startswith(self.root))

    def test_leading_slash_is_contained(self):
        rel, _ = normalize_relative("/a/b.txt", self.root)
        self.assertEqual(rel, "a/b.txt")

    def test_dotdot_escape_rejected(self):
        with self.assertRaises(PathEscapeError):
            normalize_relative("../escape.txt", self.root)

    def test_deep_dotdot_escape_rejected(self):
        with self.assertRaises(PathEscapeError):
            normalize_relative("a/../../escape.txt", self.root)

    def test_is_within_helper(self):
        from agentcubicle.paths import is_within

        self.assertTrue(is_within("a.txt", self.root))
        self.assertFalse(is_within("../a.txt", self.root))

    def test_match_any_directory_prefix(self):
        self.assertEqual(match_any("docs/a/b.txt", ["docs"]), "docs")
        self.assertIsNone(match_any("src/a.py", ["docs"]))

    def test_match_any_glob(self):
        self.assertEqual(match_any("workspace/a.txt", ["workspace/**"]), "workspace/**")
        self.assertIsNone(match_any("etc/a.txt", ["workspace/**"]))

    def test_match_any_wildcard_all(self):
        self.assertIsNotNone(match_any("anything", ["*"]))

    def test_match_any_empty(self):
        self.assertIsNone(match_any("a", []))
        self.assertIsNone(match_any("a", None))

    def test_command_matches(self):
        self.assertEqual(command_matches("git status", ["git *"]), "git *")
        self.assertIsNone(command_matches("rm -rf /", ["git *"]))
        self.assertIsNone(command_matches("   ", ["git *"]))

    def test_normalize_command_collapses_spaces(self):
        self.assertEqual(normalize_command("  echo    hi  "), "echo hi")

    def test_split_host_port(self):
        self.assertEqual(split_host_port("https://Example.COM:443/a/b"), "example.com")
        self.assertEqual(split_host_port("api.github.com"), "api.github.com")
        self.assertEqual(split_host_port("user@host.io"), "host.io")

    def test_host_matches(self):
        self.assertEqual(host_matches("https://api.github.com/x", ["*.github.com"]),
                         "*.github.com")
        self.assertIsNone(host_matches("https://evil.io", ["*.github.com"]))
        self.assertEqual(host_matches("https://evil.io", ["*"]), "*")

    def test_readable_size(self):
        self.assertEqual(readable_size(512), "512 B")
        self.assertEqual(readable_size(2048), "2.00 KB")


class PolicyTest(unittest.TestCase):
    """策略解析、校验与决策。"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cubicle-policy-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_default_policy_shape(self):
        policy = Policy.default()
        self.assertEqual(policy.name, "default")
        self.assertEqual(policy.default_effect, "ask")
        self.assertIn("workspace/**", policy.data["paths"]["write_allow"])

    def test_default_is_copied_not_shared(self):
        first = Policy.default()
        first.data["name"] = "mutated"
        self.assertNotEqual(Policy.default().name, "mutated")
        self.assertEqual(DEFAULT_POLICY["name"], "default")

    def test_validate_rejects_bad_version(self):
        with self.assertRaises(PolicyError):
            validate_policy({"version": 99})

    def test_validate_rejects_bad_default_effect(self):
        with self.assertRaises(PolicyError):
            validate_policy({"default_effect": "maybe"})

    def test_validate_rejects_non_list_rules(self):
        with self.assertRaises(PolicyError):
            validate_policy({"paths": {"write_allow": "workspace"}})

    def test_validate_rejects_negative_budget(self):
        with self.assertRaises(PolicyError):
            validate_policy({"budgets": {"max_actions": -1}})

    def test_validate_rejects_non_dict(self):
        with self.assertRaises(PolicyError):
            validate_policy(["not", "a", "dict"])

    def test_merge_replaces_lists(self):
        merged = merge_policy({"commands": {"allow": ["a", "b"]}},
                              {"commands": {"allow": ["c"]}})
        self.assertEqual(merged["commands"]["allow"], ["c"])

    def test_save_and_load_roundtrip(self):
        path = os.path.join(self.root, "policy.json")
        policy = Policy.default()
        policy.data["name"] = "roundtrip"
        policy.save(path)
        loaded = Policy.from_file(path)
        self.assertEqual(loaded.name, "roundtrip")

    # -- 决策 ---------------------------------------------------------------

    def test_write_inside_workspace_allowed(self):
        policy = Policy.default()
        decision = policy.evaluate("file.write", "workspace/a.txt", root=self.root)
        self.assertEqual(decision.effect, "allow")

    def test_write_outside_workspace_falls_back(self):
        policy = Policy.default()
        decision = policy.evaluate("file.write", "system.txt", root=self.root)
        self.assertEqual(decision.effect, "ask")

    def test_write_env_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("file.write", "workspace/.env", root=self.root)
        self.assertEqual(decision.effect, "deny")
        self.assertEqual(decision.risk, "high")

    def test_read_sensitive_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("file.read", "home/.aws/creds", root=self.root)
        self.assertEqual(decision.effect, "deny")

    def test_read_general_allowed(self):
        policy = Policy.default()
        decision = policy.evaluate("file.read", "docs/readme.md", root=self.root)
        self.assertEqual(decision.effect, "allow")

    def test_delete_denied_by_default(self):
        policy = Policy.default()
        decision = policy.evaluate("file.delete", "workspace/a.txt", root=self.root)
        self.assertEqual(decision.effect, "deny")

    def test_path_escape_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("file.write", "../outside.txt", root=self.root)
        self.assertEqual(decision.effect, "deny")
        self.assertEqual(decision.risk, "high")

    def test_command_allow_list(self):
        policy = Policy.default()
        decision = policy.evaluate("shell.exec", "git status")
        self.assertEqual(decision.effect, "allow")

    def test_command_deny_list(self):
        policy = Policy.default()
        decision = policy.evaluate("shell.exec", "sudo rm -rf /")
        self.assertEqual(decision.effect, "deny")

    def test_command_substitution_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("shell.exec", "echo $(whoami)")
        self.assertEqual(decision.effect, "deny")

    def test_command_pipe_to_shell_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("shell.exec", "cat x | sh")
        self.assertEqual(decision.effect, "deny")

    def test_command_not_listed_falls_back(self):
        policy = Policy.default()
        decision = policy.evaluate("shell.exec", "terraform apply")
        self.assertEqual(decision.effect, "ask")

    def test_network_denied_by_default(self):
        policy = Policy.default()
        decision = policy.evaluate("net.fetch", "https://example.com")
        self.assertEqual(decision.effect, "deny")

    def test_network_allow_list(self):
        data = copy.deepcopy(DEFAULT_POLICY)
        data["network"] = {"allow_hosts": ["api.github.com"], "deny_hosts": []}
        policy = Policy.from_dict(data)
        decision = policy.evaluate("net.fetch", "https://api.github.com/repos")
        self.assertEqual(decision.effect, "allow")

    def test_unknown_action_denied(self):
        policy = Policy.default()
        decision = policy.evaluate("file.launch", "x")
        self.assertEqual(decision.effect, "deny")

    def test_budget_action_cap(self):
        policy = Policy.default()
        policy.usage.actions = 200
        decision = policy.evaluate("file.write", "workspace/a.txt", root=self.root)
        self.assertEqual(decision.effect, "deny")
        self.assertIn("budget", decision.reason)

    def test_budget_write_cap(self):
        policy = Policy.default()
        decision = policy.evaluate("file.write", "workspace/a.txt",
                                   root=self.root, size_bytes=50 * 1024 * 1024)
        self.assertEqual(decision.effect, "deny")

    def test_record_updates_usage(self):
        policy = Policy.default()
        policy.record("file.write", size_bytes=100, seconds=1.5)
        self.assertEqual(policy.usage.actions, 1)
        self.assertEqual(policy.usage.write_bytes, 100)
        self.assertAlmostEqual(policy.usage.runtime_seconds, 1.5)

    def test_decision_serialization(self):
        decision = Decision("allow", "ok", rule="r", risk="low")
        data = decision.to_dict()
        self.assertEqual(data["effect"], "allow")
        self.assertTrue(decision.allowed)
        self.assertIn("ALLOW", str(decision))


class AuditChainTest(unittest.TestCase):
    """哈希链审计日志。"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cubicle-audit-")
        self.log_path = os.path.join(self.root, "audit.jsonl")
        self.log = AuditLog(self.log_path)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_empty_log_verifies(self):
        ok, problems = self.log.verify()
        self.assertTrue(ok)
        self.assertEqual(problems, [])

    def test_chain_links_correctly(self):
        first = self.log.append(cubicle="c", action="file.write",
                                target="a.txt", effect="allow")
        second = self.log.append(cubicle="c", action="file.write",
                                 target="b.txt", effect="deny")
        self.assertEqual(first.prev_hash, GENESIS_HASH)
        self.assertEqual(second.prev_hash, first.hash)
        self.assertNotEqual(first.hash, second.hash)

    def test_verify_intact(self):
        for i in range(5):
            self.log.append(cubicle="c", action="shell.exec",
                            target=f"cmd{i}", effect="allow")
        ok, problems = self.log.verify()
        self.assertTrue(ok)
        self.assertEqual(problems, [])

    def test_tampering_detected(self):
        self.log.append(cubicle="c", action="file.write", target="a", effect="allow")
        self.log.append(cubicle="c", action="file.write", target="b", effect="allow")

        with open(self.log_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        record = json.loads(lines[0])
        record["effect"] = "deny"
        lines[0] = json.dumps(record, ensure_ascii=False)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        fresh = AuditLog(self.log_path)
        ok, problems = fresh.verify()
        self.assertFalse(ok)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    def test_smart_tampering_breaks_the_link(self):
        """重算哈希的「聪明」篡改仍会被断链检测捕获。

        A "smart" tamperer who recomputes the hash is still caught by link
        verification, because the next entry still points at the old hash.
        """
        self.log.append(cubicle="c", action="file.write", target="a", effect="allow")
        self.log.append(cubicle="c", action="file.write", target="b", effect="allow")

        with open(self.log_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        record = json.loads(lines[0])
        record["effect"] = "deny"
        rebuilt = AuditLog.__new__(AuditLog)
        from agentcubicle.audit import AuditEntry

        entry = AuditEntry.from_dict(record)
        entry.hash = compute_hash(entry.payload(), entry.prev_hash)
        lines[0] = json.dumps(entry.to_dict(), ensure_ascii=False)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        fresh = AuditLog(self.log_path)
        ok, problems = fresh.verify()
        self.assertFalse(ok)
        self.assertTrue(any("broken link" in p for p in problems))
        del rebuilt

    def test_deleted_entry_detected(self):
        for i in range(3):
            self.log.append(cubicle="c", action="file.write",
                            target=f"f{i}", effect="allow")
        with open(self.log_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        with open(self.log_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join([lines[0], lines[2]]) + "\n")

        fresh = AuditLog(self.log_path)
        ok, problems = fresh.verify()
        self.assertFalse(ok)
        self.assertTrue(any("non-contiguous" in p or "broken link" in p
                            for p in problems))

    def test_tail_and_read_all(self):
        for i in range(10):
            self.log.append(cubicle="c", action="file.write",
                            target=f"f{i}", effect="allow")
        self.assertEqual(len(self.log.read_all()), 10)
        self.assertEqual(len(self.log.tail(3)), 3)
        self.assertEqual(self.log.tail(3)[-1].target, "f9")
        self.assertEqual(len(self.log), 10)

    def test_reopen_appends_with_correct_state(self):
        self.log.append(cubicle="c", action="file.write", target="a", effect="allow")
        reopened = AuditLog(self.log_path)
        self.assertEqual(reopened.last_seq, 1)
        entry = reopened.append(cubicle="c", action="file.write",
                                target="b", effect="allow")
        self.assertEqual(entry.seq, 2)
        ok, _ = reopened.verify()
        self.assertTrue(ok)

    def test_compute_hash_is_deterministic(self):
        payload = {"a": 1, "b": "x"}
        self.assertEqual(compute_hash(payload, GENESIS_HASH),
                         compute_hash(payload, GENESIS_HASH))
        self.assertNotEqual(compute_hash(payload, GENESIS_HASH),
                            compute_hash(payload, "f" * 64))

    def test_summarize(self):
        self.log.append(cubicle="c", action="file.write", target="a",
                        effect="allow", size_bytes=10, risk="low")
        self.log.append(cubicle="c", action="shell.exec", target="b",
                        effect="deny", risk="high")
        stats = summarize(self.log.read_all())
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["by_effect"], {"allow": 1, "deny": 1})
        self.assertEqual(stats["write_bytes"], 10)
        self.assertEqual(stats["by_risk"]["high"], 1)

    def test_entry_roundtrip(self):
        entry = self.log.append(cubicle="c", action="file.write", target="a",
                                effect="allow", rule="r", risk="medium",
                                size_bytes=5, duration_ms=1.25, exit_code=0,
                                actor="tester", extra={"session": "s"})
        restored = self.log.read_all()[0]
        self.assertEqual(restored.to_dict()["hash"], entry.hash)
        self.assertEqual(restored.extra["session"], "s")
        self.assertEqual(restored.iso_time[-1], "Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
