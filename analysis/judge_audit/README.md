# Judge audit

Material for the hand audit of the LLM judge (`gpt-5.4`) described in the paper's
"Judge Audit Protocol" appendix.

| File | Contents |
|---|---|
| `audit_sample.csv` | the sampled software answers with question, gold, generated answer and the human verdict (`human_correct`; blank = drawn but not adjudicated) |
| `audit_key.csv` | per item: cell (judge verdict × NLI verdict), system, generator, category, judge and NLI verdicts |
| `CODEBOOK.md` | the coding rule the adjudicator applied |
| `nli_long.csv` | NLI mutual-entailment scores (`dleemiller/ModernCE-large-nli`) for every scored answer, from which the cells and their population sizes are drawn |
| `dropped_ids.txt` | four verdicts on GraphRAG × `qwen3-32b` answers that a later re-run of that cell replaced; excluded from the analysis |
| `build_judge_audit.py` | the sampling and analysis script |

Reproduce the judge error rates reported in the paper:

```bash
uv run --with pandas --with numpy python build_judge_audit.py --analyze
```

Expected output: false positive 2.50% ± 2.28 pp, false negative 5.52% ± 4.77 pp, over
306 adjudicated answers (cells A 166, C 63, B 38, D 39).
