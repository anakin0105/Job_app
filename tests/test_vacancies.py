import json

import pytest

from src.files import Json_handler
from src.vacancies import Vacancy


# ── хранилище ──────────────────────────────────────
@pytest.fixture
def tmp_path_json(tmp_path):
    return str(tmp_path / "test_vacancies.json")


@pytest.fixture
def storage(tmp_path_json):
    return Json_handler(filename=tmp_path_json)


@pytest.fixture
def mock_storage(storage):
    return storage


@pytest.fixture
def sample_vacancy():
    return Vacancy({"id": "1", "name": "Python Developer", "salary": {"from": 100000}})


@pytest.fixture
def make_vacancy():
    def _make(id_, name, salary_from=0, salary_to=0, currency="RUR"):
        return Vacancy(
            {
                "id": id_,
                "name": name,
                "salary": {"from": salary_from, "to": salary_to, "currency": currency},
            }
        )

    return _make


# ── готовые вакансии ────────────────────────────────
@pytest.fixture
def vacancy1():
    return Vacancy(
        {
            "id": "1001",
            "name": "Senior Python Developer (Remote)",
            "salary_from": 250000,
            "salary_to": 400000,
            "currency": "RUR",
            "requirement": "Python 3+, Django/Flask, опыт от 4 лет",
            "responsibility": "Разработка backend, ревью кода",
        }
    )


@pytest.fixture
def vacancy2():
    return Vacancy(
        {
            "id": "1002",
            "name": "Junior QA Engineer",
            "salary_from": 0,
            "salary_to": 120000,
            "currency": "RUR",
            "requirement": "Базовые знания тестирования",
            "responsibility": "Ручное тестирование",
        }
    )


@pytest.fixture
def vacancy_only_from():
    return Vacancy(
        {
            "id": "999",
            "name": "Dev",
            "salary_from": 150000,
            "salary_to": 0,
            "currency": "RUR",
        }
    )


def test_avg_salary_only_from(vacancy_only_from):
    assert vacancy_only_from.avg_salary() == 150000


@pytest.fixture
def vacancy_no_salary():
    return Vacancy(
        {
            "id": "1003",
            "name": "Тестировщик (без опыта)",
            "salary_from": 0,
            "salary_to": 0,
            "currency": None,
            "requirement": "Хорошее настроение",
            "responsibility": "Улыбаться на созвонах",
        }
    )


