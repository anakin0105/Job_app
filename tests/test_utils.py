from datetime import datetime

import pytest

from src.files import Json_handler
from src.utils import (
    delete_by_id,
    delete_menu,
    find_by_keyword,
    greeting,
    new_search,
    show_all,
    top_n,
)
from src.vacancies import Vacancy


@pytest.fixture
def tmp_path_json(tmp_path):
    return str(tmp_path / "test_vacancies.json")


@pytest.fixture
def storage(tmp_path_json):
    return Json_handler(filename=tmp_path_json)


# Псевдоним — чтобы старые тесты с mock_storage не падали
@pytest.fixture
def mock_storage(storage):
    return storage


@pytest.fixture
def sample_vacancy():
    return Vacancy({"id": "1", "name": "Python Developer", "salary": {"from": 100000}})


# 1. Тест приветствия — простой и быстрый
def test_greeting():
    morning = greeting(datetime(2025, 1, 1, 9, 0))
    evening = greeting(datetime(2025, 1, 1, 20, 0))
    assert morning == "Доброе утро"
    assert evening == "Добрый вечер"


# 2. Тест show_all — проверяем только то, что реально выводится
def test_show_all(mock_storage, capfd):
    """Тест show_all: проверяем вывод названий и ссылок (то, что реально делает функция)."""
    # Добавляем одну вакансию в формате hh.ru (чтобы зарплата парсилась)
    # ID уникальный, чтобы избежать дублей
    vac_data = {
        "id": "show_test_20250227",  # уникальный, вряд ли уже есть
        "name": "Python Developer",
        "salary": {"from": 150000, "to": 200000, "currency": "RUR"},  # вложенный salary
        "alternate_url": "https://hh.ru/vacancy/show_test",
    }

    vac = Vacancy(vac_data)
    mock_storage.addData(vac)

    show_all(mock_storage)
    out = capfd.readouterr().out

    # Проверяем ТОЛЬКО то, что реально есть в твоём show_all
    assert "Python Developer" in out, "Название вакансии должно быть в выводе"
    assert "150000" in out or "200000" in out, "Зарплата должна отобразиться"
    assert "https://hh.ru/vacancy/show_test" in out, "Ссылка должна быть видна"
    assert "Найдено" in out, "Должно быть количество вакансий"


# 3. Тест top_n — проверяем сортировку и топ-N
def test_top_n(mocker, mock_storage, capfd):
    mocker.patch("builtins.input", return_value="2")

    # Добавляем вакансии с разной зарплатой (формат hh.ru)
    mock_storage.addData(
        Vacancy({"id": "high", "name": "Senior", "salary": {"from": 250000}})
    )
    mock_storage.addData(
        Vacancy({"id": "low", "name": "Junior", "salary": {"from": 80000}})
    )

    top_n(mock_storage)
    out = capfd.readouterr().out

    assert "Топ-2:" in out
    # Проверяем, что более дорогая выше (по позиции в строке)
    assert out.find("Senior") < out.find("Junior")


# 4. Тест find_by_keyword — поиск по имени
def test_find_by_keyword(mocker, mock_storage, capfd):
    mocker.patch("builtins.input", return_value="python")

    mock_storage.addData(Vacancy({"id": "p1", "name": "Python Backend"}))
    mock_storage.addData(Vacancy({"id": "j1", "name": "Java Dev"}))

    find_by_keyword(mock_storage)
    out = capfd.readouterr().out

    assert "Найдено 1" in out or "python" in out.lower()
    assert "Python Backend" in out


# 5. Тест delete_by_id — удаление и сообщения
def test_delete_by_id(mocker, mock_storage, capfd):
    # Уникальный ID
    test_id = "del_test_123"

    # Добавляем вакансию
    vac = Vacancy({"id": test_id, "name": "Для удаления"})
    mock_storage.addData(vac)

    # Мокаем ввод ID
    mocker.patch("builtins.input", return_value=test_id)

    delete_by_id(mock_storage)

    out = capfd.readouterr().out

    assert "Удалена" in out
    assert test_id not in mock_storage.data


# 6. Тест new_search — самый сложный, но короткий
def test_new_search(mocker, mock_storage, capfd):
    mocker.patch("builtins.input", side_effect=["python", "3"])

    mock_hh = mocker.Mock()
    mock_hh.get_vacancies.return_value = [
        {"id": "new1", "name": "Python 1"},
        {"id": "new2", "name": "Python 2"},
        {"id": "dup1", "name": "Duplicate"},
    ]
    mocker.patch("src.api.Hh_handler", return_value=mock_hh)

    mock_storage.data.clear()
    mock_storage.addData(Vacancy({"id": "dup1", "name": "Duplicate"}))

    new_search(mock_hh, mock_storage)

    out = capfd.readouterr().out

    assert "Добавлено 2" in out or "Добавлено 2 вакансий" in out
    assert "1 пропущено" in out or "1 пропущено как дубли" in out
    assert "✅ Добавлена" in out


def test_delete_menu_by_id(monkeypatch, storage, sample_vacancy):
    """Выбор '1' → вызывает delete_by_id."""
    storage.addData(sample_vacancy)
    monkeypatch.setattr("builtins.input", lambda _: "1\n" if "0-2" in _ else "1")
    # проще через side_effect
    inputs = iter(["1", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    delete_menu(storage)
    assert "1" not in storage.data


def test_delete_menu_clear_confirmed(monkeypatch, storage, sample_vacancy):
    """Выбор '2' + подтверждение 'да' → storage пустой."""
    storage.addData(sample_vacancy)
    inputs = iter(["2", "да"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    delete_menu(storage)
    assert storage.get_all() == []


def test_delete_menu_clear_cancelled(monkeypatch, storage, sample_vacancy):
    """Выбор '2' + 'нет' → ничего не удаляется."""
    storage.addData(sample_vacancy)
    inputs = iter(["2", "нет"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    delete_menu(storage)
    assert len(storage.get_all()) == 1


def test_delete_menu_back(monkeypatch, storage):
    """Выбор '0' → просто возврат, ничего не падает."""
    inputs = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    delete_menu(storage)  # не должна упасть


def test_compare_vacancies_happy_path(mocker, capfd):
    mockstorage = mocker.Mock()
    mockstorage.data = {
        "123": {"id": "123", "name": "Python Dev", "salary_from": 200000},
        "456": {"id": "456", "name": "QA Engineer", "salary_from": 150000},
    }

    mocker.patch("builtins.input", side_effect=["123", "456"])
    mock_compare = mocker.patch("src.vacancies.Vacancy.compare")

    from src.utils import compare_vacancies

    compare_vacancies(mockstorage)

    # compare вызван ровно 1 раз
    assert mock_compare.call_count == 1

    # vac2 — единственный аргумент (self не в args для bound-метода)
    vac2 = mock_compare.call_args.args[0]
    assert isinstance(vac2, Vacancy)
    assert vac2.id == "456"

    # Проверяем вывод
    out = capfd.readouterr().out.lower()
    assert "сравнение" in out
    assert "отлично" in out
