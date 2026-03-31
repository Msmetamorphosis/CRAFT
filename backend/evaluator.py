"""
evaluator.py - Output quality scoring for CRAFT
Scores the LLM output against task-appropriate quality dimensions.
"""

import json
import re
import anthropic
from config import MODEL_DEFAULT


EVAL_SYSTEM = """You are an expert evaluating the quality of AI-generated outputs.
Be honest and strict. Do not inflate scores. Score based on how useful this output
actually is to a real enterprise user with the stated task.
Return ONLY valid JSON with no text outside it."""

EVAL_TEMPLATES = {
    "extraction": """Score this AI output for a data extraction task.

ORIGINAL PROMPT:
{prompt}

AI OUTPUT:
{output}

Score these dimensions 0-100:
- schema_compliance: Does output follow required structure/fields?
- completeness: Are all required fields populated?
- accuracy: Are values correctly extracted (no hallucination)?
- parseable: Is output actually usable by a downstream system?

Return ONLY this JSON:
{{
  "dimensions": {{
    "schema_compliance": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "completeness": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "accuracy": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "parseable": {{"score": <0-100>, "feedback": "<specific feedback>"}}
  }},
  "total_score": <average of dimension scores>,
  "summary": "<2 sentence plain language assessment>",
  "key_failure": "<most important thing wrong, or null if good>"
}}""",

    "reasoning": """Score this AI output for a reasoning and analysis task.

ORIGINAL PROMPT:
{prompt}

AI OUTPUT:
{output}

Score these dimensions 0-100:
- relevance: Does it actually answer what was asked?
- completeness: Does it address all aspects of the situation?
- accuracy: Are claims supported or at least not contradicted by context?
- actionability: Can the user actually do something with this answer?

Return ONLY this JSON:
{{
  "dimensions": {{
    "relevance": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "completeness": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "accuracy": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "actionability": {{"score": <0-100>, "feedback": "<specific feedback>"}}
  }},
  "total_score": <average of dimension scores>,
  "summary": "<2 sentence plain language assessment>",
  "key_failure": "<most important thing wrong, or null if good>"
}}""",

    "generation": """Score this AI output for a content generation task.

ORIGINAL PROMPT:
{prompt}

AI OUTPUT:
{output}

Score these dimensions 0-100:
- coherence: Is the content well-structured and logical?
- tone_fit: Does the tone match what was requested or implied?
- constraint_adherence: Does it follow the constraints given?
- usability: Would this actually work for its stated purpose?

Return ONLY this JSON:
{{
  "dimensions": {{
    "coherence": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "tone_fit": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "constraint_adherence": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "usability": {{"score": <0-100>, "feedback": "<specific feedback>"}}
  }},
  "total_score": <average of dimension scores>,
  "summary": "<2 sentence plain language assessment>",
  "key_failure": "<most important thing wrong, or null if good>"
}}""",

    "ideation": """Score this AI output for an ideation and brainstorming task.

ORIGINAL PROMPT:
{prompt}

AI OUTPUT:
{output}

Score these dimensions 0-100:
- diversity: Are ideas genuinely different from each other?
- novelty: Are ideas beyond the obvious first answers?
- feasibility: Are ideas actually implementable given stated constraints?
- expansiveness: Does it open up thinking rather than narrow it prematurely?

Return ONLY this JSON:
{{
  "dimensions": {{
    "diversity": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "novelty": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "feasibility": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "expansiveness": {{"score": <0-100>, "feedback": "<specific feedback>"}}
  }},
  "total_score": <average of dimension scores>,
  "summary": "<2 sentence plain language assessment>",
  "key_failure": "<most important thing wrong, or null if good>"
}}""",

    "conversational": """Score this AI output for a conversational guidance task.

ORIGINAL PROMPT:
{prompt}

AI OUTPUT:
{output}

Score these dimensions 0-100:
- accuracy: Is the information correct and reliable?
- appropriate_depth: Is it the right level of detail for the question?
- clarity: Is it easy to understand for the intended user?
- forward_progress: Does it help the user move forward with their situation?

Return ONLY this JSON:
{{
  "dimensions": {{
    "accuracy": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "appropriate_depth": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "clarity": {{"score": <0-100>, "feedback": "<specific feedback>"}},
    "forward_progress": {{"score": <0-100>, "feedback": "<specific feedback>"}}
  }},
  "total_score": <average of dimension scores>,
  "summary": "<2 sentence plain language assessment>",
  "key_failure": "<most important thing wrong, or null if good>"
}}"""
}


def evaluate_output(
    client: anthropic.Anthropic,
    prompt: str,
    output: str,
    task_type: str,
    model: str = MODEL_DEFAULT
) -> dict:
    """
    Score an LLM output against task-appropriate quality dimensions.
    """
    template = EVAL_TEMPLATES.get(task_type, EVAL_TEMPLATES["conversational"])

    msg = client.messages.create(
        model=model,
        max_tokens=1000,
        system=EVAL_SYSTEM,
        messages=[{
            "role": "user",
            "content": template.format(
                prompt=prompt[:1500],
                output=output[:2000]
            )
        }]
    )

    text = msg.content[0].text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    try:
        result = json.loads(text)
        result["task_type"] = task_type
        return result
    except json.JSONDecodeError:
        return {
            "dimensions": {},
            "total_score": 0,
            "summary": "Evaluation failed. Please try again.",
            "key_failure": "Parse error",
            "task_type": task_type
        }
