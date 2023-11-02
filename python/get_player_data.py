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
from datetime import datetime, timedelta
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

from constants import  DATABASE, NHL_API_URL
from utils import calculate_age, seconds_to_string_time, split_seasonID_into_component_years, string_to_time

# formatting for ranking tables
f_0_decimals = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.0f}'.format(x)", '<string>', 'eval')
f_0_toi_to_empty = compile("lambda x: '' if x in ('00:00', None) or pd.isna(x) else x", '<string>', 'eval')
f_0_toi_to_empty_and_show_plus = compile("lambda x: '' if x in ('+00:00', '+0:00', None) or pd.isna(x) else x", '<string>', 'eval')
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

skaters_filter = f'pos in {skater_position_codes}'
forwards_filter = f'pos in {forward_position_codes}'
defense_filter = f'pos == "{defense_position_code}"'
goalie_filter = f'pos == "{goalie_position_code}"'

###############################################
###############################################
# Fantrax scoring categories
###############################################
# Forwards and Defense
sktr_cumulative_categories = ['points', 'goals', 'assists', 'shots', 'points_pp', 'pim', 'hits', 'blocked', 'takeaways', 'penalties']
sktr_cumulative_z_categories = ['z_points', 'z_goals', 'z_assists', 'z_shots', 'z_points_pp', 'z_pim', 'z_hits', 'z_blocked', 'z_takeaways', 'z_penalties']
sktr_per_game_categories = ['pts_pg', 'g_pg', 'a_pg', 'sog_pg', 'ppp_pg', 'pim_pg', 'hits_pg', 'blk_pg', 'tk_pg', 'penalties_pg']
sktr_per_game_z_categories = ['z_pts_pg', 'z_g_pg', 'z_a_pg', 'z_sog_pg', 'z_ppp_pg', 'z_pim_pg', 'z_hits_pg', 'z_blk_pg', 'z_tk_pg', 'z_penalties_pg']
sktr_per_60_categories = ['pts_p60', 'g_p60', 'a_p60', 'sog_p60', 'ppp_p60', 'pim_p60', 'hits_p60', 'blk_p60', 'tk_p60', 'penalties_p60']
sktr_per_60_z_categories = ['z_pts_p60', 'z_g_p60', 'z_a_p60', 'z_sog_p60', 'z_ppp_p60', 'z_pim_p60', 'z_hits_p60', 'z_blk_p60', 'z_tk_p60', 'z_penalties_p60']
###############################################
# Goalies
goalie_cumulative_categories = ['wins', 'saves', 'gaa', 'save%']
goalie_cumulative_z_categories = ['z_wins', 'z_saves', 'z_gaa', 'z_save%']
goalie_per_game_categories = ['wins_pg', 'saves_pg', 'gaa_pg', 'save%_pg']
goalie_per_game_z_categories = ['z_wins_pg', 'z_saves_pg', 'z_gaa_pg', 'z_save%_pg']
goalie_per_60_categories = ['wins_p60', 'saves_p60', 'gaa_p60', 'save%_p60']
goalie_per_60_z_categories = ['z_wins_p60', 'z_saves_p60', 'z_gaa_p60', 'z_save%_p60']
###############################################
###############################################
# Summary z-score columns
###############################################
# cumulative stat z-scores
sktr_cumulative_summary_z_scores = ['z_score', 'z_offense', 'z_peripheral', 'z_sog_hits_blk', 'z_hits_blk', 'z_goals_hits_pim', 'z_hits_pim']
g_cumulative_summary_z_scores = ['z_score', 'z_g_count', 'z_g_ratio']
# per game stat z-scores
sktr_per_game_summary_z_scores = ['z_score_pg', 'z_offense_pg', 'z_peripheral_pg', 'z_sog_hits_blk_pg', 'z_hits_blk_pg', 'z_goals_hits_pim_pg', 'z_hits_pim_pg']
g_per_game_summary_z_scores = ['z_score_pg', 'z_g_count_pg', 'z_g_ratio_pg']
# per 60 stat z-scores
sktr_per_60_summary_z_scores = ['z_score_p60', 'z_offense_p60', 'z_peripheral_p60', 'z_sog_hits_blk_p60', 'z_hits_blk_p60', 'z_goals_hits_pim_p60', 'z_hits_pim_p60']
g_per_60_summary_z_scores = ['z_score_p60', 'z_g_count_p60', 'z_g_ratio_p60']
###############################################
###############################################

# period for rolling averages
rolling_avg_period = 3

min_cat = defaultdict(None)
max_cat = defaultdict(None)
mean_cat = defaultdict(None)
std_cat = defaultdict(None)

def add_draft_list_columns_to_df(season_id: str, df: pd.DataFrame):

    sql = f'select * from dfDraftResults where season_id={season_id}'
    df_draft_list = pd.read_sql(sql, con=get_db_connection())

    # add draft list columns to df
    df.set_index(['player_id'], inplace=True)
    df_draft_list.set_index(['player_id'], inplace=True)

    df = df.assign(
        round = df_draft_list['round'],
        pick = df_draft_list['pick'],
        overall = df_draft_list['overall'],
        picked_by = df_draft_list['pool_team'],
    )

    df.fillna({'picked_by': ''}, inplace=True)

    df.reset_index(inplace=True)

    return df

def add_pre_draft_keeper_list_column_to_df(season_id: str, df: pd.DataFrame):

    sql = f'select player_id, "Yes" as pre_draft_keeper from KeeperListsArchive where season_id={season_id}'
    df_keeper_list = pd.read_sql(sql, con=get_db_connection())

    # add pre-draft keeper columns to df
    df.set_index(['player_id'], inplace=True)
    df_keeper_list.set_index(['player_id'], inplace=True)

    df['pre_draft_keeper'] = df_keeper_list['pre_draft_keeper']

    df.fillna({'pre_draft_keeper': ''}, inplace=True)

    df.reset_index(inplace=True)

    return

