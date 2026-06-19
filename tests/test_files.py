import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.files import Json_handler
from src.vacancies import Vacancy


@pytest.fixture
def temp_json_file():
    """Фикстура: создаёт временный JSON-файл, удаляется автоматически."""
    fd, path = tempfile.mkstemp(suffix=".json")
    yield path
    os.close(fd)
    os.remove(path)  # явное удаление на всякий случай


@pytest.fixture
def tmp_json(tmp_path):
    f = tmp_path / "test.json"
    return Json_handler(filename=str(f))


@pytest.fixture
def mock_vacancy():
    v = MagicMock()
    v.id = "42"
    v.name = "Python Dev"
    v.to_dict.return_value = {"id": "42", "name": "Python Dev", "salary_from": 150000}
    return v


@pytest.fixture
def tmp_path_json(tmp_path):
    """Фикстура: путь к несуществующему JSON-файлу во временной директории.
    tmp_path — встроенная фикстура pytest, автоматически удаляет каталог после теста."""
    return str(tmp_path / "test_vacancies.json")


@pytest.fixture
def storage(tmp_path_json):
    """Фикстура: чистое пустое хранилище."""
    return Json_handler(filename=tmp_path_json)


@pytest.fixture
def sample_vacancy():
    """Фикстура: одна вакансия с минимальным набором данных."""
    return Vacancy({"id": "1", "name": "Python Developer", "salary": {"from": 100000}})


@pytest.fixture
def two_vacancies():
    """Фикстура: две вакансии с разными зарплатами и названиями."""
    vac1 = Vacancy({"id": "1", "name": "Python Developer", "salary": {"from": 100000}})
    vac2 = Vacancy({"id": "2", "name": "Java Developer", "salary": {"from": 50000}})
    return vac1, vac2


# ---------------------------------------------------------------------------
# Инициализация и open_file
# ---------------------------------------------------------------------------


def test_init_creates_empty_file(tmp_path_json):
    """Новый файл создаётся и хранилище пустое."""
    storage = Json_handler(filename=tmp_path_json)
    assert len(storage.data) == 0
    assert os.path.exists(tmp_path_json)


def test_open_file_list_format(tmp_path_json):
    """Загрузка файла в новом формате (список словарей)."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        json.dump([{"id": "1", "name": "Test"}], f)
    storage = Json_handler(filename=tmp_path_json)
    assert len(storage.data) == 1
    assert "1" in storage.data


def test_open_file_dict_format(tmp_path_json):
    """Загрузка файла в старом формате (словарь {id: вакансия})."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        json.dump({"1": {"id": "1", "name": "Old Format"}}, f)
    storage = Json_handler(filename=tmp_path_json)
    assert len(storage.data) == 1
    assert "1" in storage.data


