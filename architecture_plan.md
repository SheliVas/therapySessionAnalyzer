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
  - Persists structured results into MongoDB (database `therapy_analysis`).
  - Publishes `analysis.completed` with video/analysis IDs.

- **report_service** (FastAPI)
  - Endpoints:
    - `GET /videos` – list analyzed videos from MongoDB.
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
- **MongoDB** – main DB for analysis results (database `therapy_analysis`), shared between `analysis_service` and `report_service`.
- **Datadog** – centralized logging/metrics; services log to stdout with Datadog-compatible format.

## MongoDB Collections (Draft)

Database: `therapy_analysis`

- **Collection: `videos`**

    {
      "_id": "uuid",  // video_id
      "filename": "session1.mp4",
      "uploaded_at": "2025-11-25T12:34:56Z",
      "video_minio_path": "therapy-videos/videos/session1.mp4",
      "audio_minio_path": "therapy-audio/audio/session1.mp3",
      "transcript_minio_path": "therapy-transcripts/transcripts/session1.json",
      "status": "analyzed"  // uploaded / audio_extracted / transcribed / analyzed / failed
    }

- **Collection: `analysis_results`**

    {
      "_id": "ObjectId",
      "video_id": "uuid",
      "word_count": 1234,
      "utterances": [
        {
          "speaker_label": "speaker_0",
          "role": "therapist",
          "start_time": 0.0,
          "end_time": 5.2,
          "text": "How are you feeling today?",
          "topic": "greeting",
          "emotion": "neutral"
        },
        {
          "speaker_label": "speaker_1",
          "role": "patient",
          "start_time": 5.5,
          "end_time": 12.3,
          "text": "I've been feeling anxious lately.",
          "topic": "anxiety",
          "emotion": "anxious"
        }
      ],
      "metrics": {
        "talk_time_therapist": 120.5,
        "talk_time_patient": 245.3,
        "patient_positive_topics": ["progress", "coping_strategies"],
        "patient_negative_topics": ["anxiety", "work_stress"]
      },
      "extra": {
        "emotion_timeline": [
          {"time_window": "0-60", "dominant_emotion": "neutral"},
          {"time_window": "60-120", "dominant_emotion": "anxious"}
        ],
        "topic_histogram": {
          "anxiety": {"positive": 2, "negative": 5},
          "work": {"positive": 1, "negative": 3}
        }
      },
      "created_at": "2025-11-25T12:45:00Z"
    }

**Indexes**

- `videos`: index on `status`, index on `_id` (default)
- `analysis_results`:
  - index on `video_id` (unique, one analysis per video)
  - optional compound index on `video_id` + `created_at` if you ever store multiple versions

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
  - `db/` (MongoDB models/repository for `analysis_results` and videos view)
- `report_service/`
  - `report_service_api.py` (FastAPI app)
  - `db/` (read-only repository into MongoDB)
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
  - MongoDB repository (using `mongomock` or in-memory MongoDB in tests).
2. Add message-handling units for RabbitMQ events with the broker mocked.
3. Add FastAPI endpoints for `upload_service` and `report_service` with HTTP tests.
4. Finally, wire everything together with Docker Compose, MinIO, RabbitMQ, Redis, MongoDB, and Datadog.

## Extra Analysis Idea

In addition to topic/emotion tagging and talk-time ratios, include at least one extra analysis metric, e.g.:

- Emotion timeline for the patient (dominant emotion per time window).
- Topic frequency histogram for positive vs negative emotions.

These will be stored in `video_metrics.extra_metrics` as JSON.
