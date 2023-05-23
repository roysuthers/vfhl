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
from typing import Dict, List, Tuple, Union
from urllib.request import pathname2url

# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# import plotly.express as px
from numpy.polynomial.polynomial import polyfit

from constants import  DATABASE
from utils import calculate_age, seconds_to_string_time, split_seasonID_into_component_years, string_to_time

# formatting for ranking tables
f_0_decimals = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.0f}'.format(x)", '<string>', 'eval')
f_0_decimals_dont_show_0_and_show_plus = compile("lambda x: '' if pd.isna(x) or x=='' or abs(round(x,0))==0 else '{:+0.0f}'.format(x)", '<string>', 'eval')
# f_0_or_1_decimal = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.0f}'.format(x) if x.is_integer() else '' if pd.isna(x) or x in ['', 0] else '{:0.1f}'.format(x)", '<string>', 'eval')
f_0_toi_to_empty = compile("lambda x: '' if x in ('00:00', None) or pd.isna(x) else x", '<string>', 'eval')
f_0_toi_to_empty_and_show_plus = compile("lambda x: '' if x in ('+00:00', '+0:00', None) or pd.isna(x) else x", '<string>', 'eval')
f_1_decimal = compile("lambda x: '' if pd.isna(x) or x in ['', 0] or round(x,1)==0.0 else '{:0.1f}'.format(x)", '<string>', 'eval')
f_1_decimal_show_0 = compile("lambda x: '' if pd.isna(x) or x=='' else '{:}'.format(int(x)) if x==0 else '{:0.1f}'.format(x)", '<string>', 'eval')
f_1_decimal_show_0_and_plus = compile("lambda x: '' if pd.isna(x) or x=='' or abs(round(x,1))==0.0 else '{:+0.1f}'.format(x)", '<string>', 'eval')
f_2_decimals = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:0.2f}'.format(x)", '<string>', 'eval')
f_2_decimals_show_0 = compile("lambda x: '' if pd.isna(x) or x=='' else '{:}'.format(int(x)) if x==0 else '{:0.2f}'.format(x)", '<string>', 'eval')
# f_2_decimals_show_0_and_plus = compile("lambda x: '' if pd.isna(x) or x=='' else '{:}'.format(int(x)) if abs(round(x,2))==0.00 else '{:+0.2f}'.format(x)", '<string>', 'eval')
f_3_decimals_no_leading_0 = compile("lambda x: '' if pd.isna(x) or x in ['', 0] else '{:.3f}'.format(x).lstrip('0')", '<string>', 'eval')
f_3_decimals_show_0 = compile("lambda x: '' if pd.isna(x) or x=='' else '{:0.3f}'.format(x)", '<string>', 'eval')
# f_int = compile("lambda x: '' if x in ['', 0] else '{:}'.format(x)", '<string>', 'eval')
f_nan_to_empty = compile("lambda x: '' if pd.isna(x) else x", '<string>', 'eval')
# f_none_to_empty = compile("lambda x:'' if x is None else x", '<string>', 'eval')
f_str = compile("lambda x: '' if pd.isna(x) or x == '' else x", '<string>', 'eval')

skater_position_codes = ("LW", "C", "RW", "D")
forward_position_codes = ("LW", "C", "RW")
defense_position_code = "D"
goalie_position_code = "G"

minimum_one_game_filter = 'games >= 1'

# 10 games or over in 82 game season
sktr_min_games_vs_team_games_filter = 'percent_of_team_games >= 0.25'
# 10 games or over in 82 game season
goalie_min_games_vs_team_games_filter = 'percent_of_team_games >= 0.25'

skaters_filter = f'pos in {skater_position_codes}'
forwards_filter = f'pos in {forward_position_codes}'
defense_filter = f'pos == "{defense_position_code}"'
goalie_filter = f'pos == "{goalie_position_code}"'

###############################################
###############################################
# Fantrax scoring categories
###############################################
# Forwards and Defense
# cumulative stats
sktr_offensive_cumulative_stat_categories = ['points', 'goals', 'assists', 'shots', 'points_pp']
sktr_peripheral_cumulative_stat_categories = ['pim', 'hits', 'blocked', 'takeaways']
sktr_cumulative_stat_categories = sktr_offensive_cumulative_stat_categories + sktr_peripheral_cumulative_stat_categories
# cumulative stat z-scores
sktr_offensive_cumulative_stat_z_categories = ['z_points', 'z_goals', 'z_assists', 'z_shots', 'z_points_pp']
sktr_peripheral_cumulative_stat_z_categories = ['z_pim', 'z_hits', 'z_blocked', 'z_takeaways']
sktr_cumulative_stat_z_categories = sktr_offensive_cumulative_stat_z_categories + sktr_peripheral_cumulative_stat_z_categories
# per game stats
sktr_offensive_per_game_categories = ['pts_pg', 'g_pg', 'a_pg', 'sog_pg', 'ppp_pg']
sktr_peripheral_per_game_categories = ['pim_pg', 'hits_pg', 'blk_pg', 'tk_pg']
sktr_per_game_categories = sktr_offensive_per_game_categories + sktr_peripheral_per_game_categories
# per game stat z-scores
sktr_offensive_per_game_z_categories = ['z_pts_pg', 'z_g_pg', 'z_a_pg', 'z_sog_pg', 'z_ppp_pg']
sktr_peripheral_per_game_z_categories = ['z_pim_pg', 'z_hits_pg', 'z_blk_pg', 'z_tk_pg']
sktr_per_game_z_categories = sktr_offensive_per_game_z_categories + sktr_peripheral_per_game_z_categories
# per 60 stats
sktr_offensive_per_60_categories = ['pts_p60', 'g_p60', 'a_p60', 'sog_p60', 'ppp_p60']
sktr_peripheral_per_60_categories = ['pim_p60', 'hits_p60', 'blk_p60', 'tk_p60']
sktr_per_60_categories = sktr_offensive_per_60_categories + sktr_peripheral_per_60_categories
# per 60 stat z-scores
sktr_offensive_per_60_z_categories = ['z_pts_p60', 'z_g_p60', 'z_a_p60', 'z_sog_p60', 'z_ppp_p60']
sktr_peripheral_per_60_z_categories = ['z_pim_p60', 'z_hits_p60', 'z_blk_p60', 'z_tk_p60']
sktr_per_60_z_categories = sktr_offensive_per_60_z_categories + sktr_peripheral_per_60_z_categories
###############################################
# Goalies
# cumulative stats
goalie_cumulative_stat_categories = ['wins', 'saves', 'gaa', 'save%']
# cumulative stat z-scores
goalie_cumulative_stat_z_categories = ['z_wins', 'z_saves', 'z_gaa', 'z_save%']
# per game stats
goalie_per_game_categories = ['wins_pg', 'saves_pg', 'gaa_pg', 'save%_pg']
# per game stat z-scores
goalie_per_game_z_categories = ['z_wins_pg', 'z_saves_pg', 'z_gaa_pg', 'z_save%_pg']
# per 60 stats
goalie_per_60_categories = ['wins_p60', 'saves_p60', 'gaa_p60', 'save%_p60']
# per 60 stat z-scores
goalie_per_60_z_categories = ['z_wins_p60', 'z_saves_p60', 'z_gaa_p60', 'z_save%_p60']
###############################################
###############################################
# Summary z-score columns
###############################################
# cumulative stat z-scores
sktr_cumulative_stat_summary_z_scores = ['z_score', 'z_offense', 'z_peripheral', 'z_sog_hits_blk', 'z_hits_blk', 'z_goals_hits_pim', 'z_hits_pim', 'z_score_vorp', 'z_offense_vorp', 'z_peripheral_vorp']
g_cumulative_stat_summary_z_scores = ['z_score', 'z_score_vorp']
# per game stat z-scores
sktr_per_game_summary_z_scores = ['z_score_pg', 'z_offense_pg', 'z_peripheral_pg', 'z_sog_hits_blk_pg', 'z_hits_blk_pg', 'z_goals_hits_pim_pg', 'z_hits_pim_pg', 'z_score_pg_vorp', 'z_offense_pg_vorp', 'z_peripheral_pg_vorp']
g_per_game_summary_z_scores = ['z_score_pg','z_score_pg_vorp']
# per 60 stat z-scores
sktr_per_60_summary_z_scores = ['z_score_p60', 'z_offense_p60', 'z_peripheral_p60', 'z_sog_hits_blk_p60', 'z_hits_blk_p60', 'z_goals_hits_pim_p60', 'z_hits_pim_p60', 'z_score_p60_vorp', 'z_offense_p60_vorp', 'z_peripheral_p60_vorp']
g_per_60_summary_z_scores = ['z_score_p60', 'z_score_p60_vorp']
###############################################
###############################################

###############################################
# sample size for calculating z-scores above replacement
# number of scoring slots per position
f_active_slots = 9
d_active_slots = 6
sktr_active_slots = 1
sktr_bench_slots = 4
g_active_slots = 2
g_bench_slots = 2
# number of teams in Fantrax league
number_of_fantrax_teams = 13
# number of highest rated players used for z-scores, by position
f_number_of_highest_rated = f_active_slots * number_of_fantrax_teams
d_number_of_highest_rated = d_active_slots * number_of_fantrax_teams
sktr_number_of_highest_rated = sktr_active_slots * number_of_fantrax_teams
g_number_of_highest_rated = g_active_slots * number_of_fantrax_teams

# period for rolling averages
rolling_avg_period = 3

