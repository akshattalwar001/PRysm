import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.1-8b-instant"

def _extract_json(text: str) -> dict:
    """
    Llama sometimes wraps JSON in ```json ... ``` even when told not to.
    this function tries to extract the JSON object from the raw text.
    """
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

"""input prompt example :"You are a senior software engineer reviewing 
                           a pull request.\n\nPR Title: Add auth..." 
                           
output of call_llm(prompt):
{
    "summary": {
        "verdict": "request_changes",
        "overall_score": 6,
        "tldr": "Auth logic has a SQL injection risk on line 42."
    },
    "inline_comments": [
        {
            "file": "src/auth.py",
            "line": 42,
            "severity": "security",
            "comment": "User input is directly interpolated into the SQL query."
        }
    ],
    "general_comments": ["Add unit tests for the login function."]
}

"""
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


"""
input example : prompt_chunks = [
    {
        "prompt": "You are a senior engineer... \n### File: src/auth.py\n...",
        "files_covered": ["src/auth.py"]
    },
    {
        "prompt": "You are a senior engineer... \n### File: src/routes.py\n...",
        "files_covered": ["src/routes.py"]
    }
]

output of review_chunks(prompt_chunks):
{
    "summary": {
        "verdict": "request_changes",
        "overall_score": 5,
        "tldr": "Reviewed 2 chunk(s). See inline comments for details."
    },
    "inline_comments": [
        # comments from chunk 1 AND chunk 2 combined
        {"file": "src/auth.py", "line": 42, "severity": "security", "comment": "..."},
        {"file": "src/routes.py", "line": 15, "severity": "bug", "comment": "..."}
    ],
    "general_comments": [
        "Add unit tests.",
        "Consider rate limiting the login endpoint."
    ]
}

"""
def review_chunks(prompt_chunks: list[dict]) -> dict:

    if not prompt_chunks:
        return {
            "summary": {"verdict": "comment", "overall_score": 0, "tldr": "No reviewable files found."},
            "inline_comments": [],
            "general_comments": [],
        }

    all_inline = []
    all_general = []
    all_scores = []
    all_verdicts = []

    for chunk in prompt_chunks:
        print(f"[LLM] Reviewing files: {chunk['files_covered']}")
        result = call_llm(chunk["prompt"])

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

    return {
        "summary": {
            "verdict": final_verdict,
            "overall_score": final_score,
            "tldr": f"Reviewed {len(prompt_chunks)} chunk(s). See inline comments for details.",
        },
        "inline_comments": all_inline,
        "general_comments": list(set(all_general)),  # remove duplicate general comments
    }