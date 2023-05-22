from datetime import date, datetime
from typing import Dict, Tuple


def calculate_age(birth_date: str) -> int:

    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()

    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    return age

def seconds_to_string_time(seconds: int):

    str_time = ''
    try:
        str_time = "{:02}:{:02}".format(*divmod(int(seconds), 60)).strip()
    except AttributeError as e:
        if 'float' in e.args[0]:
            pass
        else:
            raise

    return str_time

def split_seasonID_into_component_years(season_id: int) -> Tuple[int, int]:

    if type(season_id) is str:
        season_id = int(season_id)

    return divmod(season_id, 10000)

def string_to_time(string: str):

    seconds = 0
    try:
        minutes, seconds = map(int, string.split(':'))
        seconds += minutes * 60
    except AttributeError as e:
        if 'float' in e.args[0]:
            pass
        else:
            raise

    return seconds
