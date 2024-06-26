# import sqlite3
from datetime import date, datetime, timedelta
import os

program_data_path = os.environ['ProgramData'] # get the path of %ProgramData%
generated_html_path = os.path.join(program_data_path, 'VFHL', 'html')
DATABASE = os.path.join(program_data_path, 'VFHL', 'NHL Pool.db') # join the path with the database location

NHL_API_BASE_URL: str = 'https://api-web.nhle.com'
NHL_API_URL: str = 'https://api-web.nhle.com/v1'

NHL_API_SEARCH_SUGGESTIONS_URL: str = 'https://search.d3.nhle.com/api/v1/search/player'
NHL_API_SEARCH_SUGGESTIONS_PARAMS: dict = {'culture': 'en-us', 'limit': 100, 'q': '', 'active': True}

calendar = './python/input/images/calendar.png'

TODAY: str = date.today()
YESTERDAY: str = (date.today() - timedelta(days=1))
