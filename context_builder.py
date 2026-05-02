import fnmatch #for matching file patterns

SKIP_PATTERNS = [
    "*.lock",
    "*.min.js",
    "*.min.css",
    "dist/*",
    "build/*",
    "__pycache__/*",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "*.pyc",
    ".env*",
    "*.map",
]

MAX_CONTEXT_CHARS = 80_000  # safe limit for 128k context window


def should_skip_file(filename: str) -> bool:
    for pattern in SKIP_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

"""example of input raw_diff:
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,8 @@
 def login():
-    return None
+    token = generate_token()
+    return token
--- a/src/routes.py
+++ b/src/routes.py
@@ -5,3 +5,4 @@
 def home():
-    pass
+    return "hello" 


output of parse_diff_by_file(raw_diff):
{
    "src/auth.py": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -10,6 +10,8 @@\n def login():\n-    return None\n+    token = generate_token()\n+    return token",
    "src/routes.py": "--- a/src/routes.py\n+++ b/src/routes.py\n@@ -5,3 +5,4 @@\n def home():\n-    pass\n+    return \"hello\""
}

"""

def parse_diff_by_file(raw_diff: str) -> dict[str, str]:
    """
    Takes the full diff string and splits it into a dictionary where each key is a filename and each value is that file's diff chunk.
    Returns something like:
{
    "src/auth.py": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ ...",
    "src/routes.py": "--- a/src/routes.py\n+++ b/src/routes.py\n@@ ..."
}
    """
    files = {}
    current_file = None
    current_lines = []

    for line in raw_diff.splitlines():
        if line.startswith("--- a/"):
            if current_file:
                files[current_file] = "\n".join(current_lines)
            current_file = line[6:]  # strip "--- a/"
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_file:
        files[current_file] = "\n".join(current_lines)

    return files


""" input raw_diff: "--- a/src/auth.py\n+++ b/src/auth.py\n..."

    input of pre_metdata: pr_metadata = {
    "title": "Add user authentication",
    "author": "akshattalwar001",
    "description": "Adds JWT login and signup",
    "changed_files": ["src/auth.py", "src/routes.py", "package-lock.json"],
    "additions": 143,
    "deletions": 12
}

    output of build_prompt(raw_diff, pr_metadata):
    [
    {
        "prompt": "You are a senior software engineer reviewing a pull request.
                    \n\nPR Title: Add user authentication\nAuthor: akshattalwar001\n...",
        "files_covered": ["src/auth.py", "src/routes.py"]
    }
    ]
"""
def build_prompt(raw_diff: str, pr_metadata: dict) -> list[dict]:
    
    file_diffs = parse_diff_by_file(raw_diff)

    
    filtered = { # filter junk files
        filename: diff
        for filename, diff in file_diffs.items()
        if not should_skip_file(filename)
    }

    if not filtered:
        return []

    
    chunks = [] # chunk files so we dont blow the context window
    current_chunk_files = []
    current_chunk_size = 0

    for filename, diff in filtered.items():
        size = len(diff)
        if current_chunk_size + size > MAX_CONTEXT_CHARS and current_chunk_files:
            chunks.append(current_chunk_files)
            current_chunk_files = []
            current_chunk_size = 0
        current_chunk_files.append((filename, diff))
        current_chunk_size += size

    if current_chunk_files:
        chunks.append(current_chunk_files)

    prompts = []
    for chunk in chunks:
        files_covered = [f for f, _ in chunk]
        diff_text = "\n\n".join(
            f"### File: {filename}\n{diff}" for filename, diff in chunk
        )

        prompt = f"""You are a senior software engineer reviewing a pull request.

PR Title: {pr_metadata['title']}
Author: {pr_metadata['author']}
Description: {pr_metadata['description'] or 'No description provided.'}

Review the following diff carefully. Look for:
- Bugs: null/undefined checks, off-by-one errors, unhandled exceptions, wrong logic
- Security: hardcoded secrets, SQL injection, unvalidated inputs, exposed endpoints
- Performance: N+1 queries, blocking calls in async context, unnecessary loops
- Style: dead code, missing error handling, unclear naming (only flag real issues, not nitpicks)

Diff:
{diff_text}

Respond ONLY with a valid JSON object. No explanation, no markdown, no text outside the JSON.

JSON schema:
{{
  "summary": {{
    "verdict": "approve | request_changes | comment",
    "overall_score": <integer 1-10>,
    "tldr": "<2-3 sentence summary for the PR author>"
  }},
  "inline_comments": [
    {{
      "file": "<filename>",
      "line": <line number in the diff>,
      "severity": "bug | security | performance | style",
      "comment": "<clear, actionable explanation of the issue>"
    }}
  ],
  "general_comments": [
    "<any high-level feedback that doesn't belong on a specific line>"
  ]
}}"""

        prompts.append({"prompt": prompt, "files_covered": files_covered})

    return prompts