# Import Python modules
import os
import subprocess
import textwrap
import time
import webbrowser
from copy import copy
from datetime import timedelta
from os import path
from pathlib import Path
from typing import List
from urllib.request import pathname2url

import jmespath as j
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
import PySimpleGUI as sg
import requests
from math import ceil, floor
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression

from clsPlayer import Player
from clsSeason import Season
from constants import NHL_API_URL, calendar, program_data_path
from utils import (calculate_age, get_db_connection,
                   get_iso_week_start_end_dates, seconds_to_string_time, setCSS_TableStyles,
                   setCSS_TableStyles2, split_seasonID_into_component_years,
                   string_to_time)
from utils import generated_html_path

# period for rolling averages
rolling_avg_period = 3

def calc_player_ages(df: pd.DataFrame) -> pd.Series:

    # calculate player's current age
    # if there are no stats, the following has problem. So do't do it if there are now rows in df_player_stats
    if len(df.index) == 0:
        ages: pd.Series = np.nan
    else:
        ages: pd.Series = df.apply(lambda x: np.nan if (pd.isna(x['birth_date']) or x['birth_date']=='') else calculate_age(x['birth_date']), axis='columns')

    return ages

def calc_player_breakout_threshold(df: pd.DataFrame) -> pd.Series:

    if len(df.index) == 0:
        breakout_thresholds: pd.Series = np.nan
    else:
        breakout_thresholds: pd.Series = df.apply(lambda x: np.nan
                                                 if (
                                                        pd.isna(x['height'])
                                                        or x['height']==''
                                                        or pd.isna(x['weight'])
                                                        or x['weight']==''
                                                        or pd.isna(x['career_games'])
                                                        or x['career_games']==''
                                                        or x['pos'] == 'G'
                                                    )
                                                 else calculate_breakout_threshold(name=x['name'], height=x['height'], weight=x['weight'], career_games=x['career_games']),
                                                 axis='columns')

    return breakout_thresholds

def calculate_breakout_threshold(name: str, height: str, weight: int, career_games: int) -> int:

    feet_and_inches = height.replace("'", '').replace('"', '').split(' ')
    height_in_feet = int(feet_and_inches[0]) + round(int(feet_and_inches[1])/12, 2)
    # 5' 10" = 5.83 & 6' 2" = 6.17
    if ((height_in_feet >= 5.83 and height_in_feet <= 6.17) or (weight >= 171 and weight <= 214)) and (career_games >= 120 and career_games <= 280):
        breakout_threshold = career_games - 200
    # 5' 9" = 5.75 & 6' 3" = 6.25
    elif (height_in_feet <= 5.75 or weight <= 170 or height_in_feet >= 6.25 or weight >= 215) and (career_games >= 320 and career_games <= 480):
        breakout_threshold = career_games - 400
    else:
        breakout_threshold = np.nan

    return breakout_threshold

