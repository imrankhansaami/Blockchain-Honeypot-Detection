# Risk scoring

## Model

Each finding contributes points:

```
points = severity_base × evidence_weight × confidence_factor
```

**Severity base**

| Severity | Points |
| --- | --- |
| critical | 60 |
| high | 25 |
| medium | 12 |
| low | 5 |
| informational | 0 |

**Evidence weight** (`EvidenceSource`)

| Source | Weight |
| --- | --- |
| simulation | 1.00 |
| onchain | 0.90 |
| explorer | 0.70 |
| source_code | 0.70 |
| abi | 0.50 |
| bytecode | 0.40 |
| heuristic | 0.25 |

**Confidence factor**

| Confidence | Factor |
| --- | --- |
| confirmed | 1.00 |
| suspicious | 0.60 |
| inconclusive | 0.25 |

## De-duplication

Correlated findings are de-duplicated by **category**: only the strongest
contribution within a category is scored. This prevents one underlying issue
(e.g. a blacklist seen through bytecode, source and heuristic lenses) from being
counted three times. Genuinely independent categories (honeypot, tax, minting,
upgradeability, blacklist, whitelist, access control, transfer restriction,
liquidity) are each counted once.

## Aggregation and classification

Contributions are summed and capped at 100.

| Score | Classification |
| --- | --- |
| 0–19 | Low observed risk |
| 20–39 | Moderate risk |
| 40–59 | Elevated risk |
| 60–79 | High risk |
| 80–100 | Critical risk |

## Explainability

The report includes a line per contributing finding, e.g.:

```
+60 pts [critical/confirmed/simulation] Token can be bought but cannot be sold
+12 pts [medium/suspicious/bytecode] Owner-adjustable sell tax
Findings are de-duplicated by category; the strongest finding per category is scored.
```

Uncertainties gathered from each analyzer are listed separately.

## Reproducible example (fixtures)

`HoneypotERC20` yields a confirmed honeypot finding (60 pts) and typically scores
in the elevated/high band across a standard analysis. `StandardERC20` yields no
scored findings and scores near zero. Neither figure is a safety guarantee.
