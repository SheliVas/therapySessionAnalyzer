# Therapy Session Analyzer

A set of event-driven microservices for analyzing therapy session videos. The system uploads videos, extracts audio, transcribes speech, and performs AI-based analysis to provide insights and recommendations.

## Architecture Overview

The system consists of the following microservices and infrastructure components:

### Services
- **upload_service** (Port 8000): FastAPI service that accepts video uploads, stores them in MinIO (`therapy-videos`), and publishes a `video.uploaded` event.
- **audio_extractor_service**: Worker that consumes `video.uploaded`, extracts audio using FFmpeg, stores it in MinIO (`therapy-audio`), and publishes `audio.extracted`.
- **transcription_service**: Worker that consumes `audio.extracted`, sends audio to AssemblyAI for transcription (with diarization), stores the transcript in MinIO (`therapy-transcripts`), and publishes `transcript.created`.
- **analysis_service**: Worker that consumes `transcript.created`, uses Gemini LLM (via OpenAI-compatible API) to analyze the session. It performs speaker role mapping, utterance tagging (topic/emotion), and generates therapist recommendations as some extra feature. Results are cached in Redis and stored in MongoDB. Publishes `analysis.completed`.
- **report_service** (Port 8001): FastAPI service that provides read-only access to analysis reports stored in MongoDB.

### Infrastructure
- **RabbitMQ**: Message broker for event-driven communication between services.
- **MongoDB**: Database for storing video metadata and analysis results.
- **Redis**: Cache for LLM responses to reduce costs and latency.
- **MinIO**: S3-compatible object storage for video, audio, and transcript files.

## Prerequisites

- Docker and Docker Compose
- API Keys for:
  - **AssemblyAI** (for transcription)
  - **Google Gemini** (or another OpenAI-compatible LLM provider)

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   - `ASSEMBLYAI_API_KEY`: Your AssemblyAI API key.
   - `GEMINI_API_KEY`: Your Google Gemini API key.

   **⚠️ WARNING**: Never commit your real API keys to version control. Ensure `.env` is in your `.gitignore`.

## How to Run

1. Start the entire stack:
   ```bash
   docker compose up -d --build
   ```

2. Access the services:
   - **Upload Service API**: http://localhost:8000/docs
   - **Report Service API**: http://localhost:8001/docs
   - **MinIO Console**: http://localhost:9001 (Default: `minioadmin` / `minioadmin`)
   - **RabbitMQ Management**: http://localhost:15672 (Default: `guest` / `guest`)

## End-to-End Smoke Test

1. **Upload a Video**:
   ```bash
   curl -F "file=@sample.mp4" http://localhost:8000/videos
   ```
   *Note the `video_id` returned in the response (e.g., `video-123`).*

2. **Check Processing Status** (Optional):
   You can inspect MongoDB to see the document status update as it moves through the pipeline:
   ```bash
   docker compose exec mongo mongosh therapy_analysis --eval 'db.videos.find().pretty()'
   ```

3. **Fetch Analysis Results**:
   List all analyzed videos:
   ```bash
   curl http://localhost:8001/videos
   ```
   
   Get details for a specific video:
   ```bash
   curl http://localhost:8001/videos/<video_id>
   ```

   **Expected Output**: A JSON object containing:
   - `analysis.tagging.utterances`: List of utterances with speaker role, topic, emotion, and text.
   - `analysis.recommendations.therapist_recommendations`: AI-generated recommendations for the therapist.

## Logging & Monitoring

- **Logs**: Currently, all services log to `stdout`. You can view them using:
  ```bash
  docker compose logs -f
  ```
  
- **Datadog (Optional)**: The infrastructure supports Datadog agent integration. To enable it:
  1. Add your `DD_API_KEY` and `DD_SITE` to the `.env` file.
  2. Uncomment the Datadog agent service in `docker-compose.yml` (if present) or ensure the agent container is running.
  *Note: Datadog integration is optional and currently not active by default.*

## Troubleshooting

- **Analysis Timeout**: If the `analysis_service` times out, try increasing `LLM_TIMEOUT` in your `.env` file (default is 60s).
- **Missing Keys**: Ensure `ASSEMBLYAI_API_KEY` and `GEMINI_API_KEY` are correctly set in `.env`.
- **Stuck Pipeline**: If a step fails (e.g., transcription error), the process stops. Check the logs for the specific service:
  ```bash
  docker compose logs -f transcription_service
  ```
- **Re-running**: If analysis fails due to a transient error (like an LLM timeout), you may need to re-upload the video to trigger the pipeline again, or manually republish the event if you have access to RabbitMQ management.

## Storage Buckets

The system automatically creates and uses the following MinIO buckets:
- `therapy-videos`: Raw uploaded video files.
- `therapy-audio`: Extracted audio files.
- `therapy-transcripts`: JSON transcript files from AssemblyAI.
