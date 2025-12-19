"""Centralized prompt templates for analysis_service LLM calls.

Keep templates stable and reuse across modules.
"""

UTTERANCES_PLACEHOLDER = "{{UTTERANCES_JSON}}"
INPUT_JSON_PLACEHOLDER = "{{INPUT_JSON}}"

THERAPIST_RECOMMENDATIONS_SYSTEM_PROMPT = (
    "You generate next-session, technique-neutral therapist recommendations from tagged therapy-session utterances. "
    "Follow instructions exactly. Output MUST be valid JSON and MUST match the provided schema exactly with no extra keys. "
    "No diagnosis, no medication advice, no crisis instructions. Use ONLY evidence from provided utterances; do not invent facts. "
    "Prioritize patient content and therapist missed opportunities."
)

THERAPIST_RECOMMENDATIONS_USER_PROMPT_TEMPLATE = (
    "Input JSON:\n"
    "{{INPUT_JSON}}\n\n"
    "Requirements:\n"
    "- Produce 3–5 recommendations.\n"
    "- Output STRICT JSON only with this schema:\n"
    "{{\n"
    '  "therapist_recommendations": [\n'
    "    {{\n"
    '      "title": string,\n'
    '      "rationale": string (≤200 characters),\n'
    '      "priority": "high"|"medium"|"low",\n'
    '      "related_topics": [string] (ONLY from utterances[].topic),\n'
    '      "target_emotions": [string] (ONLY from utterances[].emotion)\n'
    "    }}\n"
    "  ]\n"
    "}}\n"
    "- Next-session focus: each recommendation must be a concrete action the therapist can take in the next session "
    "(question to ask, exercise to run, structure to add, skill to practice, or summary to reflect).\n"
    "- Technique-neutral wording (avoid naming modalities/acronyms).\n"
    "- Non-identifying: no names, locations, unique life details; don’t quote long passages.\n"
    "- Use only evidence from the utterances; no invented details.\n"
    "- Enforce sets:\n"
    "  - related_topics must be a subset of the input’s observed topics (utterances[].topic).\n"
    "  - target_emotions must be a subset of the input’s observed emotions (utterances[].emotion).\n"
    "- If evidence is thin, keep recommendations cautious and anchored to observed topics/emotions rather than guessing specifics.\n"
    '- Do not include any keys beyond "therapist_recommendations".\n\n'
    "Determinism notes (caller-side settings):\n"
    "- temperature=0\n"
    "- top_p=1\n"
    "- (optional if supported) seed=fixed_number\n"
    '- response_format={{"type":"json_object"}}'
)

