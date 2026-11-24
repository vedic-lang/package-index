"""Validate registry metadata and inspect new releases without executing package code."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}")


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd)


def entries(ref):
    result = {}
    tree = git("ls-tree", "-rz", ref, "--", "packages")
    for row in filter(None, tree.split(b"\0")):
        meta, path = row.decode().split("\t", 1)
        name = Path(path).stem
        if not NAME.fullmatch(name) or path != f"packages/{name}.toml" or not meta.startswith("100644 blob "):
            raise ValueError(f"Invalid index file {path}")
        doc = tomllib.loads(git("show", f"{ref}:{path}").decode())
        repo = doc.get("repository", "")
        if (not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo)
                or repo.split("/")[1] in {".", ".."} or repo.endswith(".git")):
            raise ValueError(f"Invalid GitHub repository in {path}")
        releases = doc.get("releases")
        if not isinstance(releases, dict) or not releases:
            raise ValueError(f"Missing releases in {path}")
        for version, commit in releases.items():
            if (not VERSION.fullmatch(version) or any(int(n) > 2**64-1 for n in version.split("."))
                    or not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)):
                raise ValueError(f"Invalid release in {path}: {version}")
        result[name] = doc
    return result


def check_source(index, name, version, commit):
    repo = index[name]["repository"]
    with tempfile.TemporaryDirectory() as temp:
        git("init", "--quiet", "--bare", "--template=", temp)
        git("-c", "http.followRedirects=false", "fetch", "--quiet", "--no-tags", "--depth=1",
            "--", f"https://github.com/{repo}.git", commit, cwd=temp)
        if git("rev-parse", "FETCH_HEAD^{commit}", cwd=temp).decode().strip() != commit:
            raise ValueError(f"Expected a commit for {name} {version}")
        for path in ("lib.ved", "vedic.toml"):
            tree = git("ls-tree", commit, "--", path, cwd=temp)
            if not tree.startswith((b"100644 blob ", b"100755 blob ")):
                raise ValueError(f"Missing regular {path} in {name} {version}")
        manifest = tomllib.loads(git("show", f"{commit}:vedic.toml", cwd=temp).decode())
    package = manifest.get("package", {})
    if package.get("name") != name or package.get("version") != version:
        raise ValueError(f"Manifest disagrees with index for {name} {version}")
    for dep, pin in manifest.get("dependencies", {}).items():
        if dep not in index or pin not in index[dep]["releases"]:
            raise ValueError(f"Missing indexed dependency {dep} {pin} for {name} {version}")
    print(f"Verified {name} {version} at {repo}@{commit}")


def validate(base, head):
    old = entries(base)
    index = entries(head)
    for name, prior in old.items():
        if name not in index or index[name]["repository"] != prior["repository"]:
            raise ValueError(f"Cannot remove or redirect indexed package {name}")
        for version, commit in prior["releases"].items():
            if index[name]["releases"].get(version) != commit:
                raise ValueError(f"Cannot replace or remove {name} {version}")
    for name, entry in index.items():
        for version, commit in entry["releases"].items():
            if version not in old.get(name, {}).get("releases", {}):
                check_source(index, name, version, commit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head", nargs="?", default="HEAD")
    args = parser.parse_args()
    validate(args.base, args.head)
