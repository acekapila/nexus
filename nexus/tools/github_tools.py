import subprocess
import os
import json
import tempfile

# ── Helper ───────────────────────────────────────────────────────────────────
def run(cmd: str, cwd: str = None) -> str:
    """Run a shell command and return output or error."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0:
        return f"❌ Error: {result.stderr.strip() or result.stdout.strip()}"
    return result.stdout.strip() or "✅ Done."


def gh(cmd: str, cwd: str = None) -> str:
    """Run a gh CLI command."""
    return run(f"gh {cmd}", cwd=cwd)


# ── Auth ─────────────────────────────────────────────────────────────────────
def check_auth() -> str:
    """Check if gh CLI is authenticated."""
    return gh("auth status")


def get_username() -> str:
    """Get the authenticated GitHub username."""
    return gh("api user --jq .login")


# ── Repos ────────────────────────────────────────────────────────────────────
def list_repos(username: str = "") -> str:
    """List repos for a user. Uses authenticated user if username is empty."""
    if not username:
        username = get_username()
    result = gh(f"repo list {username} --limit 50 --json name,description,visibility,url")
    try:
        repos = json.loads(result)
        lines = [f"📁 [{r['visibility']}] **{r['name']}** — {r['description'] or 'No description'}\n   {r['url']}" for r in repos]
        return f"Repos for {username}:\n\n" + "\n\n".join(lines)
    except Exception:
        return result


def create_repo(name: str, description: str = "", private: bool = False, auto_init: bool = True) -> str:
    """Create a new GitHub repository."""
    visibility = "--private" if private else "--public"
    init = "--add-readme" if auto_init else ""
    return gh(f'repo create {name} {visibility} {init} --description "{description}"')


def delete_repo(repo_name: str) -> str:
    """Delete a GitHub repository. Format: owner/repo"""
    return gh(f"repo delete {repo_name} --yes")


def clone_repo(repo_name: str, target_dir: str = "/tmp") -> str:
    """Clone a repo locally. Format: owner/repo"""
    return gh(f"repo clone {repo_name} {target_dir}/{repo_name.split('/')[-1]}")


def repo_info(repo_name: str) -> str:
    """Get info about a repo. Format: owner/repo"""
    return gh(f"repo view {repo_name}")


# ── Files & Commits ──────────────────────────────────────────────────────────
def push_file(repo_name: str, file_path: str, content: str, commit_message: str = "Update file via Skyler") -> str:
    """
    Push a file to a GitHub repo.
    repo_name: owner/repo
    file_path: path inside the repo e.g. index.html
    content: file content as string
    """
    repo_short = repo_name.split("/")[-1]
    username = get_username()
    work_dir = f"/tmp/skyler_{repo_short}"

    # Clone if not already cloned
    if not os.path.exists(work_dir):
        clone_result = run(f"gh repo clone {repo_name} {work_dir}")
        if "❌" in clone_result:
            return clone_result

    # Configure git identity
    run(f'git config user.email "skyler-bot@github.com"', cwd=work_dir)
    run(f'git config user.name "Skyler"', cwd=work_dir)

    # Write the file
    full_path = os.path.join(work_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

    # Stage, commit, push
    run("git add .", cwd=work_dir)
    run(f'git commit -m "{commit_message}"', cwd=work_dir)
    result = run("git push", cwd=work_dir)
    return f"✅ Pushed `{file_path}` to `{repo_name}`\n{result}"


def push_multiple_files(repo_name: str, files: dict, commit_message: str = "Update files via Skyler") -> str:
    """
    Push multiple files to a repo at once.
    files: dict of {file_path: content}
    """
    repo_short = repo_name.split("/")[-1]
    work_dir = f"/tmp/skyler_{repo_short}"

    if not os.path.exists(work_dir):
        clone_result = run(f"gh repo clone {repo_name} {work_dir}")
        if "❌" in clone_result:
            return clone_result

    run(f'git config user.email "skyler-bot@github.com"', cwd=work_dir)
    run(f'git config user.name "Skyler"', cwd=work_dir)

    for file_path, content in files.items():
        full_path = os.path.join(work_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    run("git add .", cwd=work_dir)
    run(f'git commit -m "{commit_message}"', cwd=work_dir)
    result = run("git push", cwd=work_dir)
    return f"✅ Pushed {len(files)} file(s) to `{repo_name}`\n{result}"


# ── GitHub Pages ─────────────────────────────────────────────────────────────
def enable_pages(repo_name: str, branch: str = "main", path: str = "/") -> str:
    """Enable GitHub Pages for a repo. Handles already-enabled case gracefully."""
    username = repo_name.split("/")[0]
    repo_short = repo_name.split("/")[1]
    pages_url = f"https://{username}.github.io/{repo_short}/"

    # First check if Pages is already enabled
    check = gh(f"api repos/{repo_name}/pages")
    if "❌" not in check:
        try:
            data = json.loads(check)
            existing_url = data.get("html_url", pages_url)
            return f"✅ GitHub Pages already enabled!\n🌐 URL: {existing_url}"
        except Exception:
            pass

    # Try to enable Pages via API
    result = gh(
        f'api repos/{repo_name}/pages '
        f'--method POST '
        f'--field source[branch]={branch} '
        f'--field "source[path]=/"'
    )

    if "❌" not in result:
        return f"✅ GitHub Pages enabled!\n🌐 URL: {pages_url}\n⏳ Note: Site may take 1-2 minutes to go live."

    # If API fails, try gh CLI pages command as fallback
    result2 = run(f"gh repo edit {repo_name} --homepage {pages_url}")

    # Final fallback — just return the URL even if enabling failed
    # (user may need to enable manually from GitHub settings)
    if "404" in result or "Not Found" in result:
        return (
            f"⚠️ Could not auto-enable Pages (API returned 404 — may need GitHub Pro for private repos, "
            f"or Pages may not be available on this plan).\n\n"
            f"To enable manually:\n"
            f"1. Go to https://github.com/{repo_name}/settings/pages\n"
            f"2. Under 'Source' select branch `{branch}` and folder `/`\n"
            f"3. Click Save\n\n"
            f"🌐 Once enabled, your site will be at: {pages_url}"
        )

    return result


def get_pages_status(repo_name: str) -> str:
    """Get GitHub Pages status for a repo."""
    result = gh(f"api repos/{repo_name}/pages")
    try:
        data = json.loads(result)
        return f"🌐 Pages URL: {data.get('html_url', 'Not available')}\nStatus: {data.get('status', 'unknown')}"
    except Exception:
        return result


def create_showcase_site(repo_name: str, project_title: str, project_description: str, features: list = []) -> str:
    """
    Create and publish a project showcase GitHub Pages site.
    repo_name: owner/repo (repo must already exist)
    """
    features_html = "\n".join([f"<li>{f}</li>" for f in features]) if features else "<li>Built with Python</li><li>Powered by Skyler AI Agent</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #e6edf3;
            min-height: 100vh;
        }}
        header {{
            background: linear-gradient(135deg, #161b22, #1f2937);
            padding: 60px 20px;
            text-align: center;
            border-bottom: 1px solid #30363d;
        }}
        header h1 {{
            font-size: 3rem;
            background: linear-gradient(90deg, #58a6ff, #bc8cff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 16px;
        }}
        header p {{
            font-size: 1.2rem;
            color: #8b949e;
            max-width: 600px;
            margin: 0 auto;
        }}
        .badge {{
            display: inline-block;
            background: #238636;
            color: #fff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-top: 16px;
        }}
        main {{
            max-width: 900px;
            margin: 60px auto;
            padding: 0 20px;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 24px;
        }}
        .card h2 {{
            color: #58a6ff;
            margin-bottom: 16px;
            font-size: 1.4rem;
        }}
        .card ul {{
            list-style: none;
            padding: 0;
        }}
        .card ul li {{
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
            color: #c9d1d9;
        }}
        .card ul li:before {{
            content: "→ ";
            color: #58a6ff;
        }}
        .card ul li:last-child {{
            border-bottom: none;
        }}
        .footer {{
            text-align: center;
            padding: 40px;
            color: #484f58;
            border-top: 1px solid #21262d;
            font-size: 0.9rem;
        }}
        .footer a {{
            color: #58a6ff;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{project_title}</h1>
        <p>{project_description}</p>
        <span class="badge">✨ Live on GitHub Pages</span>
    </header>
    <main>
        <div class="card">
            <h2>🚀 Features</h2>
            <ul>
                {features_html}
            </ul>
        </div>
        <div class="card">
            <h2>🤖 Powered By</h2>
            <ul>
                <li>Skyler — Personal AI Agent (Discord)</li>
                <li>Claude by Anthropic</li>
                <li>GitHub Pages</li>
                <li>Python + discord.py</li>
            </ul>
        </div>
    </main>
    <footer class="footer">
        <p>Built and deployed by <a href="https://github.com/{repo_name.split('/')[0]}">@{repo_name.split('/')[0]}</a> using Skyler AI Agent</p>
    </footer>
</body>
</html>"""

    # Push the index.html
    push_result = push_file(repo_name, "index.html", html, "Deploy project showcase via Skyler")
    if "❌" in push_result:
        return push_result

    # Enable GitHub Pages
    pages_result = enable_pages(repo_name)
    return f"{push_result}\n\n{pages_result}"


