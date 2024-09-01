import datetime
import logging
import re
import sys
import traceback
import unidecode
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta
from os import path, makedirs
from pathlib import Path
from sqlite3.dbapi2 import Cursor, OperationalError
from textwrap import dedent
from typing import List, Union

import flatten_json as fj
import hockey_scraper
import jmespath as j
import numpy as np
# from numpy.lib.twodim_base import triu_indices
import pandas as pd
import PySimpleGUI as sg
import requests
import ujson as json
from dateutil import tz
# from isoweek import Week
from jmespath import functions
from numpy.core.fromnumeric import take
from unidecode import unidecode

from clsPlayer import Player
from clsPoolTeam import PoolTeam
from clsPoolTeamRoster import PoolTeamRoster
from clsSeason import Season
# from clsHockeyPool import HockeyPool
from clsTeam import Team
from constants import NHL_API_URL, TODAY, YESTERDAY, NHL_API_SEARCH_SUGGESTIONS_URL, NHL_API_SEARCH_SUGGESTIONS_PARAMS, NHL_STATS_API_URL
from utils import get_db_connection, get_iso_week_start_end_dates, inches_to_feet, split_seasonID_into_component_years, string_to_time, seconds_to_string_time


# Custom functions for jmespathfetch_data
class CustomFunctions(functions.Functions):

    @functions.signature({'types': ['boolean', 'null']})
    def _func_boolean(self, x):

        val = False if x is None else x

        return val

    @functions.signature({'types': ['number', 'null']})
    def _func_integer(self, x):

        val = 0 if x is None else x

        return val

    @functions.signature({'types': ['string', 'null']})
    def _func_string(self, s):

        val = '' if s is None else s

        return val
options = j.Options(custom_functions=CustomFunctions())

