"""Draw the judge-reliability audit sample (software).

Objective: estimate the LLM judge's two error rates against human adjudication.

    false positive  P(answer wrong  | judge said correct)   target +/-2pp
    false negative  P(answer right  | judge said wrong)     target +/-5pp

Each rate is defined over *all* rows carrying that judge verdict, so each splits
into two cells by whether the independent NLI metric corroborates the judge:

    judge=1   A  NLI disagrees   4,397   weight 0.463
              C  NLI agrees      5,109   weight 0.537
    judge=0   B  NLI disagrees     355   weight 0.045
              D  NLI agrees      7,516   weight 0.955

Sampling all four is what makes the rates estimable rather than assumed. Within
each cell the draw is allocated proportionally across the five systems, so a cell
rate is unbiased for its population; cells are then combined by population weight.

Sample sizes are derived, not chosen: each cell gets the n that brings its
contribution to its rate's confidence interval within the target, given what the
already-audited cells contribute. A and B carry existing verdicts, so only the
shortfall is drawn.

Supersedes build_human_audit.py, which sampled the disagreement cells only.

Usage:
    uv run python analysis/build_judge_audit.py            # draw
    uv run python analysis/build_judge_audit.py --analyze  # once annotated
"""

from __future__ import annotations

import argparse
import math
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE  # release layout: every file sits next to this script
AUDIT = HERE

SEED = 20260729
PRIOR = pd.read_csv(os.path.join(HERE, "..", "human_audit_linusv2.csv"),
                    keep_default_na=False, dtype=str) \
    if os.path.exists(os.path.join(HERE, "..", "human_audit_linusv2.csv")) else None
PRIOR_KEY = os.path.join(AUDIT, "key", "human_audit_key.csv")

SAMPLE_PATH = os.path.join(HERE, "audit_sample.csv")
KEY_PATH = os.path.join(HERE, "audit_key.csv")
# verdicts on GraphRAG x qwen3-32b answers that a later re-run of that cell replaced
DROPPED = set(open(os.path.join(HERE, "dropped_ids.txt")).read().split())

CELLS = {  # name -> (judge verdict, nli verdict)
    "A_judge1_nli0": (1, 0),
    "C_judge1_nli1": (1, 1),
    "B_judge0_nli1": (0, 1),
    "D_judge0_nli0": (0, 0),
}
TARGET_N = {"A_judge1_nli0": 167, "C_judge1_nli1": 63,
            "B_judge0_nli1": 0, "D_judge0_nli0": 42}


def _allocate(sizes: pd.Series, total: int) -> pd.Series:
    """Largest-remainder proportional allocation across systems."""
    exact = sizes / sizes.sum() * total
    base = np.floor(exact).astype(int)
    short = total - int(base.sum())
    if short:
        base.loc[(exact - base).sort_values(ascending=False).index[:short]] += 1
    return base.clip(upper=sizes)


