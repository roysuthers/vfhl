import numpy as np
import os
import sqlite3
import zipfile
from datetime import date, datetime, timedelta
from numpy import int32, int64
from time import strftime, strptime
from typing import Dict, Tuple
from unidecode import unidecode

import pandas as pd
import PySimpleGUI as sg

from constants import  DATABASE

# Allow unlimited dataframe columns
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('max_colwidth', None)
pd.set_option('display.colheader_justify','left')

sg.ChangeLookAndFeel('Black')

def assign_player_ids(df: pd.DataFrame, player_name: str, nhl_team: str, pos_code: str) -> pd.Series:

    from clsNHL_API import NHL_API
    nhl_api = NHL_API()

    # Get team IDs
    team_ids = load_nhl_team_abbr_and_id_dict()

    # Get player names & id dictionary
    player_ids = load_player_name_and_id_dict()

    # Get player IDs
    playerIds = df.apply(lambda row: get_player_id(team_ids, player_ids, nhl_api, row[player_name], row[nhl_team], row[pos_code]), axis=1)

    return playerIds

def calculate_age(birth_date: str) -> int:
    """Calculate the age in years given a birth date in YYYY-MM-DD format."""

    if birth_date != '':
        born = datetime.strptime(birth_date, "%Y-%m-%d").date()
        today = date.today()

        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    else:
        age = np.nan

    return age

def get_db_connection():

    # Storing an integer in sqlite results in BLOBs (binary values) instead of INTEGER.
    # The following lines prevent this.
    sqlite3.register_adapter(int64, int)
    sqlite3.register_adapter(int32, int)

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    # uncomment the following line to print the sql statement with parameter substitution, after execution
    # connection.set_trace_callback(print)

    return connection

def get_db_cursor():

    cursor = get_db_connection().cursor()

    return cursor

def get_iso_week_start_end_dates(nhl_week: int, season) -> tuple:

    # find iso week number in ISOWEEK_TO_NHL_WEEK for the passed in nhl_week
    iso_week = season.ISOWEEK_TO_NHL_WEEK[nhl_week - 1]

    start_date = (iso_week - 1).sunday().strftime('%Y-%m-%d')
    end_date = iso_week.saturday().strftime('%Y-%m-%d')

    return (start_date, end_date)

def get_player_id(team_ids: Dict, player_ids: Dict, nhl_api: 'NHL_API', name: str, team_abbr: str, pos: str=''):
    player_id = 0
    key_name = unidecode(name).lower()
    if key_name in player_ids:
        if len(player_ids[key_name]) == 1:
            player_id = player_ids[key_name][0]['id']

        else: # multiple players on different teams with same name (e.g., Sebastian Aho)
            idx = [i for i, x in enumerate(player_ids[key_name]) if player_ids[key_name][i]['team_abbr'] == team_abbr]
            if len(idx) == 1:
                player_id = player_ids[key_name][idx[0]]['id']
            else: # multiple players on same team with same name (e.g., Elias Pettersson)
                if pos == 'F':
                    idx = [i for i, x in enumerate(player_ids[key_name]) if player_ids[key_name][i]['team_abbr'] == team_abbr and player_ids[key_name][i]['pos'] in ('C', 'LW', 'RW')]
                else:
                    idx = [i for i, x in enumerate(player_ids[key_name]) if player_ids[key_name][i]['team_abbr'] == team_abbr and pos in player_ids[key_name][i]['pos']]
                if len(idx) == 1:
                    player_id = player_ids[key_name][idx[0]]['id']
    else:
        team_id = team_ids[team_abbr] if team_abbr in team_ids else 0
        player_json = nhl_api.get_player_by_name(name=name, team_id=team_id, pos=pos)
        if player_json is not None:
            player_id = int(player_json['playerId'])

    return player_id

# def get_player_id_from_name(name: str, team_id: int=0, pos: str='') -> Dict:

#     # Define a custom Python function for case-insensitive and accented character-insensitive comparison
#     def custom_compare(str1, str2):
#         return str1.upper() == str2.upper()

#     # Take a look at clsNHL_API's get_player_by_name() function, which essentially does the same as this function
#     try:

#         # default if player id cannot be found
#         kwargs = {'full_name': name, 'current_team_id': team_id}

#         # some Fantrax & Dobber player names are different
#         player_name = name
#         # sql = f'select nhl_name from PlayerAlternateNames where alt_name=="{name}"'
#         sql = 'select nhl_name, alt_names from PlayerAlternateNames'
#         with get_db_connection() as connection:

