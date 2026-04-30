import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

# Restrict CORS to the deployed frontend URL. Set FRONTEND_URL in .env.
CORS(app, origins=os.environ.get("FRONTEND_URL", "*"))

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Load Ahmed's profile from profile.md — edit that file to update the AI context.
_profile_path = Path(__file__).parent / "profile.md"
AHMED_PROFILE = _profile_path.read_text(encoding="utf-8")

SYSTEM_PROMPT = f"""You are an AI career analyst evaluating the candidate described below for a job role.

{AHMED_PROFILE}

---

TASK:
Analyse the provided job description against the candidate's profile above and return ONLY valid JSON — no markdown, no explanation, no code fences.

Return this exact structure:
{{
  "score": <number 1.0–10.0, one decimal place>,
  "verdict": "<one of: Excellent Match | Strong Match | Good Match | Partial Match | Low Match>",
  "vcolor": "<hex: #22c55e for >=8.5 | #4ade80 for >=7 | #f59e0b for >=5.5 | #f97316 for >=4 | #ef4444 for lower>",
  "summary": "<2–3 sentence recruiter-facing summary about the candidate's fit, written in 3rd person>",
  "matches": ["<concrete skill or experience match>", ...],
  "gaps": ["<genuine gap or area to probe>", ...],
  "whyHire": ["<compelling recruiter-facing reason>", ...],
  "interviewQs": ["<suggested interview question>", ...]
}}

SCORING:
- 8.5–10.0 = Excellent Match  |  7.0–8.4 = Strong Match  |  5.5–6.9 = Good Match
- 4.0–5.4  = Partial Match    |  1.0–3.9 = Low Match
- Deduct 1.0 if senior/lead/10+ yrs experience required and role is not junior/graduate
- Deduct 0.5 per genuine gap in explicitly required (not preferred) skills

RULES:
- matches: 4–8 specific items referencing real projects or experience from the profile
- gaps: 2–5 honest items; if no real gaps, say so
- whyHire: 3–5 persuasive, recruiter-facing points referencing specific achievements
- interviewQs: 3–5 useful questions for the interviewer to explore
- Write everything in 3rd person; do not oversell absent skills
"""


@app.route("/api/analyze-jd", methods=["POST"])
def analyze_jd():
    data = request.get_json(silent=True)
    if not data or not data.get("job_description"):
        return jsonify({"error": "job_description is required"}), 400

    jd_text = data["job_description"].strip()
    if len(jd_text) < 60:
        return jsonify({"error": "Job description is too short"}), 400

    jd_text = jd_text[:12000]

    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Job description:\n\n{jd_text}"}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
