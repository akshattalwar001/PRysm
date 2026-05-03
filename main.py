import json
from fastapi import FastAPI, Request, HTTPException
from webhook_handler import verify_signature, parse_pr_event
from github_client import get_pr_diff, get_pr_metadata, post_review
from context_builder import build_prompt
from llm_client import review_chunks
from comment_poster import attach_diff_positions

app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "pr-review-agent is alive"}


@app.post("/webhook")
async def handle_webhook(request: Request):
    payload_bytes = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    if not verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"event '{event_type}' not handled"}

    payload = json.loads(payload_bytes)
    pr_data = parse_pr_event(payload)

    if pr_data is None:
        return {"status": "ignored", "reason": f"action '{payload.get('action')}' not handled"}

    repo = pr_data["repo_full_name"]
    pr_number = pr_data["pr_number"]

    print(f"\n[WEBHOOK] PR #{pr_number} {pr_data['action']} on {repo}")

    try:
        print(f"[GITHUB] Fetching diff for PR #{pr_number}...")
        raw_diff = get_pr_diff(repo, pr_number)
        metadata = get_pr_metadata(repo, pr_number)

        print(f"[GITHUB] {len(metadata['changed_files'])} files changed")

        prompt_chunks = build_prompt(raw_diff, metadata)

        if not prompt_chunks:
            print("[CONTEXT] No reviewable files after filtering. Skipping.")
            return {"status": "skipped", "reason": "no reviewable files"}

        print(f"[CONTEXT] Split into {len(prompt_chunks)} chunk(s)")
        
        review_data = await review_chunks(prompt_chunks, repo=repo, pr_number=pr_number)
        
        review_data = attach_diff_positions(review_data, raw_diff)
        post_review(repo, pr_number, review_data)

        print(f"[DONE] Review posted on PR #{pr_number} \n")
        return {"status": "reviewed", "pr": pr_number}

    except Exception as e:
        print(f"[ERROR] PR #{pr_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))