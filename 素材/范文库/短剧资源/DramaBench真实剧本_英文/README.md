---
license: mit
task_categories:
- text-generation
language:
- en
tags:
- drama
- screenplay
- script-continuation
- creative-writing
- benchmark
pretty_name: DramaBench Script Continuation Dataset
size_categories:
- 1K<n<10K
---

# DramaBench: Drama Script Continuation Dataset

<div align="center">

[![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/2512.19012)
[![GitHub](https://img.shields.io/badge/GitHub-DramaBench-blue)](https://github.com/IIIIQIIII/DramaBench)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

## Dataset Summary

**DramaBench** is a comprehensive benchmark dataset for evaluating drama script continuation capabilities of large language models.

**Current Release: v2.0 (500 samples)** - This release contains 500 carefully selected drama scripts with context-continuation pairs, designed to assess models across six independent evaluation dimensions. This represents a 5x expansion from v1.0, providing more comprehensive evaluation coverage.

### Release Roadmap

| Version | Samples | Status | Expected Release |
|---------|---------|--------|------------------|
| v1.0 | 100 | ✅ Released | 2025-12-23 |
| **v2.0** | **500** | **✅ Available Now** | **2026-01-01** |
| v3.0 (Full) | 1,103 | 📋 Planned | Q2 2026 |

**Note**: The full DramaBench benchmark consists of 1,103 professional-quality scripts. We are releasing the dataset progressively to ensure quality and gather community feedback.

### Key Features

- **High-Quality Scripts**: Carefully sampled from the full collection of 1,103 professional-quality scripts
- **Fountain Format**: Industry-standard screenplay format for consistency
- **Structured Splits**: Each script split at natural scene boundaries or midpoints
- **Rich Metadata**: Includes title, description, split statistics, and structural information
- **English Language**: All scripts in English with diverse dramatic scenarios
- **Progressive Release**: Gradual expansion from 100 → 500 → 1,103 samples

### Evaluation Framework

DramaBench evaluates script continuation across **six independent dimensions**:

1. **Format Standards**: Screenplay format compliance (rule-based)
2. **Narrative Efficiency**: Story progression effectiveness (LLM-labeled)
3. **Character Consistency**: Character voice and behavior consistency (LLM-labeled)
4. **Emotional Depth**: Emotional arc development (LLM-labeled)
5. **Logic Consistency**: Factual coherence and continuity (LLM-labeled)
6. **Conflict Handling**: Conflict development and resolution (LLM-labeled)

## Paper

**DramaBench: A Six-Dimensional Evaluation Framework for Drama Script Continuation**

*Shijian Ma, Yunqi Huang, Yan Lin*

Drama script continuation requires models to maintain character consistency, advance plot coherently, and preserve dramatic structure—capabilities that existing benchmarks fail to evaluate comprehensively. We present DramaBench, the first large-scale benchmark for evaluating drama script continuation across six independent dimensions: Format Standards, Narrative Efficiency, Character Consistency, Emotional Depth, Logic Consistency, and Conflict Handling.

Our framework combines rule-based analysis with LLM-based labeling and statistical metrics, ensuring objective and reproducible evaluation. We conduct comprehensive evaluation of 8 state-of-the-art language models on 1,103 scripts (8,824 evaluations total), with rigorous statistical significance testing (252 pairwise comparisons, 65.9% significant) and human validation (188 scripts, substantial agreement on 3/5 dimensions).

Our ablation studies confirm all six dimensions capture independent quality aspects (mean |r| = 0.020). DramaBench provides actionable, dimension-specific feedback for model improvement and establishes a rigorous standard for creative writing evaluation.

**Links:**
- **arXiv Paper**: [https://arxiv.org/abs/2512.19012](https://arxiv.org/abs/2512.19012)
- **GitHub Repository**: [https://github.com/IIIIQIIII/DramaBench](https://github.com/IIIIQIIII/DramaBench)
- **Web Demo**: [https://dramabench.pages.dev/](https://dramabench.pages.dev/)

## Dataset Structure

### Data Instances

Each instance contains a drama script split into context and continuation:

```json
{
  "id": "script_0004",
  "title": "Heiress Meets Boyfriend's Parents",
  "description": "A wealthy heiress brings expensive gifts to meet her boyfriend's mother for the first time, only to face unexpected humiliation.",
  "context": "INT. GU FAMILY LIVING ROOM - DAY\n\nGU MOTHER arranges elegant gift boxes...",
  "continuation": "EXT. GARDEN RESTAURANT ENTRANCE - DAY\n\nLINFENG waits in a slightly worn but pressed suit...",
  "stats": {
    "total_lines": 81,
    "context_lines": 28,
    "continuation_lines": 53,
    "split_ratio": "34.6%",
    "split_type": "scene_boundary",
    "split_point": 28
  }
}
```

### Data Fields

- `id` (string): Unique identifier for each script
- `title` (string): Script title
- `description` (string): Brief plot summary
- `context` (string): First half of the script (given to models)
- `continuation` (string): Second half of the script (expected generation target)
- `stats` (object): Split statistics
  - `total_lines` (int): Total lines in complete script
  - `context_lines` (int): Lines in context portion
  - `continuation_lines` (int): Lines in continuation portion
  - `split_ratio` (string): Percentage split point
  - `split_type` (string): Type of split (`scene_boundary` or `middle`)
  - `split_point` (int): Line number where split occurs

### Data Splits

**Current Version (v2.0)**:

| Split | Samples | Description |
|-------|---------|-------------|
| `train` | 500 | Extended release for comprehensive evaluation and experimentation |

**Previous Releases**:
- **v1.0 (2025-12-23)**: 100 samples - Initial release (available as separate file: `dramabench_continuation_100.jsonl`)

**Upcoming Releases**:
- **v3.0 (Q2 2026)**: 1,103 samples - Complete benchmark dataset with full coverage

**Note**: v2.0 samples do not overlap with v1.0. Both versions are available separately:
- `dramabench_continuation_100.jsonl` - v1.0 (100 samples, seed=42)
- `dramabench_continuation_500.jsonl` - v2.0 (500 samples, seed=43, non-overlapping)

## Dataset Statistics

### Current Release (v2.0)

- **Total Samples**: 500
- **Average Context Length**: ~1,601 characters (~400 tokens)
- **Average Continuation Length**: ~1,600 characters (~400 tokens)
- **Split Types**:
  - Scene Boundary: ~60%
  - Middle: ~40%
- **Format**: Fountain screenplay format (industry standard)
- **Sampling Method**: Random sampling (seed=43) from remaining scripts after v1.0 exclusion

### Previous Release (v1.0)

- **Total Samples**: 100
- **Sampling Method**: Random sampling (seed=42) from full collection
- **Status**: Available separately as `dramabench_continuation_100.jsonl`

### Full Benchmark (v3.0 - Coming Q2 2026)

- **Total Samples**: 1,103 scripts
- **Total Evaluations**: 8,824 (1,103 scripts × 8 models)
- **Statistical Tests**: 252 pairwise comparisons
- **Human Validation**: 188 scripts with substantial agreement

## Use Cases

### Primary Use Case: Script Continuation Evaluation

Given the `context` portion of a script, evaluate language models' ability to:
- Generate coherent continuations
- Maintain character voices and consistency
- Advance plot naturally
- Preserve dramatic structure
- Follow screenplay format conventions

### Secondary Use Cases

- **Creative Writing Assistance**: Training models for screenplay generation
- **Narrative Understanding**: Evaluating story comprehension and prediction
- **Format Compliance**: Testing screenplay format adherence
- **Dialogue Generation**: Assessing natural conversation generation

## Quick Start

### Basic Usage: Load and Explore Dataset

````python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("FutureMa/DramaBench", split="train")

# Access a sample
sample = dataset[0]
print(f"Title: {sample['title']}")
print(f"Description: {sample['description']}")
print(f"Context:\n{sample['context'][:300]}...")
print(f"Ground Truth Continuation:\n{sample['continuation'][:300]}...")
print(f"Stats: {sample['stats']}")
````

### Advanced Usage: Generate Script Continuation with LLM

````python
import random
from datasets import load_dataset
import httpx
import asyncio

# Load dataset and select random sample
dataset = load_dataset("FutureMa/DramaBench", split="train")
sample = random.choice(dataset)

# Official DramaBench prompt template
PROMPT_TEMPLATE = """### Role
You are an expert screenwriter and story editor specializing in drama script writing. Your task is to continue an incomplete script provided in the [CONTEXT] section.

### Task Guidelines
1.  **Analyze the Context**: Understand the genre, tone, character personalities, and current plot progression.
2.  **Maintain Consistency**:
    -   **Plot**: The continuation must logically follow the events in the context.
    -   **Character**: Maintain the specific speaking style and internal logic of each character.
    -   **Format**: Strictly follow the **Fountain Syntax** used in the context. This includes scene headings (INT./EXT.), character names (CENTERED or UPPERCASE), dialogue, parentheticals (e.g., (V.O.), (internal monologue)), and action lines.
3.  **Output Requirement**:
    -   Generate **only** the continuation. Do not repeat the input context.
    -   Do not output any conversational filler or explanations.
    -   **Strict Formatting**: The output **MUST** be wrapped in a code block labeled `continuation`.
    -   Your output should look exactly like this structure:
        ```continuation
        [Your script content here]
        ```

### Input Data
Given an incomplete drama script (CONTEXT), generate the natural continuation (CONTINUATION) that completes the story.

```context
{{context}}
```

### Output
Please generate the continuation below, ensuring it starts with ```continuation:"""

# Call LLM API (example with OpenRouter)
async def generate_continuation(context: str, api_key: str, model: str = "google/gemini-3-flash-preview"):
    prompt = PROMPT_TEMPLATE.replace("{{context}}", context)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

# Generate continuation
api_key = "your-openrouter-api-key"  # Get from https://openrouter.ai/keys
continuation = asyncio.run(generate_continuation(sample['context'], api_key))

print(f"Generated Continuation:\n{continuation}")
print(f"\nGround Truth:\n{sample['continuation']}")
````

### Supported Models

DramaBench has been evaluated with:
- **GPT-5.2** (OpenAI)
- **Gemini 3 Flash/Pro** (Google)
- **Claude Opus 4.5** (Anthropic)
- **GLM-4.6/4.7** (Zhipu AI)
- **Qwen3-Max** (Alibaba)
- **MiniMax M2** (MiniMax)
- **DeepSeek V3.2** (DeepSeek)
- **Kimi K2 Thinking** (Moonshot AI)

For more examples and evaluation code, visit the [GitHub repository](https://github.com/IIIIQIIII/DramaBench).

## Citation

If you use this dataset in your research, please cite:

```bibtex
@misc{ma2025dramabenchsixdimensionalevaluationframework,
  title={DramaBench: A Six-Dimensional Evaluation Framework for Drama Script Continuation},
  author={Shijian Ma and Yunqi Huang and Yan Lin},
  year={2025},
  eprint={2512.19012},
  archivePrefix={arXiv},
  primaryClass={cs.CL},
  url={https://arxiv.org/abs/2512.19012}
}
```

## License

This dataset is released under the MIT License. See [LICENSE](LICENSE) for details.

## Dataset Creation

### Source Data

The scripts were created and curated specifically for the DramaBench evaluation framework. Each script was:
- Written in professional Fountain screenplay format
- Split at natural narrative boundaries
- Validated for structural consistency
- Reviewed for quality and diversity

### Sampling Method

**v2.0 (Current - 500 samples)**:
- Randomly sampled (seed=43) from the full collection of 1,103 scripts
- Excludes all 100 samples used in v1.0
- Sampled from remaining 1,003 scripts to ensure no overlap

**v1.0 (100 samples)**:
- Randomly sampled (seed=42) from the full collection of 1,103 scripts
- Available separately as `dramabench_continuation_100.jsonl`

### Annotations

The dataset includes:
- **Manual Annotations**: Title, description, and quality labels
- **Automated Annotations**: Split statistics and structural metadata
- **LLM-Based Labels**: Multi-dimensional quality assessments (available in full dataset)

## Evaluation Results

The paper reports comprehensive evaluation of 8 state-of-the-art models:

| Rank | Model | Overall Score |
|------|-------|---------------|
| 🥇 1 | GPT-5.2 | 0.960 |
| 🥈 2 | GLM-4.6 | 0.930 |
| 🥉 3 | Qwen3-Max | 0.917 |
| 4 | Claude Opus 4.5 | 0.888 |
| 5 | MiniMax M2 | 0.869 |
| 6 | DeepSeek V3.2 | 0.856 |
| 7 | Gemini 3 Pro | 0.843 |
| 8 | Kimi K2 Thinking | 0.815 |

**Statistical Validation**:
- 252 pairwise comparisons performed
- 65.9% statistically significant differences (FDR-corrected)
- Human validation: substantial agreement on 3/5 dimensions

## Additional Resources

- **Paper (arXiv)**: [https://arxiv.org/abs/2512.19012](https://arxiv.org/abs/2512.19012)
- **GitHub Repository**: [https://github.com/IIIIQIIII/DramaBench](https://github.com/IIIIQIIII/DramaBench)
  - Evaluation code and pipeline
  - Full benchmark details
  - Model evaluation results
- **Interactive Web Demo**: [https://dramabench.pages.dev/](https://dramabench.pages.dev/)
  - Explore model performance
  - Compare dimension-wise scores
  - Browse case studies
- **Model Leaderboard**: Detailed per-dimension scores for 8 SOTA models

### Stay Updated

- ⭐ Star the [GitHub repo](https://github.com/IIIIQIIII/DramaBench) to get notified of new releases
- 📧 Subscribe to dataset updates on Hugging Face

