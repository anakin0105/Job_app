from unittest.mock import Mock

import pytest

from main import main
from src.api import Hh_handler
from src.files import Json_handler


def test_main_menu_full_cycle(mocker, capfd):
    # Последовательность действий пользователя (теперь актуальная для меню 0-6)
    user_inputs = [
        "1",
        "python junior",
        "10",  # новый поиск
        "2",  # показать все
        "3",
        "5",  # топ-5
        "4",
        "130702522",
        "130788177",  # сравнение двух вакансий
        "5",
        "python",  # поиск по ключу
        "6",
        "1",  # удаление (выберем пункт 1 в подменю)
        "0",  # выход
    ]

    # Мокаем input — пользователь будет "нажимать" эти значения по порядку
    mocker.patch("builtins.input", side_effect=user_inputs)

    # Мокаем внешние зависимости, чтобы не ходить в интернет и не писать файлы
    mock_hh = mocker.Mock(spec=Hh_handler)
    mock_hh.get_vacancies.return_value = [{"id": "test1", "name": "Test Vacancy"}]
    mocker.patch("main.Hh_handler", return_value=mock_hh)

    mock_storage = mocker.Mock(spec=Json_handler)
    mock_storage.data = {"130702522": {"name": "QA"}, "130788177": {"name": "SysAdmin"}}
    mock_storage.get_all.return_value = list(mock_storage.data.values())
    mocker.patch("main.Json_handler", return_value=mock_storage)

    # Мокаем функции из utils — проверяем, что они вызываются
    mock_new_search = mocker.patch("main.new_search")
    mock_show_all = mocker.patch("main.show_all")
    mock_top_n = mocker.patch("main.top_n")
    mock_compare = mocker.patch("main.compare_vacancies")
    mock_find_keyword = mocker.patch("main.find_by_keyword")
    mock_delete_menu = mocker.patch("main.delete_menu")

    # Запускаем main
    main()

    # Проверяем вывод
    captured = capfd.readouterr()
    out = captured.out.lower()

    assert "до встречи!" in out
    assert "поиск вакансий (hh.ru)" in out

    # Проверяем, что все пункты меню были вызваны хотя бы раз
    assert mock_new_search.call_count >= 1, "Пункт 1 (новый поиск) не вызван"
    assert mock_show_all.call_count >= 1, "Пункт 2 (показать все) не вызван"
    assert mock_top_n.call_count >= 1, "Пункт 3 (топ N) не вызван"
    assert mock_compare.call_count >= 1, "Пункт 4 (сравнение) не вызван"
    assert mock_find_keyword.call_count >= 1, "Пункт 5 (поиск по ключу) не вызван"
    assert mock_delete_menu.call_count >= 1, "Пункт 6 (удаление) не вызван"