SPEAKER_ROLE_MAPPING_PROMPT_TEMPLATE = (
    'RETURN ONLY JSON. NO MARKDOWN. NO PROSE. NO EXTRA KEYS.\n\n'
    'TASK\n'
    'Map diarized speaker labels to roles in a therapy session excerpt using ONLY the provided utterances (chronological).\n\n'
    'INPUT\n'
    'You will receive a JSON array of utterances. Each item contains:\n'
    '- speaker_label (string)\n'
    '- text (string)\n'
    '- optional index/time fields\n\n'
    'HARD CONSTRAINTS\n'
    '- The input contains EXACTLY 2 unique speaker_label values.\n'
    '- You MUST assign roles exactly once each: one label = "therapist" and the other = "patient". No duplicates, no unknowns.\n'
    '- The output speaker_roles object MUST contain EXACTLY the two speaker_label values that appear in the input (dynamic keys). No missing labels. No extra labels.\n'
    '- confidence values MUST be JSON numbers (not strings) within [0.0, 1.0].\n'
    '- overall_confidence MUST be a JSON number within [0.0, 1.0].\n'
    '- reason strings MUST be ≤120 characters, high-level behavioral cues only, non-sensitive, and MUST NOT quote the transcript verbatim.\n'
    '- If any constraint cannot be satisfied, still output JSON with best-effort mapping and set overall_confidence ≤ 0.40.\n\n'
    'DEFINITIONS\n'
    '- Therapist = the dominant clinical facilitator overall (guides, reflects, structures), even if the patient occasionally asks questions.\n'
    '- Patient = primarily discloses personal experiences/feelings and responds to facilitation.\n\n'
    'DETERMINISTIC DECISION RULE\n'
    'Across the full excerpt, decide which label is more therapist-like using multiple cues (not a single keyword):\n'
    'Therapist evidence (higher weight):\n'
    '- session structure: check-in, agenda, goals, next steps, summarizing progress, time/plan management\n'
    '- reflective listening: summaries, reframes, validation, gentle challenges\n'
    '- facilitation questions that guide exploration\n'
    '- coping strategies or psychoeducation\n'
    'Patient evidence:\n'
    '- personal disclosures: emotions, experiences, symptoms, relationships, day-to-day events\n'
    '- narrative responses to questions, uncertainty/vulnerability\n'
    '- requests for help/clarification, reporting progress\n\n'
    'If cues are mixed, choose the mapping with the strongest overall separation across the excerpt and reduce confidence.\n\n'
    'CONFIDENCE (deterministic guidance)\n'
    '- Base overall_confidence = 0.55.\n'
    '- Increase toward 0.95 as cues strongly separate by label across many turns (especially structure/summaries/next steps).\n'
    '- Decrease toward 0.30 if excerpt is short or both labels show similar facilitation/disclosure patterns.\n'
    '- Per-speaker confidence should be close to overall_confidence but may differ by up to 0.10.\n\n'
    'OUTPUT (STRICT JSON OBJECT ONLY)\n'
    'Keys must match exactly: speaker_roles, overall_confidence.\n'
    'speaker_roles must be an object with exactly two keys: the two speaker_label strings from the input.\n'
    'Each value must be an object with exactly: role, confidence, reason.\n\n'
    'Required schema:\n'
    '{\n'
    '  "speaker_roles": {\n'
    '    "<LABEL_1_FROM_INPUT>": {"role": "therapist"|"patient", "confidence": number, "reason": string},\n'
    '    "<LABEL_2_FROM_INPUT>": {"role": "therapist"|"patient", "confidence": number, "reason": string}\n'
    '  },\n'
    '  "overall_confidence": number\n'
    '}\n\n'
    'NOW PROCESS THIS INPUT:\n'
    '{{UTTERANCES_JSON}}\n\n\n'
    'Example input (labels are dynamic, not speaker_0/1):\n'
    '[\n'
    '  {"speaker_label":"A","text":"Before we dive in, what would you like to focus on today?"},\n'
    '  {"speaker_label":"B","text":"I’ve been anxious most days and it’s hard to unwind after work."},\n'
    '  {"speaker_label":"A","text":"When you notice the anxiety rising, what’s usually happening right beforehand?"},\n'
    '  {"speaker_label":"B","text":"Usually after interactions at work. I keep thinking about what I said."},\n'
    '  {"speaker_label":"A","text":"Let’s map one recent example and then try a brief grounding strategy and decide a next step."}\n'
    ']\n\n\n'
    'Example output (speaker_roles keys exactly match A and B; confidences are numbers):\n'
    '{\n'
    '  "speaker_roles": {\n'
    '    "A": {"role":"therapist","confidence":0.9,"reason":"Guides structure, asks exploratory questions, offers strategy/next steps"},\n'
    '    "B": {"role":"patient","confidence":0.9,"reason":"Primarily discloses feelings/experiences and responds with narrative detail"}\n'
    '  },\n'
    '  "overall_confidence": 0.9\n'
    '}\n'
)

