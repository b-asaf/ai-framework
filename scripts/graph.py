#!/usr/bin/env python3
"""graph.py - build, update and query the code graph of a project (DEC-030, S.13).

Usage:
  python graph.py [--repo PATH] build               # first graph: graphify extract --code-only (no API key, no cost)
  python graph.py [--repo PATH] update              # re-extract the changed code; builds the graph when there is none
  python graph.py [--repo PATH] query "<question>"  # graphify query on the project graph
  python graph.py [--repo PATH] path "<A>" "<B>"    # shortest path between two nodes
  python graph.py [--repo PATH] explain "<X>"       # a node and its neighbors

The graph is kept in the folder for generated files (DEC-026): <generated folder>/graphify/graphify-out/graph.json.
That folder gets a .gitignore holding `*`, which also ignores the file itself, so `git add .` never takes a graph
file along. The place is given to graphify through GRAPHIFY_OUT (an absolute path), which graphify 0.9.20 honors in
`extract` and `update` although its help does not list it; a graph file that does not appear is an error.

graphify's own git hooks and installers are not used: the hook writes a .gitattributes into the project and a second
graph at the repository root, and the installers write into AGENTS.md, CLAUDE.md and the tool config folders.

build and update print "KEY: value" lines: STATUS: OK | ERROR, GRAPH: <graph.json>, REASON: <why> (only on ERROR).
query, path and explain print what graphify prints. Exit code: 0 OK, 2 ERROR (graphify's own code for the read commands).
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

HELPER = Path("execution") / "runner" / "generated_dir.py"
SUBDIR = "graphify"
OUT_NAME = "graphify-out"
BUILD_TIMEOUT, UPDATE_TIMEOUT, READ_TIMEOUT = 900, 300, 120
READ_COMMANDS = {"query": 1, "path": 2, "explain": 1}


class GraphError(Exception):
    """The graph cannot be built, updated or read."""


def root_from_git_setting():
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "aiFramework.root"],
            capture_output=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return Path(value) if result.returncode == 0 and value else None


def find_framework_root():
    beside = Path(__file__).resolve().parent.parent
    for candidate in (beside, root_from_git_setting()):
        if candidate is not None and (candidate / HELPER).is_file():
            return candidate
    raise GraphError("the framework folder was not found; run `python setup.py`, which sets git aiFramework.root")


def load_generated_dir():
    """The generated_dir helper of the runner, loaded by file so that the runner package is not imported."""
    spec = importlib.util.spec_from_file_location("generated_dir", find_framework_root() / HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(argv, cwd, timeout, env=None):
    try:
        return subprocess.run(
            argv, cwd=str(cwd), env=env, capture_output=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise GraphError(f"`{Path(argv[0]).name} {argv[1]}` did not finish within {timeout} s") from error
    except OSError as error:
        raise GraphError(f"cannot run {argv[0]}: {error}") from error


def repo_root(start):
    result = _run(["git", "rev-parse", "--show-toplevel"], start, 30)
    top = result.stdout.strip()
    if result.returncode != 0 or not top:
        raise GraphError(f"{start} is not inside a git repository")
    return Path(top)


def graph_folder(repo):
    helper = load_generated_dir()
    try:
        return helper.absolute_dir(repo) / SUBDIR
    except helper.GeneratedDirError as error:
        raise GraphError(str(error)) from error


def graph_file(folder):
    return folder / OUT_NAME / "graph.json"


def keep_out_of_git(folder):
    folder.mkdir(parents=True, exist_ok=True)
    ignore = folder / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8", newline="\n")


def graphify(args, repo, timeout, extra_env=None):
    exe = shutil.which("graphify")
    if exe is None:
        raise GraphError("graphify is not installed; run `python setup.py` in the framework folder")
    env = {**os.environ, **(extra_env or {})}
    return _run([exe, *args], repo, timeout, env)


def _check(result, what):
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip()[-300:]
        raise GraphError(f"{what} failed (exit {result.returncode}): {tail}")


def build(repo, folder):
    keep_out_of_git(folder)
    env = {"GRAPHIFY_OUT": str(folder / OUT_NAME)}
    _check(graphify(["extract", ".", "--code-only"], repo, BUILD_TIMEOUT, env), "graphify extract")
    return graph_file(folder)


def update(repo, folder):
    if not graph_file(folder).is_file():
        return build(repo, folder)
    keep_out_of_git(folder)
    env = {"GRAPHIFY_OUT": str(folder / OUT_NAME)}
    _check(graphify(["update", "."], repo, UPDATE_TIMEOUT, env), "graphify update")
    return graph_file(folder)


def write_command(command, repo, folder):
    graph = (build if command == "build" else update)(repo, folder)
    if not graph.is_file():
        raise GraphError(f"graphify finished but {graph.as_posix()} was not written")
    print("STATUS: OK")
    print(f"GRAPH: {graph.as_posix()}")
    return 0


def read_command(command, words, repo, folder):
    graph = graph_file(folder)
    if not graph.is_file():
        raise GraphError("there is no graph yet; run `graph.py build` first")
    result = graphify([command, *words, "--graph", str(graph)], repo, READ_TIMEOUT)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def parse(argv):
    parser = argparse.ArgumentParser(description="Build, update and query the code graph of a project.")
    parser.add_argument("--repo", default=".")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "update"):
        commands.add_parser(name)
    for name, count in READ_COMMANDS.items():
        commands.add_parser(name).add_argument("words", nargs=count)
    return parser.parse_args(argv)


def run(args):
    repo = repo_root(Path(args.repo).resolve())
    folder = graph_folder(repo)
    if args.command in READ_COMMANDS:
        return read_command(args.command, args.words, repo, folder)
    return write_command(args.command, repo, folder)


def main(argv=None):
    args = parse(argv)
    try:
        return run(args)
    except GraphError as error:
        print("STATUS: ERROR")
        print(f"REASON: {error}")
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