def create_gp_per_positiion_table(pool: 'HockeyPool', season: Season):

    season = Season().getSeason(id=pool.season_id)
    season.set_season_constants()
    total_game_dates = season.count_of_total_game_dates
    game_dates_completed = season.count_of_completed_game_dates

    # calc average of games-remaining-per-team
    avg_team_games_played = pd.read_sql(f'select avg(games) from TeamStats where seasonID={season.id} and game_type="{season.type}"', con=get_db_connection()).values[0][0]
    avg_team_games_remaining = round(season.number_of_games - avg_team_games_played, 1)

    # get pool teams data
    sql = textwrap.dedent(f'''\
        select *
        from PoolTeam
        where pool_id={pool.id}
        order by points desc, name asc'''
    )
    df = pd.read_sql(sql=sql, con=get_db_connection())

    manager = []
    points = []

    for data_group in ('manager', 'forward', 'defense', 'skater', 'goalie'):

        games_played = []
        pace_games_per_day = []
        pace_games = []
        pace_over_under = []
        remaining = []
        maximum = []
        minimum = []

        for pool_team in df.itertuples():

            if data_group == 'manager':
                manager.append(pool_team.name)
                points.append('{:0.1f}'.format(pool_team.points))

            elif data_group == 'forward':
                games_played.append(pool_team.F_games_played)
                games_per_day_pace = pool_team.F_games_played / game_dates_completed
                pace_games_per_day.append('{:0.2f}'.format(games_per_day_pace))
                # until the last few days in the season, games pace can be "int(games_per_day_pace * total_game_dates)"
                # otherwise comment out this line, and use currently commented calculation
                projected_games_total = int(games_per_day_pace * total_game_dates)
                pace_games.append(projected_games_total)
                over_under_pace = projected_games_total - pool_team.F_maximum_games
                pace_over_under.append(over_under_pace)
                remaining.append(pool_team.F_maximum_games - pool_team.F_games_played if pool_team.F_games_played < pool_team.F_maximum_games else 0)
                maximum.append(pool_team.F_maximum_games)
                F_max_games = pool_team.F_maximum_games
                games_per_day_target = '{:0.2f}'.format(F_max_games / total_game_dates)
                F_L0_header = f'Forward (Max={F_max_games}, Avg={games_per_day_target})'

            elif data_group == 'defense':
                games_played.append(pool_team.D_games_played)
                games_per_day_pace = pool_team.D_games_played / game_dates_completed
                pace_games_per_day.append('{:0.2f}'.format(games_per_day_pace))
                # until the last few days in the season, games pace can be "int(games_per_day_pace * total_game_dates)"
                # otherwise comment out this line, and use currently commented calculations
                projected_games_total = int(games_per_day_pace * total_game_dates)
                pace_games.append(projected_games_total)
                over_under_pace = projected_games_total - pool_team.D_maximum_games
                pace_over_under.append(over_under_pace)
                remaining.append(pool_team.D_maximum_games - pool_team.D_games_played if pool_team.D_games_played < pool_team.D_maximum_games else 0)
                maximum.append(pool_team.D_maximum_games)
                D_max_games = pool_team.D_maximum_games
                games_per_day_target = '{:0.2f}'.format(D_max_games / total_game_dates)
                D_L0_header = f'Defense (Max={D_max_games}, Avg={games_per_day_target})'

            elif data_group == 'skater':
                games_played.append(pool_team.Skt_games_played)
                games_per_day_pace = pool_team.Skt_games_played / game_dates_completed
                pace_games_per_day.append('{:0.2f}'.format(games_per_day_pace))
                # until the last few days in the season, games pace can be "int(games_per_day_pace * total_game_dates)"
                # otherwise comment out this line, and use currently commented calculations
                projected_games_total = int(games_per_day_pace * total_game_dates)
                pace_games.append(projected_games_total)
                over_under_pace = projected_games_total - pool_team.Skt_maximum_games
                pace_over_under.append(over_under_pace)
                remaining.append(pool_team.Skt_maximum_games - pool_team.Skt_games_played if pool_team.Skt_games_played < pool_team.Skt_maximum_games else 0)
                maximum.append(pool_team.Skt_maximum_games)
                Skt_max_games = pool_team.Skt_maximum_games
                games_per_day_target = '{:0.2f}'.format(Skt_max_games / total_game_dates)
                Skt_L0_header = f'Skater (Max={Skt_max_games}, Avg={games_per_day_target})'

            elif data_group == 'goalie':
                games_played.append(pool_team.G_games_played)
                games_per_day_pace = pool_team.G_games_played / game_dates_completed
                pace_games_per_day.append('{:0.2f}'.format(games_per_day_pace))
                # until the last few days in the season, games pace can be "int(games_per_day_pace * total_game_dates)"
                # otherwise comment out this line, and use currently commented calculations
                projected_games_total = int(games_per_day_pace * total_game_dates)
                pace_games.append(projected_games_total)
                over_under_pace = projected_games_total - pool_team.G_maximum_games
                pace_over_under.append(over_under_pace)
                remaining.append(pool_team.G_maximum_games - pool_team.G_games_played if pool_team.G_games_played < pool_team.G_maximum_games else 0)
                minimum.append(pool_team.G_minimum_starts)
                G_min_games = pool_team.G_minimum_starts
                maximum.append(pool_team.G_maximum_games)
                G_max_games = pool_team.G_maximum_games
                games_per_day_target = '{:0.2f}'.format(G_max_games / total_game_dates)
                G_L0_header = f'Goalie (Min={G_min_games}\Max={G_max_games}, Avg={games_per_day_target})'


        if data_group == 'manager':
            data = {'Manager': manager, 'Points': points}
            df_managers = pd.DataFrame(data)
            df_managers.columns = pd.MultiIndex.from_tuples([('', '', 'Manager'), ('', '', 'Points')])

        elif data_group == 'goalie':
            data = {'GP': games_played, 'PacePerDay': pace_games_per_day, 'PaceGames': pace_games, '+\-': pace_over_under, 'Remaining': remaining}
            df_goalie_games_played = pd.DataFrame(data)
            df_goalie_games_played.columns = pd.MultiIndex.from_tuples([(G_L0_header,'Games Played', 'Total'), (G_L0_header,'Games Played', 'Per Day'), (G_L0_header, 'Projected Games', 'Total'), (G_L0_header, 'Projected Games', '+\-'), (G_L0_header, '', 'Remaining')])

        else:
            data = {'GP': games_played, 'PacePerDay': pace_games_per_day, 'PaceGames': pace_games, '+\-': pace_over_under, 'Remaining': remaining}
            if data_group == 'forward':
                df_forward_games_played = pd.DataFrame(data)
                df_forward_games_played.columns = pd.MultiIndex.from_tuples([(F_L0_header,'Games Played', 'Total'), (F_L0_header,'Games Played', 'Per Day'), (F_L0_header, 'Projected Games', 'Total'), (F_L0_header, 'Projected Games', '+\-'), (F_L0_header, '', 'Remaining')])
            elif data_group == 'defense':
                df_defense_games_played = pd.DataFrame(data)
                df_defense_games_played.columns = pd.MultiIndex.from_tuples([(D_L0_header,'Games Played', 'Total'), (D_L0_header,'Games Played', 'Per Day'), (D_L0_header, 'Projected Games', 'Total'), (D_L0_header, 'Projected Games', '+\-'), (D_L0_header, '', 'Remaining')])
            elif data_group == 'skater':
                df_skater_games_played = pd.DataFrame(data)
                df_skater_games_played.columns = pd.MultiIndex.from_tuples([(Skt_L0_header,'Games Played', 'Total'), (Skt_L0_header,'Games Played', 'Per Day'), (Skt_L0_header, 'Projected Games', 'Total'), (Skt_L0_header, 'Projected Games', '+\-'), (Skt_L0_header, '', 'Remaining')])

    # merge dataframes
    df_games_played_per_position = df_managers.merge(df_forward_games_played, left_index=True, right_index=True)
    df_games_played_per_position = df_games_played_per_position.merge(df_defense_games_played, left_index=True, right_index=True)
    df_games_played_per_position = df_games_played_per_position.merge(df_skater_games_played, left_index=True, right_index=True)
    df_games_played_per_position = df_games_played_per_position.merge(df_goalie_games_played, left_index=True, right_index=True)

    styler = df_games_played_per_position.style

    styler.set_table_attributes('style="display: inline-block; border-collapse:collapse"')
    styler.set_table_styles(setCSS_TableStyles2())

    styler.set_properties(subset=[['', '', 'Points']], **{'text-align': 'center'})
    styler.set_properties(subset=[[F_L0_header, 'Games Played', 'Total'], [F_L0_header, 'Games Played', 'Per Day'], [F_L0_header, 'Projected Games', 'Total'], [F_L0_header, 'Projected Games', '+\-'], [F_L0_header, '', 'Remaining']], **{'text-align': 'center'})
    styler.set_properties(subset=[[D_L0_header, 'Games Played', 'Total'], [D_L0_header, 'Games Played', 'Per Day'], [D_L0_header, 'Projected Games', 'Total'], [D_L0_header, 'Projected Games', '+\-'], [D_L0_header, '', 'Remaining']], **{'text-align': 'center'})
    styler.set_properties(subset=[[Skt_L0_header, 'Games Played', 'Total'], [Skt_L0_header, 'Games Played', 'Per Day'], [Skt_L0_header, 'Projected Games', 'Total'], [Skt_L0_header, 'Projected Games', '+\-'], [Skt_L0_header, '', 'Remaining']], **{'text-align': 'center'})
    styler.set_properties(subset=[[G_L0_header, 'Games Played', 'Total'], [G_L0_header, 'Games Played', 'Per Day'], [G_L0_header, 'Projected Games', 'Total'], [G_L0_header, 'Projected Games', '+\-'], [G_L0_header, '', 'Remaining']], **{'text-align': 'center'})

    games_played_per_position_table = styler.hide(axis='index').to_html()

    return games_played_per_position_table

