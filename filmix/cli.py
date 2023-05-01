import webbrowser
from pathlib import Path
from typing import List, Optional

import typer
from filmix import ERRORS, app_name, version, config, database, filmix_lib

app = typer.Typer()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{app_name} v{version}")
        raise typer.Exit()


@app.command()
def init(
    db_path: str = typer.Option(str(database.DEFAULT_DB_FILE_PATH),
                                "--db-path", "-db", prompt="film database location?"),
    force: bool = typer.Option(0, "--force", "-f", )
) -> None:
    """Initialize the film database."""
    app_init_error = config.init_app(db_path)
    if app_init_error:
        typer.secho(
            f'Creating config file failed with "{ERRORS[app_init_error]}"',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    db_init_error = database.init_database(Path(db_path), force)
    if db_init_error:
        typer.secho(
            f'Creating database failed with "{ERRORS[db_init_error]}"',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    else:
        typer.secho(f"The film database is {db_path}", fg=typer.colors.GREEN)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True
    )
) -> None:
    return


def get_todoer() -> filmix_lib.Todoer:
    if config.CONFIG_FILE_PATH.exists():
        db_path = database.get_database_path(config.CONFIG_FILE_PATH)
    else:
        typer.secho(
            f'Config file not found. Please, run "{app_name} init"',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    if db_path.exists():
        return filmix_lib.Todoer(db_path)
    else:
        typer.secho(
            f'Database not found. Please, run "{app_name} init"',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


@app.command()
def add(
    url: str = typer.Argument(...),
    n_selector: str = typer.Option("h1.name", "--n_selector", "-ns"),
    q_selector: str = typer.Option("div.quality", "--q_selector", "-qs"),
) -> None:
    """Add new film, first is url, options -ns, -qs"""
    todoer = get_todoer()
    film, error = todoer.add(url=url, n_selector=n_selector, q_selector=q_selector)
    if error:
        typer.secho(
            f'Adding film failed with "{ERRORS[error]}"', fg=typer.colors.RED
        )
        raise typer.Exit(1)
    else:
        typer.secho(
            f"""New url: "{film.get('url')}" \n"""
            f"""Name Selector: {film.get('n_selector')}\n"""
            f"""Quality Selector: {film.get('q_selector')}""",
            fg=typer.colors.GREEN,
        )


@app.command(name="list")
def list_all(login: bool = typer.Option(False, '--login', '-l'),
             fetch: bool = typer.Option(False, '--fetch', '-f'),
             verbose: bool = typer.Option(False, '--verbose', '-v')) -> None:
    """List all films, options --login|-l, --fetch|-f, --verbose|-v"""
    todoer = get_todoer()
    if login:
        print(todoer.login())
    film_list = todoer.get_film_list()
    if len(film_list) == 0:
        typer.secho(
            "There are no tasks in the film list yet", fg=typer.colors.RED
        )
        raise typer.Exit()
    width = 110
    table_header = f'Film List {version}'
    delimitter = (int(width/2)-len(table_header))*' '
    typer.secho(f"\n\n{delimitter}{table_header}{delimitter}",
                fg=typer.colors.GREEN, bold=True)
    spacer = "-" * width
    typer.secho(spacer, fg=typer.colors.GREEN)
    id_len = 2 if len(film_list) >= 10 else 1
    print(f'{film_list=}')

    for id, film in enumerate(film_list, 1):
        if fetch:
            todoer.get_status(film, id)
        if not film.get('name'):
            film['name'] = film.get('url')

        msg = f" {id}.{(id_len if id_len>1 and id<10 else 1)*' '} {film.get('name')}{(50-len(film.get('name')))*' '}"
        if film.get('quality'):
            msg += f"{film.get('quality')}"
        if film.get('imdb'):
            msg += (18 - len(film.get('quality'))) * \
                ' '+f"IMDB:{film.get('imdb')}"
        if film.get('filmix_users_rating'):
            msg += (18 - len(film.get('imdb'))) * ' ' + \
                f"Filmix:{film.get('filmix_users_rating')}"
        if verbose:
            msg = '| '.join([f'{key}:{val}' for key, val in film.items()])
        typer.secho(msg, fg=typer.colors.BLUE)
    typer.secho(spacer + "\n", fg=typer.colors.CYAN)
    print_menu()



@app.command()
def change(film_ids: List[int] = typer.Argument(...),
           url: str = typer.Option("", '--url', '-u'),
           name: str = typer.Option("", '--name', '-n'),
           n_selector: str = typer.Option("", "--n_selector", "-ns"),
           q_selector: str = typer.Option("", "--q_selector", "-qs")
           ) -> None:
    """Edit film, options --url, --name, -ns, -qs"""
    todoer = get_todoer()
    data = {
        'url': url,
        'name': name,
        'n_selector': n_selector,
        'q_selector': q_selector
    }
    for film_id in film_ids:
        film, error = todoer.change(film_id, **data)
        if error:
            typer.secho(
                f'Changing film # "{film_id}" failed with "{ERRORS[error]}"',
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        else:
            typer.secho(
                f"{film=}",
                fg=typer.colors.GREEN if film else typer.colors.RED,
            )


@app.command()
def remove(
    film_id: int = typer.Argument(...),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force deletion without confirmation.",
    ),
) -> None:
    """Remove a film using its film_id."""
    todoer = get_todoer()

    def _remove():
        film, error = todoer.remove(film_id)
        if error:
            typer.secho(
                f'Removing film # {film_id} failed with "{ERRORS[error]}"',
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        else:
            typer.secho(
                f"""film # {film_id}: '{film.get('name') or film.get('url')}' was removed""",
                fg=typer.colors.GREEN,
            )

    if force:
        _remove()
    else:
        film_list = todoer.get_film_list()
        try:
            film = film_list[film_id - 1]
        except IndexError:
            typer.secho("Invalid film_id", fg=typer.colors.RED)
            raise typer.Exit(1)
        delete = typer.confirm(
            f"Delete film # {film_id}: {film.get('name') or film.get('url')}?"
        )
        if delete:
            _remove()
        else:
            typer.echo("Operation canceled")


@app.command(name="clear")
def remove_all(
    force: bool = typer.Option(
        ...,
        prompt="Delete all films?",
        help="Force deletion without confirmation.",
    ),
) -> None:
    """Remove all films."""
    todoer = get_todoer()
    if force:
        error = todoer.remove_all().error
        if error:
            typer.secho(
                f'Removing films failed with "{ERRORS[error]}"',
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        else:
            typer.secho("All films were removed", fg=typer.colors.GREEN)
    else:
        typer.echo("Operation canceled")


@app.command()
def open(film_id: int = typer.Argument(...)):
    """Open in default browser 

    Args:
        film_id (int, optional): _description_. Defaults to typer.Argument(...).
    """
    try:
        todoer = get_todoer()
        film_list = todoer.get_film_list()
        webbrowser.register('vivaldi', None, webbrowser.BackgroundBrowser(
        "C:\\Program Files\\Vivaldi\Application\\vivaldi.exe"))
        webbrowser.get('vivaldi').open(film_list[film_id - 1].get('url'))
    except Exception as ex:
        print(str(ex))


def print_usefull():
    typer.secho('python -m filmix list -f', fg=typer.colors.GREEN)
    typer.secho('python -m filmix open film_id', fg=typer.colors.GREEN)
    typer.secho('python -m filmix remove film_id', fg=typer.colors.GREEN)
    typer.secho('python -m filmix add https://filmix.ac/films/1',
                fg=typer.colors.GREEN)
    typer.secho(
        'python -m filmix change film_id --url|-u --name|-n -ns -qs', fg=typer.colors.GREEN)

def print_menu():
    typer.secho('Films operations:', fg=typer.colors.GREEN)
    menu_list = ('Open browser', 'Add', 'Remove', 'List', 'Fetch', 'Print direct commands and exit')
    for id, menu in enumerate(menu_list):
        typer.secho(f'{id+1}. {menu}', fg=typer.colors.GREEN)
    typer.secho('Type 0 to exit', fg=typer.colors.GREEN)
    uinput = ''
    while True:
        uinput = typer.prompt("Select from menu")
        if uinput == '1':
            film_id = typer.prompt("Enter film id")
            if film_id.isdigit():
                open(int(film_id))
        if uinput == '2':
            url = typer.prompt("Enter film url")
            if url:
                n_selector = typer.prompt("Enter name selector or enter to use default", default='h1.name', )
                q_selector = typer.prompt("Enter quality selector or enter to use default", default='div.quality')
                if n_selector and q_selector:
                    add(url=url, n_selector=n_selector, q_selector=q_selector)
                else:
                     add(url=url)
        if uinput == '3':
            film_id = typer.prompt("Enter film id")
            if film_id.isdigit():
                remove(int(film_id))
        if uinput == '4':
            typer.clear()
            list_all(login=False, fetch=False, verbose=False)
        if uinput == '5':
            typer.clear()
            list_all(login=False, fetch=True, verbose=False)
        if uinput == '6':
            print_usefull()
            break
        if uinput == '0':
            break
    