def build() -> None:
    nli = pd.read_csv(os.path.join(OUT, "nli_long.csv"))
    nli = nli[~nli.generated.astype(str).str.lstrip().str.upper().str.startswith("ERROR")]
    sw = nli[nli.domain == "software"].copy()

    # rows already adjudicated, carried forward with their ids and verdicts
    prior = PRIOR.merge(pd.read_csv(PRIOR_KEY), on="audit_id", suffixes=("", "_k"))
    prior = prior[prior.domain == "software"].copy()
    prior["cell"] = np.where(prior.stratum.str.startswith("A"),
                             "A_judge1_nli0", "B_judge0_nli1")
    done = prior[pd.to_numeric(prior.human_correct, errors="coerce").notna()]

    rng = np.random.default_rng(SEED)
    new = []
    print(f"{'cell':<16}{'population':>11}{'have':>6}{'target':>8}{'draw':>6}   allocation")
    for cell, (j, n) in CELLS.items():
        pool = sw[(sw.judge == j) & (sw.nli_correct == n)]
        have = done[done.cell == cell] if cell in done.cell.values else done[done.cell == cell]
        n_have = len(have)
        want = max(0, TARGET_N[cell] - n_have)
        if want == 0:
            print(f"{cell:<16}{len(pool):>11}{n_have:>6}{TARGET_N[cell]:>8}{0:>6}   —")
            continue
        # exclude rows already in the sample (A/B only; C/D were never sampled)
        seen = set(zip(prior.question, prior.generated)) if cell.startswith(("A", "B")) else set()
        avail = pool[~pd.Series(list(zip(pool.question, pool.generated)),
                                index=pool.index).isin(seen)]
        # Allocate to the per-system TARGET, then draw only each system's shortfall.
        # Spreading the shortfall proportionally instead would keep adding rows to
        # systems that are already at target and leave the thin ones thin.
        target_s = _allocate(pool.groupby("system").size(), TARGET_N[cell])
        have_s = have.groupby("system").size() if n_have else pd.Series(dtype=int)
        alloc = (target_s - have_s.reindex(target_s.index).fillna(0).astype(int)).clip(lower=0)
        alloc = alloc.clip(upper=avail.groupby("system").size().reindex(alloc.index).fillna(0).astype(int))
        picks = [g.sample(int(alloc.loc[s]), random_state=int(rng.integers(1e9)))
                 for s, g in avail.groupby("system") if alloc.loc[s] > 0]
        got = pd.concat(picks)
        got["cell"] = cell
        new.append(got)
        alloc_s = " ".join(f"{s.split()[0][:4]}:{k}" for s, k in alloc.items() if k)
        print(f"{cell:<16}{len(pool):>11}{n_have:>6}{TARGET_N[cell]:>8}{len(got):>6}   {alloc_s}")

    newdf = pd.concat(new).sample(frac=1, random_state=SEED).reset_index(drop=True)
    # "N" prefix: the prior draw already used A0001-A0375, so a cell-letter
    # scheme would collide with it.
    newdf["audit_id"] = [f"N{i:04d}" for i in range(1, len(newdf) + 1)]
    newdf["human_correct"] = ""
    newdf["human_notes"] = ""

    cols = ["audit_id", "cell", "category", "question", "gold", "generated",
            "human_correct", "human_notes"]
    old = prior.assign(cell=prior.cell)[
        ["audit_id", "cell", "category", "question", "gold", "generated",
         "human_correct", "human_notes"]]
    combined = pd.concat([old, newdf[cols]], ignore_index=True)

    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    combined.drop(columns=["cell"]).to_csv(SAMPLE_PATH, index=False)
    keycols = ["audit_id", "cell", "system", "generator_label", "category",
               "judge", "nli_correct"]
    pd.concat([prior.assign(cell=prior.cell)[keycols],
               newdf[keycols]], ignore_index=True).to_csv(KEY_PATH, index=False)

    targets = newdf.audit_id.tolist()
    with open(os.path.join(AUDIT, "audit_todo.txt"), "w") as fh:
        fh.write("\n".join(targets) + "\n")
    print(f"\n{len(combined)} rows total, {len(done)} already adjudicated, "
          f"{len(targets)} to do")
    print(f"wrote {os.path.relpath(SAMPLE_PATH, HERE)}, "
          f"{os.path.relpath(KEY_PATH, HERE)}, audit_todo.txt")


def analyze() -> None:
    def wilson(k, n, z=1.96):
        if n == 0:
            return (0.0, 1.0)
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return max(0, c - h), min(1, c + h)

    nli = pd.read_csv(os.path.join(OUT, "nli_long.csv"))
    nli = nli[~nli.generated.astype(str).str.lstrip().str.upper().str.startswith("ERROR")]
    sw = nli[nli.domain == "software"]
    d = pd.read_csv(SAMPLE_PATH).merge(pd.read_csv(KEY_PATH), on="audit_id",
                                       suffixes=("", "_k"))
    d["hc"] = pd.to_numeric(d.human_correct, errors="coerce")
    d = d[d.hc.notna() & ~d.audit_id.isin(DROPPED)].copy()
    d["wrong"] = d.judge != d.hc

    for rate, cells, verdict in [("FALSE POSITIVE  P(wrong | judge said correct)",
                                 ["A_judge1_nli0", "C_judge1_nli1"], 1),
                                ("FALSE NEGATIVE  P(right | judge said wrong)",
                                 ["B_judge0_nli1", "D_judge0_nli0"], 0)]:
        pop = {c: int(((sw.judge == CELLS[c][0]) & (sw.nli_correct == CELLS[c][1])).sum())
               for c in cells}
        tot = sum(pop.values())
        est = var = 0.0
        print(f"\n{rate}")
        for c in cells:
            g = d[d.cell == c]
            n, k = len(g), int(g.wrong.sum())
            w = pop[c] / tot
            p = k / n if n else 0.0
            pv = max(p, 1.0 / (n + 2)) if n else 0.5
            est += w * p
            var += w * w * pv * (1 - pv) / n if n else 0.0
            lo, hi = wilson(k, n) if n else (0, 1)
            print(f"   {c:<16} w={w:.3f}  {k:>3}/{n:<4} = {100*p:5.1f}%  [{100*lo:.1f}, {100*hi:.1f}]")
        h = 1.96 * math.sqrt(var)
        print(f"   {'combined':<16}          {100*est:>16.2f}%  +/-{100*h:.2f}pp")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    analyze() if a.analyze else build()