generated_html_path = './output/html'

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
    df_agg_stats['toi_pg_sec'] = df_agg_stats['toi_sec']/df_agg_stats['games']

    # even time-on-ice per game in seconds
    df_agg_stats['toi_even_pg_sec'] = df_agg_stats['toi_even_sec']/df_agg_stats['games']

    # even goals IPP
    df_agg_stats['evg_ipp'] = df_agg_stats.apply(lambda x: x['evg_point'] / x['evg_on_ice'] * 100 if x['evg_on_ice'] != 0 else np.nan, axis='columns')

    # powerplay time-on-ice per game in seconds
    df_agg_stats['toi_pp_pg_sec'] = df_agg_stats['toi_pp_sec']/df_agg_stats['games']

    # team powerplay time-on-ice per game in seconds
    df_agg_stats['team_toi_pp_pg_sec'] = df_agg_stats['team_toi_pp_sec']/df_agg_stats['games']

    # powerplay goals IPP
    df_agg_stats['ppg_ipp'] = df_agg_stats.apply(lambda x: x['ppg_point'] / x['ppg_on_ice'] * 100 if x['ppg_on_ice'] != 0 else np.nan, axis='columns')

    # get ratio of powerplay time-on-ice vs. team powerplay time-on-ice
    df_agg_stats['toi_pp_pg_ratio'] = df_agg_stats['toi_pp_pg_sec']/df_agg_stats['team_toi_pp_pg_sec'] * 100

    # convert shorthand time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['toi_sh_pg_sec'] = df_agg_stats['toi_sh_sec']/df_agg_stats['games']

    # convert time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['toi_pg'] = (df_agg_stats['toi_sec']/df_agg_stats['games']/60).astype(int).map('{:02d}'.format) + (df_agg_stats['toi_sec']/df_agg_stats['games']%60).astype(int).map(':{:02d}'.format)

    # convert time-on-ice seconds rolling-average to string formatted as mm:ss
    df_agg_stats['toi_pg_ra_last'] = df_agg_stats['toi_sec_ra'].astype(int).apply(seconds_to_string_time)
    df_agg_stats['toi_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['pos'] == goalie_position_code else x['toi_pg_ra_last'], axis='columns')

    # convert even time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['toi_even_pg'] = (df_agg_stats['toi_even_sec']/df_agg_stats['games']/60).astype(int).map('{:02d}'.format) + (df_agg_stats['toi_even_sec']/df_agg_stats['games']%60).astype(int).map(':{:02d}'.format)

    # convert even time-on-ice seconds rolling-average to string formatted as mm:ss
    df_agg_stats['toi_even_pg_ra_last'] = df_agg_stats['toi_even_sec_ra'].astype(int).apply(seconds_to_string_time)
    df_agg_stats['toi_even_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['pos'] == goalie_position_code else x['toi_even_pg_ra_last'], axis='columns')

    # convert powerplay time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['toi_pp_pg'] = (df_agg_stats['toi_pp_sec']/df_agg_stats['games']/60).astype(int).map('{:02d}'.format) + (df_agg_stats['toi_pp_sec']/df_agg_stats['games']%60).astype(int).map(':{:02d}'.format)

    # convert powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    df_agg_stats['toi_pp_pg_ra_last'] = df_agg_stats['toi_pp_sec_ra'].astype(int).apply(seconds_to_string_time)
    df_agg_stats['toi_pp_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['pos'] == goalie_position_code else x['toi_pp_pg_ra_last'], axis='columns')

    # convert team powerplay time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['team_toi_pp_pg'] = (df_agg_stats['team_toi_pp_sec']/df_agg_stats['games']/60).astype(int).map('{:02d}'.format) + (df_agg_stats['team_toi_pp_sec']/df_agg_stats['games']%60).astype(int).map(':{:02d}'.format)

    # convert team powerplay time-on-ice seconds rolling-average to string formatted as mm:ss
    df_agg_stats['team_toi_pp_pg_ra_last'] = df_agg_stats['team_toi_pp_sec_ra'].astype(int).apply(seconds_to_string_time)
    df_agg_stats['team_toi_pp_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['pos'] == goalie_position_code else x['team_toi_pp_pg_ra_last'], axis='columns')

    # calc powerplay goals per 2 penalty minutes
    df_agg_stats['pp_goals_p120'] = ((df_agg_stats['goals_pp'] * 120) / df_agg_stats['toi_pp_sec'])

    # calc powerplay shots-on-goal per 2 penalty minutes
    df_agg_stats['pp_sog_p120'] = df_agg_stats.apply(lambda x: (x['shots_powerplay'] * 120) / x['toi_pp_sec'] if x['toi_pp_sec'] != 0 else np.nan, axis='columns')

    # calc powerplay points per 2 penalty minutes
    df_agg_stats['pp_pts_p120'] = ((df_agg_stats['points_pp'] * 120) / df_agg_stats['toi_pp_sec'])
    df_agg_stats['pp_pts_p120'] = df_agg_stats.apply(lambda x: '' if x['toi_pp_pg'] == '00:00' else x['pp_pts_p120'], axis='columns')

    # set toi_pp_pg_ratio & team_toi_pp_pg_ra_last & toi_pp_ratio_ra to blank if toi_pp_pg is 0
    df_agg_stats['toi_pp_pg_ratio'] = df_agg_stats.apply(lambda x: '' if x['toi_pp_pg'] == '00:00' else x['toi_pp_pg_ratio'], axis='columns')
    df_agg_stats['team_toi_pp_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['toi_pp_pg'] == '00:00' else x['team_toi_pp_pg_ra_last'], axis='columns')
    df_agg_stats['toi_pp_ratio_ra'] = df_agg_stats.apply(lambda x: '' if x['toi_pp_pg'] == '00:00' else x['toi_pp_ratio_ra'], axis='columns')

    # convert shorthand time-on-ice seconds to string formatted as mm:ss
    df_agg_stats['toi_sh_pg'] = (df_agg_stats['toi_sh_sec']/df_agg_stats['games']/60).astype(int).map('{:02d}'.format) + (df_agg_stats['toi_sh_sec']/df_agg_stats['games']%60).astype(int).map(':{:02d}'.format)

    # convert shorthand time-on-ice seconds rolling-average to string formatted as mm:ss
    df_agg_stats['toi_sh_pg_ra_last'] = df_agg_stats['toi_sh_sec_ra'].astype(int).apply(seconds_to_string_time)
    df_agg_stats['toi_sh_pg_ra_last'] = df_agg_stats.apply(lambda x: '' if x['pos'] == goalie_position_code else x['toi_sh_pg_ra_last'], axis='columns')

    ########################################################################################################
    # trend time-on-ice
    df_sktr = df.query(skaters_filter).copy(deep=True)
    df_sktr.sort_values(['player_id', 'date'], ascending=[True, True], inplace=True)
    df_sktr = df_sktr[df_sktr.groupby('player_id')['date'].transform('size') >= 2]
    df_sktr = df_sktr.groupby('player_id', group_keys=False)

    df_agg_stats['toi_pg_sec_trend'] = df_sktr['toi_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).div(60).astype(int).map('{:+1d}'.format) + df_sktr['toi_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).mod(60).astype(int).map(':{:02d}'.format)

    df_agg_stats['toi_even_pg_sec_trend'] = df_sktr['toi_even_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).div(60).astype(int).map('{:+1d}'.format) + df_sktr['toi_even_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).mod(60).astype(int).map(':{:02d}'.format)

    df_agg_stats['toi_pp_pg_sec_trend'] = df_sktr['toi_pp_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).div(60).astype(int).map('{:+1d}'.format) + df_sktr['toi_pp_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).mod(60).astype(int).map(':{:02d}'.format)

    # The following calc seems not quite right, and occasionally gives a trend value such as +161619312102409.5, and not sure this is really helpful information
    df_agg_stats['toi_pp_pg_ratio_trend'] = df_sktr['toi_pp_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]) / df_sktr['team_toi_pp_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1])

    df_agg_stats['toi_sh_pg_sec_trend'] = df_sktr['toi_sh_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).div(60).astype(int).map('{:+1d}'.format) + df_sktr['toi_sh_sec_ra'].apply(lambda x: polyfit(np.arange(0, x.size), x, 1)[1]).mul(df_agg_stats['games'], fill_value=0).mod(60).astype(int).map(':{:02d}'.format)

    ########################################################################################################

    # gaa
    df_agg_stats['gaa'] = df_agg_stats['goals_against'] / df_agg_stats['toi_sec'] * 3600
    # gaa is showing as 0.00 for skaters
    df_agg_stats['gaa'] = df_agg_stats.apply(lambda x: x['gaa'] if x['pos']==goalie_position_code else np.nan, axis='columns')

    # save%
    df_agg_stats['save%'] = df_agg_stats['saves'] / df_agg_stats['shots_against']

    # set NaN to 0
    df_agg_stats.fillna({'games': 0}, inplace=True)

    # set NaN to empty string
    df_agg_stats.fillna({'toi_pg': '', 'toi_even_pg': '', 'toi_pp_pg': '', 'team_toi_pp_pg': '', 'toi_sh_pg': ''}, inplace=True)

    df_agg_stats['team_games'] = df_agg_stats.apply(lambda x: teams_dict[x['team_id']]['games'] if pd.isna(x['team_id']) is False else np.nan, axis='columns')
    # add column for ratio of games to team games
    df_agg_stats['percent_of_team_games'] = df_agg_stats['games'].div(df_agg_stats['team_games']).round(2)

    ########################################################################################################
    df_sktr = df_agg_stats.query(skaters_filter)

    # shooting percentage
    df_agg_stats['shooting%'] = df_sktr['goals'].div(df_sktr['shots']).multiply(100).round(1)

    # Corsi For % & Fenwick For %
    df_agg_stats['corsi_for_%'] = df_sktr['corsi_for'].div(df_sktr['corsi_for'] + df_sktr['corsi_against']).multiply(100).round(1)
    df_agg_stats['fenwick_for_%'] = df_sktr['fenwick_for'].div(df_sktr['fenwick_for'] + df_sktr['fenwick_against']).multiply(100).round(1)

    ########################################################################################################

    # goalie starts as percent of team games
    df_agg_stats['starts_as_percent'] = df_agg_stats['games_started'].div(df_agg_stats['team_games']).round(2) * 100

    # quality starts as percent of starts
    df_agg_stats['quality_starts_as_percent'] = df_agg_stats['quality_starts'].div(df_agg_stats['games_started']).round(3) * 100

    ########################################################################################################
    df_agg_stats.reset_index(inplace=True)
    ########################################################################################################

    return df_agg_stats

def calc_per60_stats(df: pd.DataFrame):

    try:

        # setting 'toi_sec' to np.nan if 0, to calcualte without 'inf' values
        df['toi_sec'] = df['toi_sec'].apply(lambda x: np.nan if x==0 else x)

        # skaters
        ##########################################################################
        # points-per-60-minutes
        df['pts_p60'] = df['points'] / df['toi_sec'] * 3600

        ##########################################################################
        #  goals-per-60-minutes
        df['g_p60'] = df['goals'] / df['toi_sec'] * 3600

        ##########################################################################
        # assists-per-60-minutes
        df['a_p60'] = df['assists'] / df['toi_sec'] * 3600

        ##########################################################################
        # penalty-minutes-per-60-minutes
        df['pim_p60'] = df['pim'] / df['toi_sec'] * 3600
        df['penalties_p60'] = df['penalties'] / df['toi_sec'] * 3600

        ##########################################################################
        # shots-per-60-minutes
        df['sog_p60'] = df['shots'] / df['toi_sec'] * 3600

        ##########################################################################
        # pp shots-per-60-minutes
        df['sog_pp_p60'] = df.apply(lambda x: x['shots_powerplay'] / (x['toi_pp_sec'] * 3600) if x['toi_pp_sec'] > 0 else 0, axis='columns')

        ##########################################################################
        # powerplay-points-per
        df['ppp_p60'] = df['points_pp'] / df['toi_sec'] * 3600

        ##########################################################################
        # hits-per-60-minutes
        df['hits_p60'] = df['hits'] / df['toi_sec'] * 3600

        ##########################################################################
        # blocked-shots-per-60-minutes
        df['blk_p60'] = df['blocked'] / df['toi_sec'] * 3600

        ##########################################################################
        # takeaways-per-60-minutes
        df['tk_p60'] = df['takeaways'] / df['toi_sec'] * 3600

        ##########################################################################
        # goalies
        ##########################################################################
        #  wins-per-60-minutes
        df['wins_p60'] = df['wins'] / df['toi_sec'] * 3600

        # saves-per-60-minutes
        df['saves_p60'] = df['saves'] / df['toi_sec'] * 3600

        # gaa
        df['gaa_p60'] = df['goals_against'] / df['toi_sec'] * 3600
        # gaa is showing as 0.00 for skaters
        df['gaa_p60'] = df.apply(lambda x: x['gaa_p60'] if x['pos']==goalie_position_code else np.nan, axis='columns')

        # save%
        df['save%_p60'] = (df['saves'] / df['toi_sec'] * 3600) / (df['shots_against'] / df['toi_sec'] * 3600)

    except:
        print(f'{traceback.format_exc()} in calc_per60_stats()')

    return

def calc_per_game_stats(df: pd.DataFrame, df_game_stats: pd.DataFrame):

    try:

        # skaters
        ##########################################################################
        # points-per-game
        df['pts_pg'] = df['points'] / df['games']

        ##########################################################################
        #  goals-per-game
        df['g_pg'] = df['goals'] / df['games']

        ##########################################################################
        # assists-per-game
        df['a_pg'] = df['assists'] / df['games']

        ##########################################################################
        # penalty-minutes-per-game
        df['pim_pg'] = df['pim'] / df['games']
        df['penalties_pg'] = df['penalties'] / df['games']

        ##########################################################################
        # shots-per-game
        df['sog_pg'] = df['shots'] / df['games']

        ##########################################################################
        # shots-per-game
        df['sog_pp_pg'] = df['shots_powerplay'] / df['games']

        ##########################################################################
        # powerplay-points-per
        df['ppp_pg'] = df['points_pp'] / df['games']

        ##########################################################################
        # hits-per-game
        df['hits_pg'] = df['hits'] / df['games']

        ##########################################################################
        # blocked-shots-per-game
        df['blk_pg'] = df['blocked'] / df['games']

        ##########################################################################
        # takeaways-per-game
        df['tk_pg'] = df['takeaways'] / df['games']

        ##########################################################################
        # goalies
        ##########################################################################
        #  wins per game
        df['wins_pg'] = df['wins'] / df['games']

        # saves per game
        df['saves_pg'] = df['saves'] / df['games']

        ###################################################################
        # Calculation of gaa_gp and save%_pg needs to calculate gaa's & save%'s for each game
        # and calc mean
        df.set_index('player_id', inplace=True)
        df_game_stats_grouped = df_game_stats.query(f'pos==@goalie_position_code').groupby('player_id')

        # gaa
        df['gaa_pg'] = df_game_stats_grouped.apply(lambda x: (x['goals_against'] / x['toi_sec'] * 3600).mean())

        # save%
        df['save%_pg'] = df_game_stats_grouped.apply(lambda x: (x['saves'] / x['shots_against']).mean())

        df.reset_index(inplace=True)

    except:
        print(f'{traceback.format_exc()} in calc_per_game_stats()')

    return

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

    global max_cat
    max_cat = defaultdict(None)

    try:

        sktr_minimum_games_vs_team_games_filter = sktr_min_games_vs_team_games_filter
        goalie_minimum_games_vs_team_games_filter = goalie_min_games_vs_team_games_filter

        df_sktr = df.query(f'{skaters_filter}').copy(deep=True)
        if len(df_sktr) == 0:
            sktr_minimum_games_vs_team_games_filter = minimum_one_game_filter
            goalie_minimum_games_vs_team_games_filter = minimum_one_game_filter

            df_sktr = df.query(f'{skaters_filter}').copy(deep=True)

        df_f = df.query(f'{forwards_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter}').copy(deep=True)

        columns = list(df.columns)

        #######################################
        # Skaters
        for cat in sktr_cumulative_stat_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None
        # also...
        max_cat[f'sktr shots_powerplay'] = df_sktr['shots_powerplay'].max() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None
        # also...
        max_cat[f'sktr sog_pp_pg'] = df_sktr['sog_pp_pg'].max() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None
        # also...
        max_cat[f'sktr sog_pp_p60'] = df_sktr['sog_pp_p60'].max() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in columns else None

        #######################################
        # Forwards
        for cat in sktr_cumulative_stat_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None
        # also...
        max_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].max() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None
        # also...
        max_cat[f'f sog_pp_pg'] = df_f['sog_pp_pg'].max() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None
        # also...
        max_cat[f'f sog_pp_p60'] = df_f['sog_pp_p60'].max() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in columns else None

        #######################################
        # Defense
        for cat in sktr_cumulative_stat_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None
        # also...
        max_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].max() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None
        # also...
        max_cat[f'd sog_pp_pg'] = df_d['sog_pp_pg'].max() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None
        # also...
        max_cat[f'd sog_pp_p60'] = df_d['sog_pp_p60'].max() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in columns else None

        #######################################
        # Goalies
        for cat in goalie_cumulative_stat_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        for cat in goalie_per_game_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        for cat in goalie_per_60_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        for cat in goalie_cumulative_stat_z_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        for cat in goalie_per_game_z_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        for cat in goalie_per_60_z_categories:
            max_cat[cat] = df_g[cat].max() if cat in columns else None

        #######################################
        # Summary z-scores
        #######################################
        # cumulative stats
        #######################################
        # skaters
        for cat in sktr_cumulative_stat_summary_z_scores:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in df_f.columns else None
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in df_f.columns else None
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in df_d.columns else None

        # goalie
        for cat in g_cumulative_stat_summary_z_scores:
            max_cat[f'g {cat}'] = df_g[cat].max() if cat in df_g.columns else None

        #######################################
        # per game stats
        #######################################
        # skaters
        for cat in sktr_per_game_summary_z_scores:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in df_f.columns else None
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in df_f.columns else None
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in df_d.columns else None

        # goalie
        for cat in g_per_game_summary_z_scores:
            max_cat[f'g {cat}'] = df_g[cat].max() if cat in df_g.columns else None

        #######################################
        # per 60 stats
        #######################################
        # skaters
        for cat in sktr_per_60_summary_z_scores:
            max_cat[f'sktr {cat}'] = df_sktr[cat].max() if cat in df_f.columns else None
            max_cat[f'f {cat}'] = df_f[cat].max() if cat in df_f.columns else None
            max_cat[f'd {cat}'] = df_d[cat].max() if cat in df_d.columns else None

        # goalie
        for cat in g_per_60_summary_z_scores:
            max_cat[f'g {cat}'] = df_g[cat].max() if cat in df_g.columns else None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_maximums()')

    return

def calc_scoring_category_minimums(df: pd.DataFrame):

    global min_cat
    min_cat = defaultdict(None)

    try:

        sktr_minimum_games_vs_team_games_filter = sktr_min_games_vs_team_games_filter
        goalie_minimum_games_vs_team_games_filter = goalie_min_games_vs_team_games_filter

        df_sktr = df.query(f'{skaters_filter}').copy(deep=True)
        if len(df_sktr) == 0:
            sktr_minimum_games_vs_team_games_filter = minimum_one_game_filter
            goalie_minimum_games_vs_team_games_filter = minimum_one_game_filter

            df_sktr = df.query(f'{skaters_filter}').copy(deep=True)

        df_f = df.query(f'{forwards_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter}').copy(deep=True)

        # get list of dataframe columns
        columns = list(df.columns)

        #######################################
        # Skaters
        for cat in sktr_cumulative_stat_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None
        # also...
        min_cat[f'sktr shots_powerplay'] = df_sktr['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None
        # also...
        min_cat[f'sktr sog_pp_pg'] = df_sktr['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None
        # also...
        min_cat[f'sktr sog_pp_p60'] = df_sktr['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in columns else None

        #######################################
        # Forwards
        for cat in sktr_cumulative_stat_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None
        # also...
        min_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None
        # also...
        min_cat[f'f sog_pp_pg'] = df_f['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None
        # also...
        min_cat[f'f sog_pp_p60'] = df_f['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in columns else None

        #######################################
        # Defense
        for cat in sktr_cumulative_stat_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None
        # also...
        min_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].min() if 'shots_powerplay' in columns else None

        for cat in sktr_per_game_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None
        # also...
        min_cat[f'd sog_pp_pg'] = df_d['sog_pp_pg'].min() if 'sog_pp_pg' in columns else None

        for cat in sktr_per_60_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None
        # also...
        min_cat[f'd sog_pp_p60'] = df_d['sog_pp_p60'].min() if 'sog_pp_p60' in columns else None

        for cat in sktr_cumulative_stat_z_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None

        for cat in sktr_per_game_z_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None

        for cat in sktr_per_60_z_categories:
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in columns else None

        #######################################
        # Goalies
        for cat in goalie_cumulative_stat_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        for cat in goalie_per_game_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        for cat in goalie_per_60_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        for cat in goalie_cumulative_stat_z_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        for cat in goalie_per_game_z_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        for cat in goalie_per_60_z_categories:
            min_cat[cat] = df_g[cat].min() if cat in columns else None

        #######################################
        # Summary z-scores
        #######################################
        # cumulative stats
        #######################################
        # skaters
        for cat in sktr_cumulative_stat_summary_z_scores:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in df_f.columns else None
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in df_f.columns else None
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in df_d.columns else None

        # goalie
        for cat in g_cumulative_stat_summary_z_scores:
            min_cat[f'g {cat}'] = df_g[cat].min() if cat in df_g.columns else None

        #######################################
        # per game stats
        #######################################
        # skaters
        for cat in sktr_per_game_summary_z_scores:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in df_f.columns else None
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in df_f.columns else None
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in df_d.columns else None

        # goalie
        for cat in g_per_game_summary_z_scores:
            min_cat[f'g {cat}'] = df_g[cat].min() if cat in df_g.columns else None

        #######################################
        # per 60 stats
        #######################################
        # skaters
        for cat in sktr_per_60_summary_z_scores:
            min_cat[f'sktr {cat}'] = df_sktr[cat].min() if cat in df_f.columns else None
            min_cat[f'f {cat}'] = df_f[cat].min() if cat in df_f.columns else None
            min_cat[f'd {cat}'] = df_d[cat].min() if cat in df_d.columns else None

        # goalie
        for cat in g_per_60_summary_z_scores:
            min_cat[f'g {cat}'] = df_g[cat].min() if cat in df_g.columns else None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_minimums()')

    return

def calc_scoring_category_means(df: pd.DataFrame):

    global mean_cat
    mean_cat = defaultdict(None)

    try:

        sktr_minimum_games_vs_team_games_filter = sktr_min_games_vs_team_games_filter
        goalie_minimum_games_vs_team_games_filter = goalie_min_games_vs_team_games_filter

        df_sktr = df.query(f'{skaters_filter}').copy(deep=True)
        if len(df_sktr) == 0:
            sktr_minimum_games_vs_team_games_filter = minimum_one_game_filter
            goalie_minimum_games_vs_team_games_filter = minimum_one_game_filter

            df_sktr = df.query(f'{skaters_filter}').copy(deep=True)

        df_f = df.query(f'{forwards_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter}').copy(deep=True)

        # get list of dataframe columns
        columns = list(df.columns)

        #######################################
        # Skaters
        for cat in sktr_cumulative_stat_categories:
            mean_cat[f'sktr {cat}'] = df_sktr [cat].mean() if cat in columns else None
        # also...
        mean_cat[f'sktr shots_powerplay'] = df_sktr['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'sktr penalties'] = df_sktr['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            mean_cat[f'sktr {cat}'] = df_sktr [cat].mean() if cat in columns else None
        # also...
        mean_cat[f'sktr sog_pp_pg'] = df_sktr['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'sktr penalties_pg'] = df_sktr['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            mean_cat[f'sktr {cat}'] = df_sktr [cat].mean() if cat in columns else None
        # also...
        mean_cat[f'sktr sog_pp_p60'] = df_sktr['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'sktr penalties_p60'] = df_sktr['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Forwards
        for cat in sktr_cumulative_stat_categories:
            mean_cat[f'f {cat}'] = df_f[cat].mean() if cat in columns else None
        mean_cat[f'f shots_powerplay'] = df_f['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'f penalties'] = df_f['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            mean_cat[f'f {cat}'] = df_f[cat].mean() if cat in columns else None
        # also...
        mean_cat[f'f sog_pp_pg'] = df_f['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'f penalties_pg'] = df_f['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            mean_cat[f'f {cat}'] = df_f[cat].mean() if cat in columns else None
        # also...
        mean_cat[f'f sog_pp_p60'] = df_f['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'f penalties_p60'] = df_f['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Defense
        for cat in sktr_cumulative_stat_categories:
            mean_cat[f'd {cat}'] = df_d[cat].mean() if cat in columns else None
        # also...
        mean_cat[f'd shots_powerplay'] = df_d['shots_powerplay'].mean() if 'shots_powerplay' in columns else None
        mean_cat[f'd penalties'] = df_d['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            mean_cat[f'd {cat}'] = df_d[cat].mean() if cat in columns else None
        # also...
        mean_cat[f'd sog_pp_pg'] = df_d['sog_pp_pg'].mean() if 'sog_pp_pg' in columns else None
        mean_cat[f'd penalties_pg'] = df_d['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            mean_cat[f'd {cat}'] = df_d[cat].mean() if cat in columns else None
        # also...
        mean_cat[f'd sog_pp_p60'] = df_d['sog_pp_p60'].mean() if 'sog_pp_p60' in columns else None
        mean_cat[f'd penalties_p60'] = df_d['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Goalies
        for cat in goalie_cumulative_stat_categories:
            mean_cat[cat] = df_g[cat].mean() if cat in columns else None

        for cat in goalie_per_game_categories:
            mean_cat[cat] = df_g[cat].mean() if cat in columns else None

        for cat in goalie_per_60_categories:
            mean_cat[cat] = df_g[cat].mean() if cat in columns else None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_means()')

    return

def calc_scoring_category_std_deviations(df: pd.DataFrame):

    global std_cat
    std_cat = defaultdict(None)

    try:

        sktr_minimum_games_vs_team_games_filter = sktr_min_games_vs_team_games_filter
        goalie_minimum_games_vs_team_games_filter = goalie_min_games_vs_team_games_filter

        df_sktr = df.query(f'{skaters_filter}').copy(deep=True)
        if len(df_sktr) == 0:
            sktr_minimum_games_vs_team_games_filter = minimum_one_game_filter
            goalie_minimum_games_vs_team_games_filter = minimum_one_game_filter

            df_sktr = df.query(f'{skaters_filter}').copy(deep=True)

        df_f = df.query(f'{forwards_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter}').copy(deep=True)

        # get list of dataframe columns
        columns = list(df.columns)

        #######################################
        # Skaters
        for cat in sktr_cumulative_stat_categories:
            std_cat[f'sktr {cat}'] = df_sktr[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties'] = df_sktr['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            std_cat[f'sktr {cat}'] = df_sktr[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_pg'] = df_sktr['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            std_cat[f'sktr {cat}'] = df_sktr[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_p60'] = df_sktr['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Forwards
        for cat in sktr_cumulative_stat_categories:
            std_cat[f'f {cat}'] = df_f[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties'] = df_f['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            std_cat[f'f {cat}'] = df_f[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_pg'] = df_f['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            std_cat[f'f {cat}'] = df_f[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_p60'] = df_f['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Defense
        for cat in sktr_cumulative_stat_categories:
            std_cat[f'd {cat}'] = df_d[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties'] = df_d['penalties'].mean() if 'penalties' in columns else None

        for cat in sktr_per_game_categories:
            std_cat[f'd {cat}'] = df_d[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_pg'] = df_d['penalties_pg'].mean() if 'penalties_pg' in columns else None

        for cat in sktr_per_60_categories:
            std_cat[f'd {cat}'] = df_d[cat].std() if cat in columns else None
        # also...
        std_cat[f'sktr penalties_p60'] = df_d['penalties_p60'].mean() if 'penalties_p60' in columns else None

        #######################################
        # Goalies
        for cat in goalie_cumulative_stat_categories:
            std_cat[cat] = df_g[cat].std() if cat in columns else None

        # also need goals_against, used when calculatikng gaa z-scores
        std_cat['goals_against'] = df_g['goals_against'].std()

        for cat in goalie_per_game_categories:
            std_cat[cat] = df_g[cat].std() if cat in columns else None

        for cat in goalie_per_60_categories:
            std_cat[cat] = df_g[cat].std() if cat in columns else None

    except:
        print(f'{traceback.format_exc()} in calc_scoring_category_std_deviations()')

    return

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

        df_sktr = df.query(f'{skaters_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_f = df.query(f'{forwards_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter} and {minimum_one_game_filter}').copy(deep=True)

        ##########################################################################
        # skaters
        ##########################################################################
        #  goals
        df['z_goals'] = (df_sktr['goals'] - mean_cat['sktr goals']) / std_cat['sktr goals']
        # calc_z_cat_vorp(df=df, z_column='z_goals', pos='f_and_d')

        ##########################################################################
        # assists
        df['z_assists'] = (df_sktr['assists'] - mean_cat['sktr assists']) / std_cat['sktr assists']
        # calc_z_cat_vorp(df=df, z_column='z_assists', pos='f_and_d')

        ##########################################################################
        # penalty minutes
        df['z_pim'] = (df_sktr['pim'] - mean_cat['sktr pim']) / std_cat['sktr pim']
        # calc_z_cat_vorp(df=df, z_column='z_pim', pos='f_and_d')
        # penalties
        df['z_penalties'] = df_sktr['penalties'].apply(lambda x: ((x - mean_cat['sktr penalties']) / std_cat['sktr penalties']) if std_cat['sktr penalties'] != 0 else np.nan)
        # calc_z_cat_vorp(df=df, z_column='z_penalties', pos='f_and_d')

        ##########################################################################
        # shots
        df['z_shots'] = (df_sktr['shots'] - mean_cat['sktr shots']) / std_cat['sktr shots']
        # calc_z_cat_vorp(df=df, z_column='z_shots', pos='f_and_d')

        ##########################################################################
        # powerplay points
        df['z_points_pp'] = (df_sktr['points_pp'] - mean_cat['sktr points_pp']) / std_cat['sktr points_pp']
        # calc_z_cat_vorp(df=df, z_column='z_points_pp', pos='f_and_d')

        ##########################################################################
        # hits
        df['z_hits'] = (df_sktr['hits'] - mean_cat['sktr hits']) / std_cat['sktr hits']
        # calc_z_cat_vorp(df=df, z_column='z_hits', pos='f_and_d')

        ##########################################################################
        # blocked shots
        df['z_blocked'] = (df_sktr['blocked'] - mean_cat['sktr blocked']) / std_cat['sktr blocked']
        # calc_z_cat_vorp(df=df, z_column='z_blocked', pos='f_and_d')

        ##########################################################################
        # takeaways
        df['z_takeaways'] = (df_sktr['takeaways'] - mean_cat['sktr takeaways']) / std_cat['sktr takeaways']
        # calc_z_cat_vorp(df=df, z_column='z_takeaways', pos='f_and_d')

        ##########################################################################
        # forwards
        ##########################################################################
         # points
        df['z_points'] = (df_f['points'] - mean_cat['f points']) / std_cat['f points']

        ##########################################################################
        # defense
        ##########################################################################
        # points
        df.loc[df_d.index, 'z_points'] = (df_d['points'] - mean_cat['d points']) / std_cat['d points']
        # calc_z_cat_vorp(df=df, z_column='z_points', pos='f_and_d')

        # ##########################################################################
        # #  goals
        # df.loc[df_d.index, 'z_goals'] = (df_d['goals'] - mean_cat['d goals']) / std_cat['d goals']

        # ##########################################################################
        # # assists
        # df.loc[df_d.index, 'z_assists'] = (df_d['assists'] - mean_cat['d assists']) / std_cat['d assists']

        # ##########################################################################
        # # penalty minutes
        # df.loc[df_d.index, 'z_pim'] = (df_d['pim'] - mean_cat['d pim']) / std_cat['d pim']

        # ##########################################################################
        # # shots
        # df.loc[df_d.index, 'z_shots'] = (df_d['shots'] - mean_cat['d shots']) / std_cat['d shots']

        # ##########################################################################
        # # powerplay points
        # df.loc[df_d.index, 'z_points_pp'] = (df_d['points_pp'] - mean_cat['d points_pp']) / std_cat['d points_pp']

        # ##########################################################################
        # # hits
        # df.loc[df_d.index, 'z_hits'] = (df_d['hits'] - mean_cat['d hits']) / std_cat['d hits']

        # ##########################################################################
        # # blocked shots
        # df.loc[df_d.index, 'z_blocked'] = (df_d['blocked'] - mean_cat['d blocked']) / std_cat['d blocked']

        # ##########################################################################
        # # takeaways
        # df.loc[df_d.index, 'z_takeaways'] = (df_d['takeaways'] - mean_cat['d takeaways']) / std_cat['d takeaways']

        ##########################################################################
        # goalies
        ##########################################################################
        # wins
        df['z_wins'] = (df_g['wins'] - mean_cat['wins']) / std_cat['wins']
        # calc_z_cat_vorp(df=df, z_column='z_wins', pos='goalie')

        ##########################################################################
        # goals against average
        df['z_gaa'] = 0 - (df_g['goals_against'] - (df_g['games'] * mean_cat['gaa'])) / std_cat['goals_against']
        # calc_z_cat_vorp(df=df, z_column='z_gaa', pos='goalie')

        ##########################################################################
        # saves
        df['z_saves'] = (df_g['saves'] - mean_cat['saves']) / std_cat['saves']
        # calc_z_cat_vorp(df=df, z_column='z_saves', pos='goalie')

        ##########################################################################
        # save %
        # http://hockeygoalies.org/stats/glossary.html
        # ZSCORE = ((Saves) - (Shots * League Average SV%)) / SQRT (Shots * League Average SV% * (1 - League Average SV%))
        ########################
        # In the calculation of league-average save percentage, should I remove the goaltender in question from the totals?
        ########################
        df['z_save%'] = (df_g['saves'] - (df_g['shots_against'] * mean_cat['save%'])) / np.sqrt(df_g['shots_against'] * mean_cat['save%'] * (1 - mean_cat['save%']))
        # calc_z_cat_vorp(df=df, z_column='z_save%', pos='goalie')

        ##########################################################################
        # Overall z-scores
        # cumulative stats
        # calc category z-scores
        df['z_score'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative')
        # calc offensive category z-scores
        df['z_offense'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='offense')
        # calc peripheral category z-scores
        df['z_peripheral'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='peripheral')
        # calc sog+hits+blocks category z-scores
        df['z_sog_hits_blk'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='sog_hits_blk')
        # calc hits+blocks category z-scores
        df['z_hits_blk'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='hits_blk')
        # calc goals+hits+pim category z-scores
        df['z_goals_hits_pim'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='goals_hits_pim')
        # calc hits+pim category z-scores
        df['z_hits_pim'] = calc_z_scores_by_stat_type(df=df, points_type='cumulative', score_type='hits_pim')
        # calc offense category z-combos
        df['z_offense_combo'] = calc_z_combo(df=df, points_type='cumulative', group='offense')
        # calc peripheral category z-combos
        df['z_peripheral_combo'] = calc_z_combo(df=df, points_type='cumulative', group='peripheral')
        # calc category z-combos
        df['z_combo'] = calc_z_combo(df=df, points_type='cumulative')

        # # calculate summary of category z-scores
        # calc_summary_z_cat_vorp(df=df, stat_type='cumulative', vorp_type='cumulative')
        # calc_summary_z_cat_vorp(df=df, stat_type='cumulative', vorp_type='offense')
        # calc_summary_z_cat_vorp(df=df, stat_type='cumulative', vorp_type='peripheral')

    except:
        print(f'{traceback.format_exc()} in calc_cumulative_z_scores()')

    return

def calc_per_game_z_scores(df: pd.DataFrame):

    try:

        df_sktr = df.query(f'{skaters_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_f = df.query(f'{forwards_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter} and {minimum_one_game_filter}').copy(deep=True)

        ##########################################################################
        # skaters
        ##########################################################################
        #  goals-per-game
        df['z_g_pg'] = (df_sktr['g_pg'] - mean_cat['sktr g_pg']) / std_cat['sktr g_pg']

        ##########################################################################
        df['z_a_pg'] = (df_sktr['a_pg'] - mean_cat['sktr a_pg']) / std_cat['sktr a_pg']

        ##########################################################################
        # penalty-minutes-per-game
        df['z_pim_pg'] = (df_sktr['pim_pg'] - mean_cat['sktr pim_pg']) / std_cat['sktr pim_pg']
        # penalties-per-game
        df['z_penalties_pg'] = df_sktr['penalties_pg'].apply(lambda x: ((x - mean_cat['sktr penalties_pg']) / std_cat['sktr penalties_pg']) if std_cat['sktr penalties_pg'] != 0 else np.nan)

        ##########################################################################
        # shots-per-game
        df['z_sog_pg'] = (df_sktr['sog_pg'] - mean_cat['sktr sog_pg']) / std_cat['sktr sog_pg']

        ##########################################################################
        # powerplay-points-per=game
        df['z_ppp_pg'] = (df_sktr['ppp_pg'] - mean_cat['sktr ppp_pg']) / std_cat['sktr ppp_pg']

        ##########################################################################
        # hits-per-game
        df['z_hits_pg'] = (df_sktr['hits_pg'] - mean_cat['sktr hits_pg']) / std_cat['sktr hits_pg']

        ##########################################################################
        df['z_blk_pg'] = (df_sktr['blk_pg'] - mean_cat['sktr blk_pg']) / std_cat['sktr blk_pg']

        ##########################################################################
        # takeaways-per-game
        df['z_tk_pg'] = (df_sktr['tk_pg'] - mean_cat['sktr tk_pg']) / std_cat['sktr tk_pg']

        ##########################################################################
        # forwards
        ##########################################################################
        # points-per-game
        df['z_pts_pg'] = (df_f['pts_pg'] - mean_cat['f pts_pg']) / std_cat['f pts_pg']

        ##########################################################################
        # defense
        ##########################################################################
        # points-per-game
        df.loc[df_d.index, 'z_pts_pg'] = (df_d['pts_pg'] - mean_cat['d pts_pg']) / std_cat['d pts_pg']

        # ##########################################################################
        # #  goals-per-game
        # df.loc[df_d.index, 'z_g_pg'] = (df_d['g_pg'] - mean_cat['d g_pg']) / std_cat['d g_pg']

        # ##########################################################################
        # # assists-per-game
        # df.loc[df_d.index, 'z_a_pg'] = (df_d['a_pg'] - mean_cat['d a_pg']) / std_cat['d a_pg']

        # ##########################################################################
        # # penalty-minutes-per-game
        # df.loc[df_d.index, 'z_pim_pg'] = (df_d['pim_pg'] - mean_cat['d pim_pg']) / std_cat['d pim_pg']

        # ##########################################################################
        # # shots-per-game
        # df.loc[df_d.index, 'z_sog_pg'] = (df_d['sog_pg'] - mean_cat['d sog_pg']) / std_cat['d sog_pg']

        # ##########################################################################
        # # powerplay-points-per-game
        # df.loc[df_d.index, 'z_ppp_pg'] = (df_d['ppp_pg'] - mean_cat['d ppp_pg']) / std_cat['d ppp_pg']

        # ##########################################################################
        # # hits-per-game
        # df.loc[df_d.index, 'z_hits_pg'] = (df_d['hits_pg'] - mean_cat['d hits_pg']) / std_cat['d hits_pg']

        # ##########################################################################
        # # blocked-shots-per-game
        # df.loc[df_d.index, 'z_blk_pg'] = (df_d['blk_pg'] - mean_cat['d blk_pg']) / std_cat['d blk_pg']

        # ##########################################################################
        # # takeaways-per-game
        # df.loc[df_d.index, 'z_tk_pg'] = (df_d['tk_pg'] - mean_cat['d tk_pg']) / std_cat['d tk_pg']

        ##########################################################################
        # goalies
        ##########################################################################
        #  wins per game
        df['z_wins_pg'] = (df_g['wins_pg'] - mean_cat['wins_pg']) / std_cat['wins_pg']

        ##########################################################################
        # gaa per game
        df['z_gaa_pg'] = 0 - (df_g['gaa_pg'] - mean_cat['gaa_pg']) / std_cat['gaa_pg']

        ##########################################################################
        # saves per game
        df['z_saves_pg'] = (df_g['saves_pg'] - mean_cat['saves_pg']) / std_cat['saves_pg']

        ##########################################################################
        # save% per game
        df['z_save%_pg'] = (df_g['save%_pg'] - mean_cat['save%_pg']) / std_cat['save%_pg']

        ##########################################################################
        # Overall z-scores
        # per-game
        df['z_score_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game')
        # calc offensive category z-scores
        df['z_offense_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='offense')
        # calc peripheral category z-scores
        df['z_peripheral_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='peripheral')
        # calc sog+hits+blocks category z-scores
        df['z_sog_hits_blk_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='sog_hits_blk')
        # calc hits+blocks category z-scores
        df['z_hits_blk_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='hits_blk')
        # calc goals+hits+pim category z-scores
        df['z_goals_hits_pim_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='goals_hits_pim')
        # calc hits+pim category z-scores
        df['z_hits_pim_pg'] = calc_z_scores_by_stat_type(df=df, points_type='per game', score_type='hits_pim')
        # calc offense category pg z-combos
        df['z_offense_combo_pg'] = calc_z_combo(df=df, points_type='per game', group='offense')
        # calc peripheral category pg z-combos
        df['z_peripheral_combo_pg'] = calc_z_combo(df=df, points_type='per game', group='peripheral')
        # calc category pg z-combos
        df['z_combo_pg'] = calc_z_combo(df=df, points_type='per game')

    except:
        print(f'{traceback.format_exc()} in calc_per_game_z_scores()')

    return

def calc_per_60_z_scores(df: pd.DataFrame):

    try:

        df_sktr = df.query(f'{skaters_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_f = df.query(f'{forwards_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_d = df.query(f'{defense_filter} and {minimum_one_game_filter}').copy(deep=True)
        df_g = df.query(f'{goalie_filter} and {minimum_one_game_filter}').copy(deep=True)

        ##########################################################################
        # skaters
        ##########################################################################
        #  goals-per-60
        df['z_g_p60'] = (df_sktr['g_p60'] - mean_cat['sktr g_p60']) / std_cat['sktr g_p60']

        ##########################################################################
        # assists-per-60
        df['z_a_p60'] = (df_sktr['a_p60'] - mean_cat['sktr a_p60']) / std_cat['sktr a_p60']

        ##########################################################################
        # penalty-minutes-per-60
        df['z_pim_p60'] = (df_sktr['pim_p60'] - mean_cat['sktr pim_p60']) / std_cat['sktr pim_p60']
        # penalties-per-60
        df['z_penalties_p60'] = df_sktr['penalties_p60'].apply(lambda x: ((x - mean_cat['sktr penalties_p60']) / std_cat['sktr penalties_p60']) if std_cat['sktr penalties_p60'] != 0 else np.nan)

        ##########################################################################
        # shots-per-60
        df['z_sog_p60'] = (df_sktr['sog_p60'] - mean_cat['sktr sog_p60']) / std_cat['sktr sog_p60']

        ##########################################################################
        # powerplay-points-per-60
        df['z_ppp_p60'] = (df_sktr['ppp_p60'] - mean_cat['sktr ppp_p60']) / std_cat['sktr ppp_p60']

        ##########################################################################
        # hits-per-60
        df['z_hits_p60'] = (df_sktr['hits_p60'] - mean_cat['sktr hits_p60']) / std_cat['sktr hits_p60']

        ##########################################################################
        # blocked-shots-per-60
        df['z_blk_p60'] = (df_sktr['blk_p60'] - mean_cat['sktr blk_p60']) / std_cat['sktr blk_p60']

        ##########################################################################
        # takeaways-per-60
        df['z_tk_p60'] = (df_sktr['tk_p60'] - mean_cat['sktr tk_p60']) / std_cat['sktr tk_p60']

        ##########################################################################
        # forwards
        ##########################################################################
        # points-per-60
        df['z_pts_p60'] = (df_f['pts_p60'] - mean_cat['f pts_p60']) / std_cat['f pts_p60']

        ##########################################################################
        # defense
        ##########################################################################
        # points-per-60
        df.loc[df_d.index, 'z_pts_p60'] = (df_d['pts_p60'] - mean_cat['d pts_p60']) / std_cat['d pts_p60']

        # ##########################################################################
        # #  goals-per-60
        # df.loc[df_d.index, 'z_g_p60'] = (df_d['g_p60'] - mean_cat['d g_p60']) / std_cat['d g_p60']

        # ##########################################################################
        # # assists-per-60
        # df.loc[df_d.index, 'z_a_p60'] = (df_d['a_p60'] - mean_cat['d a_p60']) / std_cat['d a_p60']

        # ##########################################################################
        # # penalty-minutes-per-60
        # df.loc[df_d.index, 'z_pim_p60'] = (df_d['pim_p60'] - mean_cat['d pim_p60']) / std_cat['d pim_p60']

        # ##########################################################################
        # # shots-per-60
        # df.loc[df_d.index, 'z_sog_p60'] = (df_d['sog_p60'] - mean_cat['d sog_p60']) / std_cat['d sog_p60']

        # ##########################################################################
        # # powerplay-points-per-60
        # df.loc[df_d.index, 'z_ppp_p60'] = (df_d['ppp_p60'] - mean_cat['d ppp_p60']) / std_cat['d ppp_p60']

        # ##########################################################################
        # # hits-per-60
        # df.loc[df_d.index, 'z_hits_p60'] = (df_d['hits_p60'] - mean_cat['d hits_p60']) / std_cat['d hits_p60']

        # ##########################################################################
        # # blocked-shots-per-60
        # df.loc[df_d.index, 'z_blk_p60'] = (df_d['blk_p60'] - mean_cat['d blk_p60']) / std_cat['d blk_p60']

        # ##########################################################################
        # # takeaways-per-60
        # df.loc[df_d.index, 'z_tk_p60'] = (df_d['tk_p60'] - mean_cat['d tk_p60']) / std_cat['d tk_p60']

        ##########################################################################
        # goalies
        ##########################################################################
        #  wins per 60
        df['z_wins_p60'] = (df_g['wins_p60'] - mean_cat['wins_p60']) / std_cat['wins_p60']

        ##########################################################################
        # gaa per 60
        df['z_gaa_p60'] = 0 - (df_g['gaa_p60'] - mean_cat['gaa_p60']) / std_cat['gaa_p60']

        ##########################################################################
        # saves per 60
        df['z_saves_p60'] = (df_g['saves_p60'] - mean_cat['saves_p60']) / std_cat['saves_p60']

        ##########################################################################
        # save% per 60
        df['z_save%_p60'] = (df_g['save%_p60'] - mean_cat['save%_p60']) / std_cat['save%_p60']

        ##########################################################################
        # Overall z-scores
        # calc per-60 z-scores
        df['z_score_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60')
        # calc offensive category z-scores
        df['z_offense_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='offense')
        # calc peripheral category z-scores
        df['z_peripheral_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='peripheral')
        # calc sog+hits+blocks category z-scores
        df['z_sog_hits_blk_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='sog_hits_blk')
        # calc hits+blocks category z-scores
        df['z_hits_blk_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='hits_blk')
        # calc goals+hits+pim category z-scores
        df['z_goals_hits_pim_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='goals_hits_pim')
        # calc hits+pim category z-scores
        df['z_hits_pim_p60'] = calc_z_scores_by_stat_type(df=df, points_type='per 60', score_type='hits_pim')
        # calc offense category p60 z-combos
        df['z_offense_combo_p60'] = calc_z_combo(df=df, points_type='per 60', group='offense')
        # calc peripheral category p60 z-combos
        df['z_peripheral_combo_p60'] = calc_z_combo(df=df, points_type='per 60', group='peripheral')
        # calc category p60 z-combos
        df['z_combo_p60'] = calc_z_combo(df=df, points_type='per 60')

    except:
        print(f'{traceback.format_exc()} in calc_per_60_z_scores()')

    return

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

def calc_summary_z_scores_vorp(df: pd.DataFrame, stat_type: str='cumulative', vorp_type: str='cumulative'):

    # https://www.espn.com/fantasy/hockey/story/_/id/17744712/fantasy-hockey-upgrade-defense-downgrade-centers-drafts

    try:

        # sktr_minimum_games = sktr_min_games_vs_team_games_filter
        # g_minimum_games = goalie_min_games_vs_team_games_filter

        # if vorp_type == 'cumulative':
        #     sort_column = 'z_score'
        # elif vorp_type == 'offense':
        #     sort_column = 'z_offense'
        # elif vorp_type == 'peripheral':
        #     sort_column = 'z_peripheral'

        # if stat_type == 'per game':
        #     sort_column = f'{sort_column}_pg'
        # elif stat_type == 'per 60 minutes':
        #     sort_column = f'{sort_column}_p60'

        # if season.SEASON_HAS_STARTED is True and season.type == 'R':
        #     ##########################################################################
        #     # Need to add "pool_team" column if season has started, to get a proper count of Fs, Ds, and Gs that are drafted
        #     # To then find the replacement player
        #     sql = textwrap.dedent(f'''\
        #         select ptr.player_id, pt.name as pool_team
        #         from PoolTeamRoster ptr
        #              left outer join Player p on p.id=ptr.player_id
        #              left outer join PoolTeam pt on pt.id=ptr.poolteam_id
        #         where pt.pool_id={pool.id} and p.active=1'''
        #     )
        #     df_pool_team_players = pd.read_sql(sql=sql, con=get_db_connection())
        #     # set indexes to player_id
        #     df.set_index('player_id', inplace=True)
        #     df_pool_team_players.set_index('player_id', inplace=True)
        #     df['pool_team'] = df_pool_team_players['pool_team']
        #     df['pool_team'] = df['pool_team'].apply(lambda x: '' if x is None or pd.isna(x) else x)
        #     df.reset_index(inplace=True)

        #     # get number of forward & defense players, & goalies, that are on rostered on pool teams & not on IR & not in minors
        #     f_rostered = len(df.query(f'{forwards_filter} and pool_team!="" and minors==""'))
        #     d_rostered = len(df.query(f'{defense_filter} and pool_team!="" and minors==""'))
        #     g_rostered = len(df.query(f'{goalie_filter} and pool_team!="" and minors==""'))

        #     df_f = df.query(f'{forwards_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(f_rostered + 1)
        #     # if len(df_f.index) == 0:
        #     #     df_f = df.query(f'{forwards_filter} and {sktr_minimum_games}').sort_values(sort_column, ascending=False).tail(1)

        #     df_d = df.query(f'{defense_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(d_rostered + 1)
        #     # if len(df_d.index) == 0:
        #     #     df_d = df.query(f'{defense_filter} and {sktr_minimum_games}').sort_values(sort_column, ascending=False).tail(1)

        #     if vorp_type == 'cumulative':
        #         df_g = df.query(f'{goalie_filter} and {g_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(g_rostered + 1)
        #         # if len(df_g.index) == 0:
        #         #     df_g = df.query(f'{goalie_filter} and {g_minimum_games}').sort_values(sort_column, ascending=False).tail(1)

        # else:
        #     # get number of forward & defense players required to fill out bench slots & active skater slot
        #     df_f = df.query(f'{forwards_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        #     df_d = df.query(f'{defense_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        #     df_sktrs = pd.concat([df_f, df_d]).sort_values(sort_column, ascending=False).head(sktr_number_of_highest_rated)
        #     f_sktrs = len(df_sktrs.query(f'{forwards_filter}'))
        #     d_sktrs = len(df_sktrs.query(f'{defense_filter}'))

        #     df_f = df.query(f'{forwards_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + f_sktrs + 1)
        #     df_d = df.query(f'{defense_filter} and {sktr_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + d_sktrs + 1)
        #     if vorp_type == 'cumulative':
        #         df_g = df.query(f'{goalie_filter} and {g_minimum_games} and minors=="" and (injury_status=="" or injury_status.str.startswith("DAY-TO-DAY - "))').sort_values(sort_column, ascending=False).head(g_number_of_highest_rated + 1)

        sort_column = 'toi_sec'

        # get number of forward & defense players required to fill out bench slots & active skater slot
        # df_f = df.query(f'{forwards_filter} and nhl_roster_status=="y"').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        df_f = df.query(f'{forwards_filter}').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        # df_d = df.query(f'{defense_filter} and nhl_roster_status=="y"').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        df_d = df.query(f'{defense_filter}').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + sktr_number_of_highest_rated).tail(sktr_number_of_highest_rated)
        df_sktrs = pd.concat([df_f, df_d]).sort_values(sort_column, ascending=False).head(sktr_number_of_highest_rated)
        f_sktrs = len(df_sktrs.query(f'{forwards_filter}'))
        d_sktrs = len(df_sktrs.query(f'{defense_filter}'))

        # df_f = df.query(f'{forwards_filter} and nhl_roster_status=="y"').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + f_sktrs + 1)
        df_f = df.query(f'{forwards_filter}').sort_values(sort_column, ascending=False).head(f_number_of_highest_rated + f_sktrs + 1)
        # df_d = df.query(f'{defense_filter} and nhl_roster_status=="y"').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + d_sktrs + 1)
        df_d = df.query(f'{defense_filter}').sort_values(sort_column, ascending=False).head(d_number_of_highest_rated + d_sktrs + 1)
        if vorp_type == 'cumulative':
            # df_g = df.query(f'{goalie_filter} and nhl_roster_status=="y"').sort_values(sort_column, ascending=False).head(g_number_of_highest_rated + 1)
            df_g = df.query(f'{goalie_filter}').sort_values(sort_column, ascending=False).head(g_number_of_highest_rated + 1)

        f_repl_level_player_id = (df_f.tail(1)['player_id']).values[0]
        d_repl_level_player_id = (df_d.tail(1)['player_id']).values[0]
        if vorp_type == 'cumulative':
            g_repl_level_player_id = (df_g.tail(1)['player_id']).values[0]

        f_repl_level_idx = df.query(f'player_id=={f_repl_level_player_id}').index[0]
        d_repl_level_idx = df.query(f'player_id=={d_repl_level_player_id}').index[0]
        if vorp_type == 'cumulative':
            g_repl_level_idx = df.query(f'player_id=={g_repl_level_player_id}').index[0]

        ##########################################################################
        # Overall z-scores
        # cumulative stats
        if stat_type == 'cumulative' and vorp_type == 'cumulative':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_score']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_score']
            g_repl_level_value = df.loc[g_repl_level_idx, 'z_score']
            df['z_score_vorp'] = df.apply(lambda x: x['z_score'] - f_repl_level_value
                                                    if x['pos'] in forward_position_codes
                                                    else x['z_score'] - d_repl_level_value
                                                        if x['pos']==defense_position_code
                                                        else x['z_score'] - g_repl_level_value,
                                        axis='columns')

        if stat_type == 'cumulative' and vorp_type == 'offense':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_offense']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_offense']
            df['z_offense_vorp'] = df.apply(lambda x: x['z_offense'] - f_repl_level_value
                                                    if x['pos'] in forward_position_codes
                                                    else x['z_offense'] - d_repl_level_value
                                                        if x['pos']==defense_position_code
                                                        else x['z_offense'],
                                            axis='columns')

        if stat_type == 'cumulative' and vorp_type == 'peripheral':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_peripheral']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_peripheral']
            df['z_peripheral_vorp'] = df.apply(lambda x: x['z_peripheral'] - f_repl_level_value
                                                        if x['pos'] in forward_position_codes
                                                        else x['z_peripheral'] - d_repl_level_value
                                                                if x['pos']==defense_position_code
                                                                else x['z_peripheral'],
                                                axis='columns')

        # per-game
        if stat_type == 'per game' and vorp_type == 'cumulative':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_score_pg']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_score_pg']
            g_repl_level_value = df.loc[g_repl_level_idx, 'z_score_pg']
            df['z_score_pg_vorp'] = df.apply(lambda x: x['z_score_pg'] - f_repl_level_value
                                                        if x['pos'] in forward_position_codes
                                                        else x['z_score_pg'] - d_repl_level_value
                                                            if x['pos']==defense_position_code
                                                            else x['z_score_pg'] - g_repl_level_value,
                                                axis='columns')

        if stat_type == 'per game' and vorp_type == 'offense':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_offense_pg']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_offense_pg']
            df['z_offense_pg_vorp'] = df.apply(lambda x: x['z_offense_pg'] - f_repl_level_value
                                                        if x['pos'] in forward_position_codes
                                                        else x['z_offense_pg'] - d_repl_level_value
                                                                if x['pos']==defense_position_code
                                                                else x['z_offense_pg'],
                                                axis='columns')

        if stat_type == 'per game' and vorp_type == 'peripheral':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_peripheral_pg']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_peripheral_pg']
            df['z_peripheral_pg_vorp'] = df.apply(lambda x: x['z_peripheral_pg'] - f_repl_level_value
                                                            if x['pos'] in forward_position_codes
                                                            else x['z_peripheral_pg'] - d_repl_level_value
                                                                if x['pos']==defense_position_code
                                                                else x['z_peripheral_pg'],
                                                axis='columns')

        # per-60
        if stat_type == 'per 60 minutes' and vorp_type == 'cumulative':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_score_p60']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_score_p60']
            g_repl_level_value = df.loc[g_repl_level_idx, 'z_score_p60']
            df['z_score_p60_vorp'] = df.apply(lambda x: x['z_score_p60'] - f_repl_level_value
                                                        if x['pos'] in forward_position_codes
                                                        else x['z_score_p60'] - d_repl_level_value
                                                            if x['pos']==defense_position_code
                                                            else x['z_score_p60'] - g_repl_level_value,
                                            axis='columns')

        if stat_type == 'per 60 minutes' and vorp_type == 'offense':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_offense_p60']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_offense_p60']
            df['z_offense_p60_vorp'] = df.apply(lambda x: x['z_offense_p60'] - f_repl_level_value
                                                            if x['pos'] in forward_position_codes
                                                            else x['z_offense_p60'] - d_repl_level_value
                                                                if x['pos']==defense_position_code
                                                                else x['z_offense_p60'],
                                                axis='columns')

        if stat_type == 'per 60 minutes' and vorp_type == 'peripheral':
            f_repl_level_value = df.loc[f_repl_level_idx, 'z_peripheral_p60']
            d_repl_level_value = df.loc[d_repl_level_idx, 'z_peripheral_p60']
            df['z_peripheral_p60_vorp'] = df.apply(lambda x: x['z_peripheral_p60'] - f_repl_level_value
                                                            if x['pos'] in forward_position_codes
                                                            else x['z_peripheral_p60'] - d_repl_level_value
                                                                if x['pos']==defense_position_code
                                                                else x['z_peripheral_p60'],
                                                    axis='columns')

    except:
        print(f'{traceback.format_exc()} in calc_summary_z_scores_vorp()')

    return

def calc_z_scores_by_stat_type(df: pd.DataFrame, points_type: str='cumulative', score_type: str='total') -> pd.Series:

    if points_type == 'cumulative':
        # overall rank, based on Fantrax categories
        g_categories_count = ['z_wins', 'z_saves']
        g_categories_ratio = ['z_gaa', 'z_save%']
        sktr_hits_blk_categories = ['z_hits', 'z_blocked']
        sktr_sog_hits_blk_categories = ['z_shots'] + sktr_hits_blk_categories
        sktr_goals_hits_pim_categories = ['z_goals', 'z_hits', 'z_pim']
        # sktr_goals_hits_pim_categories = ['z_goals', 'z_hits', 'z_penalties']
        sktr_hits_pim_categories = ['z_hits', 'z_pim']
        # sktr_hits_pim_categories = ['z_hits', 'z_penalties']
        f_offense_categories = ['z_goals', 'z_assists', 'z_shots', 'z_points_pp']
        d_offense_categories = ['z_points'] + f_offense_categories
        sktr_peripheral_categories = ['z_hits', 'z_blocked', 'z_pim', 'z_takeaways']
        # sktr_peripheral_categories = ['z_hits', 'z_blocked', 'z_penalties', 'z_takeaways']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = ['z_points'] + f_categories
    elif points_type == 'per game':
        g_categories_count = ['z_wins_pg', 'z_saves_pg']
        g_categories_ratio = ['z_gaa_pg', 'z_save%_pg']
        sktr_hits_blk_categories = ['z_hits_pg', 'z_blk_pg']
        sktr_sog_hits_blk_categories = ['z_sog_pg'] + sktr_hits_blk_categories
        # sktr_goals_hits_pim_categories = ['z_g_pg', 'z_hits_pg', 'z_pim_pg']
        sktr_goals_hits_pim_categories = ['z_g_pg', 'z_hits_pg', 'z_penalties_pg']
        # sktr_hits_pim_categories = ['z_hits_pg', 'z_pim_pg']
        sktr_hits_pim_categories = ['z_hits_pg', 'z_penalties_pg']
        f_offense_categories = ['z_g_pg', 'z_a_pg', 'z_sog_pg', 'z_ppp_pg']
        d_offense_categories = ['z_pts_pg'] + f_offense_categories
        # sktr_peripheral_categories = ['z_hits_pg', 'z_blk_pg', 'z_pim_pg', 'z_tk_pg']
        sktr_peripheral_categories = ['z_hits_pg', 'z_blk_pg', 'z_penalties_pg', 'z_tk_pg']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = ['z_pts_pg'] + f_categories
    elif points_type == 'per 60':
        g_categories_count = ['z_wins_p60', 'z_saves_p60']
        g_categories_ratio = ['z_gaa_p60', 'z_save%_p60']
        sktr_hits_blk_categories = ['z_hits_p60', 'z_blk_p60']
        sktr_sog_hits_blk_categories = ['z_sog_p60'] + sktr_hits_blk_categories
        # sktr_goals_hits_pim_categories = ['z_g_p60', 'z_hits_p60', 'z_pim_p60']
        sktr_goals_hits_pim_categories = ['z_g_p60', 'z_hits_p60', 'z_penalties_p60']
        # sktr_hits_pim_categories = ['z_hits_p60', 'z_pim_p60']
        sktr_hits_pim_categories = ['z_hits_p60', 'z_penalties_p60']
        f_offense_categories = ['z_g_p60', 'z_a_p60', 'z_sog_p60', 'z_ppp_p60']
        d_offense_categories = ['z_pts_p60'] + f_offense_categories
        # sktr_peripheral_categories = ['z_hits_p60', 'z_blk_p60', 'z_pim_p60', 'z_tk_p60']
        sktr_peripheral_categories = ['z_hits_p60', 'z_blk_p60', 'z_penalties_p60', 'z_tk_p60']
        f_categories = f_offense_categories + sktr_peripheral_categories
        d_categories = ['z_pts_p60'] + f_categories

    # if vorp is True:
    #     g_categories = [f'{c}_vorp' for c in g_categories]
    #     sktr_peripheral_categories = [f'{c}_vorp' for c in sktr_peripheral_categories]
    #     f_offense_categories = [f'{c}_vorp' for c in f_offense_categories]
    #     f_categories = [f'{c}_vorp' for c in f_categories]
    #     d_offense_categories = [f'{c}_vorp' for c in d_offense_categories]
    #     d_categories = [f'{c}_vorp' for c in d_categories]

    if score_type == 'peripheral':
        d_categories = sktr_peripheral_categories
        f_categories = sktr_peripheral_categories
    elif score_type == 'offense':
        d_categories = d_offense_categories
        f_categories = f_offense_categories
    elif score_type == 'sog_hits_blk':
        d_categories = sktr_sog_hits_blk_categories
        f_categories = sktr_sog_hits_blk_categories
    elif score_type == 'hits_blk':
        d_categories = sktr_hits_blk_categories
        f_categories = sktr_hits_blk_categories
    elif score_type == 'goals_hits_pim':
        d_categories = sktr_goals_hits_pim_categories
        f_categories = sktr_goals_hits_pim_categories
    elif score_type == 'hits_pim':
        d_categories = sktr_hits_pim_categories
        f_categories = sktr_hits_pim_categories
    # else: # score_type == 'total':
    #     d_categories = d_offense_categories + sktr_peripheral_categories
    #     f_categories = f_offense_categories + sktr_peripheral_categories

    # construct z-score categories as string for use in eval()
    d_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in d_categories]), ']'])
    f_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in f_categories]), ']'])
    g_categories_count_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in g_categories_count]), ']'])
    g_categories_ratio_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in g_categories_ratio]), ']'])

    scores: pd.Series = df.apply(lambda x:
                        np.nan
                        if (x['pos'] in forward_position_codes and np.isnan(eval(f_categories_as_eval_str)).all())
                            or
                            (x['pos'] == defense_position_code and np.isnan(eval(d_categories_as_eval_str)).all())
                            or
                            (x['pos'] == goalie_position_code and np.isnan(eval(g_categories_count_as_eval_str)).all() and np.isnan(eval(g_categories_ratio_as_eval_str)).all())
                        else np.nansum([x if x>0 else 0 for x in eval(f_categories_as_eval_str)])
                            if x['pos'] in forward_position_codes
                            else np.nansum([x if x>0 else 0 for x in eval(d_categories_as_eval_str)])
                                if x['pos'] == defense_position_code
                                else np.nansum([x if x>0 else 0 for x in eval(g_categories_count_as_eval_str)] + [x for x in eval(g_categories_ratio_as_eval_str)])
                                     if score_type == 'total'
                                     else np.nan
                        , axis='columns')

    return scores

def calc_z_combo(df: pd.DataFrame, points_type: str='cumulative', group: str='offense_and_peripheral') -> pd.Series:

    # overall rank, based on Fantrax categories
    if points_type == 'cumulative':
        g_score_categories = ['z_wins', 'z_gaa', 'z_saves', 'z_save%']
        f_offense_score_categories = ['z_goals', 'z_assists', 'z_shots', 'z_points_pp']
        d_offense_score_categories = ['z_points'] + f_offense_score_categories
        sktr_peripheral_score_categories = ['z_hits', 'z_blocked', 'z_takeaways', 'z_pim']
        f_score_categories = f_offense_score_categories + sktr_peripheral_score_categories
        d_score_categories = d_offense_score_categories + sktr_peripheral_score_categories
    elif points_type == 'per game':
        g_score_categories = ['z_wins_pg', 'z_gaa_pg', 'z_saves_pg', 'z_save%_pg']
        f_offense_score_categories = ['z_g_pg', 'z_a_pg', 'z_sog_pg', 'z_ppp_pg']
        d_offense_score_categories = ['z_pts_pg'] + f_offense_score_categories
        sktr_peripheral_score_categories = ['z_hits_pg', 'z_blk_pg', 'z_tk_pg', 'z_pim_pg']
        f_score_categories = f_offense_score_categories + sktr_peripheral_score_categories
        d_score_categories = d_offense_score_categories + sktr_peripheral_score_categories
    elif points_type == 'per 60':
        g_score_categories = ['z_wins_p60', 'z_gaa_p60', 'z_saves_p60', 'z_save%_p60']
        f_offense_score_categories = ['z_g_p60', 'z_a_p60', 'z_sog_p60', 'z_ppp_p60']
        d_offense_score_categories = ['z_pts_p60'] + f_offense_score_categories
        sktr_peripheral_score_categories = ['z_hits_p60', 'z_blk_p60', 'z_tk_p60', 'z_pim_p60']
        f_score_categories = f_offense_score_categories + sktr_peripheral_score_categories
        d_score_categories = d_offense_score_categories + sktr_peripheral_score_categories

    # if vorp is True:
    #     goalie_score_categories = [f'{c}_vorp' for c in goalie_score_categories]
    #     defense_score_categories = [f'{c}_vorp' for c in defense_score_categories]
    #     forward_score_categories = [f'{c}_vorp' for c in forward_score_categories]

    # construct z-score categories as string for use in eval()
    if group == 'offense':
        f_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in f_offense_score_categories]), ']'])
        d_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in d_offense_score_categories]), ']'])
        g_score_categories_as_eval_str = []
    elif group == 'peripheral':
        f_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in sktr_peripheral_score_categories]), ']'])
        d_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in sktr_peripheral_score_categories]), ']'])
        g_score_categories_as_eval_str = []
    else: # group == 'offense_and_peripheral':
        f_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in f_score_categories]), ']'])
        d_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in d_score_categories]), ']'])
        g_score_categories_as_eval_str = ''.join(['[', ', '.join([f"x['{c}']" for c in g_score_categories]), ']'])

    if group == 'offense_and_peripheral':
        combos: pd.Series = df.apply(lambda x:
                            np.nan
                            if (x['pos'] in forward_position_codes and np.isnan(eval(f_score_categories_as_eval_str)).all())
                                or
                                (x['pos'] == defense_position_code and np.isnan(eval(d_score_categories_as_eval_str)).all())
                                or
                                (x['pos'] == goalie_position_code and np.isnan(eval(g_score_categories_as_eval_str)).all())
                            else format_z_combo(eval(f_score_categories_as_eval_str))
                                if x['pos'] in forward_position_codes
                                else format_z_combo(eval(d_score_categories_as_eval_str))
                                    if x['pos'] == defense_position_code
                                    else format_z_combo(eval(g_score_categories_as_eval_str))
                            , axis='columns')
    else:
        combos: pd.Series = df.apply(lambda x:
                            np.nan
                            if (x['pos'] in forward_position_codes and np.isnan(eval(f_score_categories_as_eval_str)).all())
                                or
                                (x['pos'] == defense_position_code and np.isnan(eval(d_score_categories_as_eval_str)).all())
                                or
                                (x['pos'] == goalie_position_code)
                            else format_z_combo(eval(f_score_categories_as_eval_str))
                                if x['pos'] in forward_position_codes
                                else format_z_combo(eval(d_score_categories_as_eval_str))
                            , axis='columns')

    return combos

