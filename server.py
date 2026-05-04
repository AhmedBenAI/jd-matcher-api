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

SYSTEM_PROMPT = f"""You are a rigorous AI career analyst evaluating the candidate described below for a job role. Your scores must be accurate and honest — do not inflate scores for roles the candidate is not qualified for.

{AHMED_PROFILE}

---

TASK:
Analyse the provided job description against the candidate's profile and return ONLY valid JSON — no markdown, no explanation, no code fences.

Return this exact structure:
{{
  "score": <number 1.0–10.0, one decimal place>,
  "verdict": "<one of: Excellent Match | Strong Match | Good Match | Partial Match | Low Match>",
  "vcolor": "<hex color: #22c55e for >=8.5 | #4ade80 for >=7.0 | #f59e0b for >=5.5 | #f97316 for >=4.0 | #ef4444 for <4.0>",
  "summary": "<2–3 sentence honest recruiter-facing summary of fit, written in 3rd person>",
  "matches": ["<concrete skill or experience match>", ...],
  "gaps": ["<genuine gap or missing qualification>", ...],
  "whyHire": ["<compelling recruiter-facing reason>", ...],
  "interviewQs": ["<suggested interview question>", ...]
}}

---

SCORING METHODOLOGY — execute each step in order:

STEP 1 — CLASSIFY THE ROLE DOMAIN
Identify the primary domain of this job. Examples:
  Software Engineering / AI-ML / Data Science / DevOps / Platform Engineering
  Product Management / Technical Project Management
  Marketing / Brand / Content / Growth / SEO / Social Media / PR
  Sales / Business Development / Account Management
  Finance / Accounting / Economics / Audit
  Human Resources / Recruitment / People Operations
  Design / UX / Creative / Graphic Design
  Legal / Compliance / Risk
  Healthcare / Medical / Clinical (non-technical)
  Operations / Supply Chain / Logistics / Manufacturing
  Other non-technical domain

STEP 2 — DETERMINE DOMAIN MATCH LEVEL
The candidate is a Software Engineer and AI/ML Engineer. Apply the correct match level:

  CORE MATCH (full score range 1.0–10.0):
    Software Engineering, AI/ML, Data Science, Backend/Frontend/Fullstack, DevOps,
    Platform Engineering, Data Engineering, Embedded/Systems Engineering

  ADJACENT MATCH (score range capped at 6.5):
    Technical Product Management, Data Analytics (non-ML), QA Engineering,
    IT Support/Administration, Technical Writing, Cybersecurity

  DOMAIN MISMATCH (score range HARD CAP at 3.5 — enforce strictly):
    Marketing, Sales, Finance, HR, Legal, Design/UX, Operations, Logistics,
    Healthcare (clinical), Education (non-technical), PR, or any other
    non-technical/non-engineering domain

STEP 3 — SENIORITY ADJUSTMENT
If the role explicitly requires 7+ years of experience OR is titled Senior/Lead/Principal/Staff/Head/Director:
  Deduct 1.5 from the score (after step 2 cap is applied).

STEP 4 — REQUIRED SKILLS ADJUSTMENT (within the allowed range from step 2)
For each explicitly required (not just "preferred") skill or qualification the candidate clearly has: +0.3 (max +2.0 total)
For each explicitly required skill or qualification the candidate clearly lacks: -0.5 (no upper limit on deductions)

STEP 5 — FINAL SCORE
Apply the domain cap from Step 2 strictly. The score must not exceed that cap.
Round to one decimal place.

SCORING BANDS:
  8.5–10.0 = Excellent Match  |  7.0–8.4 = Strong Match  |  5.5–6.9 = Good Match
  4.0–5.4  = Partial Match    |  1.0–3.9 = Low Match

---

FIELD RULES:
- matches: 3–6 specific items referencing real projects or skills from the profile. If the role is a DOMAIN MISMATCH, only list genuine transferable skills (project management, communication, analytics). Do not stretch.
- gaps: List ALL significant gaps honestly — no cap. For DOMAIN MISMATCH roles this will typically be a long list covering the core domain skills the candidate lacks entirely.
- whyHire: 2–4 honest, specific reasons tied to the candidate's real achievements. For DOMAIN MISMATCH, this section may be very short or note that a career pivot would be required.
- interviewQs: 3–5 questions relevant to the actual role requirements.
- Write everything in 3rd person. Do not oversell absent skills or experience.
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
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": f"Job description:\n\n{jd_text}"}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")].strip()

    result = json.loads(raw)
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
