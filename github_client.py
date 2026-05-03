from github import Github
from config import GITHUB_TOKEN

gh = Github(GITHUB_TOKEN)


def get_pr_diff(repo_full_name: str, pr_number: int) -> str:
    
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    files = pr.get_files()
    diff_parts = []

    for f in files:
        diff_parts.append(f"--- a/{f.filename}\n+++ b/{f.filename}")
        if f.patch:  # patch is None for binary files
            diff_parts.append(f.patch)

    return "\n".join(diff_parts)


def get_pr_metadata(repo_full_name: str, pr_number: int) -> dict:
    
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    files = pr.get_files()
    changed_files = [f.filename for f in files]

    return {
        "title": pr.title,
        "description": pr.body or "",
        "author": pr.user.login,
        "changed_files": changed_files,
        "additions": pr.additions,
        "deletions": pr.deletions,
    }


def post_review(repo_full_name: str, pr_number: int, review_data: dict):
    
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    comments = []
    for item in review_data.get("inline_comments", []):
        comments.append({
            "path": item["file"],
            "position": item["diff_position"],
            "body": f"**[{item['severity'].upper()}]** {item['comment']}",
        })

    verdict = review_data.get("summary", {}).get("verdict", "comment")
    event_map = {
        "approve": "APPROVE",
        "request_changes": "REQUEST_CHANGES",
        "comment": "COMMENT",
    }
    event = event_map.get(verdict, "COMMENT")

    summary_body = review_data.get("summary", {}).get("tldr", "Review complete.")
    score = review_data.get("summary", {}).get("overall_score", "N/A")

    body = f"## PR Review\n\n{summary_body}\n\n**Score:** {score}/10"

    general = review_data.get("general_comments", [])
    if general:
        body += "\n\n### General Feedback\n" + "\n".join(f"- {c}" for c in general)
    try:
        pr.create_review(body=body, event=event, comments=comments)
        print(f"[GITHUB] Posted review on PR #{pr_number} ({event})")
    except Exception as e:
        if "422" in str(e) or "Position could not be resolved" in str(e):
            print(f"[GITHUB] Inline comments failed, retrying without them...")
            pr.create_review(body=body, event=event, comments=[])
            print(f"[GITHUB] Posted review on PR #{pr_number} ({event}) [no inline comments]")
            if comments:
                fallback_body = "**Inline Comments:**\n\n"
                for item in review_data.get("inline_comments", []):
                    fallback_body += f"- `{item['file']}` line {item['line']} **[{item['severity'].upper()}]**: {item['comment']}\n"
                pr.create_issue_comment(fallback_body)
                print(f"[GITHUB] Posted inline comments as regular comment")
        else:
            raise