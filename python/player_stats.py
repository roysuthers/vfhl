# Import Python modules
import textwrap
import webbrowser
from os import path
from typing import Dict
from urllib.request import pathname2url

import numpy as np
import pandas as pd
import requests

from clsPlayer import Player
from clsSeason import Season
from constants import NHL_API_URL
from utils import calculate_age, get_db_connection, setCSS_TableStyles, setCSS_TableStyles2, split_seasonID_into_component_years
from constants import generated_html_path

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

def create_stat_summary_table(df: pd.DataFrame, max_cat: Dict, min_cat: Dict, mean_cat: Dict, std_cat: Dict, stat_type: str='Cumulative', position: str='Forwards'):

    # set position prefix
    if position == 'Skaters':
        prefix = 'sktr '
    elif position == 'Forwards':
        prefix = 'f '
    elif position == 'Defense':
        prefix = 'd '
    else:
        prefix = ''

    # Define a dictionary for each position and its corresponding conditions
    cond_dict = {
        'Skaters': (df['pos'] != "G"),
        'Forwards': (df['pos'] != "G") & (df['pos'] != "D"),
        'Defense': (df['pos'] == "D"),
        'Goalies': (df['pos'] == "G")
    }

    # Define a dictionary for each statistic and its corresponding list
    # stats_dict = {
    #     'points': pts_stats,
    #     'goals': g_stats,
    #     'assists': a_stats,
    #     'points_pp': ppp_stats,
    #     'shots': sog_stats,
    #     'takeaways': tk_stats,
    #     'hits': hit_stats,
    #     'blocked': blk_stats,
    #     'pim': pim_stats,
    #     'wins': wins_stats,
    #     'saves': saves_stats,
    #     'gaa': gaa_stats,
    #     'save%': save_pc_stats
    # }

    row_headers = ['Maximum', 'Mean', 'Std Dev', 'Std Dev % of Mean', '+ Std Dev', '1+ Std Dev', '2+ Std Dev', '3+ Std Dev']

    column_headers = {
        'Skaters': ['points', 'goals', 'assists', 'points_pp', 'shots', 'takeaways', 'hits', 'blocked', 'pim'],
        'Goalies': ['wins', 'saves', 'gaa', 'save%']
    }

    position_type = 'Skaters' if position != 'Goalies' else 'Goalies'

    data = []
    for row_header in row_headers:
        row_data = [row_header]
        for column_header in column_headers[position_type]:
            dict_elem = f'{prefix}{column_header}'
            if row_header == 'Maximum':
                if column_header == 'gaa':
                    row_data.append('{:0.2f}'.format(round(min_cat[dict_elem], 2)))
                elif column_header == 'save%':
                    row_data.append('{:0.3f}'.format(round(max_cat[dict_elem], 3)))
                else:
                    if stat_type == 'Cumulative':
                        row_data.append(int(max_cat[dict_elem]))
                    else:
                        row_data.append('{:0.1f}'.format(round(max_cat[dict_elem], 1)))
            elif row_header == 'Mean':
                if column_header == 'gaa':
                    row_data.append('{:0.2f}'.format(round(mean_cat[dict_elem], 2)))
                elif column_header == 'save%':
                    row_data.append('{:0.3f}'.format(round(mean_cat[dict_elem], 3)))
                else:
                    if stat_type == 'Cumulative':
                        row_data.append('{:0.1f}'.format(round(mean_cat[dict_elem], 1)))
                    else:
                        row_data.append('{:0.2f}'.format(round(mean_cat[dict_elem], 2)))
            elif row_header == 'Std Dev':
                if column_header == 'gaa':
                    row_data.append('{:0.2f}'.format(round(std_cat[dict_elem], 2)))
                elif column_header == 'save%':
                    row_data.append('{:0.3f}'.format(round(std_cat[dict_elem], 3)))
                else:
                    if stat_type == 'Cumulative':
                        row_data.append('{:0.1f}'.format(round(std_cat[dict_elem], 1)))
                    else:
                        row_data.append('{:0.2f}'.format(round(std_cat[dict_elem], 2)))
            elif row_header == 'Std Dev % of Mean':
                row_data.append('{:0.1f}'.format(round(std_cat[dict_elem] / mean_cat[dict_elem] * 100, 1)))
            elif row_header == '+ Std Dev':
                if column_header == 'gaa':
                    row_data.append(str(len(df[(df[column_header]<mean_cat[dict_elem]) & cond_dict[position_type]])))
                else:
                    row_data.append(str(len(df[(df[column_header]>mean_cat[dict_elem]) & cond_dict[position_type]])))
            elif row_header == '1+ Std Dev':
                if column_header == 'gaa':
                    row_data.append(str(len(df[(df[column_header]<(mean_cat[dict_elem] + std_cat[dict_elem])) & cond_dict[position_type]])))
                else:
                    row_data.append(str(len(df[(df[column_header]>(mean_cat[dict_elem] + std_cat[dict_elem])) & cond_dict[position_type]])))
            elif row_header == '2+ Std Dev':
                if column_header == 'gaa':
                    row_data.append(str(len(df[(df[column_header]<(mean_cat[dict_elem] + (2 * std_cat[dict_elem]))) & cond_dict[position_type]])))
                else:
                    row_data.append(str(len(df[(df[column_header]>(mean_cat[dict_elem] + (2 * std_cat[dict_elem]))) & cond_dict[position_type]])))
            elif row_header == '3+ Std Dev':
                if column_header == 'gaa':
                    row_data.append(str(len(df[(df[column_header]<(mean_cat[dict_elem] + (3 * std_cat[dict_elem]))) & cond_dict[position_type]])))
                else:
                    row_data.append(str(len(df[(df[column_header]>(mean_cat[dict_elem] + (3 * std_cat[dict_elem]))) & cond_dict[position_type]])))
        data.append(row_data)

    if position == 'Goalies':
        df_stat_summary = pd.DataFrame(data, columns=['Agg Type', 'wins', 'saves', 'gaa', 'save%'])
    else:
        df_stat_summary = pd.DataFrame(data, columns=['Agg Type', 'pts', 'g', 'a', 'ppp', 'sog', 'tk', 'hits', 'blk', 'pim'])

    styler = df_stat_summary.style.set_caption(f'<br /><b><u>{stat_type} Stats Summary - {position}</u></b><br /><br />')
    styler.set_table_attributes('style="display: inline-block; border-collapse:collapse"')
    styler.set_table_styles(setCSS_TableStyles())
    if position == 'Goalies':
        styler.set_properties(subset=['wins', 'saves', 'gaa', 'save%'], **{'text-align': 'center'})
    else:
        styler.set_properties(subset=['pts', 'g', 'a', 'ppp', 'sog', 'tk', 'hits', 'blk', 'pim'], **{'text-align': 'center'})
    stat_summary_table = styler.hide(axis='index').to_html()

    stat_summary_table = stat_summary_table.replace('Agg Type', '')

    return stat_summary_table

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

    game_pace_html_file = f'{generated_html_path}/Manager Game Pace for the {season.name},.html'

    try:
        with open(game_pace_html_file, 'w', encoding="utf-8-sig") as f:
            f.write(game_pace_html)

    except FileNotFoundError:
        raise Exception(f"File not found: {game_pace_html_file}")

    url = 'file:{}'.format(pathname2url(path.abspath(game_pace_html_file)))
    webbrowser.open(url)

    return

