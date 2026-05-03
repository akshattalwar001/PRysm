import re
import fnmatch


def build_diff_position_map(raw_diff: str) -> dict[str, dict[int, int]]:
    position_map: dict[str, dict[int, int]] = {}
    current_file: str | None = None
    diff_position = 0
    current_new_line = 0
    seen_first_hunk = False

    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    for line in raw_diff.splitlines():
        if line.startswith("diff --git") or line.startswith("--- "):
            continue

        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            position_map[current_file] = {}
            diff_position = 0
            seen_first_hunk = False
            continue

        if current_file is None:
            continue

        if line.startswith("@@"):
            m = hunk_re.match(line)
            if m:
                current_new_line = int(m.group(1)) - 1
            if seen_first_hunk:
                diff_position += 1  
            else:
                seen_first_hunk = True  
            continue

        if not seen_first_hunk:
            continue

        diff_position += 1

        if line.startswith("+"):
            current_new_line += 1
            position_map[current_file][current_new_line] = diff_position
        elif line.startswith("-"):
            pass  
        elif line.startswith("\\"):
            pass  
        else:
            current_new_line += 1
            position_map[current_file][current_new_line] = diff_position

    return position_map
""" example if line 42 is changed in src/auth.py 
raw diff= 
--- a/src/auth.py          ← this is counted by github_client.py separately
+++ b/src/auth.py          ← diff position 1
@@ -10,6 +10,8 @@         ← diff position 2
 def login():              ← diff position 3
-    return None           ← diff position 4
+    token = generate()    ← diff position 5  (this is actual line 42 in the file)
+    return token          ← diff position 6
example of output of build_diff_position_map(raw_diff):
Build a map:
{
    "src/auth.py": {
        42: 5,   # line 42 in the file = position 5 in the diff
        43: 6    # line 43 in the file = position 6 in the diff
    }
}
"""

def attach_diff_positions(review_data: dict, raw_diff: str) -> dict:
    position_map = build_diff_position_map(raw_diff)
    
    print(f"[DEBUG] Position map: {position_map}")
    print(f"[DEBUG] Inline comments: {review_data.get('inline_comments', [])}")
    
    valid_comments = []

    for comment in review_data.get("inline_comments", []):
        filename = comment.get("file")
        line = comment.get("line")

        file_map = position_map.get(filename, {})
        position = file_map.get(line)

        if position is None:
            print(f"[POSTER] Skipping comment, couldn't map {filename}:{line} to a diff position")
            continue

        comment["diff_position"] = position
        valid_comments.append(comment)

    review_data["inline_comments"] = valid_comments
    return review_data

"""input review_data:
{
    "summary": {
        "verdict": "request_changes",
        "overall_score": 6,
        "tldr": "Auth logic has a SQL injection risk and an unhandled exception."
    },
    "inline_comments": [
        {
            "file": "src/auth.py",
            "line": 12,
            "severity": "security",
            "comment": "User input is directly interpolated into the SQL query, this is a SQL injection risk."
        },
        {
            "file": "src/auth.py",
            "line": 99,
            "severity": "bug",
            "comment": "This will throw an exception if user is None."
        },
        {
            "file": "src/routes.py",
            "line": 15,
            "severity": "style",
            "comment": "This function name is too vague, rename it to something descriptive."
        }
    ],
    "general_comments": [
        "Add unit tests for the login function.",
        "Consider rate limiting the login endpoint."
    ]
}

output of attach_diff_positions(review_data, raw_diff):

{
    "summary": {
        "verdict": "request_changes",
        "overall_score": 6,
        "tldr": "Auth logic has a SQL injection risk and an unhandled exception."
    },
    "inline_comments": [
        {
            "file": "src/auth.py",
            "line": 12,
            "severity": "security",
            "comment": "User input is directly interpolated into the SQL query, this is a SQL injection risk.",
            "diff_position": 5
        },
        {
            "file": "src/routes.py",
            "line": 15,
            "severity": "style",
            "comment": "This function name is too vague, rename it to something descriptive.",
            "diff_position": 4
        }
    ],
    "general_comments": [
        "Add unit tests for the login function.",
        "Consider rate limiting the login endpoint."
    ]
}

"""