def aggregate_game_stats(df: pd.DataFrame) -> pd.DataFrame:

    df_agg_stats = df.sort_values(['player_id','seasonID', 'date']).groupby(['player_id'], as_index=False).aggregate({
            'seasonID': 'last',
            'player_id': ['last', 'count'],
            'name': 'last',
            'pos': 'last',
            'date': ['first', 'last'],
            'team_id': 'last',
            'team_abbr': 'last',
            'toi_sec': 'sum',
            'toi_sec_ra': 'last',
            'toi_even_sec': 'sum',
            'toi_even_sec_ra': 'last',
            'toi_pp_sec': 'sum',
            'toi_pp_sec_ra': 'last',
            'team_toi_pp_sec': 'sum',
            'team_toi_pp_sec_ra': 'last',
            'toi_pp_ratio': 'last',
            'toi_pp_ratio_ra': 'last',
            'toi_sh_sec': 'sum',
            'toi_sh_sec_ra': 'last',
            'points': 'sum',
            'points_pp': 'sum',
            'goals': 'sum',
            'assists': 'sum',
            'goals_gw': 'sum',
            'goals_ot': 'sum',
            'goals_pp': 'sum',
            'goals_ps': 'sum',
            'goals_sh': 'sum',
            'assists_gw': 'sum',
            'assists_ot': 'sum',
            'assists_pp': 'sum',
            'assists_sh': 'sum',
            'hattricks': 'sum',
            'shots': 'sum',
            'shots_powerplay': 'sum',
            'pim': 'sum',
            'penalties': 'sum',
            'minor_penalties': 'sum',
            'major_penalties': 'sum',
            'misconduct_penalties': 'sum',
            'game_misconduct_penalties': 'sum',
            'match_penalties': 'sum',
            'hits': 'sum',
            'blocked': 'sum',
            'takeaways': 'sum',
            'evg_on_ice': 'sum',
            'evg_point': 'sum',
            'ppg_on_ice': 'sum',
            'ppg_point': 'sum',
            'games_started': 'sum',
            'wins': 'sum',
            'wins_ot': 'sum',
            'wins_so': 'sum',
            'shutouts': 'sum',
            'goals_against': 'sum',
            'shots_against': 'sum',
            'saves': 'sum',
            'quality_starts': 'sum',
            'really_bad_starts': 'sum',
            'corsi_against': 'sum',
            'corsi_for': 'sum',
            'fenwick_against': 'sum',
            'fenwick_for': 'sum',
        })

    # if stats have not been yet been retrieved from nhl rest api, for the current week, df_agg_stats will be emtpy
    if len(df_agg_stats.index) == 0:
        return None

    # change column labels
    df_agg_stats.columns = df_agg_stats.columns.map('_'.join)

    df_agg_stats.rename(columns={
        'player_id_count': 'games',
        'date_first': 'first game',
        'date_last': 'last game',
    }, inplace=True)

    # don't want the '_sum', '_last'
    df_agg_stats.rename(columns={x: x.rsplit('_', 1)[0] for x in df_agg_stats.columns}, inplace=True)

    ########################################################################################################
    df_agg_stats.set_index('player_id', inplace=True)
    ########################################################################################################

    # time-on-ice per game in seconds
    toi_pg_sec = df_agg_stats['toi_sec']/df_agg_stats['games']

    # even time-on-ice per game in seconds
    toi_even_pg_sec = df_agg_stats['toi_even_sec']/df_agg_stats['games']

    # even goals IPP
    evg_ipp = np.where(df_agg_stats['evg_on_ice'] != 0, df_agg_stats['evg_point'] / df_agg_stats['evg_on_ice'] * 100, np.nan)
    evg_ipp = pd.Series(evg_ipp, index=df_agg_stats.index)

    # powerplay time-on-ice per game in seconds
    toi_pp_pg_sec = df_agg_stats['toi_pp_sec']/df_agg_stats['games']

    # team powerplay time-on-ice per game in seconds
    team_toi_pp_pg_sec = df_agg_stats['team_toi_pp_sec']/df_agg_stats['games']

    # powerplay goals IPP
    ppg_ipp = np.where(df_agg_stats['ppg_on_ice'] != 0, df_agg_stats['ppg_point'] / df_agg_stats['ppg_on_ice'] * 100, np.nan)
    ppg_ipp = pd.Series(ppg_ipp, index=df_agg_stats.index)

    # get ratio of powerplay time-on-ice vs. team powerplay time-on-ice
    toi_pp_pg_ratio = toi_pp_pg_sec / team_toi_pp_pg_sec * 100

    # convert shorthand time-on-ice seconds to string formatted as mm:ss
    toi_sh_pg_sec = df_agg_stats['toi_sh_sec']/df_agg_stats['games']

    # convert time-on-ice seconds to string formatted as mm:ss
    toi_per_game = df_agg_stats['toi_sec'] / df_agg_stats['games']
    minutes = (toi_per_game / 60).astype(int)
    seconds = (toi_per_game % 60).astype(int)
    toi_pg = minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    # convert time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_pg_ra_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_sec_ra'].astype(int).apply(seconds_to_string_time))
    toi_pg_ra_last = pd.Series(toi_pg_ra_last, index=df_agg_stats.index)

    # convert even time-on-ice seconds to string formatted as mm:ss
    toi_per_game = df_agg_stats['toi_even_sec'] / df_agg_stats['games']
    minutes = (toi_per_game / 60).astype(int)
    seconds = (toi_per_game % 60).astype(int)
    toi_even_pg = minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    # convert even time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_even_pg_ra_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_even_sec_ra'].astype(int).apply(seconds_to_string_time))
    toi_even_pg_ra_last = pd.Series(toi_even_pg_ra_last, index=df_agg_stats.index)

    # convert powerplay time-on-ice seconds to string formatted as mm:ss
    toi_per_game = df_agg_stats['toi_pp_sec'] / df_agg_stats['games']
    minutes = (toi_per_game / 60).astype(int)
    seconds = (toi_per_game % 60).astype(int)
    toi_pp_pg = minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    # convert powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_pp_pg_ra_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_pp_sec_ra'].astype(int).apply(seconds_to_string_time))
    toi_pp_pg_ra_last = pd.Series(toi_pp_pg_ra_last, index=df_agg_stats.index)

    # convert team powerplay time-on-ice seconds to string formatted as mm:ss
    toi_per_game = df_agg_stats['team_toi_pp_sec'] / df_agg_stats['games']
    minutes = (toi_per_game / 60).astype(int)
    seconds = (toi_per_game % 60).astype(int)
    team_toi_pp_pg = minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    # convert team powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    team_toi_pp_pg_ra_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['team_toi_pp_sec_ra'].astype(int).apply(seconds_to_string_time))
    team_toi_pp_pg_ra_last = pd.Series(team_toi_pp_pg_ra_last, index=df_agg_stats.index)

    # calc powerplay goals per 2 penalty minutes
    pp_goals_p120 = (df_agg_stats['goals_pp'] * 120) / df_agg_stats['toi_pp_sec']

    # calc powerplay shots-on-goal per 2 penalty minutes
    pp_sog_p120 = np.where(df_agg_stats['toi_pp_sec'] != 0, (df_agg_stats['shots_powerplay'] * 120) / df_agg_stats['toi_pp_sec'], np.nan)
    pp_sog_p120 = pd.Series(pp_sog_p120, index=df_agg_stats.index)

    # calc powerplay points per 2 penalty minutes
    pp_pts_p120 = np.where(toi_pp_pg == '00:00', np.nan, (df_agg_stats['points_pp'] * 120) / df_agg_stats['toi_pp_sec'])
    pp_pts_p120 = pd.Series(pp_pts_p120, index=df_agg_stats.index)

    # set toi_pp_pg_ratio & team_toi_pp_pg_ra_last & toi_pp_ratio_ra to blank if toi_pp_pg is 0
    toi_pp_pg_ratio = toi_pp_pg_ratio.where(toi_pp_pg != '00:00', '')
    team_toi_pp_pg_ra_last = team_toi_pp_pg_ra_last.where(toi_pp_pg != '00:00', '')
    df_agg_stats['toi_pp_ratio_ra'] = df_agg_stats['toi_pp_ratio_ra'].where(toi_pp_pg != '00:00', '')

    # convert shorthand time-on-ice seconds to string formatted as mm:ss
    toi_per_game = df_agg_stats['toi_sh_sec'] / df_agg_stats['games']
    minutes = (toi_per_game / 60).astype(int)
    seconds = (toi_per_game % 60).astype(int)
    toi_sh_pg = minutes.map('{:02d}'.format) + ':' + seconds.map('{:02d}'.format)

    # convert shorthand time-on-ice seconds rolling-average to string formatted as mm:ss
    toi_sh_pg_ra_last = np.where(df_agg_stats['pos'] == goalie_position_code, '', df_agg_stats['toi_sh_sec_ra'].astype(int).apply(seconds_to_string_time))
    toi_sh_pg_ra_last = pd.Series(toi_sh_pg_ra_last, index=df_agg_stats.index)

    ########################################################################################################
    # trend time-on-ice
    df_sktr = (df.query(skaters_filter)
            .sort_values(['player_id', 'date'], ascending=[True, True])
            .groupby('player_id')
            .filter(lambda x: x['date'].size >= 2)
            .groupby('player_id', group_keys=False))

    polyfit_result = df_sktr['toi_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1])
    minutes = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).div(60)).astype(int)
    seconds = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).mod(60)).astype(int)
    toi_pg_sec_trend = minutes.map('{:+1d}'.format) + ':' + seconds.map('{:02d}'.format)

    polyfit_result = df_sktr['toi_even_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1])
    minutes = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).div(60)).astype(int)
    seconds = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).mod(60)).astype(int)
    toi_even_pg_sec_trend = minutes.map('{:+1d}'.format) + ':' + seconds.map('{:02d}'.format)

    polyfit_result = df_sktr['toi_pp_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1])
    minutes = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).div(60)).astype(int)
    seconds = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).mod(60)).astype(int)
    toi_pp_pg_sec_trend = minutes.map('{:+1d}'.format) + ':' + seconds.map('{:02d}'.format)

    # The following calc seems not quite right, and occasionally gives a trend value such as +161619312102409.5, and not sure this is really helpful information
    def calculate_ratio(x):
        return polyfit(np.arange(0, x.size), x, 1)[1]
    toi_pp_sec_ra_ratio = df_sktr['toi_pp_sec_ra'].apply(calculate_ratio)
    team_toi_pp_sec_ra_ratio = df_sktr['team_toi_pp_sec_ra'].apply(calculate_ratio)
    toi_pp_pg_ratio_trend = toi_pp_sec_ra_ratio / team_toi_pp_sec_ra_ratio

    polyfit_result = df_sktr['toi_sh_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1])
    minutes = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).div(60)).astype(int)
    seconds = (polyfit_result.mul(df_agg_stats['games'], fill_value=0).mod(60)).astype(int)
    toi_sh_pg_sec_trend = minutes.map('{:+1d}'.format) + ':' + seconds.map('{:02d}'.format)

    ########################################################################################################

    # gaa
    gaa = df_agg_stats['goals_against'] / df_agg_stats['toi_sec'] * 3600
    gaa[df_agg_stats['pos'] != goalie_position_code] = np.nan

    # save%
    save_percent = df_agg_stats['saves'] / df_agg_stats['shots_against']

    # set NaN
    df_agg_stats.fillna({'games': 0, 'toi_pg': '', 'toi_even_pg': '', 'toi_pp_pg': '', 'team_toi_pp_pg': '', 'toi_sh_pg': ''}, inplace=True)

    team_games = df_agg_stats['team_id'].apply(lambda x: teams_dict[x]['games'] if pd.notna(x) else np.nan)
    # add column for ratio of games to team games
    percent_of_team_games = df_agg_stats['games'].div(team_games).round(2)

    ########################################################################################################
    df_sktr = df_agg_stats.query(skaters_filter)

    # shooting percentage
    shooting_percent  = df_sktr['goals'].div(df_sktr['shots']).multiply(100).round(1)

    # Corsi For % & Fenwick For %
    corsi_for_percent = df_sktr['corsi_for'].div(df_sktr['corsi_for'] + df_sktr['corsi_against']).multiply(100).round(1)
    fenwick_for_percent = df_sktr['fenwick_for'].div(df_sktr['fenwick_for'] + df_sktr['fenwick_against']).multiply(100).round(1)

    ########################################################################################################

    # goalie starts as percent of team games
    starts_as_percent = df_agg_stats['games_started'].div(team_games).round(2) * 100

    # quality starts as percent of starts
    quality_starts_as_percent = df_agg_stats['quality_starts'].div(df_agg_stats['games_started']).round(3) * 100

    df_agg_stats = df_agg_stats.assign(
        toi_pg_sec = toi_pg_sec,
        toi_even_pg_sec = toi_even_pg_sec,
        evg_ipp = evg_ipp,
        toi_pp_pg_sec = toi_pp_pg_sec,
        team_toi_pp_pg_sec = team_toi_pp_pg_sec,
        ppg_ipp = ppg_ipp,
        toi_pp_pg_ratio = toi_pp_pg_ratio,
        toi_sh_pg_sec = toi_sh_pg_sec,
        toi_pg = toi_pg,
        toi_pg_ra_last = toi_pg_ra_last,
        toi_even_pg = toi_even_pg,
        toi_even_pg_ra_last = toi_even_pg_ra_last,
        toi_pp_pg = toi_pp_pg,
        toi_pp_pg_ra_last = toi_pp_pg_ra_last,
        team_toi_pp_pg = team_toi_pp_pg,
        team_toi_pp_pg_ra_last = team_toi_pp_pg_ra_last,
        pp_goals_p120 = pp_goals_p120,
        pp_sog_p120 = pp_sog_p120,
        pp_pts_p120 = pp_pts_p120,
        toi_sh_pg = toi_sh_pg,
        toi_sh_pg_ra_last = toi_sh_pg_ra_last,
        toi_pg_sec_trend = toi_pg_sec_trend,
        toi_even_pg_sec_trend = toi_even_pg_sec_trend,
        toi_pp_pg_sec_trend = toi_pp_pg_sec_trend,
        toi_pp_pg_ratio_trend = toi_pp_pg_ratio_trend,
        toi_sh_pg_sec_trend =toi_sh_pg_sec_trend,
        gaa = gaa,
        save_percent = save_percent,
        team_games = team_games,
        percent_of_team_games = percent_of_team_games,
        shooting_percent = shooting_percent,
        corsi_for_percent = corsi_for_percent,
        fenwick_for_percent = fenwick_for_percent,
        starts_as_percent = starts_as_percent,
        quality_starts_as_percent = quality_starts_as_percent,
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

def calc_cumulative_z_scores(df: pd.DataFrame):

    try:

        # implement the following to see histograms for scoring category
        # i.e., change 'pts_pg' to desired category
        # data = list(df.query(f'{forwards_filter} and {one_game_minimum_filter} and {z_score_minimum_games_minimum_filter}')['pts_pg'])
        # plt.hist(data)
        # plt.title('Forwards - Points per Game')
        # plt.show()

        # OR

        # implement the following to see histograms for scoring category
        # i.e., change 'pts_pg' to desired category
        # import plotly.express as px
        # fig = px.histogram(df_f, x="pts_pg")
        # fig.show()

        # see https://projectile.pro/how-to-value-players-for-fantasy/ for discussion of Rate Stats, to account for players
        # with low number of games, to determine stat value for "games above average"

        skaters_mask = df.eval(skaters_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        ##########################################################################
        # skaters
        ##########################################################################
        z_goals = (df_sktr['goals'] - mean_cat['sktr goals']) / std_cat['sktr goals']
        z_assists = (df_sktr['assists'] - mean_cat['sktr assists']) / std_cat['sktr assists']
        z_pim = (df_sktr['pim'] - mean_cat['sktr pim']) / std_cat['sktr pim']
        # z_penalties = df_sktr['penalties'].apply(lambda x: ((x - mean_cat['sktr penalties']) / std_cat['sktr penalties']) if std_cat['sktr penalties'] != 0 else np.nan)
        z_penalties = (df_sktr['penalties'] - mean_cat['sktr penalties']) / np.where(std_cat['sktr penalties'] != 0, std_cat['sktr penalties'], np.nan)
        z_shots = (df_sktr['shots'] - mean_cat['sktr shots']) / std_cat['sktr shots']
        z_points_pp = (df_sktr['points_pp'] - mean_cat['sktr points_pp']) / std_cat['sktr points_pp']
        z_hits = (df_sktr['hits'] - mean_cat['sktr hits']) / std_cat['sktr hits']
        z_blocked = (df_sktr['blocked'] - mean_cat['sktr blocked']) / std_cat['sktr blocked']
        z_takeaways = (df_sktr['takeaways'] - mean_cat['sktr takeaways']) / std_cat['sktr takeaways']

        ##########################################################################
        # defense
        ##########################################################################
        z_points = (df_d['points'] - mean_cat['d points']) / std_cat['d points']

        ##########################################################################
        # goalies
        ##########################################################################
        z_wins = (df_g['wins'] - mean_cat['wins']) / std_cat['wins']
        z_saves = (df_g['saves'] - mean_cat['saves']) / std_cat['saves']

        # Remove outliers from 'gaa' column
        df_filtered = df_g.dropna(subset=['gaa'])
        z_gaa = -1 * (df_filtered['gaa'] - df_filtered['gaa'].mean()) / df_filtered['gaa'].std()

        # Remove outliers from 'save%' column
        df_filtered = df_g.dropna(subset=['save%'])
        z_save_pct = (df_filtered['save%'] - df_filtered['save%'].mean()) / df_filtered['save%'].std()

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

        ##########################################################################
        # Overall z-scores
        global cumulative_z_scores
        cumulative_z_scores = calc_summary_z_scores(df=df, points_type='cumulative')
        z_scores = pd.Series(cumulative_z_scores)

        df = df.assign(
            z_score = z_scores['score'],
            z_offense = z_scores['offense'],
            z_peripheral = z_scores['peripheral'],
            z_sog_hits_blk = z_scores['sog_hits_blk'],
            z_hits_blk = z_scores['hits_blk'],
            z_goals_hits_pim = z_scores['goals_hits_pim'],
            z_hits_pim = z_scores['hits_pim'],
            z_g_count = z_scores['g_count'],
            z_g_ratio = z_scores['g_ratio'],
            # calc z-scores are calculated in javascript code
            z_score_calc = '',
            z_offense_calc = '',
            z_peripheral_calc = '',
            z_count_calc = '',
            z_ratio_calc = '',
        )

        z_combos = calc_z_combo(df=df, points_type='cumulative', score_types=['score', 'offense', 'peripheral', 'g_count', 'g_ratio'])

        df = df.assign(
            z_combo = z_combos['score'],
            z_offense_combo = z_combos['offense'],
            z_peripheral_combo = z_combos['peripheral'],
            z_g_count_combo = z_combos['g_count'],
            z_g_ratio_combo = z_combos['g_ratio'],
        )

    except:
        print(f'{traceback.format_exc()} in calc_cumulative_z_scores()')

    return df

def calc_per_60_stats(df: pd.DataFrame):

    try:

        # setting 'toi_sec' to np.nan if 0, to calcualte without 'inf' values
        toi_sec = np.where(df['toi_sec'] == 0, np.nan, df['toi_sec'])

        # skaters
        ##########################################################################
        pts_p60 = df['points'] / df['toi_sec'] * 3600
        g_p60 = df['goals'] / df['toi_sec'] * 3600
        a_p60 = df['assists'] / df['toi_sec'] * 3600
        pim_p60 = df['pim'] / df['toi_sec'] * 3600
        penalties_p60 = df['penalties'] / df['toi_sec'] * 3600
        sog_p60 = df['shots'] / df['toi_sec'] * 3600
        sog_pp_p60 = np.where(df['toi_pp_sec'] > 0, df['shots_powerplay'] / (df['toi_pp_sec'] * 3600), 0)
        ppp_p60 = df['points_pp'] / df['toi_sec'] * 3600
        hits_p60 = df['hits'] / df['toi_sec'] * 3600
        blk_p60 = df['blocked'] / df['toi_sec'] * 3600
        tk_p60 = df['takeaways'] / df['toi_sec'] * 3600

        ##########################################################################
        # goalies
        ##########################################################################
        wins_p60 = df['wins'] / df['toi_sec'] * 3600
        saves_p60 = df['saves'] / df['toi_sec'] * 3600
        gaa_p60 = np.where(df['pos'] == goalie_position_code, df['goals_against'] / df['toi_sec'] * 3600, np.nan)
        save_percent_p60 = (df['saves'] / df['toi_sec'] * 3600) / (df['shots_against'] / df['toi_sec'] * 3600)

        df = df.assign(
            toi_sec = toi_sec,
            pts_p60 = pts_p60,
            g_p60 = g_p60,
            a_p60 = a_p60,
            pim_p60 = pim_p60,
            penalties_p60 = penalties_p60,
            sog_p60 = sog_p60,
            sog_pp_p60 = sog_pp_p60,
            ppp_p60 = ppp_p60,
            hits_p60 = hits_p60,
            blk_p60 = blk_p60,
            tk_p60 = tk_p60,
            wins_p60 = wins_p60,
            saves_p60 = saves_p60,
            gaa_p60 = gaa_p60,
            save_percent_p60 = save_percent_p60,
        )

        df['save%_p60'] = df['save_percent_p60']
        df.drop('save_percent_p60', axis=1, inplace=True)

    except:
        print(f'{traceback.format_exc()} in calc_per_60_stats()')

    return df

def calc_per_60_z_scores(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        ##########################################################################
        # skaters
        ##########################################################################
        z_g_p60 = (df_sktr['g_p60'] - mean_cat['sktr g_p60']) / std_cat['sktr g_p60']
        z_a_p60 = (df_sktr['a_p60'] - mean_cat['sktr a_p60']) / std_cat['sktr a_p60']
        z_pim_p60 = (df_sktr['pim_p60'] - mean_cat['sktr pim_p60']) / std_cat['sktr pim_p60']
        # z_penalties_p60 = df_sktr['penalties_p60'].apply(lambda x: ((x - mean_cat['sktr penalties_p60']) / std_cat['sktr penalties_p60']) if std_cat['sktr penalties_p60'] != 0 else np.nan)
        z_penalties_p60 = (df_sktr['penalties_p60'] - mean_cat['sktr penalties_p60']) / np.where(std_cat['sktr penalties_p60'] != 0, std_cat['sktr penalties_p60'], np.nan)
        z_sog_p60 = (df_sktr['sog_p60'] - mean_cat['sktr sog_p60']) / std_cat['sktr sog_p60']
        z_ppp_p60 = (df_sktr['ppp_p60'] - mean_cat['sktr ppp_p60']) / std_cat['sktr ppp_p60']
        z_hits_p60 = (df_sktr['hits_p60'] - mean_cat['sktr hits_p60']) / std_cat['sktr hits_p60']
        z_blk_p60 = (df_sktr['blk_p60'] - mean_cat['sktr blk_p60']) / std_cat['sktr blk_p60']
        z_tk_p60 = (df_sktr['tk_p60'] - mean_cat['sktr tk_p60']) / std_cat['sktr tk_p60']

        ##########################################################################
        # defense
        ##########################################################################
        z_pts_p60 = (df_d['pts_p60'] - mean_cat['d pts_p60']) / std_cat['d pts_p60']

        ##########################################################################
        # goalies
        ##########################################################################
        z_wins_p60 = (df_g['wins_p60'] - mean_cat['wins_p60']) / std_cat['wins_p60']
        z_saves_p60 = (df_g['saves_p60'] - mean_cat['saves_p60']) / std_cat['saves_p60']

        # Remove outliers from 'gaa_p60' column
        df_filtered = df_g.dropna(subset=['gaa_p60'])
        z_gaa_p60 = -1 * (df_filtered['gaa_p60'] - df_filtered['gaa_p60'].mean()) / df_filtered['gaa_p60'].std()

        # Remove outliers from 'save%_p60' column
        df_filtered = df_g.dropna(subset=['save%_p60'])
        z_save_percent_p60 = (df_filtered['save%_p60'] - df_filtered['save%_p60'].mean()) / df_filtered['save%_p60'].std()

        df = df.assign(
            z_pts_p60 = z_pts_p60,
            z_g_p60 = z_g_p60,
            z_a_p60 = z_a_p60,
            z_pim_p60 = z_pim_p60,
            z_penalties_p60 = z_penalties_p60,
            z_sog_p60 = z_sog_p60,
            z_ppp_p60 = z_ppp_p60,
            z_hits_p60 = z_hits_p60,
            z_blk_p60 = z_blk_p60,
            z_tk_p60 = z_tk_p60,
            z_wins_p60 = z_wins_p60,
            z_saves_p60 = z_saves_p60,
            z_gaa_p60 = z_gaa_p60,
            z_save_percent_p60 = z_save_percent_p60,
        )

        df['z_save%_p60'] = df['z_save_percent_p60']
        df.drop('z_save_percent_p60', axis=1, inplace=True)

        ##########################################################################
        # Overall z-scores
        global per_60_z_scores
        per_60_z_scores = calc_summary_z_scores(df=df, points_type='per 60')
        z_scores = pd.Series(per_60_z_scores)

        df = df.assign(
            z_score_p60 = z_scores['score'],
            z_offense_p60 = z_scores['offense'],
            z_peripheral_p60 = z_scores['peripheral'],
            z_sog_hits_blk_p60 = z_scores['sog_hits_blk'],
            z_hits_blk_p60 = z_scores['hits_blk'],
            z_goals_hits_pim_p60 = z_scores['goals_hits_pim'],
            z_hits_pim_p60 = z_scores['hits_pim'],
            z_g_count_p60 = z_scores['g_count'],
            z_g_ratio_p60 = z_scores['g_ratio'],
            # calc z-scores are calculated in javascript code
            z_score_p60_calc = '',
            z_offense_p60_calc = '',
            z_peripheral_p60_calc = '',
            z_count_p60_calc = '',
            z_ratio_p60_calc = '',
        )

        z_combos = calc_z_combo(df=df, points_type='per 60', score_types=['score', 'offense', 'peripheral', 'g_count', 'g_ratio'])
        df = df.assign(
            z_combo_p60 = z_combos['score'],
            z_offense_combo_p60 = z_combos['offense'],
            z_peripheral_combo_p60 = z_combos['peripheral'],
            z_g_count_combo_p60 = z_combos['g_count'],
            z_g_ratio_combo_p60 = z_combos['g_ratio'],
        )

    except:
        print(f'{traceback.format_exc()} in calc_per_60_z_scores()')

    return df

def calc_per_game_stats(df: pd.DataFrame, df_game_stats: pd.DataFrame):

    try:

        # skaters
        ##########################################################################
        pts_pg = df['points'] / df['games']
        g_pg = df['goals'] / df['games']
        a_pg = df['assists'] / df['games']
        pim_pg = df['pim'] / df['games']
        penalties_pg = df['penalties'] / df['games']
        sog_pg = df['shots'] / df['games']
        sog_pp_pg = df['shots_powerplay'] / df['games']
        ppp_pg = df['points_pp'] / df['games']
        hits_pg = df['hits'] / df['games']
        blk_pg = df['blocked'] / df['games']
        tk_pg = df['takeaways'] / df['games']

        ##########################################################################
        # goalies
        ##########################################################################
        wins_pg = df['wins'] / df['games']
        saves_pg = df['saves'] / df['games']

        df = df.assign(
            pts_pg = pts_pg,
            g_pg = g_pg,
            a_pg = a_pg,
            pim_pg = pim_pg,
            penalties_pg = penalties_pg,
            sog_pg = sog_pg,
            sog_pp_pg = sog_pp_pg,
            ppp_pg = ppp_pg,
            hits_pg = hits_pg,
            blk_pg = blk_pg,
            tk_pg = tk_pg,
            wins_pg = wins_pg,
            saves_pg = saves_pg,
        )

        ###################################################################
        # Calculation of gaa_gp and save%_pg needs to calculate gaa's & save%'s for each game
        # and calc mean
        df.set_index('player_id', inplace=True)
        df_filtered = df_game_stats.query(f'pos==@goalie_position_code')
        df_filtered.set_index('player_id', inplace=True)

        gaa_pg = (df_filtered['goals_against'] / df_filtered['toi_sec'] * 3600).groupby(df_filtered.index).agg('mean')
        save_percent_pg = (df_filtered['saves'] / df_filtered['shots_against']).groupby(df_filtered.index).agg('mean')

        df = df.assign(
            gaa_pg = gaa_pg,
            save_percent_pg = save_percent_pg,
        )

        df['save%_pg'] = df['save_percent_pg']
        df.drop('save_percent_pg', axis=1, inplace=True)

        df.reset_index(inplace=True)

    except:
        print(f'{traceback.format_exc()} in calc_per_game_stats()')

    return df

def calc_per_game_z_scores(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        ##########################################################################
        # skaters
        ##########################################################################
        z_g_pg = (df_sktr['g_pg'] - mean_cat['sktr g_pg']) / std_cat['sktr g_pg']
        z_a_pg = (df_sktr['a_pg'] - mean_cat['sktr a_pg']) / std_cat['sktr a_pg']
        z_pim_pg = (df_sktr['pim_pg'] - mean_cat['sktr pim_pg']) / std_cat['sktr pim_pg']
        # z_penalties_pg = df_sktr['penalties_pg'].apply(lambda x: ((x - mean_cat['sktr penalties_pg']) / std_cat['sktr penalties_pg']) if std_cat['sktr penalties_pg'] != 0 else np.nan)
        z_penalties_pg = (df_sktr['penalties_pg'] - mean_cat['sktr penalties_pg']) / np.where(std_cat['sktr penalties_pg'] != 0, std_cat['sktr penalties_pg'], np.nan)
        z_sog_pg = (df_sktr['sog_pg'] - mean_cat['sktr sog_pg']) / std_cat['sktr sog_pg']
        z_ppp_pg = (df_sktr['ppp_pg'] - mean_cat['sktr ppp_pg']) / std_cat['sktr ppp_pg']
        z_hits_pg = (df_sktr['hits_pg'] - mean_cat['sktr hits_pg']) / std_cat['sktr hits_pg']
        z_blk_pg = (df_sktr['blk_pg'] - mean_cat['sktr blk_pg']) / std_cat['sktr blk_pg']
        z_tk_pg = (df_sktr['tk_pg'] - mean_cat['sktr tk_pg']) / std_cat['sktr tk_pg']

        ##########################################################################
        # defense
        ##########################################################################
        z_pts_pg = (df_d['pts_pg'] - mean_cat['d pts_pg']) / std_cat['d pts_pg']

        ##########################################################################
        # goalies
        ##########################################################################
        z_wins_pg = (df_g['wins_pg'] - mean_cat['wins_pg']) / std_cat['wins_pg']
        z_saves_pg = (df_g['saves_pg'] - mean_cat['saves_pg']) / std_cat['saves_pg']

        # Remove outliers from 'gaa_pg' column
        df_filtered = df_g.dropna(subset=['gaa'])
        z_gaa_pg = -1 * (df_filtered['gaa_pg'] - df_filtered['gaa_pg'].mean()) / df_filtered['gaa_pg'].std()

        # Remove outliers from 'save%_pg' column
        df_filtered = df_g.dropna(subset=['save%_pg'])
        z_save_percent_pg = (df_filtered['save%_pg'] - df_filtered['save%_pg'].mean()) / df_filtered['save%_pg'].std()

        df = df.assign(
            z_pts_pg = z_pts_pg,
            z_g_pg = z_g_pg,
            z_a_pg = z_a_pg,
            z_pim_pg = z_pim_pg,
            z_penalties_pg = z_penalties_pg,
            z_sog_pg = z_sog_pg,
            z_ppp_pg = z_ppp_pg,
            z_hits_pg = z_hits_pg,
            z_blk_pg = z_blk_pg,
            z_tk_pg = z_tk_pg,
            z_wins_pg = z_wins_pg,
            z_saves_pg = z_saves_pg,
            z_gaa_pg = z_gaa_pg,
            z_save_percent_pg = z_save_percent_pg,
        )

        df['z_save%_pg'] = df['z_save_percent_pg']
        df.drop('z_save_percent_pg', axis=1, inplace=True)

        ##########################################################################
        # Overall z-scores
        global per_game_z_scores
        per_game_z_scores = calc_summary_z_scores(df=df, points_type='per game')
        z_scores = pd.Series(per_game_z_scores)

        df = df.assign(
            z_score_pg = z_scores['score'],
            z_offense_pg = z_scores['offense'],
            z_peripheral_pg = z_scores['peripheral'],
            z_sog_hits_blk_pg = z_scores['sog_hits_blk'],
            z_hits_blk_pg = z_scores['hits_blk'],
            z_goals_hits_pim_pg = z_scores['goals_hits_pim'],
            z_hits_pim_pg = z_scores['hits_pim'],
            z_g_count_pg = z_scores['g_count'],
            z_g_ratio_pg = z_scores['g_ratio'],
            # calc z-scores are calculated in javascript code
            z_score_pg_calc = '',
            z_offense_pg_calc = '',
            z_peripheral_pg_calc = '',
            z_count_pg_calc = '',
            z_ratio_pg_calc = '',
        )

        z_combos = calc_z_combo(df=df, points_type='per game', score_types=['score', 'offense', 'peripheral', 'g_count', 'g_ratio'])

        df = df.assign(
            z_combo_pg = z_combos['score'],
            z_offense_combo_pg = z_combos['offense'],
            z_peripheral_combo_pg = z_combos['peripheral'],
            z_g_count_combo_pg = z_combos['g_count'],
            z_g_ratio_combo_pg = z_combos['g_ratio'],
        )

    except:
        print(f'{traceback.format_exc()} in calc_per_game_z_scores()')

    return df

def calc_projected_draft_round(df_player_stats: pd.DataFrame):

        df_player_stats.set_index('player_id', inplace=True)

        # Find potential draft round using average draft position
        df_temp = df_player_stats.query('keeper!="Yes" and adp!=0 and team_abbr!="(N/A)"').sort_values('adp')
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
        # df_player_stats['pdr1'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)
        df_player_stats['pdr1'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 14 else 14)

        # Find potential draft round using Fantrax score
        df_temp = df_player_stats.query('keeper!="Yes" and fantrax_score!=0 and team_abbr!="(N/A)"').sort_values('fantrax_score', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
        # df_player_stats['pdr2'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)
        df_player_stats['pdr2'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 14 else 14)

        # Find potential draft round using z-score
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('z_score', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
        # df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 12 else 12)
        df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 14 else 14)

        # Find potential draft round using z-offense
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('z_offense', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
        # df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 12 else 12)
        df_player_stats['pdr4'] = df_temp.apply(lambda x: x if x <= 14 else 14)

        # Find potential draft round using z-peripheral
        df_temp = df_player_stats.query('keeper!="Yes" and team_abbr!="(N/A)"').sort_values('z_peripheral', ascending=False)
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
        # df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 12 else 12)
        df_player_stats['pdr5'] = df_temp.apply(lambda x: x if x <= 14 else 14)

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
        df_temp = df_temp.groupby(np.arange(len(df_temp.index))//14, axis='index').ngroup() + 1
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

    # see https://stackoverflow.com/questions/23199796/detect-and-exclude-outliers-in-a-pandas-dataframe
    # cols = df.select_dtypes('number').columns  # limits to a (float), b (int) and e (timedelta)
    # df_sub = df.loc[:, cols]
    # OPTION 1: z-score filter: z-score < 3
    # lim = np.abs((df_sub - df_sub.mean()) / df_sub.std(ddof=0)) < 3

    # # OPTION 2: quantile filter: discard 1% upper / lower values
    # lim = np.logical_or(df_sub < df_sub.quantile(0.99, numeric_only=False),
    #                     df_sub > df_sub.quantile(0.01, numeric_only=False))

    # # OPTION 3: iqr filter: within 2.22 IQR (equiv. to z-score < 3)
    # iqr = df_sub.quantile(0.75, numeric_only=False) - df_sub.quantile(0.25, numeric_only=False)
    # lim = np.abs((df_sub - df_sub.median()) / iqr) < 2.22

    # # replace outliers with nan
    # df.loc[:, cols] = df_sub.where(lim, np.nan)

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forwards_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        columns = list(df.columns)
        all_categories = sktr_cumulative_categories + sktr_per_game_categories + sktr_per_60_categories + sktr_cumulative_z_categories + sktr_per_game_z_categories + sktr_per_60_z_categories
        columns_series = pd.Series(list(df.columns))

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
        all_categories = goalie_cumulative_categories + goalie_per_game_categories + goalie_per_60_categories + goalie_cumulative_z_categories + goalie_per_game_z_categories + goalie_per_60_z_categories
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

        # cumulative stats
        #######################################
        # skaters
        for cat in sktr_cumulative_summary_z_scores:
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
        for cat in g_cumulative_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                max_cat[f'g {cat}'] = df_g[cat].max()
            else:
                max_cat[f'g {cat}'] = None

        #######################################
        # per game stats
        #######################################
        # skaters
        for cat in sktr_per_game_summary_z_scores:
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
        for cat in g_per_game_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                max_cat[f'g {cat}'] = df_g[cat].max()
            else:
                max_cat[f'g {cat}'] = None

        #######################################
        # per 60 stats
        #######################################
        # skaters
        for cat in sktr_per_60_summary_z_scores:
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
        for cat in g_per_60_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                max_cat[f'g {cat}'] = df_g[cat].max()
            else:
                max_cat[f'g {cat}'] = None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_maximums()')

    return

def calc_scoring_category_minimums(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forwards_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_cumulative_categories + sktr_per_game_categories + sktr_per_60_categories + sktr_cumulative_z_categories + sktr_per_game_z_categories + sktr_per_60_z_categories
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
        min_cat[f'sktr sog_pp_pg'] = df_sktr['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None
        min_cat[f'sktr sog_pp_p60'] = df_sktr['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[f'f {cat}'] = df_f[cat].min()
            else:
                min_cat[f'f {cat}'] = None

        # also...
        min_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].min() if 'shots_powerplay' in columns else None
        min_cat[f'f sog_pp_pg'] = df_f['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None
        min_cat[f'f sog_pp_p60'] = df_f['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                min_cat[f'd {cat}'] = df_d[cat].min()
            else:
                min_cat[f'd {cat}'] = None

        # also...
        min_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].min() if 'shots_powerplay' in columns else None
        min_cat[f'd sog_pp_pg'] = df_d['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None
        min_cat[f'd sog_pp_p60'] = df_d['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_cumulative_categories + goalie_per_game_categories + goalie_per_60_categories + goalie_cumulative_z_categories + goalie_per_game_z_categories + goalie_per_60_z_categories
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

        # cumulative stats
        # skaters
        for cat in sktr_cumulative_summary_z_scores:
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
        for cat in g_cumulative_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                min_cat[f'g {cat}'] = df_g[cat].min()
            else:
                min_cat[f'g {cat}'] = None

        # per game stats
        # skaters
        for cat in sktr_per_game_summary_z_scores:
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
        for cat in g_per_game_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                min_cat[f'g {cat}'] = df_g[cat].min()
            else:
                min_cat[f'g {cat}'] = None

        # per 60 stats
        # skaters
        for cat in sktr_per_60_summary_z_scores:
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
        for cat in g_per_60_summary_z_scores:
            if columns_series_g.isin([cat]).any():
                min_cat[f'g {cat}'] = df_g[cat].min()
            else:
                min_cat[f'g {cat}'] = None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_minimums()')

    return

def calc_scoring_category_means(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forwards_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_cumulative_categories + sktr_per_game_categories + sktr_per_60_categories
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
        mean_cat[f'sktr sog_pp_pg'] = df_sktr['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'sktr penalties_pg'] = df_sktr['penalties_pg'].mean() if 'penalties_pg' in columns else None
        mean_cat[f'sktr sog_pp_p60'] = df_sktr['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'sktr penalties_p60'] = df_sktr['penalties_p60'].mean() if 'penalties_p60' in columns else None

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
        mean_cat[f'f sog_pp_pg'] = df_f['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'f penalties_pg'] = df_f['penalties_pg'].mean() if 'penalties_pg' in columns else None
        mean_cat[f'f sog_pp_p60'] = df_f['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'f penalties_p60'] = df_f['penalties_p60'].mean() if 'penalties_p60' in columns else None

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
        mean_cat[f'd sog_pp_pg'] = df_d['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'd penalties_pg'] = df_d['penalties_pg'].mean() if 'penalties_pg' in columns else None
        mean_cat[f'd sog_pp_p60'] = df_d['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'd penalties_p60'] = df_d['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_cumulative_categories + goalie_per_game_categories + goalie_per_60_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                mean_cat[cat] = df_g[cat].mean()
            else:
                mean_cat[cat] = None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_means()')

    return

def calc_scoring_category_std_deviations(df: pd.DataFrame):

    try:

        skaters_mask = df.eval(skaters_filter)
        forwards_mask = df.eval(forwards_filter)
        defense_mask = df.eval(defense_filter)
        goalie_mask = df.eval(goalie_filter)
        minimum_one_game_mask = df.eval(minimum_one_game_filter)

        df_sktr = df.loc[skaters_mask & minimum_one_game_mask]
        df_f = df.loc[forwards_mask & minimum_one_game_mask]
        df_d = df.loc[defense_mask & minimum_one_game_mask]
        df_g = df.loc[goalie_mask & minimum_one_game_mask]

        # get list of dataframe columns
        columns = list(df.columns)
        all_categories = sktr_cumulative_categories + sktr_per_game_categories + sktr_per_60_categories
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
        std_cat[f'sktr penalties_pg'] = df_sktr['penalties_pg'].std() if 'penalties_pg' in columns else None
        std_cat[f'sktr penalties_p60'] = df_sktr['penalties_p60'].std() if 'penalties_p60' in columns else None

        #######################################
        # Forwards
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[f'f {cat}'] = df_f[cat].std()
            else:
                std_cat[f'f {cat}'] = None

        # also...
        std_cat[f'f penalties'] = df_f['penalties'].std() if 'penalties' in columns else None
        std_cat[f'f penalties_pg'] = df_f['penalties_pg'].std() if 'penalties_pg' in columns else None
        std_cat[f'f penalties_p60'] = df_f['penalties_p60'].std() if 'penalties_p60' in columns else None

        #######################################
        # Defense
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[f'd {cat}'] = df_d[cat].std()
            else:
                std_cat[f'd {cat}'] = None

        # also...
        std_cat[f'd penalties'] = df_d['penalties'].std() if 'penalties' in columns else None
        std_cat[f'd penalties_pg'] = df_d['penalties_pg'].std() if 'penalties_pg' in columns else None
        std_cat[f'd penalties_p60'] = df_d['penalties_p60'].std() if 'penalties_p60' in columns else None

        #######################################
        # Goalies
        all_categories = goalie_cumulative_categories + goalie_per_game_categories + goalie_per_60_categories
        for cat in all_categories:
            if columns_series.isin([cat]).any():
                std_cat[cat] = df_g[cat].std()
            else:
                std_cat[cat] = None

        # also need goals_against, used when calculating gaa z-scores
        std_cat['goals_against'] = df_g['goals_against'].std()

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_std_deviations()')

    return

def calc_player_ages(df: pd.DataFrame) -> pd.Series:

    # calculate player's current age
    # if there are no stats, the following has problem. So do't do it if there are now rows in df_player_stats
    if len(df.index) == 0:
        ages = np.nan
    else:
        ages = df['birth_date'].where(df['birth_date'].notna() & (df['birth_date'] != ''), np.nan).apply(calculate_age)

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

        # player may not be in df
        missing_indexes = sktr_prj[~sktr_prj.index.isin(df.index)].index
        df_missing_skaters = pd.DataFrame(columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
        if len(missing_indexes) > 0:
            for player_id in missing_indexes:
                player = sktr_prj_all.loc[player_id]
                df_player = pd.DataFrame(data=[[season_id, player_id, player["Player"], player["Pos"], player["Team"]]], columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
                df_missing_skaters = pd.concat([df_missing_skaters, df_player])

        # player may not be in df
        missing_indexes = goalie_prj[~goalie_prj.index.isin(df.index)].index
        df_missing_goalies = pd.DataFrame(columns=["seasonID", "player_id", "name", "pos", "team_abbr"])
        if len(missing_indexes) > 0:
            for player_id in missing_indexes:
                player = goalie_prj_all.loc[player_id]
                df_player = pd.DataFrame(data={'seasonID': season_id, 'player_id': player_id, 'name': player['Player'], 'pos': player['Pos'], 'team_abbr': player['Team']})
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
            percent_of_team_games = lambda x: x['games'].fillna(0).div(x['team_games']).round(2)
        )

        # Replace the values in the 'save%' column with the values in the 'save_percent' column
        df['save%'] = df['save_percent']
        # Discard the 'save_percent' column
        df.drop('save_percent', axis=1, inplace=True)

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
        print(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))

    return df

def calc_summary_z_scores(df: pd.DataFrame, points_type: str='cumulative') -> pd.DataFrame:

    sktr_score_types = ['score', 'offense', 'peripheral', 'sog_hits_blk', 'hits_blk', 'goals_hits_pim', 'hits_pim']
    g_score_types = ['score', 'g_count', 'g_ratio']
    # Concatenate the lists
    score_types = sktr_score_types + g_score_types
    # Use a list comprehension to remove duplicates while preserving order
    score_types = [item for index, item in enumerate(score_types) if score_types.index(item) == index]

    if points_type == 'cumulative':
        g_count_cats = ['wins', 'saves']
        g_ratio_gaa = ['gaa']
        g_ratio_save_pc = ['save%']
        sktr_hits_blk_cats = ['hits', 'blocked']
        sktr_sog_hits_blk_cats = ['shots'] + sktr_hits_blk_cats
        sktr_goals_hits_pim_cats = ['goals', 'hits', 'pim']
        sktr_hits_pim_cats = ['hits', 'pim']
        sktr_offense_cats = ['goals', 'assists', 'shots', 'points_pp']
        sktr_periph_cats = ['hits', 'blocked', 'pim', 'takeaways']
        d_only_cats = ['points']

    elif points_type == 'per game':
        g_count_cats = ['wins_pg', 'saves_pg']
        g_ratio_gaa = ['gaa_pg']
        g_ratio_save_pc = ['save%_pg']
        sktr_hits_blk_cats = ['hits_pg', 'blk_pg']
        sktr_sog_hits_blk_cats = ['sog_pg'] + sktr_hits_blk_cats
        sktr_goals_hits_pim_cats = ['g_pg', 'hits_pg', 'pim_pg']
        sktr_hits_pim_cats = ['hits_pg', 'pim_pg']
        sktr_offense_cats = ['g_pg', 'a_pg', 'sog_pg', 'ppp_pg']
        sktr_periph_cats = ['hits_pg', 'blk_pg', 'pim_pg', 'tk_pg']
        d_only_cats = ['pts_pg']

    elif points_type == 'per 60':
        g_count_cats = ['wins_p60', 'saves_p60']
        g_ratio_gaa = ['gaa_p60']
        g_ratio_save_pc = ['save%_p60']
        sktr_hits_blk_cats = ['hits_p60', 'blk_p60']
        sktr_sog_hits_blk_cats = ['sog_p60'] + sktr_hits_blk_cats
        sktr_goals_hits_pim_cats = ['g_p60', 'hits_p60', 'pim_p60']
        sktr_hits_pim_cats = ['hits_p60', 'pim_p60']
        sktr_offense_cats = ['g_p60', 'a_p60', 'sog_p60', 'ppp_p60']
        sktr_periph_cats = ['hits_p60', 'blk_p60', 'pim_p60', 'tk_p60']
        d_only_cats = ['pts_p60']

    sktr_cats = sktr_offense_cats + sktr_periph_cats
    d_offense_cats = d_only_cats + sktr_offense_cats
    d_cats = d_only_cats + sktr_cats
    g_ratio_cats = g_ratio_gaa + g_ratio_save_pc
    g_cats = g_count_cats + g_ratio_cats

    mask_d = df.eval(defense_filter)
    mask_g = df.eval(goalie_filter)
    mask_f = df.eval(forwards_filter)
    mask_sktr = df.eval(skaters_filter)
    minimum_one_game_mask = df.eval(minimum_one_game_filter)

    std_sktr_cats = df.loc[mask_sktr & minimum_one_game_mask, sktr_cats].std()
    std_d_cats = pd.concat([df.loc[mask_d & minimum_one_game_mask, d_only_cats].std(), std_sktr_cats])
    std_g_cats = df.loc[mask_g & minimum_one_game_mask, g_cats].std()

    scores = {}
    scores['player_id'] = df['player_id']

    d_cat_scores = df.loc[mask_d & minimum_one_game_mask, d_cats] / std_d_cats[d_cats]
    f_cat_scores = df.loc[mask_f & minimum_one_game_mask, sktr_cats] / std_sktr_cats[sktr_cats]
    g_cat_scores = pd.concat([df.loc[mask_g & minimum_one_game_mask, g_count_cats] / std_g_cats[g_count_cats], -1 * ((df.loc[mask_g & minimum_one_game_mask, g_ratio_gaa] - 3.00) / std_g_cats[g_ratio_gaa]), (df.loc[mask_g & minimum_one_game_mask, g_ratio_save_pc] - 0.900) / std_g_cats[g_ratio_save_pc]], axis=1)

    # for cat in d_cat_scores:
    #     scores[cat] = round(d_cat_scores[cat], 2)
    # for cat in f_cat_scores:
    #     scores[cat] =  pd.concat([scores[cat], f_cat_scores[cat]]).round(2)
    # for cat in g_cat_scores:
    #     scores[cat] =  round(g_cat_scores[cat], 2)

    for score_type in score_types:

        if score_type == 'peripheral':
            d_only_cats = []
            sktr_cats = sktr_periph_cats
        elif score_type == 'offense':
            sktr_cats = sktr_offense_cats
        elif score_type == 'sog_hits_blk':
            d_only_cats = []
            sktr_cats = sktr_sog_hits_blk_cats
        elif score_type == 'hits_blk':
            d_only_cats = []
            sktr_cats = sktr_hits_blk_cats
        elif score_type == 'goals_hits_pim':
            d_only_cats = []
            sktr_cats = sktr_goals_hits_pim_cats
        elif score_type == 'hits_pim':
            d_only_cats = []
            sktr_cats = sktr_hits_pim_cats
        elif score_type == 'g_count':
            g_cats = g_count_cats
        elif score_type == 'g_ratio':
            g_cats = g_ratio_cats

        d_cats = d_only_cats + sktr_cats

        if score_type in sktr_score_types:
            d_scores = d_cat_scores[d_cats].sum(axis=1)
            # # Rank as a percentage of the maximum value
            # d_scores = round((d_scores / d_scores.max()) * 100, 0)

            f_scores = f_cat_scores[sktr_cats].sum(axis=1)
            # # Rank as a percentage of the maximum value
            # f_scores = round((f_scores / f_scores.max()) * 100, 0)

            if score_type != 'score':
                sktr_scores = pd.concat([d_scores, f_scores])
                # Rank as a percentage of the maximum value
                scores[score_type] = round((sktr_scores / sktr_scores.max()) * 100, 0)

        if score_type in g_score_types:
            g_scores = g_cat_scores[g_cats].sum(axis=1)
            # don't want negative g_scores
            g_scores_min = g_scores.min()
            if g_scores_min < 0:
                g_scores += abs(g_scores_min)

            if score_type != 'score':
                # Rank as a percentage of the maximum value
                scores[score_type] = round((g_scores / g_scores.max()) * 100, 0)

        if score_type == 'score':
            score_scores = pd.concat([d_scores, f_scores, g_scores])
            scores[score_type] = round((score_scores / score_scores.max()) * 100, 0)

        if score_type == 'score':
            prefix = 'z_'
        elif score_type in sktr_score_types:
            prefix = 'sktr z_'
        elif score_type in g_score_types:
            prefix = 'g z_'

        if points_type == 'cumulative':
            suffix = ''
        elif points_type == 'per game':
            suffix = '_pg'
        elif points_type == 'per 60':
            suffix = '_p60'

        min_cat[f'{prefix}{score_type}{suffix}'] = scores[score_type].min()
        max_cat[f'{prefix}{score_type}{suffix}'] = scores[score_type].max()
        mean_cat[f'{prefix}{score_type}{suffix}'] = scores[score_type].mean()

    return scores

def calc_z_combo(df: pd.DataFrame, points_type: str='cumulative', score_types: List[str]=['score']) -> pd.Series:

    # overall rank, based on Fantrax categories
    if points_type == 'cumulative':
        g_categories_count = ['z_wins', 'z_saves']
        g_categories_ratio = ['z_gaa', 'z_save%']
        g_categories = g_categories_count + g_categories_ratio
        f_offense_categories = ['z_goals', 'z_assists', 'z_shots', 'z_points_pp']
        d_offense_categories = ['z_points'] + f_offense_categories
        sktr_peripheral_categories = ['z_hits', 'z_blocked', 'z_takeaways', 'z_pim']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = d_offense_categories + sktr_peripheral_categories
    elif points_type == 'per game':
        g_categories_count = ['z_wins_pg', 'z_saves_pg']
        g_categories_ratio = ['z_gaa_pg', 'z_save%_pg']
        g_categories = g_categories_count + g_categories_ratio
        f_offense_categories = ['z_g_pg', 'z_a_pg', 'z_sog_pg', 'z_ppp_pg']
        d_offense_categories = ['z_pts_pg'] + f_offense_categories
        sktr_peripheral_categories = ['z_hits_pg', 'z_blk_pg', 'z_tk_pg', 'z_pim_pg']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = d_offense_categories + sktr_peripheral_categories
    elif points_type == 'per 60':
        g_categories_count = ['z_wins_p60', 'z_saves_p60']
        g_categories_ratio = ['z_gaa_p60', 'z_save%_p60']
        g_categories = g_categories_count + g_categories_ratio
        f_offense_categories = ['z_g_p60', 'z_a_p60', 'z_sog_p60', 'z_ppp_p60']
        d_offense_categories = ['z_pts_p60'] + f_offense_categories
        sktr_peripheral_categories = ['z_hits_p60', 'z_blk_p60', 'z_tk_p60', 'z_pim_p60']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = d_offense_categories + sktr_peripheral_categories

    # create views for player positions
    forwards_mask = df.eval(forwards_filter)
    defense_mask = df.eval(defense_filter)
    goalie_mask = df.eval(goalie_filter)
    minimum_one_game_mask = df.eval(minimum_one_game_filter)

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

def get_game_stats(season_or_date_radios: str, from_season_id: str, to_season_id: str, from_date: str, to_date: str, pool_id: str, game_type: str='R') -> pd.DataFrame:

    try:

        if season_or_date_radios == 'date':
            sql = textwrap.dedent(f'''\
                select *
                from PlayerGameStats pgs
                where pgs.date between '{from_date}' and '{to_date}' and pgs.game_type == '{game_type}'
            ''')
        else: #  season_or_date_radios == 'season'
            if from_season_id != to_season_id:
                sql = textwrap.dedent(f'''\
                    select *
                    from PlayerGameStats pgs
                    where pgs.seasonID between {from_season_id} and {to_season_id} and pgs.game_type == '{game_type}'
                ''')
            else:
                sql = textwrap.dedent(f'''\
                    select *
                    from PlayerGameStats pgs
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

        # calc 3-game toi rolling averages
        toi_sec_ra = df_game_stats.groupby('player_id')['toi_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        toi_even_sec_ra = df_game_stats.groupby('player_id')['toi_even_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        toi_pp_sec_ra = df_game_stats.groupby('player_id')['toi_pp_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        team_toi_pp_sec_ra = df_game_stats.groupby('player_id')['team_toi_pp_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        toi_pp_ratio_ra = toi_pp_sec_ra / team_toi_pp_sec_ra * 100
        toi_sh_sec_ra = df_game_stats.groupby('player_id')['toi_sh_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())

        # calc really bad start
        # When a goalie has a save percentage in a game less than 85%
        conditions = [
            (df_game_stats['save%'].round(1) < 85.0) & (df_game_stats['pos'] == goalie_position_code) & (df_game_stats['games_started'] == 1),
            (df_game_stats['pos'] == goalie_position_code) & (df_game_stats['games_started'] == 1)
        ]
        choices = [1, 0]
        really_bad_starts = np.select(conditions, choices, default=np.nan)

        df_game_stats = df_game_stats.assign(
            toi_sec_ra = toi_sec_ra,
            toi_even_sec_ra = toi_even_sec_ra,
            toi_pp_sec_ra = toi_pp_sec_ra,
            team_toi_pp_sec_ra = team_toi_pp_sec_ra,
            toi_pp_ratio_ra = toi_pp_ratio_ra,
            toi_sh_sec_ra = toi_sh_sec_ra,
            really_bad_starts = really_bad_starts,
        )

    except:
        print(f'{traceback.format_exc()}')

    return df_game_stats

def get_columns_by_attribute(config: Dict, attribute: str) -> List[str]:

    initially_hidden_column_names = [x['title'] for x in config['columns'] if x.get(attribute)]

    return initially_hidden_column_names

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

def get_search_builder_columns(config: Dict) -> List[str]:

    search_builder_columns = sorted(x['alias'] for x in config['columns'] if x.get('search_builder') and x.get('search_builder') == True)

    return search_builder_columns

def get_stat_type_columns(config: Dict, stat_type: str, alias: bool=False) -> List[str]:

    if alias:
        stat_type_columns = [x.get('alias', x['title']) for x in config['columns'] if not x.get('stat_type') or stat_type in x['stat_type']]
    else:
        stat_type_columns = [x['title'] for x in config['columns'] if not x.get('stat_type') or stat_type in x['stat_type']]

    return stat_type_columns

def get_z_score_category_columns(config: Dict, position: str='skater') -> List[str]:

    z_score_category_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and f'{position}_z_score_cat' in x.get('data_group'))

    return z_score_category_columns

def get_z_score_summary_columns(config: Dict, position: str='skater') -> List[str]:

    z_score_category_columns = sorted(x['title'] for x in config['columns'] if x.get('data_group') and f'{position}_z_score_sum' in x.get('data_group'))

    return z_score_category_columns

def insert_fantrax_columns(df: pd.DataFrame, game_type: str='R'):

    try:

        dfFantraxPlayerInfo = pd.read_sql(sql='select * from FantraxPlayerInfo', con=get_db_connection())

        # set indexes to player_id
        df.set_index('player_id', inplace=True)
        dfFantraxPlayerInfo.set_index('player_id', inplace=True)

        # dfFantraxPlayerInfo seems to have duplicates, so drop duplicates
        dfFantraxPlayerInfo = dfFantraxPlayerInfo[~dfFantraxPlayerInfo.index.duplicated()]

        fantrax_score = dfFantraxPlayerInfo['score']
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
            rookie = rookie,
            minors = minors,
            watch_list = watch_list,
            next_opp = next_opp,
        )

        # some players in df, but not in dfFantraxPlayerInfo, can have np.nan values
        df.fillna({'fantrax_score': 0, 'rookie': '', 'minors': '', 'watch_list': '', 'next_opp': ''}, inplace=True)

        # reset index to indexes being list of row integers
        df.reset_index(inplace=True)

    except:
        print(f'{traceback.format_exc()} in insert_fantrax_columns()')

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
        where_clause = 'where tr.seasonID=? and (p.roster_status!="N" or pool_team>=1)'

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
                primary_position = j.search('people[0].primaryPosition.abbreviation', requests.get(f'{NHL_API_URL}/people/{player_id}').json())
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

    # # Reorder the columns in the DataFrame
    # columns = [col for col in df.columns if col not in ['poolteam_id', 'pool_team', 'status']] + ['poolteam_id', 'pool_team', 'status']
    # df = df.reindex(columns=columns)

    # breakout threshold
    # calculate age
    # a player's nhl team roster status, if not blank, will be one of 'Y' = active roster (e.g., 23 man roster), 'N' = full roster, not active roster, 'I' = IR
    # change active status from 1 to Y
    df = df.reset_index(drop=True)
    df = df.assign(
        keeper=lambda x: np.where(x['keeper'] == 'y', 'Yes', ''),
        age=calc_player_ages(df=df),
        # Reset the index of the resulting Series and assign it to the 'breakout_threshold' column of the df DataFrame
        breakout_threshold=calc_player_breakout_threshold(df=df).reset_index(drop=True),
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

    # # reposition player_id
    # df_stats['player_id'] = df_stats.pop('player_id')

    return df_stats

def rankings_to_html(df: pd.DataFrame, config: Dict, stat_type: str='Cumulative') -> dict:

    try:

        # set nan to 0 for numeric columns
        cols_to_fill = ['last game', 'first game', 'game today']
        df[cols_to_fill] = df[cols_to_fill].fillna('')

        # Flask’s jsonify function does not handle np.nan values
        # replace all np.nan values in your data with None before passing it to the jsonify functio
        df = df.replace(to_replace=np.nan, value=None)

        # format columns before writing to json
        col_formats = get_config_column_formats(config=config)
        cols_to_format = list(set(df.columns) & set(col_formats.keys()))
        df[cols_to_format] = df[cols_to_format].apply(lambda x: x.map(col_formats[x.name]))

        # get stat type column titles
        cumulative_column_titles = get_stat_type_columns(config=config, stat_type='Cumulative')
        per_game_column_titles = get_stat_type_columns(config=config, stat_type='Per game')
        per_60_column_titles = get_stat_type_columns(config=config, stat_type='Per 60 minutes')

        # output stats to json
        if stat_type == 'Cumulative':
            df_temp = df[cumulative_column_titles].copy(deep=True)
        elif stat_type == 'Per game':
            df_temp = df[per_game_column_titles].copy(deep=True)
        elif stat_type == 'Per 60 minutes':
            df_temp = df[per_60_column_titles].copy(deep=True)

        cumulative_stats_data = df[cumulative_column_titles].values.tolist()
        per_game_stats_data = df[per_game_column_titles].values.tolist()
        per_60_stats_data = df[per_60_column_titles].values.tolist()

        # get stat type column titles
        cumulative_column_title_aliases = get_stat_type_columns(config=config, stat_type='Cumulative', alias=True)
        per_game_column_title_aliases = get_stat_type_columns(config=config, stat_type='Per game', alias=True)
        per_60_column_title_aliases = get_stat_type_columns(config=config, stat_type='Per 60 minutes', alias=True)

        # rename df_temp column titles to aliases
        if stat_type == 'Per game':
            columns = {f'{title}': f'{alias}' for (title, alias) in zip(per_game_column_titles, per_game_column_title_aliases)}
            df_temp.rename(columns=columns, inplace=True)
        elif stat_type == 'Per 60 minutes':
            columns = {f'{title}': f'{alias}' for (title, alias) in zip(per_60_column_titles, per_60_column_title_aliases)}
            df_temp.rename(columns=columns, inplace=True)

        # cols_to_sort_numeric = [df_temp.columns.get_loc(x) for x in list(df_temp.select_dtypes([np.int,np.float,np.int64,np.float64]).columns) if x in df_temp.columns]
        cols_to_sort_descending = [df_temp.columns.get_loc(x) for x in get_config_default_sort_order_columns(config=config) if x in df_temp.columns]

        # create a dictionary that maps column names to their formatted names
        column_name_map = {x: f'{x.replace(" ","_")}:name' for x in df_temp.columns}
        # create the lists of column names using the dictionary
        general_info_column_names = [column_name_map[x] for x in get_general_info_columns(config=config) if x in df_temp.columns]
        cumulative_stat_column_names = [column_name_map[x] for x in get_stat_type_columns(config=config, stat_type='Cumulative', alias=True) if x in df_temp.columns]
        per_game_stat_column_names = [column_name_map[x] for x in get_stat_type_columns(config=config, stat_type='Per game', alias=True) if x in df_temp.columns]
        per_60_stat_column_names = [column_name_map[x] for x in get_stat_type_columns(config=config, stat_type='Per 60 minutes', alias=True) if x in df_temp.columns]
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

        max_cat_dict = process_dict(max_cat)
        min_cat_dict = process_dict(min_cat)
        mean_cat_dict = process_dict(mean_cat)
        std_cat_dict = process_dict(std_cat)

        cumulative_z_scores_dict = process_dict(cumulative_z_scores)
        per_game_z_scores_dict = process_dict(per_game_z_scores)
        per_60_z_scores_dict = process_dict(per_60_z_scores)

        # create a dictionary to hold variables to use in jquery datatable
        data_dict = {
            'cumulative_stats_data': cumulative_stats_data,
            'per_game_stats_data': per_game_stats_data,
            'per_60_stats_data': per_60_stats_data,
            'cumulative_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in cumulative_column_titles],
            'per_game_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in per_game_column_titles],
            'per_60_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in per_60_column_titles],
            # 'numeric_columns': cols_to_sort_numeric,
            'descending_columns': cols_to_sort_descending,
            'general_info_column_names': general_info_column_names,
            'sktr_info_column_names': sktr_info_column_names,
            'goalie_info_column_names': goalie_info_column_names,
            'cumulative_stat_column_names': cumulative_stat_column_names,
            'per_game_stat_column_names': per_game_stat_column_names,
            'per_60_stat_column_names': per_60_stat_column_names,
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
            'cumulative_z_scores_dict': cumulative_z_scores_dict,
            'per_game_z_scores_dict': per_game_z_scores_dict,
            'per_60_z_scores_dict': per_60_z_scores_dict,
        }

    except:
        print(f'{traceback.format_exc()} in rankings_to_html()')

    # return the JSON object as a response to the frontend
    return data_dict

def rank_players(season_or_date_radios: str, from_season_id: str, to_season_id: str, from_date: str, to_date: str, pool_id: str, game_type: str='R', stat_type: str='Cumulative', projection_source: str='') -> dict:

    if game_type == 'R':
        season_type = 'Regular Season'
    elif game_type == 'P':
        season_type = 'Playoffs'
    else: # game_type == 'Prj'
        season_type = 'Projected Season'

    global timeframe
    timeframe =  season_type

    # add team games played for each player
    # Get teams to save in dictionary
    global teams_dict
    if from_season_id == to_season_id:
        df_teams = pd.read_sql(f'select team_id, games from TeamStats where seasonID={from_season_id} and game_type="{game_type}"', con=get_db_connection())
    else:
        df_teams = pd.read_sql(f'select team_id, sum(games) as games from TeamStats where seasonID between {from_season_id} and {to_season_id} and game_type="{game_type}" group by team_id', con=get_db_connection())
    teams_dict = {x.team_id: {'games': x.games} for x in df_teams.itertuples()}

    if season_type == 'Projected Season':
        df_player_stats = calc_player_projected_stats(current_season_stats=True, season_id=from_season_id, projection_source=projection_source)
    else:
        #######################################################################################
        #######################################################################################
        # generate games statitics

        if season_or_date_radios == 'date':
            df_game_stats = get_game_stats(season_or_date_radios=season_or_date_radios, from_season_id=from_season_id, to_season_id=to_season_id, from_date=from_date, to_date=to_date, pool_id=pool_id, game_type=game_type)
        else: #  season_or_date_radios == 'season'
            df_game_stats = get_game_stats(season_or_date_radios=season_or_date_radios, from_season_id=from_season_id, to_season_id=to_season_id, from_date=from_date, to_date=to_date, pool_id=pool_id, game_type=game_type)

        #######################################################################################
        # aggregate per game stats per player
        df_player_stats = aggregate_game_stats(df=df_game_stats)

    # merge with current player info
    df_player_stats = merge_with_current_players_info(season_id=to_season_id, pool_id=pool_id, df_stats=df_player_stats, game_type=game_type)

    # add fantrax "score" & "minors" columns
    df_player_stats = insert_fantrax_columns(df=df_player_stats, game_type=game_type)

    # no need for per game & per 60 stats for season projections
    if game_type in ('R', 'P'):
        # need to add these columns after the stats have been partitioned
        # per-game stats
        df_player_stats = calc_per_game_stats(df=df_player_stats, df_game_stats=df_game_stats)
        # per-60 stats
        df_player_stats = calc_per_60_stats(df=df_player_stats)

    # calc global mean and std dev for z-score calculations
    calc_scoring_category_means(df=df_player_stats)
    calc_scoring_category_std_deviations(df=df_player_stats)

    # z-scores
    df_player_stats = calc_cumulative_z_scores(df=df_player_stats)
    # no need for per game & per 60 z-scores for season projections
    if game_type in ('R', 'P'):
        df_player_stats = calc_per_game_z_scores(df=df_player_stats)
        df_player_stats = calc_per_60_z_scores(df=df_player_stats)

    # calc global minumums & maximums
    calc_scoring_category_minimums(df=df_player_stats)
    calc_scoring_category_maximums(df=df_player_stats)

    # if show_draft_list_info:
    df_player_stats = add_draft_list_columns_to_df(season_id=to_season_id, df=df_player_stats)

    # if pre_draft_keeper columns:
    add_pre_draft_keeper_list_column_to_df(season_id=to_season_id, df=df_player_stats)

    # drop rows for irrelevant players; e.g., no games played, projected games, or not on a pool team or not on my watchlist
    if game_type == 'Prj':
        # drop players when projections are used the projected games !> 0
        df_player_stats.query('(games.notna() and games>=1) or watch_list=="Yes"', inplace=True)
    else:
        # drop players in minors and not on active nhl team roster, and not on a pool team and , when projections are used the projected games !> 0
        df_player_stats.query('(games>=1 and games.notna() and minors=="" and nhl_roster_status=="y") or (poolteam_id!="" and poolteam_id.notna()) or watch_list=="Yes" or (line.notna() and line!="") or (pp_line.notna() and pp_line!="")', inplace=True)

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

        # # ensure manager column is empty, and not None, for available players
        # df_stats['pool_team'] = df_stats['pool_team'].apply(lambda x: '' if x is None or pd.isna(x) else x)

    except:
        print(f'{traceback.format_exc()} in rank_players()')

    if len(df_stats.index) == 0:
        print('There are no players to list.')

    df_k = df_stats.copy(deep=True)

    # if stat_type == 'Cumulative':
    #     sort_columns = ['z_score_pg', 'z_score_p60', 'z_score']
    # elif stat_type == 'Per game':
    #     sort_columns = ['z_score_p60', 'z_score', 'z_score_pg']
    # elif stat_type == 'Per 60 minutes':
    #     sort_columns = ['z_score', 'z_score_pg', 'z_score_p60']
    # for sort_column in sort_columns:
    #     df_k.sort_values([sort_column], ascending=[False], inplace=True)
    #     df_k[f'{sort_column}_rank'] = df_k[sort_column].rank(method='min', na_option='bottom', ascending=False)

    # sort_column = sort_columns[-1]

    # rank will renumber based on the rows currently displayed in datatable
    # df_k['rank'] = df_k[sort_column].rank(method='min', na_option='bottom', ascending=False)
    df_k['rank'] = df_k['z_score'].rank(method='min', na_option='bottom', ascending=False)

    config = stats_config(position='all')
    column_headings = get_config_column_headings(config=config)
    df_k.rename(columns=column_headings, inplace=True)
    df_k = df_k.reindex(columns=[v for v in column_headings.values()])

    column_formats = get_config_column_formats(config=config)
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

    # Create a mask to select rows where the 'team id' column is not NaN, not an empty string, and not 0
    mask = ~df_k['team id'].isin([np.nan, '', 0])

    # Use the mask to format the 'team id' column as a string with no decimal places
    df_k.loc[mask, 'team id'] = df_k.loc[mask, 'team id'].astype(int).astype(str)

    # Use the where method to create a new column 'team id str' that contains the formatted 'team id' where the mask is True, and an empty string where the mask is False
    df_k['team id str'] = df_k['team id'].where(mask, '')

    # Use vectorized string operations to create the links for each column
    df_k['id'] = '<a target="_blank" href="https://statsapi.web.nhl.com/api/v1/people/' + df_k['id'].astype(str) + '?expand=person.stats&stats=yearByYear,yearByYearPlayoffs,careerRegularSeason&expand=stats.team" style="color: green">' + df_k['id'].astype(str) + '</a>'

    df_k['name'] = '<a target="_blank" href="https://www.fantrax.com/fantasy/league/' + league_id + '/players;reload=2;statusOrTeamFilter=ALL;searchName=' + df_k['name'].str.replace(' ', '%20') + '" style="color: green">' + df_k['name'] + '</a>'

    df_k['team'] = '<a target="_blank" href="https://statsapi.web.nhl.com/api/v1/teams/' + df_k['team id str'] + '/roster?expand=roster.person,person.names" style="color: green">' + df_k['team'] + '</a>'

    ##############################################################################################

    (start_year, end_year) = split_seasonID_into_component_years(season_id=from_season_id)
    if from_season_id != to_season_id:
        seasons = f'{from_season_id} to {to_season_id} Seasons'
    elif timeframe == 'Playoffs':
        seasons = f'{start_year-1}-{end_year-1} Playoffs'
    else:
        seasons = f'{from_season_id} Season'

    data_dict = rankings_to_html(
                    df=df_k,
                    config=config,
                    stat_type=stat_type
                )


    return data_dict

def stats_config(position: str='all') -> Tuple[List, List, List, Dict, List]:

    config = {
        'columns': [
            {'title': 'rank in group', 'runtime column': 'rank', 'format': eval(f_0_decimals)},
            {'title': 'id', 'table column': 'player_id', 'data_group': 'general', 'hide': True},
            {'title': 'name', 'table column': 'name', 'justify': 'left', 'search_builder': True},
            {'title': 'team id', 'table column': 'team_id', 'data_group': 'general', 'hide': True},
            {'title': 'team', 'table column': 'team_abbr', 'data_group': 'general', 'search_builder': True},
            {'title': 'pos', 'table column': 'pos', 'search_pane': True, 'data_group': 'general', 'search_builder': True},
            {'title': 'fantrax roster status', 'table column': 'status', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'age', 'table column': 'age', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},
            {'title': 'height', 'table column': 'height', 'data_group': 'general', 'hide': True},
            {'title': 'weight', 'table column': 'weight', 'data_group': 'general', 'hide': True},
            {'title': 'career games', 'table column': 'career_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'bt', 'table column': 'breakout_threshold', 'format': eval(f_0_decimals), 'data_group': 'skater', 'hide': True, 'search_builder': True},
            {'title': 'keeper', 'table column': 'keeper', 'format': eval(f_nan_to_empty), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'pre-draft keeper', 'table column': 'pre_draft_keeper', 'format': eval(f_nan_to_empty), 'data_group': 'draft', 'hide': True, 'search_builder': True},
            {'title': 'rookie', 'table column': 'rookie', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'active', 'table column': 'active', 'data_group': 'general', 'hide': True},
            {'title': 'nhl roster status', 'table column': 'nhl_roster_status', 'data_group': 'general', 'hide': True},
            {'title': 'minors', 'table column': 'minors', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'watch', 'table column': 'watch_list', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'prj draft round', 'runtime column': 'pdr', 'data_group': 'draft', 'hide': True},
            {'title': 'injury', 'table column': 'injury_status', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'hide': True},
            {'title': 'injury note', 'table column': 'injury_note', 'justify': 'left', 'data_group': 'general', 'hide': True},
            {'title': 'manager', 'table column': 'pool_team', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'search_builder': True},
            {'title': 'first game', 'table column': 'first game', 'format': eval(f_str), 'data_group': 'general', 'hide': True},
            {'title': 'last game', 'table column': 'last game', 'format': eval(f_str), 'data_group': 'general', 'default order': 'desc', 'search_builder': True, 'hide': True},
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
            {'title': 'managers_pick_number', 'table column': 'managers_pick_number', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'overall', 'table column': 'overall', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'picked by', 'table column': 'picked_by', 'justify': 'left', 'data_group': 'draft', 'hide': True},
        ],
    }

    config['columns'].extend(league_draft_columns['columns'])

    cumulative_zscore_summary_columns = {
        'columns': [
            {'title': 'score', 'runtime column': 'z_score', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'search_builder': True},
            {'title': 'z-score calc', 'runtime column': 'z_score_calc', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'hide': True},
            {'title': 'z-combo', 'runtime column': 'z_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum')},
            {'title': 'offense', 'runtime column': 'z_offense', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-offense calc', 'runtime column': 'z_offense_calc', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-offense combo', 'runtime column': 'z_offense_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},
            {'title': 'peripheral', 'runtime column': 'z_peripheral', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-peripheral calc', 'runtime column': 'z_peripheral_calc', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-peripheral combo', 'runtime column': 'z_peripheral_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},

            {'title': 'z-count', 'runtime column': 'z_g_count', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-count calc', 'runtime column': 'z_count_calc', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-count combo', 'runtime column': 'z_g_count_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},
            {'title': 'z-ratio', 'runtime column': 'z_g_ratio', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-ratio calc', 'runtime column': 'z_ratio_calc', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-ratio combo', 'runtime column': 'z_g_ratio_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},

            {'title': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +blks', 'runtime column': 'z_hits_blk', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +penalties', 'runtime column': 'z_hits_pim', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
        ],
    }

    config['columns'].extend(cumulative_zscore_summary_columns['columns'])

    pg_zscore_summary_columns = {
        'columns': [
            {'title': 'score pg', 'alias': 'z-score', 'runtime column': 'z_score_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'search_builder': True},
            {'title': 'z-score pg calc', 'runtime column': 'z_score_pg_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'hide': True},
            {'title': 'z-combo pg', 'alias': 'z-combo', 'runtime column': 'z_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum')},
            {'title': 'offense pg', 'alias': 'z-offense', 'runtime column': 'z_offense_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-offense pg calc', 'runtime column': 'z_offense_pg_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-offense pg combo', 'alias': 'z-offense combo', 'runtime column': 'z_offense_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},
            {'title': 'peripheral pg', 'alias': 'z-peripheral', 'runtime column': 'z_peripheral_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-peripheral pg calc', 'runtime column': 'z_peripheral_pg_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-peripheral pg combo', 'alias': 'z-peripheral combo', 'runtime column': 'z_peripheral_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},

            {'title': 'z-count pg', 'runtime column': 'z_g_count_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-count pg calc', 'runtime column': 'z_count_pg_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-count pg combo', 'runtime column': 'z_g_count_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},
            {'title': 'z-ratio pg', 'runtime column': 'z_g_ratio_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-ratio pg calc', 'runtime column': 'z_ratio_pg_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-ratio pg combo', 'runtime column': 'z_g_ratio_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},

            {'title': 'z-sog +hits +blk pg', 'alias': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +blks pg', 'alias': 'z-hits +blks', 'runtime column': 'z_hits_blk_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-goals +hits +penalties pg', 'alias': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +penalties pg', 'alias': 'z-hits +penalties', 'runtime column': 'z_hits_pim_pg', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
        ],
    }

    config['columns'].extend(pg_zscore_summary_columns['columns'])

    p60_zscore_summary_columns = {
        'columns': [
            {'title': 'score p60', 'alias': 'z-score', 'runtime column': 'z_score_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'search_builder': True},
            {'title': 'z-score p60 calc', 'runtime column': 'z_score_p60_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum'), 'hide': True},
            {'title': 'z-combo p60', 'alias': 'z-combo', 'runtime column': 'z_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater_z_score_sum', 'goalie_z_score_sum')},
            {'title': 'offense p60', 'alias': 'z-offense', 'runtime column': 'z_offense_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-offense p60 calc', 'runtime column': 'z_offense_p60_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-offense p60 combo', 'alias': 'z-offense combo', 'runtime column': 'z_offense_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},
            {'title': 'peripheral p60', 'alias': 'z-peripheral', 'runtime column': 'z_peripheral_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'search_builder': True},
            {'title': 'z-peripheral p60 calc', 'runtime column': 'z_peripheral_p60_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-peripheral p60 combo', 'alias': 'z-peripheral combo', 'runtime column': 'z_peripheral_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum'},

            {'title': 'z-count p60', 'runtime column': 'z_g_count_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-count p60 calc', 'runtime column': 'z_count_p60_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-count p60 combo', 'runtime column': 'z_g_count_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},
            {'title': 'z-ratio p60', 'runtime column': 'z_g_ratio_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'search_builder': True},
            {'title': 'z-ratio p60 calc', 'runtime column': 'z_ratio_p60_calc', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum', 'hide': True},
            {'title': 'z-ratio p60 combo', 'runtime column': 'z_g_ratio_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_sum'},

            {'title': 'z-sog +hits +blk p60', 'alias': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +blks p60', 'alias': 'z-hits +blks', 'runtime column': 'z_hits_blk_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-goals +hits +penalties p60', 'alias': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
            {'title': 'z-hits +penalties p60', 'alias': 'z-hits +penalties', 'runtime column': 'z_hits_pim_p60', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_sum', 'hide': True},
        ],
    }

    config['columns'].extend(p60_zscore_summary_columns['columns'])

    skater_columns = {
        'columns': [
            {'title': 'line', 'table column': 'line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True, 'hide': True},
            {'title': 'pp unit', 'table column': 'pp_line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True, 'hide': True},
            {'title': 'pp unit prj', 'runtime column': 'pp_unit_prj', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            {'title': 'sleeper', 'runtime column': 'sleeper', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': 'upside', 'runtime column': 'upside', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': '3yp', 'runtime column': '3yp', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            {'title': 'bandaid boy', 'runtime column': 'bandaid_boy', 'format': eval(f_str), 'data_group': 'draft', 'hide': True},

            {'title': 'toi (sec)', 'runtime column': 'toi_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg', 'table column': 'toi_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg (sec)', 'runtime column': 'toi_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg (trend)', 'runtime column': 'toi_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg ra', 'table column': 'toi_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'toi even (sec)', 'runtime column': 'toi_even_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg', 'table column': 'toi_even_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg (sec)', 'runtime column': 'toi_even_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg (trend)', 'runtime column': 'toi_even_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg ra', 'table column': 'toi_even_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'ev pts', 'table column': 'evg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev on-ice', 'table column': 'evg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev ipp', 'table column': 'evg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'cf', 'table column': 'corsi_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ca', 'table column': 'corsi_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'cf%', 'table column': 'corsi_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': False, 'hide': True, 'search_builder': True},
            {'title': 'ff', 'table column': 'fenwick_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'fa', 'table column': 'fenwick_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ff%', 'table column': 'fenwick_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': True},

            {'title': 'toi pp (sec)', 'runtime column': 'toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg', 'table column': 'toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg (sec)', 'runtime column': 'toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg (trend)', 'runtime column': 'toi_pp_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg ra', 'table column': 'toi_pp_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'pp sog/120', 'table column': 'pp_sog_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp g/120', 'table column': 'pp_goals_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp pts/120', 'table column': 'pp_pts_p120', 'format': eval(f_2_decimals_show_0), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp pts', 'table column': 'ppg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp on-ice', 'table column': 'ppg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp ipp', 'table column': 'ppg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'team toi pp (sec)', 'runtime column': 'team_toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg', 'table column': 'team_toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg (sec)', 'runtime column': 'team_toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg ra', 'table column': 'team_toi_pp_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': '%pp', 'runtime column': 'toi_pp_pg_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp (last game)', 'runtime column': 'toi_pp_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp trend', 'runtime column': 'toi_pp_pg_ratio_trend', 'format': eval(f_1_decimal_show_0_and_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp ra', 'runtime column': 'toi_pp_ratio_ra', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'toi sh (sec)', 'runtime column': 'toi_sh_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg', 'table column': 'toi_sh_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg (sec)', 'runtime column': 'toi_sh_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg (trend)', 'runtime column': 'toi_sh_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg ra', 'table column': 'toi_sh_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True, 'search_builder': True},

            {'title': 'team gp', 'table column': 'team_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True},
            {'title': 'games', 'table column': 'games', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},

            {'title': 'sh%', 'table column': 'shooting%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_columns['columns'])

    skater_cumulative_columns = {
        'columns': [
            {'title': 'pts', 'table column': 'points', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'g', 'table column': 'goals', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'a', 'table column': 'assists', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'ppp', 'table column': 'points_pp', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'sog', 'table column': 'shots', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pp sog', 'table column': 'shots_powerplay', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
            {'title': 'tk', 'table column': 'takeaways', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'hits', 'table column': 'hits', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'blk', 'table column': 'blocked', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pim', 'table column': 'pim', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'penalties', 'table column': 'penalties', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
        ],
    }

    config['columns'].extend(skater_cumulative_columns['columns'])

    skater_pg_columns = {
        'columns': [
            {'title': 'pts pg', 'alias': 'pts', 'runtime column': 'pts_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'g pg', 'alias': 'g', 'runtime column': 'g_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'a pg', 'alias': 'a', 'runtime column': 'a_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'ppp pg', 'alias': 'ppp', 'runtime column': 'ppp_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'sog pg', 'alias': 'sog', 'runtime column': 'sog_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pp sog pg', 'alias': 'pp sog', 'table column': 'sog_pp_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
            {'title': 'tk pg', 'alias': 'tk', 'runtime column': 'tk_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'hits pg', 'alias': 'hits', 'runtime column': 'hits_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'blk pg', 'alias': 'blk', 'runtime column': 'blk_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pim pg', 'alias': 'pim', 'runtime column': 'pim_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'penalties pg', 'alias': 'penalties', 'table column': 'penalties_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
        ],
    }

    config['columns'].extend(skater_pg_columns['columns'])

    skater_p60_columns = {
        'columns': [
            {'title': 'pts p60', 'alias': 'pts', 'runtime column': 'pts_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'g p60', 'alias': 'g', 'runtime column': 'g_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'a p60', 'alias': 'a', 'runtime column': 'a_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'ppp p60', 'alias': 'ppp', 'runtime column': 'ppp_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'sog p60', 'alias': 'sog', 'runtime column': 'sog_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pp sog p60', 'alias': 'pp sog', 'table column': 'sog_pp_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
            {'title': 'tk p60', 'alias': 'tk', 'runtime column': 'tk_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'hits p60', 'alias': 'hits', 'runtime column': 'hits_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'blk p60', 'alias': 'blk', 'runtime column': 'blk_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'pim p60', 'alias': 'pim', 'runtime column': 'pim_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category'},
            {'title': 'penalties p60', 'alias': 'penalties', 'table column': 'penalties_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_scoring_category', 'hide': True},
        ],
    }

    config['columns'].extend(skater_p60_columns['columns'])

    skater_cumulative_zscore_columns = {
        'columns': [
            {'title': 'z-pts', 'runtime column': 'z_points', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-g', 'runtime column': 'z_goals', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-a', 'runtime column': 'z_assists', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-ppp', 'runtime column': 'z_points_pp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sog', 'runtime column': 'z_shots', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-tk', 'runtime column': 'z_takeaways', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-hits', 'runtime column': 'z_hits', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-blk', 'runtime column': 'z_blocked', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-pim', 'runtime column': 'z_pim', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-penalties', 'runtime column': 'z_penalties', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_cumulative_zscore_columns['columns'])

    skater_pg_zscore_columns = {
        'columns': [
            {'title': 'z-pts pg', 'alias': 'z-pts', 'runtime column': 'z_pts_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-g pg', 'alias': 'z-g', 'runtime column': 'z_g_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-a pg', 'alias': 'z-a', 'runtime column': 'z_a_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-ppp pg', 'alias': 'z-ppp', 'runtime column': 'z_ppp_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sog pg', 'alias': 'z-sog', 'runtime column': 'z_sog_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-tk pg', 'alias': 'z-tk', 'runtime column': 'z_tk_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-hits pg', 'alias': 'z-hits', 'runtime column': 'z_hits_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-blk pg', 'alias': 'z-blk', 'runtime column': 'z_blk_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-pim pg', 'alias': 'z-pim', 'runtime column': 'z_pim_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-penalties pg', 'alias': 'z-penalties', 'runtime column': 'z_penalties_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_pg_zscore_columns['columns'])

    skater_p60_zscore_columns = {
        'columns': [
            {'title': 'z-pts p60', 'alias': 'z-pts', 'runtime column': 'z_pts_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-g p60', 'alias': 'z-g', 'runtime column': 'z_g_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-a p60', 'alias': 'z-a', 'runtime column': 'z_a_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-ppp p60', 'alias': 'z-ppp', 'runtime column': 'z_ppp_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sog p60', 'alias': 'z-sog', 'runtime column': 'z_sog_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-tk p60', 'alias': 'z-tk', 'runtime column': 'z_tk_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-hits p60', 'alias': 'z-hits', 'runtime column': 'z_hits_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-blk p60', 'alias': 'z-blk', 'runtime column': 'z_blk_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-pim p60', 'alias': 'z-pim', 'runtime column': 'z_pim_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-penalties p60', 'alias': 'z-penalties', 'runtime column': 'z_penalties_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'skater_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(skater_p60_zscore_columns['columns'])

    goalie_columns = {
        'columns': [
            {'title': 'tier', 'runtime column': 'tier', 'data_group': 'draft', 'hide': True},
            {'title': 'goalie starts', 'table column': 'games_started', 'format': eval(f_0_decimals), 'data_group': 'goalie', 'search_builder': True, 'hide': True},
            {'title': '% of team games started', 'table column': 'starts_as_percent', 'format': eval(f_0_decimals), 'hide': True, 'data_group': 'goalie'},
            {'title': 'qs', 'table column': 'quality_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
            {'title': 'qs %', 'table column': 'quality_starts_as_percent', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie', 'hide': True, 'search_builder': True},
            {'title': 'rbs', 'table column': 'really_bad_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
            {'title': 'goals against', 'table column': 'goals_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
            {'title': 'shots against', 'table column': 'shots_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie', 'hide': True},
        ],
    }

    config['columns'].extend(goalie_columns['columns'])

    goalie_cumulative_columns = {
        'columns': [
            {'title': 'w', 'table column': 'wins', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv', 'table column': 'saves', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'gaa', 'table column': 'gaa', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv%', 'table column': 'save%', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
        ],
    }

    config['columns'].extend(goalie_cumulative_columns['columns'])

    goalie_pg_columns = {
        'columns': [
            {'title': 'w pg', 'alias': 'w', 'runtime column': 'wins_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv pg', 'alias': 'sv', 'runtime column': 'saves_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'gaa pg', 'alias': 'gaa', 'table column': 'gaa_pg', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv% pg', 'alias': 'sv%', 'table column': 'save%_pg', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
        ],
    }

    config['columns'].extend(goalie_pg_columns['columns'])

    goalie_p60_columns = {
        'columns': [
            {'title': 'w p60', 'alias': 'w', 'runtime column': 'wins_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv p60', 'alias': 'sv', 'runtime column': 'saves_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'gaa p60', 'alias': 'gaa', 'table column': 'gaa_p60', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
            {'title': 'sv% p60', 'alias': 'sv%', 'table column': 'save%_p60', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_scoring_category'},
        ],
    }

    config['columns'].extend(goalie_p60_columns['columns'])

    goalie_cumulative_zscore_columns = {
        'columns': [
            {'title': 'z-w', 'runtime column': 'z_wins', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv', 'runtime column': 'z_saves', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-gaa', 'runtime column': 'z_gaa', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv%', 'runtime column': 'z_save%', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_cumulative_zscore_columns['columns'])

    goalie_pg_zscore_columns = {
        'columns': [
            {'title': 'z-w pg', 'alias': 'z-w', 'runtime column': 'z_wins_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv pg', 'alias': 'z-sv', 'runtime column': 'z_saves_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-gaa pg', 'alias': 'z-gaa', 'runtime column': 'z_gaa_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv% pg', 'alias': 'z-sv%', 'runtime column': 'z_save%_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_pg_zscore_columns['columns'])

    goalie_p60_zscore_columns = {
        'columns': [
            {'title': 'z-w p60', 'alias': 'z-w', 'runtime column': 'z_wins_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv p60', 'alias': 'z-sv', 'runtime column': 'z_saves_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-gaa p60', 'alias': 'z-gaa', 'runtime column': 'z_gaa_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
            {'title': 'z-sv% p60', 'alias': 'z-sv%', 'runtime column': 'z_save%_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'goalie_z_score_cat', 'hide': True, 'search_builder': True},
        ],
    }

    config['columns'].extend(goalie_p60_zscore_columns['columns'])

    return deepcopy(config)
