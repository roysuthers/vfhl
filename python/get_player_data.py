# Import Python modules
import json
import os
import sys
import sqlite3
import textwrap
import time
import traceback
import webbrowser
from collections import defaultdict
from copy import copy, deepcopy
from datetime import date, datetime, timedelta
from numpy import int32, int64
from os import path, stat
import requests
from typing import Dict, List, Tuple, Union
from urllib.request import pathname2url

import jmespath as j
# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# import plotly.express as px
from numpy.polynomial.polynomial import polyfit
import PySimpleGUI as sg

import clsSeason as Season
from constants import  DATABASE, NHL_API_URL
from utils import calculate_age, process_dict, seconds_to_string_time, split_seasonID_into_component_years, string_to_time

# formatting for ranking tables
f_0_decimals = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.0f}'.format(x)", '<string>', 'eval')
f_0_decimals_show_0 = compile("lambda x: '' if pd.isna(x) or x == '' else '{:0.0f}'.format(x)", '<string>', 'eval')
f_0_toi_to_empty = compile("lambda x: '' if x in ('00:00', None) or pd.isna(x) else x", '<string>', 'eval')
f_0_toi_to_empty_and_show_plus = compile("lambda x: '' if x in ('+00:00', '+0:00', '00:00', '0:00', None) or pd.isna(x) else x", '<string>', 'eval')
f_1_decimal = compile("lambda x: '' if pd.isna(x) or x in ['', 0] or round(x,1)==0.0 else '{:0.1f}'.format(x)", '<string>', 'eval')
f_1_decimal_show_0_and_plus = compile("lambda x: '' if pd.isna(x) or x=='' or abs(round(x,1))==0.0 else '{:+0.1f}'.format(x)", '<string>', 'eval')
f_2_decimals = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.2f}'.format(x)", '<string>', 'eval')
f_2_decimals_show_0 = compile("lambda x: '' if pd.isna(x) or x=='' else '{:}'.format(int(x)) if x==0 else '{:0.2f}'.format(x)", '<string>', 'eval')
f_3_decimals_no_leading_0 = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:.3f}'.format(x).lstrip('0')", '<string>', 'eval')
f_nan_to_empty = compile("lambda x: '' if pd.isna(x) else x", '<string>', 'eval')
f_str = compile("lambda x: '' if pd.isna(x) or x == '' else x", '<string>', 'eval')

skater_position_codes = ("LW", "C", "RW", "D")
forward_position_codes = ("LW", "C", "RW")
defense_position_code = "D"
goalie_position_code = "G"

minimum_one_game_filter = 'games >= 1'
minimum_skater_games_percent = 20
minimum_skater_games_filter = f'percent_of_team_games >= {minimum_skater_games_percent}'
minimum_goalie_games_percent = 20
minimum_goalie_starts_filter = f'percent_of_team_games >= {minimum_goalie_games_percent}'

skaters_filter = f'pos in {skater_position_codes}'
forwards_filter = f'pos in {forward_position_codes}'
defense_filter = f'pos == "{defense_position_code}"'
goalie_filter = f'pos == "{goalie_position_code}"'

###############################################
###############################################
# Fantrax scoring categories
###############################################
# Forwards and Defense
sktr_categories = ['points', 'goals', 'assists', 'shots', 'points_pp', 'pim', 'hits', 'blocked', 'takeaways', 'penalties']
sktr_z_categories = ['z_points', 'z_goals', 'z_assists', 'z_shots', 'z_points_pp', 'z_pim', 'z_hits', 'z_blocked', 'z_takeaways', 'z_penalties']
###############################################
# Goalies
goalie_categories = ['wins', 'saves', 'gaa', 'save%']
goalie_z_categories = ['z_wins', 'z_saves', 'z_gaa', 'z_save%']
###############################################
###############################################
# Summary z-score columns
###############################################
# stat z-scores
sktr_summary_z_scores = ['score', 'offense', 'peripheral']
g_summary_z_scores = ['score', 'g_count', 'g_ratio']
###############################################
###############################################

min_cat = defaultdict(None)
max_cat = defaultdict(None)
mean_cat = defaultdict(None)
std_cat = defaultdict(None)

# Stop the SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
pd.options.mode.chained_assignment = None  # default='warn'

def add_draft_list_columns_to_df(season_id: str, df: pd.DataFrame):

    sql = f'select * from dfDraftResults where season_id={season_id}'
    df_draft_list = pd.read_sql(sql, con=get_db_connection())

    # add draft list columns to df
    df.set_index(['player_id'], inplace=True)
    df_draft_list.set_index(['player_id'], inplace=True)

    # Rename columns in df_draft_list
    df_draft_list.rename(columns={'season_id': 'seasonID', 'player': 'name', 'pool_team': 'picked_by'}, inplace=True)

    # udpate players in df
    df = df.assign(
        round = df_draft_list['round'],
        pick = df_draft_list['pick'],
        overall = df_draft_list['overall'],
        picked_by = df_draft_list['picked_by'],
    )

    # add players not in df
    # Exclude empty entries before concatenation
    non_empty_entries = df_draft_list.loc[~df_draft_list.index.isin(df.index)]
    if not non_empty_entries.empty:
        df = pd.concat([df, non_empty_entries])

    df.fillna({'round': '','pick': '','overall': '','picked_by': ''}, inplace=True)

    df.reset_index(inplace=True)

    return df

def add_pre_draft_keeper_list_column_to_df(pool_id: str, df: pd.DataFrame):

    sql = f'select player_id, "Yes" as pre_draft_keeper, pool_team as pre_draft_manager from KeeperListsArchive where pool_id={pool_id}'
    df_keeper_list = pd.read_sql(sql, con=get_db_connection())

    # add pre-draft keeper columns to df
    df.set_index(['player_id'], inplace=True)
    df_keeper_list.set_index(['player_id'], inplace=True)

    df['pre_draft_keeper'] = df_keeper_list['pre_draft_keeper']
    df['pre_draft_manager'] = df_keeper_list['pre_draft_manager']

    df.fillna({'pre_draft_keeper': ''}, inplace=True)
    df.fillna({'pre_draft_manager': ''}, inplace=True)

    df.reset_index(inplace=True)

    return

def aggregate_game_stats(df: pd.DataFrame, stat_type: str='Cumulative', ewma_span: int=10) -> pd.DataFrame:

    def average_used_for_trending(x):
        try:
            return x.iloc[-ewm_span_sktr - 1]
        except IndexError:
            return None

    def per_60_minutes(df):
        def wrapper(x):
            player_toi_sec = df.loc[x.index, 'toi_sec'].sum()
            x_agg = x.sum() / player_toi_sec * 3600
            return x_agg
        return wrapper

    stat_type_agg_method = eval("'sum' if stat_type == 'Cumulative' else 'mean' if stat_type == 'Per game' else per_60_minutes(df) if stat_type == 'Per 60 minutes' else ewma(df)")

    max_games_sktr = df.query(skaters_filter).sort_values(['player_id', 'date']).groupby(['player_id'], as_index=False).agg(games = ('player_id', 'count'))['games'].max()
    max_games_g = df.query(goalie_filter).sort_values(['player_id', 'date']).groupby(['player_id'], as_index=False).agg(games = ('player_id', 'count'))['games'].max()

    calculate_ewm_args(ewma_span, max_games_sktr, max_games_g)

    df_agg_stats = df.sort_values(['player_id', 'date']).groupby(['player_id'], as_index=False).agg(
        assists = ('assists', stat_type_agg_method),
        assists_gw = ('assists_gw', 'sum'),
        assists_ot = ('assists_ot', 'sum'),
        assists_pp = ('assists_pp', 'sum'),
        assists_sh = ('assists_sh', 'sum'),
        blocked = ('blocked', stat_type_agg_method),
        corsi_against = ('corsi_against', 'sum'),
        corsi_for = ('corsi_for', 'sum'),
        evg_on_ice = ('evg_on_ice', 'sum'),
        evg_point = ('evg_point', 'sum'),
        fenwick_against = ('fenwick_against', 'sum'),
        fenwick_for = ('quality_starts', 'sum'),
        first_game = ('date', 'first'),
        game_misconduct_penalties = ('game_misconduct_penalties', stat_type_agg_method),
        games = ('player_id', 'count'),
        games_started = ('games_started', 'sum'),
        goals = ('goals', stat_type_agg_method),
        goals_against = ('goals_against', stat_type_agg_method),
        # goals_against_sum = ('goals_against', 'sum'),
        goals_gw = ('goals_gw', 'sum'),
        goals_ot = ('goals_ot', 'sum'),
        goals_pp = ('goals_pp', 'sum'),
        goals_ps = ('goals_ps', 'sum'),
        goals_sh = ('goals_sh', 'sum'),
        hattricks = ('hattricks', stat_type_agg_method),
        highDangerShots = ('highDangerShots', stat_type_agg_method),
        highDangerShotsOnGoal = ('highDangerShotsOnGoal', stat_type_agg_method),
        hits = ('hits', stat_type_agg_method),
        last_game = ('date', 'last'),
        lowDangerShots = ('lowDangerShots', stat_type_agg_method),
        lowDangerShotsOnGoal = ('lowDangerShotsOnGoal', stat_type_agg_method),
        major_penalties = ('major_penalties', stat_type_agg_method),
        match_penalties = ('match_penalties', stat_type_agg_method),
        mediumDangerShots = ('mediumDangerShots', stat_type_agg_method),
        mediumDangerShotsOnGoal = ('mediumDangerShotsOnGoal', stat_type_agg_method),
        minor_penalties = ('minor_penalties', stat_type_agg_method),
        misconduct_penalties = ('misconduct_penalties', stat_type_agg_method),
        missed_shots = ('missed_shots', stat_type_agg_method),
        missed_shots_crossbar = ('minor_penalties', 'sum'),
        missed_shots_goalpost = ('minor_penalties', 'sum'),
        name = ('name', 'last'),
        penalties = ('penalties', stat_type_agg_method),
        pim = ('pim', stat_type_agg_method),
        player_id = ('player_id', 'last'),
        points = ('points', stat_type_agg_method),
        points_pp = ('points_pp', stat_type_agg_method),
        points_pp_sum = ('points_pp', 'sum'),
        pos = ('pos', 'last'),
        ppg_on_ice = ('ppg_on_ice', 'sum'),
        ppg_point = ('ppg_point', 'sum'),
        quality_starts = ('quality_starts', 'sum'),
        really_bad_starts = ('really_bad_starts', 'sum'),
        saves = ('saves', stat_type_agg_method),
        saves_sum = ('saves', 'sum'),
        # seasonID = ('seasonID', 'last'),
        shots = ('shots', stat_type_agg_method),
        shots_against = ('shots_against', stat_type_agg_method),
        shots_against_sum = ('shots_against', 'sum'),
        shots_powerplay = ('shots_powerplay', stat_type_agg_method),
        shots_powerplay_sum = ('shots_powerplay', 'sum'),
        shutouts = ('shutouts', stat_type_agg_method),
        takeaways = ('takeaways', stat_type_agg_method),
        team_abbr = ('team_abbr', 'last'),
        team_id = ('team_id', 'last'),
        team_toi_pp_pg_sec = ('team_toi_pp_sec', 'mean'),
        team_toi_pp_sec = ('team_toi_pp_sec', 'sum'),
        team_toi_pp_sec_ewm_base = ('team_toi_pp_sec_ewm', average_used_for_trending),
        team_toi_pp_sec_ewm= ('team_toi_pp_sec_ewm', 'last'),
        toi_even_pg_sec = ('toi_even_sec', 'mean'),
        toi_even_sec = ('toi_even_sec', 'sum'),
        toi_even_sec_ewm_base = ('toi_even_sec_ewm', average_used_for_trending),
        toi_even_sec_ewm= ('toi_even_sec_ewm', 'last'),
        toi_pg_sec = ('toi_sec', 'mean'),
        toi_pp_pg_ratio_ewm_base = ('toi_pp_pg_ratio_ewm', average_used_for_trending),
        toi_pp_pg_ratio_ewm= ('toi_pp_pg_ratio_ewm', 'last'),
        toi_pp_pg_sec = ('toi_pp_sec', 'mean'),
        toi_pp_ratio = ('toi_pp_ratio', 'last'),
        toi_pp_sec = ('toi_pp_sec', 'sum'),
        toi_pp_sec_base = ('toi_pp_sec', 'mean'),
        toi_pp_sec_ewm_base = ('toi_pp_sec_ewm', average_used_for_trending),
        toi_pp_sec_ewm= ('toi_pp_sec_ewm', 'last'),
        toi_sec = ('toi_sec', 'sum'),
        toi_sec_ewm_base = ('toi_sec_ewm', average_used_for_trending),
        toi_sec_ewm= ('toi_sec_ewm', 'last'),
        toi_sh_pg_sec = ('toi_sh_sec', 'mean'),
        toi_sh_sec = ('toi_sh_sec', 'sum'),
        toi_sh_sec_ewm_base = ('toi_sh_sec_ewm', average_used_for_trending),
        toi_sh_sec_ewm= ('toi_sh_sec_ewm', 'last'),
        wins = ('wins', stat_type_agg_method),
        wins_ot = ('wins_ot', stat_type_agg_method),
        wins_so = ('wins_so', stat_type_agg_method),
        xGoals = ('xGoals', stat_type_agg_method),
        xGoalsAgainst = ('xGoalsAgainst', stat_type_agg_method),
    )

    # if stats have not been yet been retrieved from nhl rest api, for the current week, df_agg_stats will be emtpy
    if len(df_agg_stats.index) == 0:
        return None

    ########################################################################################################
    df_agg_stats.set_index('player_id', inplace=True)
    ########################################################################################################

    # time-on-ice in minutes
    toi_min = df_agg_stats['toi_sec'].div(60).astype(int)

    # even goals IPP
    evg_ipp = np.where(df_agg_stats['evg_on_ice'] != 0, df_agg_stats['evg_point'] / df_agg_stats['evg_on_ice'] * 100, np.nan)
    evg_ipp = pd.Series(evg_ipp, index=df_agg_stats.index)

    # powerplay goals IPP
    ppg_ipp = np.where(df_agg_stats['ppg_on_ice'] != 0, df_agg_stats['ppg_point'] / df_agg_stats['ppg_on_ice'] * 100, np.nan)
    ppg_ipp = pd.Series(ppg_ipp, index=df_agg_stats.index)

    # get ratio of powerplay time-on-ice vs. team powerplay time-on-ice
    toi_pp_pg_ratio = df_agg_stats['toi_pp_pg_sec'] / df_agg_stats['team_toi_pp_pg_sec'] * 100

    def format_time(df, column):
        minutes = (df[column] / 60).astype(int)
        seconds = (df[column] % 60).astype(int)
        return minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    toi_pg = format_time(df_agg_stats, 'toi_pg_sec')

    # convert time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_pg_ewm_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_sec_ewm'].astype(int).apply(seconds_to_string_time))
    toi_pg_ewm_last = pd.Series(toi_pg_ewm_last, index=df_agg_stats.index)

    toi_even_pg = format_time(df_agg_stats, 'toi_even_pg_sec')

    # convert even time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_even_pg_ewm_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_even_sec_ewm'].astype(int).apply(seconds_to_string_time))
    toi_even_pg_ewm_last = pd.Series(toi_even_pg_ewm_last, index=df_agg_stats.index)

    toi_pp_pg = format_time(df_agg_stats, 'toi_pp_pg_sec')

    # convert powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_pp_pg_ewm_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_pp_sec_ewm'].astype(int).apply(seconds_to_string_time))
    toi_pp_pg_ewm_last = pd.Series(toi_pp_pg_ewm_last, index=df_agg_stats.index)

    team_toi_pp_pg = format_time(df_agg_stats, 'team_toi_pp_pg_sec')

    # convert team powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    team_toi_pp_pg_ewm_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['team_toi_pp_sec_ewm'].astype(int).apply(seconds_to_string_time))
    team_toi_pp_pg_ewm_last = pd.Series(team_toi_pp_pg_ewm_last, index=df_agg_stats.index)

    # calc powerplay goals per 2 penalty minutes
    pp_goals_p120 = (df_agg_stats['goals_pp'] * 120) / df_agg_stats['toi_pp_sec']

    # calc powerplay shots-on-goal per 2 penalty minutes
    pp_sog_p120 = np.where(df_agg_stats['toi_pp_sec'] != 0, (df_agg_stats['shots_powerplay_sum'] * 120) / df_agg_stats['toi_pp_sec'], np.nan)
    pp_sog_p120 = pd.Series(pp_sog_p120, index=df_agg_stats.index)

    # calc powerplay points per 2 penalty minutes
    pp_pts_p120 = np.where(toi_pp_pg == '00:00', np.nan, (df_agg_stats['points_pp_sum'] * 120) / df_agg_stats['toi_pp_sec'])
    pp_pts_p120 = pd.Series(pp_pts_p120, index=df_agg_stats.index)

    # calc missed shots - crossbar + goalpost
    # Need cumulative per game & per 60 calcs
    missed_shots_metal = np.where(df_agg_stats['pos'] == goalie_position_code, np.nan, df_agg_stats['missed_shots_crossbar'].add(df_agg_stats['missed_shots_goalpost']))
    if stat_type == 'Per game':
        missed_shots_metal = missed_shots_metal / df_agg_stats['games']
    elif stat_type == 'Per 60 minutes':
        missed_shots_metal = missed_shots_metal / df_agg_stats['toi_pg_sec'] * 3600

    # set toi_pp_pg_ratio & team_toi_pp_pg_ewm_last & toi_pp_pg_ratio_ewmto blank if toi_pp_pg is 0
    toi_pp_pg_ratio = toi_pp_pg_ratio.where(toi_pp_pg != '00:00', '')
    team_toi_pp_pg_ewm_last = team_toi_pp_pg_ewm_last.where(toi_pp_pg != '00:00', '')
    df_agg_stats['toi_pp_pg_ratio_ewm'] = df_agg_stats['toi_pp_pg_ratio_ewm'].where(toi_pp_pg != '00:00', 0)

    toi_sh_pg = format_time(df_agg_stats, 'toi_sh_pg_sec')

    # convert shorthand time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_sh_pg_ewm_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_sh_sec_ewm'].astype(int).apply(seconds_to_string_time))
    toi_sh_pg_ewm_last = pd.Series(toi_sh_pg_ewm_last, index=df_agg_stats.index)

    df_agg_stats['toi_sec_ewm'] = df_agg_stats['toi_sec_ewm'].fillna(0)
    df_agg_stats['toi_sec_ewm_base'] = df_agg_stats['toi_sec_ewm_base'].fillna(df_agg_stats['toi_sec_ewm'])

    def format_time_trend(df, column, base_column):
        result = df[column].sub(df[base_column])
        abs_result = result.abs()
        minutes = (abs_result.div(60)).astype(int)
        seconds = (abs_result.mod(60)).astype(int)
        return np.sign(result).map({1: '+', -1: '-'}).fillna('').astype(str) + minutes.map('{:1d}'.format) + ':' + seconds.map('{:02d}'.format)

    toi_pg_sec_trend = format_time_trend(df_agg_stats, 'toi_sec_ewm', 'toi_sec_ewm_base')

    df_agg_stats['toi_even_sec_ewm'] = df_agg_stats['toi_even_sec_ewm'].fillna(0)
    df_agg_stats['toi_even_sec_ewm_base'] = df_agg_stats['toi_even_sec_ewm_base'].fillna(df_agg_stats['toi_even_sec_ewm'])

    toi_even_pg_sec_trend = format_time_trend(df_agg_stats, 'toi_even_sec_ewm', 'toi_even_sec_ewm_base')

    df_agg_stats['toi_pp_sec_ewm'] = df_agg_stats['toi_pp_sec_ewm'].fillna(0)
    df_agg_stats['toi_pp_sec_ewm_base'] = df_agg_stats['toi_pp_sec_ewm_base'].fillna(df_agg_stats['toi_pp_sec_ewm'])

    toi_pp_pg_sec_trend = format_time_trend(df_agg_stats, 'toi_pp_sec_ewm', 'toi_pp_sec_ewm_base')

    df_agg_stats['toi_pp_pg_ratio_ewm'] = df_agg_stats['toi_pp_pg_ratio_ewm'].fillna(0)
    df_agg_stats['toi_pp_pg_ratio_ewm_base'] = df_agg_stats['toi_pp_pg_ratio_ewm_base'].fillna(df_agg_stats['toi_pp_pg_ratio_ewm'])

    toi_pp_pg_ratio_trend = (df_agg_stats['toi_pp_pg_ratio_ewm'].sub(df_agg_stats['toi_pp_pg_ratio_ewm_base'])).fillna(0)

    df_agg_stats['toi_sh_sec_ewm'] = df_agg_stats['toi_sh_sec_ewm'].fillna(0)
    df_agg_stats['toi_sh_sec_ewm_base'] = df_agg_stats['toi_sh_sec_ewm_base'].fillna(df_agg_stats['toi_sh_sec_ewm'])

    toi_sh_pg_sec_trend = format_time_trend(df_agg_stats, 'toi_sh_sec_ewm', 'toi_sh_sec_ewm_base')

    df_g = df.query(goalie_filter)

    stat_type_agg_method = eval("ewma(df) if stat_type == 'EWMA' else 'sum'")
    gaa_and_save_percent_inputs = df_g.sort_values(['player_id','seasonID', 'date']).groupby(['player_id'], as_index=False).agg(
        player_id = ('player_id', 'last'),
        pos = ('pos', 'last'),
        goals_against = ('goals_against', stat_type_agg_method),
        shots_against = ('shots_against', stat_type_agg_method),
        saves = ('saves', stat_type_agg_method),
        toi_sec = ('toi_sec', stat_type_agg_method),
    )
    gaa_and_save_percent_inputs.set_index('player_id', inplace=True)
    # gaa
    gaa = gaa_and_save_percent_inputs['goals_against'] / gaa_and_save_percent_inputs['toi_sec'] * 3600
    # save%
    save_percent = gaa_and_save_percent_inputs['saves'] / gaa_and_save_percent_inputs['shots_against']

    # set NaN
    df_agg_stats.fillna({'games': 0, 'toi_pg': '', 'toi_even_pg': '', 'toi_pp_pg': '', 'team_toi_pp_pg': '', 'toi_sh_pg': ''}, inplace=True)

    teams_dict = df.groupby('team_id')['gamePk'].nunique().to_dict()
    team_games = df_agg_stats['team_id'].apply(lambda x: teams_dict[x] if pd.notna(x) else np.nan)
    # add column for ratio of games to team games
    percent_of_team_games = df_agg_stats['games'].div(team_games).multiply(100).round(1)

    ########################################################################################################
    # shooting percentage
    stat_type_agg_method = eval("ewma(df) if stat_type == 'EWMA' else 'sum'")
    goals_and_shots = df.sort_values(['player_id','seasonID', 'date']).groupby(['player_id'], as_index=False).agg(
        player_id = ('player_id', 'last'),
        goals = ('goals', stat_type_agg_method),
        shots = ('shots', stat_type_agg_method),
    )
    goals_and_shots.set_index('player_id', inplace=True)
    shooting_percent  = goals_and_shots['goals'].div(goals_and_shots['shots']).multiply(100).round(1)

    # Corsi For % & Fenwick For %
    def calculate_percent(df, column1, column2):
        if df[column1] + df[column2] != 0:
            return (df[column1] / (df[column1] + df[column2])) * 100
        else:
            return 0
    df_sktr = df_agg_stats.query(skaters_filter)
    corsi_for_percent = df_sktr.apply(lambda row: calculate_percent(row, 'corsi_for', 'corsi_against'), axis=1).round(1)
    fenwick_for_percent = df_sktr.apply(lambda row: calculate_percent(row, 'fenwick_for', 'fenwick_against'), axis=1).round(1)


    ########################################################################################################

    # goalie starts as percent of team games
    starts_as_percent = df_agg_stats['games_started'].div(team_games).round(2) * 100

    # quality starts as percent of starts
    quality_starts_as_percent = df_agg_stats['quality_starts'].div(df_agg_stats['games_started']).round(3) * 100

    # goalie's goals saved above expected (GSAx)
    goals_saved_above_expected = df_agg_stats['xGoalsAgainst'].sub(df_agg_stats['goals_against'])

    df_agg_stats = df_agg_stats.assign(
        corsi_for_percent = corsi_for_percent,
        evg_ipp = evg_ipp,
        fenwick_for_percent = fenwick_for_percent,
        gaa = gaa,
        goals_saved_above_expected = goals_saved_above_expected,
        missed_shots_metal = missed_shots_metal,
        percent_of_team_games = percent_of_team_games,
        pp_goals_p120 = pp_goals_p120,
        pp_pts_p120 = pp_pts_p120,
        pp_sog_p120 = pp_sog_p120,
        ppg_ipp = ppg_ipp,
        quality_starts_as_percent = quality_starts_as_percent,
        save_percent = save_percent,
        shooting_percent = shooting_percent,
        starts_as_percent = starts_as_percent,
        team_games = team_games,
        team_toi_pp_pg = team_toi_pp_pg,
        team_toi_pp_pg_ewm_last = team_toi_pp_pg_ewm_last,
        toi_even_pg = toi_even_pg,
        toi_even_pg_ewm_last = toi_even_pg_ewm_last,
        toi_even_pg_sec_trend = toi_even_pg_sec_trend,
        toi_min = toi_min,
        toi_pg = toi_pg,
        toi_pg_ewm_last = toi_pg_ewm_last,
        toi_pg_sec_trend = toi_pg_sec_trend,
        toi_pp_pg = toi_pp_pg,
        toi_pp_pg_ewm_last = toi_pp_pg_ewm_last,
        toi_pp_pg_ratio = toi_pp_pg_ratio,
        toi_pp_pg_ratio_trend = toi_pp_pg_ratio_trend,
        toi_pp_pg_sec_trend = toi_pp_pg_sec_trend,
        toi_sh_pg = toi_sh_pg,
        toi_sh_pg_ewm_last = toi_sh_pg_ewm_last,
        toi_sh_pg_sec_trend =toi_sh_pg_sec_trend,
    )

    # Replace the values in the 'save%' column with the values in the 'save_percent' column
    df_agg_stats[['save%', 'shooting%', 'corsi_for_%', 'fenwick_for_%']] = df_agg_stats[['save_percent', 'shooting_percent', 'corsi_for_percent', 'fenwick_for_percent']]

    # Discard the 'save_percent' column
    df_agg_stats.drop(['save_percent', 'shooting_percent', 'corsi_for_percent', 'fenwick_for_percent'], axis=1, inplace=True)

    ########################################################################################################
    df_agg_stats.reset_index(inplace=True)
    ########################################################################################################

    return df_agg_stats

