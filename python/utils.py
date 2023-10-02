from datetime import date, datetime, timedelta
from time import strftime, strptime
from typing import Dict, Tuple


def calculate_age(birth_date: str) -> int:
    """Calculate the age in years given a birth date in YYYY-MM-DD format."""

    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()

    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    return age

def seconds_to_string_time(seconds: int) -> str:
    """Convert seconds to a string time in MM:SS format."""

    try:
        minutes, seconds = divmod(seconds, 60)
        str_time = f"{minutes:02}:{seconds:02}"
    except ValueError:
        str_time = "00:00"

    return str_time

def split_seasonID_into_component_years(season_id: int) -> Tuple[int, int]:
    """Split a season ID into two component years."""

    try:
        season_id = int(season_id)
        first_year, second_year = divmod(season_id, 10000)
    except ValueError:
        first_year, second_year = 0, 0

    return first_year, second_year

def string_to_time(string: str) -> int:
    """Convert a string time in MM:SS format to seconds."""

    try:
        # some string values may be None, and this will fail, so set seconds = 0
        minutes, seconds = map(int, string.split(':'))
        seconds += minutes * 60
    except AttributeError:
        seconds = 0

    return seconds
