import time
from abc import ABC, abstractmethod
from typing import Dict, List

import requests as r


class Api_handler(ABC):
    """Абстрактный базовый класс для работы с API сервисов вакансий.

    Определяет единый интерфейс для отправки GET и POST запросов к любому API вакансий
    (hh.ru, SuperJob, LinkedIn API и т.д.).

    Любой конкретный сервис (например, HeadHunter) должен наследоваться от этого класса
    и реализовывать методы get() и post() с учётом особенностей конкретного API
    (заголовки, авторизация, обработка ошибок, пагинация и т.п.).

    Основная идея: унифицировать работу с разными источниками вакансий,
    чтобы в основной программе можно было легко переключаться между сервисами."""

    @abstractmethod
    def _connect_api(self, url: str, params: dict = None) -> r.Response:
        """Абстрактный метод подключения к API.

        • В абстрактном классе — НИКАКОЙ реализации (только pass)
        • Должен быть приватным (с подчёркиванием) в дочерних классах
        • Запрос направляется + проверяет статус-код
        """
        pass

    @abstractmethod
    def get_vacancies(
        self, verbal=False, params: dict = None, num: int = 50
    ) -> List[Dict]:
        """Абстрактный метод получения вакансий (отдельно от подключения).

        • В абстрактном классе — только заглушка
        • Реализация будет в Hh_handler
        """
        pass

    @abstractmethod
    def get(self, url: str, params: dict = None) -> r.Response:
        """Выполняет GET-запрос к указанному URL с параметрами.

        Абстрактный метод — должен быть реализован в каждом дочернем классе.

        Аргументы:
            url    : полный адрес (например, "https://api.hh.ru/vacancies")
            params : словарь query-параметров (?text=python&area=1&...)

        Возвращает:
            requests. Response — объект ответа от сервера

        Важно:
        • Реализация должна учитывать авторизацию (если требуется)
        • Должна обрабатывать типичные ошибки (429, 403, 500 и т.д.)
        • Желательно добавлять User-Agent и таймаут"""
        pass

    @abstractmethod
    def post(self, url: str, data: dict = None) -> r.Response:
        """Выполняет POST-запрос к указанному URL с данными в теле.

        Абстрактный метод — должен быть реализован в каждом дочернем классе.

        Аргументы:
            url  : полный адрес
            data : словарь данных, который будет отправлен в теле запроса (json)

        Возвращает:
            requests. Response — объект ответа от сервера

        Примечание:
        Сейчас в проекте с hh.ru POST почти не используется,
        но метод оставлен для возможного расширения (отклик на вакансию, авторизация и т.д.).
        """
        pass


