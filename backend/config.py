"""
config.py - CRAFT central configuration
Contextual Rewriting and Fitness Tester
"""

from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data"
RUBRICS_FILE = DATA_DIR / "rubrics" / "scoring_rubrics.json"

MODEL_DEFAULT = "claude-opus-4-5"
MAX_TOKENS    = 2000

TASK_TYPES = ["extraction", "reasoning", "generation", "ideation", "conversational"]

TASK_LABELS = {
    "extraction":     "Data Extraction",
    "reasoning":      "Reasoning and Analysis",
    "generation":     "Content Generation",
    "ideation":       "Ideation and Brainstorming",
    "conversational": "Conversational Guidance"
}

TASK_DESCRIPTIONS = {
    "extraction":     "Pulling structured data from unstructured text, documents, or reports",
    "reasoning":      "Analyzing situations, applying rules, evaluating options, explaining decisions",
    "generation":     "Drafting emails, documents, policies, job descriptions, or other content",
    "ideation":       "Brainstorming ideas, exploring solutions, generating creative options",
    "conversational": "Asking questions, seeking guidance, explaining situations, policy coaching"
}
