from pathlib import Path
from random import randint
import time
from typing import Any, Dict, List, NamedTuple
from filmix.database import DatabaseHandler
from filmix import DB_READ_ERROR, ID_ERROR, SUCCESS
from bs4 import BeautifulSoup
import requests


class CurrentTodo(NamedTuple):
    todo: Dict[str, Any]
    error: int


class Todoer:
    def __init__(self, db_path: Path) -> None:
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'}
        self.session.headers['sec-ch-ua'] = '"Chromium";v="110", "Not A(Brand";v="24"'
        self.session.headers['sec-ch-ua-platform'] = 'Windows'
        self.session.headers['origin'] = 'https://filmix.ac'
        self.session.headers['referer'] = 'https://filmix.ac/'
        self._db_handler = DatabaseHandler(db_path)

    def add(self, **kwargs) -> CurrentTodo:
        """Add a new to-do to the database."""
        film = {}
        for key, val in kwargs.items():
            film[key] = val
        read = self._db_handler.read()
        if read.error == DB_READ_ERROR:
            return CurrentTodo(film, read.error)
        read.todo_list.append(film)
        write = self._db_handler.write(read.todo_list)
        return CurrentTodo(film, write.error)

    def get_film_list(self) -> List[Dict[str, Any]]:
        """Return the current to-do list."""
        read = self._db_handler.read()
        return read.todo_list

    def set_headers_ip(self, prefix='185.3.'):
        ip_headers = ['X-Originating-IP', 'X-Forwarded-For', 'X-Remote-IP',
                      'X-Remote-Addr', 'X-Client-IP', 'X-Host', 'X-Forwared-Host']
        for head in ip_headers:
            self.session.headers[head] = f'{prefix}{randint(1,253)}.{randint(1,253)}'

    def get_status(self, film, id):
        self.set_headers_ip()
        page = self.session.get(film.get('url'))
        if page.status_code == 429:
            retry = page.headers.get('Retry-After')
            print(f'Waiting {retry}')
            print(self.session.headers)
            print(self.session.cookies)
            time.sleep(int(retry) + 1)
            page = self.session.get(film.get('url'))
        soup = BeautifulSoup(page.content, 'html.parser')
        try:
            if not film.get('name'):
                name = soup.select_one(film.get('n_selector'))
                if name:
                    film['name'] = name.text
                    self.change(id, name=film.get('name'))

            imdb = soup.select_one('span.imdb_rating') or soup.select_one('span.imdb')
            if imdb:
                film['imdb'] = '|'.join(imdb.text.split('\n')).rstrip('|')

            rate_pos = soup.select_one('span.ratePos') or ''
            rate_neg = soup.select_one('span.rateNeg') or ''
            if rate_pos or rate_neg:
                film['filmix_users_rating'] = f'{int(rate_pos.text)-int(rate_neg.text)}'

            quality = soup.select_one(film.get('q_selector'))
            if quality:
                film['quality'] = quality.text.rstrip()
                if not film['quality']:
                    film['quality'] = quality.attrs.get(
                        'title').strip('Фильм в высочайшем качестве')
            if not film.get('quality') and 'hdkinoteatr' in film.get('url'):
                film['quality'] = 'HD 720P'

            if film.get('quality') or film.get('imdb') or film.get('name'):
                self.change(id, **film)
        except AttributeError as ex:
            print(f'Cannot get film name or quality, {ex}')
        return film

    def change(self, film_id: int, **kwargs) -> CurrentTodo:
        """change to-do"""
        read = self._db_handler.read()
        if read.error:
            return CurrentTodo({}, read.error)
        try:
            todo = read.todo_list[film_id - 1]
        except IndexError:
            return CurrentTodo({}, ID_ERROR)
        for key, arg in kwargs.items():
            if arg:
                if not todo.get(key) or todo.get(key) != arg:
                    todo[key] = arg
                    write = self._db_handler.write(read.todo_list)
                    if write.error:
                        print(f'{write.error=}')
                        return CurrentTodo(todo, write.error)
        return CurrentTodo(todo, SUCCESS)

    def remove(self, film_id: int) -> CurrentTodo:
        """Remove a to-do from the database using its id or index."""
        read = self._db_handler.read()
        if read.error:
            return CurrentTodo({}, read.error)
        try:
            todo = read.todo_list.pop(film_id - 1)
        except IndexError:
            return CurrentTodo({}, ID_ERROR)
        write = self._db_handler.write(read.todo_list)
        return CurrentTodo(todo, write.error)

    def remove_all(self) -> CurrentTodo:
        """Remove all to-dos from the database."""
        write = self._db_handler.write([])
        return CurrentTodo({}, write.error)
