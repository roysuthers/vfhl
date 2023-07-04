# import sqlite3
from datetime import date, datetime, timedelta
import os
# from typing import List, Dict

# import pandas as pd
# from isoweek import Week

# DATABASE = 'C:/users/Roy/NHL Pool/NHL Pool.db'
# database is in parent folder
# DATABASE = 'data/NHL Pool.db'
program_data_path = os.environ['ProgramData'] # get the path of %ProgramData%
DATABASE = os.path.join(program_data_path, 'VFHL', 'NHL Pool.db') # join the path with the database location

NHL_API_BASE_URL: str = 'https://statsapi.web.nhl.com'
NHL_API_URL: str = 'https://statsapi.web.nhl.com/api/v1'

calendar = './input/images/calendar.png'

# with sqlite3.connect(DATABASE) as connection:
#     connection.row_factory = sqlite3.Row
#     cursor = connection.execute('select * from Season order by id desc limit 1')
#     season: sqlite3.Row = cursor.fetchone()

# # datetime.date(2021, 10, 12)
# season_start_date: date = datetime.strptime(season['start_date'], '%Y-%m-%d').date()
# # isoweek.Week(2021, 41)
# season_start_week: Week = Week.withdate(season_start_date)
# # datetime.date(2022, 04, 30)
# season_end_date: date = datetime.strptime(season['end_date'], '%Y-%m-%d').date()
# # isoweek.Week(2022, 17)
# season_end_week: Week = Week.withdate(season_end_date)

# # has season started?
# SEASON_HAS_STARTED: bool = season_start_date < date.today()
# # has season ended?
# SEASON_HAS_ENDED: bool = season_end_date < date.today()

# # 29
# WEEKS_IN_NHL_SEASON = season['weeks']

# 2021-10-13'
TODAY: str = date.today()
# '2021-10-12'
YESTERDAY: str = (date.today() - timedelta(days=1))

# # isoweek.Week(2021, 41)
# THIS_ISOWEEK: Week = Week.withdate(datetime.today().date())

# # ['2021-10-10', '2021-10-11', '2021-10-12', '2021-10-13', '2021-10-14', '2021-10-15', '2021-10-16']
# THIS_NHL_WEEK_DATES: List[str] = []
# # if date.today().strftime('%A') == 'Sunday':
# #     THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK - 1).sunday().strftime('%Y-%m-%d'))
# # else:
# #     THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).sunday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK - 1).sunday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).monday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).tuesday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).wednesday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).thursday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).friday().strftime('%Y-%m-%d'))
# THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).saturday().strftime('%Y-%m-%d'))

# # the first element in this list is the starting isoweek 41, which is nhl week 1
# # to find the current nhl week, find the element with the isoweek, and add 1
# ISOWEEK_TO_NHL_WEEK: List[int] = [season_start_week + (i - 1) for i in range(1, WEEKS_IN_NHL_SEASON + 1)]

# if SEASON_HAS_ENDED is True:
#     CURRENT_WEEK = WEEKS_IN_NHL_SEASON
# elif SEASON_HAS_STARTED is True:
#     CURRENT_WEEK = ISOWEEK_TO_NHL_WEEK.index(THIS_ISOWEEK) + 1
# else:
#     CURRENT_WEEK = None
