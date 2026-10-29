"""Build the CFO master dataset from the ledger, budget targets and marketing data.

Inputs : ledger_2026.csv, budget_targets.csv, marketing_roas.csv
Outputs: master_transactions.csv      - one row per ledger transaction, enriched
         variance_by_dept_month.csv   - budget vs actual per department per month
         master_dataset.xlsx          - all views as sheets (for the CFO)

Variance convention: Variance = Budget - Actual, so positive = under budget.
"""
from datetime import date

import pandas as pd

AS_OF = pd.Timestamp(date.today())

ledger = pd.read_csv("ledger_2026.csv", parse_dates=["date"])
budget = pd.read_csv("budget_targets.csv")
mkt = pd.read_csv("marketing_roas.csv", parse_dates=["Date"])

# --- Integrity checks: fail loudly rather than build a wrong report ----------
assert not ledger["transaction_id"].duplicated().any(), "duplicate transaction IDs"
assert not budget["Dept_code"].duplicated().any(), "duplicate budget departments"
unknown = set(ledger["dept_code"]) - set(budget["Dept_code"])
assert not unknown, f"ledger departments missing from budget: {unknown}"
assert not mkt.duplicated(["Date", "Ad_Spend"]).any(), "ambiguous marketing join key"

# --- Transaction-level master -------------------------------------------------
tx = ledger.merge(
    budget[["Dept_code", "Department_name"]],
    left_on="dept_code", right_on="Dept_code", how="left", validate="many_to_one",
).drop(columns="Dept_code")

# Marketing rows carry no shared ID; each MKT ledger entry matches exactly one
# campaign on (date, spend amount).
is_mkt = tx["dept_code"] == "MKT"
mkt_join = tx[is_mkt].merge(
    mkt, left_on=["date", "amount"], right_on=["Date", "Ad_Spend"],
    how="outer", indicator=True, validate="one_to_one",
)
unmatched = mkt_join[mkt_join["_merge"] != "both"]
assert unmatched.empty, f"marketing rows that did not match the ledger:\n{unmatched}"

tx = tx.merge(
    mkt_join[["transaction_id", "Campaign_Name", "Attributed_Revenue"]],
    on="transaction_id", how="left",
)
tx["ROAS"] = (tx["Attributed_Revenue"] / tx["amount"]).round(2).where(is_mkt)
tx["month"] = tx["date"].dt.to_period("M").astype(str)
tx["is_future_dated"] = tx["date"] > AS_OF
tx = tx.rename(columns={
    "transaction_id": "Transaction_ID", "date": "Date", "month": "Month",
    "dept_code": "Dept_Code", "Department_name": "Department", "vendor": "Vendor",
    "amount": "Amount", "is_future_dated": "Is_Future_Dated",
})[["Transaction_ID", "Date", "Month", "Dept_Code", "Department", "Vendor", "Amount",
    "Campaign_Name", "Attributed_Revenue", "ROAS", "Is_Future_Dated"]]

# --- Budget vs actual by department x month ------------------------------------
months = pd.period_range(tx["Date"].min(), tx["Date"].max(), freq="M").astype(str)
grid = pd.MultiIndex.from_product([budget["Dept_code"], months], names=["Dept_Code", "Month"])

actuals = tx.groupby(["Dept_Code", "Month"]).agg(
    Actual_Spend=("Amount", "sum"),
    Transactions=("Transaction_ID", "count"),
    Attributed_Revenue=("Attributed_Revenue", "sum"),
).reindex(grid, fill_value=0).reset_index()   # months with no spend show as 0

var = actuals.merge(budget, left_on="Dept_Code", right_on="Dept_code").drop(columns="Dept_code")
var = var.rename(columns={"Department_name": "Department", "Monthly_Budget": "Budget"})
var["Variance"] = var["Budget"] - var["Actual_Spend"]
var["Variance_Pct"] = (var["Variance"] / var["Budget"] * 100).round(1)
var["Status"] = var["Variance"].map(lambda v: "Over budget" if v < 0 else "Within budget")
var["ROAS"] = (var["Attributed_Revenue"] / var["Actual_Spend"]).round(2).where(var["Dept_Code"] == "MKT")
var["Attributed_Revenue"] = var["Attributed_Revenue"].where(var["Dept_Code"] == "MKT")
var["Is_Future_Month"] = pd.PeriodIndex(var["Month"], freq="M").start_time > AS_OF
var = var[["Dept_Code", "Department", "Month", "Budget", "Actual_Spend", "Variance",
           "Variance_Pct", "Status", "Transactions", "Attributed_Revenue", "ROAS",
           "Is_Future_Month"]].sort_values(["Dept_Code", "Month"]).reset_index(drop=True)