def dialog_layout(pool: 'HockeyPool', season: 'Season'):

    global df_active_players
    df_active_players = get_active_players()

    active_players = df_active_players.to_dict('split')
    active_players_data = active_players.get('data')
    active_players_columms = [x.replace('_', ' ') for x in active_players.get('columns')]
    visible_column_map = [False if x=='id' else True for x in active_players_columms]

    primary_list_types = ['All', 'Compare', 'Match']

    # timeframes = ['Current season', 'Pre-season', 'Previous season', 'Previous playoffs', 'Previous 3 seasons']
    timeframes = ['Current season', 'Previous season', 'Previous 3 seasons', 'Previous playoffs']

    if season.type == 'R': # regular season
        stat_types = ['Cumulative', 'Per game', 'Per 60 minutes', 'Proj - The Athletic', 'Proj - DFO', 'Proj - Dobber', 'Proj - DtZ', 'Proj - Fantrax', 'Proj - Averaged', 'Proj - 82 Games', 'Proj - Final Stats']
    else: # season.type in ('P', 'PR'): # playoffs, pre-season
        stat_types = ['Cumulative', 'Per game', 'Per 60 minutes', ]

    # Need to filter out timeframes that make no sense for the context season
    # Season has not started (i.e. upcoming season, preseason, or playoffs)
    default_timeframe = 'Current season'
    default_stat_type = 'Cumulative'
    if season.SEASON_HAS_STARTED is False:
        timeframes.remove('Current season')
        if season.type == 'R': # regular season
            # preseason = Season().getSeason(id=season.id, type='PR')
            # preseason.set_season_constants()
            default_timeframe = 'Previous 3 seasons'
            stat_types.remove('Proj - Final Stats')
            default_stat_type = 'Proj - Averaged'
        else: # i.e., pre-season or playoffs
            timeframes= []
            default_timeframe = ''
            stat_types = []
            default_stat_type = ''

    # Season has started but not ended (i.e. current season)
    if season.type in ('P', 'PR') and season.SEASON_HAS_STARTED is True and season.SEASON_HAS_ENDED is False:
        timeframes.remove('Previous season')
        timeframes.remove('Previous 3 seasons')

    # Season has completed
    if season.SEASON_HAS_STARTED is True and season.SEASON_HAS_ENDED is True:
        timeframes.remove('Previous season')
        timeframes.remove('Previous 3 seasons')

    radar_charts_by_category_disabled = False
    trend_charts_by_category_disabled = False

    heatmaps_default = True
    heatmaps_disabled = False

    scoring_categories = ['Points', 'Goals', 'Assists', 'PP Points', 'SoG', 'Takeaways', 'Hits', 'Blocks', 'PiM']
    scoring_category_types = ['Cumulative', 'Per Game']

    layout = [
        [
            sg.Column(layout = [
                    [
                        sg.Frame('Statistics:', layout = [
                            [
                                sg.Text('List Type:', size=(9, 1)),
                                sg.Combo(values=primary_list_types, default_value='All', enable_events=True, size=(10, 1), key='_PRIMARY_LIST_TYPE_'),
                                # sg.Text('Secondary Type:', size=(15, 1)),
                                # sg.Combo(values=secondary_list_types, default_value='None', enable_events=True, size=(12, 1), key='_SECONDARY_LIST_TYPE_'),
                            ],
                            [
                                sg.Column(layout = [
                                    [
                                        sg.Text('Timeframe:', size=(9, 1)),
                                        sg.Combo(values=timeframes, default_value=default_timeframe, enable_events=True, size=(20, 1), key='_TIMEFRAME_'),
                                        # sg.pin(sg.Checkbox('Dates', default=False, size=(5, 1), key='_DATES_TIMEFRAME_', enable_events=True)),
                                        sg.pin(sg.Checkbox('Date Range', default=False, size=(9, 1), key='_DATES_TIMEFRAME_', enable_events=True)),
                                        sg.pin(elem=
                                            sg.Column(layout = [
                                                [
                                                    # sg.Text('- from', size=(5, 1)),
                                                    sg.Input('', size=(10, 1), justification='center', key='_START_DATE_'),
                                                    sg.CalendarButton(
                                                        begin_at_sunday_plus=1,
                                                        button_text='',
                                                        close_when_date_chosen=True,
                                                        format='%Y-%m-%d',
                                                        image_filename=calendar,
                                                        image_subsample=5,
                                                        key='_START_DATE_CALENDAR_',
                                                        no_titlebar=False,
                                                        target='_START_DATE_',
                                                    ),
                                                    # sg.Text('to', size=(2, 1)),
                                                    sg.Text('-', size=(1, 1)),
                                                    sg.Input('', size=(10, 1), justification='center', key='_END_DATE_'),
                                                    sg.CalendarButton(
                                                        begin_at_sunday_plus=1,
                                                        button_text='',
                                                        close_when_date_chosen=True,
                                                        format='%Y-%m-%d',
                                                        image_filename=calendar,
                                                        image_subsample=5,
                                                        key='_END_DATE_CALENDAR_',
                                                        no_titlebar=False,
                                                        target='_END_DATE_',
                                                    ),
                                                ],
                                            ], visible=False, key='_DATES_PANE_', pad=(0)),
                                        ),
                                        sg.pin(sg.Checkbox('Games', default=False, size=(6, 1), key='_GAMES_TIMEFRAME_', enable_events=True)),
                                        sg.pin(elem=
                                            sg.Column(layout = [
                                                [
                                                    sg.DropDown([i for i in range(1, 83)], default_value='10', size=(3, 1), enable_events=True, key='_X_GAMES_'),
                                                ],
                                            ], visible=False, key='_X_GAMES_PANE_', pad=(1)),
                                        ),
                                        # sg.pin(sg.Checkbox('Weeks', default=False, size=(5, 1), key='_WEEKS_TIMEFRAME_', enable_events=True)),
                                        # sg.pin(elem=
                                        #     sg.Column(layout = [
                                        #         [
                                        #             sg.DropDown([i for i in range(1, season.CURRENT_WEEK + 1)], default_value='5', size=(3, 1), enable_events=True, key='_X_WEEKS_'),
                                        #         ],
                                        #     ], visible=False, key='_X_WEEKS_PANE_', pad=(0)),
                                        # ),
                                    ],
                                ], pad=(0)),
                            ],
                            [
                                sg.pin(elem=
                                    sg.Column(layout = [
                                        [
                                            sg.Text('', size=(9, 1)),
                                            sg.Checkbox(text='Generate Statistics', default=False, size=(15, 1), key='_GEN_STATS_', enable_events=True),
                                            sg.Checkbox(text='Refresh Rosters', default=False, size=(13, 1), key='_REFRESH_POOL_TEAMS_', enable_events=True),
                                            sg.Checkbox(text='Refresh Watch List', default=False, size=(15, 1), key='_REFRESH_WATCH_LIST_', enable_events=True),
                                        ],
                                    ], visible=True, pad=(0)),
                                ),
                            ],
                            [
                                sg.Text('Stat Type:', size=(9, 1)),
                                sg.Combo(values=stat_types, default_value=default_stat_type, size=(20, 1), key='_STAT_TYPE_'),
                            ],
                            [
                                sg.Text('Display:', size=(9, 1)),
                                sg.Checkbox(text='Statistics Table', default=False, size=(12, 1), key='_SHOW_STATS_TABLE_', enable_events=True),
                                sg.Checkbox(text='Statistic Summary Tables', default=False, size=(20, 1), key='_SHOW_STAT_SUMMARY_TABLES_', enable_events=True),
                                sg.Checkbox(text='Manager Game Pace Table', default=True, size=(25, 1), key='_SHOW_MANAGER_GAME_PACE_TABLE_', enable_events=True),
                            ],
                        ]),
                    ],
                ], vertical_alignment='top', expand_x=True, pad=(0)),
        ],
        [
            sg.Column(layout=
                [
                    [
                        sg.Frame('Filters:', layout=[
                            [
                                sg.pin(
                                    sg.Column(layout=[
                                        [
                                            sg.Text('Include Pool Teams:', size=(16, 1)),
                                            sg.Listbox(values=pool_teams, enable_events=True, select_mode='extended', size=(17, 5), key='_POOL_TEAMS_'),
                                        ],
                                    ], expand_y=True, visible=False, key='_POOL_TEAMS_PANE_', pad=(0))
                                , expand_y=True)
                            ],
                            [
                                sg.pin(
                                    sg.Column(layout=[
                                        [
                                            sg.Text('Match stats by:', size=(16, 1)),
                                            sg.Radio('Player', group_id='base_for_find_players', default=True, size=(6, 1), key='_BASED_ON_PLAYER_', enable_events=True),
                                            sg.Radio('Mean', group_id='base_for_find_players', default=False, size=(6, 1), key='_BASED_ON_MEAN_', enable_events=True),
                                            sg.Text('Type:', size=(6, 1)),
                                            sg.Combo(values=scoring_category_types, default_value='Per Game', size=(9, 1), key='_MATCH_BY_CATEGORY_TYPE_'),
                                        ],
                                        [
                                            sg.Text('', size=(16, 1)),
                                            sg.Text('St Dev multipliers:', size=(15, 1)),
                                            sg.Text('Lower bound', size=(10, 1)),
                                            sg.Input(default_text='', size=(3, 1), key='_MATCH_FACTOR_FROM_', justification='center'),
                                            sg.Text('Upper bound', size=(10, 1)),
                                            sg.Input(default_text='', size=(3, 1), key='_MATCH_FACTOR_TO_', justification='center'),
                                        ],
                                        [
                                            sg.Text('', size=(16, 1)),
                                            sg.Listbox(values=scoring_categories, size=(10, 3), select_mode='extended', key='_MATCH_BY_CATEGORIES_'),
                                        ],
                                    ], expand_y=True, visible=False, key='_MATCH_PLAYERS_PANE_', pad=(0))
                                , expand_y=True)
                            ],
                            [
                                sg.pin(
                                    sg.Column(layout=[
                                        [
                                            sg.Text('Select Players:', size=(16, 1)),
                                            sg.Input(size=(10, 1), enable_events=True, key='_PLAYER_SEARCH_'),
                                        ],
                                        [
                                            sg.Text('', size=(16, 1)),
                                            sg.Table(values=active_players_data, headings=active_players_columms, visible_column_map=visible_column_map, enable_events=True, select_mode='extended', justification='left', num_rows=5, selected_row_colors=('red', 'yellow'), key='_SELECT_PLAYERS_')
                                        ],
                                        [
                                            sg.Text('', size=(16, 1)),
                                            sg.Checkbox(text='Trend Charts', default=False, size=(10, 1), disabled=trend_charts_by_category_disabled, key='_SHOW_TREND_BY_CAT_CHART_', enable_events=True),
                                        ],
                                        [
                                            sg.Text('', size=(16, 1)),
                                            sg.Checkbox(text='Radar Chart', default=False, size=(10, 1), disabled=radar_charts_by_category_disabled, key='_SHOW_RADAR_CHART_', enable_events=True),
                                            sg.Combo(values=scoring_category_types, default_value='Per Game', size=(9, 1), key='_RADAR_CHART_BY_CATEGORY_TYPE_'),
                                        ],
                                    ], expand_y=True, visible=False, key='_SELECT_PLAYERS_PANE_', pad=(0))
                                , expand_y=True)
                            ],
                        ], expand_x=True, expand_y=True),
                    ],
                ], vertical_alignment='top', expand_x=True, expand_y=True, pad=(0)),
        ],
        [
            sg.OK(bind_return_key=True),
            sg.Cancel()
        ],
    ]

    return layout

