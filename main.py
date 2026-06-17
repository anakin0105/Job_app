from datetime import datetime
import os
from dotenv import load_dotenv

from src.api import Hh_handler
from src.files import Json_handler
from src.utils import (
    greeting,
    new_search,
    show_all,
    top_n,
    compare_vacancies,
    find_by_keyword,
    delete_menu,
)
from src.database import (          # ← новый файл
    create_database,
    create_tables,
    DBManager,
    fill_database,                 # ← функция заполнения 10 компаний
)

# Загружаем .env (для PostgreSQL)
load_dotenv()

current_date = datetime.now()


def json_mode() -> None:
    """Твой старый режим работы с JSON (избранное)."""
    print("\n=== Режим: Работа с JSON-избранным (твой оригинальный функционал) ===\n")
    hh = Hh_handler()
    storage = Json_handler()   # можно передать filename, если хочешь

    while True:
        print("\nЧто делаем в избранном?")
        print(" 1 — Новый поиск и сохранение вакансий")
        print(" 2 — Показать все сохранённые вакансии")
        print(" 3 — Топ N по зарплате из сохранённых")
        print(" 4 — Сравнить две вакансии по ID")
        print(" 5 — Найти по ключевому слову")
        print(" 6 — Удалить вакансии")
        print(" 0 — Вернуться в главное меню")
        choice = input("Выбери (0-6): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            new_search(hh, storage)
        elif choice == "2":
            show_all(storage)
        elif choice == "3":
            top_n(storage)
        elif choice == "4":
            compare_vacancies(storage)
        elif choice == "5":
            find_by_keyword(storage)
        elif choice == "6":
            delete_menu(storage)
        else:
            print("Неверный выбор, попробуй снова.")


def db_mode() -> None:
    """Новый режим — строго по заданию курсовой (PostgreSQL)."""
    print("\n=== Режим: Работа с базой данных PostgreSQL (курсовая) ===\n")

    # Создаём БД и таблицы один раз
    create_database()
    create_tables()

    # Заполняем данными (10 компаний + их вакансии) — можно вызывать несколько раз, дубли не добавятся
    fill_database()          # ← будет в database.py

    db_manager = DBManager()

    while True:
        print("\nМеню работы с БД:")
        print(" 1 — Список всех компаний и количество вакансий у каждой")
        print(" 2 — Показать все вакансии (компания, название, зарплата, ссылка)")
        print(" 3 — Средняя зарплата по всем вакансиям")
        print(" 4 — Вакансии с зарплатой выше средней")
        print(" 5 — Вакансии по ключевому слову (например: python)")
        print(" 0 — Вернуться в главное меню")
        choice = input("Выбери (0-5): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            data = db_manager.get_companies_and_vacancies_count()
            print("\nКомпании и количество вакансий:")
            for company, count in data:
                print(f"• {company} — {count} вакансий")
        elif choice == "2":
            data = db_manager.get_all_vacancies()
            print("\nВсе вакансии:")
            for row in data:
                # row = (company, vacancy_name, salary_from, salary_to, currency, url)
                salary = f"{row[2] or '—'} – {row[3] or '—'} {row[4] or '₽'}"
                print(f"{row[0]} | {row[1]} | {salary} | {row[5]}")
        elif choice == "3":
            avg = db_manager.get_avg_salary()
            print(f"\nСредняя зарплата по всем вакансиям: {avg:.2f} ₽")
        elif choice == "4":
            data = db_manager.get_vacancies_with_higher_salary()
            print("\nВакансии с зарплатой выше средней:")
            for row in data:
                salary = f"{row[2] or '—'} – {row[3] or '—'} {row[4] or '₽'}"
                print(f"{row[0]} | {row[1]} | {salary}")
        elif choice == "5":
            keyword = input("Введите ключевое слово: ").strip()
            if keyword:
                data = db_manager.get_vacancies_with_keyword(keyword)
                print(f"\nНайдено вакансий с '{keyword}': {len(data)}")
                for row in data:
                    salary = f"{row[2] or '—'} – {row[3] or '—'} {row[4] or '₽'}"
                    print(f"{row[0]} | {row[1]} | {salary}")
        else:
            print("Неверный выбор.")


def main():
    print(greeting(current_date))
    print("=== Поиск вакансий hh.ru + Курсовая по БД ===\n")

    while True:
        print("\nВыбери режим работы:")
        print(" 1 — JSON-режим (курсовая 1: поиск + избранное)")
        print(" 2 — PostgreSQL-режим (курсовая 2: БД, DBManager, 5 запросов)")
        print(" 0 — Выход")
        choice = input("Выбери (0-2): ").strip()

        if choice == "0":
            print("До встречи! Удачи с курсовыми и дипломом❤️")
            break
        elif choice == "1":
            json_mode()
        elif choice == "2":
            db_mode()
        else:
            print("Неверный выбор, попробуй снова.")


if __name__ == "__main__":
    main()