def format_z_combo(li: List):

    z_combo = [0] * 9

    for x in li:
        if round(x,2) >= 3.00:    # Elite
            z_combo[0] += 1
        elif round(x,2) >= 2.00:  # Excellent
            z_combo[1] += 1
        elif round(x,2) >= 1.00:  # Great
            z_combo[2] +=1
        elif round(x,2) >= 0.50:  # Above Average
            z_combo[3] +=1
        elif round(x,2) > 0.00: # Average +
            z_combo[4] +=1
        elif round(x,2) >= -0.50: # Average -
            z_combo[5] +=1
        elif round(x,2) >= -1.00: # Below Average
            z_combo[6] +=1
        elif round(x,2) >= -2.00: # Bad
            z_combo[7] +=1
        else:           # Horrible
            z_combo[8] +=1

    count_of_superior_cats = z_combo[0] + z_combo[1] + z_combo[2] + z_combo[3]

    ret_val = f'{count_of_superior_cats}.{z_combo[0]}{z_combo[1]}{z_combo[2]}{z_combo[3]}-{z_combo[4]}'

    return ret_val

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
        df_game_stats['toi_sec'] = df_game_stats['toi'].apply(lambda x: 0 if x in (None, '') else string_to_time(x))
        df_game_stats['toi_even_sec'] = df_game_stats['toi_even'].apply(lambda x: 0 if x in (None, '') else string_to_time(x))
        df_game_stats['toi_pp_sec'] = df_game_stats['toi_pp'].apply(lambda x: 0 if x in (None, '') else string_to_time(x))
        df_game_stats['team_toi_pp_sec'] = df_game_stats['team_toi_pp'].apply(lambda x: 0 if x in (None, '') else string_to_time(x))
        df_game_stats['toi_sh_sec'] = df_game_stats['toi_sh'].apply(lambda x: 0 if x in (None, '') else string_to_time(x))

        # calc powerplay toi ratio
        df_game_stats['toi_pp_ratio'] = df_game_stats['toi_pp_sec']/df_game_stats['team_toi_pp_sec'] * 100

        # calc 3-game toi rolling averages
        df_game_stats['toi_sec_ra'] = df_game_stats.groupby('player_id')['toi_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        df_game_stats['toi_even_sec_ra'] = df_game_stats.groupby('player_id')['toi_even_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        df_game_stats['toi_pp_sec_ra'] = df_game_stats.groupby('player_id')['toi_pp_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        df_game_stats['team_toi_pp_sec_ra'] = df_game_stats.groupby('player_id')['team_toi_pp_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())
        df_game_stats['toi_pp_ratio_ra'] = df_game_stats['toi_pp_sec_ra']/df_game_stats['team_toi_pp_sec_ra'] * 100
        df_game_stats['toi_sh_sec_ra'] = df_game_stats.groupby('player_id')['toi_sh_sec'].transform(lambda x: x.rolling(rolling_avg_period, 1).mean())

        # calc really bad start
        # When a goalie has a save percentage in a game less than 85%
        df_game_stats['really_bad_starts'] = df_game_stats.apply(lambda x: 1
                                                                            if round(x['saves%'], 1) < 85.0 and x['pos'] == goalie_position_code and x['games_started'] == 1
                                                                            else 0
                                                                                if x['pos'] == goalie_position_code and x['games_started'] == 1
                                                                                else np.nan,
                                                axis='columns')

    except:
        print(f'{traceback.format_exc()}')

    return df_game_stats

def get_columns_by_attribute(config: Dict, attribute: str) -> Dict:

    initially_hidden_column_names = [x['title'] for x in config['columns'] if attribute in x and x[attribute]==True]

    return initially_hidden_column_names

def get_config_column_formats(config: Dict) -> Dict:

    column_formats = {x['title']: x['format'] for x in config['columns'] if 'format' in x and ('table column' in x or 'runtime column' in x)}

    return column_formats

def get_config_column_headings(config: Dict) -> List:

    column_headings = {x['table column'] if 'table column' in x else x['runtime column'] : x['title'] for x in config['columns'] if x}

    return column_headings

def get_config_default_sort_order_columns(config: Dict) -> List:

    default_desc_sort_order_columns = [x['title'] for x in config['columns'] if 'default order' in x and x['default order']=='desc']

    return default_desc_sort_order_columns

def get_config_left_aligned_columns(config: Dict) -> List:

    left_aligned_columns = [x['title'] for x in config['columns'] if 'justify' in x and x['justify']=='left']

    return left_aligned_columns

def get_db_connection():

    # Storing an integer in sqlite results in BLOBs (binary values) instead of INTEGER.
    # The following lines prevent this.
    sqlite3.register_adapter(int64, int)
    sqlite3.register_adapter(int32, int)

    # Get the path to the parent directory
    script_path = os.path.abspath(__file__)
    # print(f'*** script path: {script_path}')
    script_dir = os.path.dirname(script_path)
    # print(f'*** script dir: {script_dir}')
    parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
    # print(f'*** Parent dir: {parent_dir}')

    # Construct the path to the SQLite database file
    db_file = os.path.join(parent_dir, DATABASE)
    # print(f'*** Database dir: {db_file}')

    connection = sqlite3.connect(db_file)

    connection.row_factory = sqlite3.Row

    # uncomment the following line to print the sql statement with parameter substitution, after execution
    # connection.set_trace_callback(print)

    return connection

def get_player_position_info_columns(config: Dict, position: str='skater') -> Dict:

    # only want columns that are position-specific & not in other data groups (e.g., 'z_score_sum'),
    # so must use "position == x['data_group']"
    position_columns = [x['title'] for x in config['columns'] if 'data_group' in x and position == x['data_group']]
    position_columns.sort()

    return position_columns

def get_general_info_columns(config: Dict) -> Dict:

    private_columns = [x['title'] for x in config['columns'] if 'data_group' in x and 'general' in x['data_group']]
    private_columns.sort()

    return private_columns

def get_scoring_category_columns(config: Dict, position: str='skater') -> Dict:

    scoring_category_columns = [x['title'] for x in config['columns'] if 'data_group' in x and 'scoring_category' in x['data_group'] and position in x['data_group']]
    scoring_category_columns.sort()

    return scoring_category_columns

def get_stat_type_columns(config: Dict, stat_type: str, alias: bool=False) -> List:

    if alias is True:
        stat_type_columns = [x['alias'] if 'alias' in x else x['title'] for x in config['columns'] if 'stat_type' not in x or ('stat_type' in x and stat_type in x['stat_type'])]
    else:
        stat_type_columns = [x['title'] for x in config['columns'] if 'stat_type' not in x or ('stat_type' in x and stat_type in x['stat_type'])]

    return stat_type_columns

def get_z_score_category_columns(config: Dict, position: str='skater') -> Dict:

    z_score_category_columns = [x['title'] for x in config['columns'] if 'data_group' in x and 'z_score_cat' in x['data_group'] and position in x['data_group']]
    z_score_category_columns.sort()

    return z_score_category_columns

def get_z_score_summary_columns(config: Dict, position: str='skater') -> Dict:

    z_score_category_columns = [x['title'] for x in config['columns'] if 'data_group' in x and 'z_score_sum' in x['data_group'] and position in x['data_group']]
    z_score_category_columns.sort()

    return z_score_category_columns

def insert_fantrax_columns(df: pd.DataFrame):

    try:

        ##########################################################################
        # Fantrax scores
        dfFantraxPlayerInfo = pd.read_sql(sql='select * from FantraxPlayerInfo', con=get_db_connection())
        # set indexes to player_id
        df.set_index('player_id', inplace=True)
        dfFantraxPlayerInfo.set_index('player_id', inplace=True)
        # dfFantraxPlayerInfo seems to have duplicates, so drop duplicates
        dfFantraxPlayerInfo = dfFantraxPlayerInfo[~dfFantraxPlayerInfo.index.duplicated()]

        # fantrax score may have been added in calc_player_projected_stats()
        if 'fantrax_score' not in df.columns:
            df['fantrax_score'] = dfFantraxPlayerInfo['score']

        ##########################################################################
        # Fantrax player is rookie
        df['rookie'] = dfFantraxPlayerInfo['rookie']
        df['rookie'] = df['rookie'].apply(lambda x: '' if (x==0 or pd.isna(x)) else 'Yes')

        ##########################################################################
        # Fantrax player in non-nhl leagues
        df['minors'] = dfFantraxPlayerInfo['minors']
        df['minors'] = df['minors'].apply(lambda x: '' if (x==0 or pd.isna(x)) else 'Yes')

        ##########################################################################
        # Fantrax watch-list players
        df['watch_list'] = dfFantraxPlayerInfo['watch_list']
        df['watch_list'] = df['watch_list'].apply(lambda x: '' if (x==0 or pd.isna(x)) else 'Yes')

        ##########################################################################
        # Fantrax next opponent
        df['next_opp'] = dfFantraxPlayerInfo['next_opp']

        # reset index to indexes being list of row integers
        df.reset_index(inplace=True)

    except:
        print(f'{traceback.format_exc()} in insert_fantrax_columns()')

    return

def make_clickable(column: str, value: str, alt_value: str='') -> str:

    # https://www.fantrax.com/fantasy/league/nhcwgeytkoxo2wc7/players;reload=2;statusOrTeamFilter=ALL;searchName=Jacob%20Bryson

    link = value

    if column == 'id':
        href = f"https://statsapi.web.nhl.com/api/v1/people/{value}?expand=person.stats&stats=yearByYear,yearByYearPlayoffs,careerRegularSeason&expand=stats.team"
        # target _blank to open new window
        link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'
    # elif column == 'name':
    #     href = f"https://www.fantrax.com/fantasy/league/{pool.league_id}/players;reload=2;statusOrTeamFilter=ALL;searchName={value.replace(' ', '%20')}"
    #     # target _blank to open new window
    #     link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'
    elif column == 'team':
        href = f"https://statsapi.web.nhl.com/api/v1/teams/{alt_value}/roster?expand=roster.person,person.names"
        # target _blank to open new window
        link =  f'<a target="_blank" href="{href}" style="color: green">{value}</a>'

    return link

def merge_with_current_players_info(season_id: str, pool_id: str, df_stats: pd.DataFrame) -> pd.DataFrame:

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
        'poolteam_id': f'(select pt.id from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool_id} and ptr.player_id=tr.player_id)',
        'pool_team': f'(select pt.name from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool_id} and ptr.player_id=tr.player_id)',
        'status': f'(select ptr.status from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool_id} and ptr.player_id=tr.player_id)',
        'keeper': f'(select ptr.keeper from PoolTeamRoster ptr join PoolTeam pt on pt.id=ptr.poolteam_id where pt.pool_id={pool_id} and ptr.player_id=tr.player_id)',
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
    where_clause = f'where tr.seasonID={season_id} and (p.roster_status!="N" or pool_team>=1)'

    # get players on nhl team rosters
    df = pd.read_sql(f'{select_sql} {from_tables} {where_clause}', con=get_db_connection())

    columns = [
        f'{season_id} as seasonID',
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

    where_clause = f'where pt.pool_id={pool_id} and p.active!=1'

    sql = textwrap.dedent(f'''\
        {select_sql}
        {from_tables}
        {where_clause}
    ''')

    # get inactive nhl players on pool team rosters
    df_temp = pd.read_sql(sql, con=get_db_connection())

    # iterate to get player's primary position
    for idx, row in df_temp.iterrows():
        primary_position = j.search('people[0].primaryPosition.abbreviation', requests.get(f'{NHL_API_URL}/people/{row.player_id}').json())
        df_temp.loc[idx, 'pos'] = primary_position

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

def rankings_to_html(df: pd.DataFrame, config: Dict, stat_type: str='Cumulative') -> dict:

    try:

        # set nan to 0 for numeric columns
        if 'last game' in list(df.columns):
            df['last game'].fillna('', inplace=True)
        if 'first game' in list(df.columns):
            df['first game'].fillna('', inplace=True)
        if 'game today' in list(df.columns):
            df['game today'].fillna('', inplace=True)

        # format columns before writing to json
        col_formats = get_config_column_formats(config=config)
        for col in df.columns:
            if col in col_formats:
                df[col] = df[col].map(col_formats[col])

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
        cumulative_column_titles = get_stat_type_columns(config=config, stat_type='Cumulative', alias=True)
        per_game_column_titles = get_stat_type_columns(config=config, stat_type='Per game', alias=True)
        per_60_column_titles = get_stat_type_columns(config=config, stat_type='Per 60 minutes', alias=True)

        cols_to_sort_numeric = [df_temp.columns.get_loc(x) for x in list(df_temp.select_dtypes([np.int64,np.float64]).columns) if x in df_temp.columns]
        cols_to_sort_descending = [df_temp.columns.get_loc(x) for x in get_config_default_sort_order_columns(config=config) if x in df_temp.columns]

        general_info_column_names = [f'{x.replace(" ","_")}:name' for x in get_general_info_columns(config=config) if x in df_temp.columns]
        cumulative_stat_column_names = [f'{x.replace(" ","_")}:name' for x in get_stat_type_columns(config=config, stat_type='Cumulative', alias=True) if x in df_temp.columns]
        per_game_stat_column_names = [f'{x.replace(" ","_")}:name' for x in get_stat_type_columns(config=config, stat_type='Per game', alias=True) if x in df_temp.columns]
        per_60_stat_column_names = [f'{x.replace(" ","_")}:name' for x in get_stat_type_columns(config=config, stat_type='Per 60 minutes', alias=True) if x in df_temp.columns]
        sktr_info_column_names = [f'{x.replace(" ","_")}:name' for x in get_player_position_info_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_info_column_names = [f'{x.replace(" ","_")}:name' for x in get_player_position_info_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_scoring_categories_column_names = [f'{x.replace(" ","_")}:name' for x in get_scoring_category_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_scoring_categories_column_names = [f'{x.replace(" ","_")}:name' for x in get_scoring_category_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_z_score_categories_column_names = [f'{x.replace(" ","_")}:name' for x in get_z_score_category_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_z_score_categories_column_names = [f'{x.replace(" ","_")}:name' for x in get_z_score_category_columns(config=config, position='goalie') if x in df_temp.columns]
        sktr_z_score_summary_column_names = [f'{x.replace(" ","_")}:name' for x in get_z_score_summary_columns(config=config, position='skater') if x in df_temp.columns]
        goalie_z_score_summary_column_names = [f'{x.replace(" ","_")}:name' for x in get_z_score_summary_columns(config=config, position='goalie') if x in df_temp.columns]

        initially_hidden_column_names = [f'{x.replace(" ","_")}:name' for x in get_columns_by_attribute(config=config, attribute='hide') if x in df_temp.columns]

        # set NaN values to 0
        for key in max_cat.keys():
            if max_cat[key] is None or np.isnan(max_cat[key]):
                max_cat[key] = 0
            if isinstance(max_cat[key], np.int64):
                max_cat[key] = int(max_cat[key])
        for key in min_cat.keys():
            if min_cat[key] is None or np.isnan(min_cat[key]):
                min_cat[key] = 0
            if isinstance(min_cat[key], np.int64):
                min_cat[key] = int(min_cat[key])
        for key in mean_cat.keys():
            if mean_cat[key] is None or np.isnan(mean_cat[key]):
                mean_cat[key] = 0
            if isinstance(mean_cat[key], np.int64):
                mean_cat[key] = int(mean_cat[key])
        max_cat_dict = dict(max_cat)
        min_cat_dict = dict(min_cat)
        mean_cat_dict = dict(mean_cat)

        # create a dictionary to hold variables to use in jquery datatable
        data_dict = {
            'cumulative_stats_data': cumulative_stats_data,
            'per_game_stats_data': per_game_stats_data,
            'per_60_stats_data': per_60_stats_data,
            'cumulative_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in cumulative_column_titles],
            'per_game_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in per_game_column_titles],
            'per_60_column_titles': [{"title": col, "name": col.replace(" ","_")} for col in per_60_column_titles],
            'numeric_columns': cols_to_sort_numeric,
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
            'initially_hidden_column_names': initially_hidden_column_names,
            'max_cat_dict': max_cat_dict,
            'min_cat_dict': min_cat_dict,
            'mean_cat_dict': mean_cat_dict,
        }

    except:
        print(f'{traceback.format_exc()} in rankings_to_html()')

    # return the JSON object as a response to the frontend
    return data_dict

def rank_players(season_or_date_radios: str, from_season_id: str, to_season_id: str, from_date: str, to_date: str, pool_id: str, game_type: str='R', stat_type: str='Cumulative') -> dict:

    if game_type == 'R':
        season_type = 'Regular Season'
    else: # game_type == 'P'
        season_type = 'Playoffs'

    global timeframe
    timeframe =  season_type

    # # settings to determine columns to show in html
    # global stat_type
    # stat_type = 'Cumulative'

    #######################################################################################
    #######################################################################################
    # generate games statitics

    if season_or_date_radios == 'date':
        df_game_stats = get_game_stats(season_or_date_radios=season_or_date_radios, from_season_id=from_season_id, to_season_id=to_season_id, from_date=from_date, to_date=to_date, pool_id=pool_id, game_type=game_type)
    else: #  season_or_date_radios == 'season'
        # (start_year, _) = split_seasonID_into_component_years(season_id=from_season_id)
        # (_, end_year) = split_seasonID_into_component_years(season_id=to_season_id)
        df_game_stats = get_game_stats(season_or_date_radios=season_or_date_radios, from_season_id=from_season_id, to_season_id=to_season_id, from_date=from_date, to_date=to_date, pool_id=pool_id, game_type=game_type)

    # add team games played for each player
    # Get teams to save in dictionary
    global teams_dict
    if from_season_id == to_season_id:
        df_teams = pd.read_sql(f'select team_id, games from TeamStats where seasonID={from_season_id} and game_type="{game_type}"', con=get_db_connection())
    else:
        df_teams = pd.read_sql(f'select team_id, sum(games) as games from TeamStats where seasonID between {from_season_id} and {to_season_id} and game_type="{game_type}" group by team_id', con=get_db_connection())
    teams_dict = {x.team_id: {'games': x.games} for x in df_teams.itertuples()}

    #######################################################################################
    # aggregate per game stats per player
    df_player_stats = aggregate_game_stats(df=df_game_stats)

    # # merge with current player info
    # if season.SEASON_HAS_STARTED is True and season.type == 'R':
    #     df_player_stats = merge_with_current_players_info(season=season, pool=pool, df_stats=df_player_stats)
    # elif season.SEASON_HAS_STARTED is True and season.type == 'P':
    #     next_season_id = season.getNextSeasonID()
    #     next_season_pool = HockeyPool().fetch(**{'Criteria': [['season_id', '==', next_season_id]]})
    #     df_player_stats = merge_with_current_players_info(season=season, pool=next_season_pool, df_stats=df_player_stats)
    # else: # timeframe in ('Previous playoffs', 'Previous 3 seasons', 'Previous season')
    #     df_player_stats = merge_with_current_players_info(season=prev_season, pool=pool, df_stats=df_player_stats)
    df_player_stats = merge_with_current_players_info(season_id=to_season_id, pool_id=pool_id, df_stats=df_player_stats)

    # add fantrax "score" & "minors" columns
    insert_fantrax_columns(df=df_player_stats)

    # need to add these columns after the stats have been partitioned
    # per-game stats
    calc_per_game_stats(df=df_player_stats, df_game_stats=df_game_stats)

    # per-60 stats
    calc_per60_stats(df=df_player_stats)

    # calc global mean and std dev for z-score calculations
    calc_scoring_category_means(df=df_player_stats)
    calc_scoring_category_std_deviations(df=df_player_stats)
    # z-scores
    calc_cumulative_z_scores(df=df_player_stats)
    calc_per_game_z_scores(df=df_player_stats)
    calc_per_60_z_scores(df=df_player_stats)

    # calc_projection_z_scores(df=df_player_stats)

    # vorp = value over replacement player
    if timeframe == 'Regular Season': # regular season
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='cumulative', vorp_type='cumulative')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='cumulative', vorp_type='offense')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='cumulative', vorp_type='peripheral')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per game', vorp_type='cumulative')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per game', vorp_type='offense')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per game', vorp_type='peripheral')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per 60 minutes', vorp_type='cumulative')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per 60 minutes', vorp_type='offense')
        calc_summary_z_scores_vorp(df=df_player_stats, stat_type='per 60 minutes', vorp_type='peripheral')

    # calc global minumums & maximums
    calc_scoring_category_minimums(df=df_player_stats)
    calc_scoring_category_maximums(df=df_player_stats)

    # # if show_draft_list_info:
    # add_draft_list_columns_to_df(season=season, df=df_player_stats)

    # # if pre_draft_keeper columns:
    # add_pre_draft_keeper_list_column_to_df(season=season, df=df_player_stats)

    # drop rows for irrelevant players; e.g., no games played, projected games, or not on a pool team or not on my watchlist
    # drop players in minors and not on active nhl team roster, and not on a pool team and , when projections are used the projected games !> 0
    df_player_stats.query('(games>=1 and games.notna() and minors=="" and nhl_roster_status=="y") or (poolteam_id>=1 and poolteam_id.notna()) or watch_list=="Yes" or (line.notna() and line!="") or (pp_line.notna() and pp_line!="")', inplace=True)

    # df_player_stats['pool_team'].fillna(value='', inplace=True)

    # # potential draft round
    # if current_season_stats is False and stat_type in ('Proj - Fantrax', 'Proj - Averaged'):

    #     df_player_stats.set_index('player_id', inplace=True)

    #     # Find potential draft round using average draft position
    #     df_temp = df_player_stats.query('keeper!="Yes" and adp!=0').sort_values('adp')
    #     df_temp = df_temp.groupby(np.arange(len(df_temp.index))//13, axis='index').ngroup() + 1
    #     df_player_stats['pdr1'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)

    #     # Find potential draft round using Fantrax score
    #     df_temp = df_player_stats.query('keeper!="Yes" and fantrax_score!=0').sort_values('fantrax_score', ascending=False)
    #     df_temp = df_temp.groupby(np.arange(len(df_temp.index))//13, axis='index').ngroup() + 1
    #     df_player_stats['pdr2'] = df_temp.apply(lambda x: int(round(x,0)) if int(round(x,0)) <= 12 else 12)

    #     # Find potential draft round using z-score
    #     df_temp = df_player_stats.query('keeper!="Yes").sort_values('z_score', ascending=False)
    #     df_temp = df_temp.groupby(np.arange(len(df_temp.index))//13, axis='index').ngroup() + 1
    #     df_player_stats['pdr3'] = df_temp.apply(lambda x: x if x <= 12 else 12)

    #     # Find potential draft round using z-score vorp
    #     if 'z_score_vorp' in df_player_stats.columns:
    #         df_temp = df_player_stats.query('keeper!="Yes" and z_score_vorp!=0').sort_values('z_score_vorp', ascending=False)
    #         df_temp = df_temp.groupby(np.arange(len(df_temp.index))//13, axis='index').ngroup() + 1
    #         df_player_stats['pdr4'] = df_temp.apply(lambda x: x if x <= 12 else 12)
    #     else:
    #         df_player_stats['pdr4'] = np.nan

    #     # get mean, min & max pdr
    #     df_player_stats['pdr_min'] = df_player_stats.apply(lambda x: np.nanmin([x.pdr1, x.pdr2, x.pdr3, x.pdr4])
    #                                                                     if any([not np.isnan(x.pdr1), not np.isnan(x.pdr2), not np.isnan(x.pdr3), not np.isnan(x.pdr4)])
    #                                                                     else np.nan,
    #                                     axis='columns')

    #     df_player_stats['pdr_max'] = df_player_stats.apply(lambda x: round(np.nanmax([x.pdr1, x.pdr2, x.pdr3, x.pdr4]), 0)
    #                                                                     if any([not np.isnan(x.pdr1), not np.isnan(x.pdr2), not np.isnan(x.pdr3), not np.isnan(x.pdr4)])
    #                                                                     else np.nan,
    #                                     axis='columns')

    #     df_player_stats['pdr_mean'] = df_player_stats.apply(lambda x: np.nanmean([x.pdr1, x.pdr2, x.pdr3, x.pdr4])
    #                                                                     if any([not np.isnan(x.pdr1), not np.isnan(x.pdr2), not np.isnan(x.pdr3), not np.isnan(x.pdr4)])
    #                                                                     else np.nan,
    #                                     axis='columns')

    #     df_player_stats['pdr'] = df_player_stats.apply(lambda x: f'{int(round(x.pdr_min,0))} - {int(round(x.pdr_mean,0))}'
    #                                                             if not np.isnan(x.pdr_min) and not np.isnan(x.pdr_mean) and int(round(x.pdr_min,0))<int(round(x.pdr_mean,0))
    #                                                             else f'{int(round(x.pdr_mean,0))} - {int(round(x.pdr_min,0))}'
    #                                                                 if not np.isnan(x.pdr_min) and not np.isnan(x.pdr_mean) and int(round(x.pdr_mean,0))<int(round(x.pdr_min,0))
    #                                                                     else int(round(x.pdr_min,0))
    #                                                                         if not np.isnan(x.pdr_min)
    #                                                                         else int(round(x.pdr_mean,0))
    #                                                                                 if not np.isnan(x.pdr_mean)
    #                                                                                 else '',
    #                                                     axis='columns')

    #     # if projected draft round is 0, set to ''
    #     df_player_stats['pdr'] = df_player_stats['pdr'].apply(lambda x: '' if x == 0 else x)

    #     df_player_stats.reset_index(inplace=True)

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

    if stat_type == 'Cumulative':
        sort_columns = ['z_score_pg', 'z_score_p60', 'z_score']
    elif stat_type == 'Per game':
        sort_columns = ['z_score_p60', 'z_score', 'z_score_pg']
    elif stat_type == 'Per 60 minutes':
        sort_columns = ['z_score', 'z_score_pg', 'z_score_p60']
    for sort_column in sort_columns:
        df_k.sort_values([sort_column], ascending=[False], inplace=True)
        df_k[f'{sort_column}_rank'] = df_k[sort_column].rank(method='min', na_option='bottom', ascending=False)

    sort_column = sort_columns[-1]

    # add rank & overall rank, hopefully based on my z-scores
    # overall rank will remain fixed in datatable
    # rank will renumber based on the rows currently displayed in datatable
    df_k['rank'] = df_k[sort_column].rank(method='min', na_option='bottom', ascending=False)

    config = stats_config(position='all')
    column_headings = get_config_column_headings(config=config)
    df_k.rename(columns=column_headings, inplace=True)
    df_k = df_k.reindex(columns=[v for v in column_headings.values()])

    column_formats = get_config_column_formats(config=config)
    column_left_alignment = get_config_left_aligned_columns(config=config)

    # before dropping hidden columns, set cells with clickable links
    df_k['id'] = df_k.apply(lambda x: make_clickable(column='id', value=x['id']), axis='columns')
    df_k['name'] = df_k.apply(lambda x: make_clickable(column='name', value=x['name']), axis='columns')
    df_k['team'] = df_k.apply(lambda x: make_clickable(column='team', value=x['team'], alt_value='' if pd.isna(x['team id']) or x['team id'] in ['', 0] else '{:0.0f}'.format(x['team id'])), axis='columns')

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
            {'title': 'team id', 'table column': 'team_id', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True},
            {'title': 'team', 'table column': 'team_abbr', 'data_group': 'general', 'search_builder': True},
            {'title': 'pos', 'table column': 'pos', 'search_pane': True, 'data_group': 'general', 'search_builder': True},
            {'title': 'fantrax roster status', 'table column': 'status', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'age', 'table column': 'age', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},
            {'title': 'height', 'table column': 'height', 'data_group': 'general', 'hide': True},
            {'title': 'weight', 'table column': 'weight', 'data_group': 'general', 'hide': True},
            {'title': 'career gp', 'table column': 'career_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True},
            {'title': 'bt', 'table column': 'breakout_threshold', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'keeper', 'table column': 'keeper', 'format': eval(f_nan_to_empty), 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'pre-draft keeper', 'table column': 'pre_draft_keeper', 'format': eval(f_nan_to_empty), 'data_group': 'draft', 'hide': True},
            {'title': 'rookie', 'table column': 'rookie', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'active', 'table column': 'active', 'data_group': 'general', 'hide': True},
            {'title': 'nhl roster status', 'table column': 'nhl_roster_status', 'data_group': 'general', 'hide': True},
            {'title': 'minors', 'table column': 'minors', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'watch', 'table column': 'watch_list', 'data_group': 'general', 'hide': True, 'search_builder': True},
            {'title': 'injury', 'table column': 'injury_status', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'hide': True},
            {'title': 'injury note', 'table column': 'injury_note', 'justify': 'left', 'data_group': 'general', 'hide': True},
            # {'title': 'bandaid boy', 'runtime column': 'bandaid_prj', 'format': eval(f_str), 'data_group': 'general', 'hide': True},
            {'title': 'manager', 'table column': 'pool_team', 'justify': 'left', 'data_group': 'general', 'search_pane': True, 'search_builder': True},
            {'title': 'first game', 'table column': 'first game', 'format': eval(f_str), 'data_group': 'general', 'hide': True},
            {'title': 'last game', 'table column': 'last game', 'format': eval(f_str), 'data_group': 'general', 'default order': 'desc', 'search_builder': True, 'hide': True},
            {'title': 'game today', 'table column': 'next_opp', 'data_group': 'general', 'hide': True, 'search_builder': True},
        ],
    }

    cumulative_zscore_summary_columns = {
        'columns': [
            {'title': 'z-score', 'runtime column': 'z_score', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-combo', 'runtime column': 'z_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-offense', 'runtime column': 'z_offense', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo offense', 'runtime column': 'z_offense_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-peripheral', 'runtime column': 'z_peripheral', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo peripheral', 'runtime column': 'z_peripheral_combo', 'format': eval(f_str), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},

            {'title': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +blks', 'runtime column': 'z_hits_blk', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +penalties', 'runtime column': 'z_hits_pim', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},

            # {'title': 'z-cats sum vorp', 'runtime column': 'z_cats_sum_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('general', 'z_score_sum'), 'hide': True},
            {'title': 'z-score vorp', 'runtime column': 'z_score_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('general', 'z_score_sum'), 'hide': True},
            # {'title': 'z-cats offense vorp', 'runtime column': 'z_cats_offense_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater','z_score_sum'), 'hide': True},
            {'title': 'z-offense vorp', 'runtime column': 'z_offense_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater','z_score_sum'), 'hide': True},
            # {'title': 'z-cats peripheral vorp', 'runtime column': 'z_cats_peripheral_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group':  ('skater','z_score_sum'), 'hide': True},
            {'title': 'z-peripheral vorp', 'runtime column': 'z_peripheral_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group':  ('skater','z_score_sum'), 'hide': True},
        ],
    }

    config['columns'].extend(cumulative_zscore_summary_columns['columns'])

    pg_zscore_summary_columns = {
        'columns': [
            {'title': 'z-score pg', 'alias': 'z-score', 'runtime column': 'z_score_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-combo pg', 'alias': 'z-combo', 'runtime column': 'z_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-offense pg', 'alias': 'z-offense', 'runtime column': 'z_offense_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo offense pg', 'alias': 'z-combo offense', 'runtime column': 'z_offense_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-peripheral pg', 'alias': 'z-peripheral', 'runtime column': 'z_peripheral_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo peripheral pg', 'alias': 'z-combo peripheral', 'runtime column': 'z_peripheral_combo_pg', 'format': eval(f_str), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},

            {'title': 'z-sog +hits +blk pg', 'alias': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +blks pg', 'alias': 'z-hits +blks', 'runtime column': 'z_hits_blk_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-goals +hits +penalties pg', 'alias': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +penalties pg', 'alias': 'z-hits +penalties', 'runtime column': 'z_hits_pim_pg', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},

            {'title': 'z-score vorp pg', 'alias': 'z-score vorp', 'runtime column': 'z_score_pg_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('general', 'z_score_sum'), 'hide': True},
            {'title': 'z-offense vorp pg', 'alias': 'z-offense vorp', 'runtime column': 'z_offense_pg_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-peripheral vorp pg', 'alias': 'z-peripheral vorp', 'runtime column': 'z_peripheral_pg_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
        ],
    }

    config['columns'].extend(pg_zscore_summary_columns['columns'])

    p60_zscore_summary_columns = {
        'columns': [
            {'title': 'z-score p60', 'alias': 'z-score', 'runtime column': 'z_score_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-combo p60', 'alias': 'z-combo', 'runtime column': 'z_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': 'general'},
            {'title': 'z-offense p60', 'alias': 'z-offense', 'runtime column': 'z_offense_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo offense p60', 'alias': 'z-combo offense', 'runtime column': 'z_offense_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-peripheral p60', 'alias': 'z-peripheral', 'runtime column': 'z_peripheral_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},
            {'title': 'z-combo peripheral p60', 'alias': 'z-combo peripheral', 'runtime column': 'z_peripheral_combo_p60', 'format': eval(f_str), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum')},

            {'title': 'z-sog +hits +blk p60', 'alias': 'z-sog +hits +blk', 'runtime column': 'z_sog_hits_blk_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +blks p60', 'alias': 'z-hits +blks', 'runtime column': 'z_hits_blk_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-goals +hits +penalties p60', 'alias': 'z-goals +hits +penalties', 'runtime column': 'z_goals_hits_pim_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-hits +penalties p60', 'alias': 'z-hits +penalties', 'runtime column': 'z_hits_pim_p60', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},

            {'title': 'z-score vorp p60', 'alias': 'z-score vorp', 'runtime column': 'z_score_p60_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('general', 'z_score_sum'), 'hide': True},
            {'title': 'z-offense vorp p60', 'alias': 'z-offense vorp', 'runtime column': 'z_offense_p60_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
            {'title': 'z-peripheral vorp p60', 'alias': 'z-peripheral vorp', 'runtime column': 'z_peripheral_p60_vorp', 'format': eval(f_1_decimal), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_sum'), 'hide': True},
        ],
    }

    config['columns'].extend(p60_zscore_summary_columns['columns'])

    other_score_columns = {
        'columns': [
            {'title': 'z-score rank', 'runtime column': 'z_score_rank', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'data_group': 'general', 'hide': True},
            {'title': 'z-score pg rank', 'alias': 'z-score rank', 'runtime column': 'z_score_pg_rank', 'format': eval(f_0_decimals), 'stat_type': 'Per game', 'data_group': 'general', 'hide': True},
            {'title': 'z-score p60 rank', 'alias': 'z-score rank', 'runtime column': 'z_score_p60_rank', 'format': eval(f_0_decimals), 'stat_type': 'Per 60 minutes', 'data_group': 'general', 'hide': True},
            # {'title': 'athletic z-score rank', 'runtime column': 'athletic_rank', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            # {'title': 'dfo z-score rank', 'runtime column': 'dfo_rank', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            # {'title': 'dobber z-score rank', 'runtime column': 'dobber_rank', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            # {'title': 'dtz z-score rank', 'runtime column': 'dtz_rank', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            # {'title': 'fantrax z-score rank', 'runtime column': 'fantrax_rank', 'format': eval(f_0_decimals), 'data_group': 'draft', 'hide': True},
            # {'title': 'fantrax score', 'runtime column': 'fantrax_score', 'visible': not season.SEASON_HAS_ENDED, 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'general', 'hide': True},
            # {'title': 'fantrax adp', 'runtime column': 'adp', 'format': eval(f_1_decimal), 'data_group': 'draft', 'hide': True},
        ],
    }

    config['columns'].extend(other_score_columns['columns'])

    skater_columns = {
        'columns': [
            {'title': 'line', 'table column': 'line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True},
            {'title': 'pp unit', 'table column': 'pp_line', 'format': eval(f_0_decimals), 'data_group': 'skater', 'search_builder': True},
            # {'title': 'pp unit prj', 'runtime column': 'pp_line_prj', 'format': eval(f_0_decimals), 'data_group': ('skater', 'draft'), 'hide': True},
            # {'title': 'prj draft round', 'runtime column': 'pdr', 'data_group': 'draft', 'hide': True},
            # {'title': 'sleeper prj', 'runtime column': 'sleeper_prj', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            # {'title': 'upside prj', 'runtime column': 'upside_prj', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},
            # {'title': '3yp prj', 'runtime column': '3yp_prj', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'draft', 'hide': True},

            {'title': 'toi (sec)', 'runtime column': 'toi_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg', 'table column': 'toi_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg (sec)', 'runtime column': 'toi_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg (trend)', 'runtime column': 'toi_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pg ra', 'table column': 'toi_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'toi even (sec)', 'runtime column': 'toi_even_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg', 'table column': 'toi_even_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc'},
            {'title': 'toi even pg (sec)', 'runtime column': 'toi_even_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg (trend)', 'runtime column': 'toi_even_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi even pg ra', 'table column': 'toi_even_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'ev pts', 'table column': 'evg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev on-ice', 'table column': 'evg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'ev ipp', 'table column': 'evg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'cf', 'table column': 'corsi_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ca', 'table column': 'corsi_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'cf%', 'table column': 'corsi_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': False},
            {'title': 'ff', 'table column': 'fenwick_for', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'fa', 'table column': 'fenwick_against', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'ff%', 'table column': 'fenwick_for_%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': True},

            {'title': 'toi pp (sec)', 'runtime column': 'toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg', 'table column': 'toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc'},
            {'title': 'toi pp pg (sec)', 'runtime column': 'toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg (trend)', 'runtime column': 'toi_pp_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi pp pg ra', 'table column': 'toi_pp_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'pp sog/120', 'table column': 'pp_sog_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp g/120', 'table column': 'pp_goals_p120', 'format': eval(f_2_decimals_show_0), 'default order': 'desc', 'data_group': 'skater', 'hide': True},
            {'title': 'pp pts/120', 'table column': 'pp_pts_p120', 'format': eval(f_2_decimals_show_0), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp pts', 'table column': 'ppg_point', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp on-ice', 'table column': 'ppg_on_ice', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'pp ipp', 'table column': 'ppg_ipp', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'team toi pp (sec)', 'runtime column': 'team_toi_pp_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg', 'table column': 'team_toi_pp_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg (sec)', 'runtime column': 'team_toi_pp_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'team toi pp pg ra', 'table column': 'team_toi_pp_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': '%pp', 'runtime column': 'toi_pp_pg_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc'},
            {'title': '%pp (last game)', 'runtime column': 'toi_pp_ratio', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp trend', 'runtime column': 'toi_pp_pg_ratio_trend', 'format': eval(f_1_decimal_show_0_and_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': '%pp ra', 'runtime column': 'toi_pp_ratio_ra', 'format': eval(f_1_decimal), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'toi sh (sec)', 'runtime column': 'toi_sh_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg', 'table column': 'toi_sh_pg', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg (sec)', 'runtime column': 'toi_sh_pg_sec', 'format': eval(f_0_decimals), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg (trend)', 'runtime column': 'toi_sh_pg_sec_trend', 'format': eval(f_0_toi_to_empty_and_show_plus), 'data_group': 'skater', 'default order': 'desc', 'hide': True},
            {'title': 'toi sh pg ra', 'table column': 'toi_sh_pg_ra_last', 'format': eval(f_0_toi_to_empty), 'data_group': 'skater', 'default order': 'desc', 'hide': True},

            {'title': 'team gp', 'table column': 'team_games', 'format': eval(f_0_decimals), 'data_group': 'general', 'hide': True},
            {'title': 'games', 'table column': 'games', 'format': eval(f_0_decimals), 'data_group': 'general', 'search_builder': True},

            {'title': 'sh%', 'table column': 'shooting%', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'skater', 'hide': False},
        ],
    }

    config['columns'].extend(skater_columns['columns'])

    skater_cumulative_columns = {
        'columns': [
            {'title': 'pts', 'table column': 'points', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'g', 'table column': 'goals', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'a', 'table column': 'assists', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'ppp', 'table column': 'points_pp', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'sog', 'table column': 'shots', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pp sog', 'table column': 'shots_powerplay', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
            {'title': 'tk', 'table column': 'takeaways', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'hits', 'table column': 'hits', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'blk', 'table column': 'blocked', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pim', 'table column': 'pim', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'penalties', 'table column': 'penalties', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_cumulative_columns['columns'])

    skater_pg_columns = {
        'columns': [
            {'title': 'pts pg', 'alias': 'pts', 'runtime column': 'pts_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'g pg', 'alias': 'g', 'runtime column': 'g_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'a pg', 'alias': 'a', 'runtime column': 'a_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'ppp pg', 'alias': 'ppp', 'runtime column': 'ppp_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'sog pg', 'alias': 'sog', 'runtime column': 'sog_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pp sog pg', 'alias': 'pp sog', 'table column': 'sog_pp_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
            {'title': 'tk pg', 'alias': 'tk', 'runtime column': 'tk_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'hits pg', 'alias': 'hits', 'runtime column': 'hits_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'blk pg', 'alias': 'blk', 'runtime column': 'blk_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pim pg', 'alias': 'pim', 'runtime column': 'pim_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'penalties pg', 'alias': 'penalties', 'table column': 'penalties_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_pg_columns['columns'])

    skater_p60_columns = {
        'columns': [
            {'title': 'pts p60', 'alias': 'pts', 'runtime column': 'pts_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'g p60', 'alias': 'g', 'runtime column': 'g_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'a p60', 'alias': 'a', 'runtime column': 'a_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'ppp p60', 'alias': 'ppp', 'runtime column': 'ppp_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'sog p60', 'alias': 'sog', 'runtime column': 'sog_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pp sog p60', 'alias': 'pp sog', 'table column': 'sog_pp_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
            {'title': 'tk p60', 'alias': 'tk', 'runtime column': 'tk_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'hits p60', 'alias': 'hits', 'runtime column': 'hits_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'blk p60', 'alias': 'blk', 'runtime column': 'blk_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'pim p60', 'alias': 'pim', 'runtime column': 'pim_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category')},
            {'title': 'penalties p60', 'alias': 'penalties', 'table column': 'penalties_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'scoring_category'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_p60_columns['columns'])

    skater_cumulative_zscore_columns = {
        'columns': [
            {'title': 'z-pts', 'runtime column': 'z_points', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-pts vorp', 'runtime column': 'z_points_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-g', 'runtime column': 'z_goals', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-g vorp', 'runtime column': 'z_goals_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-a', 'runtime column': 'z_assists', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-a vorp', 'runtime column': 'z_assists_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-ppp', 'runtime column': 'z_points_pp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-ppp vorp', 'runtime column': 'z_points_pp_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-sog', 'runtime column': 'z_shots', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-sog vorp', 'runtime column': 'z_shots_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-tk', 'runtime column': 'z_takeaways', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-tk vorp', 'runtime column': 'z_takeaways_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-hits', 'runtime column': 'z_hits', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-hits vorp', 'runtime column': 'z_hits_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-blk', 'runtime column': 'z_blocked', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-blk vorp', 'runtime column': 'z_blocked_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-pim', 'runtime column': 'z_pim', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-pim vorp', 'runtime column': 'z_pim_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-penalties', 'runtime column': 'z_penalties', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            # {'title': 'z-penalties vorp', 'runtime column': 'z_penalties_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_cumulative_zscore_columns['columns'])

    skater_pg_zscore_columns = {
        'columns': [
            {'title': 'z-pts pg', 'alias': 'z-pts', 'runtime column': 'z_pts_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-g pg', 'alias': 'z-g', 'runtime column': 'z_g_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-a pg', 'alias': 'z-a', 'runtime column': 'z_a_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-ppp pg', 'alias': 'z-ppp', 'runtime column': 'z_ppp_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-sog pg', 'alias': 'z-sog', 'runtime column': 'z_sog_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-tk pg', 'alias': 'z-tk', 'runtime column': 'z_tk_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-hits pg', 'alias': 'z-hits', 'runtime column': 'z_hits_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-blk pg', 'alias': 'z-blk', 'runtime column': 'z_blk_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-pim pg', 'alias': 'z-pim', 'runtime column': 'z_pim_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-penalties pg', 'alias': 'z-penalties', 'runtime column': 'z_penalties_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_pg_zscore_columns['columns'])

    skater_p60_zscore_columns = {
        'columns': [
            {'title': 'z-pts p60', 'alias': 'z-pts', 'runtime column': 'z_pts_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-g p60', 'alias': 'z-g', 'runtime column': 'z_g_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-a p60', 'alias': 'z-a', 'runtime column': 'z_a_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-ppp p60', 'alias': 'z-ppp', 'runtime column': 'z_ppp_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-sog p60', 'alias': 'z-sog', 'runtime column': 'z_sog_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-tk p60', 'alias': 'z-tk', 'runtime column': 'z_tk_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-hits p60', 'alias': 'z-hits', 'runtime column': 'z_hits_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-blk p60', 'alias': 'z-blk', 'runtime column': 'z_blk_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-pim p60', 'alias': 'z-pim', 'runtime column': 'z_pim_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
            {'title': 'z-penalties p60', 'alias': 'z-penalties', 'runtime column': 'z_penalties_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('skater', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(skater_p60_zscore_columns['columns'])

    goalie_columns = {
        'columns': [
            {'title': 'goalie starts', 'table column': 'games_started', 'format': eval(f_0_decimals), 'data_group': 'goalie', 'search_builder': True},
            {'title': '% of team games started', 'table column': 'starts_as_percent', 'format': eval(f_0_decimals), 'hide': True, 'data_group': 'goalie'},
            {'title': 'qs', 'table column': 'quality_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie'},
            {'title': 'qs %', 'table column': 'quality_starts_as_percent', 'format': eval(f_1_decimal), 'default order': 'desc', 'data_group': 'goalie'},
            {'title': 'rbs', 'table column': 'really_bad_starts', 'format': eval(f_0_decimals), 'default order': 'desc', 'data_group': 'goalie'},
        ],
    }

    config['columns'].extend(goalie_columns['columns'])

    goalie_cumulative_columns = {
        'columns': [
            {'title': 'w', 'table column': 'wins', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv', 'table column': 'saves', 'format': eval(f_0_decimals), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'gaa', 'table column': 'gaa', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv%', 'table column': 'save%', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
        ],
    }

    config['columns'].extend(goalie_cumulative_columns['columns'])

    goalie_pg_columns = {
        'columns': [
            {'title': 'w pg', 'alias': 'w', 'runtime column': 'wins_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv pg', 'alias': 'sv', 'runtime column': 'saves_pg', 'format': eval(f_2_decimals), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'gaa pg', 'alias': 'gaa', 'table column': 'gaa_pg', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv% pg', 'alias': 'sv%', 'table column': 'save%_pg', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
        ],
    }

    config['columns'].extend(goalie_pg_columns['columns'])

    goalie_p60_columns = {
        'columns': [
            {'title': 'w p60', 'alias': 'w', 'runtime column': 'wins_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv p60', 'alias': 'sv', 'runtime column': 'saves_p60', 'format': eval(f_2_decimals), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'gaa p60', 'alias': 'gaa', 'table column': 'gaa_p60', 'format': lambda x: '' if pd.isna(x) or x == '' else '{:0.2f}'.format(x), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
            {'title': 'sv% p60', 'alias': 'sv%', 'table column': 'save%_p60', 'format': eval(f_3_decimals_no_leading_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'scoring_category')},
        ],
    }

    config['columns'].extend(goalie_p60_columns['columns'])

    goalie_cumulative_zscore_columns = {
        'columns': [
            {'title': 'z-wins', 'runtime column': 'z_wins', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            # {'title': 'z-wins vorp', 'runtime column': 'z_wins_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-saves', 'runtime column': 'z_saves', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            # {'title': 'z-saves vorp', 'runtime column': 'z_saves_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-gaa', 'runtime column': 'z_gaa', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            # {'title': 'z-gaa vorp', 'runtime column': 'z_gaa_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-sv%', 'runtime column': 'z_save%', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            # {'title': 'z-sv% vorp', 'runtime column': 'z_save%_vorp', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Cumulative', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(goalie_cumulative_zscore_columns['columns'])

    goalie_pg_zscore_columns = {
        'columns': [
            {'title': 'z-w pg', 'alias': 'z-wins', 'runtime column': 'z_wins_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-sv pg', 'alias': 'z-saves', 'runtime column': 'z_saves_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-gaa pg', 'alias': 'z-gaa', 'runtime column': 'z_gaa_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-sv% pg', 'alias': 'z-sv%', 'runtime column': 'z_save%_pg', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per game', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(goalie_pg_zscore_columns['columns'])

    goalie_p60_zscore_columns = {
        'columns': [
            {'title': 'z-w p60', 'alias': 'z-wins', 'runtime column': 'z_wins_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-sv p60', 'alias': 'z-saves', 'runtime column': 'z_saves_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-gaa p60', 'alias': 'z-gaa', 'runtime column': 'z_gaa_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
            {'title': 'z-sv% p60', 'alias': 'z-sv%', 'runtime column': 'z_save%_p60', 'format': eval(f_2_decimals_show_0), 'stat_type': 'Per 60 minutes', 'default order': 'desc', 'data_group': ('goalie', 'z_score_cat'), 'hide': True},
        ],
    }

    config['columns'].extend(goalie_p60_zscore_columns['columns'])

    return deepcopy(config)

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/player-data')
def player_data():

    # Get the values for the request parameters
    season_or_date_radios = request.args.get('seasonOrDateRadios')
    from_season = request.args.get('fromSeason')
    to_season = request.args.get('toSeason')
    from_date = request.args.get('fromDate')
    to_date = request.args.get('toDate')
    game_type = request.args.get('gameType')
    stat_type = request.args.get('statType')
    pool_id = request.args.get('poolID')

    # Call your get_player_data function with the specified parameters
    data_dict = rank_players(season_or_date_radios, from_season, to_season, from_date, to_date, pool_id, game_type, stat_type)

    # Return the player data as JSON
    return jsonify(data_dict).get_json()

if __name__ == '__main__':
    app.run()
