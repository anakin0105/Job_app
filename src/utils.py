
"""Модуль с вспомогательными функциями для работы с пользователем.

Содержит меню, поиск, вывод вакансий и другие утилиты для JSON-режима.
"""
import logging
from datetime import datetime
from typing import List, Union
from unittest.mock import Mock

from src.api import Hh_handler
from src.vacancies import Vacancy


def greeting(date_: datetime) -> str:
    """
    Возвращает приветствие в зависимости от времени суток.

    Параметры
    ----------
    date_ : datetime
        Объект ``datetime`` с текущей датой/временем.

    Возвращает
    -------
    str
        Одно из: «Доброй ночи», «Доброе утро», «Добрый день», «Добрый вечер».
    """
    logging.info("Обработка времени: %s", date_)

    hour = date_.hour
    if 0 <= hour < 6:
        return "Доброй ночи"
    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    return "Добрый вечер"


current_date = datetime.now()


def new_search(hh, storage):
    """Выполняет новый поиск вакансий по запросу пользователя и добавляет их в избранное.

        Args:
            hh (Hh_handler): Обработчик API hh.ru.
            storage (Json_handler): Объект хранилища для сохранения вакансий.
        """
    query = input("Поисковый запрос (например: python django remote) ").strip()
    if not query:
        return print("Запрос пустой")
    count = int(input("Сколько вакансий (max 100): ") or 50)

    raw_vacancies = hh.get_vacancies(verbal=False, params={"text": query}, num=count)
    if not raw_vacancies:
        return print("Ничего не найдено")
    added = 0
    doubles = 0
    for item in raw_vacancies:
        try:
            vac = Vacancy(item)

            if storage.addData(vac):
                added += 1
            else:
                doubles += 1
        except Exception as e:
            print(f"Пропущена: {e}")
    print(f"Добавлено {added} вакансий, {doubles} пропущено как дубли.")


def show_all(storage):
    """Выводит все сохранённые вакансии в красивом формате с использованием метода show_beautiful()."""
    all_vacs = storage.get_all()
    if not all_vacs:
        print("Сейчас в избранном ничего нет")

    print(f"\nНайдено {len(all_vacs)} вакансий:")
    for v_dict in all_vacs:
        print(
            f"• {v_dict.get('name')}  ({v_dict.get('salary_from', '—')} – {v_dict.get('salary_to', '—')})"
        )
        print(f"  {v_dict.get('url')[:70]}...\n")

    count = len(all_vacs)
    ending = "я" if count == 1 else "й" if count % 10 in (0, 5, 6, 7, 8, 9) else "и"
    print(f"\n📂 Избранное: найдено {count} вакансии{ending}\n")

    for vac_dict in all_vacs:
        vac = Vacancy(vac_dict)  # создаём объект → он сам заполнит все поля
        vac.show_beautiful()


def top_n(storage):
    """Показывает топ-N вакансий по зарплате из избранного."""
    all_vacs = storage.get_all()
    if not all_vacs:
        return print("Нет вакансий")
    n = int(input("Топ сколько? ") or 5)
    objects = [Vacancy(v) for v in all_vacs]
    objects.sort(reverse=True)
    print(f"Топ-{min(n, len(objects))}:")
    for vac in objects[:n]:
        vac.show()
        print("-" * 60)


def compare_vacancies(storage):
    """Позволяет сравнить две вакансии по их ID из избранного.
    Всё объясняем пользователю шаг за шагом — чтобы никто не запутался."""

    print("\n=== Сравнение двух вакансий по ID ===")
    print("Сейчас мы возьмём две вакансии из твоего избранного и покажем их бок о бок.")
    print(
        "Тебе нужно ввести два уникальных ID (это числа, которые ты видишь в списке вакансий)."
    )
    print("Если не помнишь ID — сначала зайди в пункт 2 меню и посмотри список.\n")

    # Шаг 1 — первая вакансия
    while True:
        id1 = input("Введите номер (ID) первой вакансии: ").strip()
        if not id1:
            print("Пожалуйста, введи ID (это число из списка вакансий)")
            continue
        if id1 not in storage.data:
            print(f"Вакансия с ID {id1} не найдена. Проверь номер и попробуй снова.")
            continue
        break

    # Шаг 2 — вторая вакансия (можно даже защитить от ввода того же ID)
    while True:
        id2 = input("Введите номер (ID) второй вакансии: ").strip()
        if not id2:
            print("Пожалуйста, введи ID второй вакансии")
            continue
        if id2 not in storage.data:
            print(f"Вакансия с ID {id2} не найдена. Проверь номер.")
            continue
        if id1 == id2:
            print("Нельзя сравнивать вакансию саму с собой 😄 Введи другой ID.")
            continue
        break

    # Нашли обе — показываем
    print(f"\nОтлично! Сравниваем вакансии {id1} и {id2}...\n")

    vac1_dict = storage.data[id1]
    vac2_dict = storage.data[id2]

    vac1 = Vacancy(vac1_dict)
    vac2 = Vacancy(vac2_dict)

    vac1.compare(vac2)


def find_by_keyword(storage):
    """Ищет вакансии по ключевому слову среди сохранённых."""
    word = input("Ключевое слово: ").strip().lower()
    if not word:
        return
    found = storage.find({"keyword": word})
    print(f"Найдено {len(found)} с '{word}':")
    for v in found[:10]:
        print(f"• {v.get('name')} — {v.get('url')[:60]}...")


def delete_by_id(storage):
    """Удаляет одну вакансию по ID."""
    vid = input("ID для удаления: ").strip()
    if storage.delete_data(vid):
        print("Удалена")
    else:
        print("Не найдена")


def delete_menu(storage):
    """Меню удаления вакансий (по ID или всех сразу)."""
    print("\n  1 — Удалить вакансию по ID")
    print("  2 — Удалить все вакансии")
    print("  0 — Назад")
    choice = input("Выбери (0-2): ").strip()
    if choice == "1":
        delete_by_id(storage)
    elif choice == "2":
        confirm = input("Точно удалить ВСЕ вакансии? (да/нет): ").strip().lower()
        if confirm == "да":
            storage.clear()
            print("Все вакансии удалены.")
        else:
            print("Отменено.")
    elif choice == "0":
        return
    else:
        print("Неверный выбор")
