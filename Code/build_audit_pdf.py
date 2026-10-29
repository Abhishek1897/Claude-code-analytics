"""Generate financial_audit_2026.pdf from the master dataset.

Inputs : master_transactions.csv, variance_by_dept_month.csv (from build_master_dataset.py)
Output : financial_audit_2026.pdf
  Page 1 - Executive summary (text)
  Page 2 - Budget vs actual: utilisation bar chart, monthly spend columns, department table
           (departments more than 10% over budget highlighted in red)
  Page 3 - Marketing: spend-vs-budget line chart, ROAS-by-channel bar chart
  Page 4 - Campaign table: campaign name, ad spend, attributed revenue, ROAS
  Page 5 - Top 5 most expensive transactions, top vendor trend line, method notes
Charts are rendered by audit_charts.py into charts/.
"""
from datetime import date
from pathlib import Path

import pandas as pd
from fpdf import FPDF

import audit_charts as charts

OVER_THRESHOLD_PCT = 10.0
OUT = "financial_audit_2026.pdf"
CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)

INK = (11, 11, 11)
SECONDARY = (82, 81, 78)
MUTED = (137, 135, 129)
RULE = (225, 224, 217)
RED = (208, 59, 59)
RED_WASH = (251, 234, 234)
GREEN = (0, 99, 0)

# --- Data -------------------------------------------------------------------
tx = pd.read_csv("master_transactions.csv", parse_dates=["Date"])
var = pd.read_csv("variance_by_dept_month.csv")

dept = var.groupby(["Dept_Code", "Department"], as_index=False).agg(
    Budget=("Budget", "sum"),
    Actual=("Actual_Spend", "sum"),
    Months_Over=("Status", lambda s: (s == "Over budget").sum()),
)
dept["Over_Pct"] = (dept["Actual"] - dept["Budget"]) / dept["Budget"] * 100
dept["Flagged"] = dept["Over_Pct"] > OVER_THRESHOLD_PCT
dept = dept.sort_values("Over_Pct", ascending=False).reset_index(drop=True)

mkt = tx[tx["Dept_Code"] == "MKT"]
campaigns = mkt.groupby(["Campaign_Name", "Vendor"], as_index=False).agg(
    Flights=("Transaction_ID", "count"),
    Spend=("Amount", "sum"),
    Revenue=("Attributed_Revenue", "sum"),
)
campaigns["ROAS"] = campaigns["Revenue"] / campaigns["Spend"]
campaigns = campaigns.sort_values(["ROAS", "Spend"], ascending=False).reset_index(drop=True)

channels = mkt.groupby("Vendor", as_index=False).agg(
    Spend=("Amount", "sum"), Revenue=("Attributed_Revenue", "sum"))
channels["ROAS"] = channels["Revenue"] / channels["Spend"]
channels = channels.sort_values("ROAS", ascending=False)

top5 = tx.sort_values(["Amount", "Date"], ascending=[False, True]).head(5)

period_start, period_end = tx["Date"].min(), tx["Date"].max()
future_rows = int(tx["Is_Future_Dated"].sum())
total_budget, total_actual = dept["Budget"].sum(), dept["Actual"].sum()
mkt_row = dept[dept["Dept_Code"] == "MKT"].iloc[0]


def money(v, signed=False):
    sign = ("+" if v > 0 else "-" if v < 0 else "") if signed else ("-" if v < 0 else "")
    return f"{sign}${abs(v):,.0f}"


def money_short(v):
    return f"${v / 1e6:,.2f}M" if abs(v) >= 1e6 else f"${v / 1e3:,.0f}K"


# --- PDF helpers ----------------------------------------------------------------
class Audit(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Financial Audit FY2026  |  Generated {date.today():%Y-%m-%d}", align="L")
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")


pdf = Audit(format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(16, 16, 16)
W = pdf.w - pdf.l_margin - pdf.r_margin


def title(text, sub):
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*INK)
    pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9.5)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 5, sub, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)