def get_active_players() -> pd.DataFrame:

    with get_db_connection() as connection:
        sql = textwrap.dedent('''\
            select p.id, (p.last_name || ", " || p.first_name) as name, t.abbr
            from Player p
                 join Team t on t.id=p.current_team_id
            where p.active=1
            order by p.last_name COLLATE NOCASE ASC, p.first_name COLLATE NOCASE ASC'''
        )
        df = pd.read_sql(sql=sql, con=connection)

    return df

def get_player_stats(season: Season, pool: 'HockeyPool', historical: bool=False, pt_roster: bool=False) -> pd.DataFrame:

    if pt_roster is False:
        general_columns = [
            'ps.seasonID',
            'ps.player_id',
            'ps.name',
            'ps.team_id',
            'ps.team_abbr',
            'ps.pos',
            'ps.games',
            'ps.team_games',
            'ps.points',
            'ps.goals',
            'ps.assists',
        ]

        skater_columns = [
            'ps.toi_pg',
            'ps.toi_even_pg',
            'ps.toi_pp_pg',
            'ps.toi_sh_pg',
            'ps.goals_pp',
            'ps.assists_pp',
            'ps.goals_sh',
            'ps.assists_sh',
            'ps.goals_gw',
            'ps.assists_gw',
            'ps.goals_ot',
            'ps.assists_ot',
            'ps.goals_ps',
            'ps.hattricks',
            'ps.pim',
            'ps.shots',
            'ps.points_pp',
            'ps.hits',
            'ps.blocked',
            'ps.takeaways',
        ]

        goalie_columns = [
            'ps.games_started',
            'ps.quality_starts',
            'ps.wins',
            'ps.wins_ot',
            'ps.wins_so',
            'ps.shutouts',
            'ps.gaa',
            'ps.goals_against',
            'ps.shots_against',
            'ps.saves',
            'ps."save%"'
        ]

        select_columns_sql = ' '.join(['select', ', '.join(general_columns+skater_columns+goalie_columns)])

        from_tables = f'from PlayerStats ps'

        if historical is True:
            (start_year, end_year) = split_seasonID_into_component_years(season_id=season.id)
            where_clause = f"where ps.seasonID between {start_year-3}{end_year-3} and {start_year-1}{end_year-1} and ps.season_type='{season.type}'"
        else:
            where_clause = f"where ps.seasonID={season.id} and ps.season_type='{season.type}'"

        order_by_clause = "order by ps.player_id, ps.seasonID"

        df_player_stats = pd.read_sql(f'{select_columns_sql} {from_tables} {where_clause} {order_by_clause}', con=get_db_connection())

    return df_player_stats

def merge_with_current_players_info(season: Season, pool: 'HockeyPool', df_stats: pd.DataFrame) -> pd.DataFrame:

    columns = [
        'tr.seasonID',
        'tr.player_id',
        'tr.name',
        'tr.pos',
        'tr.team_abbr',
        'tr.line',
        'tr.pp_line',
        'p.birth_date',
        'p.height',
        'p.weight',
        'p.active',
        'p.roster_status as nhl_roster_status',
        'p.games as career_games',
        'p.injury_status',
        'p.injury_note',
    ]

    subquery_columns = {
        'poolteam_id': f'(select pt.id from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool.id} and ptr.player_id=tr.player_id)',
        'pool_team': f'(select pt.name from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool.id} and ptr.player_id=tr.player_id)',
        'status': f'(select ptr.status from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool.id} and ptr.player_id=tr.player_id)',
        'keeper': f'(select ptr.keeper from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool.id} and ptr.player_id=tr.player_id)',
    }

    select_sql = ', '.join([
        ' '.join(['select', ', '.join(columns)]),
        ', '.join([f'{v} as {k}' for k,v in subquery_columns.items()])
    ])

    # build table joins
    from_tables = textwrap.dedent('''\
        from TeamRosters tr
             left outer join Player p on p.id=tr.player_id
    ''')

    # exclude players with p.roster_status!="N" (e.g., include p.roster_status=="Y" or p.roster_status=="I")
    where_clause = f'where tr.seasonID={season.id} and (p.roster_status!="N" or pool_team>=1)'

    # get players on nhl team rosters
    df = pd.read_sql(f'{select_sql} {from_tables} {where_clause}', con=get_db_connection())

    columns = [
        f'{season.id} as seasonID',
        'ptr.player_id',
        'p.full_name as name',
        'p.primary_position as pos',
        '\'(N/A)\' as team_abbr',
        '\'\' as line',
        '\'\' as pp_line',
        'p.birth_date',
        'p.height',
        'p.weight',
        'p.active',
        'p.roster_status as nhl_roster_status',
        'p.games as career_games',
        'p.injury_status',
        'p.injury_note',
        'ptr.poolteam_id',
        'pt.name as pool_team',
        'ptr.status',
        'ptr.keeper',
    ]

    select_sql = ', '.join([
        ' '.join(['select', ', '.join(columns)]),
    ])

    # build table joins
    from_tables = textwrap.dedent('''\
        from PoolTeamRoster ptr
        left outer join Player p on p.id=ptr.player_id
        left outer join PoolTeam pt ON pt.id=ptr.poolteam_id
    ''')

    where_clause = f'where pt.pool_id={pool.id} and p.active!=1'

    sql = textwrap.dedent(f'''\
        {select_sql}
        {from_tables}
        {where_clause}
    ''')

    # get inactive nhl players on pool team rosters
    df_temp = pd.read_sql(sql, con=get_db_connection())

    # iterate to get player's primary position
    for idx, row in df_temp.iterrows():
        primary_position = ''
        team_abbr = '(N/A)'
        try:
            # primary_position = j.search('people[0].primaryPosition.abbreviation', requests.get(f'{NHL_API_URL}/people/{row.player_id}').json())
            player = requests.get(f'{NHL_API_URL}/player/{row.player_id}/landing').json()
            primary_position = player['position']
            team_abbr = player['currentTeamAbbrev'] if 'currentTeamAbbrev' in player else '(N/A)'
        except Exception as e:
            player_id = df_temp.loc[idx, 'player_id']
            if player_id == 8470860: # Halak
                primary_position = 'G'
            elif player_id == 8470638: # Bergeron
                primary_position = 'C'
            elif player_id == 8474141: # Patrick Kane
                primary_position = 'C'
        df_temp.loc[idx, 'pos'] = primary_position
        df_temp.loc[idx, 'team_abbr'] = team_abbr

    # merge dataframes
    df = pd.concat([df, df_temp])

    # set None column values to empty
    df['poolteam_id'] = df['poolteam_id'].apply(lambda x: '' if x is None else x)
    df['pool_team'] = df['pool_team'].apply(lambda x: '' if x is None else x)
    df['status'] = df['status'].apply(lambda x: '' if x is None else x)
    df['keeper'] = df['keeper'].apply(lambda x: 'Yes' if x=='y' else '')

    # reposition columns
    df['poolteam_id'] = df.pop('poolteam_id')
    df['pool_team'] = df.pop('pool_team')
    df['status'] = df.pop('status')

    # calculate age
    df['age'] = calc_player_ages(df=df)

    # breakout threshold
    df['breakout_threshold'] = calc_player_breakout_threshold(df=df)

    # a player's nhl team roster status, if not blank, will be one of 'Y' = active roster (e.g., 23 man roster), 'N' = full roster, not active roster, 'I' = IR
    df['nhl_roster_status'] = df['nhl_roster_status'].apply(lambda x: '' if x in ('N','') else 'ir' if x=='I' else 'y')

    # change active status from 1 to Y
    df['active'] = df['active'].apply(lambda x: 'y' if x == 1 else '')

    ##################################################
    # merge dataframes
    ##################################################

    # drop columns that are duplicates
    columns_to_drop = list(df.columns)
    columns_to_drop.remove('player_id')
    df_stats.drop(columns=columns_to_drop, axis='columns', inplace=True, errors='ignore')

    df_stats = pd.merge(df, df_stats, how='left', on=['player_id'])

    df_stats.reset_index(inplace=True)

    # reposition player_id
    df_stats['player_id'] = df_stats.pop('player_id')

    return df_stats