def test_open_file_empty_content(tmp_path_json):
    """Пустой файл (пустая строка) → пустое хранилище, не падает."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        f.write("")
    storage = Json_handler(filename=tmp_path_json)
    assert storage.data == {}


def test_open_file_corrupted_json(tmp_path_json):
    """Невалидный JSON → пустое хранилище, не падает."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        f.write("not valid json {{{{")
    storage = Json_handler(filename=tmp_path_json)
    assert storage.data == {}


def test_open_file_unknown_format(tmp_path_json):
    """Файл содержит не список и не словарь → пустое хранилище."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        json.dump("just a string", f)  # строка — не list и не dict
    storage = Json_handler(filename=tmp_path_json)
    assert storage.data == {}


def test_init_filename_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    storage = Json_handler(filename=None)

    data_dir = tmp_path / "data"
    assert data_dir.is_dir()

    json_files = list(data_dir.glob("*.json"))
    assert len(json_files) == 1, "Должен создаться ровно один JSON-файл в data/"

    assert storage.data == {}


# ---------------------------------------------------------------------------
# addData
# ---------------------------------------------------------------------------


def test_addData_success(storage, sample_vacancy):
    """Вакансия добавляется, возвращает True."""
    result = storage.addData(sample_vacancy)
    assert result is True
    assert "1" in storage.data


def test_addData_persisted_to_file(storage, sample_vacancy, tmp_path_json):
    """После addData файл содержит список с одной записью."""
    storage.addData(sample_vacancy)
    with open(tmp_path_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 1


def test_addData_duplicate_returns_false(storage, sample_vacancy):
    """Попытка добавить дубль → возвращает False, размер не меняется."""
    storage.addData(sample_vacancy)
    result = storage.addData(sample_vacancy)
    assert result is False
    assert len(storage.data) == 1


def test_addData_multiple(storage, two_vacancies):
    """Несколько разных вакансий добавляются без проблем."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    assert len(storage.data) == 2


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------


def test_find_by_keyword(storage, two_vacancies):
    """Поиск по ключевому слову находит нужную вакансию."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    results = storage.find({"keyword": "python"})
    assert len(results) == 1
    assert results[0]["id"] == "1"


def test_find_by_salary(storage, two_vacancies):
    """Поиск по минимальной зарплате фильтрует вакансии правильно."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    results = storage.find({"salary_from_min": 80000})
    assert len(results) == 1
    assert results[0]["id"] == "1"


def test_find_combined(storage, two_vacancies):
    """Поиск по keyword + salary_from_min вместе."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    results = storage.find({"keyword": "python", "salary_from_min": 80000})
    assert len(results) == 1
    assert results[0]["id"] == "1"


def test_find_no_criteria_returns_all(storage, two_vacancies):
    """Поиск без критериев возвращает все вакансии."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    results = storage.find({})
    assert len(results) == 2


def test_find_no_results(storage, sample_vacancy):
    """Поиск, который ничего не найдёт → пустой список."""
    storage.addData(sample_vacancy)
    results = storage.find({"keyword": "golang"})
    assert results == []


# ---------------------------------------------------------------------------
# delete_data
# ---------------------------------------------------------------------------


def test_delete_existing(storage, sample_vacancy):
    """Удаление существующей вакансии → True, хранилище пустеет."""
    storage.addData(sample_vacancy)
    result = storage.delete_data("1")
    assert result is True
    assert "1" not in storage.data


def test_delete_persisted(storage, sample_vacancy, tmp_path_json):
    """После удаления файл тоже обновляется."""
    storage.addData(sample_vacancy)
    storage.delete_data("1")
    with open(tmp_path_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == []


def test_delete_nonexistent(storage):
    """Удаление несуществующего ID → False."""
    result = storage.delete_data("999")
    assert result is False


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_empties_storage(storage, two_vacancies):
    """clear() очищает data в памяти."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    storage.clear()
    assert len(storage.data) == 0


def test_clear_empties_file(storage, sample_vacancy, tmp_path_json):
    """clear() записывает пустой список в файл."""
    storage.addData(sample_vacancy)
    storage.clear()
    with open(tmp_path_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == []


def test_addData_after_clear(storage, sample_vacancy):
    """После clear() можно снова добавить ту же вакансию."""
    storage.addData(sample_vacancy)
    storage.clear()
    result = storage.addData(sample_vacancy)
    assert result is True
    assert len(storage.data) == 1


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------


def test_get_all_empty(storage):
    """get_all() на пустом хранилище возвращает пустой список."""
    assert storage.get_all() == []


def test_get_all_returns_list_of_dicts(storage, two_vacancies):
    """get_all() возвращает список словарей."""
    vac1, vac2 = two_vacancies
    storage.addData(vac1)
    storage.addData(vac2)
    all_vacs = storage.get_all()
    assert isinstance(all_vacs, list)
    assert len(all_vacs) == 2
    assert all(isinstance(v, dict) for v in all_vacs)


def test_open_file_dict_format1(tmp_path_json):
    """Загрузка файла в старом формате (словарь {id: вакансия})."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        json.dump({"1": {"id": "1", "name": "Old Format"}}, f)
    storage = Json_handler(filename=tmp_path_json)
    assert len(storage.data) == 1
    assert "1" in storage.data


def test_open_file_unknown_format2(tmp_path_json):
    """Файл содержит не список и не словарь → пустое хранилище."""
    with open(tmp_path_json, "w", encoding="utf-8") as f:
        json.dump("just a string", f)
    storage = Json_handler(filename=tmp_path_json)
    assert storage.data == {}


def test_init_filename_none3(tmp_path, monkeypatch):
    """filename=None → файл создаётся в подпапке data/ с именем по дате."""
    monkeypatch.chdir(tmp_path)

    storage = Json_handler(filename=None)

    # Проверяем создание папки data/
    data_dir = tmp_path / "data"
    assert data_dir.is_dir(), "Папка data/ не создалась"

    # Ищем все .json-файлы в data/
    json_files = list(data_dir.glob("*.json"))
    assert len(json_files) == 1, "Должен создаться ровно один JSON-файл в data/"

    file_name = json_files[0].name
    assert file_name.endswith(".json"), "Файл должен заканчиваться на .json"

    # Проверяем формат имени: YYYYMMDD-HHMMSS.json
    name_without_ext = file_name[:-5]  # убираем .json
    assert len(name_without_ext) == 15, "Имя без расширения должно быть 15 символов (YYYYMMDD-HHMMSS)"
    assert name_without_ext[8] == "-", "Между датой и временем должно быть тире"
    assert name_without_ext[:8].isdigit(), "Первые 8 символов — дата YYYYMMDD"
    assert name_without_ext[9:].isdigit(), "После тире — время HHMMSS"

    # Проверяем, что хранилище пустое
    assert storage.data == {}, "При создании нового файла хранилище должно быть пустым"

def test_open_file_unexpected_exception(tmp_path_json, monkeypatch):
    """Неизвестная ошибка при чтении файла → data = {}, не падает."""
    storage = Json_handler(filename=tmp_path_json)  # сначала создаём нормально
    monkeypatch.setattr(
        "builtins.open", lambda *a, **kw: (_ for _ in ()).throw(OSError("disk error"))
    )
    storage.open_file()  # теперь патчим и вызываем напрямую
    assert storage.data == {}