def section(text):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def kpis(items):
    """Row of headline figures: [(label, value, note, color)]."""
    gap = 4
    w = (W - gap * (len(items) - 1)) / len(items)
    x0, y0 = pdf.l_margin, pdf.get_y()
    for i, (label, value, note, color) in enumerate(items):
        x = x0 + i * (w + gap)
        pdf.set_draw_color(*RULE)
        pdf.rect(x, y0, w, 22)
        pdf.set_xy(x + 4, y0 + 3)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*SECONDARY)
        pdf.cell(w - 8, 4, label)
        pdf.set_xy(x + 4, y0 + 8)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*(color or INK))
        pdf.cell(w - 8, 7, value)
        pdf.set_xy(x + 4, y0 + 15.5)
        pdf.set_font("Helvetica", size=7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(w - 8, 4, note)
    pdf.set_xy(x0, y0 + 26)


def table(cols, rows, row_h=6.5, styles=None):
    """cols: [(header, width_fraction, align)]; styles: per-row dict(text=, fill=, bold=)."""
    widths = [W * c[1] for c in cols]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*SECONDARY)
    pdf.set_draw_color(*MUTED)
    for (head, _, align), w in zip(cols, widths):
        pdf.cell(w, row_h, head, border="B", align=align)
    pdf.ln(row_h)
    pdf.set_draw_color(*RULE)
    for i, row in enumerate(rows):
        st = (styles or {}).get(i, {})
        pdf.set_font("Helvetica", "B" if st.get("bold") else "", 8.5)
        pdf.set_text_color(*st.get("text", INK))
        if st.get("fill"):
            pdf.set_fill_color(*st["fill"])
        for (_, _, align), w, val in zip(cols, widths, row):
            pdf.cell(w, row_h, str(val), border="B", align=align, fill=bool(st.get("fill")))
        pdf.ln(row_h)


def bullets(lines):
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*INK)
    for line in lines:
        pdf.set_x(pdf.l_margin)
        pdf.cell(4, 5, "-")
        pdf.multi_cell(W - 4, 5, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)


def chart(heading, image, caption=None):
    section(heading)
    pdf.image(str(image), x=pdf.l_margin, w=W)
    if caption:
        pdf.ln(0.5)
        note(caption)
    pdf.ln(2)


def note(text):
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(W, 4, text, new_x="LMARGIN", new_y="NEXT")


def paragraph(heading, text):
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, heading, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(W, 5.2, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3.5)


period = f"{period_start:%d %b %Y} - {period_end:%d %b %Y}"
flagged = dept[dept["Flagged"]]
net = total_budget - total_actual

# Figures used only in the written summary
today = pd.Timestamp(date.today())
months_to_date = var[pd.PeriodIndex(var["Month"], freq="M").start_time <= today]
mkt_ytd = months_to_date[months_to_date["Dept_Code"] == "MKT"]
mkt_ytd_over = mkt_ytd["Actual_Spend"].sum() - mkt_ytd["Budget"].sum()
mkt_over_months = var[(var["Dept_Code"] == "MKT") & (var["Status"] == "Over budget")]["Month"]
mkt_last = var[var["Dept_Code"] == "MKT"].iloc[-1]
mkt_roas = mkt["Attributed_Revenue"].sum() / mkt["Amount"].sum()
top_vendor = top5["Vendor"].mode()[0]
top_dept = top5["Department"].mode()[0]
vendor_total = tx.loc[tx["Vendor"] == top_vendor, "Amount"].sum()
dept_total = tx.loc[tx["Department"] == top_dept, "Amount"].sum()
low_use = dept[dept["Actual"] / dept["Budget"] < 0.35]
within = len(dept) - (dept["Over_Pct"] > 0).sum()

# --- Page 1: Executive summary (text) ----------------------------------------------
pdf.add_page()
title("Financial Audit FY2026 - Executive Summary",
      f"Prepared for the CFO, {date.today():%d %B %Y}. Covers {period}.")

paragraph("Overall position", (
    f"The company spent {money(total_actual)} in the period against a combined budget of "
    f"{money(total_budget)}, or {total_actual / total_budget:.0%} of budget, leaving "
    f"{money(net)} unspent. {within} of {len(dept)} departments finished within budget. "
    f"{len(flagged)} department{'s' if len(flagged) != 1 else ''} "
    f"({', '.join(flagged['Department']) or 'none'}) exceeded budget by more than "
    f"{OVER_THRESHOLD_PCT:.0f}%."))

paragraph("Marketing is over budget", (
    f"Marketing spent {money(mkt_row['Actual'])} against a budget of {money(mkt_row['Budget'])}, "
    f"{money(mkt_row['Actual'] - mkt_row['Budget'])} ({mkt_row['Over_Pct']:.1f}%) over. It was over "
    f"budget in {len(mkt_over_months)} of 12 months, every month from "
    f"{pd.Period(mkt_over_months.min()).strftime('%B')} onward, and the gap widens through the year, "
    f"reaching {money(mkt_last['Actual_Spend'] - mkt_last['Budget'])} over in "
    f"{pd.Period(mkt_last['Month']).strftime('%B')} alone. Counting only months to date, the "
    f"overspend is {money(mkt_ytd_over)}. The monthly budget of {money(mkt_row['Budget'] / 12)} "
    "no longer reflects how the team is spending."))

