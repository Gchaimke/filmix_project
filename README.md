# Simple Typer scraper
This scraper working without selenium or chromebrowser<br>
can do login if needed

## Instalation
```
git clone https://github.com/Gchaimke/filmix_project.git
cd filmix_project
pip install -r requirements.txt
python setup.py install
```
## Usage
```
# list films db
> python -m filmix list
# fetch films db from url
> python -m filmix list -f
# add film to db
> python -m filmix add https://filmix.ac/films/1
# open film with default browser
> python -m filmix open film_id
# remove film from db
> python -m filmix remove film_id
```