class NHL_API():

    def fill_missing_player_data(self, player_id: int) -> List:

        # The row's index is retrieved using row.name, which returns a list of (seasonID, player_id)
        player = requests.get(f'{NHL_API_URL}/player/{player_id}/landing').json()
        # But already have a 'name' column in row (e.g., Joe Thornton), so how do I set row.name without clobbering the index?
        name = j.search('firstName.default', person) + ' ' + j.search('lastName.default', person)
        team_id = player.get('currentTeamId')
        team_abbr = player.get('currentTeamAbbrev')
        position = player.get('position')
        pos = 'LW' if position == 'L' else 'RW' if position == 'R' else position

        return (name, team_id, team_abbr, pos)

    def get_nhl_dot_com_report_data(self, season: Season, report: str, position: str='skater', batch: bool=False) -> List:

        if batch:
            logger = logging.getLogger(__name__)

        year, _ = split_seasonID_into_component_years(season_id=season.id)
        game_type = '03' if season.type == 'P' else '02'
        first_game_num = 1
        last_game_num = 225

        # Set the API endpoint URL
        url_base = f'https://api.nhle.com/stats/rest/en/{position}'

        # set request parameters
        params = {
            "isAggregate": 'false',
            "isGame": 'true',
            "sort": '[{"property" : "playerId", "direction": "ASC"}, {"property" : "gameId", "direction": "ASC"}]',
            "start": 0,
            # Setting limit = 0 returns all games for game date
            "limit": 0,
            "factCayenneExp": 'gamesPlayed>=1',
            "cayenneExp": f'gameId>={year}{game_type}{str(first_game_num).zfill(4)} and gameId<={year}{game_type}{str(last_game_num).zfill(4)}'
        }

        # 'penaltyShots' report doesn't accept "gamesPlayed > 1"
        if report == 'penaltyShots':
            del params['factCayenneExp']

        rows = []
        while True:

            # Send a GET request to the API endpoint with the parameters
            response = requests.get(url=f'{url_base}/{report}', params=params)

            # Check if the request was successful (HTTP status code 200)
            if response.status_code == 200:
                # Extract the data from the JSON response
                data = response.json()['data']
                if len(data) == 0:
                    break
                rows += data
                first_game_num += 225
                last_game_num += 225
                params['cayenneExp'] = f'gameId>={year}{game_type}{str(first_game_num).zfill(4)} and gameId<={year}{game_type}{str(last_game_num).zfill(4)}'

            else:
                # Handle any errors
                msg = f'Error: {response.reason}. Response Status Code is {response.status_code}.'
                if batch:
                    logger.debug(msg)
                # else:
                #     dialog['-PROG-'].update(msg)
                #     event, values = dialog.read(timeout=10)
                return msg

        return rows

    def get_player_by_name(self, name: str, team_id: int, team_abbr: str='', pos: str='') -> json:

        try:

            params = deepcopy(NHL_API_SEARCH_SUGGESTIONS_PARAMS)
            player_json:json = None
            params['q'] = name

            for iteration in range(2):

                if iteration != 0:
                    params['active'] = False

                update_PlayerAlternateNames = False

                suggestions = requests.get(NHL_API_SEARCH_SUGGESTIONS_URL, params).json()
                idx = [i for i, x in enumerate(suggestions) if unidecode(name).lower() == unidecode(suggestions[i]['name']).lower()]

                if len(idx) != 1:
                    update_PlayerAlternateNames = True

                if len(idx) == 0 and len(suggestions) > 0:
                    names = name.split(' ')
                    if len(names) == 2:
                        first_name, last_name = name.split(' ', 1)
                    else:
                        ... # what do I do?

                    # try using last name
                    idx = [i for i, x in enumerate(suggestions) if unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower())]

                    if len(idx) > 1:
                        # try name starting with first name & ending with last name
                        idx_save = idx
                        idx = [i for i in idx  if unidecode(suggestions[i]['name']).lower().startswith(unidecode(first_name).lower()) and unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower())]

                        if len(idx) == 0:
                            idx = idx_save
                            idx = [i for i in idx if unidecode(first_name).lower().startswith(unidecode(suggestions[i]['name']).lower().split(' ', 1)[0]) and unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower())]
                            if len(idx) == 0:
                                idx = idx_save

                if len(idx) > 1:
                    idx = [i for i in idx if str(team_id) == suggestions[i]['teamId']]

                if len(idx) > 1:
                    # When scraping Fantrax player info, forwards have pos = 'F', rather than 'C", 'LW', or 'RW'
                    if pos == 'F':
                        idx = [i for i in idx if suggestions[i]['positionCode'] in ('C', 'LW', 'RW')]
                    else:
                        idx = [i for i in idx if pos == suggestions[i]['positionCode']]

                if len(idx) == 1:

                    player_json = suggestions[idx[0]]

                    if update_PlayerAlternateNames is True:
                        # Update PlayerAlternateNames
                        with get_db_connection() as connection:
                            nhl_name = player_json['name']
                            cursor = connection.cursor()
                            cursor.execute("SELECT * FROM PlayerAlternateNames WHERE nhl_name = ?", (nhl_name,))
                            result = cursor.fetchone()
                            if result:
                                # Update existing record
                                alt_names = result['alt_names'] + ', ' + name
                                cursor.execute("UPDATE PlayerAlternateNames SET alt_names = ? WHERE nhl_name = ?", (alt_names, nhl_name))
                                print(f'Updated PlayerAlternateNames table for "{nhl_name}". Set alt_names to "{alt_names}".')
                            else:
                                # Insert new record
                                cursor.execute("INSERT INTO PlayerAlternateNames (nhl_name, alt_names) VALUES (?, ?)", (nhl_name, name))
                                print(f'Added "{nhl_name}" to PlayerAlternateNames table. Set alt_names to "{name}".')
                            connection.commit()

                    return player_json

            # params['active'] = True

            # try stripping spaces from last name
            # if ' ' in last_name:
            #     last_name_no_spaces = last_name.replace(" ", "")
            #     params['q'] = f"{first_name} {last_name_no_spaces}"
            #     suggestions = requests.get(NHL_API_SEARCH_SUGGESTIONS_URL, params).json()
                # if len(suggestions) > 0:
                #     last_name = last_name_no_spaces
                #     full_name = f'{first_name} {last_name}'

            # if len(idx) == 0:
            #     params['active'] = False
            #     suggestions = requests.get(NHL_API_SEARCH_SUGGESTIONS_URL, params).json()
            #     idx = [i for i, x in enumerate(suggestions) if unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower())]

            # if len(idx) > 1:
            #     idx = [i for i, x in enumerate(suggestions) if unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower()) and str(team_id) == suggestions[i]['teamId']]

            # if len(idx) > 1 and pos != '':
            #     idx = [i for i, x in enumerate(suggestions) if unidecode(suggestions[i]['name']).lower().endswith(unidecode(last_name).lower()) and str(team_id) == suggestions[i]['teamId'] and pos == suggestions[i]['positionCode']]

            # if len(suggestions) == 0:
            #     last_name = name.rsplit(' ', 1)[1]
            #     params['q'] = last_name
            #     suggestions = requests.get(NHL_API_SEARCH_SUGGESTIONS_URL, params).json()

            # # if len(suggestions) == 0:
            # #     # raise RuntimeError(f'Exception: Player "{full_name}" not found at {NHL_API_SEARCH_SUGGESTIONS_URL}')
            # #     return None

            # if len(idx) == 1:
            #     return suggestions[idx[0]]

            # for suggestion in suggestions:
            #     if suggestion['name'].endswith(last_name):
            #         player_id = suggestion['playerId']
            #         player_json = requests.get(f'{NHL_API_URL}/player/{player_id}/landing').json()
            #         initials1 = ''.join([char for char in first_name if char.isupper()])
            #         initials2 = '.'.join([char for char in first_name if char.isupper()])
            #         player_first_name = j.search('firstName.default', player_json)
            #         if player_first_name != first_name and initials1 != player_first_name and initials2 != player_first_name:
            #             if len(first_name) > len(player_first_name):
            #                 if player_first_name not in first_name:
            #                     continue
            #             elif len(player_first_name) > len(first_name):
            #                 if first_name not in player_first_name:
            #                     continue
            #         # check that the team id is the same before accepting this player
            #         if 'currentTeamId' in player_json:
            #             if team_id != player_json.get('currentTeamId') and len(suggestions) > 1:
            #                 player_json = None
            #                 continue
            #         else:
            #             if team_id != Team().get_team_id_from_team_abbr(team_abbr=suggestion['teamId'], suppress_error=True) and len(suggestions) > 1:
            #                 player_json = None
            #                 continue
            #             # player['current_team_id'] = team_id
            #         return player_json

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f'ConnectionError: Player "{full_name}" not found at {NHL_API_SEARCH_SUGGESTIONS_URL} due to a connection error.')

        except RuntimeError:
            raise

        # get nhl team
        kwargs = {'Criteria': [['id', '==', team_id]]}
        team = Team().fetch(**kwargs)
        if team.id == 0:
            print(f'There are no NHL players with name "{name}" on {team.abbr}.')
        else:
            print(f'There are no NHL players with name "{name}" on team id {team_id}.')

        return None

    def fetch_data(self, url):
        response = requests.get(url)
        if response.status_code == 404:
            return response.status_code
        else:
            return response.json()

    def process_player(self, player, roster_status):
        player_id = player.get('id')
        first_name = j.search('firstName.default', player)
        last_name = j.search('lastName.default', player)
        player = self.fetch_data(f'{NHL_API_URL}/player/{player_id}/landing')
        position = player.get('position')
        return {
            'id': player_id,
            'fantrax_id': '',
            'first_name': first_name,
            'last_name': last_name,
            'full_name': first_name + ' ' + last_name,
            'birth_date': player.get('birthDate'),
            'height': inches_to_feet(player.get('heightInInches')) if 'heightInInches' in player else '',
            'weight': player.get('weightInPounds') if 'weightInPounds' in player else '',
            'active': player.get('isActive'),
            'roster_status': roster_status,
            'current_team_id': player.get('currentTeamId'),
            'current_team_abbr': player.get('currentTeamAbbrev'),
            'primary_position': 'LW' if position == 'L' else 'RW' if position == 'R' else position,
            'games': j.search('careerTotals.regularSeason.gamesPlayed', player),
        }

    def get_players(self, season: Season, batch: bool=False):

        request_error = False

        try:

            seasonID: int = season.id

            if batch:
                logger = logging.getLogger(__name__)
            else:
                # layout the progress dialog
                layout = [
                    [
                        sg.Text(f'Update Players...', size=(100, 3), key='-PROG-')
                    ],
                    [
                        sg.Cancel()
                    ],
                ]
                # create the dialog
                dialog = sg.Window(f'Update Players', layout, modal=True, finalize=True)

            with ThreadPoolExecutor() as executor:
                # There is no api to get a list of teams (for now), so using the current standings
                # As of May 15, 2024, getting standings by date returns an empty list
                # https://api-web.nhle.com/v1/standings/{date}
                # standings = self.fetch_data(f'{NHL_API_URL}/standings/{season.start_date}')
                # # https://api-web.nhle.com/v1/standings/now
                # standings = self.fetch_data(f'{NHL_API_URL}/standings/now')

                # standings by date works now
                standings = self.fetch_data(f'{NHL_API_URL}/standings/{season.start_date}')

                if standings == 404:
                    error_msg = standings['text']
                    msg = f'API request failed: Error message "{error_msg}"...'
                    if batch:
                        logger.debug(msg)
                    else:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                    request_error = True
                    return

                teams = [x for x in j.search('standings[*].teamAbbrev.default', standings)]

                # https://api-web.nhle.com/v1/roster/TOR/current
                # https://api-web.nhle.com/v1/roster/TOR/20222023
                # https://api-web.nhle.com/v1/prospects/TOR
                msg = f'Getting team players for {season.name} from "{NHL_API_URL}"...'
                if batch:
                    logger.debug(msg)
                else:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return

                players = []
                for team_abbr in teams:
                    roster = self.fetch_data(f'{NHL_API_URL}/roster/{team_abbr}/{seasonID}')
                    if roster == 404:
                        roster_seasonID = season.getPreviousSeasonID()
                        roster = self.fetch_data(f'{NHL_API_URL}/roster/{team_abbr}/{roster_seasonID}')
                    if roster == 404:
                        error_msg = roster['text']
                        msg = f'API request failed: Error message "{error_msg}"...'
                        if batch:
                            logger.debug(msg)
                        else:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                        request_error = True
                        return

                    prospects = self.fetch_data(f'{NHL_API_URL}/prospects/{team_abbr}')
                    if prospects == 404:
                        error_msg = prospects['text']
                        msg = f'API request failed: Error message "{error_msg}"...'
                        if batch:
                            logger.debug(msg)
                        else:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                        request_error = True
                        return

                    # roster_players = [x for x in [item for sublist in j.search('*', roster) for item in sublist]]
                    # prospect_players = [x for x in [item for sublist in j.search('*', prospects) for item in sublist]]
                    # all_players = roster_players + prospect_players

                    roster_players = [x for x in [item for sublist in j.search('*', roster) for item in sublist]]
                    prospect_players = [x for x in [item for sublist in j.search('*', prospects) for item in sublist]]

                    # Add all roster_players to all_players_dict
                    all_players_dict = {player['id']: player for player in roster_players}

                    # Only add prospect_players that are not in roster_players
                    all_players_dict.update({player['id']: player for player in prospect_players if player['id'] not in all_players_dict})

                    # Convert the dictionary back to a list
                    all_players = list(all_players_dict.values())

                    players.extend(executor.map(self.process_player, all_players, ['Y'] * len(roster_players) + ['N'] * len(prospect_players)))

            msg = 'Convert team players from json to dataframe...'
            if batch:
                logger.debug(msg)
            else:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return

            df_players = pd.DataFrame(players)
            df_players['games'].fillna(0, inplace=True)

            msg = 'Getting current players from database Player table...'
            if batch:
                logger.debug(msg)
            else:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return

            # Get a database connection
            conn = get_db_connection()

            # Read the Player table from the database
            dfPlayers = pd.read_sql(sql='select id from Player', con=conn)

            # Filter out rows where id is 0
            dfPlayers = dfPlayers[dfPlayers['id'] != 0]

            # Copy df_players and set 'id' as the index
            df = df_players.copy(deep=True)
            df.set_index('id', inplace=True)

            msg = 'Getting NHL API players not in database...'
            if batch:
                logger.debug(msg)
            else:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return

            # Remove rows in df that exist in dfPlayers
            df = df.loc[~df.index.isin(dfPlayers['id'])]

            # Drop rows with missing values
            df.dropna(inplace=True)

            # Drop duplicate rows
            df.drop_duplicates(inplace=True)

            # Reset the index
            df.reset_index(inplace=True)

            msg = 'Write new players to database Player table...'
            if batch:
                logger.debug(msg)
            else:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return

            # Write df to the Player table in the database
            df.to_sql('Player', con=conn, index=False, if_exists='append')

            msg = 'Updating database players with birthdate, height, or weight, active status, and roster status...'
            if batch:
                logger.debug(msg)
            else:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return

            # Get a database connection
            with get_db_connection() as connection:
                # Update Player table
                sql = "update Player set active = 0, roster_status = 'N', current_team_id = 0, current_team_abbr=''"
                connection.execute(sql)

                # Iterate over players
                c = connection.cursor()
                for idx, row in df_players.iterrows():
                    player_id = row['id']
                    # Update player attributes in the database
                    sql = dedent(f"""\
                        update Player
                        set height = ?,
                            weight = ?,
                            active = ?,
                            current_team_id = ?,
                            current_team_abbr = ?,
                            primary_position = ?,
                            roster_status = ?,
                            games = ?
                        where id = ?
                    """)
                    params = (row['height'], row['weight'], row['active'], row['current_team_id'], row['current_team_abbr'], row['primary_position'], row['roster_status'], int(row['games']), player_id)
                    c.execute(sql, params)

                    sql = dedent(f"""\
                        UPDATE TeamRosters
                        SET seasonID={season.id}, player_id={player_id}, team_abbr="{row['current_team_abbr']}", name="{row['first_name']} {row['last_name']}", pos="{row['primary_position']}"
                        WHERE seasonID = {season.id} AND player_id = {player_id}
                    """)
                    c.execute(sql)
                    # If no row was updated, insert a new one
                    c.execute("SELECT changes()")
                    if c.fetchone()[0] == 0:
                        sql = dedent(f"""\
                            INSERT INTO TeamRosters (seasonID, player_id, team_abbr, name, pos)
                            VALUES ({season.id}, {player_id}, "{row['current_team_abbr']}", "{row['first_name']} {row['last_name']}", "{row['primary_position']}")
                        """)
                        c.execute(sql)

                connection.commit()

        except Exception as e:
            if batch:
                logger.error(repr(e))
                raise
            else:
                sg.popup_ok(f'{Path(__file__).stem}, Line {e.__traceback__.tb_lineno}: {e}({str(e)})')

        finally:
            if not batch:
                dialog.close()
            if request_error is False:
                msg ='Update of players completed...'
            if batch:
                logger.debug(msg)
            else:
                sg.popup_notify(msg, title=sys._getframe().f_code.co_name)

        return

    def get_players_current_team(self, nhl_id: int):

        try:

            team_id = j.search('people[0].currentTeam.id', requests.get(f'{NHL_API_URL}/people/{nhl_id}').json())

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)

        return team_id

    def get_player_stats(self, season: Season, batch: bool=False):

        try:

            if batch:
                logger = logging.getLogger(__name__)
            else:
                # layout the progress dialog
                layout = [
                    [
                        sg.Text(f'Get player statistics...', size=(100, 3), key='-PROG-')
                    ],
                    [
                        sg.Cancel()
                    ],
                ]
                # create the dialog
                dialog = sg.Window(f'Get Player Statistics', layout, modal=True, finalize=True)

            season_start_date: date = datetime.strptime(season.start_date, '%Y-%m-%d').date()
            season_end_date: date = datetime.strptime(season.end_date, '%Y-%m-%d').date()
            season_started: bool = season_start_date <= date.today()
            season_over: bool = season_end_date < date.today()
            if season_started is False:
                return
            elif season_over is False:
                end_date = YESTERDAY
            elif season.id == season.getCurrent()[0].id and season.type == season.getCurrent()[0].type:
                # though the season is over, allow a few days for stats to be complete
                end_date = season_end_date + timedelta(days=2)
            else:
                # though the season is over, allow a few days for stats to be complete
                end_date = season_end_date
            end_date = date.strftime(end_date, '%Y-%m-%d')

            ####################################################################
            # get count of total game dates and currently completed game dates
            switch_to_api_nhle_com = True
            # try:
            #     season_game_dates: List = requests.get(f'{NHL_API_URL}/schedule?season={season.id}&gameType={season.type}').json()
            #     game_dates: List = requests.get(f'{NHL_API_URL}/schedule?season={season.id}&gameType={season.type}&startDate={season.start_date}&endDate={end_date}').json()
            # except requests.exceptions.ConnectionError as e:
            #     switch_to_api_nhle_com = True
            #     if batch:
            #         logger.warning(f'ConnectionError: Max retries exceeded for url host: "{NHL_API_URL}" Switching to "api.nhle.com"')

            if (switch_to_api_nhle_com):
                url_base = 'https://api.nhle.com/stats/rest/en/team/summary'

                game_type_id = '3' if season.type == 'P' else '2'

                # set request parameters
                params = {
                    "isAggregate": 'false',
                    "isGame": 'true',
                    "sort": '[{"property" : "gameDate", "direction": "ASC"}, {"property" : "teamId", "direction": "ASC"}]',
                    "start": 0,
                    # Setting limit = 0 returns all games for game date
                    "limit": 0,
                    "factCayenneExp": 'gamesPlayed>=1',
                    "cayenneExp": f'seasonId={season.id} and gameTypeId={game_type_id}'
                }

                # Send a GET request to the API endpoint with the parameters
                response = requests.get(url=f'{url_base}', params=params)

                # Check if the request was successful (HTTP status code 200)
                if response.status_code == 200:
                    # Extract the data from the JSON response
                    data = response.json()['data']
                    season.count_of_total_game_dates = 183 # hardcoding for now, 'til I figure out how to get this when statsapi.web.nhl.com is not available
                    season.count_of_completed_game_dates = len(set(d['gameDate'] for d in data if 'gameDate' in d))
                else:
                    # Handle any errors
                    msg = f'Error: {response.status_code}'
                    if batch:
                        logger.debug(msg)
                    else:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        return

            else:
                season.count_of_total_game_dates = len(season_game_dates['dates'])
                season.count_of_completed_game_dates = len(game_dates['dates'])

            season.persist()

            ####################################################################
            # Get teams to save in dictionary
            dfTeams = self.get_team_stats(season=season, game_type=season.type, batch=batch)
            if dfTeams is None: # this is usually true for upcoming season for which API call return "object not found" error
                return
            teams_dict = {}
            for x in dfTeams.itertuples():
                team_abbr = Team().get_team_abbr_from_team_id(team_id=x.id)
                teams_dict[team_abbr] = {'id': x.id, 'games': x.games}

            ####################################################################
            team_game_stats = {}
            # Set the API endpoint URL
            url_base = 'https://api.nhle.com/stats/rest/en/team/powerplaytime'

            game_type_id = '3' if season.type == 'P' else '2'

            # set request parameters
            params = {
                "isAggregate": 'false',
                "isGame": 'true',
                "sort": '[{"property" : "teamId", "direction": "ASC"}, {"property" : "gameId", "direction": "ASC"}]',
                "start": 0,
                # Setting limit = 0 returns all games for game date
                "limit": 0,
                "factCayenneExp": 'gamesPlayed>=1',
                "cayenneExp": f'seasonId={season.id} and gameTypeId={game_type_id}'
            }

            # Send a GET request to the API endpoint with the parameters
            response = requests.get(url=f'{url_base}', params=params)

            # Check if the request was successful (HTTP status code 200)
            if response.status_code == 200:
                # Extract the data from the JSON response
                rows = response.json()['data']
            else:
                # Handle any errors
                msg = f'Error: {response.status_code}'
                if batch:
                    logger.debug(msg)
                else:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    return

            # {
            #     "gameDate": "2022-10-13",
            #     "gameId": 2022020012,
            #     "gamesPlayed": 1,
            #     "goals4v3": 0,
            #     "goals5v3": 0,
            #     "goals5v4": 1,
            #     "homeRoad": "R",
            #     "opponentTeamAbbrev": "PHI",
            #     "opportunities4v3": 0,
            #     "opportunities5v3": 0,
            #     "opportunities5v4": 3,
            #     "overallPowerPlayPct": 0.33333,
            #     "pointPct": 0.00000,
            #     "powerPlayGoalsFor": 1,
            #     "powerPlayPct4v3": null,
            #     "powerPlayPct5v3": null,
            #     "powerPlayPct5v4": 0.33333,
            #     "ppOpportunities": 3,
            #     "teamFullName": "New Jersey Devils",
            #     "teamId": 1,
            #     "timeOnIce4v3": 0,
            #     "timeOnIce5v3": 0,
            #     "timeOnIce5v4": 323,
            #     "timeOnIcePp": 323
            # }
            for row in rows:
                if row['teamId'] in team_game_stats:
                    team_game_stats[row['teamId']][row['gameId']] = {
                        'date': row['gameDate'],
                        'home_road': row['homeRoad'],
                        'opp_abb': row['opponentTeamAbbrev'],
                        'toi_pp': row['timeOnIcePp']
                    }
                else:
                    team_game_stats[row['teamId']] = {
                        'team_name': row['teamFullName'],
                        row['gameId']: {
                            'date': row['gameDate'],
                            'home_road': row['homeRoad'],
                            'opp_abb': row['opponentTeamAbbrev'],
                            'toi_pp': row['timeOnIcePp']
                        }
                    }

            skater_game_stats = {}
            ###################################################################################
            # skater summary report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='summary', batch=batch)
            # {
            #   "assists":1,
            #   "evGoals":3,
            #   "evPoints":3,
            #   "faceoffWinPct":0.40000,
            #   "gameDate":"2022-12-07",
            #   "gameId":2022020412,
            #   "gameWinningGoals":1,
            #   "gamesPlayed":1,
            #   "goals":5,
            #   "homeRoad":"R",
            #   "lastName":"Thompson",
            #   "opponentTeamAbbrev":"CBJ",
            #   "otGoals":0,
            #   "penaltyMinutes":0,
            #   "playerId":8479420,
            #   "plusMinus":3,
            #   "points":6,
            #   "pointsPerGame":6.00000,
            #   "positionCode":"C",
            #   "ppGoals":2,
            #   "ppPoints":3,
            #   "shGoals":0,
            #   "shPoints":0,
            #   "shootingPct":0.55555,
            #   "shootsCatches":"R",
            #   "shots":9,
            #   "skaterFullName":"Tage Thompson",
            #   "teamAbbrev":"BUF",
            #   "timeOnIcePerGame":836.0000
            # }
            for row in rows:
                if row['gameId'] in skater_game_stats:
                    skater_game_stats[row['gameId']][row['playerId']] = row
                else:
                    skater_game_stats[row['gameId']] = {row['playerId']: row}

            ###################################################################################
            # skater miscellaneous report (e.g., hits, blocks, takeaways, giveaways)
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='realtime', batch=batch)
            # {
            #   "blockedShots":2,
            #   "blockedShotsPer60":6.92,
            #   "emptyNetAssists":0,
            #   "emptyNetGoals":0,
            #   "emptyNetPoints":0,
            #   "firstGoals":0,
            #   "gameDate":"2022-11-12",
            #   "gameId":2022020230,
            #   "gamesPlayed":1,
            #   "giveaways":0,
            #   "giveawaysPer60":0.00,
            #   "hits":12,
            #   "hitsPer60":41.57,
            #   "homeRoad":"R",
            #   "lastName":"Schenn",
            #   "missedShotCrossbar":0,
            #   "missedShotGoalpost":0,
            #   "missedShotOverNet":0,
            #   "missedShotWideOfNet":0,
            #   "missedShots":0,
            #   "opponentTeamAbbrev":"TOR",
            #   "otGoals":0,
            #   "playerId":8474568,
            #   "positionCode":"D",
            #   "shootsCatches":"R",
            #   "skaterFullName":"Luke Schenn",
            #   "takeaways":2,
            #   "takeawaysPer60":6.92,
            #   "teamAbbrev":"VAN",
            #   "timeOnIcePerGame":1039.00
            # }
            # The skater miscellaneous report is failing (as of June/24) for playoffs.
            # Other than `takeaways`, The stats collected here aren't used in Fantrax. They were for my PickupHockey league.
            if isinstance(rows, str):
                if not batch:
                    # `rows` is a message string
                    dialog['-PROG-'].update(rows)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
            else:
                for row in rows:
                    skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater scoringpergame report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='scoringpergame', batch=batch)
            # {
            #   "assists":1,
            #   "assistsPerGame":1.0000,
            #   "blockedShots":0,
            #   "blocksPerGame":0.0000,
            #   "gameDate":"2022-12-07",
            #   "gameId":2022020412,
            #   "gamesPlayed":1,
            #   "goals":5,
            #   "goalsPerGame":5.000000,
            #   "hits":0,
            #   "hitsPerGame":0.0000,
            #   "homeRoad":"R",
            #   "lastName":"Thompson",
            #   "opponentTeamAbbrev":"CBJ",
            #   "penaltyMinutes":0,
            #   "penaltyMinutesPerGame":0.000000,
            #   "playerId":8479420,
            #   "points":6,
            #   "pointsPerGame":6.000000,
            #   "positionCode":"C",
            #   "primaryAssistsPerGame":0.0000,
            #   "secondaryAssistsPerGame":1.0000,
            #   "shootsCatches":"R",
            #   "shots":9,
            #   "shotsPerGame":9.000000,
            #   "skaterFullName":"Tage Thompson",
            #   "teamAbbrev":"BUF",
            #   "timeOnIce":836,
            #   "timeOnIcePerGame":836.00,
            #   "totalPrimaryAssists":0,
            #   "totalSecondaryAssists":1
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater powerplay report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='powerplay', batch=batch)
            # {
            #   "gameDate":"2022-12-30",
            #   "gameId":2022020576,
            #   "gamesPlayed":1,
            #   "homeRoad":"H",
            #   "lastName":"Guentzel",
            #   "opponentTeamAbbrev":"NJD",
            #   "playerId":8477404,
            #   "positionCode":"L",
            #   "ppAssists":0,
            #   "ppGoals":0,
            #   "ppGoalsForPer60":0.00000,
            #   "ppGoalsPer60":0.000,
            #   "ppIndividualSatFor":0,
            #   "ppIndividualSatForPer60":0.000,
            #   "ppPoints":0,
            #   "ppPointsPer60":0.000,
            #   "ppPrimaryAssists":0,
            #   "ppPrimaryAssistsPer60":null,
            #   "ppSecondaryAssists":0,
            #   "ppSecondaryAssistsPer60":null,
            #   "ppShootingPct":0.000,
            #   "ppShots":0,
            #   "ppShotsPer60":0.000,
            #   "ppTimeOnIce":757,
            #   "ppTimeOnIcePctPerGame":0.766,
            #   "ppTimeOnIcePerGame":757.000,
            #   "skaterFullName":"Jake Guentzel",
            #   "teamAbbrev":"PIT"
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater penalties report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='penalties', batch=batch)
            # {
            #   "assists":0,
            #   "gameDate":"2022-11-26",
            #   "gameId":2022020339,
            #   "gameMisconductPenalties":1,
            #   "gamesPlayed":1,
            #   "goals":0,
            #   "homeRoad":"R",
            #   "lastName":"Glendening",
            #   "majorPenalties":1,
            #   "matchPenalties":0,
            #   "minorPenalties":1,
            #   "misconductPenalties":1,
            #   "netPenalties":-3,
            #   "netPenaltiesPer60":-13.81075,
            #   "opponentTeamAbbrev":"COL",
            #   "penalties":4,
            #   "penaltiesDrawn":1,
            #   "penaltiesDrawnPer60":4.60358,
            #   "penaltiesTakenPer60":18.41434,
            #   "penaltyMinutes":27,
            #   "penaltyMinutesPerTimeOnIce":2.07161,
            #   "penaltySecondsPerGame":1620,
            #   "playerId":8476822,
            #   "points":0,
            #   "positionCode":"C",
            #   "skaterFullName":"Luke Glendening",
            #   "teamAbbrev":"DAL",
            #   "timeOnIcePerGame":782
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater penaltyShots report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='penaltyShots', batch=batch)
            # {
            #   "gameDate":"2022-11-05",
            #   "gameId":2022020179,
            #   "homeRoad":"R",
            #   "lastName":"Marchand",
            #   "opponentTeamAbbrev":"TOR",
            #   "penaltyShotAttempts":1,
            #   "penaltyShotShootingPct":1.000000,
            #   "penaltyShotsFailed":0,
            #   "penaltyShotsGoals":1,
            #   "playerId":8473419,
            #   "positionCode":"L",
            #   "shootsCatches":"L",
            #   "skaterFullName":"Brad Marchand",
            #   "teamAbbrev":"BOS"
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater goalsForAgainst report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='goalsForAgainst', batch=batch)
            # {
            #   "assists":1,
            #   "evenStrengthGoalDifference":7,
            #   "evenStrengthGoalsAgainst":0,
            #   "evenStrengthGoalsFor":7,
            #   "evenStrengthGoalsForPct":1.000000,
            #   "evenStrengthTimeOnIcePerGame":1283.000000,
            #   "gameDate":"2023-01-14",
            #   "gameId":2022020687,
            #   "gamesPlayed":1,
            #   "goals":0,
            #   "homeRoad":"R",
            #   "lastName":"Larsson",
            #   "opponentTeamAbbrev":"CHI",
            #   "playerId":8476457,
            #   "points":1,
            #   "positionCode":"D",
            #   "powerPlayGoalFor":0,
            #   "powerPlayGoalsAgainst":1,
            #   "powerPlayTimeOnIcePerGame":7.000,
            #   "shortHandedGoalsAgainst":0,
            #   "shortHandedGoalsFor":0,
            #   "shortHandedTimeOnIcePerGame":109.000,
            #   "skaterFullName":"Adam Larsson",
            #   "teamAbbrev":"SEA"
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater shot attempt counts (5v5) report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='summaryshooting', batch=batch)
            # {
            #   "gameDate":"2023-02-10",
            #   "gameId":2022020831,
            #   "gamesPlayed":1,
            #   "homeRoad":"R",
            #   "opponentTeamAbbrev":"ANA",
            #   "playerId":8477404,
            #   "positionCode":"L",
            #   "satAgainst":5,
            #   "satAhead":28,
            #   "satBehind":null,
            #   "satClose":8,
            #   "satFor":40,
            #   "satRelative":0.344,
            #   "satTied":7,
            #   "satTotal":35,
            #   "shootsCatches":"L",
            #   "skaterFullName":"Jake Guentzel",
            #   "timeOnIcePerGame5v5":1035.00,
            #   "usatAgainst":4,
            #   "usatAhead":24,
            #   "usatBehind":null,
            #   "usatClose":5,
            #   "usatFor":32,
            #   "usatRelative":0.353,
            #   "usatTied":4,
            #   "usatTotal":28
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            # ###################################################################################
            # # skater shot attempt % (5v5) report
            # ###################################################################################
            # rows = self.get_nhl_dot_com_report_data(season=season, report='percentages', batch=batch)
            # # {
            # #   "gameDate":"2023-02-18",
            # #   "gameId":2022020891,
            # #   "gamesPlayed":1,
            # #   "homeRoad":"R",
            # #   "lastName":"Seeler",
            # #   "opponentTeamAbbrev":"VAN",
            # #   "playerId":8476372,
            # #   "positionCode":"D",
            # #   "satPercentage":0.947,
            # #   "satPercentageAhead":null,
            # #   "satPercentageBehind":null,
            # #   "satPercentageClose":0.916,
            # #   "satPercentageTied":0.833,
            # #   "satRelative":0.330,
            # #   "shootingPct5v5":null,
            # #   "shootsCatches":"L",
            # #   "skaterFullName":"Nick Seeler",
            # #   "skaterSavePct5v5":null,
            # #   "skaterShootingPlusSavePct5v5":null,
            # #   "teamAbbrev":"PHI",
            # #   "timeOnIcePerGame5v5":716.000,
            # #   "usatPercentage":0.928,
            # #   "usatPercentageAhead":null,
            # #   "usatPercentageBehind":null,
            # #   "usatPercentageTied":0.800,
            # #   "usatPrecentageClose":0.888,
            # #   "usatRelative":0.342,
            # #   "zoneStartPct5v5":0.750
            # # }
            # for row in rows:
            #     skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # skater time on ice report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='timeonice', batch=batch)
            # {
            #   "evTimeOnIce":1260,
            #   "evTimeOnIcePerGame":1260.00000,
            #   "gameDate":"2022-12-28",
            #   "gameId":2022020562,
            #   "gamesPlayed":1,
            #   "homeRoad":"R",
            #   "lastName":"Pietrangelo",
            #   "opponentTeamAbbrev":"ANA",
            #   "otTimeOnIce":236,
            #   "otTimeOnIcePerOtGame":236.00000,
            #   "playerId":8474565,
            #   "positionCode":"D",
            #   "ppTimeOnIce":353,
            #   "ppTimeOnIcePerGame":353.00000,
            #   "shTimeOnIce":443,
            #   "shTimeOnIcePerGame":443.00000,
            #   "shifts":34,
            #   "shiftsPerGame":34.00000,
            #   "shootsCatches":"R",
            #   "skaterFullName":"Alex Pietrangelo",
            #   "teamAbbrev":"VGK",
            #   "timeOnIce":2056,
            #   "timeOnIcePerGame":2056.00000,
            #   "timeOnIcePerShift":60.47058
            # }
            for row in rows:
                skater_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # goalie stats
            ###################################################################################
            goalie_game_stats = {}
            ###################################################################################
            # goalie summary report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='summary', position='goalie', batch=batch)
            # {
            #     "assists":0,
            #     "gameDate":"2022-12-13",
            #     "gameId":2022020457,
            #     "gamesPlayed":1,
            #     "gamesStarted":1,
            #     "goalieFullName":"Craig Anderson",
            #     "goals":0,
            #     "goalsAgainst":0,
            #     "goalsAgainstAverage":0.00000,
            #     "homeRoad":"H",
            #     "lastName":"Anderson",
            #     "losses":0,
            #     "opponentTeamAbbrev":"LAK",
            #     "otLosses":0,
            #     "penaltyMinutes":0,
            #     "playerId":8467950,
            #     "points":0,
            #     "savePct":1.00000,
            #     "saves":40,
            #     "shootsCatches":"L",
            #     "shotsAgainst":40,
            #     "shutouts":1,
            #     "teamAbbrev":"BUF",
            #     "ties":null,
            #     "timeOnIce":3590,
            #     "wins":1
            # }
            for row in rows:
                if row['gameId'] in goalie_game_stats:
                    goalie_game_stats[row['gameId']][row['playerId']] = row
                else:
                    goalie_game_stats[row['gameId']] = {row['playerId']: row}

            ###################################################################################
            # goalie advanced report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='advanced', position='goalie', batch=batch)
            # {
            #   "completeGamePct":1.000000,
            #   "completeGames":1,
            #   "gameDate":"2022-12-13",
            #   "gameId":2022020457,
            #   "gamesPlayed":1,
            #   "gamesStarted":1,
            #   "goalieFullName":"Craig Anderson",
            #   "goalsAgainst":0,
            #   "goalsAgainstAverage":0.00000,
            #   "goalsFor":6,
            #   "goalsForAverage":6.01671,
            #   "homeRoad":"H",
            #   "incompleteGames":0,
            #   "lastName":"Anderson",
            #   "opponentTeamAbbrev":"LAK",
            #   "playerId":8467950,
            #   "qualityStart":1,
            #   "qualityStartsPct":1.000000,
            #   "regulationLosses":0,
            #   "regulationWins":1,
            #   "savePct":1.000000,
            #   "shootsCatches":"L",
            #   "shotsAgainstPer60":40.111429,
            #   "teamAbbrev":"BUF",
            #   "timeOnIce":3590
            # }
            for row in rows:
                goalie_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # goalie savesByStrength report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='savesByStrength', position='goalie', batch=batch)
            # {
            #   "evGoalsAgainst":0,
            #   "evSavePct":1.000000,
            #   "evSaves":30,
            #   "evShotsAgainst":30,
            #   "gameDate":"2022-12-13",
            #   "gameId":2022020457,
            #   "gamesPlayed":1,
            #   "gamesStarted":1,
            #   "goalieFullName":"Craig Anderson",
            #   "goalsAgainst":0,
            #   "homeRoad":"H",
            #   "lastName":"Anderson",
            #   "losses":0,
            #   "opponentTeamAbbrev":"LAK",
            #   "otLosses":0,
            #   "playerId":8467950,
            #   "ppGoalsAgainst":0,
            #   "ppSavePct":1.000000,
            #   "ppSaves":9,
            #   "ppShotsAgainst":9,
            #   "savePct":1.000000,
            #   "saves":40,
            #   "shGoalsAgainst":0,
            #   "shSavePct":1.000000,
            #   "shSaves":1,
            #   "shShotsAgainst":1,
            #   "shootsCatches":"L",
            #   "shotsAgainst":40,
            #   "teamAbbrev":"BUF",
            #   "ties":null,
            #   "wins":1
            # }
            for row in rows:
                goalie_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # goalie startedVsRelieved report
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='startedVsRelieved', position='goalie', batch=batch)
            # {
            #   "gameDate":"2022-12-13",
            #   "gameId":2022020457,
            #   "gamesPlayed":1,
            #   "gamesRelieved":0,
            #   "gamesRelievedGoalsAgainst":0,
            #   "gamesRelievedLosses":0,
            #   "gamesRelievedOtLosses":0,
            #   "gamesRelievedSavePct":null,
            #   "gamesRelievedSaves":0,
            #   "gamesRelievedShotsAgainst":0,
            #   "gamesRelievedTies":null,
            #   "gamesRelievedWins":0,
            #   "gamesStarted":1,
            #   "gamesStartedGoalsAgainst":0,
            #   "gamesStartedLosses":0,
            #   "gamesStartedOtLosses":0,
            #   "gamesStartedSavePct":1.00000,
            #   "gamesStartedSaves":40,
            #   "gamesStartedShotsAgainst":40,
            #   "gamesStartedTies":null,
            #   "gamesStartedWins":1,
            #   "goalieFullName":"Craig Anderson",
            #   "homeRoad":"H",
            #   "lastName":"Anderson",
            #   "losses":0,
            #   "opponentTeamAbbrev":"LAK",
            #   "otLosses":0,
            #   "playerId":8467950,
            #   "savePct":1.00000,
            #   "shootsCatches":"L",
            #   "teamAbbrev":"BUF",
            #   "ties":null,
            #   "wins":1
            # }
            for row in rows:
                goalie_game_stats[row['gameId']][row['playerId']].update(row)

            ###################################################################################
            # goalie shootout report
            # there won't be a row for every game. it seems that only the games with shootouts are returned.
            ###################################################################################
            rows = self.get_nhl_dot_com_report_data(season=season, report='shootout', position='goalie', batch=batch)
            # {
            #   "careerShootoutGamesPlayed":66,
            #   "careerShootoutGoalsAllowed":77,
            #   "careerShootoutLosses":32,
            #   "careerShootoutSavePct":0.666666,
            #   "careerShootoutSaves":154,
            #   "careerShootoutShotsAgainst":231,
            #   "careerShootoutWins":34,
            #   "gameDate":"2022-11-30",
            #   "gameId":2022020361,
            #   "gamesPlayed":1,
            #   "goalieFullName":"Craig Anderson",
            #   "homeRoad":"R",
            #   "lastName":"Anderson",
            #   "opponentTeamAbbrev":"DET",
            #   "playerId":8467950,
            #   "shootoutGoalsAgainst":0,
            #   "shootoutLosses":0,
            #   "shootoutSavePct":1.000000,
            #   "shootoutSaves":3,
            #   "shootoutShotsAgainst":3,
            #   "shootoutWins":1,
            #   "shootsCatches":"L",
            #   "teamAbbrev":"BUF"
            # }
            for row in rows:
                goalie_game_stats[row['gameId']][row['playerId']].update(row)

            ##########################################################################
            # need some additional stats not available from nhl.com, for PickupHockey fantasy leagues
            # not used since 2021-2022 season
            # Get game feeds for season
            game_feeds = []
            if season.type == 'R':
                game_type_id = '2'
            elif season.type == 'P':
                game_type_id = '3'

            if not switch_to_api_nhle_com:
                ##########################################################################
                # don't use start and end dates to find game feeds, as it seems to miss some games
                scheduled_games = f'{NHL_API_URL}/schedule?season={season.id}&gameType={season.type}&expand=schedule'
                ##########################################################################

                msg = f'Getting game feeds for {season.name} from "{scheduled_games}" ...'
                if batch:
                    logger.debug(msg)
                else:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return

                game_dates: List = list(filter(lambda x: x['date'] <= end_date, requests.get(scheduled_games).json()['dates']))
                # Loop over the game packs
                for game_date in game_dates:
                    for game in game_date['games']:
                        game_feed = requests.get(f"{NHL_API_URL}/game/{game['gamePk']}/feed/live").json()
                        game_feeds.append(game_feed)

                msg = 'Processing game feeds...'
                if batch:
                    logger.debug(msg)
                else:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return

                # Get player game stats
                player_game_stats = []
                for game in game_feeds:

                    # only want "Final" games
                    game_data = j.search('gameData', game)
                    if j.search('status.detailedState', game_data) != 'Final':
                        continue

                    # *******************************************************************************************************************
                    # *******************************************************************************************************************
                    # Get scoring plays
                    gwg_event = list(filter(lambda x:
                        x["about"]["periodType"] in ("REGULAR", 'OVERTIME')
                        and x["result"]["eventTypeId"] == "GOAL"
                        and x['result']['gameWinningGoal'] is True,
                        game['liveData']['plays']['allPlays']
                    ))
                    if len(gwg_event) == 0:
                        # should be SHOOTOUT
                        continue
                    gwg_event = gwg_event[0]
                    gwg_players = list(filter(lambda x: x["playerType"] != "Goalie", gwg_event['players']))
                    for player in gwg_players:
                        player_type = player['playerType']
                        period_type = gwg_event['about']['periodType']
                        points_gw = 0
                        points_ot = 0
                        assists_gw = 0
                        assists_ot = 0
                        if player_type == 'Scorer':
                            points_gw = 1
                            if period_type == 'OVERTIME':
                                points_ot = 1
                        elif player_type == 'Assist':
                            points_gw = 1
                            assists_gw = 1
                            if period_type == 'OVERTIME':
                                points_ot = 1
                                assists_ot = 1

                        player_game_stat = {
                            'player_id': player['player']['id'],
                            'gamePk': game['gamePk'],
                            'points_ot': points_ot,
                            'points_gw': points_gw,
                            'assists_ot': assists_ot,
                            'assists_gw': assists_gw,
                        }
                        player_game_stats.append(player_game_stat)

                # update skater_game_stats & goalie_game_stats
                for stats in player_game_stats:
                    if stats['player_id'] in goalie_game_stats[stats['gamePk']]:
                        # goalies can get assists or goals, actually
                        goalie_game_stats[stats['gamePk']][stats['player_id']].update(stats)
                    else:
                        skater_game_stats[stats['gamePk']][stats['player_id']].update(stats)

            # ##########################################################################
            # # write skater_game_stats to database table
            # df_stats = pd.DataFrame.from_dict({(i,j): skater_game_stats[i][j] for i in skater_game_stats.keys() for j in skater_game_stats[i].keys()}, orient='index')
            # # sort column names lexicographically
            # df_stats = df_stats.reindex(sorted(df_stats.columns), axis=1)
            # df_stats.to_sql('skater_games_stats', con=get_db_connection(), index=False, if_exists='replace')

            ##########################################################################
            # build player game stats for skaters
            player_game_stats = []
            for gameId in skater_game_stats:
                for playerId in skater_game_stats[gameId]:
                    player = skater_game_stats[gameId][playerId]
                    player_game_stat = {}

                    player_game_stat['assists_en'] = player['emptyNetAssists'] if 'emptyNetAssists' in player else 0
                    player_game_stat['assists_gw'] = player['assists_gw'] if 'assists_gw' in player else 0
                    player_game_stat['assists_ot'] = player['assists_ot'] if 'assists_ot' in player else 0
                    player_game_stat['assists_pp'] = player['ppAssists']
                    player_game_stat['assists_sh'] = player['shPoints'] - player['shGoals']
                    player_game_stat['assists'] = player['assists']
                    player_game_stat['assists1'] = player['totalPrimaryAssists']
                    player_game_stat['assists2'] = player['totalSecondaryAssists']
                    player_game_stat['blocked'] = player['blockedShots']
                    player_game_stat['corsi_against'] = player['satAgainst'] if 'satAgainst' in player else np.nan
                    player_game_stat['corsi_for'] = player['satFor'] if 'satFor' in player else np.nan
                    player_game_stat['date'] = player['gameDate']
                    # player_game_stat['even_goals_against_on_ice'] = player['evenStrengthGoalsAgainst']
                    # player_game_stat['even_goals_for_on_ice'] = player['evenStrengthGoalsFor']
                    # player_game_stat['even_shots_against_on_ice'] = int(player['evenStrengthGoalsAgainst'] / (1 - player['skaterSavePct5v5'])) if player['evenStrengthGoalsAgainst'] and player['skaterSavePct5v5'] and (1 - player['skaterSavePct5v5']) != 0 else 0
                    # player_game_stat['even_shots_for_on_ice'] = int(player['evenStrengthGoalsFor'] / player['shootingPct5v5']) if player['evenStrengthGoalsFor'] and player['shootingPct5v5'] and player['shootingPct5v5'] != 0 else 0
                    player_game_stat['evg_on_ice'] = player['evenStrengthGoalsFor']
                    player_game_stat['evg_point'] = player['evPoints']
                    player_game_stat['faceoff%'] = player['faceoffWinPct']
                    player_game_stat['fenwick_against'] = player['usatAgainst'] if 'usatAgainst' in player else np.nan
                    player_game_stat['fenwick_for'] = player['usatFor'] if 'usatFor' in player else np.nan
                    player_game_stat['game_misconduct_penalties'] = player['gameMisconductPenalties']
                    player_game_stat['game_type'] = season.type
                    player_game_stat['gamePk'] = player['gameId']
                    player_game_stat['games_started'] = np.nan
                    player_game_stat['goals_against'] = np.nan
                    player_game_stat['goals_en'] = player['emptyNetGoals'] if 'emptyNetGoals' in player else 0
                    player_game_stat['goals_gw'] = player['gameWinningGoals']
                    player_game_stat['goals_ot'] = player['otGoals']
                    player_game_stat['goals_pp'] = player['ppGoals']
                    player_game_stat['goals_ps'] = player['penaltyShotsGoals'] if 'penaltyShotsGoals' in player else np.nan
                    player_game_stat['goals_sh'] = player['shGoals']
                    player_game_stat['goals'] = player['goals']
                    player_game_stat['hattricks'] = 1 if player['goals']>=3 else 0
                    player_game_stat['hits'] = player['hits']
                    player_game_stat['home_away'] = 'home' if player['homeRoad']=='H' else 'away'
                    player_game_stat['losses'] = np.nan
                    player_game_stat['major_penalties'] = player['majorPenalties']
                    player_game_stat['match_penalties'] = player['matchPenalties']
                    player_game_stat['minor_penalties'] = player['minorPenalties']
                    player_game_stat['misconduct_penalties'] = player['misconductPenalties']
                    player_game_stat['missed_shots'] = player['missedShots'] if 'missedShots' in player else 0
                    player_game_stat['missed_shots_crossbar'] = player['missedShotCrossbar'] if 'missedShotCrossbar' in player else 0
                    player_game_stat['missed_shots_goalpost'] = player['missedShotGoalpost'] if 'missedShotGoalpost' in player else 0
                    player_game_stat['name'] = player['skaterFullName']
                    player_game_stat['opp_abbr'] = player['opponentTeamAbbrev']
                    player_game_stat['opp_id'] = teams_dict[player['opponentTeamAbbrev']]['id']
                    player_game_stat['penalties'] = player['penalties']
                    player_game_stat['pim'] = player['penaltyMinutes']
                    player_game_stat['player_id'] = player['playerId']
                    player_game_stat['plus_minus'] = player['plusMinus']
                    player_game_stat['points_en'] = player['emptyNetPoints'] if 'emptyNetPoints' in player else 0
                    player_game_stat['points_gw'] = player['points_gw'] if 'points_gw' in player else 0
                    player_game_stat['points_ot'] = player['points_ot'] if 'points_ot' in player else 0
                    player_game_stat['points_pp'] = player['ppPoints']
                    player_game_stat['points_sh'] = player['shPoints']
                    player_game_stat['points'] = player['points']
                    player_game_stat['pos'] = f"{player['positionCode']}W" if player['positionCode'] in ('L', 'R') else player['positionCode']
                    player_game_stat['ppg_on_ice'] = player['powerPlayGoalFor']
                    player_game_stat['ppg_point'] = player['ppPoints']
                    player_game_stat['quality_starts'] = np.nan
                    player_game_stat['saves_even'] = np.nan
                    player_game_stat['saves_pp'] = np.nan
                    player_game_stat['saves_sh'] = np.nan
                    player_game_stat['saves'] = np.nan
                    player_game_stat['save%_even'] = np.nan
                    player_game_stat['save%_pp'] = np.nan
                    player_game_stat['save%_sh'] = np.nan
                    player_game_stat['save%'] = np.nan
                    player_game_stat['seasonID'] = season.id
                    player_game_stat['shifts'] = player['shifts']
                    player_game_stat['shot%'] = player['shootingPct']
                    player_game_stat['shots_against'] = np.nan
                    player_game_stat['shots_even'] = np.nan
                    player_game_stat['shots_powerplay'] = player['ppShots']
                    player_game_stat['shots_pp'] = np.nan
                    player_game_stat['shots_sh'] = np.nan
                    player_game_stat['shots'] = player['shots']
                    player_game_stat['shutouts'] = np.nan
                    player_game_stat['takeaways'] = player['takeaways'] if 'takeaways' in player else 0
                    player_game_stat['team_abbr'] = player['teamAbbrev']
                    player_game_stat['team_id'] = teams_dict[player['teamAbbrev']]['id']
                    player_game_stat['team_toi_pp'] = seconds_to_string_time(team_game_stats[player_game_stat['team_id']][player_game_stat['gamePk']]['toi_pp']) if player_game_stat['gamePk'] in team_game_stats[player_game_stat['team_id']] else '00:00'
                    player_game_stat['toi_even'] = seconds_to_string_time(player['evTimeOnIce'])
                    player_game_stat['toi_pp'] = seconds_to_string_time(player['ppTimeOnIce'])
                    player_game_stat['toi_sh'] = seconds_to_string_time(player['shTimeOnIce'])
                    player_game_stat['toi'] = seconds_to_string_time(player['timeOnIce'])
                    player_game_stat['wins_ot'] = np.nan
                    player_game_stat['wins_so'] = np.nan
                    player_game_stat['wins'] = np.nan

                    player_game_stats.append(player_game_stat)

            # ##########################################################################
            # # write goalie_game_stats to database table
            # df_stats = pd.DataFrame.from_dict({(i,j): goalie_game_stats[i][j] for i in goalie_game_stats.keys() for j in goalie_game_stats[i].keys()}, orient='index')
            # # add positionCode column
            # df_stats['positionCode'] = 'G'
            # # sort column names lexicographically
            # df_stats = df_stats.reindex(sorted(df_stats.columns), axis=1)
            # df_stats.to_sql('goalie_game_stats', con=get_db_connection(), index=False, if_exists='replace')

            ##########################################################################
            # build player game stats for goalies
            for gameId in goalie_game_stats:
                for playerId in goalie_game_stats[gameId]:
                    player = goalie_game_stats[gameId][playerId]
                    player_game_stat = {}
                    shootoutWins = 0 if 'shootoutWins' not in player else player['shootoutWins']

                    player_game_stat['assists_en'] = np.nan
                    player_game_stat['assists_gw'] = np.nan
                    player_game_stat['assists_ot'] = np.nan
                    player_game_stat['assists_pp'] = np.nan
                    player_game_stat['assists_sh'] = np.nan
                    player_game_stat['assists'] = player['assists']
                    player_game_stat['assists1'] = np.nan
                    player_game_stat['assists2'] = np.nan
                    player_game_stat['blocked'] = np.nan
                    player_game_stat['corsi_against'] =  np.nan
                    player_game_stat['corsi_for'] =  np.nan
                    player_game_stat['date'] = player['gameDate']
                    # player_game_stat['even_goals_against_on_ice'] = np.nan
                    # player_game_stat['even_goals_for_on_ice'] = np.nan
                    # player_game_stat['even_shots_against_on_ice'] = np.nan
                    # player_game_stat['even_shots_for_on_ice'] = np.nan
                    player_game_stat['evg_on_ice'] = np.nan
                    player_game_stat['evg_point'] = np.nan
                    player_game_stat['faceoff%'] = np.nan
                    player_game_stat['fenwick_against'] = np.nan
                    player_game_stat['fenwick_for'] = np.nan
                    player_game_stat['game_misconduct_penalties'] = np.nan
                    player_game_stat['game_type'] = season.type
                    player_game_stat['gamePk'] = player['gameId']
                    player_game_stat['games_started'] = player['gamesStarted']
                    player_game_stat['goals_against'] = player['goalsAgainst']
                    player_game_stat['goals_en'] = np.nan
                    player_game_stat['goals_gw'] = np.nan
                    player_game_stat['goals_ot'] = np.nan
                    player_game_stat['goals_pp'] = np.nan
                    player_game_stat['goals_ps'] = np.nan
                    player_game_stat['goals_sh'] = np.nan
                    player_game_stat['goals'] = player['goals']
                    player_game_stat['hattricks'] = np.nan
                    player_game_stat['hits'] = np.nan
                    player_game_stat['home_away'] = 'home' if player['homeRoad']=='H' else 'away'
                    player_game_stat['losses'] = player['losses']
                    player_game_stat['major_penalties'] = np.nan
                    player_game_stat['match_penalties'] = np.nan
                    player_game_stat['minor_penalties'] = np.nan
                    player_game_stat['misconduct_penalties'] = np.nan
                    player_game_stat['missed_shots'] = np.nan
                    player_game_stat['missed_shots_crossbar'] = np.nan
                    player_game_stat['missed_shots_goalpost'] = np.nan
                    player_game_stat['name'] = player['goalieFullName']
                    player_game_stat['opp_abbr'] = player['opponentTeamAbbrev']
                    player_game_stat['opp_id'] = teams_dict[player['opponentTeamAbbrev']]['id']
                    player_game_stat['penalties'] = np.nan
                    player_game_stat['pim'] = player['penaltyMinutes']
                    player_game_stat['player_id'] = player['playerId']
                    player_game_stat['plus_minus'] = np.nan
                    player_game_stat['points_en'] = np.nan
                    player_game_stat['points_gw'] = np.nan
                    player_game_stat['points_ot'] = np.nan
                    player_game_stat['points_pp'] = np.nan
                    player_game_stat['points_sh'] = np.nan
                    player_game_stat['points'] = player['points']
                    player_game_stat['pos'] = 'G'
                    player_game_stat['ppg_on_ice'] = np.nan
                    player_game_stat['ppg_point'] = np.nan
                    player_game_stat['quality_starts'] = player['qualityStart']
                    player_game_stat['saves_even'] = player['evSaves']
                    player_game_stat['saves_pp'] = player['ppSaves']
                    player_game_stat['saves_sh'] = player['shSaves']
                    player_game_stat['saves'] = player['saves']
                    player_game_stat['save%_even'] = player['evSavePct']
                    player_game_stat['save%_pp'] = player['ppSavePct']
                    player_game_stat['save%_sh'] = player['shSavePct']
                    player_game_stat['save%'] = player['savePct'] * 100 if player['savePct'] != None else np.nan
                    player_game_stat['seasonID'] = season.id
                    player_game_stat['shifts'] = np.nan
                    player_game_stat['shot%'] = np.nan
                    player_game_stat['shots_against'] = player['shotsAgainst']
                    player_game_stat['shots_even'] = player['evShotsAgainst']
                    player_game_stat['shots_powerplay'] = np.nan
                    player_game_stat['shots_pp'] = player['ppShotsAgainst']
                    player_game_stat['shots_sh'] = player['shShotsAgainst']
                    player_game_stat['shots'] = np.nan
                    player_game_stat['shutouts'] = player['shutouts']
                    player_game_stat['takeaways'] = np.nan
                    player_game_stat['team_abbr'] = player['teamAbbrev']
                    player_game_stat['team_id'] = teams_dict[player['teamAbbrev']]['id']
                    player_game_stat['team_toi_pp'] = np.nan
                    player_game_stat['toi_even'] = np.nan
                    player_game_stat['toi_pp'] = np.nan
                    player_game_stat['toi_sh'] = np.nan
                    player_game_stat['toi'] = seconds_to_string_time(player['timeOnIce'])
                    player_game_stat['wins_ot'] = 1 if player['wins']==1 and player['regulationWins']==0 and shootoutWins==0 else 0
                    player_game_stat['wins_so'] = player['shootoutWins'] if 'shootoutWins' in player else np.nan
                    player_game_stat['wins'] = player['wins']

                    player_game_stats.append(player_game_stat)

            dfPlayerGameStats = pd.DataFrame(player_game_stats)

            # *******************************************************************************************************************
            # *******************************************************************************************************************
            # Aggregate dfPlayerGameStats into dfPlayerStats
            dfTemp = dfPlayerGameStats.copy(deep=True)
            # Drop columns not needed
            dfTemp.drop(columns=[
                'date',
                'home_away',
                'opp_id',
                'opp_abbr',
            ], inplace=True)

            # add toi_sec, toi_even_sec, toi_pp_sec, & toi_sh_sec, for aggregation
            # added "x!=x" condition for cases where the string value is NaN
            dfTemp['toi_sec'] = dfTemp['toi'].apply(lambda x: 0 if x in (None, '') or x!=x else string_to_time(x))
            dfTemp['toi_even_sec'] = dfTemp['toi_even'].apply(lambda x: 0 if x in (None, '') or x!=x else string_to_time(x))
            dfTemp['toi_pp_sec'] = dfTemp['toi_pp'].apply(lambda x: 0 if x in (None, '') or x!=x else string_to_time(x))
            dfTemp['toi_sh_sec'] = dfTemp['toi_sh'].apply(lambda x: 0 if x in (None, '') or x!=x else string_to_time(x))

            # Aggregate data
            dfPlayerStats = dfTemp.groupby(['player_id']).aggregate({
                'seasonID': 'last',
                'name': 'last',
                'pos': 'last',
                'team_id': 'last',
                'team_abbr': 'last',
                'gamePk': 'count',
                'shifts': 'sum',
                'assists_en': 'sum',
                'assists_gw': 'sum',
                'assists_ot': 'sum',
                'assists_pp': 'sum',
                'assists_sh': 'sum',
                'assists1': 'sum',
                'assists2': 'sum',
                'assists': 'sum',
                'blocked': 'sum',
                'corsi_against': 'sum',
                'corsi_for': 'sum',
                'fenwick_against': 'sum',
                'fenwick_for': 'sum',
                'game_type': 'last',
                'games_started': 'sum',
                'goals_against': 'sum',
                'goals_en': 'sum',
                'goals_gw': 'sum',
                'goals_ot': 'sum',
                'goals_pp': 'sum',
                'goals_ps': 'sum',
                'goals_sh': 'sum',
                'goals': 'sum',
                'hattricks': 'sum',
                'hits': 'sum',
                'losses': 'sum',
                'pim': 'sum',
                'penalties': 'sum',
                'minor_penalties': 'sum',
                'major_penalties': 'sum',
                'misconduct_penalties': 'sum',
                'major_penalties': 'sum',
                'missed_shots': 'sum',
                'missed_shots_crossbar': 'sum',
                'missed_shots_goalpost': 'sum',
                'plus_minus': 'sum',
                'points_en': 'sum',
                'points_gw': 'sum',
                'points_ot': 'sum',
                'points_pp': 'sum',
                'points_sh': 'sum',
                'points': 'sum',
                'quality_starts': 'sum',
                'saves': 'sum',
                'saves_even': 'sum',
                'saves_pp': 'sum',
                'saves_sh': 'sum',
                'shots': 'sum',
                'shots_even': 'sum',
                'shots_powerplay': 'sum',
                'shots_pp': 'sum',
                'shots_sh': 'sum',
                'shots_against': 'sum',
                'shutouts': 'sum',
                'takeaways': 'sum',
                'toi_sec': 'sum',
                'toi_even_sec': 'sum',
                'toi_pp_sec': 'sum',
                'toi_sh_sec': 'sum',
                'wins': 'sum',
                'wins_so': 'sum',
                'wins_ot': 'sum',
            })
            dfPlayerStats.rename(columns={'gamePk': 'games', 'game_type': 'season_type'}, inplace=True)

            dfPlayerStats['team_games'] = dfPlayerStats.apply(lambda x: teams_dict[x['team_abbr']]['games'] if pd.isna(x['team_abbr']) is False else x['team_games'], axis='columns')
            del dfTemp

            # Calculate percentages
            dfPlayerStats['shot%'] = dfPlayerStats.apply(lambda row: round((row['goals']/row['shots']) * 100, 2) if row['shots'] > 0 else 0.0 if row['shots'] == 0 else np.nan, axis='columns')

            # Set toi string values
            dfPlayerStats['toi'] = dfPlayerStats['toi_sec'].apply(lambda x: 0 if x in (None, '') else seconds_to_string_time(x))
            dfPlayerStats['toi_even'] = dfPlayerStats['toi_even_sec'].apply(lambda x: 0 if x in (None, '') else seconds_to_string_time(x))
            dfPlayerStats['toi_pp'] = dfPlayerStats['toi_pp_sec'].apply(lambda x: 0 if x in (None, '') else seconds_to_string_time(x))
            dfPlayerStats['toi_sh'] = dfPlayerStats['toi_sh_sec'].apply(lambda x: 0 if x in (None, '') else seconds_to_string_time(x))

            # convert time-on-ice seconds to string formatted as mm:ss
            dfPlayerStats['toi_pg'] = (dfPlayerStats['toi_sec']/dfPlayerStats['games']/60).astype(int).map('{:02d}'.format) + (dfPlayerStats['toi_sec']/dfPlayerStats['games']%60).astype(int).map(':{:02d}'.format)
            dfPlayerStats['toi_even_pg'] = (dfPlayerStats['toi_even_sec']/dfPlayerStats['games']/60).astype(int).map('{:02d}'.format) + (dfPlayerStats['toi_even_sec']/dfPlayerStats['games']%60).astype(int).map(':{:02d}'.format)
            dfPlayerStats['toi_pp_pg'] = (dfPlayerStats['toi_pp_sec']/dfPlayerStats['games']/60).astype(int).map('{:02d}'.format) + (dfPlayerStats['toi_pp_sec']/dfPlayerStats['games']%60).astype(int).map(':{:02d}'.format)
            dfPlayerStats['toi_sh_pg'] = (dfPlayerStats['toi_sh_sec']/dfPlayerStats['games']/60).astype(int).map('{:02d}'.format) + (dfPlayerStats['toi_sh_sec']/dfPlayerStats['games']%60).astype(int).map(':{:02d}'.format)

            # gaa
            dfPlayerStats['gaa'] = dfPlayerStats.apply(lambda x: (x['goals_against'] / x['toi_sec'] * 3600 if x['toi_sec'] != 0 else np.nan), axis='columns')
            # save%
            dfPlayerStats['save%'] = dfPlayerStats.apply(lambda x: (x['saves'] / x['shots_against']) if x['shots_against'] != 0 else np.nan, axis='columns')
            # save%_pp
            dfPlayerStats['save%_pp'] = dfPlayerStats.apply(lambda x: (x['saves_pp'] / x['shots_pp']) if x['shots_pp'] != 0 else np.nan, axis='columns')
            # save%_sh
            dfPlayerStats['save%_sh'] = dfPlayerStats.apply(lambda x: (x['saves_sh'] / x['shots_sh']) if x['shots_sh'] != 0 else np.nan, axis='columns')
            # save%_even
            dfPlayerStats['save%_even'] = dfPlayerStats.apply(lambda x: (x['saves_even'] / x['shots_even'] if x['shots_even'] != 0 else np.nan), axis='columns')

            # Drop columns not needed
            dfPlayerStats.drop(columns=[
                'toi_sec',
                'toi_even_sec',
                'toi_pp_sec',
                'toi_sh_sec',
            ], inplace=True)

            # For some reason, some players have duplicate rows
            dfPlayerStats.drop_duplicates(inplace=True)

            # dtypes for dfPlayerGameStats.to_sql
            dtypes = {
                'assists_en': 'INTEGER',
                'assists_gw': 'INTEGER',
                'assists_ot': 'INTEGER',
                'assists_pp': 'INTEGER',
                'assists_sh': 'INTEGER',
                'assists': 'INTEGER',
                'assists1': 'INTEGER',
                'assists2': 'INTEGER',
                'blocked': 'INTEGER',
                'corsi_against': 'INTEGER',
                'corsi_for': 'INTEGER',
                # 'even_goals_against_on_ice': 'INTEGER',
                # 'even_goals_for_on_ice': 'INTEGER',
                # 'even_shots_against_on_ice': 'INTEGER',
                # 'even_shots_for_on_ice': 'INTEGER',
                'fenwick_against': 'INTEGER',
                'fenwick_for': 'INTEGER',
                'games_started': 'INTEGER',
                'games': 'INTEGER',
                'goals_against': 'INTEGER',
                'goals_en': 'INTEGER',
                'goals_gw': 'INTEGER',
                'goals_ot': 'INTEGER',
                'goals_pp': 'INTEGER',
                'goals_sh': 'INTEGER',
                'goals_ps': 'INTEGER',
                'goals': 'INTEGER',
                'hattricks': 'INTEGER',
                'hits': 'INTEGER',
                'losses': 'INTEGER',
                'pim': 'INTEGER',
                'penalties': 'INTEGER',
                'minor_penalties': 'INTEGER',
                'major_penalties': 'INTEGER',
                'misconduct_penalties': 'INTEGER',
                'game_misconduct_penalties': 'INTEGER',
                'match_penalties': 'INTEGER',
                'missed_shots': 'INTEGER',
                'missed_shots_crossbar': 'INTEGER',
                'missed_shots_goalpost': 'INTEGER',
                'plus_minus': 'INTEGER',
                'points_en': 'INTEGER',
                'points_gw': 'INTEGER',
                'points_ot': 'INTEGER',
                'points_pp': 'INTEGER',
                'points_sh': 'INTEGER',
                'points': 'INTEGER',
                'quality_starts': 'INTEGER',
                'saves_even': 'INTEGER',
                'saves_pp': 'INTEGER',
                'saves_sh': 'INTEGER',
                'saves': 'INTEGER',
                'shifts': 'INTEGER',
                'shots_against': 'INTEGER',
                'shots_even': 'INTEGER',
                'shots_pp': 'INTEGER',
                'shots_sh': 'INTEGER',
                'shots': 'INTEGER',
                'shots_powerplay': 'INTEGER',
                'shutouts': 'INTEGER',
                'takeaways': 'INTEGER',
                'wins': 'INTEGER',
                'wins_ot': 'INTEGER',
                'wins_so': 'INTEGER',
            }

            # some players are on a team, but not "officially" on the team roster, primarily contract disputes (e.g., Brady Tkachuk in 2021-2022)
            # first, iterate though pool teams for season
            missing_team_roster_players = []
            if not switch_to_api_nhle_com and season.id == season.getCurrent()[0].id:
                ####################################
                # Get team rosters
                sql = f'select * from TeamRosters where seasonID={season.id}'
                team_rosters = pd.read_sql(sql, con=get_db_connection()).to_dict(orient='records')

                pools = pd.read_sql(sql=f'select id from HockeyPool where season_id=={season.id}', con=get_db_connection()).id.values.tolist()
                for pool in pools:
                    kwargs = {'Criteria': [['pool_id', '==', pool]]}
                    pool_teams = PoolTeam().fetch_many(**kwargs)
                    for pool_team in pool_teams:
                        kwargs = {'Criteria': [['poolteam_id', '==', pool_team.id]]}
                        roster = PoolTeamRoster().fetch_many(**kwargs)
                        for player in roster:
                            # check if player has a stats row for current season
                            df = dfPlayerStats.query('seasonID==@season.id and season_type==@season.type and player_id==@player.player_id').copy()
                            if len(df.index) == 0:
                                (name, game_logs_team_id, team_abbr, pos) = self.fill_missing_player_data(player_id=player.player_id)
                                df.loc[player.player_id, ['seasonID', 'season_type', 'name', 'pos', 'team_id', 'team_abbr']] = [season.id, season.type, name, pos, game_logs_team_id, team_abbr]
                                dfPlayerStats = pd.concat([dfPlayerStats, df])
                                # add to missing_team_roster_players, if not in team_rosters
                                if player.player_id not in [x['player_id'] for x in team_rosters if x['team_abbr'] == team_abbr]:
                                    missing_team_roster_players.append({
                                        'team_abbr': team_abbr if team_abbr else '(N/A)',
                                        'player_id': player.player_id,
                                        'name': name,
                                        'pos': pos,
                                        'line': '',
                                        'pp_line': ''
                                    })
                            else:
                                # a stats row may exist, but if created from game aggregates, the row will be missing player name, etc.
                                # need to reset index, moving index columns to dataframe columns, because the index uses "name" for its indices
                                df.reset_index(inplace=True)
                                name = df['name'][0]
                                if name == "" or pd.isna(name):
                                    (name, game_logs_team_id, team_abbr, pos) = self.fill_missing_player_data(player_id=player.player_id)
                                    dfPlayerStats.loc[(season.id, season.type, player.player_id), ['name', 'pos', 'team_id', 'team_abbr']] = [name, pos, game_logs_team_id, team_abbr]
                                    # add to missing_team_roster_players, if not in team_rosters
                                    if player.player_id not in [x['player_id'] for x in team_rosters if x['team_abbr'] == team_abbr]:
                                        missing_team_roster_players.append({
                                            'team_abbr': team_abbr if team_abbr else '(N/A)',
                                            'player_id': player.player_id,
                                            'name': name,
                                            'pos': pos,
                                            'line': '',
                                            'pp_line': ''
                                        })

            # Delete PlayerStats, PlayerGameStats, and TeamRosters for season
            try:

                with get_db_connection() as connection:

                    cursor = connection.cursor()

                    # some players have not played a game, and are not on a pool team roster, but have a row in dfPlayerStats with no data
                    # might as well delete these for now
                    rows_to_drop = dfPlayerStats.index[pd.isna(dfPlayerStats['name'])]
                    dfPlayerStats.drop(index=rows_to_drop, inplace=True)
                    sql1 = f"delete from PlayerStats where seasonID={season.id} and season_type='{season.type}'"
                    cursor.execute(sql1)

                    dfPlayerStats.reset_index(inplace=True)
                    dfPlayerStats.to_sql('PlayerStats', con=connection, if_exists='append', index=False, dtype=dtypes)

                    sql2 = f"delete from PlayerGameStats where seasonID={season.id} and game_type='{season.type}'"
                    cursor.execute(sql2)
                    dfPlayerGameStats.to_sql('PlayerGameStats', con=connection, if_exists='append', index=False, dtype=dtypes)

                    # only required for regular season, not pre-season or playoffs
                    if season.id == season.getCurrent()[0].id and season.type == 'R' and len(missing_team_roster_players) > 0 :

                        # put new team rosters, for season, to dataframe
                        dfMissingTeamRosterPlayers = pd.DataFrame(missing_team_roster_players)
                        # shouldn't be any duplicates, but leaving this in case I'm wrong
                        dfMissingTeamRosterPlayers.drop_duplicates(inplace=True)

                        dfMissingTeamRosterPlayers.to_sql('TeamRosters', con=connection, if_exists='append', dtype=dtypes, index=False)

                    # # write PoolTeamRosterPlayerStats
                    # # NOTE: This is execution-time dependent, but should be OK because the stats need to be "current" each Sunday mornning
                    # # to determine the PickupHockey weekly pool winner
                    # # NOTE: This is only for the current season
                    # # if season.type == 'R' and season.id == season.getCurrent()[0].id:
                    #     dfPlayerStats.drop(columns=['season_type'], inplace=True)
                    #     # get PickupHockey pool in current season
                    #     pools = pd.read_sql(sql=f'select id from HockeyPool where season_id=={season.id} and web_host="PickupHockey"', con=connection).id.values.tolist()
                    #     for pool in pools:
                    #         kwargs = {'Criteria': [['pool_id', '==', pool]]}
                    #         pool_teams = PoolTeam().fetch_many(**kwargs)
                    #         for pool_team in pool_teams:
                    #             kwargs = {'Criteria': [['poolteam_id', '==', pool_team.id]]}
                    #             roster = PoolTeamRoster().fetch_many(**kwargs)
                    #             for player in roster:
                    #                 # player should have a stats row for current season
                    #                 df = dfPlayerStats.query('player_id==@player.player_id').copy()
                    #                 if (player.date_added is None and player.date_removed is None) \
                    #                     or (player.date_added is None and (date.strftime(date.today(), '%Y-%m_%d') < player.date_removed)) \
                    #                     or ((player.date_added <= date.strftime(date.today(), '%Y-%m_%d')) and player.date_removed is None) \
                    #                     or (player.date_added <= date.strftime(date.today(), '%Y-%m_%d') < player.date_removed):
                    #                     df.reset_index(inplace=True)
                    #                     df['poolteam_id'] = player.poolteam_id
                    #                     df.set_index(['seasonID', 'poolteam_id', 'player_id'], inplace=True)
                    #                     df.sort_index(inplace=True)
                    #                     # delete existing row
                    #                     sql = f'delete from PoolTeamRosterPlayerStats where seasonID={season.id} and poolteam_id={player.poolteam_id} and player_id={player.player_id}'
                    #                     cursor.execute(sql)
                    #                     df.to_sql('PoolTeamRosterPlayerStats', con=connection, if_exists='append', dtype=dtypes)

                    cursor.close()

            except Exception as e:
                if batch:
                    logger.error(repr(e))
                else:
                    sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')

        except Exception as e:
            if batch:
                logger.error(repr(e))
                raise
            else:
                sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')

        finally:
            msg = 'clsNHL_API.get_player_stats() completed.'
            if batch:
                logger.debug(msg)
            else:
                dialog.close()
                sg.popup_notify(msg, title=sys._getframe().f_code.co_name)

        return

    def get_team_logos(self, team_id: str):

        global logos

        if team_id not in logos:
            logos[team_id] = f'../../python/input/nhl-images/logos/{team_id}.png'

        return logos[team_id]

    def get_teams(self, season: Season):

        # game_type one of 'R' = Regular season, 'P' = Playoffs, 'PR' = Pre-season

        try:
            # https://statsapi.web.nhl.com/api/v1/teams?season=20212022
            teams = [{'id': d['id'], 'name': d['fullName'], 'abbr': d['triCode']} for d in j.search('data', requests.get(f'{NHL_STATS_API_URL}/team').json())]
        except TypeError:
            # season information not yet set up in NHL API
            df = pd.DataFrame()

        df = pd.DataFrame(teams)

        return df

    def get_team_stats(self, season: str, game_type: str='R', batch=False):

        if batch:
            logger = logging.getLogger(__name__)

        request_error = False

        try:

            # # https://statsapi.web.nhl.com/api/v1/teams?season=20212022
            # api_result = requests.get(f'{NHL_API_URL}/teams/?season={season.id}').json()

            # if 'message' in api_result:
            #     error_msg = api_result['message']
            #     msg = f'API request failed: Error message "{error_msg}"...'
            #     request_error = True
            #     return

            url_base = 'https://api.nhle.com/stats/rest/en/team/summary'

            game_type_id = '3' if season.type == 'P' else '2'

            # set request parameters
            params = {
                "isAggregate": 'false',
                "isGame": 'true',
                "sort": '[{"property" : "teamId", "direction": "ASC"}]',
                "start": 0,
                # Setting limit = 0 returns all games for game date
                "limit": 0,
                "factCayenneExp": 'gamesPlayed>=1',
                "cayenneExp": f'seasonId={season.id} and gameTypeId={game_type_id}'
            }

            # Send a GET request to the API endpoint with the parameters
            response = requests.get(url=f'{url_base}', params=params)

            # Check if the request was successful (HTTP status code 200)
            if response.status_code == 200:
                # Extract the data from the JSON response
                data = response.json()['data']

                # teams = [{'id': d['teamId'], 'name': d['teamFullName'], 'abbr': d['abbreviation'], 'game': d['gamesPlayed']} for d in data]
                team_counts = Counter(d['teamId'] for d in data)
                # Now create a new list with the aggregated data
                teams = []
                for team_id, games_played in team_counts.items():
                    # Find the team name by searching the original data
                    # (Assumes that all entries for a team have the same name)
                    team_name = next((d['teamFullName'] for d in data if d['teamId'] == team_id), None)

                    teams.append({
                        'id': team_id,
                        'name': team_name,
                        'games': games_played
                    })

                with get_db_connection() as connection:
                    for team in teams:
                        team_id = team['id']
                        team_games = team['games']
                        # # https://statsapi.web.nhl.com/api/v1/schedule?season=20212022&gameType=PR&teamId=1
                        # team['games'] = j.search('totalGames', requests.get(f'{NHL_API_URL}/schedule?season={season.id}&gameType={game_type}&startDate={season.start_date}&endDate={datetime.strftime(YESTERDAY, "%Y-%m-%d")}&teamId={team_id}').json())

                        sql = f'''insert or replace into TeamStats
                                (seasonID, game_type, team_id, games)
                                values ({season.id}, "{game_type}", {team_id}, {team_games})'''
                        cursor = connection.cursor()
                        cursor.execute(sql)

            else:
                # Handle any errors
                request_error = True
                msg = f'Error: {response.status_code}'
                if batch:
                    logger.error(msg)

        except Exception as e:
            logger.error(repr(e))

        finally:
            if request_error is False:
                df = pd.DataFrame(teams)
            else: # request_error is True
                if batch is False:
                    sg.popup_notify(msg, title=sys._getframe().f_code.co_name)
                df = pd.DataFrame()

        return df

    # def get_season(self, season: str):

    #     # https://statsapi.web.nhl.com/api/v1/seasons/?season=20212022
    #     season_info = [{'startDate': d['regularSeasonStartDate'], 'endDate': d['regularSeasonEndDate'], 'numberOfGames': d['numberOfGames']} for d in j.search('seasons', requests.get(f'{NHL_API_URL}/seasons/?season={season}').json())]

    #     return season_info

    def save_stats_snapshot(self, season: Season, week_number: int, batch: bool=False):

        # NOTE: Need to update this code to include pool team roster players that are not "officially" on nhl team roster
        # see getPlayerStats()

        try:

            if batch:
                logger = logging.getLogger(__name__)

            if not season:
                msg = 'Season is required. Returning...'
                if batch:
                    logger.error(msg)
                else:
                    sg.popup_error(msg, title='NHL Pool')
                return

            if week_number is None or week_number == '' or not (1 <= week_number <= season.WEEKS_IN_NHL_SEASON):
                msg = f'"{week_number}"" is not valid. Must be between 1 and {season.WEEKS_IN_NHL_SEASON}'
                if batch:
                    logger.error(msg)
                else:
                    sg.popup_error(msg, title='NHL Pool')
                return

            seasonID: int = season.id

            (start_date, end_date) = get_iso_week_start_end_dates(nhl_week=week_number)
            if datetime.strptime(end_date, '%Y-%m-%d').date() > YESTERDAY:
                end_date = date.strftime(YESTERDAY, '%Y-%m-%d')

            week_started: bool = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).date() <= TODAY
            week_over: bool = datetime.strptime(end_date, '%Y-%m-%d').date() < TODAY

            from_zone = tz.tzutc()
            to_zone = tz.tzlocal()

            # Get player stats as of week
            file_path = f'./python/input/nhl-data/{seasonID}/PlayerSeasonStats.json'
            if path.isfile(file_path):
                if batch:
                    logger.debug(f'Retrieving "{file_path}"')
                with open(file_path, 'r') as from_json:
                    player_stats_as_of_week = json.load(from_json)

                file_path = f'./python/input/nhl-data/{seasonID}/Snapshots/Week{str(week_number).zfill(2)}PlayerStats.json'
                if batch:
                    logger.debug(f'Saving to "{file_path}"')
                with open(file_path, 'w') as to_json:
                    json.dump(player_stats_as_of_week, to_json)

            # Get game feeds for week
            file_path = f'./python/input/nhl-data/{seasonID}/GameFeeds.json'
            if path.isfile(file_path):
                if batch:
                    logger.debug(f'Retrieving "{file_path}"')
                with open(file_path, 'r') as from_json:
                    game_feeds_for_week = json.load(from_json)

                if batch:
                    logger.debug('Processing game feeds for week..')
                game_feeds = j.search('[*]', game_feeds_for_week)
                game_dates_utc: List[str] = j.search('[*].gameData.datetime.dateTime', game_feeds)
                game_dates_local: List[str] = []
                for date_utc in game_dates_utc:
                    utc_date: datetime = datetime.strptime(date_utc, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=from_zone)
                    game_dates_local.append(datetime.strftime(utc_date.astimezone(to_zone).date(), '%Y-%m-%d'))
                indexes = [i for i, x in enumerate(game_dates_local) if start_date <= x <= end_date]
                new_game_feeds = []
                for idx in indexes:
                    new_game_feeds.append(game_feeds[idx])
                game_feeds_for_week = new_game_feeds

                file_path = f'./python/input/nhl-data/{seasonID}/Snapshots/Week{str(week_number).zfill(2)}GameFeeds.json'
                if batch:
                    logger.debug(f'Saving to "{file_path}"')
                with open(file_path, 'w') as to_json:
                    json.dump(game_feeds_for_week, to_json)

            # Get player game logs for week
            file_path = f'./python/input/nhl-data/{seasonID}/PlayerGameLogs.json'
            if path.isfile(file_path):
                if batch:
                    logger.debug(f'Retrieving "{file_path}"')
                with open(file_path, 'r') as from_json:
                    player_game_logs_for_week: json = json.load(from_json)

                if batch:
                    logger.debug('Processing player game logs for week..')
                teams = j.search('teams[*]', player_game_logs_for_week)
                for t_idx, team in enumerate(teams):
                    roster = j.search('roster.roster', team)
                    for r_idx, player in enumerate(roster):
                        stats =j.search('person.stats[0].splits', player)
                        indexes = [i for i, x in enumerate(stats) if start_date <= x['date'] <= end_date]
                        new_stats = []
                        for idx in indexes:
                            new_stats.append(stats[idx])
                        player_game_logs_for_week['teams'][t_idx]['roster']['roster'][r_idx]['person']['stats'][0]['splits'] = new_stats

                file_path = f'./python/input/nhl-data/{seasonID}/Snapshots/Week{str(week_number).zfill(2)}PlayerGameLogs.json'
                if batch:
                    logger.debug(f'Saving to "{file_path}"')
                with open(file_path, 'w') as to_json:
                    json.dump(player_game_logs_for_week, to_json)

            # Get scoring plays for week
            file_path = f'./python/input/nhl-data/{seasonID}/ScoringPlays.json'
            if path.isfile(file_path):
                if batch:
                    logger.debug(f'Retrieving "{file_path}"')
                with open(file_path, 'r') as from_json:
                    scoring_plays_for_week = json.load(from_json)

                if batch:
                    logger.debug('Processing scoring plays for week..')
                dates: List = j.search('dates[*]', scoring_plays_for_week)
                game_dates: List = j.search('[*].date', dates)
                indexes = [i for i, x in enumerate(game_dates) if start_date <= x <= end_date]
                new_dates = []
                total_items = 0
                for idx in indexes:
                    new_dates.append(dates[idx])
                    total_items += dates[idx]['totalItems']
                scoring_plays_for_week['dates'] = new_dates
                scoring_plays_for_week['totalItems'] = total_items
                scoring_plays_for_week['totalGames'] = total_items

                file_path = f'./python/input/nhl-data/{seasonID}/Snapshots/Week{str(week_number).zfill(2)}ScoringPlays.json'
                if batch:
                    logger.debug(f'Saving to "{file_path}"')
                with open(file_path, 'w') as to_json:
                    json.dump(scoring_plays_for_week, to_json)

        except Exception as e:
            if batch:
                logger.error(repr(e))
            else:
                sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')
            raise

        return