def show_stat_summary_tables(df_cumulative: pd.DataFrame, df_per_game: pd.DataFrame, cumulative_max_cat: Dict, cumulative_min_cat: Dict, cumulative_mean_cat: Dict, cumulative_std_cat: Dict, per_game_max_cat: Dict, per_game_min_cat: Dict, per_game_mean_cat: Dict, per_game_std_cat: Dict, caption: str):

    file_name = caption.replace('<b>', '')\
                        .replace('</b>', '')\
                        .replace('<u>', '')\
                        .replace('</u>', '')\
                        .replace('<br/>', '')\
                        .strip()
    stats_summary_html_file = f'{generated_html_path}/Stats Summary for {file_name}.html'

    stat_summary_tables_html = textwrap.dedent('''\
        <!doctype html>
        <html>
            <caption><b><u>{caption}</u></b></caption.
            <body>
                <!-- Stat Summary Tables -->
                <div>
                    {sktr_cumulative_stat_summary_table}
                    &nbsp;&nbsp;
                    {sktr_per_game_stat_summary_table}
                </div>
                <div>
                    {f_cumulative_stat_summary_table}
                    &nbsp;&nbsp;
                    {f_per_game_stat_summary_table}
                </div>
                <div>
                    {d_cumulative_stat_summary_table}
                    &nbsp;&nbsp;
                    {d_per_game_stat_summary_table}
                </div>
                <div>
                    {g_cumulative_stat_summary_table}
                    &nbsp;&nbsp;
                    {g_per_game_stat_summary_table}
                </div>
            </body>
        </html>
    ''').format(
        caption=caption,
        sktr_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Skaters'),
        sktr_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Skaters'),
        f_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Forwards'),
        f_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Forwards'),
        d_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Defense'),
        d_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Defense'),
        g_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Goalies'),
        g_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Goalies'),
    )

    with open(stats_summary_html_file, 'w', encoding="utf-8-sig") as f:
        f.write(stat_summary_tables_html)

    url = 'file:{}'.format(pathname2url(path.abspath(stats_summary_html_file)))
    webbrowser.open(url)

    return
