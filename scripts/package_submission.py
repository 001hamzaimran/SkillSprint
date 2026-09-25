"""Allowlisted local submission archive. Never includes private environment/uploads."""

import sys, json, hashlib, zipfile, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import ROOT, Settings

OUT = ROOT / "output/submission"


def main():
    settings = Settings()
    secrets = [
        s.encode()
        for s in [
            settings.openai_api_key,
            settings.app_secret_key,
            settings.bootstrap_admin_password,
        ]
        if len(s) >= 12
    ]
    roots = [
        "app",
        "templates",
        "static",
        "tests",
        "scripts",
        "prompt_templates",
        "schemas",
        "documentation",
        "sample_documents",
        "hidden_test_ready",
        "reports",
    ]
    files = []
    for folder in roots:
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in [".pyc", ".log"]
        )
    files.extend(
        ROOT / n
        for n in [
            "README.md",
            "PROJECT_PLAN.md",
            "AI_USAGE.md",
            "LICENSE",
            "requirements.txt",
            "requirements-lock.txt",
            "requirements-artifacts.txt",
            "run.py",
            "manage.py",
            "start.ps1",
            ".env.example",
            ".gitignore",
        ]
    )
    files.extend(
        p
        for p in OUT.rglob("*")
        if p.is_file()
        and p.suffix != ".zip"
        and p.name not in ["SHA256_MANIFEST.json", "PACKAGE_CHECK.json"]
    )
    entries = []
    for p in sorted(set(files)):
        relative = p.relative_to(ROOT).as_posix()
        data = p.read_bytes()
        if any(secret in data for secret in secrets):
            raise RuntimeError("Configured secret found in " + relative)
        if re.search(rb"sk-proj-[A-Za-z0-9_-]{25,}", data):
            raise RuntimeError("Potential provider key found in " + relative)
        assert not any(part in [".venv", "uploads", ".git"] for part in p.relative_to(ROOT).parts)
        assert p.name != ".env"
        entries.append(
            {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    manifest = OUT / "SHA256_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "files": entries,
                "note": "Hashes cover included payload files; manifest excludes itself.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    archive = OUT / "SkillSprint_local_submission.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for entry in entries:
            z.write(ROOT / entry["path"], entry["path"])
        z.write(manifest, manifest.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for entry in entries:
            assert hashlib.sha256(z.read(entry["path"])).hexdigest() == entry["sha256"]
    result = {
        "files": len(entries) + 1,
        "archive_bytes": archive.stat().st_size,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "zip_integrity": "passed",
        "configured_secret_scan": "passed",
        "excluded": [".env", "uploads", ".venv", ".git", "SRS"],
        "scope": "Local delivery only; publication and human verification not claimed.",
    }
    (OUT / "PACKAGE_CHECK.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
