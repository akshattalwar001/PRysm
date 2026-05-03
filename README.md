<div>
<img src="https://i.imgur.com/RWx6LxA.png" align="right" width="300"/>
<h3><b>PRysm</b></h3>
<p>An open source GitHub PR review bot.<br/>
It watches for pull requests, reads the diff, and posts a code review<br/>
directly on GitHub automatically.</p>
</div>

## how it works

1. someone opens a PR on your repo
2. GitHub sends a webhook to PRysm
3. PRysm fetches the diff and sends it to Llama via Groq
4. the AI reviews it and PRysm posts the feedback as a GitHub review

---

## prerequisites

before you start, you need three things:

- a **GitHub personal access token**  needs `repo` scope. get it at github.com/settings/tokens
- a **Groq API key**  free at console.groq.com
- a **webhook secret**  just make up any random string, you'll use it in both your `.env` and GitHub webhook settings

---

## setup (INSTALLATION)

### method 1  use the hosted version (easiest)
no setup needed. PRysm is already deployed and running, you just need to point your GitHub webhook at it.
**step 1**  go to your GitHub repo where you want PR reviews
``` settings → webhooks → add webhook ```
**step 2**  fill in the form
|field | value|
|---|---|
|payload url | https://prysm-pr-review-agent.onrender.com/webhook|
|content type| application/json |
|secret |make up any random string and save it somewhere| 
|events | select "let me select individual events" -> check pull requests only|

---

### method 2 : clone the repo

**step 1**  clone and enter the project

```bash
git clone https://github.com/akshattalwar001/PRysm.git
cd PRysm
```

**step 2**  create a virtual environment and install dependencies

```bash
python -m venv venv

# on mac/linux
source venv/bin/activate

# on windows
venv\Scripts\activate

pip install -r requirements.txt
```

**step 3**  create your `.env` file

open `.env` and fill in your keys:

```
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
WEBHOOK_SECRET=your_webhook_secret
```

**step 4**  start the server

```bash
uvicorn main:app --reload --port 8000
```

server will be running at `http://localhost:8000`

---

### method 3 : docker

**step 1**  pull the image

```bash
docker pull akshattalwar/prysm-pr-review-agent:latest
```

**step 2**  create your `.env` file with your keys

```
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
WEBHOOK_SECRET=your_webhook_secret
```

**step 3**  run the container

```bash
docker run -p 8000:8000 --env-file .env akshattalwar/prysm-pr-review-agent:latest
```

or if you cloned the repo and want to use docker compose:

```bash
docker compose up --build
```

server will be running at `http://localhost:8000`

<p align="left">
  <img src="https://i.imgur.com/UVF9WZG.png" width="400"/>
</p>

> docker image is also available at: https://hub.docker.com/repository/docker/akshattalwar/prysm-pr-review-agent

---

## setting up the github webhook

once your server is running (and exposed to the internet via ngrok or a real server)

**step 1** expose your local server (if running locally)

```bash
ngrok http 8000
```

copy the `https://` URL ngrok gives you.

**step 2**  go to your GitHub repo settings

```
your repo -> settings -> webhooks -> add webhook
```

**step 3** fill in the webhook form

| field | value |
|---|---|
| payload url | `https://your-url.ngrok.io/webhook` |
| content type | `application/json` |
| secret | same value as your `WEBHOOK_SECRET` in `.env` |
| events | select "let me select individual events" -> check **pull requests** only |

**step 4**  click "add webhook"

now if any PR opens up on that repo and PRysm will automatically review it.

---

## project structure

```
PRysm/
├── main.py              # entry point, handles incoming webhooks
├── webhook_handler.py   # verifies github signature, parses PR payload
├── github_client.py     # fetches diffs, posts reviews to github
├── context_builder.py   # builds the AI prompt from the diff
├── llm_client.py        # calls llama via groq, handles retries
├── comment_poster.py    # maps line numbers to diff positions
├── config.py            # loads env vars
├── requirements.txt     # dependencies
├── .env           # environmnet variables
├── Dockerfile           # docker setup
└── docker-compose.yml   # docker compose config
```

---

## License

MIT see [LICENSE](LICENSE)
