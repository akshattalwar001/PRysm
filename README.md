<div>
<img src="https://i.imgur.com/RWx6LxA.png" align="right" width="300"/>
<h3><b>PRysm</b></h3>
<p>An open source AI-powered GitHub PR review bot with memory.<br/>
It watches for pull requests, reads the diffand posts a detailed code review<br/>
directly on GitHub and gets smarter with every PR it reviews.</p>
</div>

## how it works

1. someone opens a PR on your repo
2. GitHub sends a webhook to PRysm
3. PRysm fetches the diff and checks its memory for past review patterns on this repo
4. the diff + memory context is sent to Llama via Groq
5. the AI reviews it and PRysm posts inline comments directly on the diff lines
6. the review is saved to memory so future PRs on this repo benefit from past context

---

## features

- **inline comments** :  feedback posted directly on the changed lines in the diff
- **per-repo memory** :  PRysm remembers past reviews for each repo separately and gets smarter over time
- **chunked review** :  handles large PRs by splitting the diff into chunks
- **smart file filtering** :  skips lock files, binaries, minified filesand build artifacts
- **auto retry** : if the LLM returns invalid JSON, PRysm automatically retries with a correction prompt

---
## memory

PRysm uses [Hindsight](https://hindsight.vectorize.io) to remember past PR reviews. Each repo gets its own isolated memory bank. Over time PRysm learns the patterns, recurring issuesand code style of your codebase and uses that context when reviewing new PRs.

<p align="left">
  <img src="https://i.imgur.com/vdWO6Vo.png" width="600"/>
</p>

> the graph above shows PRysm's memory bank for a test repository after 12 PRs   each node is a memory, connected by semantic, temporaland entity relationships.

---


## prerequisites

before you start, you need:

- a **GitHub personal access token**   needs `repo` scope. get it at github.com/settings/tokens
- a **Groq API key**   free at console.groq.com
- a **webhook secret**   just make up any random string, you'll use it in both your `.env` and GitHub webhook settings
- a **Hindsight API key**   free at ui.hindsight.vectorize.io (for memory)

---

## setup

### method 1   use the hosted version (easiest)
no setup needed. PRysm is already deployed and running, just point your GitHub webhook at it.

**step 1** go to your GitHub repo -> settings -> webhooks -> add webhook

**step 2** fill in the form

| field | value |
|---|---|
| payload url | https://prysm-pr-review-agent.onrender.com/webhook |
| content type | application/json |
| secret | make up any random string and save it |
| events | select "let me select individual events" -> check pull requests only |

---

### method 2   clone the repo

**step 1** clone and enter the project

```bash
git clone https://github.com/akshattalwar001/PRysm.git
cd PRysm
```

**step 2** create a virtual environment and install dependencies

```bash
python -m venv venv

# on mac/linux
source venv/bin/activate

# on windows
venv\Scripts\activate

pip install -r requirements.txt
```

**step 3** create your `.env` file

open `.env` and fill in your keys:

```
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
WEBHOOK_SECRET=your_webhook_secret
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your_hindsight_api_key
```

**step 4** start the server

```bash
uvicorn main:app --reload --port 8000
```

server will be running at `http://localhost:8000`

---

### method 3   docker

**step 1** pull the image

```bash
docker pull akshattalwar/prysm-pr-review-agent:latest
```

**step 2** create your `.env` file with your keys (same as method 2)

**step 3** run the container

```bash
docker run -p 8000:8000 --env-file .env akshattalwar/prysm-pr-review-agent:latest
```

or with docker compose:

```bash
docker compose up --build
```

> docker image also available at: https://hub.docker.com/repository/docker/akshattalwar/prysm-pr-review-agent

---

## setting up the github webhook

once your server is running (and exposed via ngrok or a real server)

**step 1** expose your local server (if running locally)

```bash
ngrok http 8000
```

copy the `https://` URL ngrok gives you.

**step 2** go to your GitHub repo -> settings -> webhooks -> add webhook

**step 3** fill in the form

| field | value |
|---|---|
| payload url | `https://your-url.ngrok.io/webhook` |
| content type | `application/json` |
| secret | same value as your `WEBHOOK_SECRET` in `.env` |
| events | select "let me select individual events" -> check **pull requests** only |

**step 4** click "add webhook"   PRysm will now automatically review every PR opened on that repo.

---
## project structure

```
PRysm/
├── main.py              
├── webhook_handler.py   
├── github_client.py     
├── context_builder.py   
├── llm_client.py        
├── comment_poster.py    
├── config.py            
├── requirements.txt     
├── .env           
├── Dockerfile           
└── docker-compose.yml   
```

---

## License

MIT see [LICENSE](LICENSE)