#             # Register the custom function with SQLite
#             connection.create_function("custom_compare", 2, custom_compare)

#             cursor = connection.cursor()
#             cursor.execute(sql)
#             # row = cursor.fetchone()
#             # if row:
#             #     player_name = row['nhl_name']
#             # kwargs = {'full_name': player_name}
#             rows = cursor.fetchall()
#             indexes = [i for i, row in enumerate(rows) if player_name.lower() in row['alt_names'].lower()]
#             if len(indexes) == 1:
#                 player_name = rows[indexes[0]]['nhl_name']
#             elif len(indexes) > 1:
#                 ...

#             kwargs = {'full_name': player_name}

#             # # in most cases, there will be only one player returned when fetching using the player's name
#             # sql = f'select count(*) as count from Player where full_name=="{player_name}"'
#             # cursor.execute(sql)
#             # row = cursor.fetchone()
#             # if row is None or row['count'] != 1:
#             #     sql = f'select count(*) as count from Player where full_name=="{player_name}" and primary_position=="{pos}"'
#             #     cursor.execute(sql)
#             #     row = cursor.fetchone()
#             #     if pos != '' and row and row['count'] == 1:
#             #         kwargs = {'full_name': player_name, 'primary_position': pos}
#             #     else: # use player name and team id to find player
#             #         sql = f'select count(*) as count from Player where full_name=="{player_name}" and current_team_id=={team_id}'
#             #         cursor.execute(sql)
#             #         row = cursor.fetchone()
#             #         if row and row['count'] == 1:
#             #             kwargs = {'full_name': player_name, 'current_team_id': team_id}

#             # in most cases, there will be only one player returned when fetching using the player's name
#             sql = 'SELECT id FROM Player WHERE custom_compare(full_name, ?)'
#             cursor.execute(sql, (player_name,))
#             rows = cursor.fetchall()
#             if len(rows) == 1:
#                 kwargs = {'id': rows[0]['id']}
#             else:
#                 # use player name and team id to find player
#                 sql = f'SELECT id FROM Player WHERE custom_compare(full_name, ?) and current_team_id=={team_id}'
#                 cursor.execute(sql, (player_name,))
#                 rows = cursor.fetchall()
#                 if len(rows) == 1:
#                     kwargs = {'id': rows[0]['id']}

#     except Exception:
#         # logging.exception('Exception')
#         raise

#     return kwargs

def inches_to_feet(inches):
    feet = inches // 12
    remaining_inches = inches % 12
    return f"{feet}' {remaining_inches}\""

def load_nhl_team_abbr_and_id_dict() -> Dict:

    sql = 'SELECT id, abbr, id FROM Team'
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        nhl_team_abbr_id_dict = {row['abbr']: row['id'] for row in rows}

    return nhl_team_abbr_id_dict

def load_player_name_and_id_dict() -> Dict:

    sql = 'SELECT full_name, id, current_team_abbr as team_abbr, primary_position as pos FROM Player where id > 0'
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        player_id_dict = {}
        for row in rows:
            name = unidecode(row['full_name']).lower()
            if name not in player_id_dict:
                player_id_dict[name] = []
            player_id_dict[name].append({'id': row['id'], 'team_abbr': row['team_abbr'], 'pos': row['Pos']})

    sql = 'select pan.nhl_name, pan.alt_names, p.id from PlayerAlternateNames pan join Player p on p.full_name=pan.nhl_name'
    with get_db_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

    for row in rows:
        nhl_name = unidecode(row['nhl_name']).lower()
        alt_names = row['alt_names'].split(',')
        for name in alt_names:
            # player_id_dict[name.strip()] = row['id']
            name = name = unidecode(name.strip()).lower()
            if nhl_name != name and name not in player_id_dict:
                player_id_dict[name] = []
                for dict_name in player_id_dict[nhl_name]:
                    player_id_dict[name].append({'id': dict_name['id'], 'team_abbr': dict_name['team_abbr'], 'pos': dict_name['pos']})

    return player_id_dict

def process_dict(d):
    for key in d.keys():
        if isinstance(d[key], pd.Series):
            d[key] = d[key].fillna(0).tolist()
        elif isinstance(d[key], np.int64):
            d[key] = int(d[key])
        elif isinstance(d[key], list):
            continue
        elif isinstance(d[key], dict):
            continue
        elif d[key] is None or np.isnan(d[key]):
            d[key] = 0
    return dict(d)

