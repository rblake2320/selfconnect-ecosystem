#!/usr/bin/env python3
"""Fail-closed source and artifact gate for the selfconnect Python package.

The gate statically verifies claim boundaries, version identity, tracked-file
hygiene, wheel RECORD integrity, source-distribution paths, and optional release
tag binding. It never imports or executes code from a built artifact.
"""

from __future__ import annotations

import argparse
import ast
import base64
import csv
import email
import hashlib
import io
import pathlib
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile


PACKAGE_NAME = "selfconnect"
TAG_PREFIX = "selfconnect-py-v"
TEXT_SUFFIXES = {".json", ".md", ".py", ".rst", ".toml", ".txt", ".yaml", ".yml"}
PUBLIC_EXCLUDES = {"LOG.md", "WHY.md", "PARKED.md"}
PROHIBITED_CLAIMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bIL\s*7\b", re.IGNORECASE), "IL7 is not a current DoD CC SRG impact level"),
    (re.compile(r"\bIL\s*6\s*[/\-\u2013]\s*(?:IL\s*)?7\b", re.IGNORECASE), "IL6/IL7 range claim"),
    (re.compile(r"\bimmutable\s+audit\b", re.IGNORECASE), "immutable-audit claim"),
    (re.compile(r"\bcompliance\s+for\s+every\b", re.IGNORECASE), "unbounded compliance claim"),
    (re.compile(r"\bevery\s+LLM\b", re.IGNORECASE), "unbounded LLM callback claim"),
    (re.compile(r"\bevery\s+tool\b", re.IGNORECASE), "unbounded tool callback claim"),
    (re.compile(r"\bposts?\s+all\s+LLM\b", re.IGNORECASE), "unbounded callback coverage claim"),
    (re.compile(r"\brecords?\s+every\b", re.IGNORECASE), "unbounded event-completeness claim"),
    (re.compile(r"\bhard\s+budget\s+enforcement\b", re.IGNORECASE), "SDK enforcement claim"),
    (re.compile(r"\bhardware[- ]bound\b", re.IGNORECASE), "unqualified hardware-binding claim"),
    (re.compile(r"\breplay[- ]proof\b", re.IGNORECASE), "absolute replay-resistance claim"),
    (
        re.compile(r"\bsuitable\s+for\s+compliance\s+export\b", re.IGNORECASE),
        "compliance-export conclusion",
    ),
    (re.compile(r"\bfederal[- ]tier\s+compliance\b", re.IGNORECASE), "federal compliance claim"),
)


class GateError(RuntimeError):
    """A bounded release-gate failure."""


def run_git(root: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
    )
    if result.returncode:
        raise GateError(f"git {' '.join(args)} failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def parse_version_file(path: pathlib.Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value
    raise GateError(f"{path}: missing literal __version__ assignment")


def source_version(package_dir: pathlib.Path) -> str:
    config = tomllib.loads((package_dir / "pyproject.toml").read_text(encoding="utf-8"))
    project = config.get("project", {})
    if project.get("name") != PACKAGE_NAME:
        raise GateError(f"project.name must be {PACKAGE_NAME!r}")
    if project.get("dynamic") != ["version"] or "version" in project:
        raise GateError("pyproject must use only dynamic version metadata")
    version_path = config.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
    if version_path != "selfconnect/_version.py":
        raise GateError("Hatch version path must be selfconnect/_version.py")
    return parse_version_file(package_dir / version_path)


def iter_public_source_files(root: pathlib.Path, package_dir: pathlib.Path):
    for name in ("README.md", "AGENTS.md", "CLAUDE.md"):
        path = root / name
        if path.exists():
            yield path
    docs = root / "docs"
    if docs.exists():
        for path in sorted(docs.rglob("*.md")):
            if path.name not in PUBLIC_EXCLUDES:
                yield path
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel_parts = path.relative_to(package_dir).parts
        if "dist" in rel_parts or "build" in rel_parts or "__pycache__" in rel_parts:
            continue
        if "tests" in rel_parts:
            continue
        yield path


def claim_hits(path: str, text: str) -> list[str]:
    hits = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern, label in PROHIBITED_CLAIMS:
            if pattern.search(line):
                hits.append(f"{path}:{line_number}: {label}")
    return hits


def check_claims(files, root: pathlib.Path) -> list[str]:
    hits = []
    for path in files:
        try:
            display = str(path.relative_to(root))
        except ValueError:
            display = str(path)
        hits.extend(claim_hits(display, path.read_text(encoding="utf-8")))
    return hits


def check_tracked_hygiene(root: pathlib.Path, package_dir: pathlib.Path) -> list[str]:
    rel = package_dir.relative_to(root).as_posix()
    tracked = run_git(root, "ls-files", "--", f"{rel}/**").splitlines()
    bad = []
    for name in tracked:
        normalized = name.replace("\\", "/")
        if (
            "/dist/" in normalized
            or "/build/" in normalized
            or "/__pycache__/" in normalized
            or "/.pytest_cache/" in normalized
            or normalized.endswith(".pyc")
            or normalized.endswith(".pyo")
            or normalized.endswith(".whl")
            or normalized.endswith(".tar.gz")
            or ".egg-info/" in normalized
        ):
            bad.append(f"tracked generated artifact: {normalized}")
    return bad


def check_source_contract(root: pathlib.Path, package_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    version = source_version(package_dir)
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z]+\d+)?", version):
        errors.append(f"source version is not a bounded release identifier: {version}")

    init_text = (package_dir / "selfconnect" / "__init__.py").read_text(encoding="utf-8")
    client_text = (package_dir / "selfconnect" / "client.py").read_text(encoding="utf-8")
    handler_text = (package_dir / "selfconnect" / "langchain_handler.py").read_text(encoding="utf-8")
    if "from ._version import __version__" not in init_text:
        errors.append("__init__.py must export version from _version.py")
    if 'f"selfconnect-py/{__version__}"' not in client_text:
        errors.append("client User-Agent must derive from __version__")
    if '"handler_version": __version__' not in handler_text:
        errors.append("LangChain handler metadata must derive from __version__")

    errors.extend(check_tracked_hygiene(root, package_dir))
    errors.extend(check_claims(iter_public_source_files(root, package_dir), root))
    return errors


