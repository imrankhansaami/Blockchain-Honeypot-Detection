# Example reports

These files are **real output** produced by
`scripts/generate_example_report.py`, which deploys the `HoneypotERC20` fixture
onto a local Anvil with the mock DEX, performs an actual buy/sell simulation, and
runs the honeypot / tax / owner / risk analyzers.

- `example-honeypot.json` — machine-readable report
- `example-honeypot.html` — human-readable report
- `example-honeypot.pdf` — PDF report

The token is a deliberately malicious **test fixture**, not a real token. The
report demonstrates the format and the evidence the tool records: a confirmed
`honeypot.cannot_sell` finding sourced from simulation, an effective-tax result,
owner privileges, and an explainable risk score.

Regenerate with:

```bash
python scripts/generate_example_report.py
```
