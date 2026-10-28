import csv
from pathlib import Path

folder = Path(__file__).resolve().parent

filename = input("Введите название CSV-файла: ").strip()
file_path = folder / filename

if not file_path.is_file():
   print("Ошибка! Такого файла не существует")
   raise SystemExit(1)

seen = set()

unique_total = 0
unique_orders = []
duplicate_count = 0
invalid_count = 0
invalid_orders = []


with open(file_path, "r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    columns = reader.fieldnames

    required_colums = {"name", "product", "price"}

    missing = required_colums - set(reader.fieldnames or [])

    if missing:
       print("Ошибка! Отсутствуют столбцы:", missing)
       raise SystemExit(1)

    for order in reader:
        if not (order.get("name") or "").strip():
            print("Ошибка! Не указано имя")
            invalid_count += 1
            invalid_orders.append(order)
            continue
        
        if not (order.get("product") or "").strip():
         print("Ошибка! Не указано название товара")
         invalid_count += 1
         invalid_orders.append(order)
         continue

        try:
           price = int(order["price"])
        except ValueError:
           invalid_count += 1
           invalid_orders.append(order)
           print("Неправильная цена:", order["price"])
           continue
        
        key = (order["name"], order["product"], order["price"])
        if key in seen:
         duplicate_count += 1
         print("Найден дубликат:", key)
        else:
         seen.add(key)
         unique_total += int(order["price"])
         unique_orders.append(order)

print("\n====== ОТЧЁТ ======")
print("Всего заказов:", len(unique_orders) + duplicate_count + invalid_count)
print("Количество дубликатов:", duplicate_count)
print("Уникальных заказов:", len(unique_orders))
print("Выручка без дубликатов:", unique_total)
print("Количество неправильных записей:", invalid_count)

clean_path = folder / "clean_orders.csv"

with open(clean_path, "w", encoding="utf-8", newline="") as file:
   writer = csv.DictWriter(file, fieldnames=columns)

   writer.writeheader()
   writer.writerows(unique_orders)

report_path = folder / "report.txt"

with open(report_path, "w", encoding="utf-8") as file:
   file.write("===== ОТЧЁТ =====\n")
   file.write(f"Всего заказов: {len(unique_orders) + duplicate_count + invalid_count}\n")
   file.write(f"Количество дубликатов: {duplicate_count}\n")
   file.write(f"Уникальных заказов: {len(unique_orders)}\n")
   file.write(f"Выручка без дубликатов: {unique_total}\n")
   file.write(f"Количество неправильных записей: {invalid_count}\n")


invalid_path = folder / "invalid_orders.csv"

with open(invalid_path, "w", encoding="utf-8", newline="") as file:
   writer = csv.DictWriter(file, fieldnames=columns)

   writer.writeheader()
   writer.writerows(invalid_orders)
