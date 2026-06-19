import builtins
from unittest.mock import patch

import pytest
import requests_mock as req_mock
from requests.exceptions import ConnectionError, HTTPError, Timeout

from src.api import Api_handler, Hh_handler


@pytest.fixture
def hh():
    """Фикстура для создания экземпляра Hh_handler перед каждым тестом."""
    return Hh_handler()


def make_vacancy(name="Test Dev", salary=None):
    return {
        "name": name,
        "alternate_url": "https://hh.ru/vacancy/1",
        "area": {"name": "Москва"},
        "employer": {"name": "ООО Тест"},
        "snippet": {"requirement": "Знание Python", "responsibility": "Писать код"},
        "salary": salary,
    }


# ── 1. Базовые проверки класса ──────────────────────────────────────────────


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        Api_handler()


def test_abstract_methods_are_implemented():
    assert isinstance(Hh_handler(), Api_handler)


def test_init(hh):
    assert hh._Hh_handler__base_url == "https://api.hh.ru/vacancies"
    assert hh._Hh_handler__params is None
    assert hh._Hh_handler__last_response is None


# ── 2. get_vacancies — успешные сценарии ───────────────────────────────────


def test_get_vacancies_success(hh):
    with req_mock.Mocker() as m:
        m.get(
            "https://api.hh.ru/vacancies",
            json={"items": [{"name": "Test"}]},
            status_code=200,
        )
        result = hh.get_vacancies(query="test", per_page=1)
        assert result[0]["name"] == "Test"
        assert hh._Hh_handler__last_response.status_code == 200


def test_get_vacancies_with_params(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="python", params={"area": "1"}, per_page=50)
        url = m.request_history[0].url
        assert "text=python" in url
        assert "area=1" in url
        assert "per_page=50" in url


def test_get_vacancies_empty_items(hh):
    with req_mock.Mocker() as m:
        m.get("https://api.hh.ru/vacancies", json={"items": []}, status_code=200)
        assert hh.get_vacancies("empty") == []


def test_get_vacancies_uses_num(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="test", num=30)
        assert "per_page=30" in m.request_history[0].url


def test_get_vacancies_per_page_from_params(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="test", params={"per_page": 25})
        assert "per_page=25" in m.request_history[0].url


def test_get_vacancies_per_page_clamped_to_100(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="test", per_page=999)
        assert "per_page=100" in m.request_history[0].url


def test_get_vacancies_per_page_min_is_1(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="test", per_page=0)
        assert "per_page=1" in m.request_history[0].url


def test_get_vacancies_explicit_per_page_overrides_num(hh):
    with req_mock.Mocker() as m:
        m.get(req_mock.ANY, json={"items": []}, status_code=200)
        hh.get_vacancies(query="test", num=10, per_page=77)
        assert "per_page=77" in m.request_history[0].url


# ── 3. get_vacancies — ошибки ──────────────────────────────────────────────


def test_get_vacancies_timeout_returns_empty(hh, mocker):
    mocker.patch.object(hh, "_Hh_handler__connect_api", side_effect=Timeout())
    assert hh.get_vacancies("test") == []


def test_get_vacancies_connection_error_returns_empty(hh, mocker):
    mocker.patch.object(hh, "_Hh_handler__connect_api", side_effect=ConnectionError())
    assert hh.get_vacancies("test") == []


def test_get_vacancies_http_error_returns_empty(hh, mocker):
    mock_resp = mocker.Mock(status_code=500, text="Error")
    mocker.patch.object(
        hh, "_Hh_handler__connect_api", side_effect=HTTPError(response=mock_resp)
    )
    assert hh.get_vacancies("test") == []


# ── 4. get() — обработка HTTP-ошибок ──────────────────────────────────────


def _mock_http_error(hh, mocker, status_code):
    mock_resp = mocker.Mock(status_code=status_code, text="err")
    mocker.patch.object(
        hh, "_Hh_handler__connect_api", side_effect=HTTPError(response=mock_resp)
    )


