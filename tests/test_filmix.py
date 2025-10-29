import asyncio
from os import read
from typer.testing import CliRunner
import pytest
import json
from filmix import (
    cli,
)

from filmix import SUCCESS, app_name, version, filmix_lib
runner = CliRunner()
tmp_path = '/tests'


def test_version():
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert f"{app_name} v{version}\n" in result.stdout


@pytest.fixture
def mock_json_file(tmp_path):
    film = [{'url': 'https://filmix.ac/films/fjuntezia/164933-podzemelya-i-drakony-chest-sredi-vorov-vibe-2023.html',
             'n_selector': 'h1.name',
             'q_selector': 'div.quality',
             'name': 'Подземелья и драконы: Честь среди воров',
             'filmix_users_rating': '567',
             'imdb': '|7.5|53966',
             'quality': 'TS 1080'}]
    db_file = tmp_path / "filmix.json"
    with db_file.open("w") as db:
        json.dump(film, db, indent=4)
    return db_file


test_data1 = {'url': 'https://filmix.ac/films/fjuntezia/164933-podzemelya-i-drakony-chest-sredi-vorov-vibe-2023.html',
              'n_selector': 'h1.name',
              'q_selector': 'div.quality',
              'name': 'Подземелья и драконы: Честь среди воров',
              'filmix_users_rating': '567',
              'imdb': '|7.5|53966',
              'quality': 'TS 1080'}

test_data2 = {'url': 'https://filmix.ac/films/fjuntezia/164933-podzemelya-i-drakony-chest-sredi-vorov-vibe-2023.html',
              'n_selector': 'h1.name',
              'q_selector': 'div.quality',
              'name': 'Подземелья и драконы: Честь среди воров',
              'filmix_users_rating': '567',
              'imdb': '|7.5|53966',
              'quality': 'TS 1080'}


@pytest.mark.parametrize(
    "url, n_selector, q_selector, expected, expected_key",
    [
        pytest.param(test_data1["url"], test_data1["n_selector"],
                     test_data1["q_selector"], 'div.quality', 'q_selector'),
        pytest.param(test_data2["url"], test_data2["n_selector"],
                     test_data2["q_selector"], 'h1.name', 'n_selector'),
    ],
)
def test_add(mock_json_file, url, n_selector, q_selector, expected, expected_key):
    todoer = filmix_lib.Todoer(mock_json_file)
    film = todoer.add(url=url, n_selector=n_selector, q_selector=q_selector)
    assert film.todo.get(expected_key) == expected
    film_list = todoer.get_film_list()
    assert len(film_list) == 2
    assert film.todo.get('url') == url


def test_remove(mock_json_file):
    todoer = filmix_lib.Todoer(mock_json_file)
    todoer.add(url='test', n_selector='test', q_selector='test')
    film_list = todoer.get_film_list()
    assert len(film_list) == 2
    film = todoer.remove(0)
    assert film.error == SUCCESS
    film_list = todoer.get_film_list()
    assert len(film_list) == 1


def test_remove_all(mock_json_file):
    todoer = filmix_lib.Todoer(mock_json_file)
    todoer.add(url='test1', n_selector='test1', q_selector='test1')
    todoer.add(url='test2', n_selector='test2', q_selector='test2')
    film_list = todoer.get_film_list()
    assert len(film_list) == 3
    todoer.remove_all()
    film_list = todoer.get_film_list()
    assert len(film_list) == 0


def test_change(mock_json_file):
    todoer = filmix_lib.Todoer(mock_json_file)
    film = todoer.change(1, name='New Name', quality='HD 1080P')
    assert film.error == SUCCESS
    read = todoer._db_handler.read()
    assert read.todo_list[0].get('name') == 'New Name'
    assert read.todo_list[0].get('quality') == 'HD 1080P'


def test_set_headers_ip(mock_json_file):
    todoer = filmix_lib.Todoer(mock_json_file)
    ip_headers = todoer.set_random_headers()
    assert 'X-Forwarded-For' in ip_headers
    assert 'X-Remote-IP' in ip_headers

