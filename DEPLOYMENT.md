# malloc() — FastAPI Deployment Guide 🚀

**malloc()** is now deployed directly using **FastAPI**! A single Uvicorn process serves both the interactive Web UI (Chat with Speech-to-Text and Vision, Memory Vault, and Job Tracker) and the complete REST API / OpenAPI docs.

---

## ⚡ Quick Start (Deploy in 1 Command)

```bash
# 1. Navigate to memora directory
cd memora

# 2. Run the FastAPI application server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser to view the application!
Interactive API Documentation is available at **`http://localhost:8000/docs`**.

---

## 🔑 Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `groq` | `"groq"` (free) or `"anthropic"` |
| `GROQ_API_KEY` | *(Required if groq)* | Get free key at [console.groq.com/keys](https://console.groq.com/keys) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq LLM model name |
| `ANTHROPIC_API_KEY` | *(Optional)* | Anthropic API key |
| `DATABASE_URL` | `sqlite:///./memora.db` | Database connection URL |
| `PORT` | `8000` | Web server port |

---

## 🌟 1. Render.com (1-Click Free Hosting)

1. Push your repository to GitHub.
2. Go to [dashboard.render.com](https://dashboard.render.com) -> **New +** -> **Blueprint**.
3. Select this repository. Render automatically reads `render.yaml`.
4. Enter your `GROQ_API_KEY` in the environment variable prompt.
5. Click **Apply**. Render will deploy your FastAPI service with a live HTTPS URL.

---

## 🌟 2. Railway / Koyeb / Fly.io

### Railway:
1. Connect your GitHub repository to [railway.app](https://railway.app).
2. Set `GROQ_API_KEY` in service variables.
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Fly.io:
```bash
fly launch
fly secrets set GROQ_API_KEY="your-api-key"
fly deploy
```

---

## 🌟 3. Docker Container Deployment

```bash
# Build the Docker image
docker build -t malloc-app .

# Run container with your API key
docker run -d -p 8000:8000 \
  -e GROQ_API_KEY="your-groq-key" \
  --name malloc malloc-app
```
Access the application at `http://localhost:8000`.

---

## 🌟 4. Instant Live Public HTTPS Tunnel

To share your local FastAPI deployment with anyone online in seconds:

```bash
# 1. Run FastAPI
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. In another terminal, open a free Cloudflare Tunnel
npx cloudflared tunnel --url http://localhost:8000
```
This gives you an instant, secure public `https://*.trycloudflare.com` URL.

---

## 🎯 Architecture Summary

- **`GET /`**: Serves the modern glassmorphic web application (Chat, Voice, Memory Vault, Job Tracker).
- **`POST /chat`**: AI Assistant turn with automatic background memory extraction.
- **`GET /memories/{user_id}`**: Retrieves active extracted user memories.
- **`POST /media/transcribe`**: Transcribes audio recordings using faster-whisper.
- **`POST /media/caption`**: Captions uploaded images using Salesforce BLIP.
- **`CRUD /jobs`**: Manages job application pipeline and follow-up deadlines.
- **`GET /docs`**: Interactive Swagger OpenAPI explorer.