def calc_breakout_threshold(name: str, height: str, weight: int, career_games: int) -> int:

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

def calculate_ewm_args(ewma_span, max_games_sktr, max_games_g):

    global ewm_span_sktr, ewm_span_g

    # ewm_span_sktr_percent_of_games = 50
    # ewm_span_g_percent_of_games = 50

    # # period for exponential moving averages
    # ewm_span_sktr_max = 10
    # ewm_span_g_max = 10

    # ewm_span_sktr = max(1, min(ewm_span_sktr_max, int(max_games_sktr // (100 / ewm_span_percent_of_games))))
    # ewm_span_g = max(1, min(ewm_span_g_max, int(max_games_g // (100 / ewm_span_percent_of_games))))
    # ewm_span_sktr = max(1, ewm_span_sktr_max, int(max_games_sktr // (100 / ewm_span_sktr_percent_of_games)))
    # ewm_span_g = max(1, ewm_span_g_max, int(max_games_g // (100 / ewm_span_g_percent_of_games)))
    # ewm_span_sktr = max(1, min(ewm_span_sktr_max, max_games_sktr))
    # ewm_span_g = max(1, min(ewm_span_g_max, max_games_g))
    ewm_span_sktr = max(1, min(ewma_span, max_games_sktr))
    ewm_span_g = max(1, min(ewma_span, max_games_g))

    return

