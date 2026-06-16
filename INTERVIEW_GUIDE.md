# Therapy Session Analyzer — Interview Ownership Guide

> Read this top-to-bottom once. Then reread sections 1, 6, and 9 right before you walk in.
> You built this. This doc just hands your own knowledge back to you in order.

---

## 0. The 30-second pitch (memorize this rhythm, not the words)

> "It's an **event-driven microservices pipeline** that turns a raw therapy
> session **video** into **structured, AI-generated insights**. You upload a
> video; it flows through five independent services connected by RabbitMQ —
> extract audio, transcribe with speaker diarization, run LLM analysis, and
> expose the results through a read API. Each stage is its own service so it
> can fail, scale, and be tested in isolation. I built it test-first — **290
> passing tests** — with the domain logic fully decoupled from infrastructure
> via Python Protocols and dependency injection."

That single paragraph hits: *what it does, the architecture, the tech, and a quality signal.* Everything below is you being able to defend every clause of it.

---

## 1. THE COMPLETE FLOW (the spine — know this cold)

One video upload triggers a chain of **4 RabbitMQ events** across **5 services**. Trace it like a story:

```
   CLIENT
     │  POST /videos  (multipart file)
     ▼
┌─────────────────┐
│ upload_service  │  FastAPI, port 8000
│                 │  • saves video → MinIO bucket "therapy-videos"
│                 │  • writes metadata row → Mongo (status="uploaded")
│                 │  • publishes ───────────────┐
└─────────────────┘                             │  event: video.uploaded
                                                 ▼
┌──────────────────────────┐
│ audio_extractor_service  │  worker (no HTTP)
│                          │  • downloads video from MinIO
│                          │  • ffmpeg → MP3  (subprocess, stdin→stdout pipes)
│                          │  • uploads MP3 → "therapy-audio"
│                          │  • Mongo status="audio_extracted"
│                          │  • publishes ──────────┐  event: audio.extracted
└──────────────────────────┘                        ▼
┌──────────────────────────┐
│ transcription_service    │  worker
│                          │  • downloads MP3
│                          │  • AssemblyAI, speaker_labels=True (diarization)
│                          │  • formats as "Speaker A: ...\nSpeaker B: ..."
│                          │  • stores transcript → "therapy-transcripts"
│                          │  • Mongo status="transcribed"
│                          │  • publishes ──────────┐  event: transcript.created
└──────────────────────────┘                        ▼
┌──────────────────────────┐
│ analysis_service         │  worker — THE BRAIN
│                          │  3 LLM steps (Gemini), each Redis-cached:
│                          │   1. map speakers → therapist/patient roles
│                          │   2. tag each utterance → topic + emotion
│                          │   3. generate therapist recommendations
│                          │  • saves AnalysisResult → Mongo
│                          │  • Mongo status="analyzed"
│                          │  • publishes ──────────┐  event: analysis.completed
└──────────────────────────┘                        ▼
                                              (terminal event)
┌─────────────────┐
│ report_service  │  FastAPI, port 8001 — READ-ONLY
│                 │  GET /videos          → list
│                 │  GET /videos/{id}     → full analysis
└─────────────────┘
     ▲
   CLIENT polls for results
```

**The one-liner per service** (be able to say these instantly):
| Service | Type | Job | In → Out |
|---|---|---|---|
| upload_service | FastAPI :8000 | accept upload, store, kick off pipeline | HTTP → `video.uploaded` |
| audio_extractor | worker | video → MP3 | `video.uploaded` → `audio.extracted` |
| transcription | worker | MP3 → diarized transcript | `audio.extracted` → `transcript.created` |
| analysis | worker | transcript → insights (LLM) | `transcript.created` → `analysis.completed` |
| report_service | FastAPI :8001 | serve results | HTTP read from Mongo |