def seconds_to_string_time(seconds: int) -> str:
    """Convert seconds to a string time in MM:SS format."""

    try:
        minutes, seconds = divmod(seconds, 60)
        str_time = f"{minutes:02}:{seconds:02}"
    except ValueError:
        str_time = "00:00"

    return str_time

def setCSS_TableStyles():

    # Set CSS properties for 'table' tag elements in dataframe
    table_props = [
        ('border', '1px solid black')
    ]

    # # Set CSS properties for 'th' tag elements in dataframe
    # # position: sticky & top: 0px are for sticky column headers
    # th_props = [
    #     ('background', 'rgb(242, 242, 242)'),
    #     ('border', '1px solid black'),
    #     ('padding', '5px'),
    #     ('position', 'sticky'),
    #     ('top', '0'),
    #     ('left', '0'),
    # ]

    # Set CSS properties for 'td' tag elements in dataframe
    td_props = [
        ('border', '1px solid black'),
        ('padding', '5px')
    ]

    # Set CSS properties for 'tr:nth-child' tag elements in dataframe
    # NOTE: This doesn't alter the background in the email table
    # However, when the email html source is displayed in a browser, the background does alternate
    tr_nth_child_props = [
        ('background', 'rgb(253, 233, 217)')
    ]

    # # hyperlink styles
    # hyperlink = [
    #     ('color', 'green'),
    #     ('background-color', 'transparent'),
    #     ('text-decoration', 'none')
    # ]

    # visited_hyperlink = [
    #     ('color', 'green'),
    #     ('background-color', 'transparent'),
    #     ('text-decoration', 'none')
    # ]

    # hover_hyperlink = [
    #     ('color', 'red'),
    #     ('background-color', 'transparent'),
    #     ('text-decoration', 'underline')
    # ]

    # active_hyperlink = [
    #     ('color', 'yellow'),
    #     ('background-color', 'transparent'),
    #     ('text-decoration', 'underline')
    # ]

    # dropdown select control
    select_props = [
        ('font-family', 'inherit'),
        ('font-size', 'inherit'),
    ]

    # Set table styles
    styles = [
        dict(selector="table", props=table_props),
        # dict(selector="th", props=th_props),
        dict(selector="td", props=td_props),
        dict(selector="tr:nth-child(even)", props=tr_nth_child_props),
        # dict(selector="a:link", props=hyperlink),
        # dict(selector="a:visited", props=visited_hyperlink),
        # dict(selector="a:hover", props=hover_hyperlink),
        # dict(selector="a:active", props=active_hyperlink),
        dict(selector="select", props=select_props),
    ]

    return styles

def setCSS_TableStyles2():

    # Set CSS properties for 'table' tag elements in dataframe
    table_props = [
        ('border', '1px solid black')
    ]

    # Set CSS properties for 'th' tag elements in dataframe
    # position: sticky & top: 0px are for sticky column headers
    th_props = [
        ('background', 'rgb(242, 242, 242)'),
        ('border', '1px solid black'),
        ('padding', '5px'),
        ('top', '0'),
        ('left', '0'),
    ]

    # Set CSS properties for 'td' tag elements in dataframe
    td_props = [
        ('border', '1px solid black'),
        ('padding', '5px')
    ]

    # Set CSS properties for 'tr:nth-child' tag elements in dataframe
    # NOTE: This doesn't alter the background in the email table
    # However, when the email html source is displayed in a browser, the background does alternate
    tr_nth_child_props = [
        ('background', 'rgb(253, 233, 217)')
    ]

    # Set table styles
    styles = [
        dict(selector="table", props=table_props),
        dict(selector="th", props=th_props),
        dict(selector="td", props=td_props),
        dict(selector="tr:nth-child(even)", props=tr_nth_child_props),
    ]

    return styles

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

def unzip_file(zip_filepath: str, dest_dir: str=''):

    if dest_dir == '':
        dest_dir = zip_filepath.rsplit('\\', 1)[0]
    else:
        os.makedirs(dest_dir, exist_ok=True)

    if not os.path.exists(zip_filepath):
        raise FileNotFoundError(f"File {zip_filepath} does not exist.")
    if not os.access(zip_filepath, os.R_OK):
        raise PermissionError(f"Do not have the necessary permissions to read the zip file.")
    if not os.access(dest_dir, os.W_OK):
        raise PermissionError(f"Do not have the necessary permissions to write to the destination directory.")

    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
    except zipfile.BadZipFile:
        raise ValueError(f"The file {zip_filepath} is not a zip file.")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}")
