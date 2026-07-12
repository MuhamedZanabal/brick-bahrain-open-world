from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from verify_v15_authority import load_manifest, verify_artifact  # noqa: E402


def run(*args: str, cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE)
    return completed.stdout.strip()


class AuthorityVerifierTests(unittest.TestCase):
    def test_source_zip_hash_and_project_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "source.zip"
            import zipfile

            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("project.godot", 'config_version=5\nconfig/features=PackedStringArray("4.3")\n')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "artifacts": {
                            archive.name: {
                                "kind": "source_zip",
                                "sha256": digest,
                                "size": archive.stat().st_size,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = verify_artifact(archive, load_manifest(manifest_path))
            self.assertTrue(result["passed"], result)

    def test_hash_mismatch_stops_deeper_processing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "bad.apk"
            artifact.write_bytes(b"not an apk")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "artifacts": {
                            artifact.name: {
                                "kind": "apk",
                                "sha256": "0" * 64,
                                "size": artifact.stat().st_size,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = verify_artifact(artifact, load_manifest(manifest_path))
            self.assertFalse(result["passed"])
            self.assertFalse(next(c for c in result["checks"] if c["name"] == "sha256")["passed"])
            self.assertNotIn("zip_integrity", {c["name"] for c in result["checks"]})

    def test_synthetic_git_bundle_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.name", "Test", cwd=repo)
            run("git", "config", "user.email", "test@example.com", cwd=repo)
            (repo / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            run("git", "add", "project.godot", cwd=repo)
            run("git", "commit", "-m", "baseline", cwd=repo)
            run("git", "checkout", "-b", "audit/test-authority", cwd=repo)
            (repo / "README.md").write_text("authority\n", encoding="utf-8")
            run("git", "add", "README.md", cwd=repo)
            run("git", "commit", "-m", "authority", cwd=repo)
            commit = run("git", "rev-parse", "HEAD", cwd=repo)
            tree = run("git", "rev-parse", "HEAD^{tree}", cwd=repo)
            bundle = root / "authority.bundle"
            run("git", "bundle", "create", str(bundle), "audit/test-authority", cwd=repo)
            digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "authority": {
                            "branch": "audit/test-authority",
                            "commit": commit,
                            "tree": tree,
                        },
                        "artifacts": {
                            bundle.name: {
                                "kind": "git_bundle",
                                "sha256": digest,
                                "size": bundle.stat().st_size,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = verify_artifact(bundle, load_manifest(manifest_path))
            self.assertTrue(result["passed"], result)


if __name__ == "__main__":
    unittest.main()
