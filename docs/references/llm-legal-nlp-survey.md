# LLMs for legal / administrative text — survey

**Theme file** (the LLM document-analysis we use; not NER).

## References
- **LLMs in law (survey).** *Large language models in law: A survey* (AI Open, 2024).
  https://www.sciencedirect.com/science/article/pii/S2666651024000172
- **Legal-domain NLP (survey).** *Natural Language Processing for the Legal Domain: A Survey of Tasks, Datasets,
  Models, and Challenges* (2024). https://arxiv.org/abs/2410.21306
- **LLM text classification (caveat).** *Large Language Models for Text Classification: Case Study and
  Comprehensive Review* (2025). https://arxiv.org/abs/2501.08457

## Why it matters to our work
We use an **LLM (Qwen)** for three document-side tasks: per-document **topic + summary** (`evaluate`), and
**cluster naming** (`processo-cluster`). These surveys ground that use of LLMs on legal/administrative text and
supply an honest **caveat we should report**: general-purpose LLMs are often *out-performed by smaller fine-tuned
models* on specialized legal classification (≈30 pts in one study), and legal AI must meet "strict standards of
accuracy, fairness, and transparency" — directly relevant to how we frame the reliability of our LLM-derived
topics/names. (We explicitly **do not** use NER.)

## How we cite it
Method (LLM topic/summary/naming) + a measured limitation; reinforces the AI & Law accuracy/transparency framing.
