from typing import Any, Dict, Optional

from tabulate import tabulate


class Vacancy:
    """Класс для представления одной вакансии с hh.ru.

    Этот класс хранит данные о вакансии, полученные из API hh.ru, и предоставляет методы для работы с ними.
    Атрибуты определяются через __slots__ для экономии памяти (как фиксированный инвентарь в игре — нельзя добавить лишние вещи).

    Атрибуты:
        id (Optional[str]): Уникальный идентификатор вакансии.
        name (Optional[str]): Название вакансии.
        url (Optional[str]): Ссылка на вакансию (по умолчанию 'Нет ссылки', если не указана).
        currency (Optional[str]): Валюта зарплаты (например, 'RUR' для рублей).
        salary_from (int): Минимальная зарплата (0, если не указана).
        salary_to (int): Максимальная зарплата (0, если не указана).
        requirement (Optional[str]): Требования к кандидату ('Не указано', если отсутствует).
        responsibility (Optional[str]): Обязанности ('Не указано', если отсутствует).
        vac_dict (Optional[Dict[str, Any]]): Исходный словарь с данными вакансии из API (для отладки или расширения).

    Пример использования:
        vac_data = {'id': '123', 'name': 'Developer', 'salary': {'from': 100000, 'to': 150000, 'currency': 'RUR'}, ...}
        vacancy = Vacancy(vac_data)
        print(vacancy) # Выводит строковое представление вакансии."""

    __slots__ = (
        "id",  # id вакансии
        "name",  # название
        "url",  # ссылка
        "currency",  # валюта
        "salary_from",  # зарплата от
        "salary_to",  # зарплата до
        "requirement",  # требования
        "responsibility",  # обязанности
        "city",  # area.name
        "company",  # employer.name
        "salary_gross",  # True = до вычета налогов
        "vac_dict",  # исходные данные
    )

    def __init__(self, vac_dict: Optional[Dict[str, Any]] = None) -> None:
        """Инициализирует объект вакансии на основе словаря из API.

        Если vac_dict равен None, создаётся "пустая" вакансия с дефолтными значениями (как пустой слот в инвентаре).
        Иначе извлекает данные из словаря и устанавливает атрибуты.

        Параметры:
            vac_dict (Optional[Dict[str, Any]]): Словарь с данными вакансии из API hh.ru.

        Вызывает:
            self._validate() для проверки и корректировки данных после инициализации."""
        self.vac_dict = vac_dict
        if vac_dict is None:
            # Пустая вакансия (редко нужно)
            self.id = None
            self.name = None
            self.url = None
            self.salary_from = 0
            self.salary_to = 0
            self.currency = None
            self.requirement = None
            self.responsibility = None
            return
        # Основные поля — безопасно, без KeyError
        self.id = str(vac_dict.get("id", ""))
        self.name = vac_dict.get("name", "Без названия")
        self.url = vac_dict.get("alternate_url") or vac_dict.get("url", "Нет ссылки")

        # Зарплата — самый критичный блок
        salary = vac_dict.get("salary") or {}
        self.salary_from = salary.get("from") or vac_dict.get("salary_from", 0)
        self.salary_to = salary.get("to") or vac_dict.get("salary_to", 0)
        self.currency = salary.get("currency") or vac_dict.get("currency")
        self.salary_gross = salary.get("gross", False) or vac_dict.get(
            "salary_gross", False
        )

        # Требования и обязанности — то же самое
        snippet = vac_dict.get("snippet", {})
        self.requirement = snippet.get("requirement") or vac_dict.get(
            "requirement", "Не указано"
        )
        self.responsibility = snippet.get("responsibility") or vac_dict.get(
            "responsibility", "Не указано"
        )

        # Убираем подсветку hh.ru — две строчки, без лишнего
        self.requirement = (
            self.requirement.replace("<highlighttext>", "")
            .replace("</highlighttext>", "")
            .strip()
        )
        self.responsibility = (
            self.responsibility.replace("<highlighttext>", "")
            .replace("</highlighttext>", "")
            .strip()
        )

        # Город — два источника: API-формат или уже сохранённый
        area = vac_dict.get("area", {})
        self.city = (
            area.get("name")
            if isinstance(area, dict) and "name" in area
            else vac_dict.get("city", "Не указан")
        )

        # Компания
        employer = vac_dict.get("employer", {})
        self.company = (
            employer.get("name")
            if isinstance(employer, dict) and "name" in employer
            else vac_dict.get("company", "Не указана")
        )
        self.__validate()

    def __validate(self) -> None:
        """Приватный метод для валидации данных вакансии.

        Проверяет корректность атрибутов (зарплата >= 0, salary_to >= salary_from, типы данных и т.д.).
        Если данные некорректны, корректирует их (например, устанавливает 0 для зарплаты) или raises ValueError.

        Возвращает:
            None (работает in-place, изменяя атрибуты объекта).

        Raises:
            ValueError: Если salary_to < salary_from или ID некорректный."""
        # Валидация salary_from
        if not isinstance(self.salary_from, (int, float)) or self.salary_from < 0:
            # logging.warning(f"Некорректная salary_from для вакансии {self.id}: {self.salary_from}. Устанавливаю 0.")
            self.salary_from = 0

        # Валидация salary_to
        if not isinstance(self.salary_to, (int, float)) or self.salary_to < 0:
            # logging.warning(f"Некорректная salary_to для вакансии {self.id}: {self.salary_to}. Устанавливаю 0.")
            self.salary_to = 0

        # Проверка, чтобы salary_to >= salary_from
        if self.salary_to > 0 and self.salary_to < self.salary_from:
            raise ValueError(
                f"Для вакансии {self.id}: salary_to ({self.salary_to}) меньше salary_from ({self.salary_from})."
            )

        # Если зарплата указана, но валюта None
        if (self.salary_from > 0 or self.salary_to > 0) and self.currency is None:
            # logging.warning(f"Зарплата указана для вакансии {self.id}, но валюта не задана. Устанавливаю 'RUR' по умолчанию.")
            self.currency = "RUR"

            # Валидация ID
        if not isinstance(self.id, (str, int)):
            raise ValueError(
                f"Некорректный ID вакансии: {self.id}. Должен быть строкой или числом."
            )

        # Валидация URL
        if not isinstance(self.url, str):
            self.url = "Нет ссылки"

        # Дополнительно: если requirement или responsibility None - ставим 'Не указано'
        if self.requirement is None:
            self.requirement = "Не указано"
        if self.responsibility is None:
            self.responsibility = "Не указано"

    def avg_salary(self) -> int:
        """Вычисляет среднюю зарплату (int). Если данных нет — возвращает 0.

        Средняя считается как (from + to) / 2, если оба указаны. Иначе берёт то, что есть.
        Это как расчёт среднего урона оружия в игре — чтобы сравнить эффективность.

        Возвращает:
            int: Средняя зарплата (округлённая вниз)."""
        if self.salary_from != 0 and self.salary_to != 0:
            return (self.salary_from + self.salary_to) // 2
        if self.salary_from != 0:
            return self.salary_from
        if self.salary_to != 0:
            return self.salary_to
        return 0

    def __eq__(self, other: object) -> bool:
        """Проверка на равенство по зарплате"""

        if not isinstance(other, Vacancy):
            return False
        return self.avg_salary() == other.avg_salary()

    def __lt__(self, other: object) -> bool:
        """Проверка на меньше по зарплате"""

        if not isinstance(other, Vacancy):
            return NotImplemented
        return self.avg_salary() < other.avg_salary()

    def __le__(self, other: object) -> bool:
        """Проверка на меньше или равно по зарплате"""

        if not isinstance(other, Vacancy):
            return NotImplemented
        return self.avg_salary() <= other.avg_salary()

    def __gt__(self, other: object) -> bool:
        """Проверка на больше по зарплате"""

        if not isinstance(other, Vacancy):
            return NotImplemented
        return self.avg_salary() > other.avg_salary()

    def __ge__(self, other: object) -> bool:
        """Проверка на больше или равно по зарплате"""

        if not isinstance(other, Vacancy):
            return NotImplemented
        return self.avg_salary() >= other.avg_salary()

    def __str__(self) -> str:
        """Строковое представление вакансии"""

        return (
            f"Вакансия: {self.title}\n"
            f"Ссылка: {self.url}\n"
            f"Зарплата: {self.salary_from} до {self.salary_to} {self.currency or 'Не указано'}\n"
            f"Обязанности: {self.responsibility}\n"
            f"Требуемый опыт: {self.requirement}"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "salary_from": self.salary_from,
            "salary_to": self.salary_to,
            "currency": self.currency,
            "salary_gross": self.salary_gross,  # ← добавили!
            "requirement": self.requirement,
            "responsibility": self.responsibility,
            "city": self.city,  # ← обязательно
            "company": self.company,  # ← обязательно
        }

    def show(self) -> None:
        """
        Простой, но надёжный вывод вакансии (для топ-N и других мест).
        Безопасно обрабатывает отсутствие данных.
        """
        name = self.name or "Без названия"
        url = self.url or "Нет ссылки"

        # Зарплата — как в show_beautiful
        if self.salary_from == 0 and self.salary_to == 0:
            salary_str = "По договорённости"
        elif self.salary_from == 0 and self.salary_to == 0:
            salary_str = "Зарплата не указана"
        else:
            fr = (
                f"от {self.salary_from:,}".replace(",", " ") if self.salary_from else ""
            )
            to = f"до {self.salary_to:,}".replace(",", " ") if self.salary_to else ""
            currency = self.currency or "₽"
            salary_str = f"{fr} {to} {currency}".strip() or "Не указана"

        req = self.requirement or "Не указано"
        resp = self.responsibility or "Не указано"

        output = (
            f"ID: {self.id or '—'}\n"
            f"Название: {name}\n"
            f"Ссылка: {url}\n"
            f"Зарплата: {salary_str}\n"
            f"Требования: {req}\n"
            f"Обязанности: {resp}"
        )

        print(output)
        return output

    def compare(self, other) -> None:
        """Красивое сравнение двух вакансий с выводом таблицы в консоль.

        Сравнивает атрибуты двух вакансий и выводит таблицу с использованием tabulate.
        Выделяет жирным шрифтом лучшие значения зарплаты.

        Параметры:
            other (Vacancy): Другая вакансия для сравнения.

        Возвращает:
            None (выводит таблицу в консоль).

        Требует: Библиотека tabulate должна быть импортирована."""

        # Форматируем зарплату красиво
        def format_salary(value, currency):
            if value == 0:
                return "Не указано"
            if currency is None:
                currency = ""
            return f"{value:,} {currency}".replace(",", " ")

        salary1_from = format_salary(self.salary_from, self.currency)
        salary1_to = format_salary(self.salary_to, self.currency)
        salary2_from = format_salary(other.salary_from, other.currency)
        salary2_to = format_salary(other.salary_to, other.currency)

        # Выделяем жирным самую лучшую зарплату
        if self.salary_from > other.salary_from:
            salary1_from = f"**{salary1_from}**"
        elif other.salary_from > self.salary_from:
            salary2_from = f"**{salary2_from}**"

        if self.salary_to > other.salary_to and other.salary_to != 0:
            salary1_to = f"**{salary1_to}**"
        elif other.salary_to > self.salary_to and self.salary_to != 0:
            salary2_to = f"**{salary2_to}**"

        # Короткие названия для заголовков колонок
        title1 = self.name[:30] + "..." if len(self.name) > 30 else self.name
        title2 = other.name[:30] + "..." if len(other.name) > 30 else other.name

        # Данные таблицы
        data = [
            ["ID", self.id, other.id],
            ["Вакансия", self.name, other.name],
            ["Ссылка", self.url, other.url],
            ["Валюта", self.currency or "Не указано", other.currency or "Не указано"],
            ["Зарплата от", salary1_from, salary2_from],
            ["Зарплата до", salary1_to, salary2_to],
            ["Требования", self.requirement, other.requirement],
            ["Обязанности", self.responsibility, other.responsibility],
        ]

        # Красивый вывод
        print(f"\n🔥 Сравнение вакансий:\n")
        print(
            tabulate(
                data,
                headers=["Параметр", title1, title2],
                tablefmt="grid",
                stralign="left",
                maxcolwidths=[15, 40, 40],
            )
        )

    def show_beautiful(self) -> None:
        """
        Красивый вывод одной вакансии в консоль (для избранного).
        Безопасно обрабатывает отсутствие полей.
        """
        name = (self.name or "Без названия").strip()
        if len(name) > 65:
            name = name[:62] + "..."

        # Зарплата — учитываем реальное поведение hh.ru
        if self.salary_from == 0 and self.salary_to == 0:
            salary_line = "💰 По договорённости"
        elif not (self.salary_from or self.salary_to):
            salary_line = "💰 Зарплата не указана"
        else:
            fr = (
                f"от {self.salary_from:,}".replace(",", " ") if self.salary_from else ""
            )
            to = f"до {self.salary_to:,}".replace(",", " ") if self.salary_to else ""
            currency = self.currency or "₽"
            gross_text = " (gross)" if self.salary_gross else " (на руки)"
            salary_line = f"💰 {fr} {to} {currency}{gross_text}".strip()

        city = self.city or "—"
        company = self.company or "—"

        # Выводим ID сразу после названия — чтобы всегда было видно
        print(f"📌 {name}")
        print(f"   🆔 ID: {self.id or '—'}")  # ← вот это добавляем
        print(f"   {salary_line}")
        print(f"   🏙️ {city} • {company}")
        print(f"   🔗 {self.url}")

        if self.requirement and self.requirement != "Не указано":
            req = self.requirement[:140].rstrip() + (
                "..." if len(self.requirement) > 140 else ""
            )
            print(f"   📋 Требования: {req}")

        if self.responsibility and self.responsibility != "Не указано":
            resp = self.responsibility[:140].rstrip() + (
                "..." if len(self.responsibility) > 140 else ""
            )
            print(f"   ⚙️ Обязанности: {resp}")

        print("─" * 90)
