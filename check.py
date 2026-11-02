"""Независимая сверка daily_by_sku.csv: тот же расчёт другим способом (pandas).

Запуск: python check.py [sales.csv] [daily_by_sku.csv]
Нужен pandas: pip install -r requirements-check.txt
"""
import sys

import pandas as pd

sales_path = sys.argv[1] if len(sys.argv) > 1 else "sales.csv"
result_path = sys.argv[2] if len(sys.argv) > 2 else "daily_by_sku.csv"

sales = pd.read_csv(sales_path, dtype=str)
sales = sales.drop_duplicates()  # полные дубли строк
assert sales["order_id"].is_unique, "после удаления полных дублей order_id повторяется"

sales["status"] = sales["status"].str.strip().str.lower().replace({"canceled": "cancelled"})
assert set(sales["status"]) == {"delivered", "cancelled"}, set(sales["status"])

delivered = sales["status"] == "delivered"
sales["revenue"] = 0
sales.loc[delivered, "revenue"] = (
    sales.loc[delivered, "quantity"].astype(int) * sales.loc[delivered, "price"].astype(int)
)

expected = (
    sales.groupby(["sku", "order_date"])
    .agg(orders=("order_id", "count"), revenue=("revenue", "sum"))
    .reset_index()
    .sort_values(["sku", "order_date"])
    .reset_index(drop=True)
)
actual = pd.read_csv(result_path, dtype={"sku": str, "order_date": str})

pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
assert list(actual[["sku", "order_date"]].itertuples(index=False)) == sorted(
    actual[["sku", "order_date"]].itertuples(index=False)
), "строки не отсортированы"

print("Совпадает построчно:", len(actual), "строк")
print("Контрольные цифры:")
print("  уникальных заказов:", len(sales), "| в отчёте:", actual["orders"].sum())
print("  выкуплено заказов:", delivered.sum(), "| отменено:", (~delivered).sum())
print("  выручка всего:", sales["revenue"].sum(), "| в отчёте:", actual["revenue"].sum())
print("Выручка по артикулам:")
print(actual.groupby("sku")["revenue"].sum().to_string())
