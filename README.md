# aigateway-py (Python)

Official Python SDK for [AIgateway](https://aigateway.sh) — one OpenAI-compatible API for every frontier and open-weight model, every modality.

> Distribution name on PyPI is **`aigateway-py`** (the bare `aigateway` name was unavailable). The import path is still `aigateway`.

For **chat, embeddings, images, STT, TTS, moderation** — just use the `openai` package with `base_url='https://api.aigateway.sh/v1'`. AIgateway is drop-in.

This SDK covers the aggregator-native surface OpenAI doesn't model:

- **Async jobs** — text-to-video, music, 3D with a typed `jobs.wait(id)` helper
- **Sub-accounts** — one scoped key per end customer with spend caps
- **Evals** — pick the winning model from a candidate set; alias as `eval:<run_id>`
- **Replays** — re-run any past request on a new model and diff the output
- **Signed file URLs** — share job results without handing out the gateway key
- **Webhook signature verification** — HMAC-SHA256 with `verify_webhook()`

## Install

```sh
pip install aigateway-py
```

You still `import aigateway` in code — the PyPI distribution name and the import name are intentionally different.

Requires Python 3.9+.

## Quickstart

```python
import os
from aigateway import AIgateway

client = AIgateway(api_key=os.environ["AIGATEWAY_API_KEY"])

# 1. Submit a video job with a webhook.
job = client.jobs.create_video(
    prompt="a sunset over mountains, cinematic",
    model="runwayml/gen-4",
    duration=5,
    webhook_url="https://yourapp.com/hooks/aigateway",
)

# 2. Or poll until it's done:
done = client.jobs.wait(job.id, timeout_seconds=600)
print(done.result_url)

# 3. Mint a shareable signed URL:
signed = client.files.signed_url(job.id, "video.mp4", expires_in=3600)
print(signed["url"])
```

## Async

```python
import asyncio
from aigateway import AsyncAIgateway

async def main():
    async with AsyncAIgateway(api_key="sk-aig-...") as client:
        job = await client.jobs.create_video(prompt="a cat")
        result = await client.jobs.wait(job.id)
        print(result.result_url)

asyncio.run(main())
```

## Webhook verification

```python
from aigateway import verify_webhook
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
SECRET = os.environ["AIGATEWAY_WEBHOOK_SECRET"]

@app.post("/hooks/aigateway")
async def hook(request: Request):
    raw = await request.body()
    sig = request.headers.get("x-gateway-signature", "")
    if not verify_webhook(SECRET, raw, sig):
        raise HTTPException(status_code=401)
    # ... handle the payload
```

Fetch your webhook secret with `client.webhook_secret.get()` or rotate it with `client.webhook_secret.rotate()`.

## Source, issues, examples

- Source — [github.com/aigateway-sh/sdk-python](https://github.com/aigateway-sh/sdk-python)
- Issues — [github.com/aigateway-sh/sdk-python/issues](https://github.com/aigateway-sh/sdk-python/issues)
- Working examples — [github.com/aigateway-sh/examples](https://github.com/aigateway-sh/examples)
- Support — **support@aigateway.sh** · [aigateway.sh/support](https://aigateway.sh/support)
- Follow — [github.com/aigateway-sh](https://github.com/aigateway-sh) · [linkedin.com/in/rakeshroushan1002](https://www.linkedin.com/in/rakeshroushan1002/) · [x.com/buildwithrakesh](https://x.com/buildwithrakesh)

## License

MIT © AIgateway