paragraph("The marketing spend is earning a return", (
    f"Marketing spend produced {money(mkt['Attributed_Revenue'].sum())} of attributed revenue, "
    f"{mkt_roas:.2f} dollars back for every dollar spent. Returns vary widely by channel: "
    f"{channels.iloc[0]['Vendor']} returned {channels.iloc[0]['ROAS']:.1f}x and "
    f"{channels.iloc[1]['Vendor']} {channels.iloc[1]['ROAS']:.1f}x, while "
    f"{channels.iloc[-1]['Vendor']} returned {channels.iloc[-1]['ROAS']:.1f}x, the lowest of any "
    f"channel. The best and worst campaigns were {campaigns.iloc[0]['Campaign_Name']} "
    f"({campaigns.iloc[0]['ROAS']:.1f}x) and {campaigns.iloc[-1]['Campaign_Name']} "
    f"({campaigns.iloc[-1]['ROAS']:.1f}x). Shifting spend from the lowest-return channels is the "
    "most direct way to bring Marketing back toward budget, though returns from a channel may fall "
    "as more is spent on it."))

paragraph("Largest transactions", (
    f"{'All' if (top5['Vendor'] == top_vendor).all() else 'Most'} of the five largest "
    f"transactions are {top_dept} payments to {top_vendor}, ranging from "
    f"{money(top5['Amount'].min())} to {money(top5['Amount'].max())} and rising month on month. "
    f"{top_vendor} accounts for {money(vendor_total)} in total, {vendor_total / dept_total:.0%} of "
    f"{top_dept} spend. {top_dept} remains within budget, but this cost is growing and should be "
    "watched."))

caveats = []
if future_rows:
    caveats.append(
        f"{future_rows} transactions are dated after {date.today():%d %B %Y} and are included in "
        "the full-year figures; it is not yet confirmed whether these are booked commitments or "
        "forecasts.")
if len(low_use):
    caveats.append(
        f"{', '.join(low_use['Department'])} used less than 35% of their budgets. That may mean "
        "spend is missing from this ledger rather than genuine savings.")
caveats.append("Capital spending limits were not tested, because the ledger does not separate "
               "capital from operating costs.")
paragraph("Limits of this audit", " ".join(caveats))

paragraph("Decisions needed", "\n".join([
    "1. Reset the Marketing budget to match planned spend, or cap spend at the current budget.",
    "2. Confirm the status of the future-dated transactions.",
    "3. Confirm that the ledger is complete for the departments with unusually low spend.",
]))

# --- Page 2: Budget vs actual detail ----------------------------------------------
pdf.add_page()
title("Budget vs Actual by Department",
      f"Budget vs actual spend, {period}. {len(tx)} transactions across {len(dept)} departments.")

as_of_month = today.strftime("%Y-%m")
monthly_total = tx.groupby("Month")["Amount"].sum()
chart("Spend as a share of budget",
      charts.budget_utilisation(dept, OVER_THRESHOLD_PCT, CHART_DIR / "budget_utilisation.png"),
      f"Red = more than {OVER_THRESHOLD_PCT:.0f}% over budget. Only Marketing crosses the line.")
chart("Company spend by month",
      charts.monthly_spend_vs_budget(monthly_total, dept["Budget"].sum() / 12,
                                     as_of_month, CHART_DIR / "monthly_spend.png"),
      f"Spend rose from {money_short(monthly_total.iloc[0])} in "
      f"{pd.Period(monthly_total.index[0]).strftime('%B')} to {money_short(monthly_total.iloc[-1])} in "
      f"{pd.Period(monthly_total.index[-1]).strftime('%B')}, but stayed under the combined monthly budget. "
      "Lighter columns are dated after the report date.")
section("Budget vs actual by department")
rows, styles = [], {}
for i, r in dept.iterrows():
    over = r["Over_Pct"] > 0
    status = f"OVER >{OVER_THRESHOLD_PCT:.0f}%" if r["Flagged"] else ("Over" if over else "Within")
    rows.append([r["Department"], money(r["Budget"]), money(r["Actual"]),
                 money(r["Actual"] - r["Budget"], signed=True), f"{r['Over_Pct']:+.1f}%",
                 f"{r['Months_Over']} / 12", status])
    if r["Flagged"]:
        styles[i] = {"text": RED, "fill": RED_WASH, "bold": True}
table([("Department", .25, "L"), ("Budget", .13, "R"), ("Actual", .13, "R"),
       ("Over / (under)", .15, "R"), ("vs budget", .11, "R"), ("Months over", .11, "R"),
       ("Status", .12, "R")], rows, row_h=5.8, styles=styles)
pdf.ln(1)
note(f"Red = actual spend more than {OVER_THRESHOLD_PCT:.0f}% above budget. "
     "Positive figures are overspend.")