# ── Issues ───────────────────────────────────────────────────────────────────
def list_issues(repo_name: str, state: str = "open") -> str:
    """List issues in a repo. state: open, closed, all"""
    result = gh(f"issue list --repo {repo_name} --state {state} --json number,title,state,url")
    try:
        issues = json.loads(result)
        if not issues:
            return f"No {state} issues in {repo_name}"
        lines = [f"#{i['number']} [{i['state']}] {i['title']}\n   {i['url']}" for i in issues]
        return "\n\n".join(lines)
    except Exception:
        return result


def create_issue(repo_name: str, title: str, body: str = "", labels: str = "") -> str:
    """Create an issue in a repo."""
    label_flag = f'--label "{labels}"' if labels else ""
    return gh(f'issue create --repo {repo_name} --title "{title}" --body "{body}" {label_flag}')


def close_issue(repo_name: str, issue_number: int) -> str:
    """Close an issue by number."""
    return gh(f"issue close {issue_number} --repo {repo_name}")


def comment_issue(repo_name: str, issue_number: int, comment: str) -> str:
    """Add a comment to an issue."""
    return gh(f'issue comment {issue_number} --repo {repo_name} --body "{comment}"')


# ── Pull Requests ────────────────────────────────────────────────────────────
def list_prs(repo_name: str, state: str = "open") -> str:
    """List pull requests in a repo."""
    result = gh(f"pr list --repo {repo_name} --state {state} --json number,title,state,url")
    try:
        prs = json.loads(result)
        if not prs:
            return f"No {state} PRs in {repo_name}"
        lines = [f"#{p['number']} [{p['state']}] {p['title']}\n   {p['url']}" for p in prs]
        return "\n\n".join(lines)
    except Exception:
        return result


def create_pr(repo_name: str, title: str, body: str = "", base: str = "main", head: str = "") -> str:
    """Create a pull request."""
    head_flag = f"--head {head}" if head else ""
    return gh(f'pr create --repo {repo_name} --title "{title}" --body "{body}" --base {base} {head_flag}')


def merge_pr(repo_name: str, pr_number: int) -> str:
    """Merge a pull request."""
    return gh(f"pr merge {pr_number} --repo {repo_name} --merge")
