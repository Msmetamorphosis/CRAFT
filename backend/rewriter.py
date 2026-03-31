"""
rewriter.py - Prompt improvement engine for CRAFT
Takes a prompt, its classification, and audit results,
then produces an improved version with explanation of changes.
"""

import json
import re
import anthropic
from config import MODEL_DEFAULT, MAX_TOKENS


REWRITE_SYSTEM = """You are an expert prompt engineer improving enterprise prompts.
Your rewrites must be grounded in the original intent. Never invent facts the user did not provide.
Use placeholders like [YOUR ROLE] or [SPECIFIC CONSTRAINT] for user-only gaps.
Return ONLY valid JSON with no text outside it."""

REWRITE_TEMPLATE = """Improve this prompt based on the audit findings below.

ORIGINAL PROMPT:
{prompt}

TASK TYPE: {task_type}

AUDIT FINDINGS:
- Total score: {total_score}/100
- Ceiling score: {ceiling_score}/100
- Automated gaps (things you can fix): {automated_gaps}
- User gaps (use placeholders for these): {user_gaps}
- Summary: {summary}

REWRITING RULES:
1. Fix all automated gaps directly
2. Add placeholders in [BRACKETS] for user-only gaps
3. Keep the original intent exactly
4. Do not invent domain facts or specific context the user did not provide
5. For extraction tasks: add explicit output schema if missing
6. For reasoning tasks: add context scaffolding and constraint prompts
7. For generation tasks: add tone, audience, and format instructions
8. For ideation tasks: add evaluation criteria but keep solution space open
9. For conversational tasks: add role context and depth instructions

Return ONLY this JSON:
{{
  "rewritten_prompt": "<the improved prompt>",
  "changes_made": [
    {{
      "type": "automated",
      "change": "<what was changed>",
      "reason": "<why this improves the prompt>"
    }}
  ],
  "placeholders_added": [
    {{
      "placeholder": "<[PLACEHOLDER TEXT]>",
      "what_to_fill": "<explanation of what the user should put here>"
    }}
  ],
  "expected_score_improvement": "<brief explanation of why the rewrite should score higher>",
  "user_action_required": "<what the user needs to do to reach ceiling score, or null>"
}}"""


def rewrite_prompt(
    client: anthropic.Anthropic,
    original_prompt: str,
    task_type: str,
    audit_result: dict,
    model: str = MODEL_DEFAULT
) -> dict:
    """
    Produce an improved version of the prompt based on audit findings.
    """
    msg = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=REWRITE_SYSTEM,
        messages=[{
            "role": "user",
            "content": REWRITE_TEMPLATE.format(
                prompt=original_prompt[:2000],
                task_type=task_type,
                total_score=audit_result.get("total_score", 0),
                ceiling_score=audit_result.get("ceiling_score", 0),
                automated_gaps=json.dumps(audit_result.get("automated_gaps", [])),
                user_gaps=json.dumps(audit_result.get("user_gaps", [])),
                summary=audit_result.get("summary", "")
            )
        }]
    )

    text = msg.content[0].text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "rewritten_prompt": original_prompt,
            "changes_made": [],
            "placeholders_added": [],
            "expected_score_improvement": "Rewrite failed, original prompt returned.",
            "user_action_required": None
        }
