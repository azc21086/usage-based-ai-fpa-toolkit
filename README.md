# Usage-Based AI FP&A Toolkit

A free toolkit for planning usage-based cloud and AI products. It links usage to revenue, LLM cost, cloud cost and gross margin, and shows ROI as a risk-adjusted range instead of a single number.

Companion to: Chopra, A. (2026). *Financial Planning for Agentic & AI Systems: Managing Volatility in the Age of Autonomy.* California Management Review Insights.
https://cmr.berkeley.edu/2026/02/financial-planning-for-agentic-ai-systems-managing-volatility-in-the-age-of-autonomy/

Version 1.0.0 | License: MIT | All example data is synthetic and illustrative.

## What is in the box

| Folder / file | What it is |
|---|---|
| `spreadsheet/Usage_Based_AI_FPA_Model.xlsx` | Excel model: README, Methodology_Data, Inputs, three monthly scenario tabs (Low, Base, High), Summary with charts. No macros. |
| `python/agentic_ai_fpa_model.py` | Same model in Python (numpy and pandas only), plus an optional Monte Carlo run. |
| `inputs_template.json` | The inputs, shared by the script and the LLM package. Matches the Inputs sheet. |
| `llm/SKILL.md` and `llm/prompt.md` | Method and ready-to-paste instructions for a custom GPT (or similar assistant) to build, edit and sense-check your own models. |
| `examples/` | Expected results for the default inputs, so you can confirm everything works. |
| `LICENSE`, `CITATION.cff` | MIT licence and citation metadata. |

## The model in one paragraph

Customers x interactions per customer x tokens per interaction gives usage. Usage x price (with a prepaid discount on part of the volume, plus an optional subscription fee) gives revenue. Tokens x provider cost x (1 - efficiency gain) gives LLM cost. Interactions x fully loaded cloud cost (compute + storage + network, per 1,000 interactions) x (1 - discount) gives cloud cost. Gross margin is revenue minus those costs and a small other-cost line. ROI is shown as a corridor: the ceiling is standard ROI, the floor applies a risk factor built from technical, data readiness and adoption haircuts. Three scenarios (Low = conservative, Base, High = optimistic) differ only in five levers.

## Quick start

### Spreadsheet
1. Open the workbook and read the README and Methodology_Data tabs.
2. Edit only blue-on-yellow cells on the Inputs tab. Check that the input checks show OK.
3. Read the Summary tab: ROI corridor, payback month, adoption dip, annual results, cost mix, unit cost versus total spend.

Google Sheets users: File > Import the .xlsx.

### Python
```bash
pip install -r python/requirements.txt
python python/agentic_ai_fpa_model.py --config inputs_template.json --out results
python python/agentic_ai_fpa_model.py --config inputs_template.json --out results --monte-carlo 5000
```
Edit `inputs_template.json` (or copy it) with your own numbers. CSV files are written to the output folder.

### LLM package
Follow `llm/prompt.md` to create a custom GPT: paste the instructions, upload `SKILL.md`, `inputs_template.json`, the Python script and the workbook, and enable code execution. Then ask it to build a model from your numbers.

## Expected results with the default inputs

The spreadsheet and the script were cross-checked line by line and agree to rounding. The default inputs should reproduce:

| Scenario | 36M cumulative gross margin | ROI floor (risk-adjusted) | ROI ceiling (standard) | Payback month | Year 3 gross margin % |
|---|---|---|---|---|---|
| Low | $751,854 | -31.0% | 0.2% | 36 | 46.7% |
| Base | $1,570,740 | 44.2% | 109.4% | 26 | 59.2% |
| High | $3,275,287 | 200.7% | 336.7% | 21 | 69.0% |

More detail is in `examples/`. The Monte Carlo file is approximate and depends on the random seed (42 by default).

## Limits of version 1

One blended cloud discount (no commitment minimum or take-or-pay shortfall); constant tokens per interaction; constant efficiency gain applied to LLM cost only; no seasonality; three discrete scenarios; gross margin is the benefit (no operating expenses); single currency. See the Methodology_Data tab for the full list and ideas for next versions.

## Important

This toolkit is decision support. Accountability for decisions stays with the people using it. It is not financial advice and not an audited forecast. Example numbers are synthetic and do not represent any company. Replace them with your own data.

## How to cite

Chopra, A. (2026). *Usage-Based AI FP&A Toolkit* (v1.0.0) [Software]. Companion to "Financial Planning for Agentic & AI Systems: Managing Volatility in the Age of Autonomy", California Management Review Insights. Add the DOI or repository link here once published.
