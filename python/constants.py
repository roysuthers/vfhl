# import sqlite3
from datetime import date, datetime, timedelta
import os
program_data_path = os.environ['ProgramData'] # get the path of %ProgramData%
DATABASE = os.path.join(program_data_path, 'VFHL', 'NHL Pool.db') # join the path with the database location

NHL_API_BASE_URL: str = 'https://statsapi.web.nhl.com'
NHL_API_URL: str = 'https://statsapi.web.nhl.com/api/v1'

calendar = './input/images/calendar.png'

TODAY: str = date.today()
YESTERDAY: str = (date.today() - timedelta(days=1))
