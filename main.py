import argparse
import csv
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = {"name", "product", "price"}


@dataclass
class Result:
    columns: list[str]
    orders: list[dict[str, str]]
    invalid: list[dict[str, object]]
    duplicates: int
    total_cents: int

    @property
    def count(self):
        return len(self.orders) + len(self.invalid) + self.duplicates


def format_price(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def parse_price(value):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        raise ValueError("Цена должна быть неотрицательным числом с максимум двумя знаками после точки")
    whole, _, fraction = value.partition(".")
    return int(whole) * 100 + int(fraction.ljust(2, "0"))


def validate_order(columns, values):
    if len(values) != len(columns):
        raise ValueError(f"Ожидалось полей: {len(columns)}, получено: {len(values)}")
    order = dict(zip(columns, (value.strip() for value in values)))
    if not order["name"]:
        raise ValueError("Не указано имя")
    if not order["product"]:
        raise ValueError("Не указан товар")
    cents = parse_price(order["price"])
    order["price"] = format_price(cents)
    return order, cents


def process_orders(file_path):
    with Path(file_path).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, strict=True)
        columns = [value.strip() for value in next(reader, [])]
        if not columns or any(not column for column in columns):
            raise ValueError("Заголовок отсутствует или содержит пустое название столбца")
        if len(columns) != len(set(columns)):
            raise ValueError("Названия столбцов не должны повторяться")
        missing = REQUIRED_COLUMNS - set(columns)
        if missing:
            raise ValueError("Отсутствуют столбцы: " + ", ".join(sorted(missing)))
        result = Result(columns, [], [], 0, 0)
        seen = set()
        while True:
            line_number = reader.line_num + 1
            try:
                values = next(reader)
            except StopIteration:
                break
            if not values:  # Пустые физические строки не являются заказами.
                continue
            try:
                order, cents = validate_order(columns, values)
            except ValueError as error:
                result.invalid.append({
                    "line_number": line_number,
                    "error": str(error),
                    "original_fields": json.dumps(values, ensure_ascii=False),
                })
                continue
            key = tuple(order[column] for column in columns)
            if key in seen:
                result.duplicates += 1
            else:
                seen.add(key)
                result.orders.append(order)
                result.total_cents += cents
        return result


def make_report(result):
    return (
        "===== ОТЧЁТ =====\n"
        f"Всего заказов: {result.count}\n"
        f"Количество дубликатов: {result.duplicates}\n"
        f"Уникальных заказов: {len(result.orders)}\n"
        f"Выручка без дубликатов: {format_price(result.total_cents)}\n"
        f"Количество неправильных записей: {len(result.invalid)}\n"
    )


def write_csv(path, columns, rows):
    with path.open("x", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def save_results(result, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Новая папка исключает перезапись исходника и предыдущих результатов.
    destination = Path(tempfile.mkdtemp(prefix="run-", dir=output_dir))
    try:
        write_csv(destination / "clean_orders.csv", result.columns, result.orders)
        write_csv(destination / "invalid_orders.csv",
                  ["line_number", "error", "original_fields"], result.invalid)
        with (destination / "report.txt").open("x", encoding="utf-8") as file:
            file.write(make_report(result))
    except OSError as error:
        raise OSError(f"Не удалось сохранить полный результат в {destination}: {error}") from error
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description="Очистка CSV с заказами")
    parser.add_argument("input_file", nargs="?", help="Путь к исходному CSV")
    parser.add_argument("--output-dir", default="results", help="Папка результатов (по умолчанию results)")
    args = parser.parse_args(argv)
    try:
        filename = args.input_file or input("Введите путь к CSV-файлу: ").strip()
        if not filename:
            raise ValueError("Не указан путь к CSV-файлу")
        result = process_orders(filename)
        destination = save_results(result, args.output_dir)
    except (OSError, UnicodeError, csv.Error, ValueError, EOFError) as error:
        print(f"Ошибка: {error}")
        return 1
    print(make_report(result), end="")
    print(f"Результаты сохранены: {destination.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
