from src.api import Hh_handler
from src.files import Json_handler
from src.utils import (
    compare_vacancies,
    current_date,
    delete_menu,
    find_by_keyword,
    greeting,
    new_search,
    show_all,
    top_n,
)


def main():
    print(greeting(current_date))
    print("=== Поиск вакансий (hh.ru) ===\n")
    hh = Hh_handler()
    storage = Json_handler()  # Или с filename
    while True:
        print("\nЧто делаем?")
        print(" 1 — Новый поиск и сохранение вакансий")
        print(" 2 — Показать все сохранённые вакансии")
        print(" 3 — Топ N по зарплате из сохранённых")
        print(" 4 — Сравнить две вакансии по ID")
        print(" 5 — Найти по ключевому слову")
        print(" 6 — Удалить вакансии")
        print(" 0 — Выход")
        choice = input("Выбери (0-5): ").strip()
        if choice == "0":
            print("До встречи!")
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
            print("Неверный выбор")


if __name__ == "__main__":
    main()