def manager_game_pace(season: Season, pool: 'HockeyPool'):

    caption = f'<b><u>Manager Game Pace for the {season.name}, with {season.count_of_completed_game_dates} of {season.count_of_total_game_dates} game dates completed</u></b>'

    # manager game pace table
    game_pace_html = textwrap.dedent('''\
        <!doctype html>
        <html>
            <caption><b><u>{caption}</u></b></caption.
            <body>
                <!-- Games Played Per Postition -->
                <div><br />{games_played_per_position_table}<br /><br /></div>
            </body>
        </html>
    ''').format(
        caption=caption,
        games_played_per_position_table=create_gp_per_positiion_table(pool=pool, season=season),
    )

    file_name = caption.replace('<b>', '')\
                       .replace('</b>', '')\
                       .replace('<u>', '')\
                       .replace('</u>', '')\
                       .replace('<br/>', '')\
                       .strip()
    html_path = Path(os.getcwd()) / generated_html_path
    game_pace_html_file = f'{html_path}/{file_name}.html'

    try:
        with open(game_pace_html_file, 'w', encoding="utf-8-sig") as f:
            f.write(game_pace_html)

    except FileNotFoundError:
        raise Exception(f"File not found: {game_pace_html_file}")

    url = 'file:{}'.format(pathname2url(path.abspath(game_pace_html_file)))
    webbrowser.open(url)

    return