def safe_member_name(name: str) -> bool:
    path = pathlib.PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def verify_wheel_record(archive: zipfile.ZipFile, dist_info: str) -> list[str]:
    errors = []
    record_name = f"{dist_info}/RECORD"
    try:
        rows = list(
            csv.reader(io.TextIOWrapper(archive.open(record_name), encoding="utf-8", newline=""))
        )
        record_names: set[str] = set()
        for row in rows:
            if len(row) != 3:
                errors.append(f"wheel RECORD row must have three fields: {row!r}")
                continue
            name, digest, size = row
            if not safe_member_name(name):
                errors.append(f"unsafe wheel RECORD path: {name}")
                continue
            if name in record_names:
                errors.append(f"duplicate wheel RECORD path: {name}")
                continue
            record_names.add(name)
            if not digest:
                if name != record_name:
                    errors.append(f"wheel RECORD entry lacks digest: {name}")
                if size:
                    errors.append(f"wheel RECORD self-entry must not declare size: {name}")
                continue
            algorithm, encoded = digest.split("=", 1)
            if algorithm != "sha256":
                errors.append(f"wheel RECORD must use sha256: {name}")
                continue
            data = archive.read(name)
            actual = base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest()).rstrip(b"=").decode()
            if actual != encoded:
                errors.append(f"wheel RECORD digest mismatch: {name}")
            if str(len(data)) != size:
                errors.append(f"wheel RECORD size mismatch: {name}")
        archive_files = {name for name in archive.namelist() if not name.endswith("/")}
        missing_from_record = sorted(archive_files - record_names)
        missing_from_archive = sorted(record_names - archive_files)
        errors.extend(f"wheel member missing from RECORD: {name}" for name in missing_from_record)
        errors.extend(f"wheel RECORD member missing from archive: {name}" for name in missing_from_archive)
    except (KeyError, ValueError, csv.Error) as exc:
        errors.append(f"invalid wheel RECORD: {exc}")
    return errors


def inspect_wheel(path: pathlib.Path, expected_version: str) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        errors.extend(f"duplicate wheel member: {name}" for name in duplicate_names)
        unsafe = [name for name in names if not safe_member_name(name)]
        errors.extend(f"unsafe wheel path: {name}" for name in unsafe)
        errors.extend(
            f"generated artifact in wheel: {name}"
            for name in names
            if "__pycache__/" in name or name.endswith(".pyc")
        )
        dist_infos = {
            name.split("/", 1)[0]
            for name in names
            if name.endswith(".dist-info/METADATA")
        }
        if len(dist_infos) != 1:
            return errors + [f"wheel must contain one dist-info directory, found {sorted(dist_infos)}"]
        dist_info = next(iter(dist_infos))
        permitted_metadata = {
            f"{dist_info}/METADATA",
            f"{dist_info}/RECORD",
            f"{dist_info}/WHEEL",
            f"{dist_info}/entry_points.txt",
        }
        for name in names:
            if name.endswith("/"):
                continue
            if name.startswith(f"{PACKAGE_NAME}/"):
                if pathlib.PurePosixPath(name).suffix != ".py":
                    errors.append(f"unexpected non-Python package payload: {name}")
                continue
            if name not in permitted_metadata:
                errors.append(f"unexpected wheel payload: {name}")
        metadata_text = archive.read(f"{dist_info}/METADATA").decode("utf-8")
        metadata = email.message_from_string(metadata_text)
        if metadata.get("Name") != PACKAGE_NAME:
            errors.append(f"wheel Name mismatch: {metadata.get('Name')!r}")
        if metadata.get("Version") != expected_version:
            errors.append(f"wheel Version mismatch: {metadata.get('Version')!r}")
        errors.extend(claim_hits(f"{path.name}:METADATA", metadata_text))
        for name in names:
            if pathlib.PurePosixPath(name).suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = archive.read(name).decode("utf-8")
            except UnicodeDecodeError:
                errors.append(f"wheel text member is not UTF-8: {name}")
                continue
            errors.extend(claim_hits(f"{path.name}:{name}", text))
        errors.extend(verify_wheel_record(archive, dist_info))
        version_name = f"{PACKAGE_NAME}/_version.py"
        try:
            artifact_version = parse_version_text(archive.read(version_name).decode("utf-8"), version_name)
        except KeyError:
            errors.append(f"wheel missing {version_name}")
        else:
            if artifact_version != expected_version:
                errors.append(f"wheel runtime version mismatch: {artifact_version}")
    return errors