def test_get_http_error_400(hh, mocker):
    _mock_http_error(hh, mocker, 400)
    with pytest.raises(HTTPError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_http_error_403(hh, mocker):
    _mock_http_error(hh, mocker, 403)
    with pytest.raises(HTTPError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_http_error_429(hh, mocker):
    _mock_http_error(hh, mocker, 429)
    with pytest.raises(HTTPError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_http_error_500(hh, mocker):
    _mock_http_error(hh, mocker, 500)
    with pytest.raises(HTTPError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_http_error_unexpected_418(hh, mocker):
    _mock_http_error(hh, mocker, 418)
    with pytest.raises(HTTPError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_timeout_raises(hh, mocker):
    mocker.patch.object(hh, "_Hh_handler__connect_api", side_effect=Timeout())
    with pytest.raises(Timeout):
        hh.get("https://api.hh.ru/vacancies")


def test_get_connection_error_raises(hh, mocker):
    mocker.patch.object(hh, "_Hh_handler__connect_api", side_effect=ConnectionError())
    with pytest.raises(ConnectionError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_unknown_exception_raises(hh, mocker):
    mocker.patch.object(
        hh, "_Hh_handler__connect_api", side_effect=ValueError("unexpected")
    )
    with pytest.raises(ValueError):
        hh.get("https://api.hh.ru/vacancies")


def test_get_success_returns_response(hh, mocker):
    mock_resp = mocker.Mock(status_code=200)
    mocker.patch.object(hh, "_Hh_handler__connect_api", return_value=mock_resp)
    assert hh.get("https://api.hh.ru/vacancies").status_code == 200


# ── 5. __connect_api — retry-логика ───────────────────────────────────────


def test_connect_api_retries_on_429(hh, mocker):
    """3 попытки: первые две — 429, третья — 200."""
    mocker.patch("time.sleep")
    with req_mock.Mocker() as m:
        m.get(
            "https://api.hh.ru/vacancies",
            [
                {"status_code": 429},
                {"status_code": 429},
                {"json": {"items": [{"name": "ok"}]}, "status_code": 200},
            ],
        )
        result = hh.get_vacancies("test")
        assert m.call_count == 3
        assert result[0]["name"] == "ok"


def test_connect_api_all_timeout_returns_empty(hh, mocker):
    """Все 3 попытки — Timeout → get_vacancies возвращает []."""
    mocker.patch("time.sleep")
    with req_mock.Mocker() as m:
        m.get("https://api.hh.ru/vacancies", exc=Timeout())
        result = hh.get_vacancies("test")
        assert result == []
        assert m.call_count == 3


def test_connect_api_no_retry_on_403(hh, mocker):
    """403 — не временная ошибка, retry не делается."""
    mocker.patch("time.sleep")
    with req_mock.Mocker() as m:
        m.get("https://api.hh.ru/vacancies", status_code=403)
        result = hh.get_vacancies("test")
        assert result == []
        assert m.call_count == 1


# ── 6. print_vacancies_beautiful ──────────────────────────────────────────
#
# def test_print_empty(capsys):
#     Hh_handler.print_vacancies_beautiful([])
#     assert "не найдено" in capsys.readouterr().out.lower()
#
# def test_print_one_vacancy(capsys):
#     vac = make_vacancy("Python Dev", salary={"from": 100000, "to": 200000, "currency": "RUR", "gross": False})
#     Hh_handler.print_vacancies_beautiful([vac])
#     out = capsys.readouterr().out
#     assert "Python Dev" in out and "Москва" in out
#
# def test_print_salary_from_only(capsys):
#     vac = make_vacancy(salary={"from": 80000, "to": None, "currency": "RUR", "gross": True})
#     Hh_handler.print_vacancies_beautiful([vac])
#     assert "от" in capsys.readouterr().out
#
# def test_print_salary_to_only(capsys):
#     vac = make_vacancy(salary={"from": None, "to": 150000, "currency": "RUR", "gross": False})
#     Hh_handler.print_vacancies_beautiful([vac])
#     assert "до" in capsys.readouterr().out
#
# def test_print_salary_no_amount(capsys):
#     vac = make_vacancy(salary={"from": None, "to": None, "currency": "USD", "gross": False})
#     Hh_handler.print_vacancies_beautiful([vac])
#     assert "без суммы" in capsys.readouterr().out
#
# def test_print_no_salary(capsys):
#     vac = make_vacancy(salary=None)
#     Hh_handler.print_vacancies_beautiful([vac])
#     assert "Не указана" in capsys.readouterr().out
#
# def test_print_long_description_truncated(capsys):
#     vac = make_vacancy()
#     vac["snippet"]["requirement"] = "А" * 300
#     Hh_handler.print_vacancies_beautiful([vac])
#     assert "..." in capsys.readouterr().out
#
# def test_print_multiple_vacancies(capsys):
#     vacancies = [make_vacancy(f"Вакансия {i}") for i in range(3)]
#     Hh_handler.print_vacancies_beautiful(vacancies)
#     out = capsys.readouterr().out
#     for i in range(3):
#         assert f"Вакансия {i}" in out


# # ── 7. verbal=True/False ───────────────────────────────────────────────────
#
# def test_get_vacancies_verbal_true_calls_print(hh, mocker):
#     mock_print = mocker.patch.object(Hh_handler, 'print_vacancies_beautiful')
#     with req_mock.Mocker() as m:
#         m.get("https://api.hh.ru/vacancies", json={"items": [{"name": "Dev"}]}, status_code=200)
#         hh.get_vacancies("test", verbal=True)
#         mock_print.assert_called_once()
#
# def test_get_vacancies_verbal_false_no_print(hh, mocker):
#     mock_print = mocker.patch.object(Hh_handler, 'print_vacancies_beautiful')
#     with req_mock.Mocker() as m:
#         m.get("https://api.hh.ru/vacancies", json={"items": [{"name": "Dev"}]}, status_code=200)
#         hh.get_vacancies("test", verbal=False)
#         mock_print.assert_not_called()


# ── 8. post() ──────────────────────────────────────────────────────────────


def test_post_not_implemented(hh):
    with pytest.raises(NotImplementedError):
        hh.post("url")


def test_get_vacancies_timeout(hh, mocker):
    """Тест обработки Timeout: get_vacancies возвращает [] и не падает."""

    mock_connect = mocker.patch.object(hh, "_Hh_handler__connect_api")
    mock_connect.side_effect = Timeout()

    # get_vacancies глотает все ошибки и возвращает []
    result = hh.get_vacancies("test")

    assert result == [], "При Timeout должен вернуться пустой список"
    assert mock_connect.call_count == 1


def test_get_error_400(hh, mocker):
    """Тест обработки 400: get() возвращает ответ (не кидает исключение)."""

    mock_connect = mocker.patch.object(hh, "_Hh_handler__connect_api")

    mock_response = mocker.Mock(status_code=400, text="Bad params")
    mock_connect.return_value = mock_response

    # get() НЕ кидает HTTPError — просто возвращает ответ как есть
    response = hh.get("https://api.hh.ru/vacancies")

    assert response.status_code == 400
    assert mock_connect.call_count == 1


def test_connect_api_public_delegates(hh, mocker):
    """_connect_api делегирует вызов в __connect_api."""
    mock = mocker.patch.object(
        hh, "_Hh_handler__connect_api", return_value=mocker.Mock(status_code=200)
    )
    hh._connect_api("https://api.hh.ru/vacancies", {"text": "python"})
    mock.assert_called_once_with("https://api.hh.ru/vacancies", {"text": "python"})


def test_connect_api_raises_after_all_attempts(hh):
    """После 3 неудачных попыток бросается ConnectionError."""
    with req_mock.Mocker() as m:
        with patch("time.sleep"):
            m.get(
                "https://api.hh.ru/vacancies",
                [
                    {"exc": Timeout()},
                    {"exc": Timeout()},
                    {"exc": Timeout()},
                ],
            )
            with pytest.raises(builtins.ConnectionError):  # встроенный, не из requests
                hh._connect_api("https://api.hh.ru/vacancies")
