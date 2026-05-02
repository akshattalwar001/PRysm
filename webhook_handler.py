import hmac
import hashlib
from fastapi import Request, HTTPException
from config import WEBHOOK_SECRET


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature_header)


def parse_pr_event(payload: dict) -> dict | None:
    action = payload.get("action")
    if action not in ("opened", "synchronize", "reopened"):
        return None

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    return {
        "action": action,
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title"),
        "pr_author": pr.get("user", {}).get("login"),
        "base_branch": pr.get("base", {}).get("ref"),
        "head_branch": pr.get("head", {}).get("ref"),
        "head_sha": pr.get("head", {}).get("sha"),
        "repo_full_name": repo.get("full_name"),  #like "akshattalwar001/PRysm"
        "pr_url": pr.get("html_url"),
    }


"""
example payload structure for reference:
{
  "action": "opened",
  "number": 42,
  "pull_request": {
    "number": 42,
    "title": "Add user authentication",
    "html_url": "https://github.com/akshattalwar001/PRysm/pull/42",
    "state": "open",
    "body": "This PR adds JWT based login and signup endpoints.",
    "user": {
      "login": "akshat",
      "id": 8291823,
      "avatar_url": "https://avatars.githubusercontent.com/u/8291823"
    },
    "base": {
      "ref": "main",
      "sha": "def456abc123",
      "repo": {
        "full_name": "akshattalwar001/PRysm"
      }
    },
    "head": {
      "ref": "feature/auth",
      "sha": "abc123def456",
      "repo": {
        "full_name": "akshattalwar001/PRysm"
      }
    },
    "additions": 143,
    "deletions": 12,
    "changed_files": 6,
    "commits": 3,
    "draft": false
  },
  "repository": {
    "id": 123456789,
    "full_name": "akshattalwar001/PRysm",
    "private": false,
    "owner": {
      "login": "akshattalwar001"
    },
    "html_url": "https://github.com/akshattalwar001/PRysm",
    "default_branch": "main"
  },
  "sender": {
    "login": "akshattalwar001",
    "id": 8291823
  }
}
"""