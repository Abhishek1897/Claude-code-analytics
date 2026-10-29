# Claude Code for Data Analysis

> From raw, messy data to a professional Trading Desk, built end to end with **Claude Code**, an agentic AI coding assistant.

**Created by:** Abhishek Shinde
**Platform:** Windows 11 · PowerShell · Claude Code v2.1.312

---

## Table of Contents

- [Overview](#overview)
- [What's Inside](#whats-inside)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Modules](#modules)
  - [1. Agentic Data Engineering](#1-agentic-data-engineering)
  - [2. Data Engineering Pipeline](#2-data-engineering-pipeline)
  - [3. The Executive Audit](#3-the-executive-audit)
  - [4. Future Wealth Forecaster](#4-future-wealth-forecaster)
  - [5. Professional Trading Desk](#5-professional-trading-desk)
- [Key Results](#key-results)
- [Command Reference](#command-reference)
- [Troubleshooting](#troubleshooting)
- [Cost Monitoring](#cost-monitoring)
- [Lessons Learned](#lessons-learned)
- [Disclaimer](#disclaimer)

---

## Overview

This project shows how an **AI agent** can take business data through a complete analytics workflow. I described each outcome in plain English, and Claude Code planned the work, wrote and ran the Python scripts, checked the results, and fixed its own mistakes. My role was to:

- Set up the environment.
- Write clear prompts.
- Approve changes.
- Review the output critically.

**Agentic AI, in one line:** a chatbot answers questions; an agent is given a goal and tools, then reads files, writes code, runs it, inspects errors, and iterates until the task is done.

## What's Inside

| Deliverable | Description |
|---|---|
| 🧹 Data cleaning pipeline | Turns messy bank exports into clean, standardized data |
| 📊 Interactive dashboard | Browser-based table with filters, sorting, and KPIs |
| 🔗 Master dataset | Triple join of ledger, budgets, and marketing ROAS |
| 📄 Executive audit PDF | 5-page CFO report with narrative summary and charts |
| 💰 Future Wealth forecaster | Lump-sum and monthly-contribution (DCA) projections |
| 📈 Trading Desk | Bloomberg-style dark dashboard with 14-day RSI signals |

## Project Structure

```
claude-analytics/
├── bank_statement.csv          # 50 rows of deliberately messy bank data
├── clean_bank_data.py          # Reusable cleaning script
├── cleaned_data.csv            # 43 clean rows, ISO dates, no duplicates
├── dashboard.html              # Interactive dashboard (Future Wealth + Trading Desk)
├── ledger_2026.csv             # General-ledger transactions
├── budget_targets.csv          # Monthly budget per department
├── marketing_roas.csv          # Ad spend mapped to attributed revenue
├── build_master_dataset.py     # Automated triple-join script
├── master_dataset.csv          # Consolidated dataset
├── financial_audit_2026.pdf    # Executive audit report
└── wealth_tracker.py           # Portfolio script: forecaster + RSI signal engine
```

## Tech Stack

- **Claude Code**: agentic AI coding assistant (terminal)
- **Python**: pandas, tabulate, FPDF2, Matplotlib/Seaborn
- **HTML / CSS / JavaScript**: dashboards
- **PowerShell**: environment setup and launch
- **Prerequisites**: Node.js, Python (added to PATH), Git

## Getting Started

### 1. Install Claude Code (Windows PowerShell)

```powershell
irm https://claude.ai/install.ps1 | iex
```

Verify the install and find its location:

```powershell
claude --version
(Get-Command claude).Source
```

If `claude` is not recognized, add the install folder to your user PATH, then open a **new** PowerShell window:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:USERPROFILE\.local\bin", "User")
```

### 2. Set up API billing

1. Sign in to the [Claude Console](https://console.anthropic.com) and add credits (the $5 minimum is enough to start).
2. Create a key with **Get API key**.
3. Save it as a user environment variable:

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "paste-your-key-here", "User")
```

In a new window, check that it loaded without printing it:

```powershell
if ($env:ANTHROPIC_API_KEY) { "Key is set" } else { "Key not found" }
```

> ⚠️ **Never commit, screenshot, or share your API key.** If it is ever exposed, revoke it in the Console and create a new one.

### 3. Create a dedicated workspace

```powershell
mkdir claude-analytics
cd claude-analytics
claude
```

When prompted, choose **Yes, I trust this folder**. Trust only the project folder, never your whole user profile.

### 4. Re-run the cleaning pipeline

```powershell
python clean_bank_data.py bank_statement.csv cleaned_data.csv
```

## Modules

Type each prompt directly at Claude Code's `>` prompt, without the `claude` command in front.

### 1. Agentic Data Engineering

**Generate messy data:**
```text
Generate 50 rows of messy bank data where we will have duplicate records and messy date formats... save as bank_statement.csv
```

**Clean and standardize:**
```text
Standardize all dates to YYYY-MM-DD, fill in any missing amounts using the average value, remove duplicates, and save the final output as cleaned_data.csv.
```

**Build a dashboard:**
```text
Create an interactive HTML table to preview all the data in cleaned_data.csv so it can be opened as a dashboard in the browser.
```

### 2. Data Engineering Pipeline

**Triple join:**
```text
Claude, I need to prepare a master dataset for our CFO. Join the ledger with the budget targets so we can see our variance and then map in the marketing performance data.
```

**Terminal preview:**
```text
Claude, do not summarize. Use Python to print the first 10 rows of the master data as a formatted ASCII table using the tabulate library.
```

> Tip: press **Ctrl + O** to expand collapsed output.

### 3. The Executive Audit

**Generate the report:**
```text
Claude, I have the master_dataset.csv. I need you to write a Python script using FPDF to generate a professional PDF financial audit. Start with a one-page summary for the CFO. Highlight any department that is more than 10% over budget in red. Also create a dedicated section for marketing with campaign name, ROAS, and ad spend. Give me a list of top 5 most expensive transactions. Keep design clean, no corporate fluff.
```

**Add the missing written summary:**
```text
I do not see the one-page summary in the report that I asked for. Please include a one-page summary and combine the report you just created with the summary. I want the summary in text.
```

**Add charts:**
```text
Claude, please include several charts, different from the table chart that you have used. I want to see a combination of bar charts and line charts that explain the data. The purpose of the report is to have things summarized and concise.
```

### 4. Future Wealth Forecaster

```text
I want to add a Forecaster to our script. Add a feature where a user can enter either an initial investment (lump sum) or a monthly contribution (DCA). Using a conservative 10% annual growth rate for stocks and 30% for crypto, calculate the projected value after 12 months. Update dashboard.html to show a "Future Wealth" section with the stock and crypto projections side by side.
```

**Math:**
- **Lump sum:** `FV = P × (1 + g)`
- **Monthly contribution (DCA):** `FV = C × ((1 + r)^12 − 1) / r`, where `r = (1 + g)^(1/12) − 1`

### 5. Professional Trading Desk

```text
We are upgrading our tool into a professional Trading Desk. First read @wealth_tracker.py and @dashboard.html; this is our current foundation.

1. Refactor the Python script and add a "Signal" engine that calculates a 14-day RSI (Relative Strength Index) for all 20 assets.
2. Update dashboard.html with a Bloomberg-style dark mode (CSS).
3. If an asset's RSI is below 30, color its row neon green with a "BUY" tag.
4. If an asset's RSI is above 70, color its row red with a "CAUTION" tag.
5. Keep all existing "Future Value" logic exactly as it is.
```

**RSI** = `100 − 100 / (1 + average gain / average loss)` over 14 days.

| RSI | Reading | Dashboard |
|---|---|---|
| < 30 | Oversold | 🟢 Neon green row, `BUY` |
| 30–70 | Neutral | Standard row |
| > 70 | Overbought | 🔴 Red row, `CAUTION` |

## Key Results

**Data cleaning**
- 50 rows in, 43 out. Seven duplicates were removed: five exact copies, one that differed only in spacing and capitalization, and one with the same date written another way.
- All dates were standardized to `YYYY-MM-DD`.
- Amounts were normalized: `($89.99)` became `-89.99`, and currency symbols and separators were removed.
- Two rows were flagged for review instead of guessed: one missing a date, one missing a currency.

**Financial audit FY2026**
- Total spend was **$4.39M** against a **$7.73M** budget (57%).
- **9 of 10** departments stayed within budget.
- **Marketing** was **31.2% over budget**: $866K against $660K.
- Marketing earned a blended **ROAS of 5.32x** ($4.61M attributed revenue).
  - Best channel: Mailchimp at 9.7x. Worst: TikTok Ads at 3.5x.
- The top 5 transactions were all Azure payments. Azure costs rose 89% over the year.

## Command Reference

| Command | Where | Purpose |
|---|---|---|
| `irm https://claude.ai/install.ps1 \| iex` | PowerShell | Install Claude Code |
| `Get-Command claude` / `where.exe claude` | PowerShell | Show install location |
| `claude --help` / `claude --version` | PowerShell | Verify install |
| `claude` | PowerShell | Start Claude Code in current folder |
| `/status` | Claude Code | Account, auth method, model |
| `/logout` / `/login` | Claude Code | Switch account or billing |
| `/model` | Claude Code | Switch between Opus, Sonnet, Haiku |
| `/cost` | Claude Code | Current session spend |
| `/exit` | Claude Code | Quit |
| `!dir` | Claude Code | Run a shell command |
| `@file` | Claude Code | Reference a file in a prompt |
| `Ctrl + O` | Claude Code | Expand collapsed output |

## Troubleshooting

| Problem | Fix |
|---|---|
| *Your organization has disabled Claude subscription access for Claude Code* | Use an API key: set `ANTHROPIC_API_KEY`, then `/logout`, `/exit`, and restart `claude` |
| Same message after setting the key | An old sign-in is taking priority. Run `/logout` and restart |
| *Remote managed settings failed to load (403)* | Harmless warning; Claude Code runs with default settings |
| `claude` not recognized | Add `%USERPROFILE%\.local\bin` to PATH and open a new terminal |
| Typed `claude "..."` at the `>` prompt | Inside Claude Code, type the request directly |

## Cost Monitoring

- Run `/cost` during a session, or check the Claude Console usage page.
- **Input tokens** (reading files and prompts) cost less than **output tokens** (writing code and reports).
- Long sessions get more expensive because Claude re-reads the conversation history. Start a fresh session for each new task.
- Use `/model` to switch to Sonnet or Haiku for simpler jobs.

## Lessons Learned

1. **Use a dedicated workspace.** Trust only the project folder.
2. **Know where commands go.** `claude` runs in PowerShell, requests go at the `>` prompt, and `/commands` control the session.
3. **Protect your API key.** Keep it in an environment variable and nowhere else.
4. **Be specific in prompts.** Name files, formats, thresholds, and what must *not* change.
5. **Review and iterate.** The audit improved over three prompts.
6. **Ask for scripts, not one-off answers.** A reusable script turns a one-time analysis into a pipeline.
7. **Keep judgment human.** Claude flagged ambiguous data; deciding what to do with it is the analyst's call.

## Disclaimer

The forecasting growth rates (10% stocks, 30% crypto) are fixed assumptions for illustration. The RSI tags are educational signals. **Nothing in this project is investment advice.** All datasets are synthetic, generated for practice.

---

**Author:** Abhishek Shinde · Built with [Claude Code](https://claude.com/claude-code)
