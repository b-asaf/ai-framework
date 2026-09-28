#!/usr/bin/env python3
"""open-draft-pr.py
-------------------
Deterministic push + draft PR/MR opener (see skills/pr-provider/SKILL.md and
AGENTS.md Check 4). Provider detection, URL parsing, request building and
response parsing all happen here, in code — never in an LLM's head.

What it does, in order:
  1. Refuses to run on the base branch (or main/master).
  2. Reads the origin remote URL and detects the provider
     (GitHub / GitLab / Azure DevOps).
  3. Pushes the branch (never with --force).
  4. Opens the PR/MR as a DRAFT:
       GitLab       -> git push options (single push, no token needed)
       GitHub       -> REST API, needs GITHUB_TOKEN (or GH_TOKEN)
       Azure DevOps -> REST API, needs ADO_PAT (or AZURE_DEVOPS_EXT_PAT);
                       cloud (dev.azure.com, *.visualstudio.com) and
                       Azure DevOps Server / TFS on-prem are both supported
  5. Verifies the API response really says "draft" (servers that don't support
     drafts silently ignore the flag) and reports it if not.
  6. Prints a small, fixed output contract and exits with a fixed code.

Usage:
  python open-draft-pr.py [--branch B] [--base BASE] [--title T]
                          [--body B | --body-file F] [--remote origin]

  Omitted values are derived deterministically:
    --branch  current branch
    --base    origin's default branch (origin/HEAD), else "main"
    --title   subject of the last commit
    --body    body of the last commit

Self-hosted hosts: Azure DevOps Server is detected automatically (its remote
path always contains "/_git/"). For self-hosted GitLab / GitHub Enterprise with
a host name that doesn't say so, set the provider once per repo:
  git config ai-framework.provider gitlab      # github | gitlab | ado
(GitHub Enterprise Server uses https://<host>/api/v3 automatically.)
Azure DevOps Server REST API version: tried newest-first (7.1, 7.0, 6.0, 5.1);
pin one with  git config ai-framework.adoApiVersion 6.0

Output contract (stdout, one KEY: value per line; token is never printed):
  STATUS:   DRAFT_PR_OPENED | PR_ALREADY_EXISTS | PUSHED_MANUAL_PR_NEEDED |
            PR_OPENED_NOT_DRAFT | PUSH_FAILED | API_FAILED | USAGE_ERROR
  PROVIDER: github | gitlab | ado | unknown
  URL:      PR/MR link (opened/existing), or a manual "create PR" link
  REASON:   present when STATUS is not DRAFT_PR_OPENED

Exit codes:
  0  draft PR/MR opened (or one already exists)
  1  push failed
  2  usage error / refused (e.g. on the base branch)
  4  pushed, but the provider API call failed
  5  a PR was opened but the server did NOT make it a draft (convert or
     abandon it yourself); see REASON
  10 pushed, but the PR/MR must be opened manually (no token, unknown host)
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

EXIT_OK, EXIT_PUSH_FAILED, EXIT_USAGE, EXIT_API_FAILED, EXIT_NOT_DRAFT, EXIT_MANUAL = 0, 1, 2, 4, 5, 10


# ── helpers ──────────────────────────────────────────────────────────────────

def git(*args, timeout=None):
    """Run git, return (returncode, stdout, stderr). Never raises on non-zero.
    On timeout returns (124, "", "timed out ...") instead of hanging."""
    try:
        r = subprocess.run(
            ["git", *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", (f"git {args[0]} timed out after {timeout}s — it was probably "
                         "waiting for credentials or an SSH prompt")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def redact(text, secrets):
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


def emit(status, provider="unknown", url="", reason=""):
    print(f"STATUS: {status}")
    print(f"PROVIDER: {provider}")
    if url:
        print(f"URL: {url}")
    if reason:
        print(f"REASON: {reason}")


# ── remote parsing & provider detection ──────────────────────────────────────

def parse_remote(url):
    """Return dict(scheme, host, netloc, path) from https / ssh / scp-style URLs.
    netloc = host[:port] for http(s) remotes (the port matters for on-prem
    servers); the port of an ssh remote is deliberately NOT carried over."""
    url = url.strip()
    m = re.match(r"^([\w.+-]+)://(?:[^@/]+@)?([^/:]+)(?::(\d+))?/(.+?)/?$", url)
    if m:
        scheme, host, port, path = m.group(1).lower(), m.group(2).lower(), m.group(3), m.group(4)
    else:
        m = re.match(r"^(?:[^@/]+@)?([^:/]+):(.+?)/?$", url)   # git@host:path
        if not m:
            return None
        scheme, host, port, path = "ssh", m.group(1).lower(), None, m.group(2)
    if path.endswith(".git"):
        path = path[:-4]
    netloc = f"{host}:{port}" if port and scheme in ("http", "https") else host
    return {"scheme": scheme, "host": host, "netloc": netloc, "path": path}


def detect_provider(host, override="", path=""):
    if override in ("github", "gitlab", "ado"):
        return override
    if host == "github.com":
        return "github"
    if host in ("dev.azure.com", "ssh.dev.azure.com") or host.endswith(".visualstudio.com"):
        return "ado"
    if "_git" in path.split("/"):          # Azure DevOps Server / TFS (on-prem)
        return "ado"
    if "gitlab" in host:
        return "gitlab"
    return "unknown"


def parse_ado(host, path, scheme="https", netloc=None):
    """Return (api_base, collection, project, repo) for Azure DevOps remotes.
    `collection` is "org" on dev.azure.com, "" on *.visualstudio.com, and the
    collection path (e.g. "tfs/DefaultCollection") on Azure DevOps Server.
    Components are percent-DECODED here (remote URLs encode spaces as %20);
    every URL built later encodes them again exactly once."""
    parts = [urllib.parse.unquote(p) for p in path.split("/") if p]
    if host == "ssh.dev.azure.com":                          # v3/org/project/repo
        if len(parts) >= 4 and parts[0] == "v3":
            return "https://dev.azure.com", parts[1], parts[2], parts[3]
        return None
    if "_git" not in parts:
        return None
    i = parts.index("_git")
    if i + 1 >= len(parts):
        return None
    repo = parts[i + 1]
    if host.endswith(".visualstudio.com"):                   # [DefaultCollection/]project/_git/repo
        rest = [p for p in parts[:i] if p.lower() != "defaultcollection"]
        return f"https://{host}", "", (rest[-1] if rest else repo), repo
    if host == "dev.azure.com":                              # org/project/_git/repo  (or org/_git/repo)
        if i == 0:
            return None
        return "https://dev.azure.com", parts[0], (parts[i - 1] if i >= 2 else repo), repo
    if i == 0:                                               # on-prem: <collection>/<project>/_git/<repo>
        return None
    api_scheme = scheme if scheme in ("http", "https") else "https"
    return f"{api_scheme}://{netloc or host}", "/".join(parts[: i - 1]), parts[i - 1], repo


# ── request building (pure functions, unit-testable) ─────────────────────────

def github_request(host, path, branch, base, title, body, token):
    api = "https://api.github.com" if host == "github.com" else f"https://{host}/api/v3"
    return (
        f"{api}/repos/{path}/pulls",
        {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json",
         "Content-Type": "application/json",
         "User-Agent": "ai-framework-open-draft-pr"},
        {"title": title, "head": branch, "base": base, "body": body, "draft": True},
    )


def _ado_root(api_base, collection, project):
    q = lambda x: urllib.parse.quote(x, safe="")
    segs = [q(c) for c in collection.split("/") if c] + [q(project)]
    return f"{api_base}/" + "/".join(segs)


def ado_request(api_base, collection, project, repo, branch, base, title, body, pat,
                api_version="7.1"):
    q = lambda x: urllib.parse.quote(x, safe="")
    auth = base64.b64encode(f":{pat}".encode()).decode()
    return (
        f"{_ado_root(api_base, collection, project)}/_apis/git/repositories/{q(repo)}"
        f"/pullrequests?api-version={api_version}",
        {"Authorization": f"Basic {auth}",
         "Content-Type": "application/json",
         "User-Agent": "ai-framework-open-draft-pr"},
        {"sourceRefName": f"refs/heads/{branch}",
         "targetRefName": f"refs/heads/{base}",
         "title": title, "description": body, "isDraft": True},
    )


def manual_url(provider, host, path, branch, base, ado=None):
    b, t = urllib.parse.quote(branch, safe=""), urllib.parse.quote(base, safe="")
    if provider == "github":
        return f"https://{host}/{path}/compare/{t}...{b}?expand=1"
    if provider == "gitlab":
        return (f"https://{host}/{path}/-/merge_requests/new"
                f"?merge_request[source_branch]={b}&merge_request[target_branch]={t}")
    if provider == "ado" and ado:
        api_base, collection, project, repo = ado
        return (f"{_ado_root(api_base, collection, project)}/_git/"
                f"{urllib.parse.quote(repo, safe='')}/pullrequestcreate?sourceRef={b}&targetRef={t}")
    return ""


def ado_web_url(api_base, collection, project, repo, pr_id):
    return (f"{_ado_root(api_base, collection, project)}/_git/"
            f"{urllib.parse.quote(repo, safe='')}/pullrequest/{pr_id}")


def version_rejected(data):
    """True if an ADO 400 means 'this server doesn't know that api-version'."""
    text = (json.dumps(data) if isinstance(data, dict) else str(data)).lower()
    return "requested version" in text or "vssversionoutofrange" in text


