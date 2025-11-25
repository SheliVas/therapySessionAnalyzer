# Therapy Session Analyzer – Architecture & Plan

## Microservices Overview

All services are Python, each in its own Docker container, communicating only via RabbitMQ events.

- **upload_service** (FastAPI)
  - Endpoint: `POST /videos`
  - Accepts video file upload.
  - Stores raw video in MinIO (e.g., bucket `therapy-videos`).
  - Publishes RabbitMQ event `video.uploaded` with payload: video ID, MinIO path, metadata.

- **audio_extractor_service** (worker)
  - Subscribes to `video.uploaded`.
  - Downloads video from MinIO.
  - Extracts audio to MP3 (e.g., using `ffmpeg`/`moviepy`).
  - Uploads MP3 to MinIO (bucket `therapy-audio`).
  - Publishes `audio.extracted` with MP3 MinIO path.

- **transcription_service** (worker)
  - Subscribes to `audio.extracted`.
  - Downloads MP3 from MinIO.
  - Calls AssemblyAI with speaker diarization enabled.
  - Stores raw transcript JSON in MinIO (bucket `therapy-transcripts`).
  - Publishes `transcript.created` with transcript location/ID.

- **analysis_service** (worker)
  - Subscribes to `transcript.created`.
  - Fetches transcript JSON.
  - Calls chosen LLM to:
    - Identify which speaker is the therapist vs patient.
    - Tag each utterance with `topic` and `emotion`.
  - Uses Redis to cache LLM calls (keyed by deterministic hash of transcript chunk + prompt).
  - Computes additional analytics, e.g.:
    - Topic sentiment distribution over time.
    - Topics that make the patient feel good/bad.
    - Talk-time ratio therapist vs patient.
  - Persists structured results into SQLite.
  - Publishes `analysis.completed` with video/analysis IDs.

- **report_service** (FastAPI)
  - Endpoints:
    - `GET /videos` – list analyzed videos from SQLite.
    - `GET /videos/{video_id}` – full analysis for a given video.
  - Can also expose aggregated stats across sessions.

## Shared Infrastructure

- **RabbitMQ** – event bus for:
  - `video.uploaded`
  - `audio.extracted`
  - `transcript.created`
  - `analysis.completed`
- **MinIO** – object storage for:
  - Raw videos (bucket `therapy-videos`).
  - Extracted audio (bucket `therapy-audio`).
  - Transcripts (bucket `therapy-transcripts`).
- **Redis** – cache for LLM responses.
- **SQLite** – main DB for analysis results, shared between `analysis_service` and `report_service`.
- **Datadog** – centralized logging/metrics; services log to stdout with Datadog-compatible format.

## SQLite Schema (Draft)

Single database file, e.g. `/data/therapy_analysis.db`, mounted in `analysis_service` and `report_service`.

- **videos**
  - `id` (TEXT PRIMARY KEY, e.g., UUID)
  - `filename` (TEXT)
  - `uploaded_at` (TIMESTAMP)
  - `video_minio_path` (TEXT)
  - `audio_minio_path` (TEXT NULL)
  - `transcript_minio_path` (TEXT NULL)
  - `status` (TEXT: `uploaded` / `audio_extracted` / `transcribed` / `analyzed` / `failed`)

- **utterances**
  - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
  - `video_id` (TEXT REFERENCES `videos`(id))
  - `speaker_label` (TEXT, e.g., `speaker_0`)
  - `role` (TEXT: `therapist` / `patient` / `unknown`)
  - `start_time` (REAL seconds)
  - `end_time` (REAL seconds)
  - `text` (TEXT)
  - `topic` (TEXT)
  - `emotion` (TEXT)

- **video_metrics**
  - `video_id` (TEXT PRIMARY KEY REFERENCES `videos`(id))
  - `patient_positive_topics` (TEXT JSON)
  - `patient_negative_topics` (TEXT JSON)
  - `talk_time_therapist` (REAL)
  - `talk_time_patient` (REAL)
  - `extra_metrics` (TEXT JSON) – for additional analysis (e.g., emotion timeline, topic histograms).

## RabbitMQ Event Payloads (Draft)

- **`video.uploaded`**
  ```json
  {
    "video_id": "uuid",
    "filename": "session1.mp4",
    "minio_bucket": "therapy-videos",
    "minio_key": "videos/session1.mp4",
    "uploaded_at": "2025-11-25T12:34:56Z"
  }
  ```

- **`audio.extracted`**
  ```json
  {
    "video_id": "uuid",
    "audio_minio_bucket": "therapy-audio",
    "audio_minio_key": "audio/session1.mp3"
  }
  ```

- **`transcript.created`**
  ```json
  {
    "video_id": "uuid",
    "transcript_minio_bucket": "therapy-transcripts",
    "transcript_minio_key": "transcripts/session1.json"
  }
  ```

- **`analysis.completed`**
  ```json
  {
    "video_id": "uuid",
    "status": "analyzed"
  }
  ```

## Project Structure (Planned)

Under `therapySessionAnalyzer/`:

- `upload_service/`
  - `upload_service_api.py` (FastAPI app)
- `audio_extractor_service/`
  - `audio_extractor_worker.py`
- `transcription_service/`
  - `transcription_worker.py`
- `analysis_service/`
  - `analysis_worker.py`
  - `domain/` (transcript parsing, LLM client, metrics, etc.)
  - `db/` (SQLite models/repository)
- `report_service/`
  - `report_service_api.py` (FastAPI app)
  - `db/` (read-only repository into SQLite)
- `shared/`
  - `messaging.py` (event models)
  - `logging_config.py` (central logging setup)
- `docker-compose.yml`
- One `Dockerfile` per service.

## TDD Approach

1. Start with pure Python domain modules and tests (no FastAPI/Docker yet):
   - Transcript parsing (AssemblyAI JSON → utterances).
   - LLM client with Redis cache mocked.
   - Metrics computation (talk time, topic/emotion aggregation).
   - SQLite repository (using `:memory:` in tests).
2. Add message-handling units for RabbitMQ events with the broker mocked.
3. Add FastAPI endpoints for `upload_service` and `report_service` with HTTP tests.
4. Finally, wire everything together with Docker Compose, MinIO, RabbitMQ, Redis, SQLite volume, and Datadog.

## Extra Analysis Idea

In addition to topic/emotion tagging and talk-time ratios, include at least one extra analysis metric, e.g.:

- Emotion timeline for the patient (dominant emotion per time window).
- Topic frequency histogram for positive vs negative emotions.

These will be stored in `video_metrics.extra_metrics` as JSON.