def calc_z_scores(df: pd.DataFrame, positional_scoring: bool=False, stat_type: str='Cumulative'):

    try:

        # see https://projectile.pro/how-to-value-players-for-fantasy/ for discussion of Rate Stats, to account for players
        # with low number of games, to determine stat value for "games above average"

        skaters_mask = df.eval(skaters_filter)
        forward_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)
        # minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        # minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forward_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        sktr_games = df_sktr['games']
        f_games = df_f['games']
        d_games = df_d['games']
        g_games = df_g['games']

        sktr_max_games = sktr_games.max()
        f_max_games = f_games.max()
        d_max_games = d_games.max()
        g_max_games = g_games.max()

        # Calculate the multipliers
        if stat_type == 'Cumulative':
            sktr_multipliers = 1
            f_multipliers = 1
            d_multipliers = 1
            g_count_multipliers = 1
            g_ratio_multipliers = custom_decay(g_games, g_max_games)
        # elif stat_type == 'EWMA':
        #     # ewm_span_sktr & ewm_span_g are global, calculated in calculate_ewm_args()
        #     sktr_multipliers = custom_decay(sktr_games, ewm_span_sktr)
        #     f_multipliers = custom_decay(f_games, ewm_span_sktr)
        #     d_multipliers = custom_decay(d_games, ewm_span_sktr)
        #     g_count_multipliers = custom_decay(g_games, ewm_span_g)
        #     g_ratio_multipliers = g_count_multipliers
        else:
            sktr_multipliers = custom_decay(sktr_games, sktr_max_games)
            f_multipliers = custom_decay(f_games, f_max_games)
            d_multipliers = custom_decay(d_games, d_max_games)
            g_count_multipliers = custom_decay(g_games, g_max_games)
            g_ratio_multipliers = g_count_multipliers

        ##########################################################################
        # skaters
        ##########################################################################
        if positional_scoring is True:
            z_goals = pd.concat([((df_f['goals'] - mean_cat['f goals']) / std_cat['f goals']).multiply(f_multipliers, axis=0), ((df_d['goals'] - mean_cat['d goals']) / std_cat['d goals']).multiply(d_multipliers, axis=0)])
            z_assists = pd.concat([((df_f['assists'] - mean_cat['f assists']) / std_cat['f assists']).multiply(f_multipliers, axis=0), ((df_d['assists'] - mean_cat['d assists']) / std_cat['d assists']).multiply(d_multipliers, axis=0)])
            z_pim = pd.concat([((df_f['pim'] - mean_cat['f pim']) / std_cat['f pim']).multiply(f_multipliers, axis=0), ((df_d['pim'] - mean_cat['d pim']) / std_cat['d pim']).multiply(d_multipliers, axis=0)])
            z_penalties = pd.concat([((df_f['penalties'] - mean_cat['f penalties']) / std_cat['f penalties']).multiply(f_multipliers, axis=0), ((df_d['penalties'] - mean_cat['d penalties']) / std_cat['d penalties']).multiply(d_multipliers, axis=0)])
            z_shots = pd.concat([((df_f['shots'] - mean_cat['f shots']) / std_cat['f shots']).multiply(f_multipliers, axis=0), ((df_d['shots'] - mean_cat['d shots']) / std_cat['d shots']).multiply(d_multipliers, axis=0)])
            z_points_pp = pd.concat([((df_f['points_pp'] - mean_cat['f points_pp']) / std_cat['f points_pp']).multiply(f_multipliers, axis=0), ((df_d['points_pp'] - mean_cat['d points_pp']) / std_cat['d points_pp']).multiply(d_multipliers, axis=0)])
            z_hits = pd.concat([((df_f['hits'] - mean_cat['f hits']) / std_cat['f hits']).multiply(f_multipliers, axis=0), ((df_d['hits'] - mean_cat['d hits']) / std_cat['d hits']).multiply(d_multipliers, axis=0)])
            z_blocked = pd.concat([((df_f['blocked'] - mean_cat['f blocked']) / std_cat['f blocked']).multiply(f_multipliers, axis=0), ((df_d['blocked'] - mean_cat['d blocked']) / std_cat['d blocked']).multiply(d_multipliers, axis=0)])
            z_takeaways = pd.concat([((df_f['takeaways'] - mean_cat['f takeaways']) / std_cat['f takeaways']).multiply(f_multipliers, axis=0), ((df_d['takeaways'] - mean_cat['d takeaways']) / std_cat['d takeaways']).multiply(d_multipliers, axis=0)])
        else:
            z_goals = ((df_sktr['goals'] - mean_cat['sktr goals']) / std_cat['sktr goals']).multiply(sktr_multipliers, axis=0)
            z_assists = ((df_sktr['assists'] - mean_cat['sktr assists']) / std_cat['sktr assists']).multiply(sktr_multipliers, axis=0)
            z_pim = ((df_sktr['pim'] - mean_cat['sktr pim']) / std_cat['sktr pim']).multiply(sktr_multipliers, axis=0)
            z_penalties = ((df_sktr['penalties'] - mean_cat['sktr penalties']) / np.where(std_cat['sktr penalties'] != 0, std_cat['sktr penalties'], np.nan)).multiply(sktr_multipliers, axis=0)
            z_shots = ((df_sktr['shots'] - mean_cat['sktr shots']) / std_cat['sktr shots']).multiply(sktr_multipliers, axis=0)
            z_points_pp = ((df_sktr['points_pp'] - mean_cat['sktr points_pp']) / std_cat['sktr points_pp']).multiply(sktr_multipliers, axis=0)
            z_hits = ((df_sktr['hits'] - mean_cat['sktr hits']) / std_cat['sktr hits']).multiply(sktr_multipliers, axis=0)
            z_blocked = ((df_sktr['blocked'] - mean_cat['sktr blocked']) / std_cat['sktr blocked']).multiply(sktr_multipliers, axis=0)
            z_takeaways = ((df_sktr['takeaways'] - mean_cat['sktr takeaways']) / std_cat['sktr takeaways']).multiply(sktr_multipliers, axis=0)

        ##########################################################################
        # defense
        ##########################################################################
        z_points = ((df_d['points'] - mean_cat['d points']) / std_cat['d points']).multiply(d_multipliers, axis=0)

        ##########################################################################
        # goalies
        ##########################################################################
        z_wins = ((df_g['wins'] - mean_cat['wins']) / std_cat['wins']).multiply(g_count_multipliers, axis=0)
        z_saves = ((df_g['saves'] - mean_cat['saves']) / std_cat['saves']).multiply(g_count_multipliers, axis=0)
        z_gaa = (-1 * (df_g['gaa'] - mean_cat['gaa']) / std_cat['gaa']).multiply(g_ratio_multipliers, axis=0)
        z_save_pct = ((df_g['save%'] - mean_cat['save%']) / std_cat['save%']).multiply(g_ratio_multipliers, axis=0)

        df = df.assign(
            z_points = z_points,
            z_goals = z_goals,
            z_assists = z_assists,
            z_pim = z_pim,
            z_penalties = z_penalties,
            z_shots = z_shots,
            z_points_pp = z_points_pp,
            z_hits = z_hits,
            z_blocked = z_blocked,
            z_takeaways = z_takeaways,
            z_wins = z_wins,
            z_saves = z_saves,
            z_gaa = z_gaa,
            z_save_pct = z_save_pct,
        )

        df['z_save%'] = df['z_save_pct']
        df.drop('z_save_pct', axis=1, inplace=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return df

def calc_projected_draft_round(df_player_stats: pd.DataFrame):

        df_player_stats.set_index('player_id', inplace=True)

        # Find potential draft round using average draft position
        df_temp = df_player_stats.query('keeper!="Yes" and adp!=0 and team_abbr!="(N/A)"').sort_values('adp')
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr1'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)

        # Find potential draft round using Fantrax score
        df_temp = df_player_stats.query('keeper!="Yes" and fantrax_score!=0 and team_abbr!="(N/A)"').sort_values('fantrax_score', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr2'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)

        # Find potential draft round using z-score
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('score', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 12 else 12)

        # Find potential draft round using z-offense
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('offense', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr4'] = df_temp.apply(lambda x: x if x <= 12 else 12)

        # Find potential draft round using z-peripheral
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('peripheral', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr5'] = df_temp.apply(lambda x: x if x <= 12 else 12)

        # get mean, min & max pdr
        # pdr_columns = ['pdr1', 'pdr2', 'pdr3', 'pdr4', 'pdr5']
        pdr_columns = ['pdr1', 'pdr2', 'pdr4', 'pdr5']
        df_player_stats['pdr_min'] = pd.to_numeric(df_player_stats[pdr_columns].min(axis='columns'), errors='coerce').fillna(0).round().astype(int).astype(str)
        df_player_stats['pdr_max'] = pd.to_numeric(df_player_stats[pdr_columns].max(axis='columns'), errors='coerce').fillna(0).round().astype(int).astype(str)
        # df_player_stats['pdr_mean'] = pd.to_numeric(df_player_stats[pdr_columns].mean(axis='columns'), errors='coerce').fillna(0).round().astype(int).astype(str)
        # df_player_stats['pdr_min'] = pd.to_numeric(df_player_stats[pdr_columns].min(axis='columns'), errors='coerce').fillna(0)
        # df_player_stats['pdr_max'] = pd.to_numeric(df_player_stats[pdr_columns].max(axis='columns'), errors='coerce').fillna(0)
        df_player_stats['pdr_mean'] = pd.to_numeric(df_player_stats[pdr_columns].mean(axis='columns'), errors='coerce').fillna(0).round(1)

        # Set the value of the 'pdr' column based on the calculated values
        # conditions = [
        #     ~df_player_stats['pdr_min'].isnull() & ~df_player_stats['pdr_mean'].isnull() & (df_player_stats['pdr_min'] < df_player_stats['pdr_mean']),
        #     ~df_player_stats['pdr_mean'].isnull() & ~df_player_stats['pdr_max'].isnull() & (df_player_stats['pdr_mean'] < df_player_stats['pdr_max']),
        #     ~df_player_stats['pdr_min'].isnull(),
        #     ~df_player_stats['pdr_max'].isnull(),
        # ]
        # choices = [
        #     df_player_stats['pdr_min'] + ' - ' + df_player_stats['pdr_mean'],
        #     df_player_stats['pdr_mean'] + ' - ' + df_player_stats['pdr_max'],
        #     # ((df_player_stats['pdr_min'] + df_player_stats['pdr_mean']) / 2).round(1).astype(str),
        #     # ((df_player_stats['pdr_mean'] + df_player_stats['pdr_max']) / 2).round(1).astype(str),
        #     df_player_stats['pdr_min'],
        #     df_player_stats['pdr_max'],
        #     # df_player_stats['pdr_min'].round(1).astype(str),
        #     # df_player_stats['pdr_max'].round(1).astype(str),
        # ]
        # default = ''
        # df_player_stats['pdr'] = np.select(conditions, choices, default=default)
        # df_player_stats['pdr'] = df_player_stats['pdr_mean']
        df_temp = df_player_stats.query('keeper!="Yes" and pdr_mean>0 and team_abbr!="(N/A)"').sort_values('pdr_mean')
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14).ngroup() + 1
        df_player_stats['pdr'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 14 else 14)

        # if projected draft round is 0, set to ''
        # df_player_stats['pdr'] = np.where(df_player_stats['pdr'] == '0', '', df_player_stats['pdr'])
        # df_player_stats['pdr'] = np.where(df_player_stats['pdr'] == '0.0', '', df_player_stats['pdr'])
        # Connor Bedard will be drafted first
        # df_player_stats['pdr'] = np.where(df_player_stats['pdr'] == '1.0', '1.1', df_player_stats['pdr'])
        # df_player_stats['pdr'] = np.where(df_player_stats.index  == 8484144, '1.0', df_player_stats['pdr'])
        # df_player_stats['pdr'] = np.where(df_player_stats.index  == 8484144, '1.0', df_player_stats['pdr'])

        df_player_stats.reset_index(inplace=True)

def calc_scoring_category_maximums(df: pd.DataFrame):

    # Create a deep copy of df
    df_copy = df.copy(deep=True)

    # # see https://stackoverflow.com/questions/23199796/detect-and-exclude-outliers-in-a-pandas-dataframe
    # # cols = df_copy.select_dtypes('number').columns  # limits to a (float), b (int) and e (timedelta)
    # cols=['score', 'offense', 'peripheral']
    # df_sub = df_copy.loc[:, cols]
    # # OPTION 1: z-score filter: z-score < 3
    # # lim = np.abs((df_sub - df_sub.mean()) / df_sub.std(ddof=0)) < 3

    # # OPTION 2: quantile filter: discard 1% upper / lower values
    # # lim = np.logical_or(df_sub > df_sub.quantile(0.99, numeric_only=False),
    # #                     df_sub < df_sub.quantile(0.01, numeric_only=False))
    # lim = np.logical_or(df_sub > df_sub.quantile(0.99,), df_sub < df_sub.quantile(0.01))

    # # OPTION 3: iqr filter: within 2.22 IQR (equiv. to z-score < 3)
    # # iqr = df_sub.quantile(0.75, numeric_only=False) - df_sub.quantile(0.25, numeric_only=False)
    # # lim = np.abs((df_sub - df_sub.median()) / iqr) < 2.22

    # # replace outliers with nan
    # df_copy.loc[:, cols] = df_sub.where(~lim, np.nan)

    try:

        skaters_mask = df_copy.eval(skaters_filter)
        forwards_mask = df_copy.eval(forwards_filter)
        defense_mask = df_copy.eval(defense_filter)
        goalie_mask = df_copy.eval(goalie_filter)
        # minimum_one_game_mask = df_copy.eval(minimum_one_game_filter)
        minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df_copy.loc[skaters_mask & minimum_skater_games_mask]
        df_f = df_copy.loc[forwards_mask & minimum_skater_games_mask]
        df_d = df_copy.loc[defense_mask & minimum_skater_games_mask]
        df_g = df_copy.loc[goalie_mask & minimum_goalie_starts_mask]

        columns = list(df_copy.columns)
        all_categories = sktr_categories + sktr_z_categories
        columns_series = pd.Series(list(df_copy.columns))

        #######################################
        # Skaters
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                max_cat[f'sktr {cat}'] = df_sktr[cat].max()
            else:
                max_cat[f'sktr {cat}'] = None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                max_cat[f'f {cat}'] = df_f[cat].max()
            else:
                max_cat[f'f {cat}'] = None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                max_cat[f'd {cat}'] = df_d[cat].max()
            else:
                max_cat[f'd {cat}'] = None

        #######################################
        # Goalies
        all_categories = goalie_categories + goalie_z_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                max_cat[cat] = df_g[cat].max()
            else:
                max_cat[cat] = None

        #######################################
        # Summary z-scores
        #######################################
        columns_series_sktr = pd.Series(df_sktr.columns)
        columns_series_f = pd.Series(df_f.columns)
        columns_series_d = pd.Series(df_d.columns)
        columns_series_g = pd.Series(df_g.columns)

        # stats
        #######################################
        # skaters
        for cat in sktr_summary_z_scores:
            if columns_series_sktr.isin([cat]).any():
                max_cat[f'sktr {cat}'] = df_sktr[cat].max()
            else:
                max_cat[f'sktr {cat}'] = None
            if columns_series_f.isin([cat]).any():
                max_cat[f'f {cat}'] = df_f[cat].max()
            else:
                max_cat[f'f {cat}'] = None
            if columns_series_d.isin([cat]).any():
                max_cat[f'd {cat}'] = df_d[cat].max()
            else:
                max_cat[f'd {cat}'] = None

        # goalie
        for cat in g_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                max_cat[f'g {cat}'] = df_g[cat].max()
            else:
                max_cat[f'g {cat}'] = None

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return

def calc_scoring_category_minimums(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        # minimum_one_game_mask = df.eval(minimum_one_game_filter)
        minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df.loc[skaters_mask & minimum_skater_games_mask]
        df_f = df.loc[forwards_mask & minimum_skater_games_mask]
        df_d = df.loc[defense_mask & minimum_skater_games_mask]
        df_g = df.loc[goalie_mask & minimum_goalie_starts_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_categories + sktr_z_categories
        columns_series = pd.Series(columns)

        #######################################
        # Skaters
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[f'sktr {cat}'] = df_sktr[cat].min()
            else:
                min_cat[f'sktr {cat}'] = None

        # also...
        min_cat[f'sktr shots_powerplay'] = df_sktr['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[f'f {cat}'] = df_f[cat].min()
            else:
                min_cat[f'f {cat}'] = None

        # also...
        min_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[f'd {cat}'] = df_d[cat].min()
            else:
                min_cat[f'd {cat}'] = None

        # also...
        min_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_categories + goalie_z_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[cat] = df_g[cat].min()
            else:
                min_cat[cat] = None

        #######################################
        # Summary z-scores
        #######################################
        columns_series_sktr = pd.Series(df_sktr.columns)
        columns_series_f = pd.Series(df_f.columns)
        columns_series_d = pd.Series(df_d.columns)
        columns_series_g = pd.Series(df_g.columns)

        # stats
        # skaters
        for cat in sktr_summary_z_scores:
            if columns_series_sktr.isin([cat]).any():
                min_cat[f'sktr {cat}'] = df_sktr[cat].min()
            else:
                min_cat[f'sktr {cat}'] = None
            if columns_series_f.isin([cat]).any():
                min_cat[f'f {cat}'] = df_f[cat].min()
            else:
                min_cat[f'f {cat}'] = None
            if columns_series_d.isin([cat]).any():
                min_cat[f'd {cat}'] = df_d[cat].min()
            else:
                min_cat[f'd {cat}'] = None

        # goalie
        for cat in g_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                min_cat[f'g {cat}'] = df_g[cat].min()
            else:
                min_cat[f'g {cat}'] = None

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return

def calc_scoring_category_means(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        # minimum_one_game_mask = df.eval(minimum_one_game_filter)
        minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df.loc[skaters_mask & minimum_skater_games_mask]
        df_f = df.loc[forwards_mask & minimum_skater_games_mask]
        df_d = df.loc[defense_mask & minimum_skater_games_mask]
        df_g = df.loc[goalie_mask & minimum_goalie_starts_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_categories
        columns_series = pd.Series(columns)

        #######################################
        # Skaters
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                mean_cat[f'sktr {cat}'] = df_sktr[cat].mean()
            else:
                mean_cat[f'sktr {cat}'] = None

        # also...
        mean_cat[f'sktr shots_powerplay'] = df_sktr['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'sktr penalties'] = df_sktr['penalties'].mean() if 'penalties' in columns else None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                mean_cat[f'f {cat}'] = df_f[cat].mean()
            else:
                mean_cat[f'f {cat}'] = None

        # also...
        mean_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'f penalties'] = df_f['penalties'].mean() if 'penalties' in columns else None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                mean_cat[f'd {cat}'] = df_d[cat].mean()
            else:
                mean_cat[f'd {cat}'] = None

        # also...
        mean_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'd penalties'] = df_d['penalties'].mean() if 'penalties' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                # if cat == 'gaa':
                #     mean_cat[cat] = df_g['goals_against_sum'].sum() / df_g['toi_sec'].sum() * 3600
                # elif cat == 'save%':
                #     mean_cat[cat] = df_g['saves_sum'].sum() / df_g['shots_against_sum'].sum()
                # else:
                #     mean_cat[cat] = df_g[cat].mean()
                mean_cat[cat] = df_g[cat].mean()
            else:
                mean_cat[cat] = None

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return

def calc_scoring_category_scores(df: pd.DataFrame, positional_scoring: bool=False,):

    try:

        skaters_mask = df.eval(skaters_filter)
        forward_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)
        # minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        # minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forward_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        sktr_games = df_sktr['games']
        f_games = df_f['games']
        d_games = df_d['games']
        g_games = df_g['games']

        sktr_max_games = sktr_games.max()
        f_max_games = f_games.max()
        d_max_games = d_games.max()
        g_max_games = g_games.max()

        # Calculate the multipliers
        if statType == 'Cumulative':
            sktr_multipliers = 1
            f_multipliers = 1
            d_multipliers = 1
            g_count_multipliers = 1
            g_ratio_multipliers = custom_decay(g_games, g_max_games)
        # elif statType == 'EWMA':
        #     # ewm_span_sktr & ewm_span_g are global, calculated in calculate_ewm_args()
        #     sktr_multipliers = custom_decay(sktr_games, ewm_span_sktr)
        #     f_multipliers = custom_decay(f_games, ewm_span_sktr)
        #     d_multipliers = custom_decay(d_games, ewm_span_sktr)
        #     g_count_multipliers = custom_decay(g_games, ewm_span_g)
        #     g_ratio_multipliers = g_count_multipliers
        else:
            sktr_multipliers = custom_decay(sktr_games, sktr_max_games)
            f_multipliers = custom_decay(f_games, f_max_games)
            d_multipliers = custom_decay(d_games, d_max_games)
            g_count_multipliers = custom_decay(g_games, g_max_games)
            g_ratio_multipliers = g_count_multipliers

        ##########################################################################
        # skaters
        ##########################################################################
        if positional_scoring is True:
            goals = pd.concat([(df_f['goals'] / df_f['goals'].max()).multiply(f_multipliers, axis=0), (df_d['goals'] / df_d['goals'].max()).multiply(d_multipliers, axis=0)])
            assists = pd.concat([(df_f['assists'] / df_f['assists'].max()).multiply(f_multipliers, axis=0), (df_d['assists'] / df_d['assists'].max()).multiply(d_multipliers, axis=0)])
            pim = pd.concat([(df_f['pim'] / df_f['pim'].max()).multiply(f_multipliers, axis=0), (df_d['pim'] / df_d['pim'].max()).multiply(d_multipliers, axis=0)])
            penalties = pd.concat([(df_f['penalties'] / df_f['penalties'].max()).multiply(f_multipliers, axis=0), (df_d['penalties'] / df_d['penalties'].max()).multiply(d_multipliers, axis=0)])
            shots = pd.concat([(df_f['shots'] / df_f['shots'].max()).multiply(f_multipliers, axis=0), (df_d['shots'] / df_d['shots'].max()).multiply(d_multipliers, axis=0)])
            points_pp = pd.concat([(df_f['points_pp'] / df_f['points_pp'].max()).multiply(f_multipliers, axis=0), (df_d['points_pp'] / df_d['points_pp'].max()).multiply(d_multipliers, axis=0)])
            hits = pd.concat([(df_f['hits'] / df_f['hits'].max()).multiply(f_multipliers, axis=0), (df_d['hits'] / df_d['hits'].max()).multiply(d_multipliers, axis=0)])
            blocked = pd.concat([(df_f['blocked'] / df_f['blocked'].max()).multiply(f_multipliers, axis=0), (df_d['blocked'] / df_d['blocked'].max()).multiply(d_multipliers, axis=0)])
            takeaways = pd.concat([(df_f['takeaways'] / df_f['takeaways'].max()).multiply(f_multipliers, axis=0), (df_d['takeaways'] / df_d['takeaways'].max()).multiply(d_multipliers, axis=0)])

        else:
            goals = (df_sktr['goals'] / df_sktr['goals'].max()).multiply(sktr_multipliers, axis=0)
            assists = (df_sktr['assists'] / df_sktr['assists'].max()).multiply(sktr_multipliers, axis=0)
            pim = (df_sktr['pim'] / df_sktr['pim'].max()).multiply(sktr_multipliers, axis=0)
            penalties = (df_sktr['penalties'] / df_sktr['penalties'].max()).multiply(sktr_multipliers, axis=0)
            shots = (df_sktr['shots'] / df_sktr['shots'].max()).multiply(sktr_multipliers, axis=0)
            points_pp = (df_sktr['points_pp'] / df_sktr['points_pp'].max()).multiply(sktr_multipliers, axis=0)
            hits = (df_sktr['hits'] / df_sktr['hits'].max()).multiply(sktr_multipliers, axis=0)
            blocked = (df_sktr['blocked'] / df_sktr['blocked'].max()).multiply(sktr_multipliers, axis=0)
            takeaways = (df_sktr['takeaways'] / df_sktr['takeaways'].max()).multiply(sktr_multipliers, axis=0)

        ##########################################################################
        # defense
        ##########################################################################
        points = (df_d['points'] / df_d['points'].max()).multiply(d_multipliers, axis=0)

        ##########################################################################
        # goalies
        ##########################################################################
        wins = (df_g['wins'] / df_g['wins'].max()).multiply(g_count_multipliers, axis=0)
        saves = (df_g['saves'] / df_g['saves'].max()).multiply(g_count_multipliers, axis=0)
        gaa_delta_from_max = (df_g['gaa'].max() - df_g['gaa'])
        max_gaa_delta_from_max = gaa_delta_from_max.max()
        gaa = (gaa_delta_from_max / max_gaa_delta_from_max).multiply(g_ratio_multipliers, axis=0)
        # gaa = (-1 * (df_g['gaa'] - mean_cat['gaa']) / std_cat['gaa']).multiply(g_ratio_multipliers, axis=0)
        save_pct = (df_g['save%'] / df_g['save%'].max()).multiply(g_ratio_multipliers, axis=0)

        df = df.assign(
            d_points_score = round(points * 100, 0),
            goals_score = round(goals * 100, 0),
            assists_score = round(assists * 100, 0),
            pim_score = round(pim * 100, 0),
            penalties_score = round(penalties * 100, 0),
            shots_score = round(shots * 100, 0),
            points_pp_score = round(points_pp * 100, 0),
            hits_score = round(hits * 100, 0),
            blocked_score = round(blocked * 100, 0),
            takeaways_score = round(takeaways * 100, 0),
            wins_score = round(wins * 100, 0),
            saves_score = round(saves * 100, 0),
            gaa_score = round(gaa * 100, 0),
            save_pct_score = round(save_pct * 100, 0),
        )

        df['save%_score'] = df['save_pct_score']
        df.drop('save_pct_score', axis=1, inplace=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return df

def calc_scoring_category_std_deviations(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        # minimum_one_game_mask = df.eval(minimum_one_game_filter)
        minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
        minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

        df_sktr = df.loc[skaters_mask & minimum_skater_games_mask]
        df_f = df.loc[forwards_mask & minimum_skater_games_mask]
        df_d = df.loc[defense_mask & minimum_skater_games_mask]
        df_g = df.loc[goalie_mask & minimum_goalie_starts_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_categories
        columns_series = pd.Series(columns)

        #######################################
        # Skaters
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[f'sktr {cat}'] = df_sktr[cat].std()
            else:
                std_cat[f'sktr {cat}'] = None

        # also...
        std_cat[f'sktr penalties'] = df_sktr['penalties'].std() if 'penalties' in columns else None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[f'f {cat}'] = df_f[cat].std()
            else:
                std_cat[f'f {cat}'] = None

        # also...
        std_cat[f'f penalties'] = df_f['penalties'].std() if 'penalties' in columns else None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[f'd {cat}'] = df_d[cat].std()
            else:
                std_cat[f'd {cat}'] = None

        # also...
        std_cat[f'd penalties'] = df_d['penalties'].std() if 'penalties' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[cat] = df_g[cat].std()
            else:
                std_cat[cat] = None

        # also need goals_against, used when calculating gaa z-scores
        # std_cat['goals_against'] = df_g['goals_against_sum'].std()
        std_cat['goals_against'] = df_g['goals_against'].std()

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return

def calc_player_ages(df: pd.DataFrame) -> pd.Series:

    # calculate player's current age
    # if there are no stats, the following has problem. So do't do it if there are now rows in df_player_stats
    if len(df.index) == 0:
        ages = np.nan
    else:
        ages = df['birth_date'].where(df['birth_date'].notna() & (df['birth_date'] != ''), '').apply(calculate_age)

    return ages

def calc_player_breakout_threshold(df: pd.DataFrame) -> pd.Series:

    if len(df.index) == 0:
        breakout_thresholds = np.nan
    else:
        # Remove rows with missing values in the specified columns
        mask = (df['height'].notna() & (df['height'] != '')) & (df['weight'].notna() & (df['weight'] != '')) & (df['career_games'].notna() & (df['career_games'] != '')) & (df['pos'].notna() & (df['pos'] != ''))
        df = df[mask]
        breakout_thresholds = df.apply(lambda x: np.nan if x['pos'] == 'G' else calc_breakout_threshold(name=x['name'], height=x['height'], weight=x['weight'], career_games=x['career_games']), axis='columns')

    return breakout_thresholds

def calc_player_projected_stats(current_season_stats: bool, season_id: str, projection_source: str):

    try:

        ##########################################################################
        # need to get basic player info, without statistics
        sql = textwrap.dedent('''\
            select *
            from TeamRosters tr
                 left outer join PlayerStats ps on ps.player_id = tr.player_id and ps.seasonID == ?
            where tr.seasonID == ?
        ''')
        params = (season_id, season_id)
        df = pd.read_sql_query(sql=sql, params=params, con=get_db_connection())
        # Drop the duplicate columns from the resulting DataFrame, keeping only the first occurrence
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        ##########################################################################

        # Check if all values in the team_id column are None or empty
        if df['team_id'].isnull().all():
            # Connect to the SQLite database
            conn = get_db_connection()
            c = conn.cursor()
            # Execute a query to retrieve the id and team_abbr columns from the Team table
            c.execute('SELECT id as team_id, abbr as team_abbr FROM Team')
            result = c.fetchall()
            # Close the database connection
            conn.close()

            # Convert the result to a DataFrame
            result_df = pd.DataFrame(result, columns=['team_id', 'team_abbr'])

            # Update the team_id column in the df DataFrame with the values from the result_df DataFrame
            df['team_id'] = df['team_abbr'].map(result_df.set_index('team_abbr')['team_id'])

        # Get prior year & 3 years prior, if needed
        from_year = int(season_id[:-4])
        to_year = int(season_id[-4:])
        prior_year = datetime(year=from_year - 1, month=1, day=1)
        three_years_prior = datetime(year=from_year - 3, month=1, day=1)
        prior_year_str = f"{prior_year.year}{prior_year.year + 1}"
        three_years_prior_str = f"{three_years_prior.year}{three_years_prior.year + 1}"

        # some stats are not projected
        sql = textwrap.dedent(f'''\
            select CAST(SUM(points_pp) AS FLOAT) / CAST(SUM(games) AS FLOAT) AS ppp_pg,
                   CAST(SUM(saves) AS FLOAT) / CAST(SUM(games) AS FLOAT) AS saves_pg,
                   CAST(SUM(saves) AS FLOAT) / CAST(SUM(shots_against) AS FLOAT) AS save_percent,
                   CAST(SUM(takeaways) AS FLOAT) / CAST(SUM(games) AS FLOAT) AS tk_pg,
                   player_id
            from PlayerStats
            where seasonID >= {three_years_prior_str} and seasonID <= {prior_year_str} and games > 10
            group by player_id
        ''')
        df_temp = pd.read_sql(sql=sql, con=get_db_connection())
        df_temp.set_index('player_id', inplace=True)

        ##########################################################################
        # skaters
        ##########################################################################

        # must set index here & remove at end of function; otherwise projections won't calculate
        df.set_index('player_id', inplace=True)

        # get The Athletic's projections
        sktr_prj_athletic = pd.read_sql('select * from AthleticSkatersDraftList where Games>0', con=get_db_connection(), index_col='player_id')
        goalie_prj_athletic = pd.read_sql('select * from AthleticGoaliesDraftList where Games>0', con=get_db_connection(), index_col='player_id')
        # get Dobber's projections
        sktr_prj_dobber = pd.read_sql('select * from DobberSkatersDraftList where Games>0', con=get_db_connection(), index_col='player_id')
        goalie_prj_dobber = pd.read_sql('select * from DobberGoaliesDraftList where Games>0', con=get_db_connection(), index_col='player_id')
        # get Fantrax projections
        sktr_prj_fantrax = pd.read_sql('select * from FantraxSkatersDraftList where Games>0', con=get_db_connection(), index_col='player_id')
        goalie_prj_fantrax = pd.read_sql('select * from FantraxGoaliesDraftList where Games>0', con=get_db_connection(), index_col='player_id')

        if projection_source in ('Athletic', 'Averaged'):
            sktr_prj_all = sktr_prj_athletic
            goalie_prj_all = goalie_prj_athletic

            sktr_prj = sktr_prj_athletic
            goalie_prj = goalie_prj_athletic

        if projection_source in ('Dobber', 'Averaged'):
            #  projected powerplay points
            sktr_prj_dobber = pd.merge(sktr_prj_dobber, df_temp[['ppp_pg']], how='left', on=['player_id'])
            sktr_prj_dobber['PPP'] = sktr_prj_dobber["ppp_pg"].fillna(0).mul(sktr_prj_dobber["Games"].fillna(0))

            # Alex Vlasic has two rows
            sktr_prj_dobber = sktr_prj_dobber.reset_index().drop_duplicates(subset='player_id', keep='first').set_index('player_id')

            # goalie saves & save %
            goalie_prj_dobber = pd.merge(goalie_prj_dobber, df_temp[['saves_pg', 'save_percent']], how='left', on=['player_id'])
            goalie_prj_dobber['Saves'] = goalie_prj_dobber["saves_pg"].fillna(0).mul(goalie_prj_dobber["Games"].fillna(0))
            goalie_prj_dobber['Save%'] = goalie_prj_dobber["save_percent"].fillna(0)

            sktr_prj_all = sktr_prj_dobber
            goalie_prj_all = goalie_prj_dobber

            sktr_prj = sktr_prj_dobber
            goalie_prj = goalie_prj_dobber

        if projection_source in ('Fantrax', 'Averaged'):
            sktr_prj_all = sktr_prj_fantrax
            goalie_prj_all = goalie_prj_fantrax

            sktr_prj = sktr_prj_fantrax
            goalie_prj = goalie_prj_fantrax

        if projection_source == 'Averaged':
            # get means
            dataframes = [sktr_prj_athletic, sktr_prj_dobber]
            sktr_prj_all = pd.concat([df for df in dataframes if not df.empty])

            dataframes = [goalie_prj_athletic, goalie_prj_dobber]
            goalie_prj_all = pd.concat([df for df in dataframes if not df.empty])

            sktr_prj = sktr_prj_all.groupby(level=0).mean(numeric_only=True)
            goalie_prj = goalie_prj_all.groupby(level=0).mean(numeric_only=True)

        # skaters may not be in df
        missing_indexes = sktr_prj[~sktr_prj.index.isin(df.index)].index
        df_missing_skaters = pd.DataFrame(columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
        if len(missing_indexes) > 0:
            for player_id in missing_indexes:
                player = sktr_prj_all.loc[player_id]
                df_player = pd.DataFrame(data=[[season_id, player_id, player["Player"], player["Pos"], player["Team"]]], columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
                df_missing_skaters = pd.concat([df_missing_skaters, df_player])

        # goalies may not be in df
        missing_indexes = goalie_prj[~goalie_prj.index.isin(df.index)].index
        df_missing_goalies = pd.DataFrame(columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
        if len(missing_indexes) > 0:
            for player_id in missing_indexes:
                player = goalie_prj_all.loc[player_id]
                df_player = pd.DataFrame(data=[[season_id, player_id, player["Player"], player["Pos"], player["Team"]]], columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
                df_missing_goalies = pd.concat([df_missing_goalies, df_player])

        df_missing_skaters.set_index('player_id', inplace=True)
        df_missing_goalies.set_index('player_id', inplace=True)
        if len(df_missing_skaters) > 0 or len(df_missing_goalies) > 0:
            df = pd.concat([df, df_missing_skaters, df_missing_goalies])

        df = df.assign(
            games = sktr_prj['Games'].add(goalie_prj['Games'], fill_value=0),
            toi_sec = sktr_prj['Games'].add(goalie_prj['Games'], fill_value=0) * 3600,
            goals = sktr_prj['Goals'],
            assists = sktr_prj['Assists'],
            points = lambda x: x['goals'] + x['assists'],
            pim = sktr_prj['PIM'],
            penalties = np.nan,
            shots = sktr_prj['SOG'],
            shots_powerplay = 0,
            points_pp = sktr_prj['PPP'],
            hits = sktr_prj['Hits'],
            blocked = sktr_prj['BLKS'],
            takeaways = df_temp['tk_pg'].mul(sktr_prj['Games']),
            wins = goalie_prj['Wins'],
            saves = goalie_prj['Saves'],
            gaa = goalie_prj['GAA'],
            save_percent = goalie_prj['Save%'],
            shots_against = lambda x: np.where(x['save_percent'] == 0, 0, x['saves'].div(x['save_percent'])),
            goals_against = lambda x: x['gaa'].mul(x['games']),
            team_games = 82,
            percent_of_team_games = lambda x: x['games'].fillna(0).div(x['team_games']).multiply(100).round(1)
        )

        # Replace the values in the 'save%' column with the values in the 'save_percent' column
        df['save%'] = df['save_percent']
        # Discard the 'save_percent' column
        df.drop('save_percent', axis=1, inplace=True)

        #  sktr_prj_dobber has non unique indexes, so drop them keeping only the first
        sktr_prj_dobber = sktr_prj_dobber.loc[~sktr_prj_dobber.index.duplicated(keep='first')]
        df = df.assign(
            sleeper = sktr_prj_dobber['Sleeper'],
            upside = sktr_prj_dobber['Upside'],
            yp3 = sktr_prj_dobber['3YP'],
            bandaid_boy = sktr_prj_dobber['Band-Aid Boy'].combine_first(goalie_prj_dobber['Band-Aid Boy']),
            pp_unit_prj = sktr_prj_dobber['PP Unit'],
            tier = goalie_prj_dobber['Notes'],
        )
        # Rename the 'yp3' column to '3yp'
        df = df.rename(columns={'yp3': '3yp'})

        sktr_prj_fantrax['ADP'] = sktr_prj_fantrax['ADP'].str.replace('-', '0').astype(float)
        goalie_prj_fantrax['ADP'] = goalie_prj_fantrax['ADP'].str.replace('-', '0').astype(float)
        df = df.assign(
            fantrax_score = sktr_prj_fantrax['Score'].add(goalie_prj_fantrax['Score'], fill_value=0),
            adp = sktr_prj_fantrax['ADP'].combine_first(goalie_prj_fantrax['ADP']),
            team_abbr = sktr_prj_fantrax['Team'].combine_first(goalie_prj_fantrax['Team'])
        )

        df.reset_index(inplace=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return df

def calc_summary_scores(df: pd.DataFrame, positional_scoring: bool=False, categories_to_exclude: List=[]) -> pd.DataFrame:

    sktr_summary_score_types = ['score', 'offense', 'peripheral']
    g_summary_score_types = ['score', 'g_count', 'g_ratio']
    summary_score_types = sktr_summary_score_types + g_summary_score_types
    # use a set to remove duplicates and convert it back to a list while preserving order
    summary_score_types = list(dict.fromkeys(sktr_summary_score_types + g_summary_score_types))

    # z cats
    sktr_offense_z_cats = [cat for cat in ['z_goals', 'z_assists', 'z_shots', 'z_points_pp'] if cat not in categories_to_exclude]
    sktr_periph_z_cats = [cat for cat in ['z_hits', 'z_blocked', 'z_pim', 'z_takeaways'] if cat not in categories_to_exclude]
    sktr_z_cats = sktr_offense_z_cats + sktr_periph_z_cats

    f_offense_z_cats = sktr_offense_z_cats
    f_periph_z_cats = sktr_periph_z_cats
    f_z_cats = f_offense_z_cats + f_periph_z_cats

    d_only_z_cats = [cat for cat in ['z_points'] if cat not in categories_to_exclude]
    d_offense_z_cats = d_only_z_cats + sktr_offense_z_cats
    d_periph_z_cats = sktr_periph_z_cats
    d_z_cats = d_offense_z_cats + d_periph_z_cats

    g_count_z_cats = [cat for cat in ['z_wins', 'z_saves'] if cat not in categories_to_exclude]
    g_ratio_z_cats = [cat for cat in ['z_gaa', 'z_save%'] if cat not in categories_to_exclude]
    g_z_cats = g_count_z_cats + g_ratio_z_cats

    # score cats
    sktr_offense_score_cats = [cat.replace('z_', '') + '_score' for cat in sktr_offense_z_cats]
    sktr_periph_score_cats = [cat.replace('z_', '') + '_score' for cat in sktr_periph_z_cats]
    sktr_score_cats = sktr_offense_score_cats + sktr_periph_score_cats

    f_offense_score_cats = sktr_offense_score_cats
    f_periph_score_cats = sktr_periph_score_cats
    f_score_cats = f_offense_score_cats + f_periph_score_cats

    d_only_score_cats = [cat.replace('z_', 'd_') + '_score' if cat == 'z_points' else cat.replace('z_', '') + '_score' for cat in d_only_z_cats]
    d_offense_score_cats = d_only_score_cats + sktr_offense_score_cats
    d_periph_score_cats = sktr_periph_score_cats
    d_score_cats = d_offense_score_cats + d_periph_score_cats

    g_count_score_cats = [cat.replace('z_', '') + '_score' for cat in g_count_z_cats]
    g_ratio_score_cats = [cat.replace('z_', '') + '_score' for cat in g_ratio_z_cats]
    g_score_cats = g_count_score_cats + g_ratio_score_cats

    mask_sktr = df.eval(f"{skaters_filter} and {minimum_one_game_filter}")
    mask_f = df.eval(f"{forwards_filter} and {minimum_one_game_filter}")
    mask_d = df.eval(f"{defense_filter} and {minimum_one_game_filter}")
    mask_g = df.eval(f"{goalie_filter} and {minimum_one_game_filter}")

    df_sktr = df.loc[mask_sktr,:]
    df_f = df.loc[mask_f,:]
    df_d = df.loc[mask_d,:]
    df_g = df.loc[mask_g,:]

    # Adjust scores to remove negative values
    sktr_cat_z_scores = df_sktr[sktr_z_cats]
    # sktr_cat_scores_min = sktr_cat_z_scores.min()
    # sktr_cat_scores = sktr_cat_z_scores + abs(sktr_cat_scores_min)
    sktr_cat_scores = df_sktr[sktr_score_cats]

    f_cat_z_scores = df_f[f_z_cats]
    # f_cat_scores_min = f_cat_z_scores.min()
    # f_cat_scores = f_cat_z_scores + abs(f_cat_scores_min)
    f_cat_scores = df_f[f_score_cats]

    d_only_cat_z_scores = df_d[d_only_z_cats]
    # d_only_cat_scores_min = d_only_cat_z_scores.min()
    # d_only_cat_scores = d_only_cat_z_scores + abs(d_only_cat_scores_min)
    d_only_cat_scores = df_d[d_only_score_cats]

    d_cat_z_scores = df_d[d_z_cats]
    # d_cat_scores_min = d_cat_z_scores.min()
    # d_cat_scores = d_cat_z_scores + abs(d_cat_scores_min)
    d_cat_scores = df_d[d_score_cats]

    g_count_cat_z_scores = df_g[g_count_z_cats]
    # g_count_cat_scores_min = g_count_cat_z_scores.min()
    # g_count_cat_scores = g_count_cat_z_scores + abs(g_count_cat_scores_min)
    g_count_cat_scores = df_g[g_count_score_cats]

    g_ratio_cat_z_scores = df_g[g_ratio_z_cats]
    # g_ratio_cat_scores_min = g_ratio_cat_z_scores.min()
    # g_ratio_cat_scores = g_ratio_cat_z_scores + abs(g_ratio_cat_scores_min)
    g_ratio_cat_scores = df_g[g_ratio_score_cats]

    # Overall scores
    global scores
    scores = {}
    scores['player_id'] = df['player_id']
    for score_type in summary_score_types:
        if score_type == 'peripheral':
            d_only_z_cats = []
            sktr_z_cats = sktr_periph_z_cats
            f_z_cats = f_periph_z_cats
            d_z_cats = d_periph_z_cats
            d_only_score_cats = []
            sktr_score_cats = sktr_periph_score_cats
            f_score_cats = f_periph_score_cats
            d_score_cats = d_periph_score_cats
        elif score_type == 'offense':
            sktr_z_cats = sktr_offense_z_cats
            f_z_cats = f_offense_z_cats
            d_z_cats = d_offense_z_cats
            sktr_score_cats = sktr_offense_score_cats
            f_score_cats = f_offense_score_cats
            d_score_cats = d_offense_score_cats
        elif score_type == 'g_count':
            g_z_cats = g_count_z_cats
            g_score_cats = g_count_score_cats
        elif score_type == 'g_ratio':
            g_z_cats = g_ratio_z_cats
            g_score_cats = g_ratio_score_cats

        if score_type in sktr_summary_score_types:
            sktr_scores_sum = pd.concat([d_only_cat_scores[d_only_score_cats], sktr_cat_scores[sktr_score_cats]], axis=1).sum(axis=1)
            # sktr_scores = round(normalize_scores(sktr_scores_sum, new_min=3), 2)
            sktr_scores = normalize_scores(sktr_scores_sum)
            sktr_z_scores = pd.concat([d_only_cat_z_scores[d_only_cat_z_scores > 0][d_only_z_cats], sktr_cat_z_scores[sktr_cat_z_scores > 0][sktr_z_cats]], axis=1).sum(axis=1)

            f_scores_sum = f_cat_scores[f_score_cats].sum(axis=1)
            # f_scores = round(normalize_scores(f_scores_sum, new_min=3), 2)
            f_scores = normalize_scores(f_scores_sum)
            f_z_scores = f_cat_z_scores[f_cat_z_scores > 0][f_z_cats].sum(axis=1)

            d_scores_sum = d_cat_scores[d_score_cats].sum(axis=1)
            # d_scores = round(normalize_scores(d_scores_sum, new_min=3), 2)
            d_scores = normalize_scores(d_scores_sum)
            d_z_scores = d_cat_z_scores[d_cat_z_scores > 0][d_z_cats].sum(axis=1)

        if score_type in g_summary_score_types:
            g_count_scores_sum = g_count_cat_scores[g_count_score_cats].sum(axis=1)
            g_count_z_scores = g_count_cat_z_scores[g_count_cat_z_scores > 0][g_count_z_cats].sum(axis=1)

            g_ratio_scores_sum = g_ratio_cat_scores[g_ratio_score_cats].sum(axis=1)
            g_ratio_z_scores = g_ratio_cat_z_scores[g_ratio_z_cats].sum(axis=1)

            if score_type == 'score':
                # g_scores = round(normalize_scores(g_count_scores_sum + g_ratio_scores_sum, new_min=25), 2)
                g_scores = normalize_scores(g_count_scores_sum + g_ratio_scores_sum)
                g_z_scores = g_count_z_scores + g_ratio_z_scores
            elif score_type == 'g_count':
                # g_scores = round(normalize_scores(g_count_scores_sum, new_min=25), 2)
                g_scores = normalize_scores(g_count_scores_sum)
                g_z_scores = g_count_z_scores
            elif score_type == 'g_ratio':
                # g_scores = round(normalize_scores(g_ratio_scores_sum, new_min=25), 2)
                g_scores = normalize_scores(g_ratio_scores_sum)
                g_z_scores = g_ratio_z_scores

        if score_type in sktr_summary_score_types:
            if score_type != 'score':
                if positional_scoring is True:
                    scores[score_type] = pd.concat([f_scores, d_scores])
                    scores[f'z_{score_type}'] = pd.concat([f_z_scores, d_z_scores])
                else:
                    scores[score_type] = sktr_scores
                    scores[f'z_{score_type}'] = sktr_z_scores

        if score_type in g_summary_score_types:
            if score_type != 'score':
                scores[score_type] = g_scores
                scores[f'z_{score_type}'] = g_z_scores

        if score_type == 'score':
            if positional_scoring is True:
                scores[score_type] = pd.concat([f_scores, d_scores, g_scores])
                scores[f'z_{score_type}'] = pd.concat([f_z_scores, d_z_scores, g_z_scores])
            else:
                # scores[score_type] = pd.concat([sktr_scores, g_scores])
                # scores[f'z_{score_type}'] = pd.concat([sktr_z_scores, g_z_scores])
                all_pos_scores_sum = pd.concat([d_only_cat_scores[d_only_score_cats], sktr_cat_scores[sktr_score_cats], g_count_scores_sum + g_ratio_scores_sum], axis=1).sum(axis=1)
                all_pos_scores = normalize_scores(all_pos_scores_sum)
                all_pos_z_scores = pd.concat([d_only_cat_z_scores[d_only_cat_z_scores > 0][d_only_z_cats], sktr_cat_z_scores[sktr_cat_z_scores > 0][sktr_z_cats], g_count_z_scores + g_ratio_z_scores], axis=1).sum(axis=1)
                scores[score_type] = all_pos_scores
                scores[f'z_{score_type}'] = all_pos_z_scores


        if score_type == 'score':
            prefix = ''
        elif score_type in sktr_summary_score_types:
            prefix = 'sktr '
        elif score_type in g_summary_score_types:
            prefix = 'g '

        min_cat[f'{prefix}{score_type}'] = scores[score_type].min()
        min_cat[f'{prefix}z_{score_type}'] = scores[f'z_{score_type}'].min()

        max_cat[f'{prefix}{score_type}'] = scores[score_type].max()
        max_cat[f'{prefix}z_{score_type}'] = scores[f'z_{score_type}'].max()

        mean_cat[f'{prefix}{score_type}'] = scores[score_type].mean()
        mean_cat[f'{prefix}z_{score_type}'] = scores[f'z_{score_type}'].mean()

    df = df.assign(
        score = scores['score'],
        offense = scores['offense'],
        peripheral = scores['peripheral'],
        g_count = scores['g_count'],
        g_ratio = scores['g_ratio'],
        z_score = scores['z_score'],
        z_offense = scores['z_offense'],
        z_peripheral = scores['z_peripheral'],
        z_count = scores['z_g_count'],
        z_ratio = scores['z_g_ratio'],
    )

    z_combos = calc_z_combo(df=df, score_types=['score', 'offense', 'peripheral', 'g_count', 'g_ratio'], categories_to_exclude=categories_to_exclude)

    df = df.assign(
        z_combo = z_combos['score'],
        z_offense_combo = z_combos['offense'],
        z_peripheral_combo = z_combos['peripheral'],
        z_g_count_combo = z_combos['g_count'],
        z_g_ratio_combo = z_combos['g_ratio'],
    )

    return df

def calc_z_combo(df: pd.DataFrame, score_types: List[str]=['score'], categories_to_exclude: List=[]) -> pd.Series:

    # overall rank, based on Fantrax categories
    g_categories_count = [cat for cat in ['z_wins', 'z_saves'] if cat not in categories_to_exclude]
    g_categories_ratio = [cat for cat in ['z_gaa', 'z_save%'] if cat not in categories_to_exclude]

    f_offense_categories = [cat for cat in ['z_goals', 'z_assists', 'z_shots', 'z_points_pp'] if cat not in categories_to_exclude]
    d_offense_categories = [cat for cat in ['z_points'] + f_offense_categories if cat not in categories_to_exclude]
    sktr_peripheral_categories = [cat for cat in ['z_hits', 'z_blocked', 'z_pim', 'z_takeaways'] if cat not in categories_to_exclude]

    f_categories = f_offense_categories + sktr_peripheral_categories
    d_categories = d_offense_categories + sktr_peripheral_categories
    g_categories = g_categories_count + g_categories_ratio

    # create views for player positions
    forwards_mask = df.eval(forwards_filter)
    defense_mask = df.eval(defense_filter)
    goalie_mask = df.eval(goalie_filter)
    minimum_one_game_mask = df.eval(minimum_one_game_filter)
    # minimum_skater_games_mask = df.eval(minimum_skater_games_filter)
    # minimum_goalie_starts_mask = df.eval(minimum_goalie_starts_filter)

    df_f = df.loc[forwards_mask & minimum_one_game_mask]
    df_d = df.loc[defense_mask & minimum_one_game_mask]
    df_g = df.loc[goalie_mask & minimum_one_game_mask]

    z_combos = {}
    z_combos['player_id'] = df['player_id']
    for score_type in score_types:

        if score_type == 'peripheral':
            d_categories = sktr_peripheral_categories
            f_categories = sktr_peripheral_categories
        elif score_type == 'offense':
            d_categories = d_offense_categories
            f_categories = f_offense_categories

        # construct z-score categories as string for use in eval()
        d_categories_as_eval_str = ''.join(['[', ', '.join([f"'{c}'" for c in d_categories]), ']'])
        f_categories_as_eval_str = ''.join(['[', ', '.join([f"'{c}'" for c in f_categories]), ']'])
        g_categories_count_as_eval_str = ''.join(['[', ', '.join([f"'{c}'" for c in g_categories_count]), ']'])
        g_categories_ratio_as_eval_str = ''.join(['[', ', '.join([f"'{c}'" for c in g_categories_ratio]), ']'])
        g_categories_as_eval_str = ''.join(['[', ', '.join([f"'{c}'" for c in g_categories]), ']'])

        if score_type not in ( 'g_count', 'g_ratio'):
            # update combos for forwards
            z_combos[score_type] = format_z_combo(df_f[eval(f_categories_as_eval_str)])

            # update combos for defense
            z_combos[score_type] = pd.concat([z_combos[score_type], format_z_combo(df_d[eval(d_categories_as_eval_str)])])

        # update combos for goalies
        if score_type == 'g_ratio':
            z_combos[score_type] = format_z_combo(df_g[eval(g_categories_ratio_as_eval_str)])
        elif score_type == 'g_count':
            z_combos[score_type] = format_z_combo(df_g[eval(g_categories_count_as_eval_str)])
        elif score_type == 'score':
            z_combos[score_type] = pd.concat([z_combos[score_type], format_z_combo(df_g[eval(g_categories_as_eval_str)])])

    return pd.Series(z_combos)

# def custom_decay(n_games, max_games, a=1):
#     return (n_games / max_games) ** a
def custom_decay(n_games, max_games, k=20, midpoint=0.1):
    # The logistic function for S-curve
    return 1 / (1 + np.exp(-k * ((n_games / max_games) - midpoint)))

def ewma(df):
    def wrapper(x):
        position = df.loc[x.index, 'pos'].iloc[0]
        games = df.loc[x.index, 'player_id'].count()

        if position == 'G':
            ewm_span = ewm_span_g
        else:
            ewm_span = ewm_span_sktr

        execute_ewm = True
        goalie_stats = ('goals_against', 'saves', 'shots_against', 'shutouts', 'toi_sec', 'wins_ot', 'wins_so', 'wins', 'xGoalsAgainst')
        if position == 'G':
            if x.name not in goalie_stats:
                execute_ewm = False
        else: # Skaters
            if x.name in goalie_stats:
                execute_ewm = False
        if execute_ewm is True:
            # x_agg = x.ewm(span=min(ewm_span, games)).mean()
            x_agg = x.ewm(span=ewm_span).mean()
            return x_agg.iloc[-1] # return last value in series
        else:
            return np.nan
    return wrapper

def format_z_combo(df: pd.DataFrame) -> pd.Series:

    z_combo = pd.DataFrame(index=df.index, columns=['Elite', 'Excellent', 'Great', 'Above Average', 'Average +', 'Average -', 'Below Average', 'Bad', 'Horrible'], data=0)
    z_combo['Elite'] = (df >= 3.00).sum(axis=1)
    z_combo['Excellent'] = ((df >= 2.00) & (df < 3.00)).sum(axis=1)
    z_combo['Great'] = ((df >= 1.00) & (df < 2.00)).sum(axis=1)
    z_combo['Above Average'] = ((df >= 0.50) & (df < 1.00)).sum(axis=1)
    z_combo['Average +'] = ((df > 0.00) & (df < 0.50)).sum(axis=1)
    z_combo['Average -'] = ((df >= -0.50) & (df <= 0.00)).sum(axis=1)
    z_combo['Below Average'] = ((df >= -1.00) & (df < -0.50)).sum(axis=1)
    z_combo['Bad'] = ((df >= -2.00) & (df < -1.00)).sum(axis=1)
    z_combo['Horrible'] = (df < -2.00).sum(axis=1)

    count_of_superior_cats = z_combo[['Elite', 'Excellent', 'Great', 'Above Average']].sum(axis=1)

    z_combos = count_of_superior_cats.astype(str) + '.' + z_combo['Elite'].astype(str) + z_combo['Excellent'].astype(str) + z_combo['Great'].astype(str) + z_combo['Above Average'].astype(str) + '.' + z_combo['Average +'].astype(str) + z_combo['Average -'].astype(str) + '.' + z_combo['Below Average'].astype(str) + z_combo['Bad'].astype(str) + z_combo['Horrible'].astype(str)

    return z_combos

def get_game_stats(season_or_date_radios: str, from_season_id: str, to_season_id: str, from_date: str, to_date: str, pool_id: str, game_type: str='R', ewma_span: int=10) -> pd.DataFrame:

    try:

        if season_or_date_radios == 'date':
            sql = textwrap.dedent(f'''\
                select pgs.*, mpss.xGoals, mpss.highDangerShots, mpss.highDangerShotsOnGoal, mpss.lowDangerShots, mpss.lowDangerShotsOnGoal, mpss.mediumDangerShots, mpss.mediumDangerShotsOnGoal, mpgs.xGoalsAgainst
                from PlayerGameStats pgs
                     left outer join MoneypuckSkaterStats mpss on mpss.game_id=pgs.gamePk and mpss.player_id=pgs.player_id
                     left outer join MoneypuckGoalieStats mpgs on mpgs.game_id=pgs.gamePk and mpgs.player_id=pgs.player_id
                where pgs.date between '{from_date}' and '{to_date}' and pgs.game_type == '{game_type}'
            ''')
        else: #  season_or_date_radios == 'season'
            if from_season_id != to_season_id:
                sql = textwrap.dedent(f'''\
                    select pgs.*, mpss.xGoals, mpss.highDangerShots, mpss.highDangerShotsOnGoal, mpss.lowDangerShots, mpss.lowDangerShotsOnGoal, mpss.mediumDangerShots, mpss.mediumDangerShotsOnGoal, mpgs.xGoalsAgainst
                    from PlayerGameStats pgs
                         left outer join MoneypuckSkaterStats mpss on mpss.game_id=pgs.gamePk and mpss.player_id=pgs.player_id
                         left outer join MoneypuckGoalieStats mpgs on mpgs.game_id=pgs.gamePk and mpgs.player_id=pgs.player_id
                    where pgs.seasonID between {from_season_id} and {to_season_id} and pgs.game_type == '{game_type}'
                ''')
            else:
                sql = textwrap.dedent(f'''\
                    select pgs.*, mpss.xGoals, mpss.highDangerShots, mpss.highDangerShotsOnGoal, mpss.lowDangerShots, mpss.lowDangerShotsOnGoal, mpss.mediumDangerShots, mpss.mediumDangerShotsOnGoal, mpgs.xGoalsAgainst
                    from PlayerGameStats pgs
                         left outer join MoneypuckSkaterStats mpss on mpss.game_id=pgs.gamePk and mpss.player_id=pgs.player_id
                         left outer join MoneypuckGoalieStats mpgs on mpgs.game_id=pgs.gamePk and mpgs.player_id=pgs.player_id
                    where pgs.seasonID == {from_season_id} and pgs.game_type == '{game_type}'
                ''')

        df_game_stats = pd.read_sql(sql=sql, con=get_db_connection())

        # add toi_sec, toi_even_sec, toi_pp_sec, & toi_sh_sec, for aggregation or sorting
        toi_sec = np.where(df_game_stats['toi'].isin([None, '']), 0, df_game_stats['toi'].apply(string_to_time))
        toi_even_sec = np.where(df_game_stats['toi_even'].isin([None, '']), 0, df_game_stats['toi_even'].apply(string_to_time))
        toi_pp_sec = np.where(df_game_stats['toi_pp'].isin([None, '']), 0, df_game_stats['toi_pp'].apply(string_to_time))
        team_toi_pp_sec = np.where(df_game_stats['team_toi_pp'].isin([None, '']), 0, df_game_stats['team_toi_pp'].apply(string_to_time))
        toi_sh_sec = np.where(df_game_stats['toi_sh'].isin([None, '']), 0, df_game_stats['toi_sh'].apply(string_to_time))

        # calc powerplay toi ratio
        # not sure why I have to set these as pandas seriex (fram array) to get the following calc to work
        toi_pp_sec = pd.Series(toi_pp_sec, index=df_game_stats.index)
        team_toi_pp_sec = pd.Series(team_toi_pp_sec, index=df_game_stats.index)
        toi_pp_ratio = toi_pp_sec / team_toi_pp_sec * 100

        df_game_stats = df_game_stats.assign(
            toi_sec = toi_sec,
            toi_even_sec = toi_even_sec,
            toi_pp_sec = toi_pp_sec,
            team_toi_pp_sec = team_toi_pp_sec,
            toi_sh_sec = toi_sh_sec,
            toi_pp_ratio = toi_pp_ratio,
        )

        def calculate_ewm(df, column):
            return df[column].transform(lambda x: x.ewm(span=ewm_span_sktr).mean().astype(int))

        max_games_sktr = df_game_stats.query(skaters_filter).sort_values(['player_id', 'date']).groupby(['player_id'], as_index=False).agg(games = ('player_id', 'count'))['games'].max()
        max_games_g = df_game_stats.query(goalie_filter).sort_values(['player_id', 'date']).groupby(['player_id'], as_index=False).agg(games = ('player_id', 'count'))['games'].max()
        calculate_ewm_args(ewma_span, max_games_sktr, max_games_g)

        # Sort and group your DataFrame once
        df_sorted_grouped = df_game_stats.sort_values(['player_id','seasonID', 'date']).groupby('player_id')

        # Apply the transformation to each column
        toi_sec_ewm= calculate_ewm(df_sorted_grouped, 'toi_sec')
        toi_even_sec_ewm= calculate_ewm(df_sorted_grouped, 'toi_even_sec')
        toi_pp_sec_ewm= calculate_ewm(df_sorted_grouped, 'toi_pp_sec')
        team_toi_pp_sec_ewm= calculate_ewm(df_sorted_grouped, 'team_toi_pp_sec')
        toi_pp_pg_ratio_ewm= toi_pp_sec_ewm/ team_toi_pp_sec_ewm* 100
        toi_sh_sec_ewm= calculate_ewm(df_sorted_grouped, 'toi_sh_sec')

        # calc really bad start
        # When a goalie has a save percentage in a game less than 85%
        conditions = [
            (df_game_stats['save%'].round(1) < 85.0) & (df_game_stats['pos'] == goalie_position_code) & (df_game_stats['games_started'] == 1),
            (df_game_stats['pos'] == goalie_position_code) & (df_game_stats['games_started'] == 1)
        ]
        choices = [1, 0]
        really_bad_starts = np.select(conditions, choices, default=np.nan)

        df_game_stats = df_game_stats.assign(
            toi_sec_ewm = toi_sec_ewm,
            toi_even_sec_ewm = toi_even_sec_ewm,
            toi_pp_sec_ewm = toi_pp_sec_ewm,
            team_toi_pp_sec_ewm = team_toi_pp_sec_ewm,
            toi_pp_pg_ratio_ewm = toi_pp_pg_ratio_ewm,
            toi_sh_sec_ewm = toi_sh_sec_ewm,
            really_bad_starts = really_bad_starts,
        )

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return df_game_stats

def get_columns_by_attribute(config: Dict, attribute: str) -> List[str]:

    #  ensure that the list elements are unique by converting the list to a set, which only allows unique elements,
    #  and then converting it back to a list
    columns = sorted(list(set(x['title'] for x in config['columns'] if x.get(attribute))))

    return columns

def get_config_column_formats(config: Dict) -> Dict:

    column_formats = {x['title']: x['format'] for x in config['columns'] if 'format' in x and ('table column' in x or 'runtime column' in x)}

    return column_formats

def get_config_column_headings(config: Dict) -> Dict:

    column_headings = {x.get('table column', x.get('runtime column')): x['title'] for x in config['columns'] if x}

    return column_headings

def get_config_default_sort_order_columns(config: Dict) -> List[str]:

    default_desc_sort_order_columns = [x['title'] for x in config['columns'] if x.get('default order') == 'desc']

    return default_desc_sort_order_columns

def get_config_left_aligned_columns(config: Dict) -> List[str]:

    left_aligned_columns = [x['title'] for x in config['columns'] if x.get('justify') == 'left']

    return left_aligned_columns

def get_db_connection():

    # Storing an integer in sqlite results in BLOBs (binary values) instead of INTEGER.
    # The following lines prevent this.
    sqlite3.register_adapter(int64, int)
    sqlite3.register_adapter(int32, int)

    # Get the path to the parent directory
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    parent_dir = os.path.abspath(os.path.join(script_dir, '..'))

    # Construct the path to the SQLite database file
    db_file = os.path.join(parent_dir, DATABASE)

    connection = sqlite3.connect(db_file)

    connection.row_factory = sqlite3.Row

    # uncomment the following line to print the sql statement with parameter substitution, after execution
    # connection.set_trace_callback(print)

    return connection

def get_draft_info_columns(config: Dict) -> List[str]:

    draft_info_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and 'draft' == x.get('data_group'))

    return draft_info_columns

def get_player_position_info_columns(config: Dict, position: str='skater') -> List[str]:

    # only want columns that are position-specific & not in other data groups (e.g., 'z_score_sum'),
    # so must use "position == x['data_group']"
    position_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and position == x.get('data_group'))

    return position_columns

def get_general_info_columns(config: Dict) -> List[str]:

    private_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and 'general' in x.get('data_group'))

    return private_columns

def get_scoring_category_columns(config: Dict, position: str='skater') -> List[str]:

    scoring_category_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and f'{position}_scoring_category' in x.get('data_group'))

    return scoring_category_columns

def get_config_columns(config: Dict) -> List[str]:

    columns = [x['title'] for x in config['columns']]

    return columns

def get_nhl_dot_com_report_data(from_season_id: str='', to_season_id: str='', from_date: str='', to_date: str='', game_type: str='R', position: str='skater', report: str='percentages') -> List:

    # year, _ = split_seasonID_into_component_years(season_id=from_season_id)
    game_type = '03' if game_type == 'P' else '02'
    # first_game_num = 1
    # last_game_num = 225

    # Set the API endpoint URL
    url_base = f'https://api.nhle.com/stats/rest/en/{position}'

    # set request parameters
    params = {
        "isAggregate": 'true',
        "isGame": 'true',
        "sort": '[{"property" : "playerId", "direction": "ASC"}]',
        "start": 0,
        # Setting limit = 0 returns all games for game date
        "limit": 0,
        "factCayenneExp": 'gamesPlayed>=1',
        # "cayenneExp": f'gameId>={year}{game_type}{str(first_game_num).zfill(4)} and gameId<={year}{game_type}{str(last_game_num).zfill(4)}'
        "cayenneExp": f'gameTypeId={game_type} and seasonId>={from_season_id} and seasonId<={to_season_id}'
    }

    # 'penaltyShots' report doesn't accept "gamesPlayed > 1"
    if report == 'penaltyShots':
        del params['factCayenneExp']

    if from_season_id == '' and to_season_id == '' and from_date != '' and to_date != '':
        params["cayenneExp"] = f'gameTypeId={game_type} and gameDate>="{from_date}" and gameDate<="{to_date}"'

    # Send a GET request to the API endpoint with the parameters
    response = requests.get(url=f'{url_base}/{report}', params=params)

    # Check if the request was successful (HTTP status code 200)
    if response.status_code == 200:
        # Extract the data from the JSON response
        data = response.json()['data']
        if len(data) == 0:
            return None
        df = pd.DataFrame(data)
        return df
    else:
        # Handle any errors
        # msg = f'Error: {response.status_code}'
        # dialog['-PROG-'].update(msg)
        # event, values = dialog.read(timeout=10)
        return None

def get_z_score_category_columns(config: Dict, position: str='skater') -> List[str]:

    z_score_category_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and f'{position}_z_score_cat' in x.get('data_group'))

    return z_score_category_columns

def get_z_score_summary_columns(config: Dict, position: str='skater') -> List[str]:

    z_score_category_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and f'{position}_z_score_sum' in x.get('data_group'))

    return z_score_category_columns

def insert_fantrax_columns(df: pd.DataFrame, season_id: Season, game_type: str='R'):

    try:

        dfFantraxPlayerInfo = pd.read_sql(sql=f'select * from FantraxPlayerInfo where season_id={season_id}', con=get_db_connection())

        # set indexes to player_id
        df.set_index('player_id', inplace=True)
        dfFantraxPlayerInfo.set_index('player_id', inplace=True)

        # dfFantraxPlayerInfo seems to have duplicates, so drop duplicates
        dfFantraxPlayerInfo = dfFantraxPlayerInfo[~dfFantraxPlayerInfo.index.duplicated()]

        fantrax_score = dfFantraxPlayerInfo['score']
        fantrax_id = dfFantraxPlayerInfo['fantrax_id']
        rookie = dfFantraxPlayerInfo['rookie'].where(dfFantraxPlayerInfo['rookie'] == 1, '').replace(1,'Yes')

        # if we're getting projected stats, and there are no rookies, there should be, so get from Dobber
        if game_type == 'Prj' and np.count_nonzero(rookie.values) < 10:
            skaters = pd.read_sql_query('SELECT CASE WHEN Rookie = "Y" THEN "Yes" ELSE "" END AS rookie, player_id FROM DobberSkatersDraftList', con=get_db_connection())
            skaters = skaters.set_index('player_id')
            goalies = pd.read_sql_query('SELECT CASE WHEN Rookie = "Y" THEN "Yes" ELSE "" END AS rookie, player_id FROM DobberGoaliesDraftList', con=get_db_connection())
            goalies = goalies.set_index('player_id')
            rookie = skaters['rookie'].combine_first(goalies['rookie'])

        minors = dfFantraxPlayerInfo['minors'].where(dfFantraxPlayerInfo['minors'] == 1, '').replace(1,'Yes')
        watch_list = dfFantraxPlayerInfo['watch_list'].where(dfFantraxPlayerInfo['watch_list'] == 1, '').replace(1,'Yes')
        next_opp = dfFantraxPlayerInfo['next_opp']

        df = df.assign(
            fantrax_score = fantrax_score,
            fantrax_id = fantrax_id,
            rookie = rookie,
            minors = minors,
            watch_list = watch_list,
            next_opp = next_opp,
        )

        # some players in df, but not in dfFantraxPlayerInfo, can have np.nan values
        df.fillna({'fantrax_score': 0, 'rookie': '', 'minors': '', 'watch_list': '', 'next_opp': ''}, inplace=True)

        # reset index to indexes being list of row integers
        df.reset_index(inplace=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    return df

def make_clickable(column: str, value: str, alt_value: str=',', league_id: str='') -> str:

    # https://www.fantrax.com/fantasy/league/nhcwgeytkoxo2wc7/players;reload=2;statusOrTeamFilter=ALL;searchName=Jacob%20Bryson

    link = value

    if column == 'id':
        href = f"https://statsapi.web.nhl.com/api/v1/people/{value}?expand=person.stats&stats=yearByYear,yearByYearPlayoffs,careerRegularSeason&expand=stats.team"
        # target _blank to open new window
        link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'
    elif column == 'name' and league_id != '':
        href = f"https://www.fantrax.com/fantasy/league/{league_id}/players;reload=2;statusOrTeamFilter=ALL;searchName={value.replace(' ', '%20')}"
        # target _blank to open new window
        link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'
    elif column == 'team':
        href = f"https://statsapi.web.nhl.com/api/v1/teams/{alt_value}/roster?expand=roster.person,person.names"
        # target _blank to open new window
        link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'

    return link

def merge_with_current_players_info(season_id: str, pool_id: str, df_stats: pd.DataFrame, game_type: str='R') -> pd.DataFrame:

    columns = ' '.join(textwrap.dedent('''\
        tr.seasonID,
        tr.player_id,
        tr.name,
        tr.pos,
        tr.team_abbr,
        tr.line,
        tr.pp_line,
        p.birth_date,
        p.height,
        p.weight,
        p.active,
        p.roster_status as nhl_roster_status,
        p.games as career_games,
        p.injury_status,
        p.injury_note,
        subquery.id as poolteam_id,
        subquery.name as pool_team,
        subquery.status,
        subquery.keeper
    ''').splitlines())

    select_sql = f'select {columns}'

    # build table joins
    from_tables = textwrap.dedent('''\
        from TeamRosters tr
             left outer join Player p on p.id=tr.player_id
             left outer join (
                select ptr.player_id, pt.id, pt.name, ptr.status, ptr.keeper
                from PoolTeamRoster ptr
                     join PoolTeam pt on pt.id=ptr.poolteam_id
                where pt.pool_id=?
             ) as subquery
             on subquery.player_id=tr.player_id
    ''')

    # get players on nhl team rosters
    if game_type == 'Prj':
        # get players on nhl team rosters, including non-active players (e.g., Connor Bedard with CHI not yet active)
        where_clause = 'where tr.seasonID=?'
    else:
        # get players on nhl team rosters
        # exclude players with p.roster_status!="N" (e.g., include p.roster_status=="Y" or p.roster_status=="I")
        # where_clause = 'where tr.seasonID=? and (p.roster_status!="N" or pool_team>=1)'
        where_clause = 'where tr.seasonID=?'

    sql = textwrap.dedent(f'''\
        {select_sql}
        {from_tables}
        {where_clause}
    ''')

    params = (pool_id, season_id)

    df = pd.read_sql(sql, params=params, con=get_db_connection())

    # get inactive players on pool team rosters
    if game_type == 'Prj':
        columns = ' '.join(textwrap.dedent(f'''\
            {season_id} as seasonID,
            ptr.player_id,
            p.full_name as name,
            p.primary_position as pos,
            '(N/A)' as team_abbr,
            '' as line,
            '' as pp_line,
            p.birth_date,
            p.height,
            p.weight,
            p.active,
            p.roster_status as nhl_roster_status,
            p.games as career_games,
            p.injury_status,
            p.injury_note,
            ptr.poolteam_id,
            pt.name as pool_team,
            ptr.status,
            ptr.keeper
        ''').splitlines())

        select_sql = f'select {columns}'

        # build table joins
        from_tables = textwrap.dedent('''\
            from PoolTeamRoster ptr
            left outer join Player p on p.id=ptr.player_id
            left outer join PoolTeam pt ON pt.id=ptr.poolteam_id
        ''')

        where_clause = f'where pt.pool_id=? and p.active!=1'

        sql = textwrap.dedent(f'''\
            {select_sql}
            {from_tables}
            {where_clause}
        ''')

        params = (pool_id,)

        df_temp = pd.read_sql(sql, params=params, con=get_db_connection())

        # Define a function to get the primary position for a player
        def get_primary_position(player_id):
            try:
                primary_position = j.search('position', requests.get(f'{NHL_API_URL}/player/{player_id}/landing').json())
            except Exception as e:
                if player_id == 8470860: # Halak
                    primary_position = 'G'
                elif player_id == 8470638: # Bergeron
                    primary_position = 'C'
                elif player_id == 8474141: # Patrick Kane
                    primary_position = 'C'
            return primary_position

        # Use the apply method to add the primary position information to the df_temp DataFrame
        df_temp['pos'] = df_temp['player_id'].apply(get_primary_position)

        # merge dataframes
        df = pd.concat([df, df_temp])

    # Replace None values in the specified columns with an empty string
    df[['poolteam_id', 'pool_team', 'status']] = df[['poolteam_id', 'pool_team', 'status']].fillna('')

    # breakout threshold
    # calculate age
    # a player's nhl team roster status, if not blank, will be one of 'Y' = active roster (e.g., 23 man roster), 'N' = full roster, not active roster, 'I' = IR
    # change active status from 1 to Y
    df = df.reset_index(drop=True)
    breakout_thresholds = calc_player_breakout_threshold(df=df)
    # breakout_thresholds = breakout_thresholds.reset_index(drop=True)
    df = df.assign(
        keeper=lambda x: np.where(x['keeper'] == 'y', 'Yes', ''),
        age=calc_player_ages(df=df),
        # Reset the index of the resulting Series and assign it to the 'breakout_threshold' column of the df DataFrame
        breakout_threshold = breakout_thresholds,
        nhl_roster_status=lambda x: x['nhl_roster_status'].replace({'N': '', 'Y': 'y', 'I': 'ir'}, regex=False),
        active=lambda x: np.where(x['active'] == '1', 'y', '')
    )
    ##################################################
    # merge dataframes
    ##################################################

    # drop columns that are duplicates
    columns_to_drop = list(df.columns)
    columns_to_drop.remove('player_id')
    df_stats.drop(columns=columns_to_drop, axis='columns', errors='ignore', inplace=True)

    df_stats = pd.merge(df, df_stats, how='left', on=['player_id'])

    df_stats.set_index(['player_id'], inplace=True)
    # some players are appearing twice; once for team they were on, and the second with team = (N/A); only want the (N/A) row
    # Create a mask to select rows with unique index values
    mask = ~df_stats.index.duplicated(keep='last')
    # Use the mask to filter the DataFrame and keep only rows with unique index values
    df_stats = df_stats.loc[mask]
    df_stats.reset_index(inplace=True)

    return df_stats

# def normalize_scores(series, new_min=0, new_max=100):
#     # It seems the Fantrax has a min = ~3 for skaters, and min = ~25
#     # I have no particular reason to replicate these minimums, but just gonnar run with them for now
#     old_min = series.min()
#     old_max = series.max()
#     return ((series - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min

def normalize_scores(series):
    max = series.max()
    return round((series / max) * 100, 0)

def rankings_to_html(df: pd.DataFrame, config: Dict) -> dict:

    try:

        # set nan to 0 for numeric columns
        cols_to_fill = ['last game', 'first game', 'game today']
        df[cols_to_fill] = df[cols_to_fill].fillna('')

        # Flask’s jsonify function does not handle np.nan values
        # replace all np.nan values in your data with None before passing it to the jsonify function
        df = df.replace(to_replace=np.nan, value=None)

        # format columns before writing to json
        col_formats = get_config_column_formats(config=config)
        cols_to_format = list(set(df.columns) & set(col_formats.keys()))
        df[cols_to_format] = df[cols_to_format].apply(lambda x: x.map(col_formats[x.name]))

        # get stat type column titles
        column_titles = get_config_columns(config=config)

        df_temp = df[column_titles].copy(deep=True)

        stats_data = df_temp[column_titles].values.tolist()

        # cols_to_sort_numeric = [df_temp.columns.get_loc(x) for x in list(df_temp.select_dtypes([np.int,np.float,np.int64,np.float64]).columns) if x in df_temp.columns]
        cols_to_sort_descending = [df_temp.columns.get_loc(x) for x in get_config_default_sort_order_columns(config=config) if x in df_temp.columns]

        # create a dictionary that maps column names to their formatted names
        column_name_map = {x: f'{x.replace(" ","_")}:name' for x in df_temp.columns}
        # create the lists of column names using the dictionary
        general_info_column_names = [column_name_map[x] for x in get_general_info_columns(config=config) if x in df_temp.columns]

        stat_column_names = [column_name_map[x] for x in get_config_columns(config=config) if x in df_temp.columns]

        sktr_info_column_names = [column_name_map[x] for x in get_player_position_info_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_info_column_names = [column_name_map[x] for x in get_player_position_info_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_scoring_categories_column_names = [column_name_map[x] for x in get_scoring_category_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_scoring_categories_column_names = [column_name_map[x] for x in get_scoring_category_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_z_score_categories_column_names = [column_name_map[x] for x in get_z_score_category_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_z_score_categories_column_names = [column_name_map[x] for x in get_z_score_category_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_z_score_summary_column_names = [column_name_map[x] for x in get_z_score_summary_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_z_score_summary_column_names = [column_name_map[x] for x in get_z_score_summary_columns(config=config, position='goalie') if x in df_temp.columns]
        draft_info_column_names = [column_name_map[x] for x in get_draft_info_columns(config=config) if x in df_temp.columns]
        initially_hidden_column_names = [column_name_map[x] for x in get_columns_by_attribute(config=config, attribute='hide') if x in df_temp.columns]
        search_builder_column_names = [column_name_map[x] for x in get_columns_by_attribute(config=config, attribute='search_builder') if x in df_temp.columns]

        max_cat_dict = process_dict(max_cat)
        min_cat_dict = process_dict(min_cat)
        mean_cat_dict = process_dict(mean_cat)
        std_cat_dict = process_dict(std_cat)

        scores_dict = process_dict(scores)

        # create a dictionary to hold variables to use in jquery datatable
        data_dict = {
            'stats_data': stats_data,
            'column_titles': [{"title": col, "name": col.replace(" ","_")} for col in column_titles],
            'descending_columns': cols_to_sort_descending,
            'general_info_column_names': general_info_column_names,
            'sktr_info_column_names': sktr_info_column_names,
            'goalie_info_column_names': goalie_info_column_names,
            'stat_column_names': stat_column_names,
            'sktr_scoring_categories_column_names': sktr_scoring_categories_column_names,
            'goalie_scoring_categories_column_names': goalie_scoring_categories_column_names,
            'sktr_z_score_summary_column_names': sktr_z_score_summary_column_names,
            'goalie_z_score_summary_column_names': goalie_z_score_summary_column_names,
            'sktr_z_score_categories_column_names': sktr_z_score_categories_column_names,
            'goalie_z_score_categories_column_names': goalie_z_score_categories_column_names,
            'draft_info_column_names': draft_info_column_names,
            'initially_hidden_column_names': initially_hidden_column_names,
            'search_builder_column_names': search_builder_column_names,
            'max_cat_dict': max_cat_dict,
            'min_cat_dict': min_cat_dict,
            'mean_cat_dict': mean_cat_dict,
            'std_cat_dict': std_cat_dict,
            'scores_dict': scores_dict,
        }

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    # return the JSON object as a response to the frontend
    return data_dict

def rank_players(generation_type: str, season_or_date_radios: str, from_season_id: str, to_season_id: str, from_date: str, to_date: str, pool_id: str, game_type: str='R', stat_type: str='Cumulative', ewma_span: int=10, projection_source: str='', categories_to_exclude: List=[], positional_scoring: bool=False) -> dict:

    global statType
    statType = stat_type

    if game_type == 'R':
        season_type = 'Regular Season'
    elif game_type == 'P':
        season_type = 'Playoffs'
    else: # game_type == 'Prj'
        season_type = 'Projected Season'

    # # add team games played for each player
    # # Get teams to save in dictionary
    # # global teams_dict
    # if from_season_id == to_season_id:
    #     df_teams = pd.read_sql(f'select team_id, games from TeamStats where seasonID={from_season_id} and game_type="{game_type}"', con=get_db_connection())
    # else:
    #     df_teams = pd.read_sql(f'select team_id, sum(games) as games from TeamStats where seasonID between {from_season_id} and {to_season_id} and game_type="{game_type}" group by team_id', con=get_db_connection())
    # teams_dict = {x.team_id: {'games': x.games} for x in df_teams.itertuples()}

    if season_type == 'Projected Season':
        df_player_stats = calc_player_projected_stats(current_season_stats=True, season_id=from_season_id, projection_source=projection_source)
    else:
        #######################################################################################
        #######################################################################################
        # generate games statitics

        if generation_type == 'full':

            df_game_stats = get_game_stats(season_or_date_radios=season_or_date_radios, from_season_id=from_season_id, to_season_id=to_season_id, from_date=from_date, to_date=to_date, pool_id=pool_id, game_type=game_type, ewma_span=ewma_span)

            # save to json file
            ###################################################################
            # Create the absolute path to the parent directory
            parent_dir = os.getcwd()
            # Create the 'json' folder if it doesn't exist
            json_folder = os.path.join(parent_dir, 'json')
            os.makedirs(json_folder, exist_ok=True)
            # Save the DataFrame as a JSON file in the 'json' folder
            json_file_path = os.path.join(json_folder, 'player_game_data.json')
            df_game_stats.to_json(json_file_path)
            ###################################################################

        if generation_type == 'aggregateData':

            # get dataframe from json file
            ###################################################################
            # Create the absolute path to the parent directory
            parent_dir = os.getcwd()
            json_folder = os.path.join(parent_dir, 'json')
            json_file_path = os.path.join(json_folder, 'player_game_data.json')
            # Read the DataFrame from JSON file in the 'json' folder
            df_game_stats = pd.read_json(json_file_path)
            ###################################################################

        if generation_type in ('full', 'aggregateData'):
            #######################################################################################
            # aggregate per game stats per player
            df_player_stats = aggregate_game_stats(df=df_game_stats, stat_type=stat_type, ewma_span=ewma_span)

            if df_player_stats is None or df_player_stats.empty:
                return None

            ###################################################################################
            # skater shot attempt % (5v5) report
            # {
            #   "gameDate":"2023-02-18",
            #   "gameId":2022020891,
            #   "gamesPlayed":1,
            #   "homeRoad":"R",
            #   "lastName":"Seeler",
            #   "opponentTeamAbbrev":"VAN",
            #   "playerId":8476372,
            #   "positionCode":"D",
            #   "satPercentage":0.947,
            #   "satPercentageAhead":null,
            #   "satPercentageBehind":null,
            #   "satPercentageClose":0.916,
            #   "satPercentageTied":0.833,
            #   "satRelative":0.330,
            #   "shootingPct5v5":null,
            #   "shootsCatches":"L",
            #   "skaterFullName":"Nick Seeler",
            #   "skaterSavePct5v5":null,
            #   "skaterShootingPlusSavePct5v5":null,
            #   "teamAbbrev":"PHI",
            #   "timeOnIcePerGame5v5":716.000,
            #   "usatPercentage":0.928,
            #   "usatPercentageAhead":null,
            #   "usatPercentageBehind":null,
            #   "usatPercentageTied":0.800,
            #   "usatPrecentageClose":0.888,
            #   "usatRelative":0.342,
            #   "zoneStartPct5v5":0.750
            # }
            ###################################################################################
            if season_or_date_radios == 'date':
                df_api = get_nhl_dot_com_report_data(from_date=from_date, to_date=to_date, game_type=game_type, position='skater', report='percentages')
            else:
                df_api = get_nhl_dot_com_report_data(from_season_id=from_season_id, to_season_id=to_season_id, game_type=game_type, position='skater', report='percentages')

            if df_api is not None and not df_api.empty:
                df_api = df_api[['playerId', 'skaterSavePct5v5', 'shootingPct5v5', 'skaterShootingPlusSavePct5v5']]
                df_api['skaterSavePct5v5'] = df_api['skaterSavePct5v5'].multiply(100)
                df_api['shootingPct5v5'] = df_api['shootingPct5v5'].multiply(100)
                df_api['skaterShootingPlusSavePct5v5'] = df_api['skaterShootingPlusSavePct5v5'].multiply(100)
                # Rename the columns
                df_api = df_api.rename(columns={
                            'playerId': 'player_id',
                            'skaterSavePct5v5': 'on_ice_sv_pct',
                            'shootingPct5v5': 'on_ice_sh_pct',
                            'skaterShootingPlusSavePct5v5': 'pdo'
                        })
            else:
                # Create an empty DataFrame with the column names
                df_api = pd.DataFrame(columns=['player_id', 'on_ice_sv_pct', 'on_ice_sh_pct', 'pdo'])

            # Merge df_player_stats and df_api
            df_player_stats = pd.merge(df_player_stats, df_api, how='left', on='player_id')

    if generation_type != 'calculateScores':

        # save to json file
        ###################################################################
        # Create the absolute path to the parent directory
        parent_dir = os.getcwd()
        # Create the 'json' folder if it doesn't exist
        json_folder = os.path.join(parent_dir, 'json')
        os.makedirs(json_folder, exist_ok=True)
        # Save the DataFrame as a JSON file in the 'json' folder
        json_file_path = os.path.join(json_folder, 'player_data.json')
        df_player_stats.to_json(json_file_path)
        ###################################################################

    if generation_type == 'calculateScores':

        # get dataframe from json file
        ###################################################################
        # Create the absolute path to the parent directory
        parent_dir = os.getcwd()
        json_folder = os.path.join(parent_dir, 'json')
        json_file_path = os.path.join(json_folder, 'player_data.json')
        # Read the DataFrame from JSON file in the 'json' folder
        df_player_stats = pd.read_json(json_file_path)
        ###################################################################

    ###################################################################
    # at this point, generation_type in ('full', 'aggregateData', 'calculateScores')

    # merge with current player info
    df_player_stats = merge_with_current_players_info(season_id=to_season_id, pool_id=pool_id, df_stats=df_player_stats, game_type=game_type)

    # add fantrax "score" & "minors" columns
    df_player_stats = insert_fantrax_columns(df=df_player_stats, season_id=to_season_id, game_type=game_type)

    # calc global mean and std dev for z-score calculations
    calc_scoring_category_means(df=df_player_stats)
    calc_scoring_category_std_deviations(df=df_player_stats)

    # z-scores
    df_player_stats = calc_z_scores(df=df_player_stats, positional_scoring=positional_scoring, stat_type=statType)

    # calc global minumums & maximums
    calc_scoring_category_minimums(df=df_player_stats)
    calc_scoring_category_maximums(df=df_player_stats)

    # scoring category scores
    df_player_stats = calc_scoring_category_scores(df=df_player_stats, positional_scoring=positional_scoring)

    # summary scores
    df_player_stats = calc_summary_scores(df=df_player_stats, positional_scoring=positional_scoring, categories_to_exclude=categories_to_exclude)

    # add draft list info
    df_player_stats = add_draft_list_columns_to_df(season_id=to_season_id, df=df_player_stats)

    # add pre_draft_keeper & pre_draft_manager columns:
    add_pre_draft_keeper_list_column_to_df(pool_id=pool_id, df=df_player_stats)

    # drop rows for irrelevant players; e.g., no games played, projected games, or not on a pool team or not on my watchlist
    if game_type == 'Prj':
        # drop players when projections are used the projected games !> 0
        df_player_stats.query('(games.notna() and games>=1) or watch_list=="Yes" or keeper=="Yes"', inplace=True)
    else:
        # drop players in minors and not on active nhl team roster, and not on a pool team
        # removed minors=="" from `'(games>=1 and games.notna() and minors=="" and nhl_roster_status=="y")`. if player has
        # played games, then should be in player lists
        # for the same reason as above, I removed nhl_roster_status=="y" from `'(games>=1 and games.notna() and minors=="" and nhl_roster_status=="y")`
        df_player_stats.query('(games>=1 and games.notna()) or (poolteam_id!="" and poolteam_id.notna()) or watch_list=="Yes" or (line.notna() and line!="") or (pp_line.notna() and pp_line!="") or picked_by!=""', inplace=True)

    # df_player_stats['pool_team'].fillna(value='', inplace=True)

    # potential draft round
    # if game_type == 'Prj' and projection_source in ['Averaged', 'Fantrax']:
    if game_type == 'Prj':
        calc_projected_draft_round(df_player_stats=df_player_stats)
    #####################################################################
    # df_player_stats should not change past this point

    # stats have been generated
    try:

        df_stats = df_player_stats.copy(deep=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        sg.popup_error(msg)

    if len(df_stats.index) == 0:
        print('There are no players to list.')

    df_k = df_stats.copy(deep=True)

    # Add a checkbox column at the beginning of the DataFrame
    df_k['checkbox'] = '<input type="checkbox" class="row-checkbox"></input>'

    config = stats_config(position='all')
    column_formats = get_config_column_formats(config=config)

    # z-score rank
    df_k['z_score_rank'] = pd.to_numeric(df_k['z_score'].apply(column_formats['z-score']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)

    skaters_mask = df_k.eval(skaters_filter)
    goalie_mask = df_k.eval(goalie_filter)
    minimum_one_game_mask = df_k.eval(minimum_one_game_filter)
    df_sktr = df_k.loc[skaters_mask & minimum_one_game_mask]
    df_g = df_k.loc[goalie_mask & minimum_one_game_mask]

    # z-offense rank
    df_k['z_offense_rank'] = pd.to_numeric(df_sktr['z_offense'].apply(column_formats['z-offense']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)
    # z-peripheral rank
    df_k['z_peripheral_rank'] = pd.to_numeric(df_sktr['z_peripheral'].apply(column_formats['z-peripheral']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)

    # z-count rank
    df_k['z_count_rank'] = pd.to_numeric(df_g['z_count'].apply(column_formats['z-count']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)
    # z-peripheral rank
    df_k['z_ratio_rank'] = pd.to_numeric(df_g['z_ratio'].apply(column_formats['z-ratio']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)

    # score rank
    df_k['score_rank'] =  pd.to_numeric(df_k['score'].apply(column_formats['score']).replace('', np.nan), errors='coerce').astype(float).rank(method='min', na_option='bottom', ascending=False)

    # these rankins weill be set in data_tables.js, so their values aren't really important here
    df_k['rank'] = df_k['z_score_rank']
    df_k['sort_rank'] = df_k['z_score_rank']

    column_headings = get_config_column_headings(config=config)
    df_k.rename(columns=column_headings, inplace=True)
    df_k = df_k.reindex(columns=[v for v in column_headings.values()])

    column_left_alignment = get_config_left_aligned_columns(config=config)

    ##############################################################################################
    # before dropping hidden columns, set cells with clickable links

    conn = get_db_connection()
    c = conn.cursor()
    # Execute a query to retrieve the league_id from the HockeyPool table using the given pool_id
    c.execute('SELECT league_id FROM HockeyPool WHERE id = ?', (pool_id,))
    league_id = c.fetchone()[0]
    # Close the database connection
    conn.close()

    def create_link(row, league_id):
        if pd.notnull(row['fantrax id']) and row['fantrax id'] != '':
            return '<a target="_blank" href="https://www.fantrax.com/player/' + row['fantrax id'] + '/' + league_id + '" style="color: green">' + row['name'] + '</a>'
        else:
            return '<a target="_blank" href="https://www.fantrax.com/fantasy/league/' + league_id + '/players;reload=2;statusOrTeamFilter=ALL;searchName=' + row['name'].replace(' ', '%20') + '" style="color: green">' + row['name'] + '</a>'

    df_k['name'] = df_k.apply(create_link, axis=1, args=(league_id,))

    # df_k['team'] = '<a target="_blank" href="https://statsapi.web.nhl.com/api/v1/teams/' + df_k['team id str'] + '/roster?expand=roster.person,person.names" style="color: green">' + df_k['team'] + '</a>'

    ##############################################################################################

    (start_year, end_year) = split_seasonID_into_component_years(season_id=from_season_id)
    if from_season_id != to_season_id:
        seasons = f'{from_season_id} to {to_season_id} Seasons'
    elif season_type == 'Playoffs':
        seasons = f'{start_year-1}-{end_year-1} Playoffs'
    else:
        seasons = f'{from_season_id} Season'

    data_dict = rankings_to_html(
                    df=df_k,
                    config=config
                )


    return data_dict

def stats_config(position: str='all') -> Tuple[List, List, List, Dict, List]:

    config = {
        'columns': [
            {'title': 'sel', 'table column': 'checkbox'},
            {'title': 'list rank', 'runtime column': 'rank', 'data_group': 'general', 'format': eval(f_0_decimals)},
            {'title': 'z-score rank', 'runtime column': 'z_score_rank', 'data_group': 'general', 'format': eval(f_0_decimals), 'search_builder': True},
            {'title': 'z-offense rank', 'runtime column': 'z_offense_rank', 'data_group': 'skater_z_score_sum', 'format': eval(f_0_decimals), 'search_builder': True, 'hide': True},
            {'title': 'z-peripheral rank', 'runtime column': 'z_peripheral_rank', 'data_group': 'skater_z_score_sum', 'format': eval(f_0_decimals), 'search_builder': True, 'hide': True},
            {'title': 'z-count rank', 'runtime column': 'z_count_rank', 'data_group': 'goalie_z_score_sum', 'format': eval(f_0_decimals), 'search_builder': True, 'hide': True},
            {'title': 'z-ratio rank', 'runtime column': 'z_ratio_rank', 'data_group': 'goalie_z_score_sum', 'format': eval(f_0_decimals), 'search_builder': True, 'hide': True},
            {'title': 'score rank', 'runtime column': 'score_rank', 'data_group': 'general', 'format': eval(f_0_decimals), 'search_builder': True},
            {'title': 'sort rank', 'runtime column': 'sort_rank', 'data_group': 'general', 'format': eval(f_0_decimals)},
            {'title': 'id', 'table column': 'player_id', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'fantrax id', 'table column': 'fantrax_id', 'data_group': 'general', 'hide': True},
            {'title': 'name', 'table column': 'name', 'justify': 'left', 'search_builder': True},
            {'title': 'team id', 'table column': 'team_id', 'data_group': 'general', 'hide': True},
            {'title': 'team', 'table column': 'team_abbr', 'data_group': 'general', 'search_builder': True},
            {'title': 'pos', 'table column': 'pos', 'search_pane': True, 'data_group': 'general', 'search_builder': True},
            {'title': 'fantrax roster status', 'table column': 'status', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'age', 'table column': 'age', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},
            {'title': 'height', 'table column': 'height', 'data_group': 'general', 'hide': True},
            {'title': 'weight', 'table column': 'weight', 'data_group': 'general', 'hide': True},
            {'title': 'career games', 'table column': 'career_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'bt', 'table column': 'breakout_threshold', 'format': eval(f_0_decimals_show_0), 'data_group': 'skater', 'hide': True, 'search_builder': True},
            {'title': 'keeper', 'table column': 'keeper', 'format': eval(f_nan_to_empty), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'pre-draft keeper', 'table column': 'pre_draft_keeper', 'format': eval(f_nan_to_empty), 'data_group': 'draft', 'hide': True, 'search_builder': True},
            {'title': 'pre-draft manager', 'table column': 'pre_draft_manager', 'format': eval(f_nan_to_empty), 'data_group': 'draft', 'hide': True, 'search_builder': True},
            {'title': 'rookie', 'table column': 'rookie', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'active', 'table column': 'active', 'data_group': 'general', 'hide': True},
            {'title': 'nhl roster status', 'table column': 'nhl_roster_status', 'data_group': 'general', 'hide': True},
            {'title': 'minors', 'table column': 'minors', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'watch', 'table column': 'watch_list', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'prj draft round', 'runtime column': 'pdr', 'data_group': 'draft', 'hide': True},
            {'title': 'injury', 'table column': 'injury_status', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'hide': True},
            {'title': 'injury note', 'table column': 'injury_note', 'justify': 'left', 'data_group': 'general', 'hide': True},
            {'title': 'manager', 'table column': 'pool_team', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'search_builder': True},
            {'title': 'team gp', 'table column': 'team_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True},
            {'title': 'gp', 'table column': 'games', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},
            {'title': '% of team gp', 'table column': 'percent_of_team_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'first game', 'table column': 'first_game', 'format': eval(f_str), 'data_group': 'general', 'hide': True},
            {'title': 'last game', 'table column': 'last_game', 'format': eval(f_str), 'data_group': 'general', 'default order': 'desc', 'search_builder': True, 'hide': True},
            {'title': 'game today', 'table column': 'next_opp', 'data_group': 'general', 'hide': True, 'search_builder': True},
        ],
    }

    other_score_columns = {
        'columns': [
            {'title': 'fantrax score', 'runtime column': 'fantrax_score', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'general', 'hide': True},
            {'title': 'fantrax adp', 'runtime column': 'adp', 'format': eval(f_1_decimal), 'data_group': 'draft', 'hide': True},
        ],
    }

    config['columns'].extend(other_score_columns['columns'])

    league_draft_columns = {
        'columns': [
            {'title': 'draft round', 'table column': 'round', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True, 'search_builder': True},
            {'title': 'draft position', 'table column': 'pick', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'manager\'s pick #', 'table column': 'managers_pick_number', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'overall', 'table column': 'overall', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'picked by', 'table column': 'picked_by', 'justify': 'left', 'data_group': 'draft', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(league_draft_columns['columns'])

    score_summary_columns = {
        'columns': [
            {'title': 'z-score', 'runtime column': 'z_score', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'search_builder': True},
            {'title': 'score', 'runtime column': 'score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'search_builder': True},
            {'title': 'z-combo', 'runtime column': 'z_combo', 'format': eval(f_str), 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum')},
            {'title': 'z-offense', 'runtime column': 'z_offense', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'offense score', 'runtime column': 'offense', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-offense combo', 'runtime column': 'z_offense_combo', 'format': eval(f_str), 'default order': 'desc', 'data_group': 'skater_z_score_sum'},
            {'title': 'z-peripheral', 'runtime column': 'z_peripheral', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'peripheral score', 'runtime column': 'peripheral', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-peripheral combo', 'runtime column': 'z_peripheral_combo', 'format': eval(f_str), 'default order': 'desc', 'data_group': 'skater_z_score_sum'},

            {'title': 'z-count', 'runtime column': 'z_count', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'count score', 'runtime column': 'g_count', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-count combo', 'runtime column': 'z_g_count_combo', 'format': eval(f_str), 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},
            {'title': 'z-ratio', 'runtime column': 'z_ratio', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'ratio score', 'runtime column': 'g_ratio', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-ratio combo', 'runtime column': 'z_g_ratio_combo', 'format': eval(f_str), 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},

        ],
    }

    config['columns'].extend(score_summary_columns['columns'])

    skater_columns = {
        'columns': [
            {'title': 'line', 'table column': 'line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True},
            {'title': 'pp unit', 'table column': 'pp_line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True},
            {'title': 'pp unit prj', 'runtime column': 'pp_unit_prj', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'sleeper', 'runtime column': 'sleeper', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': 'upside', 'runtime column': 'upside', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': '3yp', 'runtime column': '3yp', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': 'bandaid boy', 'runtime column': 'bandaid_boy', 'format': eval(f_str), 'data_group': 'draft', 'hide': True},

            {'title': 'on-ice sh%', 'table column': 'on_ice_sh_pct', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'on-ice sv%', 'table column': 'on_ice_sv_pct', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pdo', 'table column': 'pdo', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'toi (sec)', 'runtime column': 'toi_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi (min)', 'runtime column': 'toi_min', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi pg', 'table column': 'toi_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi pg (sec)', 'runtime column': 'toi_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg (trend)', 'runtime column': 'toi_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi pg (ewm)', 'table column': 'toi_pg_ewm_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'search_builder': True},

            {'title': 'toi even (sec)', 'runtime column': 'toi_even_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg', 'table column': 'toi_even_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi even pg (sec)', 'runtime column': 'toi_even_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg (trend)', 'runtime column': 'toi_even_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi even pg (ewm)', 'table column': 'toi_even_pg_ewm_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'search_builder': True},

            {'title': 'ev pts', 'table column': 'evg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev on-ice', 'table column': 'evg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev ipp', 'table column': 'evg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'cf', 'table column': 'corsi_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ca', 'table column': 'corsi_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'cf%', 'table column': 'corsi_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': False, 'hide': True, 'search_builder': True},
            {'title': 'ff', 'table column': 'fenwick_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'fa', 'table column': 'fenwick_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ff%', 'table column': 'fenwick_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': True},

            {'title': 'toi pp (sec)', 'runtime column': 'toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg', 'table column': 'toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi pp pg (sec)', 'runtime column': 'toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg (trend)', 'runtime column': 'toi_pp_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi pp pg (ewm)', 'table column': 'toi_pp_pg_ewm_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'search_builder': True},

            {'title': 'pp sog/120', 'table column': 'pp_sog_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp g/120', 'table column': 'pp_goals_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp pts/120', 'table column': 'pp_pts_p120', 'format': eval(f_2_decimals_show_0), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp pts', 'table column': 'ppg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp on-ice', 'table column': 'ppg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp ipp', 'table column': 'ppg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'team toi pp (sec)', 'runtime column': 'team_toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg', 'table column': 'team_toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg (sec)', 'runtime column': 'team_toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg (ewm)', 'table column': 'team_toi_pp_pg_ewm_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': '%pp', 'runtime column': 'toi_pp_pg_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp (last game)', 'runtime column': 'toi_pp_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp (trend)', 'runtime column': 'toi_pp_pg_ratio_trend', 'format': eval(f_1_decimal_show_0_and_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': '%pp (ewm)', 'runtime column': 'toi_pp_pg_ratio_ewm', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'search_builder': True},

            {'title': 'toi sh (sec)', 'runtime column': 'toi_sh_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg', 'table column': 'toi_sh_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi sh pg (sec)', 'runtime column': 'toi_sh_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg (trend)', 'runtime column': 'toi_sh_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},
            {'title': 'toi sh pg (ewm)', 'table column': 'toi_sh_pg_ewm_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'search_builder': True},

            {'title': 'sh%', 'table column': 'shooting%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'search_builder': True, 'hide': True},
            {'title': 'hd sat', 'table column': 'highDangerShots', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'hd sog', 'table column': 'highDangerShotsOnGoal', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'xg', 'table column': 'xGoals', 'format': eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_columns['columns'])

    skater_stat_columns = {
        'columns': [
            {'title': 'pts', 'table column': 'points', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'g', 'table column': 'goals', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'a', 'table column': 'assists', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'ppp', 'table column': 'points_pp', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'sog', 'table column': 'shots', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'missed shots', 'table column': 'missed_shots', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'missed shots (metal)', 'table column': 'missed_shots_metal', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp sog', 'table column': 'shots_powerplay', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'tk', 'table column': 'takeaways', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'hits', 'table column': 'hits', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'blk', 'table column': 'blocked', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'pim', 'table column': 'pim', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'search_builder': True},
            {'title': 'penalties', 'table column': 'penalties', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_stat_columns['columns'])

    skater_zscore_columns = {
        'columns': [
            {'title': 'z-pts', 'runtime column': 'z_points', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-g', 'runtime column': 'z_goals', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-a', 'runtime column': 'z_assists', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-ppp', 'runtime column': 'z_points_pp', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sog', 'runtime column': 'z_shots', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-tk', 'runtime column': 'z_takeaways', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-hits', 'runtime column': 'z_hits', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-blk', 'runtime column': 'z_blocked', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-pim', 'runtime column': 'z_pim', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-penalties', 'runtime column': 'z_penalties', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_zscore_columns['columns'])

    skater_category_score_columns = {
        'columns': [
            {'title': 'pts score', 'runtime column': 'd_points_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'g score', 'runtime column': 'goals_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'a score', 'runtime column': 'assists_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'ppp score', 'runtime column': 'points_pp_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'sog score', 'runtime column': 'shots_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'tk score', 'runtime column': 'takeaways_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'hits score', 'runtime column': 'hits_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'blk score', 'runtime column': 'blocked_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'pim score', 'runtime column': 'pim_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'penalties score', 'runtime column': 'penalties_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_category_score_columns['columns'])

    goalie_columns = {
        'columns': [
            {'title': 'tier', 'runtime column': 'tier', 'data_group': 'draft', 'hide': True},
            {'title': 'goalie starts', 'table column': 'games_started', 'format': eval(f_0_decimals), 'data_group': 'goalie', 'search_builder': True},
            {'title': '% of team games started', 'table column': 'starts_as_percent', 'format': eval(f_0_decimals), 'hide': True, 'data_group': 'goalie'},
            {'title': 'qs', 'table column': 'quality_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie'},
            {'title': 'qs %', 'table column': 'quality_starts_as_percent', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie', 'search_builder': True},
            {'title': 'rbs', 'table column': 'really_bad_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie'},
            {'title': 'goals against', 'table column': 'goals_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
            {'title': 'xga', 'table column': 'xGoalsAgainst', 'format': eval(f_2_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
            {'title': 'gsax', 'table column': 'goals_saved_above_expected', 'format': eval(f_2_decimals), 'default order': 'desc', 'data_group': 'goalie'},
            {'title': 'shots against', 'table column': 'shots_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
        ],
    }

    config['columns'].extend(goalie_columns['columns'])

    goalie_stat_columns = {
        'columns': [
            {'title': 'w', 'table column': 'wins', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_2_decimals), 'default order': 'desc', 'data_group': 'goalie_scoring_category', 'search_builder': True},
            {'title': 'sv', 'table column': 'saves', 'format': eval(f_0_decimals) if statType=='Cumulative' else eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie_scoring_category', 'search_builder': True},
            {'title': 'gaa', 'table column': 'gaa', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'default order': 'desc', 'data_group': 'goalie_scoring_category', 'search_builder': True},
            {'title': 'sv%', 'table column': 'save%', 'format': eval(f_3_decimals_no_leading_0), 'default order': 'desc', 'data_group': 'goalie_scoring_category', 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_stat_columns['columns'])

    goalie_zscore_columns = {
        'columns': [
            {'title': 'z-w', 'runtime column': 'z_wins', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv', 'runtime column': 'z_saves', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-gaa', 'runtime column': 'z_gaa', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv%', 'runtime column': 'z_save%', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_zscore_columns['columns'])

    goalie_category_score_columns = {
        'columns': [
            {'title': 'w score', 'runtime column': 'wins_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'sv score', 'runtime column': 'saves_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'gaa score', 'runtime column': 'gaa_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'sv% score', 'runtime column': 'save%_score', 'format': eval(f_0_decimals_show_0), 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_category_score_columns['columns'])

    return deepcopy(config)