# --- Annual summary per department ----------------------------------------------
n_months = len(months)
annual = var.groupby(["Dept_Code", "Department"], as_index=False).agg(
    Budget=("Budget", "sum"), Actual_Spend=("Actual_Spend", "sum"),
    Months_Over_Budget=("Status", lambda s: (s == "Over budget").sum()),
    Attributed_Revenue=("Attributed_Revenue", "sum"),
)
annual["Variance"] = annual["Budget"] - annual["Actual_Spend"]
annual["Variance_Pct"] = (annual["Variance"] / annual["Budget"] * 100).round(1)
annual["Status"] = annual["Variance"].map(lambda v: "Over budget" if v < 0 else "Within budget")
annual["ROAS"] = (annual["Attributed_Revenue"] / annual["Actual_Spend"]).round(2).where(annual["Dept_Code"] == "MKT")
annual["Attributed_Revenue"] = annual["Attributed_Revenue"].where(annual["Dept_Code"] == "MKT")
annual = annual.merge(budget[["Dept_code", "CapEx_Limit"]], left_on="Dept_Code", right_on="Dept_code").drop(columns="Dept_code")
annual = annual[["Dept_Code", "Department", "Budget", "Actual_Spend", "Variance", "Variance_Pct",
                 "Status", "Months_Over_Budget", "Attributed_Revenue", "ROAS", "CapEx_Limit"]]

# --- Campaign performance -------------------------------------------------------
campaigns = tx[tx["Dept_Code"] == "MKT"].groupby(["Campaign_Name", "Vendor"], as_index=False).agg(
    Flights=("Transaction_ID", "count"), Ad_Spend=("Amount", "sum"),
    Attributed_Revenue=("Attributed_Revenue", "sum"),
    First_Date=("Date", "min"), Last_Date=("Date", "max"),
)
campaigns["ROAS"] = (campaigns["Attributed_Revenue"] / campaigns["Ad_Spend"]).round(2)
campaigns = campaigns.sort_values("ROAS", ascending=False).reset_index(drop=True)

# --- Reconciliation: totals must survive every join -----------------------------
assert tx["Amount"].sum() == ledger["amount"].sum()
assert var["Actual_Spend"].sum() == ledger["amount"].sum()
assert tx["Attributed_Revenue"].sum() == mkt["Attributed_Revenue"].sum()
assert len(tx) == len(ledger)

# --- Write outputs ----------------------------------------------------------------
tx.to_csv("master_transactions.csv", index=False, date_format="%Y-%m-%d")
var.to_csv("variance_by_dept_month.csv", index=False)

notes = pd.DataFrame({"Note": [
    f"Built {AS_OF:%Y-%m-%d} from ledger_2026.csv, budget_targets.csv, marketing_roas.csv.",
    "Variance = Budget - Actual. Positive = under budget; negative = over budget.",
    "Monthly budget is the Monthly_Budget target; annual budget = monthly x "
    f"{n_months} months.",
    "Marketing campaigns are matched to MKT ledger rows on date + spend amount "
    f"({is_mkt.sum()} of {len(mkt)} matched, 1:1).",
    "ROAS = Attributed_Revenue / spend (Marketing only).",
    f"{int(tx['Is_Future_Dated'].sum())} ledger rows are dated after {AS_OF:%Y-%m-%d} "
    "(flagged Is_Future_Dated) - confirm whether these are booked commitments or forecasts.",
    "CapEx_Limit is carried for reference only; the ledger does not mark CapEx vs OpEx.",
]})

with pd.ExcelWriter("master_dataset.xlsx", engine="openpyxl", datetime_format="yyyy-mm-dd") as xw:
    for name, frame in [("Summary_by_Dept", annual), ("Variance_Dept_Month", var),
                        ("Campaign_ROAS", campaigns), ("Transactions", tx), ("Notes", notes)]:
        frame.to_excel(xw, sheet_name=name, index=False)
        ws = xw.sheets[name]
        ws.freeze_panes = "A2"
        for col in ws.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(width + 2, 90)

print(f"Transactions: {len(tx)} rows | Variance grid: {len(var)} rows | Campaigns: {len(campaigns)}")
print(f"Future-dated ledger rows (after {AS_OF:%Y-%m-%d}): {int(tx['Is_Future_Dated'].sum())}")
print("\nAnnual summary:")
print(annual.to_string(index=False))
print("\nMonths over budget:", (var["Status"] == "Over budget").sum(), "of", len(var))
