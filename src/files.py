import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class File_handler(ABC):
    """Абстрактный базовый класс (интерфейс) для работы с хранилищем вакансий.

    Определяет основные операции CRUD-подобные операции над вакансиями:
    • добавление
    • поиск по критериям
    • удаление по id
    • полная очистка хранилища

    Конкретные реализации могут работать с:
    • JSON-файлом
    • CSV / Excel
    • облачным хранилищем (Google Sheets, Notion и т.д.)

    Цель — чтобы основной код программы не зависел от формата хранения."""

    @abstractmethod
    def addData(self, data):
        """Добавляет данные в файл.

        Аргументы:
            data — объект данных (обычно экземпляр класса Vacancy)

        Поведение:
        • Если данные с таким id уже существует → обычно перезаписать или пропустить
          (решение принимает конкретная реализация)
        • Должен выбрасывать исключение при ошибке записи"""
        pass

    @abstractmethod
    def open_file(self):
        """Открывает / загружает файл хранилища.

        Поведение:
        • Должен быть вызван при инициализации хранилища
        • Данные из файла загружает в память (или создаёт пустое хранилище);
        • Может создавать новый файл, если его не существует
        • Должен быть безопасным при отсутствии файла / повреждённом файле"""
        pass

    # @abstractmethod
    # def find(self, criteria: dict):
    #     """ Ищет вакансии, удовлетворяющие заданным критериям.
    #
    #     Аргументы:
    #         criteria — словарь условий фильтрации, например:
    #             {
    #                 "salary_from_min": 100000,
    #                 "city": "Москва",
    #                 "keyword": "python",
    #                 "experience": "between1And3"
    #             }
    #             Формат ключей и значений зависит от конкретной реализации.
    #
    #     Возвращает:
    #         список найденных объектов Vacancy (или словарей — по договорённости) """
    #     pass

    @abstractmethod
    def delete_data(self, data_id):
        """Удаляет данные по их идентификатору.

        Аргументы:
            data_id — идентификатор записи (обычно строка, иногда число)

        Возвращает:
            bool — True, если запись была найдена и удалена
                   False, если запись не найдена

        При ошибке должен либо выбрасывать исключение, либо возвращать False
        (решение за конкретной реализацией)."""
        pass

    @abstractmethod
    def clear(self):
        """Полностью очищает хранилище (удаляет все вакансии).

        Используется, например, при старте программы с чистого листа
        или при команде "очистить избранное"."""
        pass


