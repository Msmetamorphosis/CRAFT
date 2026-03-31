"""
auditor.py - Prompt quality scoring for CRAFT
Scores a prompt against task-appropriate rubric criteria.
Returns a detailed breakdown with scores, gaps, and ceiling.
"""

import json
import re
import anthropic
from config import MODEL_DEFAULT, RUBRICS_FILE


def load_rubrics() -> dict:
    with open(RUBRICS_FILE, "r") as f:
        return json.load(f)


AUDIT_SYSTEM = """You are an expert prompt engineer scoring prompts against a quality rubric.
You must be honest and strict. Do not inflate scores. Missing context should be penalized.
Return ONLY valid JSON with no text outside it."""

AUDIT_TEMPLATE = """Score this prompt against the rubric below. Be strict and honest.

PROMPT TO SCORE:
{prompt}

TASK TYPE: {task_type}

SCORING RUBRIC:
{rubric_json}

Instructions:
- Score each criterion 0-100 based on how well the prompt satisfies it
- Identify specific gaps: things that are missing or unclear
- Identify user-only gaps: things only the user can add (domain context, specific facts)
- Calculate weighted_total using the weights provided
- Set ceiling_score to the maximum achievable with current information

Return ONLY this JSON:
{{
  "criteria_scores": {{
    "<criterion_name>": {{
      "score": <0-100>,
      "weight": <weight from rubric>,
      "weighted_score": <score * weight / 100>,
      "feedback": "<specific one-sentence feedback>",
      "gap": "<what is missing or null if satisfied>"
    }}
  }},
  "bonus_scores": {{
    "<bonus_name>": {{
      "score": <0-100>,
      "weight": <weight>,
      "weighted_score": <score * weight / 100>,
      "feedback": "<specific feedback>"
    }}
  }},
  "total_score": <sum of all weighted_scores, 0-100>,
  "ceiling_score": <max possible given available info, 0-100>,
  "automated_gaps": ["<things the system can fix>"],
  "user_gaps": ["<things only the user can provide>"],
  "summary": "<2 sentence plain language assessment>"
}}"""


def audit_prompt(
    client: anthropic.Anthropic,
    prompt: str,
    task_type: str,
    model: str = MODEL_DEFAULT
) -> dict:
    """
    Score a prompt against the task-appropriate rubric.
    Returns detailed scoring breakdown.
    """
    rubrics = load_rubrics()

    # Build scoring rubric for this task type
    universal = rubrics["universal_criteria"]
    modifier  = rubrics["task_modifiers"].get(task_type, {})

    # Apply weight adjustments
    adjusted_criteria = {}
    for name, criterion in universal.items():
        adjusted = dict(criterion)
        adjustment = modifier.get("weight_adjustments", {}).get(name, 0)
        adjusted["weight"] = max(5, criterion["weight"] + adjustment)
        adjusted_criteria[name] = adjusted

    bonus_criteria = modifier.get("bonus_criteria", {})
    ceiling_note   = modifier.get("ceiling_note", "")

    rubric_for_prompt = {
        "criteria": adjusted_criteria,
        "bonus_criteria": bonus_criteria,
        "ceiling_note": ceiling_note
    }

    msg = client.messages.create(
        model=model,
        max_tokens=1500,
        system=AUDIT_SYSTEM,
        messages=[{
            "role": "user",
            "content": AUDIT_TEMPLATE.format(
                prompt=prompt[:2000],
                task_type=task_type,
                rubric_json=json.dumps(rubric_for_prompt, indent=2)
            )
        }]
    )

    text = msg.content[0].text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    try:
        result = json.loads(text)
        result["task_type"]   = task_type
        result["ceiling_note"] = ceiling_note
        return result
    except json.JSONDecodeError:
        return {
            "criteria_scores": {},
            "bonus_scores": {},
            "total_score": 0,
            "ceiling_score": 0,
            "automated_gaps": ["Could not parse scoring result"],
            "user_gaps": [],
            "summary": "Scoring failed. Please try again.",
            "task_type": task_type,
            "ceiling_note": ceiling_note
        }
