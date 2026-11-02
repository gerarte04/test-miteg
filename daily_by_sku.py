"""Считает заказы и выручку по артикулу за каждый день из выгрузки sales.csv.

Запуск: python daily_by_sku.py [входной.csv] [выходной.csv]
"""
import argparse
import csv
from collections import defaultdict

# Опечатки в статусах, которые встречаются в выгрузке, помимо регистра и пробелов.
STATUS_ALIASES = {"canceled": "cancelled"}
KNOWN_STATUSES = {"delivered", "cancelled"}


def normalize_status(raw):
    status = raw.strip().lower()
    return STATUS_ALIASES.get(status, status)


def read_orders(path):
    """Читает выгрузку и возвращает заказы без дублей: {order_id: строка}.

    Всё, что нельзя исправить однозначно, останавливает скрипт с ошибкой,
    чтобы неверные данные не попали в отчёт молча.
    """
    orders = {}
    report = {"rows": 0, "duplicates": 0, "fixed_statuses": 0, "empty_quantity": 0}

    with open(path, encoding="utf-8", newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            report["rows"] += 1

            status = normalize_status(row["status"])
            if status not in KNOWN_STATUSES:
                raise ValueError(f"строка {line_no}: неизвестный статус {row['status']!r}")
            if status != row["status"]:
                report["fixed_statuses"] += 1
            row["status"] = status

            if not row["quantity"].strip():
                # Для отменённого заказа количество не нужно: в выручку он не идёт.
                if status == "delivered":
                    raise ValueError(f"строка {line_no}: у выкупленного заказа нет quantity")
                report["empty_quantity"] += 1

            order_id = row["order_id"]
            if order_id in orders:
                if orders[order_id] != row:
                    raise ValueError(f"строка {line_no}: заказ {order_id} повторяется с другими данными")
                report["duplicates"] += 1
                continue
            orders[order_id] = row

    return orders, report


def aggregate(orders):
    """Возвращает {(sku, order_date): [orders, revenue]}."""
    totals = defaultdict(lambda: [0, 0])
    for order in orders.values():
        key = (order["sku"], order["order_date"])
        totals[key][0] += 1
        if order["status"] == "delivered":
            totals[key][1] += int(order["quantity"]) * int(order["price"])
    return totals


def write_result(totals, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "order_date", "orders", "revenue"])
        for (sku, day), (orders_count, revenue) in sorted(totals.items()):
            writer.writerow([sku, day, orders_count, revenue])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="sales.csv")
    parser.add_argument("output", nargs="?", default="daily_by_sku.csv")
    args = parser.parse_args()

    orders, report = read_orders(args.input)
    totals = aggregate(orders)
    write_result(totals, args.output)

    print(f"Прочитано строк: {report['rows']}")
    print(f"Удалено дублей: {report['duplicates']}")
    print(f"Исправлено статусов: {report['fixed_statuses']}")
    print(f"Отменённых заказов без quantity: {report['empty_quantity']}")
    print(f"Уникальных заказов: {len(orders)}")
    print(f"Выручка всего: {sum(revenue for _, revenue in totals.values())}")
    print(f"Записано строк в {args.output}: {len(totals)}")


if __name__ == "__main__":
    main()