**Status field is the thread that ties it together:** every service updates the
same Mongo `videos` document's `status` (`uploaded → audio_extracted →
transcribed → analyzed`). That's how you can see where any video is in the pipeline.

---

## 2. WHAT WAS THE CHALLENGE (frame it as problems, not features)

When they ask "what was the challenge," don't list features. Name the *hard problems* and how the design answers them:

1. **Long, multi-stage processing that can't be one request.** Transcription
   + 3 LLM calls take far too long for a synchronous HTTP call. → **Solution:**
   decompose into async services connected by a message queue. Upload returns
   instantly with a `video_id`; the rest happens in the background.

2. **Each stage has different failure modes and resource needs.** ffmpeg is
   CPU-bound; transcription and LLM calls are slow + flaky external APIs. →
   **Solution:** isolate each into its own service/container so one slow or
   failing stage doesn't block the others, and each can scale independently.

3. **LLMs are non-deterministic, slow, and cost money.** → **Solution:**
   `temperature=0` for determinism, **strict output validators** that reject
   malformed JSON, and **Redis caching** keyed by a hash of the input so
   re-processing the same transcript is free and instant.

4. **Trusting LLM output.** A model can return the wrong shape or hallucinate a
   topic that was never in the session. → **Solution:** validators that enforce
   exact schema *and* check semantic constraints (e.g. recommendations may only
   reference topics/emotions actually observed in the transcript).

---

## 3. INTERFACES (internal & external — they explicitly ask this)

### External interfaces (things outside the system talk to)
- **HTTP / REST (FastAPI):**
  - `POST /videos` (upload_service) — multipart file in, `{video_id, filename}` out, `201`.
  - `GET /videos`, `GET /videos/{id}` (report_service) — JSON analysis out; `404` if missing.
  - `GET /health` on both — for container/orchestration health checks.
- **AssemblyAI** — external transcription API (speaker diarization).
- **Gemini** (`gemini-2.5-flash`) — external LLM, called over plain HTTPS with `httpx`.

### Internal interfaces (services talk to each other)
- **RabbitMQ events** are the *only* way services talk to each other. No service
  calls another directly. The 4 events ARE the internal API:
  - `video.uploaded` → `{video_id, filename, bucket, key, uploaded_at}`
  - `audio.extracted` → `{video_id, bucket, key}`
  - `transcript.created` → `{video_id, bucket, key}`
  - `analysis.completed` → `{video_id, word_count, analysis}`
- Events are **Pydantic models** serialized to JSON; queues are **durable** and
  messages are **persistent** (`delivery_mode=2`) so they survive a broker restart.

### Shared backing services (data interfaces)
- **MinIO** (S3-compatible) — large binary blobs: video, audio, transcript files.
- **MongoDB** — `videos` (metadata + status) and analysis results. Shared between
  analysis (writes) and report (reads).
- **Redis** — LLM response cache (TTL'd).

### The "internal contract" you're proud of — Protocols
The domain code never imports MinIO/Mongo/pika directly. It depends on
**`typing.Protocol`** interfaces in `src/shared/protocols.py` (`StorageClient`,
`VideosRepository`) and per-service ABCs (`AnalysisBackend`, `RedisCache`, etc.).
Real infra implements these; tests pass in fakes. **This is the single most
important design point in the whole project — lead with it.**

---

## 4. METHODS / TECH STACK

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | — |
| Web | FastAPI + Uvicorn | async, auto OpenAPI docs, Pydantic-native |
| Validation/models | Pydantic | event schemas + request/response models |
| Messaging | RabbitMQ via `pika` | durable queues, decouples services |
| Object storage | MinIO (`minio`) | S3-compatible, runs locally in Docker |
| Database | MongoDB (`pymongo`) | flexible schema for nested analysis JSON |
| Cache | Redis (`redis`) | cache slow/expensive LLM calls |
| Transcription | AssemblyAI SDK | managed diarization |
| LLM | Google Gemini via `httpx` | structured JSON output |
| Audio | FFmpeg (subprocess) | industry standard, streamed via pipes |
| Tests | pytest, mongomock, pytest-mock | **290 tests**, fakes via Protocols |
| Packaging | Docker + docker-compose | one Dockerfile per service |

**Method = Test-Driven Development.** The architecture plan literally lays out the
TDD order: pure domain modules + tests first, then message handlers with a mocked
broker, then FastAPI endpoints, then wire it all up with Docker last.

---

## 5. KEY FILES (so you can navigate live if asked to open something)

```
src/
  shared/
    protocols.py        ← StorageClient, VideosRepository (THE contracts)
    rabbitmq.py         ← base Publisher/Consumer (QoS=1, durable, nack-on-error)
    minio_storage.py    ← real StorageClient impl
  upload_service/
    domain.py           ← handle_video_upload() — pure logic, fully injected
    app.py              ← FastAPI; create_app(deps) vs create_production_app()
  audio_extractor_service/
    ffmpeg_converter.py ← subprocess pipe in→out
    worker.py / domain.py
  transcription_service/
    backend.py          ← AssemblyAI, speaker_labels=True
  analysis_service/
    llm_backend.py      ← orchestrates the 3 LLM steps  ← THE BRAIN
    speaker_role_mapper.py / recommendations.py
    cached_operation.py ← generic cache-or-compute helper
    cache_keys.py       ← sha256(input+prompt_id) cache keys
    llm_output_validators.py ← strict schema + semantic checks
    llm_client.py       ← Gemini over httpx, retry on 429
    run_worker.py       ← composition root (builds & injects everything)
  report_service/
    app.py              ← read-only GET endpoints