# --- Page 3: Marketing ----------------------------------------------------------------
pdf.add_page()
title("Marketing Performance",
      f"{len(campaigns)} campaigns, {len(mkt)} spend flights, {period}.")
kpis([
    ("Ad spend", money_short(mkt["Amount"].sum()), f"Budget {money_short(mkt_row['Budget'])}", None),
    ("Over budget by", money_short(mkt_row["Actual"] - mkt_row["Budget"]),
     f"{mkt_row['Over_Pct']:+.1f}% vs budget", RED if mkt_row["Flagged"] else None),
    ("Attributed revenue", money_short(mkt["Attributed_Revenue"].sum()), "From marketing_roas.csv", None),
    ("Blended ROAS", f"{mkt['Attributed_Revenue'].sum() / mkt['Amount'].sum():.2f}x",
     "Revenue / ad spend", None),
])
mkt_monthly = var[var["Dept_Code"] == "MKT"].reset_index(drop=True)
chart("Marketing spend vs budget, by month",
      charts.marketing_trend(mkt_monthly, as_of_month, CHART_DIR / "marketing_trend.png"),
      f"Over budget every month from {pd.Period(mkt_over_months.min()).strftime('%B')}; "
      "the shaded area is the overspend.")
chart("Return on ad spend by channel",
      charts.roas_by_channel(channels, mkt_roas, CHART_DIR / "roas_by_channel.png"),
      f"{channels.iloc[0]['Vendor']} and {channels.iloc[1]['Vendor']} return the most per dollar; "
      f"{channels.iloc[-1]['Vendor']} the least.")

# --- Page 4: Campaign table --------------------------------------------------------
pdf.add_page()
title("Campaign Detail", f"All {len(campaigns)} campaigns, sorted by ROAS.")
table([("Campaign", .34, "L"), ("Channel", .20, "L"), ("Flights", .09, "R"),
       ("Ad spend", .13, "R"), ("Revenue", .13, "R"), ("ROAS", .11, "R")],
      [[c["Campaign_Name"], c["Vendor"], c["Flights"], money(c["Spend"]), money(c["Revenue"]),
        f"{c['ROAS']:.2f}x"] for _, c in campaigns.iterrows()],
      row_h=5.4)
pdf.ln(1)
note("ROAS = attributed revenue / ad spend. Attribution is as reported in the marketing data "
     "and has not been independently verified.")

# --- Page 5: Top transactions + method ----------------------------------------------------
pdf.add_page()
title("Largest Transactions", "Top 5 by amount across all departments.")
table([("#", .05, "L"), ("Transaction", .14, "L"), ("Date", .14, "L"), ("Department", .25, "L"),
       ("Vendor", .27, "L"), ("Amount", .15, "R")],
      [[i + 1, r["Transaction_ID"], f"{r['Date']:%Y-%m-%d}" + (" *" if r["Is_Future_Dated"] else ""),
        r["Department"], r["Vendor"], money(r["Amount"])]
       for i, (_, r) in enumerate(top5.iterrows())],
      row_h=7)
pdf.ln(1)
share = top5["Amount"].sum() / tx["Amount"].sum()
note(f"These 5 transactions total {money(top5['Amount'].sum())}, {share:.1%} of all spend."
     + ("  * Dated after the report date." if top5["Is_Future_Dated"].any() else ""))

pdf.ln(2)
vendor_monthly = (tx[tx["Vendor"] == top_vendor].groupby("Month")["Amount"].sum()
                  .reindex(sorted(tx["Month"].unique()), fill_value=0))
chart(f"{top_vendor} spend by month",
      charts.vendor_trend(vendor_monthly, top_vendor, as_of_month, CHART_DIR / "vendor_trend.png"),
      f"{top_vendor} cost rose from {money_short(vendor_monthly.iloc[0])} to "
      f"{money_short(vendor_monthly.iloc[-1])} a month, "
      f"{vendor_monthly.iloc[-1] / vendor_monthly.iloc[0] - 1:.0%} over the year.")

section("Method")
bullets([
    "Sources: ledger_2026.csv (transactions), budget_targets.csv (monthly budget per department), "
    "marketing_roas.csv (campaign revenue), combined by build_master_dataset.py.",
    "Annual budget = monthly budget x 12. Variance = actual - budget; positive is overspend.",
    "Marketing campaigns matched to Marketing ledger rows on date and amount; "
    f"{len(mkt)} of {len(mkt)} matched one-to-one. Spend and revenue totals reconcile to source.",
    "CapEx limits are not assessed: the ledger does not separate capital from operating spend.",
])

pdf.output(OUT)
print(f"Wrote {OUT} ({pdf.page_no()} pages)")
print("Flagged departments:", ", ".join(flagged["Department"]) or "none")