UTTERANCE_TAGGING_PROMPT_TEMPLATE = (
    'You are a JSON transformation engine.\n\n'
    'INPUT: A JSON object with key "utterances" (array). Each element has: "index", "speaker_label", "role", "text".\n'
    'OUTPUT: A JSON object with key "utterances" (array) of the SAME LENGTH and SAME ORDER, where each element is the same as input plus exactly two new fields: "topic" and "emotion".\n\n'
    'HARD CONSTRAINTS (must follow):\n'
    '- Output STRICT JSON ONLY. No markdown. No extra keys. No explanations.\n'
    '- Output MUST conform exactly to:\n'
    '{\n'
    '  "utterances": [\n'
    '    {\n'
    '      "index": number,\n'
    '      "speaker_label": string,\n'
    '      "role": "therapist"|"patient",\n'
    '      "text": string,\n'
    '      "topic": string,\n'
    '      "emotion": string\n'
    '    }\n'
    '  ]\n'
    '}\n'
    '- Copy "index", "speaker_label", "role", and "text" EXACTLY as provided (byte-for-byte). Do not edit or paraphrase "text".\n'
    '- "emotion" MUST be one of the allowed EMOTION values listed below (exact lowercase match).\n'
    '- "topic" MUST follow the TOPIC RULES below.\n'
    '- Choose exactly ONE topic and ONE emotion per utterance.\n'
    '- Do not invent any facts. Do not add or infer names, places, or identifying details. Do not diagnose.\n'
    '- If "text" is empty or only whitespace: set topic="other" and emotion="neutral".\n'
    '- If uncertain/ambiguous: set topic="other" and emotion="neutral".\n\n'
    'ALLOWED EMOTION VALUES (lowercase):\n'
    '["neutral","calm","anxious","sad","angry","frustrated","overwhelmed","stressed","fearful","ashamed","guilty","confused","hopeful","relieved","grateful","discouraged","encouraged","joyful"]\n\n'
    'TOPIC RULES (controlled free-text):\n'
    '- Format: snake_case only (lowercase letters a-z, digits allowed, underscores). No spaces, hyphens, punctuation, or emojis.\n'
    '- Length: 1–3 words separated by underscores; max 24 characters total.\n'
    '- Semantics: must be general and reusable across many sessions; no names, places, organizations, dates, times, addresses, usernames, IDs, or other unique identifiers.\n'
    '- Safety: no diagnoses or medical/mental health disorder labels (e.g., do not output "depression", "ptsd", "bipolar", "adhd", "ocd", "autism", "eating_disorder", etc.).\n'
    '- Non-verbatim: MUST NOT repeat or paraphrase the full utterance; it must be a short label, not a sentence.\n'
    '- If you cannot find a compliant general topic, use "other".\n\n'
    'DETERMINISTIC TOPIC SELECTION (apply in order; fse the list as guidance, but choose the best-fitting topic label):\n'
    '1) If the utterance is a greeting/check-in/opening ("hi", "hello", "how are you", "how have you been") → "check_in"\n'
    '2) If it is about the therapy process, agenda, session structure, goals for today, or reflecting on therapy → "therapy_process"\n'
    '3) If it is about breathing, grounding, relaxation, mindfulness, meditation → "mindfulness"\n'
    '4) If it is about coping tools/strategies, skills, exercises, or "what can I do when..." → "coping_skills"\n'
    '5) If it is about sleep, insomnia, fatigue, nightmares, waking up → "sleep"\n'
    '6) If it is about work/school, performance, deadlines, exams → "work_stress"\n'
    '7) If it is about relationships broadly (partner/friends/social) → "relationships"\n'
    '8) If it is about family/parenting/caregiving roles → "family"\n'
    '9) If it is about communication (asserting needs, listening, difficult conversations) → "communication"\n'
    '10) If it is about conflict, boundaries, saying no, people-pleasing → "boundaries"\n'
    '11) If it is about self-worth, self-criticism, confidence, identity → "self_esteem"\n'
    '12) If it is about grief, loss, missing someone (without identifying who) → "grief"\n'
    '13) If it is about health habits (exercise, food, general wellbeing) without medical labeling → "wellbeing"\n'
    '14) If it is about motivation, goals, planning next steps → "goal_setting"\n'
    '15) If it assigns between-session practice/homework/journaling/worksheet → "home_practice"\n'
    '16) If it is primarily labeling/exploring feelings (e.g., "I feel...", "that sounds...") and none above matched → "emotions"\n'
    '17) Else → "other"\n\n'
    'EMOTION SELECTION RULES:\n'
    '- Prefer explicitly stated feelings (e.g., “stressed”, “anxious”, “sad”, “angry”, “overwhelmed”).\n'
    '- If multiple emotions appear, choose the strongest/most central one.\n'
    '- If no clear emotion markers, use "neutral".\n'
    '- Never output any emotion outside the allowed list.\n\n'
    'Transform this input JSON by adding "topic" and "emotion" per utterance, following the system rules:\n'
    '{{UTTERANCES_JSON}}\n\n'
    '{"example_input":{"utterances":[{"index":0,"speaker_label":"A","role":"therapist","text":"How have things been since we last talked?"},{"index":1,"speaker_label":"B","role":"patient","text":"I\'ve been overwhelmed at work and I keep waking up at night."},{"index":2,"speaker_label":"A","role":"therapist","text":"Let’s try a slow breathing exercise together for a minute."}]},"example_output":{"utterances":[{"index":0,"speaker_label":"A","role":"therapist","text":"How have things been since we last talked?","topic":"check_in","emotion":"neutral"},{"index":1,"speaker_label":"B","role":"patient","text":"I\'ve been overwhelmed at work and I keep waking up at night.","topic":"work_stress","emotion":"overwhelmed"},{"index":2,"speaker_label":"A","role":"therapist","text":"Let’s try a slow breathing exercise together for a minute.","topic":"mindfulness","emotion":"calm"}]}}\n'
)
