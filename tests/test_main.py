import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import main, parse_price, process_orders, save_results


class CleanerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def process(self, content):
        path = self.root / "input.csv"
        path.write_text(content, encoding="utf-8")
        return process_orders(path)

    def test_repository_example(self):
        result = process_orders(Path(__file__).resolve().parents[1] / "examples" / "orders.csv")
        self.assertEqual((result.count, result.duplicates, len(result.orders),
                          result.total_cents, len(result.invalid)), (9, 1, 5, 1680000, 3))

    def test_invalid_headers(self):
        for content in ("", "name,price\n", "name,product,price,price\n", "name,product,price,\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.process(content)

    def test_bom_and_normalization(self):
        result = self.process('\ufeffname, product,price,date\n Олег , Мышка ,0800, 2026\nОлег,Мышка,800.00,2026\nОлег,Мышка,800,2027\n')
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(result.total_cents, 160000)
        self.assertEqual(result.orders[0]["name"], "Олег")

    def test_invalid_rows_preserved(self):
        result = self.process('name,product,price\nИван,Мышка\nИван,Мышка,100,лишнее\n   ,Мышка,10\nИван, ,10\nИван,Мышка,\n')
        self.assertEqual(len(result.invalid), 5)
        self.assertEqual(result.invalid[0]["line_number"], 2)
        self.assertEqual(json.loads(result.invalid[1]["original_fields"])[-1], "лишнее")

    def test_prices(self):
        for value in ("", "неизвестно", "-1", "NaN", "Infinity", "1.001", "1,50", "1e2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_price(value)
        self.assertEqual(parse_price("0"), 0)
        self.assertEqual(parse_price("1.5"), 150)
        self.assertEqual(parse_price("0001.05"), 105)

    def test_exact_sum(self):
        result = self.process('name,product,price\nА,Б,0.10\nА,В,0.20\n')
        self.assertEqual(result.total_cents, 30)

    def test_csv_quotes_multiline_and_blank_lines(self):
        result = self.process('name,product,price\n\nИван,"Мышка, USB",10\nИван,"две\nстроки",20\nИван,Товар,плохо\n')
        self.assertEqual(len(result.orders), 2)
        self.assertEqual(result.invalid[0]["line_number"], 6)
        self.assertEqual(result.count, 3)

    def test_broken_csv(self):
        with self.assertRaises(csv.Error):
            self.process('name,product,price\nИван,"незакрытая кавычка,10\n')

    def test_header_only(self):
        self.assertEqual(self.process('name,product,price\n').count, 0)

    def test_save_and_repeat_without_overwrite(self):
        source = self.root / "clean_orders.csv"
        original = 'name,product,price\nИван,Мышка,10\nИван,Мышка,нет\n'
        source.write_text(original, encoding="utf-8")
        result = process_orders(source)
        first = save_results(result, self.root)
        second = save_results(result, self.root)
        self.assertNotEqual(first, second)
        self.assertEqual(source.read_text(encoding="utf-8"), original)
        with (first / "invalid_orders.csv").open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]["line_number"], "3")
        self.assertIn("10.00", (first / "report.txt").read_text(encoding="utf-8"))

    def test_cli_errors(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(self.root / "missing.csv")]), 1)
        self.assertIn("Ошибка:", output.getvalue())
        with patch("main.process_orders", side_effect=PermissionError("Нет доступа")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["orders.csv"]), 1)


if __name__ == "__main__":
    unittest.main()
