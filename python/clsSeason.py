import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import PySimpleGUI as sg
from isoweek import Week
from PySimpleGUI.PySimpleGUI import Input

from utils import (get_db_connection, get_db_cursor,
                   split_seasonID_into_component_years)


class Season:

    def __init__(self):
        self.id = 0
        self.type = 'R'
        self.name = ''
        self.start_date = ''
        self.end_date = ''
        self.number_of_games = 0
        self.weeks = 0
        self.count_of_total_game_dates = 0
        self.count_of_completed_game_dates = 0

        return

    def make_season(self):
        return Season()

    def __repr__(self):
        return 'Season({})'

    def dialog(self, season: 'Season'):

        try:

            layout = [[
                    sg.Frame('Season...', layout=[
                        [
                            sg.Column(
                            [
                                [
                                    sg.Text('Season ID:', size=(15, 1)),
                                    sg.Input(season.id, size=(10, 1), enable_events=True, key='SEASON_ID', focus=True),
                                ],
                                [
                                    sg.Text('Season:', size=(14,1)),
                                    sg.Input(season.name, size=(24,1), key='SEASON_NAME', enable_events=True),
                                ],
                                [
                                    sg.Text('Season Start:', size=(14,1)),
                                    sg.Input(season.start_date, size=(10,1), key='SEASON_START', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                                [
                                    sg.Text('Total Game Dates:', size=(14,1)),
                                    sg.Input(season.count_of_completed_game_dates, size=(10,1), key='count_of_total_game_dates', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                            ], pad=(0,0), expand_x=True, expand_y=True),
                            sg.Column(
                            [
                                [
                                    sg.Text('Number of Games:', size=(14,1)),
                                    sg.Input(season.number_of_games, size=(5,1), key='Number_Of_Games', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                                [
                                    sg.Text('Weeks in Season:', size=(14,1)),
                                    sg.Input(season.weeks, size=(5,1), key='Weeks_In_Season', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                                [
                                    sg.Text('Season End:', size=(14,1)),
                                    sg.Input(season.end_date, size=(10,1), key='Season_End', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                                [
                                    sg.Text('Completed Game Dates:', size=(14,1)),
                                    sg.Input(season.count_of_completed_game_dates, size=(10,1), key='count_of_completed_game_dates', disabled=True,     disabled_readonly_background_color='dark slate gray', disabled_readonly_text_color='white'),
                                ],
                            ], pad=(0,0), expand_x=True, expand_y=True),
                        ],
                        [sg.OK(), sg.Cancel()],
                    ]),
            ]]

            dlg = sg.Window('NHL Season Selector', layout, font=("Helvetica", 10), finalize=True)

            while True:
                event, values = dlg.Read()
                if event in (None, 'Cancel'):
                    dlg.Close()
                    break
                if event == 'OK':
                    # row_number = values['_ROW_SELECTION_'][0]
                    # ID = seasons_list[row_number][0] # The first element in the row is the season oid
                    dlg.Close()
                    break

            # if not ID:
            #     sg.Popup('No selection was made.', title='askForSeason()')
            #     return None

            # season = Season().getSeason(ID=ID)

        except Exception as e:
            print(e)

        return season

    def fetch(self, **kwargs):

        sql = 'select * from Season'
        values = []
        count = 0
        for criterion in kwargs['Criteria']:
            (property, opcode, value) = criterion
            if count > 0:
                sql = f'{sql} and {property} {opcode} ?'
            else:
                sql = f'{sql} where {property} {opcode} ?'
            # Make case insensitive
            if type(value) == str:
                sql = f'{sql} COLLATE NOCASE'
            values.append(value)
            count += 1

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            if row:
                self.id = row['id']
                self.type = row['type']
                self.name = row['name']
                self.start_date = row['start_date']
                self.end_date = row['end_date']
                self.number_of_games = row['number_of_games']
                self.weeks = row['weeks']
                self.count_of_total_game_dates = row['count_of_total_game_dates']
                self.count_of_completed_game_dates = row['count_of_completed_game_dates']
        except sqlite3.Error as e:
            print('Database error: {0}'.format(e.args[0]))
        except Exception as e:
            print('Exception in fetch: {0}'.format(e.args[0]))
        finally:
            cursor.close()

        return self

    def fetch_many(self, **kwargs):

        sql = f'select * from Season'
        values = []
        if kwargs and 'Criteria' in kwargs:
            count = 0
            for criterion in kwargs['Criteria']:
                (property, opcode, value) = criterion
                if count > 0:
                    sql = f'{sql} and {property} {opcode} ?'
                else:
                    sql = f'{sql} where {property} {opcode} ?'
                if type(value) == str:
                    sql = f'{sql} COLLATE NOCASE'
                values.append(value)
                count += 1
        sql = f'{sql} order by start_date desc'

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            rows = cursor.fetchall()

        except sqlite3.Error as e:
            print('Database error: {0}'.format(e.args[0]))
        except Exception as e:
            print('Exception in fetch_many: {0}'.format(e.args[0]))
        finally:
            cursor.close()

        return rows

    def getCurrent(self):

        # allow 3 days grace from season end date
        today = datetime.now().date()

        # current season could be one of regular season, playoffs, or pre-season
        # seasons = self.fetch_many(**{'Criteria': [['start_date', '<=', today], ['end_date', '>=', today], ['type', '==', f'{season_type}']]})

        # by default, fetch_many returns seasons sorted by start_date in desc order
        seasons = self.fetch_many(**{'Criteria': [['start_date', '<=', today], ['end_date', '>=', today - timedelta(days=3)]]})

        current_seasons = []
        if len(seasons) == 0:
            seasons = self.fetch_many()
            if len(seasons) == 0:
                print('Oh. Oh. No season found.')
                return current_seasons

        # the 2022-2023 regular season overlaps the pre-season (Nashville & San Jose playing in Europe)
        for idx, row in enumerate(seasons):
            # should never be more than 2
            if idx > 1:
                break
            # Setting self caused problems. The calling method should set the season if it's required.
            # It should not be done here.
            season = Season()
            season.id = row['id']
            season.type = row['type']
            season.name = row['name']
            season.start_date = row['start_date']
            season.end_date = row['end_date']
            season.number_of_games = row['number_of_games']
            season.weeks = row['weeks']
            season.type = row['type']
            season.count_of_total_game_dates = row['count_of_total_game_dates']
            season.count_of_completed_game_dates = row['count_of_completed_game_dates']
            current_seasons.append(season)

        return current_seasons

    def getNextSeasonID(self) -> int:

        (start_year, end_year) = split_seasonID_into_component_years(season_id=self.id)

        return (start_year + 1) * 10000 + (end_year + 1)

    def getPreviousSeasonID(self) -> int:

        (start_year, end_year) = split_seasonID_into_component_years(season_id=self.id)

        return (start_year - 1) * 10000 + (end_year - 1)

    def getSeason(self, id: int, type: str='R'):

        self.fetch(**{'Criteria': [['id', '==', id], ['type', '==', type]]})

        return self

    def persist(self, connection=None):

        if not connection:
            connection = get_db_connection()

        values = [self.name, self.start_date, self.end_date, self.number_of_games, self.weeks, self.count_of_total_game_dates, self.count_of_completed_game_dates]
        values.append(self.type)
        values.append(str(self.id))
        sql = '''update Season
                    set name=?, start_date=?, end_date=?, number_of_games=?, weeks=?, count_of_total_game_dates=?, count_of_completed_game_dates=?
                    where type=? and ID=?'''
        returnCode = True
        try:
            connection.execute(sql, tuple(values))
            connection.commit()
        except sqlite3.Error as e:
            print('Database error: {0}'.format(e.args[0]))
            connection.rollback()
            returnCode = False
        except Exception as e:
            print('Exception in persist: {0}'.format(e.args[0]))
            connection.rollback()
            returnCode = False

        return returnCode

    def set_season_constants(self):

        # datetime.date(2021, 10, 12)
        season_start_date: date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        # isoweek.Week(2021, 41)
        season_start_week: Week = Week.withdate(season_start_date)
        # datetime.date(2022, 04, 30)
        season_end_date: date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        # isoweek.Week(2022, 17)
        season_end_week: Week = Week.withdate(season_end_date)
        # number of days in season
        self.DAYS_IN_SEASON = (season_end_date - season_start_date).days + 1

        # has season started?
        self.SEASON_HAS_STARTED: bool = season_start_date < date.today()
        # has season ended?
        self.SEASON_HAS_ENDED: bool = season_end_date < date.today()

        # 29
        self.WEEKS_IN_NHL_SEASON = self.weeks

        # isoweek.Week(2021, 41)
        self.THIS_ISOWEEK: Week = Week.withdate(datetime.today().date())

        # ['2021-10-10', '2021-10-11', '2021-10-12', '2021-10-13', '2021-10-14', '2021-10-15', '2021-10-16']
        self.THIS_NHL_WEEK_DATES: List[str] = []
        # if date.today().strftime('%A') == 'Sunday':
        #     THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK - 1).sunday().strftime('%Y-%m-%d'))
        # else:
        #     THIS_NHL_WEEK_DATES.append((THIS_ISOWEEK).sunday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK - 1).sunday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).monday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).tuesday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).wednesday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).thursday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).friday().strftime('%Y-%m-%d'))
        self.THIS_NHL_WEEK_DATES.append((self.THIS_ISOWEEK).saturday().strftime('%Y-%m-%d'))

        # the first element in this list is the starting isoweek 41, which is nhl week 1
        # to find the current nhl week, find the element with the isoweek, and add 1
        self.ISOWEEK_TO_NHL_WEEK: List[int] = [season_start_week + (i - 1) for i in range(1, self.WEEKS_IN_NHL_SEASON + 1)]

        if self.SEASON_HAS_ENDED is True:
            self.CURRENT_WEEK = self.WEEKS_IN_NHL_SEASON
        elif self.SEASON_HAS_STARTED is True:
            self.CURRENT_WEEK = self.ISOWEEK_TO_NHL_WEEK.index(self.THIS_ISOWEEK) + 1
        else:
            self.CURRENT_WEEK = self.ISOWEEK_TO_NHL_WEEK[0].week

        return
