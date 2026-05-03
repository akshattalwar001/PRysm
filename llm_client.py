import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from hindsight_client import Hindsight
from config import GROQ_API_KEY, HINDSIGHT_API_URL, HINDSIGHT_API_KEY

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

hindsight = Hindsight(
    base_url=HINDSIGHT_API_URL,
    api_key=HINDSIGHT_API_KEY,
)

_executor = ThreadPoolExecutor(max_workers=2)

def _run_in_thread(fn, *args, **kwargs):
    """
    FastAPI runs an async event loop. Hindsight sync SDK calls block it.
    This runs them in a separate thread to avoid the conflict.
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))

def _create_bank(bank_id: str, repo: str):
    try:
        hindsight.create_bank(
            bank_id=bank_id,
            name=repo,
            background=f"PR review memory system for the repository {repo}. Stores past pull request reviews, recurring bugs, code patterns, and common issues found in this codebase.",
        )
        print(f"[Hindsight] Created memory bank for repo: {repo}")
    except Exception as e:
        print(f"[Hindsight] Bank already exists or creation skipped: {e}")


def _fetch(bank_id: str, query: str):
    return hindsight.recall(bank_id=bank_id, query=query)


def _store(bank_id: str, content: str):
    hindsight.retain(bank_id=bank_id, content=content)


async def create_bank_if_not_exists(repo: str) -> None:
    bank_id = repo.replace("/", "-")
    await _run_in_thread(_create_bank, bank_id, repo)


async def fetch_memories(repo: str, query: str) -> str:
    try:
        bank_id = repo.replace("/", "-")
        result = await _run_in_thread(_fetch, bank_id, query)

        if not result.results:
            return ""

        memory_lines = "\n".join(f"- {m.text}" for m in result.results)
        return f"\n\n### Past review memory for this repo:\n{memory_lines}\n"

    except Exception as e:
        print(f"[Hindsight] fetch_memories failed (non-fatal): {e}")
        return ""


async def store_memory(repo: str, pr_number: int, review_data: dict) -> None:
    try:
        bank_id = repo.replace("/", "-")
        tldr = review_data.get("summary", {}).get("tldr", "")
        score = review_data.get("summary", {}).get("overall_score", "?")
        verdict = review_data.get("summary", {}).get("verdict", "?")
        issues = [c["comment"] for c in review_data.get("inline_comments", [])[:3]]

        memory_text = (
            f"PR #{pr_number}: verdict={verdict}, score={score}/10. "
            f"Summary: {tldr}"
        )
        if issues:
            memory_text += " Key issues: " + " | ".join(issues)

        await _run_in_thread(_store, bank_id, memory_text)
        print(f"[Hindsight] Stored memory for PR #{pr_number} in bank: {bank_id}")

    except Exception as e:
        print(f"[Hindsight] store_memory failed (non-fatal): {e}")


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response:\n{text[:500]}")

def call_llm(prompt: str) -> dict:
    messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content

    try:
        return _extract_json(raw)
    except ValueError:
        print("[LLM] First response wasn't valid JSON. Retrying with correction prompt...")

        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": (
                "Your previous response was not valid JSON. "
                "Please respond again with ONLY a valid JSON object matching the schema. "
                "No explanation, no markdown fences."
            ),
        })

        retry_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
        )

        retry_raw = retry_response.choices[0].message.content
        return _extract_json(retry_raw)
    

async def review_chunks(prompt_chunks: list[dict], repo: str = "", pr_number: int = 0) -> dict:
    if not prompt_chunks:
        return {
            "summary": {"verdict": "comment", "overall_score": 0, "tldr": "No reviewable files found."},
            "inline_comments": [],
            "general_comments": [],
        }

    if repo:
        await create_bank_if_not_exists(repo)

    memory_context = await fetch_memories(repo, query=prompt_chunks[0]["prompt"][:300]) if repo else ""
    if memory_context:
        print(f"[Hindsight] Injected memory context into prompt")

    all_inline = []
    all_general = []
    all_scores = []
    all_verdicts = []

    for chunk in prompt_chunks:
        print(f"[LLM] Reviewing files: {chunk['files_covered']}")
        enriched_prompt = chunk["prompt"] + memory_context
        result = call_llm(enriched_prompt)

        all_inline.extend(result.get("inline_comments", []))
        all_general.extend(result.get("general_comments", []))

        summary = result.get("summary", {})
        all_scores.append(summary.get("overall_score", 5))
        all_verdicts.append(summary.get("verdict", "comment"))

    final_score = round(sum(all_scores) / len(all_scores))

    if "request_changes" in all_verdicts:
        final_verdict = "request_changes"
    elif "comment" in all_verdicts:
        final_verdict = "comment"
    else:
        final_verdict = "approve"

    final_result = {
        "summary": {
            "verdict": final_verdict,
            "overall_score": final_score,
            "tldr": f"Reviewed {len(prompt_chunks)} chunk(s). See inline comments for details.",
        },
        "inline_comments": all_inline,
        "general_comments": list(set(all_general)),
    }

    if repo and pr_number:
        await store_memory(repo, pr_number, final_result)

    return final_result