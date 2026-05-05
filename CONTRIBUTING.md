#   Contributing to PRysm

thanks for your interest in contributing. this document covers the basics.

---

## before you start

- check [open issues](https://github.com/akshattalwar001/PRysm/issues) to see if someone is already working on it
- for big changes, open an issue first to discuss the idea before writing code
- for small fixes (typos, bugs, docs) just open a PR directly

---

## setup

follow the local setup steps in the [README](README.md) (method 2).

make sure your `.env` is configured and the server starts with:

```bash
uvicorn main:app --reload --port 8000
```

---

## making changes

**Step 1** fork the repo and create a branch

```bash
git checkout -b fix/your-branch-name
```

branch naming:
- `fix/` for bug fixes
- `feat/` for new features
- `docs/` for documentation

**Step 2** make your changes

keep each PR focused on one thing. avoid mixing unrelated changes.

**Step 3** test your changes

use `test_payload.py` to simulate a webhook event locally before pushing.

**Step 4** open a PR

- write a clear title and a short description of what changed and why
- link the related issue if there is one

---

## code style

- follow the existing patterns in each file
- keep functions small and focused
- add comments where the logic is not obvious
- do not commit `.env` files or API keys

---

## what to work on

good areas to contribute:

- improving the prompt in `context_builder.py`
- adding support for more file types or skipping patterns
- better error handling in `llm_client.py`
- writing actual tests
- improving the diff position mapping in `comment_poster.py`

---

## questions

open a GitHub issue and tag it `question`.
