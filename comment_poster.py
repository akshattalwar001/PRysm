def build_diff_position_map(raw_diff: str) -> dict[str, dict[int, int]]:
    
    position_map = {}
    current_file = None
    diff_position = 0
    current_line = 0  

    for line in raw_diff.splitlines():
        if line.startswith("--- a/"):
            current_file = line[6:]
            position_map[current_file] = {}
            diff_position = 0

        elif line.startswith("+++ b/"):
            diff_position += 1

        elif line.startswith("@@ "):
            # @@ -old_start,old_count +new_start,new_count @@
            diff_position += 1
            try:
                new_info = line.split("+")[1].split("@@")[0].strip()
                new_start = int(new_info.split(",")[0])
                current_line = new_start - 1  # will be incremented on first + line
            except (IndexError, ValueError):
                pass

        elif line.startswith("+"):
            diff_position += 1
            current_line += 1
            if current_file:
                position_map[current_file][current_line] = diff_position

        elif line.startswith("-"):
            diff_position += 1
            
        else:
            diff_position += 1
            current_line += 1

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