def scoring_category_radar_charts(pool: 'HockeyPool', df: pd.DataFrame, player_ids: List, stat_type: str, pos: str):

    if pool.web_host == 'Fantrax':
        # overall rank, based on Fantrax categories
        goalie_score_categories = ['z_wins', 'z_gaa', 'z_saves', 'z_save%']
        defense_score_categories = ['z_points', 'z_goals', 'z_assists', 'z_points_pp', 'z_shots', 'z_pim', 'z_hits', 'z_blocked', 'z_takeaways']
        forward_score_categories = ['z_goals', 'z_assists', 'z_points_pp', 'z_shots', 'z_pim', 'z_hits', 'z_blocked', 'z_takeaways']
        goalie_pg_score_categories = ['z_wins_pg', 'z_gaa_pg', 'z_saves_pg', 'z_save%_pg']
        defense_pg_score_categories = ['z_pts_pg', 'z_g_pg', 'z_a_pg', 'z_ppp_pg', 'z_sog_pg', 'z_pim_pg', 'z_hits_pg', 'z_blk_pg', 'z_tk_pg']
        forward_pg_score_categories = ['z_g_pg', 'z_a_pg', 'z_ppp_pg', 'z_sog_pg', 'z_pim_pg', 'z_hits_pg', 'z_blk_pg', 'z_tk_pg']

        goalie_score_category_labels = ['z-wins', 'z-gaa', 'z-saves', 'z-save%']
        defense_score_category_labels = ['z-points', 'z-goals', 'z-assists', 'z-ppp', 'z-shots', 'z-pim', 'z-hits', 'z-blk', 'z-tk']
        forward_score_category_labels = ['z-goals', 'z-assists', 'z-ppp', 'z-shots', 'z-pim', 'z-hits', 'z-blk', 'z-tk']
        goalie_pg_score_category_labels = ['z-wins pg', 'z-gaa pg', 'z-saves pg', 'z-save% pg']
        defense_pg_score_category_labels = ['z-pts pg', 'z-g pg', 'z-a pg', 'z-ppp pg', 'z-sog pg', 'z-pim pg', 'z-hits pg', 'z-blk pg', 'z-tk pg']
        forward_pg_score_category_labels = ['z-g pg', 'z-a pg', 'z-ppp pg', 'z-sog pg', 'z-pim pg', 'z-hits pg', 'z-blk pg', 'z-tk pg']

    # if stat_type == 'Cumulative':
    #     min_z = min(min_cat['f z_goals'], min_cat['f z_assists'], min_cat['f z_points_pp'], min_cat['f z_shots'], min_cat['f z_pim'], min_cat['f z_hits'], min_cat['f z_blocked'], min_cat['f z_takeaways']) \
    #             if pos == 'F' \
    #             else min(min_cat['d z_points'], min_cat['d z_goals'], min_cat['d z_assists'], min_cat['d z_points_pp'], min_cat['d z_shots'], min_cat['d z_pim'], min_cat['d z_hits'], min_cat['d z_blocked'], min_cat['d z_takeaways']) \
    #                 if pos in ('D', 'S') \
    #                 else min(min_cat['z_wins'], min_cat['z_saves'], min_cat['z_gaa'], min_cat['z_save%'])
    #     max_z = max(max_cat['f z_goals'], max_cat['f z_assists'], max_cat['f z_points_pp'], max_cat['f z_shots'], max_cat['f z_pim'], max_cat['f z_hits'], max_cat['f z_blocked'], max_cat['f z_takeaways']) \
    #             if pos == 'F' \
    #             else max(max_cat['d z_points'], max_cat['d z_goals'], max_cat['d z_assists'], max_cat['d z_points_pp'], max_cat['d z_shots'], max_cat['d z_pim'], max_cat['d z_hits'], max_cat['d z_blocked'], max_cat['d z_takeaways']) \
    #                 if pos in ('D', 'S') \
    #                 else max(max_cat['z_wins'], max_cat['z_saves'], max_cat['z_gaa'], max_cat['z_save%'])
    # else: # stat_type == 'Per Game':
    #     min_z = min(min_cat['f z_g_pg'], min_cat['f z_a_pg'], min_cat['f z_ppp_pg'], min_cat['f z_sog_pg'], min_cat['f z_pim_pg'], min_cat['f z_hits_pg'], min_cat['f z_blk_pg'], min_cat['f z_tk_pg']) \
    #             if pos == 'F' \
    #             else min(min_cat['d z_pts_pg'], min_cat['d z_g_pg'], min_cat['d z_a_pg'], min_cat['d z_ppp_pg'], min_cat['d z_sog_pg'], min_cat['d z_pim_pg'], min_cat['d z_hits_pg'], min_cat['d z_blk_pg'], min_cat['d z_tk_pg']) \
    #                 if pos in ('D', 'S') \
    #                 else min(min_cat['z_wins_pg'], min_cat['z_saves_pg'], min_cat['z_gaa_pg'], min_cat['z_save%_pg'])
    #     max_z = max(max_cat['f z_g_pg'], max_cat['f z_a_pg'], max_cat['f z_ppp_pg'], max_cat['f z_sog_pg'], max_cat['f z_pim_pg'], max_cat['f z_hits_pg'], max_cat['f z_blk_pg'], max_cat['f z_tk_pg']) \
    #             if  pos == 'F' \
    #             else max(max_cat['d z_pts_pg'], max_cat['d z_g_pg'], max_cat['d z_a_pg'], max_cat['d z_ppp_pg'], max_cat['d z_sog_pg'], max_cat['d z_pim_pg'], max_cat['d z_hits_pg'], max_cat['d z_blk_pg'], max_cat['d z_tk_pg']) \
    #                 if pos in ('D', 'S') \
    #                 else max(max_cat['z_wins_pg'], max_cat['z_saves_pg'], max_cat['z_gaa_pg'], max_cat['z_save%_pg'])

    if stat_type == 'Cumulative':
        min_z = min(df['z_goals'].min(), df['z_assists'].min(), df['z_points_pp'].min(), df['z_shots'].min(), df['z_pim'].min(), df['z_hits'].min(), df['z_blocked'].min(), df['z_takeaways'].min()) \
                if pos == 'F' \
                else min(df['z_points'].min(), df['z_goals'].min(), df['z_assists'].min(), df['z_points_pp'].min(), df['z_shots'].min(), df['z_pim'].min(), df['z_hits'].min(), df['z_blocked'].min(), df['z_takeaways'].min()) \
                    if pos in ('D', 'S') \
                    else min(df['z_wins'].min(), df['z_saves'].min(), df['z_gaa'].min(), df['z_save%'].min())
        max_z = max(df['z_goals'].max(), df['z_assists'].max(), df['z_points_pp'].max(), df['z_shots'].max(), df['z_pim'].max(), df['z_hits'].max(), df['z_blocked'].max(), df['z_takeaways'].max()) \
                if pos == 'F' \
                else max(df['z_points'].max(), df['z_goals'].max(), df['z_assists'].max(), df['z_points_pp'].max(), df['z_shots'].max(), df['z_pim'].max(), df['z_hits'].max(), df['z_blocked'].max(), df['z_takeaways'].max()) \
                    if pos in ('D', 'S') \
                    else max(df['z_wins'].max(), df['z_saves'].max(), df['z_gaa'].max(), df['z_save%'].max())
    else: # stat_type == 'Per Game':
        min_z = min(df['z_g_pg'].min(), df['z_a_pg'].min(), df['z_ppp_pg'].min(), df['z_sog_pg'].min(), df['z_pim_pg'].min(), df['z_hits_pg'].min(), df['z_blk_pg'].min(), df['z_tk_pg'].min()) \
                if pos == 'F' \
                else min(df['z_pts_pg'].min(), df['z_g_pg'].min(), df['z_a_pg'].min(), df['z_ppp_pg'].min(), df['z_sog_pg'].min(), df['z_pim_pg'].min(), df['z_hits_pg'].min(), df['z_blk_pg'].min(), df['z_tk_pg'].min()) \
                    if pos in ('D', 'S') \
                    else min(df['z_wins_pg'].min(), df['z_saves_pg'].min(), df['z_gaa_pg'].min(), df['z_save%_pg'].min())
        max_z = max(df['z_g_pg'].max(), df['z_a_pg'].max(), df['z_ppp_pg'].max(), df['z_sog_pg'].max(), df['z_pim_pg'].max(), df['z_hits_pg'].max(), df['z_blk_pg'].max(), df['z_tk_pg'].max()) \
                if  pos == 'F' \
                else max(df['z_pts_pg'].max(), df['z_g_pg'].max(), df['z_a_pg'].max(), df['z_ppp_pg'].max(), df['z_sog_pg'].max(), df['z_pim_pg'].max(), df['z_hits_pg'].max(), df['z_blk_pg'].max(), df['z_tk_pg'].max()) \
                    if pos in ('D', 'S') \
                    else max(df['z_wins_pg'].max(), df['z_saves_pg'].max(), df['z_gaa_pg'].max(), df['z_save%_pg'].max())

    fig = []

    for player_id in player_ids:

        df_player = df.query('player_id==@player_id').copy(deep=True).reindex()
        df_player.fillna(0, inplace=True)

        kwargs = {'id': player_id}
        player = Player().fetch(**kwargs)
        # pos = player.primary_position
        player_name = player.full_name

        if stat_type == 'Cumulative':
            scoring_categories = forward_score_categories \
                                 if pos == 'F' \
                                 else defense_score_categories \
                                      if pos in ('D', 'S') \
                                      else goalie_score_categories
            scoring_category_labels = forward_score_category_labels \
                                      if pos == 'F' \
                                      else defense_score_category_labels \
                                           if pos in ('D', 'S') \
                                           else goalie_score_category_labels
        else: # stat_type == 'Per Game':
            scoring_categories = forward_pg_score_categories \
                                 if pos == 'F' \
                                 else defense_pg_score_categories \
                                      if pos in ('D', 'S') \
                                      else goalie_pg_score_categories
            scoring_category_labels = forward_pg_score_category_labels \
                                      if pos == 'F' \
                                      else defense_pg_score_category_labels \
                                      if pos in ('D', 'S') \
                                           else goalie_pg_score_category_labels

        df_temp = df_player[scoring_categories]
        data = df_temp.to_dict('split')['data'][0]

        scoring_category_labels = [*scoring_category_labels, scoring_category_labels[0]]
        data = [*data, data[0]]

        fig.append(go.Scatterpolar(r=data, theta=scoring_category_labels, line={'shape': 'spline'}, name=player_name))

    fig = go.Figure(
        data=fig,
        layout=go.Layout(
            template='plotly_dark',
            polar={'radialaxis': {'visible': True}},
            showlegend=True,
            title=go.layout.Title(text='Category Z-scores'),
            width=800, height=600,
            paper_bgcolor='rgba(0,0,0,0)', # transparent
        )
    )

    fig.update_polars(radialaxis=dict(range=[min_z, max_z]))

    radar_chart = pyo.plot(fig, output_type='div')

    # name = player_name.replace(' ', '_')
    # plt.savefig(f'./output/images/scoring_category_radar_chart_for_{name}.png')
    # # mpld3.save_html(fig, f'./output/images/scoring_category_radar_chart_for_{name}.html')

    # plt.close()

    # # open radar chart
    # os.system(f'start ./output/images/scoring_category_radar_chart_for_{name}.png')

    return radar_chart