class Json_handler(File_handler):
    """Конкретная реализация хранилища вакансий в формате JSON-файла.

    Наследуется от абстрактного класса File_handler.
    Хранит вакансии в виде словаря {id: данные_вакансии} внутри JSON-файла.

    Аналогия из игры:
    Представь, что это твой «инвентарь избранного» в RPG.
    Каждая вакансия — это предмет с уникальным ID.
    Ты можешь добавлять предметы, удалять по ID, очищать весь инвентарь.
    Всё сохраняется в файле на диске (JSON).

    Важные особенности текущей реализации:
    • При добавлении вакансии файл **перезаписывается** целиком
    • Данные хранится в виде словаря, а не списка → быстрый поиск и отсутствие дублей по id
    • При инициализации без имени файла создаётся новый файл с текущей датой-временем"""

    def __init__(self, filename: Optional[str] = "all_searches.json"):
        """Инициализирует хранилище вакансий в JSON-файле.

        Параметры:
            filename : str или None
                Если передан — используем этот файл.
                Если None — создаём новый файл с именем вида 20250211-143022.json

        Поведение:
            • Если файл новый — создаётся пустой JSON []
            • Если файл уже существует — данные загружаются при вызове open_file()
            • Атрибут self.data — рабочая копия данных в памяти (словарь)"""

        if filename is not None:
            self.__filename = filename
        else:
            fn = time.strftime("%Y%m%d-%H%M%S.json")
            self.__filename = fn

        # Создаём файл только если его нет
        if not os.path.exists(self.__filename):
            with open(self.__filename, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        self.data = {}
        self.open_file()

        print(f"Загружено {len(self.data)} вакансий из {self.__filename}")

    def open_file(self):
        """Открывает / загружает файл хранилища.

        Поведение:
        • Загружает данные из файла в память (self.data)
        • Если файла нет или он пустой/повреждён — создаёт пустое хранилище
        • Функция поддерживает и старый формат (словарь), и новый (список словарей)
        • Должен быть безопасным при отсутствии файла / повреждённом файле"""

        if not os.path.exists(self.__filename):
            print(f"Файл {self.__filename} не найден → начинаем с пустого хранилища")
            self.data = {}
            return

        try:
            with open(self.__filename, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                print(f"Файл {self.__filename} пустой → загружаем 0 вакансий")
                self.data = {}
                return

            raw = json.loads(content)

            if isinstance(raw, list):
                # Новый формат — список вакансий
                loaded = {str(v.get("id")): v for v in raw if v.get("id")}
            elif isinstance(raw, dict):
                # Старый формат — словарь
                loaded = {str(k): v for k, v in raw.items()}
            else:
                print(
                    f"Неизвестный формат данных в {self.__filename} → начинаем с пустого"
                )
                loaded = {}

            self.data = loaded
            print(f"Успешно загружено {len(self.data)} вакансий из {self.__filename}")

        except json.JSONDecodeError as e:
            print(f"Файл {self.__filename} повреждён (невалидный JSON): {e}")
            print("   → начинаем с пустого хранилища")
            self.data = {}
        except UnicodeDecodeError:
            print(f"Ошибка кодировки в файле {self.__filename} — файл не в UTF-8?")
            self.data = {}
        except Exception as e:
            print(
                f"Неизвестная ошибка при загрузке {self.__filename}: {type(e).__name__} — {e}"
            )
            self.data = {}

    def _save(self) -> None:
        """Сохраняет весь словарь в файл КАК СПИСОК словарей (требование курсовой)"""
        # Превращаем в список — именно так хочет проверяющий
        data_list = list(self.data.values())

        with open(self.__filename, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

    def addData(self, data):
        """
        Добавляет вакансию в хранилище, если такой ещё нет.

        Аргументы:
            data — объект класса Vacancy

        Поведение:
            • Если вакансия с таким id уже существует то данные не добавляются
            • Если данные добавлены возвращает True, если пропущено как дубликат False
        """
        vac_id = str(data.id)
        if vac_id in self.data:
            print(f"⚠️ Вакансия с ID {vac_id} уже существует → пропуск")
            return False

        self.data[vac_id] = data.to_dict()
        self._save()
        print(f"✅ Добавлена новая вакансия: {data.name} (ID: {vac_id})")
        return True

    def find(self, criteria: Dict[str, Any]) -> List[dict]:
        """
        Очень простая фильтрация (можно потом улучшить)
        Пример criteria: {"salary_from_min": 100000, "keyword": "python"}
        """
        results = []
        keyword = criteria.get("keyword", "").lower()
        min_salary = criteria.get("salary_from_min", 0)

        for vac_dict in self.data.values():
            salary_ok = True
            if min_salary > 0:
                sal = vac_dict.get("salary_from", 0) or 0
                salary_ok = sal >= min_salary

            text_ok = True
            if keyword:
                text = " ".join(
                    [
                        vac_dict.get("name", ""),
                        vac_dict.get("requirement", ""),
                        vac_dict.get("responsibility", ""),
                    ]
                ).lower()
                text_ok = keyword in text

            if salary_ok and text_ok:
                results.append(vac_dict)

        return results

    def delete_data(self, data_id):
        """Удаляет вакансию по id. Возвращает True если была удалена"""
        vac_id = str(data_id)
        if vac_id in self.data:
            del self.data[vac_id]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Очищает весь файл"""
        self.data.clear()
        self._save()

    def get_all(self) -> List[dict]:
        """Возвращает все вакансии как список словарей"""
        return list(self.data.values())
