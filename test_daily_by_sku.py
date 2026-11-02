"""Тесты на маленькой выгрузке, где ожидаемые цифры посчитаны вручную.

Запуск: python -m unittest -v
"""
import csv
import os
import tempfile
import unittest

from daily_by_sku import aggregate, read_orders, write_result

HEADER = "order_id,order_date,sku,quantity,price,status\n"


def run(rows):
    """Прогоняет строки CSV через скрипт и возвращает результат как список словарей."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "sales.csv")
        dst = os.path.join(tmp, "out.csv")
        with open(src, "w", encoding="utf-8") as f:
            f.write(HEADER + "".join(rows))
        orders, _ = read_orders(src)
        write_result(aggregate(orders), dst)
        with open(dst, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


class DailyBySkuTest(unittest.TestCase):
    def test_counts_and_revenue(self):
        result = run([
            "1,2026-09-01,A,2,100,delivered\n",   # 200
            "2,2026-09-01,A,1,100,cancelled\n",   # заказ есть, выручки нет
            "3,2026-09-01,A,3,100,delivered\n",   # 300
            "4,2026-09-02,A,1,100,delivered\n",   # другой день
        ])
        self.assertEqual(result, [
            {"sku": "A", "order_date": "2026-09-01", "orders": "3", "revenue": "500"},
            {"sku": "A", "order_date": "2026-09-02", "orders": "1", "revenue": "100"},
        ])

    def test_duplicate_row_counted_once(self):
        result = run([
            "1,2026-09-01,A,2,100,delivered\n",
            "1,2026-09-01,A,2,100,delivered\n",
        ])
        self.assertEqual(result[0]["orders"], "1")
        self.assertEqual(result[0]["revenue"], "200")

    def test_status_typos(self):
        result = run([
            "1,2026-09-01,A,1,100,Delivered\n",
            "2,2026-09-01,A,1,100,delivered \n",
            "3,2026-09-01,A,1,100,DELIVERED\n",
            "4,2026-09-01,A,1,100,canceled\n",
            "5,2026-09-01,A,1,100,CANCELLED\n",
        ])
        self.assertEqual(result[0]["orders"], "5")
        self.assertEqual(result[0]["revenue"], "300")

    def test_cancelled_without_quantity_is_counted(self):
        result = run(["1,2026-09-01,A,,100,cancelled\n"])
        self.assertEqual(result[0]["orders"], "1")
        self.assertEqual(result[0]["revenue"], "0")

    def test_sorted_by_sku_then_date(self):
        result = run([
            "1,2026-09-02,B,1,100,delivered\n",
            "2,2026-09-01,B,1,100,delivered\n",
            "3,2026-09-03,A,1,100,delivered\n",
        ])
        keys = [(r["sku"], r["order_date"]) for r in result]
        self.assertEqual(keys, [("A", "2026-09-03"), ("B", "2026-09-01"), ("B", "2026-09-02")])

    def test_ambiguous_data_stops_script(self):
        cases = {
            "неизвестный статус": ["1,2026-09-01,A,1,100,returned\n"],
            "выкуплен без quantity": ["1,2026-09-01,A,,100,delivered\n"],
            "дубль с другими данными": [
                "1,2026-09-01,A,1,100,delivered\n",
                "1,2026-09-01,A,2,100,delivered\n",
            ],
        }
        for name, rows in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                run(rows)


if __name__ == "__main__":
    unittest.main()