class Hh_handler(Api_handler):
    """Обработчик API HeadHunter (hh.ru) — основной класс для получения вакансий.

    Наследуется от абстрактного класса Api_handler.
    Реализует унифицированный интерфейс для работы с API hh.ru:
    • формирование и выполнение запросов к поиску вакансий
    • обработка базовых параметров запроса
    • получение и возврат данных в формате списка словарей

    Основная идея: предоставить удобный и надёжный способ получать вакансии
    с hh.ru, соблюдая при этом контракт, заданный в абстрактном классе Api_handler.

    Атрибуты экземпляра (приватные, с name mangling):
        __base_url      — базовый адрес API для поиска вакансий
        __params        — последние использованные параметры запроса
        __last_response — последний полученный объект ответа (для отладки)
    """

    def __init__(self):
        """Инициализация обработчика API hh.ru.

        Устанавливает:
        • базовый URL API вакансий
        • пустые значения для хранения параметров и последнего ответа.
        Вызывает конструктор родительского класса.
        """
        super().__init__()
        self.__base_url = "https://api.hh.ru/vacancies"
        self.__params = None
        self.__last_response = None

    def _connect_api(self, url: str, params: dict = None) -> r.Response:
        """Реализация абстрактного метода из Api_handler.

        Просто передаёт управление во внутренний сверх-приватный метод.
        """
        return self.__connect_api(url, params)

    def __connect_api(self, url: str, params: dict = None) -> r.Response:
        """Надёжное подключение к API hh.ru с повторными попытками и обработкой типичных ошибок.

        Этот приватный метод — сердце всей работы с внешним API. Именно здесь происходит:
        • отправка GET-запроса
        • установка обязательного заголовка User-Agent (без него hh.ru возвращает 400 Bad Request)
        • проверка кода ответа
        • повторные попытки при временных сбоях (самые частые: 429, таймаут, 5xx)


        Аргументы:
            url (str): Полный адрес API.
                       Обычно это self.__base_url = "https://api.hh.ru/vacancies"
            params (dict, optional): Словарь query-параметров (?text=python&area=1&per_page=50...).
                                     Если None — отправляется пустой запрос.

        Возвращает:
            requests.Response: Объект ответа от сервера (уже проверенный на 200 OK).

        Исключения:
            requests.exceptions.HTTPError: При 4xx/5xx ошибках после всех попыток
                                           (кроме временных 429/5xx — их пытаемся повторить)
            requests.exceptions.Timeout: Таймаут соединения после всех попыток
            requests.exceptions.ConnectionError: Проблемы с сетью
            ConnectionError: Все попытки исчерпаны — не удалось достучаться до API

        Поведение и логика (как в игре с авто-возрождением):
        1. Устанавливаем заголовок User-Agent — без него hh.ru блокирует запрос (400 Bad Request).
           Формат: "ИмяПриложения/Версия (почта для связи)"
        2. Делаем до 3 попыток подключения.
        3. Между попытками ждём паузу (экспоненциальный backoff):
           • 1-я попытка провалилась → ждём ~1 сек
           • 2-я → ~2 сек
           • 3-я → ~4 сек
        4. Обрабатываем самые частые "временные" ошибки:
           • 429 — Too Many Requests
           • 500, 502, 503, 504 — сервер упал/перезагружается
           • Timeout — интернет лаганул или hh.ru долго думает
        5. Если ошибка не временная (403 Forbidden, 400 Bad Request и т.п.) — сразу кидаем исключение.
        6. При успехе (200 OK) — возвращаем response.

        Пример использования (внутри get_vacancies):
            response = self.__connect_api(self.__base_url, search_params)
            data = response.json()
            return data.get("items", [])

        Почему именно 3 попытки и такая пауза?
        • 3 — золотая середина: не слишком долго ждём, но даём шанс серверу "прийти в себя"
        • Экспоненциальная пауза — стандартный приём, чтобы не добивать сервер лишними запросами

        Рекомендации по использованию:
        • Всегда передавайте params с хотя бы text=... иначе вернётся пустой список
        • per_page ≤ 100 (максимум hh.ru за один запрос)
        • Если часто получаете 429 — добавьте больше задержки между вызовами get_vacancies()
        • В production-коде (не в курсовой) можно читать заголовок Retry-After из ответа 429
        """
        headers = {"User-Agent": "VacancySearcherBot/1.0 (coursework)"}

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"Попытка {attempt}/{max_attempts} подключения к API...")

                response = r.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=10,
                )

                if response.status_code != 200:
                    # Для 429 делаем retry, для остальных — кидаем сразу
                    if response.status_code == 429:
                        print("429 Too Many Requests — сервер просит подождать...")
                        time.sleep(2 ** (attempt - 1))
                        continue
                    else:
                        response.raise_for_status()  # кидает HTTPError для 4xx/5xx

                print("Успех! Получен ответ 200")
                return response

            except r.exceptions.HTTPError:
                raise  # 4xx/5xx — сразу наружу, без retry

            except r.exceptions.RequestException as e:

                if attempt == max_attempts:
                    raise ConnectionError(  # ← оборачиваем в ConnectionError
                        f"Не удалось подключиться к hh.ru API после {max_attempts} попыток. "
                        "Проверьте интернет, подождите 5–10 минут или уменьшите частоту запросов."
                    ) from e

                time.sleep(2 ** (attempt - 1))

    def get(self, url: str, params: dict = None) -> r.Response:
        """Выполняет GET-запрос к указанному URL с параметрами.

        Реализация абстрактного метода из Api_handler.
        Делегирует низкоуровневое подключение приватному методу __connect_api,
        но добавляет обработку возможных невалидных / ошибочных ответов.

        Аргументы:
            url    : полный адрес (обычно self.__base_url)
            params : словарь query-параметров (?text=python&area=1&per_page=50...)

        Возвращает:
            requests.Response — объект ответа от сервера (только если код 200 OK)

        Поведение при ошибках (примеры из документации hh.ru):
        • 400 Bad Request — невалидные параметры (нет User-Agent, кривой text, area и т.д.)
        • 403 Forbidden — запрещён доступ (редко, если нарушили правила)
        • 429 Too Many Requests — превышен лимит запросов (самая частая проблема при быстрых тестах)
        • 500+ — ошибка на стороне hh.ru

        Важно:
        • Всегда используй User-Agent (уже добавлен в __connect_api)
        • Если часто 429 — уменьшай частоту вызовов get_vacancies (добавь time.sleep(1) между запросами)
        """
        try:
            # Делегируем подключение приватному методу
            response = self.__connect_api(url, params)

            # Если дошли сюда → статус 200 (raise_for_status() уже прошёл)
            print(f"Успешный GET-запрос → статус {response.status_code}")
            return response

        except r.exceptions.HTTPError as http_err:
            # Здесь response уже есть в http_err.response
            status_code = http_err.response.status_code
            error_text = http_err.response.text.strip()[:200]  # обрезаем длинный текст

            if status_code == 400:
                print(f"400 Bad Request — ошибка в параметрах запроса.")
                print(f"Подробности: {error_text or 'нет описания от сервера'}")
                print("Проверь: text, area, salary, per_page (≤100), опыт и т.д.")
                print(
                    "Также обязательно нужен User-Agent — он уже установлен в __connect_api."
                )

            elif status_code == 403:
                print(f"403 Forbidden — доступ запрещён.")
                print("Возможные причины: нарушение правил API, блокировка по IP.")
                print(f"Детали: {error_text or 'нет описания'}")

            elif status_code == 429:
                print(f"429 Too Many Requests — превышен лимит запросов к hh.ru.")
                print("Подожди 5–15 секунд и попробуй снова (или реже делай запросы).")
                print(
                    "hh.ru ограничивает ~5000 запросов в день + rate-limit по секундам."
                )
                # Можно добавить time.sleep(10), но лучше оставить пользователю решать

            elif status_code >= 500:
                print(f"{status_code} — ошибка на стороне сервера hh.ru.")
                print("Попробуй позже — это временная проблема у них.")
                print(f"Детали: {error_text or 'нет описания'}")

            else:
                print(f"Неожиданная HTTP-ошибка {status_code}:")
                print(f"{error_text or 'нет текста ошибки'}")

            # Пробрасываем исключение дальше (чтобы get_vacancies мог обработать, если нужно)
            raise

        except r.exceptions.Timeout:
            print("Таймаут запроса — hh.ru не ответил вовремя (возможно, перегружен).")
            print("Попробуй позже или проверь интернет.")
            raise

        except r.exceptions.ConnectionError:
            print("Ошибка соединения — нет интернета или hh.ru недоступен.")
            raise

        except Exception as e:
            print(f"Неизвестная ошибка при GET-запросе: {type(e).__name__}")
            print(f"Детали: {str(e)}")
            raise

    def get_vacancies(
        self,
        query: str | None = None,
        verbal: bool = False,
        params: dict | None = None,
        num: int = 50,
        per_page: int | None = None,  # ← новый явный параметр
    ) -> List[Dict]:
        """
        Получает список вакансий с hh.ru по заданным параметрам.

        Аргументы:
            query     : поисковая фраза (если передана — добавляется в params["text"])
            verbal    : печатать ли красивый вывод сразу после получения
            params    : дополнительные параметры поиска (area, salary, experience и др.)
            num       : желаемое количество вакансий (удобен для per_page)
            per_page  : явное указание количества вакансий на страницу (приоритет выше, чем num)

        Возвращает:
            List[Dict] — список вакансий (поле "items" из ответа API)

        Примечание:
            • Максимальное значение per_page = 100 (ограничение hh.ru)
            • Если переданы и num, и per_page — приоритет у per_page
            • Если ничего не передано — берётся значение по умолчанию 50
        """
        if params is None:
            params = {}

        # Создаём копию, чтобы не портить внешний словарь
        search_params = params.copy()

        # 1. Добавляем текст поиска, если передан
        if query:
            search_params["text"] = query.strip()

        # 2. Определяем итоговое значение per_page
        #    Приоритет: per_page → num → 50 (по умолчанию)
        # final_per_page = 50  # fallback

        if per_page is not None:
            final_per_page = per_page
        elif "per_page" in search_params:
            final_per_page = search_params["per_page"]
        else:
            final_per_page = num

        # 3. Ограничиваем разумными пределами hh.ru
        final_per_page = max(1, min(100, int(final_per_page)))

        # 4. Записываем в параметры запроса
        search_params["per_page"] = final_per_page

        # Сохраняем для отладки / повторных вызовов
        self.__params = search_params
        self.__last_response = None

        try:
            response = self.get(self.__base_url, search_params)
            self.__last_response = response

            data = response.json()
            items = data.get("items", [])

            if verbal and items:
                self.print_vacancies_beautiful(items)

            return items

        except Exception as e:
            print(f"⚠️ Ошибка при загрузке вакансий: {str(e)}")
            print("   Попробуйте:")
            print("   • подождать 10–60 секунд (особенно при 429)")
            print("   • упростить запрос")
            print("   • проверить интернет")
            return []

    def post(self, url: str, data: dict = None) -> r.Response:
        """Выполняет POST-запрос (заглушка / заготовка под будущее).

        Реализация абстрактного метода из Api_handler.
        В текущей версии проекта hh.ru не требует POST-запросов,
        поэтому метод возвращает NotImplemented.

        Аргументы:
            url  : адрес
            data : данные для отправки в теле запроса

        Возвращает:
            Никогда не возвращает (выбрасывает исключение)

        Примечание:
        Оставлен для совместимости с интерфейсом Api_handler.
        При необходимости можно реализовать полноценно.
        """
        raise NotImplementedError("POST-запросы пока не поддерживаются для hh.ru")

    # def print_vacancies_beautiful(vacancies: List[dict], title: str = "🎉 Найдено вакансий") -> None:
    #     if not vacancies:
    #         print("😔 Вакансий не найдено.")
    #         return
    #
    #     print(f"🎉 Найдено {len(vacancies)} вакансий\n")
    #     print("=" * 100)
    #
    #     output = ""  # ← ДО цикла
    #
    #     for i, vac in enumerate(vacancies, start=1):
    #         name = vac['name']
    #         url = vac.get('alternate_url', 'Нет ссылки')
    #         city = vac['area']['name']
    #         company = vac['employer']['name']
    #
    #         requirement = vac['snippet'].get('requirement', 'Не указано')
    #         responsibility = vac['snippet'].get('responsibility', 'Не указано')
    #         description = requirement or responsibility or "Описание отсутствует"
    #         if len(description) > 200:
    #             description = description[:200] + "..."
    #
    #         salary = vac.get('salary')
    #         if salary:
    #             fr = salary.get('from')
    #             to = salary.get('to')
    #             curr = salary.get('currency', 'RUR')
    #             gross = " (на руки)" if not salary.get('gross') else " (до вычета налогов)"
    #             if fr and to:
    #                 salary_text = f"от {fr:,} до {to:,} {curr}{gross}".replace(",", " ")
    #             elif fr:
    #                 salary_text = f"от {fr:,} {curr}{gross}".replace(",", " ")
    #             elif to:
    #                 salary_text = f"до {to:,} {curr}{gross}".replace(",", " ")
    #             else:
    #                 salary_text = f"Зарплата указана, но без суммы ({curr})"
    #         else:
    #             salary_text = "Не указана"
    #
    #         # Вывод карточки — внутри цикла, одинаковый отступ с остальным кодом
    #         output += f"{i:2}. {name}\n"
    #         output += f"    💰 Зарплата: {salary_text}\n"
    #         output += f"    🏙️ Город: {city}\n"
    #         output += f"    🏢 Компания: {company}\n"
    #         output += f"    📝 Описание: {description}\n"
    #         output += f"    🔗 Ссылка: {url}\n"
    #         output += "-" * 100 + "\n"
    #
    #     # После цикла
    #     print(output)
    #     return output
    #