def scoring_category_trend_charts(pool: 'HockeyPool', df: pd.DataFrame, player_ids: List):

    # overall rank, based on Fantrax categories
    goalie_compare_data = ['games_started', 'wins', 'gaa', 'saves', 'save%']
    skater_compare_data = ['toi_even_sec', 'toi_pp_sec', 'toi_pp_ratio_ra', 'points', 'goals', 'assists', 'points_pp', 'shots', 'takeaways', 'hits', 'blocked']

    players = []
    for player_id in player_ids:

        player = Player().fetch(**{'id': player_id})
        players.append({'name': player.full_name, 'pos': player.primary_position})

    positions = [x['pos'] for x in players]
    if 'G' in positions and any(['D' in positions, 'LW' in positions, 'C' in positions, 'RW' in positions]):
        sg.popup_notify('Cannot mix goalies & skaters in same comparison...')
        return

    categories = goalie_compare_data if 'G' in positions else skater_compare_data

    # set rows & columns for subplots
    rows = len(categories)
    cols = len(players)

    if 'G' in positions:
            subplot_titles = ['Starts',
                              'Wins',
                              'GAA',
                              'Saves',
                              'Save %'
                             ]
    else:
        subplot_titles = ['Even Time-on-Ice',
                          'Powerplay Time-on-Ice',
                          'Powerplay Time-on-Ice %',
                          'Points',
                          'Goals',
                          'Assists',
                          'Powerplay Points',
                          'Shots on Goal',
                          'Takeaways',
                          'Hits',
                          'Blocks',
                         ]

    subplot_titles = np.repeat(subplot_titles, len(players))

    column_titles= [x['name'] for x in players]

    fig = make_subplots(rows=rows,
                        cols=cols,
                        subplot_titles=subplot_titles,
                        column_titles=column_titles,
                        row_heights=[200 for i in range(len(skater_compare_data))],
                        #  shared_yaxes=True
                    )

    # get maximum values per category to compare players on the same scale
    df_temp = df.copy(deep=True)
    if 'G' in positions:

        df_temp['games_started'] = df_temp.groupby('player_id')['games_started'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_games_started = df_temp['games_started'].max()
        min_games_started = df_temp['games_started'].min()
        max_games_started = ceil(max_games_started) + 0.5 if max_games_started % 1 == 0 else ceil(max_games_started)
        min_games_started = floor(min_games_started) - 0.5 if min_games_started % 1 == 0 else floor(min_games_started)

        df_temp['wins'] = df_temp.groupby('player_id')['wins'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_wins = df_temp['wins'].max()
        min_wins = df_temp['wins'].min()
        max_wins = ceil(max_wins) + 0.5 if max_wins % 1 == 0 else ceil(max_wins)
        min_wins = floor(min_wins) - 0.5 if min_wins % 1 == 0 else floor(min_wins)

        df_temp['saves'] = df_temp.groupby('player_id')['saves'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_saves = df_temp['saves'].max()
        min_saves = df_temp['saves'].min()
        max_saves = ceil(max_saves) + 0.5 if max_saves % 1 == 0 else ceil(max_saves)
        min_saves = floor(min_saves) - 0.5 if min_saves % 1 == 0 else floor(min_saves)

        df_temp['gaa'] = df_temp.groupby('player_id')['gaa'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_gaa = df_temp['gaa'].max()
        min_gaa = df_temp['gaa'].min()
        max_gaa = ceil(max_gaa) + 0.05 if max_gaa % 1 == 0 else ceil(max_gaa)
        min_gaa = floor(min_gaa) - 0.05 if min_gaa % 1 == 0 else floor(min_gaa)

        df_temp['save%'] = df_temp.groupby('player_id')['save%'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_save_pc = df_temp['save%'].max()
        min_save_pc = df_temp['save%'].min()
        max_save_pc = ceil(max_save_pc) + 0.05 if max_save_pc % 1 == 0 else ceil(max_save_pc)
        min_save_pc = floor(min_save_pc) - 0.05 if min_save_pc % 1 == 0 else floor(min_save_pc)

    else:

        df_temp['points'] = df_temp.groupby('player_id')['points'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_pts = df_temp['points'].max()
        min_pts = df_temp['points'].min()
        max_pts = ceil(max_pts) if max_pts % 1 == 0 else ceil(max_pts)
        min_pts = floor(min_pts) - 0.5 if min_pts % 1 == 0 and floor(min_pts) != 0 else 0

        df_temp['goals'] = df_temp.groupby('player_id')['goals'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_g = df_temp['goals'].max()
        min_g = df_temp['goals'].min()
        max_g = ceil(max_g) if max_g % 1 == 0 else ceil(max_g)
        min_g = floor(min_g) - 0.5 if min_g % 1 == 0 and floor(min_g) != 0 else 0

        df_temp['toi_pp_ratio_ra'] = df_temp.groupby('player_id')['toi_pp_ratio_ra'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_toi_pp_ra = df_temp['toi_pp_ratio_ra'].max()
        min_toi_pp_ra = df_temp['toi_pp_ratio_ra'].min()
        max_toi_pp_ra = ceil(max_toi_pp_ra) if max_toi_pp_ra % 1 == 0 else ceil(max_toi_pp_ra)
        min_toi_pp_ra = floor(min_toi_pp_ra) - 1 if min_toi_pp_ra % 1 == 0 and floor(min_toi_pp_ra) != 0 else 0

        df_temp['assists'] = df_temp.groupby('player_id')['assists'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_a = df_temp['assists'].max()
        min_a = df_temp['assists'].min()
        max_a = ceil(max_a) if max_a % 1 == 0 else ceil(max_a)
        min_a = floor(min_a) - 0.5 if min_a % 1 == 0 and floor(min_a) != 0 else 0

        df_temp['points_pp'] = df_temp.groupby('player_id')['points_pp'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_ppp = df_temp['points_pp'].max()
        min_ppp = df_temp['points_pp'].min()
        max_ppp = ceil(max_ppp) if max_ppp % 1 == 0 else ceil(max_ppp)
        min_ppp = floor(min_ppp) - 0.5 if min_ppp % 1 == 0 and floor(min_ppp) != 0 else 0

        df_temp['shots'] = df_temp.groupby('player_id')['shots'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_sog = df_temp['shots'].max()
        min_sog = df_temp['shots'].min()
        max_sog = ceil(max_sog) if max_sog % 1 == 0 else ceil(max_sog)
        min_sog = floor(min_sog) - 0.5 if min_sog % 1 == 0 and floor(min_sog) != 0 else 0

        # df_temp['pim'] = df_temp.groupby('player_id')['pim'].transform(lambda x: x.rolling(rolling_period, 1).mean())
        # max_pim = df_temp['pim'].max()
        # min_pim = df_temp['pim'].min()
        # max_pim = ceil(max_pim) if max_pim % 1 == 0 else ceil(max_pim)
        # min_pim = floor(min_pim) - 0.5 if min_pim % 1 == 0 and floor(min_pim) != 0 else 0

        df_temp['hits'] = df_temp.groupby('player_id')['hits'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_hits = df_temp['hits'].max()
        min_hits = df_temp['hits'].min()
        max_hits = ceil(max_hits) if max_hits % 1 == 0 else ceil(max_hits)
        min_hits = floor(min_hits) - 0.5 if min_hits % 1 == 0 and floor(min_hits) != 0 else 0

        df_temp['blocked'] = df_temp.groupby('player_id')['blocked'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_blk = df_temp['blocked'].max()
        min_blk = df_temp['blocked'].min()
        max_blk = ceil(max_blk) if max_blk % 1 == 0 else ceil(max_blk)
        min_blk = floor(min_blk) - 0.5 if min_blk % 1 == 0 and floor(min_blk) != 0 else 0

        df_temp['takeaways'] = df_temp.groupby('player_id')['takeaways'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_tk = df_temp['takeaways'].max()
        min_tk = df_temp['takeaways'].min()
        max_tk = ceil(max_tk) if max_tk % 1 == 0 else ceil(max_tk)
        min_tk = floor(min_tk) - 0.5 if min_tk % 1 == 0 and floor(min_tk) != 0 else 0

        # convert to timedelta...
        # get maximum values for toi columns to compare players on the same scale
        df_temp['toi_even_sec'] = df_temp.groupby('player_id')['toi_even_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_toi_even = df_temp['toi_even_sec'].apply(lambda s: pd.Timedelta(seconds=s)).astype('timedelta64[s]').astype('int64').max()
        min_toi_even = df_temp['toi_even_sec'].apply(lambda s: pd.Timedelta(seconds=s)).astype('timedelta64[s]').astype('int64').min()
        max_toi_even = ceil(max_toi_even) + 30 if max_toi_even % 1 == 0 else ceil(max_toi_even)
        min_toi_even = floor(min_toi_even) - 30 if min_toi_even % 1 == 0 and floor(min_toi_even) != 0 else 0

        df_temp['toi_pp_sec'] = df_temp.groupby('player_id')['toi_pp_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        max_toi_pp = df_temp['toi_pp_sec'].apply(lambda s: pd.Timedelta(seconds=s)).astype('timedelta64[s]').astype('int64').max()
        min_toi_pp = df_temp['toi_pp_sec'].apply(lambda s: pd.Timedelta(seconds=s)).astype('timedelta64[s]').astype('int64').min()
        max_toi_pp = ceil(max_toi_pp) + 30 if max_toi_pp % 1 == 0 else ceil(max_toi_pp)
        min_toi_pp = floor(min_toi_pp) - 30 if min_toi_pp % 1 == 0 and floor(min_toi_pp) != 0 else 0

    idx = 1
    for player_id in player_ids:

        df_player = df.query('player_id==@player_id').copy(deep=True).reindex()
        df_player.fillna(0, inplace=True)

        for i, cat in enumerate(categories):

            df_temp = df_player.copy(deep=True)
            df_temp = df_temp[['player_id', 'date', cat]]
            df_temp[cat] = df_temp.groupby('player_id')[cat].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())

            # add trendline
            if df_temp[cat].size > 0:
                model = LinearRegression().fit(np.array(df_temp['date'].astype('datetime64[ns]').astype('int64')).reshape(-1,1), np.array(df_temp[cat]))
                y_hat = model.predict(np.array(df_temp['date'].astype('datetime64[ns]').astype('int64')).reshape(-1,1))

            if cat in ('toi_even_sec', 'toi_pp_sec'):
                # convert to timedelta...
                df_temp['time'] = df_temp[cat].apply(lambda s: pd.Timedelta(seconds=s))

                fig.add_trace(go.Scatter(x=df_temp['date'],
                                         y=df_temp['time'].astype('timedelta64[s]').astype('int64'),
                                         marker={'color': 'red', 'symbol': 'x', 'size': 10},
                                         mode="markers",
                                         hovertemplate=df_temp['time'].astype('timedelta64[s]').astype('int64').apply(lambda t: ''.join(['Date: %{x} <br>TOI: ', seconds_to_string_time(t)])),
                                         cliponaxis=False,
                                ),
                        row=i + 1, col=idx
                        )

            else:

                fig.add_trace(go.Scatter(x=df_temp['date'],
                                         y=df_temp[cat],
                                         marker={'color': 'red', 'symbol': 'x', 'size': 10},
                                         mode="markers",
                                        # hovertemplate=''.join(['Date: %{x} <br>', f'{subplot_titles[cat]}'+': %{y}']),
                                         cliponaxis=False,
                                    ),
                        row=i + 1, col=idx
                        )

            # add trendline
            if df_temp[cat].size > 0:
                fig.add_trace(go.Scatter(x=df_temp['date'], y=y_hat, marker={'color': 'black'}, mode='lines'), row=i + 1, col=idx)

        idx = idx + 1

    fig.update_layout(overwrite=True,
                      height=len(categories) * 210,
                      width=1800 if len(players) >= 2 else 900,
                      title_text=f'{rolling_avg_period}-Game Rolling Average',
                      title_font_size=36,
                      title_x=0.5,
                      template='plotly_dark',
                      showlegend=False,
                )
    fig.update_xaxes(
        mirror=True,
        ticks='outside',
        showline=True,
    )
    fig.update_yaxes(
        mirror=True,
        ticks='outside',
        showline=True,
    )

    # fix up tick labels
    toi_even_ticks = pd.Series(range(min_toi_even, max_toi_even, 60 if (max_toi_even - min_toi_even) < 120 else 120))
    toi_pp_ticks = pd.Series(range(min_toi_pp, max_toi_pp, 30 if (max_toi_pp - min_toi_pp) < 60 else 60))

    for i in range(1, idx):

        fig.update_yaxes(range=[min_toi_even, max_toi_even,], tickmode='array', tickvals=toi_even_ticks, ticktext=toi_even_ticks.apply(seconds_to_string_time), row=skater_compare_data.index('toi_even_sec') + 1, col=i)
        fig.update_yaxes(range=[min_toi_pp, max_toi_pp,], tickmode='array', tickvals=toi_pp_ticks, ticktext=toi_pp_ticks.apply(seconds_to_string_time), row=skater_compare_data.index('toi_pp_sec') + 1, col=i)
        fig.update_yaxes(range=[min_toi_pp_ra, max_toi_pp_ra,], row=skater_compare_data.index('toi_pp_ratio_ra') + 1, col=i)
        fig.update_yaxes(range=[min_pts, max_pts,], row=skater_compare_data.index('points') + 1, col=i)
        fig.update_yaxes(range=[min_g, max_g,], row=skater_compare_data.index('goals') + 1, col=i)
        fig.update_yaxes(range=[min_a, max_a,], row=skater_compare_data.index('assists') + 1, col=i)
        fig.update_yaxes(range=[min_ppp, max_ppp,], row=skater_compare_data.index('points_pp') + 1, col=i)
        fig.update_yaxes(range=[min_sog, max_sog,], row=skater_compare_data.index('shots') + 1, col=i)
        fig.update_yaxes(range=[min_tk, max_tk,], row=skater_compare_data.index('takeaways') + 1, col=i)
        fig.update_yaxes(range=[min_hits, max_hits,], row=skater_compare_data.index('hits') + 1, col=i)
        fig.update_yaxes(range=[min_blk, max_blk,], row=skater_compare_data.index('blocked') + 1, col=i)
        # fig.update_yaxes(range=[min_pim, max_pim,], row=skater_compare_data.index('points') + 1, col=i)

    # column titles are overlaying the first subplot title
    fig.for_each_annotation(lambda a: a.update(y = 1.01) if a.text in column_titles else a)
    fig.for_each_annotation(lambda a: a.update(font=dict(size=24)) if a.text in column_titles else a)

    rolling_average_charts = pyo.plot(fig, output_type='div')

    return rolling_average_charts
