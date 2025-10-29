import datetime
from pathlib import Path
from random import randint
from typing import Any, Dict, List, NamedTuple
import urllib
import urllib.parse
from filmix.database import DatabaseHandler
from filmix import DB_READ_ERROR, ID_ERROR, SUCCESS
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import fake_useragent


SESSION_STATIC_HEADERS = {
    'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24"',
    'sec-ch-ua-platform': 'Windows',
}


class CurrentTodo(NamedTuple):
    todo: Dict[str, Any]
    error: int = SUCCESS


class Todoer:
    def __init__(self, db_path: Path) -> None:
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

    def set_random_headers(self):
        current_ip = f'{randint(1,253)}.{randint(1,253)}.{randint(1,253)}.{randint(1,253)}'
        return {
            'X-Originating-IP': current_ip,
            'X-Forwarded-For': current_ip,
            'X-Remote-IP': current_ip,
            'X-Remote-Addr': current_ip,
            'X-Client-IP': current_ip,
            'X-Host': current_ip,
            'X-Forwarded-Host': current_ip,
            'User-Agent': fake_useragent.UserAgent().random,
        }

    def start_fetch(self):
        asyncio.run(self.fetch_all_statuses())

    async def fetch_all_statuses(self):
        tasks = []
        film_list = self.get_film_list()
        for idx, film in enumerate(film_list, start=1):
            last_checked = film.get('last_checked')
            if not last_checked or last_checked < datetime.datetime.now().strftime('%Y-%m-%d'):
                film['last_checked'] = datetime.datetime.now().strftime('%Y-%m-%d')
                tasks.append(self.get_status(film, idx))
        if len(tasks) > 0:
            print(f'Fetching statuses for {len(tasks)} films...')
        else:
            print('All films are up to date, no need to fetch statuses.')
        await asyncio.gather(*tasks)

    async def fetch_one_status(self, film, debug=False):
        url = film.get('url')
        origin = urllib.parse.urlparse(url).netloc
        try:
            current_headers = SESSION_STATIC_HEADERS.copy()
            current_headers = {**current_headers, **self.set_random_headers(),
                               'origin': f'https://{origin}', 'referer': f'https://{origin}/'}
            async with aiohttp.ClientSession(headers=current_headers) as session:
                async with session.get(url) as page:
                    if debug:
                        print(f'Fetching status for url {film.get("url")} with ip '
                              f'{session.headers.get("X-Forwarded-For")}')
                    await page.read()
                    if page.status == 429:
                        print('Too many requests, retrying with new IP...')
                        session.headers.update(self.set_random_headers())
                        retry = int(page.headers.get(
                            'Retry-After')) + randint(5, 10)
                        print(f'Waiting {retry} seconds to retry...')
                        await asyncio.sleep(retry)
                        if debug:
                            print(session.headers)
                        page = await session.get(url)
                        await page.read()
                        if page.status == 429:
                            print('Still too many requests, skipping...')
                            return ''
                    return await page.text()
        except Exception as ex:
            print(f'Cannot fetch url {url}, {ex}')
            return ''

    async def get_status(self, film, film_id, debug=False) -> Dict[str, Any]:
        page_content = await self.fetch_one_status(film, debug)
        soup = BeautifulSoup(page_content, 'html.parser')
        name = None
        try:
            if not film.get('name'):
                name = soup.select_one(film.get('n_selector'))
                if name:
                    film['name'] = name.text
                    self.change(film_id=film_id, name=film.get('name'))

            imdb = soup.select_one(
                'span.imdb_rating') or soup.select_one('span.imdb')
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

            if quality or imdb or name or rate_pos or rate_neg:
                if debug:
                    print(
                        f'Fetched film info: {name=}, {imdb=}, {quality=}, {rate_pos=}, {rate_neg=}')
                self.change(film_id, **film)
        except AttributeError as ex:
            print(f'Cannot get film name or quality, {ex}')

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