# ── network ──────────────────────────────────────────────────────────────────

def post_json(url, headers, payload):
    """Return (status_code, parsed_json_or_text). Never raises on HTTP errors."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        raw, code = e.read().decode("utf-8", errors="replace"), e.code
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, str(e)
    try:
        return code, json.loads(raw)
    except ValueError:
        return code, raw


# ── main flow ────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="Push a branch and open a draft PR/MR.")
    ap.add_argument("--branch")
    ap.add_argument("--base")
    ap.add_argument("--title")
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--remote", default="origin")
    args = ap.parse_args(argv)

    # -- derive defaults deterministically
    branch = args.branch or git("branch", "--show-current")[1]
    if not branch:
        emit("USAGE_ERROR", reason="No current branch (detached HEAD?) and --branch not given.")
        return EXIT_USAGE
    base = args.base
    if not base:
        rc, out, _ = git("symbolic-ref", f"refs/remotes/{args.remote}/HEAD")
        base = out.rsplit("/", 1)[-1] if rc == 0 and out else "main"
    if branch == base or branch in ("main", "master"):
        emit("USAGE_ERROR", reason=f"Refusing to open a PR from '{branch}' (base is '{base}'). "
                                   "Work must be on its own branch.")
        return EXIT_USAGE
    title = args.title or git("log", "-1", "--pretty=%s")[1]
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = args.body if args.body is not None else git("log", "-1", "--pretty=%b")[1]

    # -- detect provider
    rc, remote_url, _ = git("remote", "get-url", args.remote)
    if rc != 0 or not remote_url:
        emit("PUSH_FAILED", reason=f"No '{args.remote}' remote configured. "
                                   f"Add one: git remote add {args.remote} <url>")
        return EXIT_PUSH_FAILED
    # An unparseable remote (local path, odd scheme) must never block the push:
    # it just means "provider unknown" (unless overridden via git config).
    parsed = parse_remote(remote_url) or {"scheme": "", "host": "", "netloc": "", "path": ""}
    host, netloc, path = parsed["host"], parsed["netloc"], parsed["path"]
    override = git("config", "--get", "ai-framework.provider")[1].lower()
    provider = detect_provider(host, override, path)
    ado = parse_ado(host, path, parsed["scheme"], netloc) if provider == "ado" else None

    # -- push (GitLab: push + MR in one command)
    push_cmd = ["push", "-u", args.remote, branch]
    if provider == "gitlab":
        mr_title = title if title.lower().startswith(("draft:", "wip:")) else f"Draft: {title}"
        push_cmd += ["-o", "merge_request.create", "-o", f"merge_request.target={base}",
                     "-o", f"merge_request.title={mr_title}", "-o", "merge_request.draft"]
        if body and "\n" not in body and "\r" not in body:
            push_cmd += ["-o", f"merge_request.description={body}"]
    rc, out, err = git(*push_cmd, timeout=180)
    if rc != 0:
        lines = [l.strip() for l in (err or out).splitlines() if l.strip()]
        reason = " ".join(lines[-3:]) if lines else "git push failed"
        emit("PUSH_FAILED", provider, reason=f"{reason} (run `git push -u {args.remote} {branch}` "
                                             "manually to see the full git error)")
        return EXIT_PUSH_FAILED

    manual = manual_url(provider, netloc, path, branch, base, ado)

    if provider == "gitlab":
        m = re.search(r"https?://\S+/merge_requests/\d+", f"{out}\n{err}")
        if m:
            emit("DRAFT_PR_OPENED", provider, m.group(0))
            return EXIT_OK
        emit("PUSHED_MANUAL_PR_NEEDED", provider, manual,
             "Pushed, but the server returned no merge request link (push options "
             "may be disabled or unsupported on this GitLab).")
        return EXIT_MANUAL

    if provider == "unknown" or (provider == "ado" and not ado):
        emit("PUSHED_MANUAL_PR_NEEDED", provider, manual,
             f"Unrecognized remote '{host or remote_url}'. If it is self-hosted, run: "
             "git config ai-framework.provider <github|gitlab|ado>")
        return EXIT_MANUAL

    # -- GitHub / Azure DevOps: need a token
    if provider == "github":
        var, token = "GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    else:
        var, token = "ADO_PAT", os.environ.get("ADO_PAT") or os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if not token:
        emit("PUSHED_MANUAL_PR_NEEDED", provider, manual,
             f"${var} is not set in the environment, so the draft PR cannot be opened automatically.")
        return EXIT_MANUAL

    if provider == "github":
        url, headers, payload = github_request(netloc, path, branch, base, title, body, token)
        code, data = post_json(url, headers, payload)
    else:
        pinned = git("config", "--get", "ai-framework.adoApiVersion")[1]
        for ver in ([pinned] if pinned else ["7.1", "7.0", "6.0", "5.1"]):
            url, headers, payload = ado_request(*ado, branch, base, title, body, token, ver)
            code, data = post_json(url, headers, payload)
            if not (code == 400 and version_rejected(data)):
                break                      # only walk down versions on a version error
    detail = redact(json.dumps(data) if isinstance(data, dict) else str(data), [token])[:300]

    if provider == "github" and code == 201 and isinstance(data, dict):
        link, is_draft = data.get("html_url", ""), data.get("draft") is True
    elif provider == "ado" and code in (200, 201) and isinstance(data, dict) and data.get("pullRequestId"):
        link, is_draft = ado_web_url(*ado, data["pullRequestId"]), data.get("isDraft") is True
    else:
        link = None
    if link is not None:
        if is_draft:
            emit("DRAFT_PR_OPENED", provider, link)
            return EXIT_OK
        emit("PR_OPENED_NOT_DRAFT", provider, link,
             "The server created the PR but did not mark it as a draft (it may not support "
             "drafts). Convert it to a draft or abandon it yourself.")
        return EXIT_NOT_DRAFT
    if (provider == "github" and code == 422 and "already exists" in detail.lower()) or \
       (provider == "ado" and code == 409):
        emit("PR_ALREADY_EXISTS", provider, manual.split("?")[0],
             "A PR for this branch already exists; nothing was created.")
        return EXIT_OK

    emit("API_FAILED", provider, manual, f"HTTP {code}: {detail}")
    return EXIT_API_FAILED


if __name__ == "__main__":
    sys.exit(main())