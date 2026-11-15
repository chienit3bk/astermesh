# Astermesh Token Benchmark Guide

This guide explains how to benchmark and verify token savings and context efficiency when using **Astermesh** compared to naive raw codebase dumps.

---

## 1. Why Benchmark?

When large codebases are fed into Large Language Models (LLMs), feeding raw source files introduces:
1. **Severe Token Bloat**: Thousands of tokens wasted on implementation bodies, boilerplate, whitespace, and comments.
2. **Context Window Saturation**: Quick exhaustion of 128k/200k context limits, degrading attention mechanism quality.
3. **Escalated API Costs**: Redundant tokens billed repeatedly across multi-turn developer prompts.

**Astermesh** extracts deterministic logic entities (classes, methods, functions, components, hooks, services, variables), preserves physical line ranges (`[line_start, line_end]`), and clusters them via the **Leiden community algorithm** into dense `#ACN2` wire notation.

---

## 2. Quick Start: Benchmark Your Own Codebase

Clone this repository and run the benchmark directly against any local repository:

```bash
# 1. Install Astermesh in your environment
git clone https://github.com/ddthang2611/astermesh.git
cd astermesh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Run benchmark on your target project (#ACN2 vs raw source & #ACN1)
astermesh benchmark /path/to/your/project --report benchmark_report.md

# Optional: compare against deprecated legacy XML or evaluate a token budget
astermesh benchmark /path/to/your/project --include-xml-legacy --max-tokens 8000
```

---

## 3. How to Interpret the Benchmark Metrics

The generated report (`benchmark_report.md` or terminal output) provides quantitative indicators:

### Metric Explanations

- **Raw Codebase Dump**: Total token count if all source files in the project are concatenated directly into the LLM prompt.
- **Dense ACN Wire (`#ACN2`)**: Token count of the generated `#ACN2` context wire (exported by default to `astermesh-graph/context_graph.acn`), containing compressed directory/file/asset tables, typed entities, line coordinates, and relationships.
- **Compact XML (Legacy, opt-in)**: Evaluated only when `--include-xml-legacy` is passed.
- **Improvement / Savings Percentage**:
  Shows token reduction against raw source code, `#ACN1`, and (when opted in) legacy XML.
- **Single Community Average**: Average `#ACN2` token size per discovered Leiden community for micro-context queries via `get_community_wire(name)`.
- **Cost Savings (Estimated)**: Financial savings per 1,000 queries calculated at the standard reference price of \$3.00 / 1M input tokens.

---

## 4. Benchmark Methodology & Precision

Astermesh ensures high-fidelity benchmarks:
- **Tokenizer**: Uses OpenAI `tiktoken` with the `cl100k_base` BPE tokenizer (used by GPT-4, Claude 3.x estimation, and modern LLM coding engines). Falls back to deterministic character estimation (`max(1, len(text) // 4)`) if `tiktoken` is not installed.
- **Ignored Files**: Automatically skips `.git`, `.venv`, `node_modules`, `dist`, `build`, `astermesh-graph`, `xml-graph`, `generated`, `__generated__`, and non-source binaries to prevent artificial token inflation.
- **In-Memory Execution**: Benchmark renders `#ACN2` wire context entirely in memory without polluting the target repository with temporary files.
