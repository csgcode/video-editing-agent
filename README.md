# video-editing-agent

Prompt-guided video-to-ad editing POC.

## Requirements
- Python 3.12
- `uv`
- `ffmpeg`, `ffprobe`
- Docker (optional, for async Redis/Celery)

## Setup
```bash
make setup
make migrate
```

## Run (default, eager tasks)
```bash
make run
```
Then open `http://127.0.0.1:8000/app`.

## Gemini provider (phase 1)
In `.env`:
```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=<your_api_key>
GEMINI_MODEL=gemini-2.0-flash
GEMINI_TIMEOUT_SECONDS=20
```
If `AI_PROVIDER=gemini` and key is missing/fails, the app falls back to local copy generation.

## Run (async with Redis + Celery)
Terminal 1:
```bash
make redis-up
make runserver-async
```

Terminal 2:
```bash
make worker-async
```

## Quality checks
```bash
make test
make lint
```

## API Docs
- `http://127.0.0.1:8000/api/docs/`
- `http://127.0.0.1:8000/api/schema/`