```

**Pattern to point at:** `app.py` files have two functions — `create_app(deps...)`
takes injected dependencies (used by tests), and `create_production_app()` builds
the real MinIO/Mongo/Rabbit clients and passes them in. Same for `run_worker.py`.
That split between "wiring" and "logic" is what makes it all testable.

---

## 6. JUNCTIONS & IMPORTANT DECISIONS (the gold — interviewers dig here)

For each: **what you decided, the alternative, and the trade-off.** This is what separates "I wrote code" from "I own this."

1. **Event-driven microservices over a monolith.**
   - *Why:* stages have wildly different latency/resources; async decoupling;
     independent scaling and failure isolation.
   - *Trade-off:* more operational complexity (a broker, eventual consistency,
     harder end-to-end debugging) — justified by the long-running, staged workload.

2. **Dependency Injection via Protocols (structural typing).**
   - *Why:* domain logic depends on interfaces, not MinIO/Mongo/pika. Swap real
     infra for fakes in tests → fast, no Docker needed for unit tests.
   - *Alternative:* import clients directly → untestable without live infra.

3. **Redis cache keyed by `sha256(prompt_id + input)`.** (`cache_keys.py`)
   - *Why:* LLM calls are slow + cost money; same transcript shouldn't be
     re-analyzed. Including `prompt_id` means **changing the prompt busts the cache**
     automatically — old results won't be served for a new prompt version.
   - The `execute_cached_operation` helper is generic: get → on miss compute →
     validate → store. Used by all 3 LLM steps. (DRY.)

4. **Strict LLM output validation, including semantic checks.** (`llm_output_validators.py`)
   - Not just "is it JSON" — recommendations can only reference topics/emotions
     **actually observed** in the session; exactly one therapist + one patient;
     confidence ∈ [0,1]. Treats the LLM as an untrusted boundary.

5. **`temperature=0` + `responseMimeType: application/json`.**
   - Deterministic, parseable output → makes caching meaningful and validation reliable.

6. **At-least-once delivery, `prefetch_count=1`, durable queues, persistent msgs.**
   - QoS=1 → a worker only takes one message at a time (fair dispatch, no hoarding).
   - On exception the message is **nack'd with `requeue=False`** → it won't poison-loop
     forever; it's dropped (a dead-letter queue would be the next improvement).
   - Durable + persistent → survives broker restart.

7. **Three separate LLM calls instead of one mega-prompt.**
   - Role-mapping, tagging, and recommendations are distinct tasks with distinct
     output schemas; smaller focused prompts validate better and cache independently.
   - *Trade-off:* more round-trips (mitigated by caching).

8. **`on_progress` callback in the analysis backend.**
   - Partial results are saved to Mongo after role-mapping and after tagging, so a
     failure in step 3 doesn't lose steps 1–2, and a reader can see progress.

9. **Retry with exponential backoff only on HTTP 429** (rate limit) in the LLM client.
   - Retries the *transient* failure; other HTTP errors fail fast.

10. **MinIO for blobs, Mongo for metadata.** Don't put big video bytes in the DB;
    DB holds paths/pointers + status. Standard, clean separation.

---

## 7. DEMO SCRIPT (if they want a demo — keep it tight)

> Note: a live demo needs API keys (AssemblyAI + Gemini). If you can't run live,
> walk the code + the test suite instead — that's a perfectly strong demo.

**Live path:**
```bash
docker compose up -d --build
# upload
curl -F "file=@sample.mp4" http://localhost:8000/videos      # → {video_id}
# watch status advance
docker compose exec mongo mongosh therapy_analysis \
  --eval 'db.videos.find().pretty()'
