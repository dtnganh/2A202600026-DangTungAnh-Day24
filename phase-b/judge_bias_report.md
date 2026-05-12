# Judge Bias Report

## Quantified Bias Checks

| Bias | Measurement | Result | Interpretation |
|---|---:|---:|---|
| Position bias | A wins when listed first | 24/30 (80.0%) | Expected near 50%; values above 55% suggest first-position preference. |
| Length bias | Longer answer wins | 22/25 (88.0%) | Values above 55% suggest the judge rewards verbosity. |

## Mitigation Strategy

- Keep swap-and-average for all pairwise judgments.
- Keep concise rubric wording that prioritizes factual accuracy over style.
- Track length-bias statistics in every judge run before trusting the aggregate result.