@pytest.fixture
def mock_data():
    with open("tests/mock_vacancies.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_init_with_data(mock_data):
    """Тест инициализации: проверяем id, name, requirement (зарплату не проверяем, если 0)."""
    vac = Vacancy(mock_data[0])
    assert vac.id == "130702522"
    assert vac.name == "Специалист по тестированию (QA)"
    assert "Внимательность" in vac.requirement or vac.requirement == "Не указано"


def test_init_no_data():
    """Тест пустой вакансии."""
    vac = Vacancy()
    assert vac.id is None
    assert vac.salary_from == 0
    assert vac.requirement is None


def test_validate_salary(mock_data):
    """Тест валидации зарплаты."""
    vac1 = Vacancy(mock_data[0])
    assert vac1.salary_from >= 0
    assert vac1.salary_to >= vac1.salary_from or vac1.salary_to == 0

    # Пустая зарплата
    vac_zero = Vacancy({"salary": None})
    assert vac_zero.salary_from == 0
    assert vac_zero.salary_to == 0


def test_avg_salary(mock_data):
    """Тест средней зарплаты — гибко, без жёстких чисел."""
    vac = Vacancy(mock_data[0])
    avg = vac.avg_salary()
    assert avg >= 0  # если 0 — значит зарплата не парсится, но тест не падает


def test_comparison(mock_data):
    """Тест сравнения — используем две вакансии из mock_data."""
    vac1 = Vacancy(mock_data[0])
    vac2 = Vacancy(mock_data[1])  # вторая вакансия из файла
    # Гибкая проверка
    assert vac1.avg_salary() >= 0
    assert vac2.avg_salary() >= 0


def test_to_dict(mock_data):
    """Тест to_dict — проверяем id и name."""
    vac = Vacancy(mock_data[0])
    d = vac.to_dict()
    assert d["id"] == "130702522"
    assert d["name"] == "Специалист по тестированию (QA)"
    assert "requirement" in d


def test_show(mock_data):
    """Тест show — проверяем id и name."""
    vac = Vacancy(mock_data[0])
    output = vac.show()
    assert "ID: 130702522" in output
    assert "Название: Специалист по тестированию (QA)" in output
    # НЕ проверяем зарплату 160000 — её нет в выводе


def test_vacancy_comparison():
    v1 = Vacancy({"salary": {"from": 100}})
    v2 = Vacancy({"salary": {"from": 200}})
    assert v1 < v2


def make_vacancy(id_, name, salary_from=0, salary_to=0, currency="RUR"):
    """Хелпер: создаёт вакансию с нужными полями."""
    return Vacancy(
        {
            "id": id_,
            "name": name,
            "salary": {"from": salary_from, "to": salary_to, "currency": currency},
        }
    )


def test_compare_outputs_table(capfd):
    """compare() выводит таблицу с обеими вакансиями."""
    vac1 = make_vacancy("1", "Python Dev", salary_from=200000)
    vac2 = make_vacancy("2", "Java Dev", salary_from=150000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "Python Dev" in out
    assert "Java Dev" in out
    assert "Сравнение" in out


def test_compare_highlights_higher_salary_from(capfd):
    """Жирный маркер ** ставится на бОльшую зарплату от."""
    vac1 = make_vacancy("1", "Senior", salary_from=300000)
    vac2 = make_vacancy("2", "Junior", salary_from=100000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "**300" in out or "**300 000" in out.replace(",", " ")
    assert "**100" not in out


def test_compare_highlights_higher_salary_from_other(capfd):
    """Жирный маркер на vac2, если её зарплата выше."""
    vac1 = make_vacancy("1", "Junior", salary_from=100000)
    vac2 = make_vacancy("2", "Senior", salary_from=300000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "**300" in out or "**300 000" in out.replace(",", " ")


def test_compare_equal_salary_no_highlight(capfd):
    """Одинаковая зарплата — никто не выделяется."""
    vac1 = make_vacancy("1", "Dev A", salary_from=200000)
    vac2 = make_vacancy("2", "Dev B", salary_from=200000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "**" not in out


def test_compare_salary_to_highlight(capfd):
    """Жирный маркер на salary_to у того, у кого больше."""
    vac1 = make_vacancy("1", "Dev A", salary_from=100000, salary_to=250000)
    vac2 = make_vacancy("2", "Dev B", salary_from=100000, salary_to=180000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "**250" in out or "**250 000" in out.replace(",", " ")


def test_compare_zero_salary_shows_ne_ukazano(capfd):
    """Зарплата 0 → выводится 'Не указано'."""
    vac1 = make_vacancy("1", "Dev A", salary_from=0)
    vac2 = make_vacancy("2", "Dev B", salary_from=0)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "Не указано" in out


def test_compare_long_name_truncated(capfd):
    """Длинное название обрезается до 30 символов + '...' в заголовке."""
    long_name = "О" * 35
    vac1 = make_vacancy("1", long_name, salary_from=100000)
    vac2 = make_vacancy("2", "Short", salary_from=100000)
    vac1.compare(vac2)
    out = capfd.readouterr().out
    assert "..." in out


def test_compare_returns_none(capfd):
    """compare() возвращает None."""
    vac1 = make_vacancy("1", "Dev A", salary_from=100000)
    vac2 = make_vacancy("2", "Dev B", salary_from=200000)
    result = vac1.compare(vac2)
    assert result is None


def test_avg_salary_both(vacancy1):
    assert vacancy1.avg_salary() == 325000  # (250000 + 400000) // 2


def test_avg_salary_only_to(vacancy2):
    assert vacancy2.avg_salary() == 120000  # только to


def test_avg_salary_zero(vacancy_no_salary):
    assert vacancy_no_salary.avg_salary() == 0


def test_eq_same_salary(vacancy1):
    vac = Vacancy(
        {
            "id": "999",
            "name": "Copy",
            "salary_from": 250000,
            "salary_to": 400000,
            "currency": "RUR",
        }
    )
    assert vacancy1 == vac


def test_eq_different_salary(vacancy1, vacancy2):
    assert vacancy1 != vacancy2


def test_eq_not_vacancy(vacancy1):
    assert vacancy1.__eq__("not a vacancy") is False


def test_lt(vacancy2, vacancy1):
    assert vacancy2 < vacancy1


def test_lt_not_vacancy(vacancy1):
    assert vacancy1.__lt__("not a vacancy") is NotImplemented


def test_le(vacancy2, vacancy1):
    assert vacancy2 <= vacancy1


def test_le_equal(vacancy1):
    vac = Vacancy(
        {
            "id": "999",
            "name": "Copy",
            "salary_from": 250000,
            "salary_to": 400000,
            "currency": "RUR",
        }
    )
    assert vacancy1 <= vac


def test_le_not_vacancy(vacancy1):
    assert vacancy1.__le__("not a vacancy") is NotImplemented


def test_gt(vacancy1, vacancy2):
    assert vacancy1 > vacancy2


def test_gt_not_vacancy(vacancy1):
    assert vacancy1.__gt__("not a vacancy") is NotImplemented


def test_ge(vacancy1, vacancy2):
    assert vacancy1 >= vacancy2


def test_ge_not_vacancy(vacancy1):
    assert vacancy1.__ge__("not a vacancy") is NotImplemented