# fetch result
curl http://localhost:8001/videos/<video_id>
# show the queues moving
open http://localhost:15672   # RabbitMQ mgmt (guest/guest)
```

**Safer "demo" if no keys / no time:**
```bash
python -m pytest -q          # 290 passed — show green
```
Then open `llm_backend.py` and narrate the 3-step flow, and `protocols.py` to show
the DI seam. **A clean test run IS a demo** — it proves the behavior without flaky external APIs.

---

## 8. WHAT YOU LEARNED (have 3 honest ones ready)

Pick the ones that feel true to you:
- **Treat the LLM as an untrusted external boundary.** Strict schema + semantic
  validation + determinism matters more than prompt cleverness.
- **Protocols + DI make a distributed system testable** without spinning up infra —
  290 fast tests came from that one decision.
- **Caching keyed on content hash + prompt version** is a clean way to make
  expensive, non-deterministic calls cheap and safe to evolve.
- **Honest gap / next step:** there's no dead-letter queue or automatic retry of a
  failed pipeline yet — a failed stage currently requires re-uploading. That's the
  first thing I'd harden for production. *(Naming a real limitation builds trust.)*

---

## 9. LIKELY QUESTIONS — fast answers

- **"What happens if the analysis service crashes mid-message?"** Message was
  taken with QoS=1 and only ack'd on success; on crash before ack RabbitMQ
  redelivers it. On a handled exception we nack without requeue so it doesn't loop.
- **"How do you avoid double-charging the LLM on a retry?"** Redis cache keyed on
  input hash — a redelivery hits the cache.
- **"How do you know which speaker is the therapist?"** First LLM step asks the
  model to map speaker labels → roles with confidence + reasoning, validated to be
  exactly one therapist + one patient.
- **"Why RabbitMQ and not just call the next service?"** Decoupling, buffering of
  slow stages, retries/durability, independent scaling. Direct calls would couple
  availability and block on the slowest stage.
- **"Why MongoDB?"** Analysis output is deeply nested, evolving JSON (utterances,
  metrics, recommendations) — a document store fits without rigid migrations.
- **"How would you scale the slow part?"** Run N analysis_service replicas all
  consuming the same queue; RabbitMQ load-balances. That's why QoS=1 matters.
- **"How is it tested without real infra?"** Fakes implementing the Protocols,
  `mongomock` for Mongo, mocked broker/HTTP. Domain logic is pure functions.
- **"What's the bottleneck?"** External APIs (transcription + LLM). Mitigated by
  caching and by the async pipeline so the user isn't blocked.

---

## 10. THREE-HOUR PLAN (tonight)

- **0:00–0:45** — Read this guide once, slowly. Then close it and **say the
  section-1 flow out loud** from memory. Peek only when stuck. Repeat once.
- **0:45–1:15** — Open the 5 files marked "THE BRAIN / contracts" (sec. 5) and
  read them with this guide beside you. You wrote them; it'll come back fast.
- **1:15–1:45** — Out loud, deliver the **30-sec pitch + the 5-service table +
  3 decisions from sec. 6**. Record yourself once on your phone; replay it.
- **1:45–2:15** — Run `python -m pytest -q`, confirm green, and skim one test file
  (e.g. `tests/upload_service/test_handle_video_upload.py`) to see the fakes pattern.
- **2:15–3:00** — Live-coding warmup (below). Then STOP and sleep. Sleep > cramming.

### Live-coding warmup (you're rusty, not unable)
Don't grind 20 problems. Do **3–4 deliberately**, out loud, in the Glider editor
style (talk through approach before coding):
1. One **string/array** problem (two-pointer or hash map) — e.g. two-sum, valid
   anagram, reverse words.
2. One **dict/counting** problem — e.g. group anagrams, top-K frequent.
3. One problem **close to your own domain**: "parse `Speaker A: text` lines into a
   list of dicts" — that's literally your `parse_transcript`. You *know* this shape.
Reps to lock in: enumerate over lines, `.split(':', 1)`, `dict`/`set`/`collections.Counter`,
list comprehensions. **Narrate while you code** — interviewers score communication
as much as correctness.

---

### Final note
You have green tests, a clean architecture, and a real system that does something
genuinely useful. The gap tonight is *familiarity*, and familiarity is exactly
what this doc + saying it out loud will fix. Do the plan, then sleep. You've got this.
