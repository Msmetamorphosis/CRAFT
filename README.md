# CRAFT
## Contextual Rewriting and Fidelity Tester

**Crystal Tubbs | KSU MSAI | Metamorphic Curations LLC**

CRAFT is a prompt quality analysis and improvement tool built on research from the
LLM Reliability Pipeline project. It diagnoses enterprise prompts, scores them against
task-appropriate rubrics, rewrites them with fidelity to the original intent, and shows
the measurable improvement in output quality.

Born from research finding: prompt style determines output quality more than model capability.
CRAFT operationalizes that finding into a practical tool for enterprise users.

---

## What CRAFT does

1. **Classifies** your prompt into one of five enterprise task types
2. **Scores** it against a task-appropriate rubric (0-100)
3. **Runs** your original prompt through Claude and scores the output
4. **Rewrites** your prompt, fixing automated gaps and flagging user-only gaps with placeholders
5. **Runs** the improved prompt and scores the new output
6. **Shows** a side-by-side comparison with quantified improvement

---

## Five task types

| Type | Description | Example |
|---|---|---|
| Extraction | Pulling structured data from text | Extract fields from a contract |
| Reasoning | Analyzing situations, applying rules | Does this employee qualify for FMLA? |
| Generation | Drafting content and communications | Write an email to a client |
| Ideation | Brainstorming and creative exploration | Ideas for a new product feature |
| Conversational | Guidance, coaching, policy questions | How do I handle this situation? |

---

## Scoring

**Prompt quality score (0-100):** Rubric-based audit of the prompt against task-appropriate criteria including clarity of intent, context completeness, specificity, and output specification. Weights shift per task type.

**Output quality score (0-100):** Claude-evaluated assessment of the actual output against task-appropriate dimensions (schema compliance for extraction, actionability for reasoning, tone fit for generation, etc.)

**Ceiling score:** The maximum score achievable with the information provided. Some gaps can only be filled by the user. CRAFT shows you exactly what those are.


## Related project

**LLM Reliability Pipeline** — the research project this tool operationalizes.
`https://github.com/Msmetamorphosis/llm-reliability-dashboard`

---

## Research context

CRAFT extends the LLM Reliability Pipeline research by investigating whether
prompt-level interventions, specifically completeness auditing and task-appropriate
rewriting, improve output quality across enterprise task types. The hypothesis is that
improvement will be largest for reasoning and conversational tasks, which are the most
underspecified in practice.

Try it for yourself, just add your Anthropic API key and go: https://msmetamorphosis.github.io/CRAFT/