def parse_version_text(text: str, name: str) -> str:
    tree = ast.parse(text, filename=name)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value
    raise GateError(f"{name}: missing literal __version__ assignment")


def inspect_sdist(path: pathlib.Path, expected_version: str) -> list[str]:
    errors = []
    prefix = f"{PACKAGE_NAME}-{expected_version}/"
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        member_names = [member.name for member in members]
        duplicate_names = sorted({name for name in member_names if member_names.count(name) > 1})
        errors.extend(f"duplicate sdist member: {name}" for name in duplicate_names)
        for member in members:
            if not safe_member_name(member.name):
                errors.append(f"unsafe sdist path: {member.name}")
            if not member.name.startswith(prefix):
                errors.append(f"sdist member outside expected prefix: {member.name}")
            if member.issym() or member.islnk():
                errors.append(f"sdist links are not permitted: {member.name}")
            if "__pycache__/" in member.name or member.name.endswith(".pyc") or "/dist/" in member.name:
                errors.append(f"generated artifact in sdist: {member.name}")
            if not member.isfile() or pathlib.PurePosixPath(member.name).suffix.lower() not in TEXT_SUFFIXES:
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                errors.append(f"could not read sdist member: {member.name}")
                continue
            text = extracted.read().decode("utf-8")
            errors.extend(claim_hits(f"{path.name}:{member.name}", text))
        try:
            pkg_info = archive.extractfile(f"{prefix}PKG-INFO")
        except KeyError:
            pkg_info = None
        if pkg_info is None:
            errors.append("sdist missing PKG-INFO")
        else:
            metadata = email.message_from_bytes(pkg_info.read())
            if metadata.get("Name") != PACKAGE_NAME:
                errors.append(f"sdist Name mismatch: {metadata.get('Name')!r}")
            if metadata.get("Version") != expected_version:
                errors.append(f"sdist Version mismatch: {metadata.get('Version')!r}")
        try:
            version_member = archive.extractfile(f"{prefix}{PACKAGE_NAME}/_version.py")
        except KeyError:
            version_member = None
        if version_member is None:
            errors.append(f"sdist missing {PACKAGE_NAME}/_version.py")
        else:
            artifact_version = parse_version_text(
                version_member.read().decode("utf-8"),
                f"{path.name}:{PACKAGE_NAME}/_version.py",
            )
            if artifact_version != expected_version:
                errors.append(f"sdist runtime version mismatch: {artifact_version}")
    return errors


def check_artifacts(dist_dir: pathlib.Path, expected_version: str) -> list[str]:
    expected_wheel = dist_dir / f"{PACKAGE_NAME}-{expected_version}-py3-none-any.whl"
    expected_sdist = dist_dir / f"{PACKAGE_NAME}-{expected_version}.tar.gz"
    errors = []
    actual = sorted(path.name for path in dist_dir.iterdir() if path.is_file())
    expected = sorted([expected_wheel.name, expected_sdist.name])
    if actual != expected:
        return [f"dist must contain exactly {expected}, found {actual}"]
    errors.extend(inspect_wheel(expected_wheel, expected_version))
    errors.extend(inspect_sdist(expected_sdist, expected_version))
    return errors


def check_tag_binding(root: pathlib.Path, tag: str, version: str) -> list[str]:
    expected_tag = f"{TAG_PREFIX}{version}"
    if tag != expected_tag:
        return [f"release tag must be {expected_tag}, found {tag}"]
    if run_git(root, "cat-file", "-t", tag) != "tag":
        return [f"release tag {tag} must be an annotated tag object"]
    head = run_git(root, "rev-parse", "HEAD")
    tag_commit = run_git(root, "rev-list", "-n", "1", tag)
    if tag_commit != head:
        return [f"tag {tag} resolves to {tag_commit}, not checked-out HEAD {head}"]
    run_git(root, "merge-base", "--is-ancestor", head, "origin/main")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--package-dir", type=pathlib.Path)
    parser.add_argument("--dist-dir", type=pathlib.Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-tag")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    package_dir = (args.package_dir or root / "packages" / "selfconnect-py").resolve()
    try:
        version = source_version(package_dir)
        if args.expected_version and version != args.expected_version:
            raise GateError(f"expected version {args.expected_version}, found {version}")
        errors = check_source_contract(root, package_dir)
        if args.dist_dir:
            errors.extend(check_artifacts(args.dist_dir.resolve(), version))
        if args.expected_tag:
            errors.extend(check_tag_binding(root, args.expected_tag, version))
    except (GateError, OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    scope = "source + artifacts" if args.dist_dir else "source"
    print(f"OK: selfconnect {version} {scope} release gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
