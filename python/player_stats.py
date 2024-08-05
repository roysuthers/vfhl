# Import Python modules
import textwrap
import webbrowser
from os import path
from typing import Dict
from urllib.request import pathname2url

import numpy as np
import pandas as pd
import requests

import get_player_data
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

    if position == 'Forwards':
        forward_mask = df.eval(get_player_data.forwards_filter)
        minimum_games_filter = get_player_data.minimum_skater_games_percent
        minimum_skater_games_mask = df.eval(get_player_data.minimum_skater_games_filter)
        df = df.loc[forward_mask & minimum_skater_games_mask]
    elif position == 'Defensemen':
        defense_mask = df.eval(get_player_data.defense_filter)
        minimum_games_filter = get_player_data.minimum_skater_games_percent
        minimum_skater_games_mask = df.eval(get_player_data.minimum_skater_games_filter)
        df = df.loc[defense_mask & minimum_skater_games_mask]
    else: # positiion == 'Goalies':
        goalie_mask = df.eval(get_player_data.goalie_filter)
        minimum_games_filter = get_player_data.minimum_goalie_games_percent
        minimum_goalie_starts_mask = df.eval(get_player_data.minimum_goalie_starts_filter)
        df = df.loc[goalie_mask & minimum_goalie_starts_mask]

    # set position prefix
    if position == 'Forwards':
        prefix = 'f '
    elif position == 'Defensemen':
        prefix = 'd '
    else:
        prefix = ''

    row_headers = ['Minimum', 'Maximum', 'Mean', 'Std Dev', 'Z-score Counts', 'Elite', 'Great', 'Good', 'Average', 'Total - Average +']

    column_headers = {
        'Forwards': ['goals', 'assists', 'points_pp', 'shots', 'takeaways', 'hits', 'blocked', 'pim'],
        'Defensemen': ['points', 'goals', 'assists', 'points_pp', 'shots', 'takeaways', 'hits', 'blocked', 'pim'],
        'Goalies': ['wins', 'saves', 'gaa', 'save%']
    }

    # Define formatting information for each row header and column header combination
    formatting_info = {
        'Minimum': {
            'gaa': '{:0.2f}',
            'save%': '{:0.3f}',
            'default': '{:0.2f}' if stat_type != 'Cumulative' else '{:.0f}'
        },
        'Maximum': {
            'gaa': '{:0.2f}',
            'save%': '{:0.3f}',
            'default': '{:0.2f}' if stat_type != 'Cumulative' else '{:.0f}'
        },
        'Mean': {
            'gaa': '{:0.2f}',
            'save%': '{:0.3f}',
            'default': '{:0.2f}' if stat_type != 'Cumulative' else '{:0.1f}'
        },
        'Std Dev': {
            'gaa': '{:0.2f}',
            'save%': '{:0.3f}',
            'default': '{:0.2f}' if stat_type != 'Cumulative' else '{:0.1f}'
        },
        'Z-score Counts': {
            'default': ''
        },
        'Elite': {
            'default': lambda x, z_from: str(len(df[(df[x] >= z_from)])),
        },
        'Great': {
            'default': lambda x, z_from, z_to: str(len(df[(df[x] >= z_from) & (df[x] < z_to)])),
        },
        'Good': {
            'default': lambda x, z_from, z_to: str(len(df[(df[x] >= z_from) & (df[x] < z_to)])),
        },
        'Average': {
            'default': lambda x, z_from, z_to: str(len(df[(df[x] >= z_from) & (df[x] < z_to)])),
        },
        'Total - Average +': {
            'default': lambda x, z_from: str(len(df[(df[x] >= z_from)])),
        }
    }

    data = []
    for row_header in row_headers:
        if row_header == 'Elite':
            z_from = 3
            row_data = [f'&nbsp;&nbsp;>= {z_from}']
        elif row_header == 'Great':
            z_from = 2
            z_to = 3
            row_data = [f'&nbsp;&nbsp;>= {z_from} and < {z_to}']
        elif row_header == 'Good':
            z_from = 1
            z_to = 2
            row_data = [f'&nbsp;&nbsp;>= {z_from} and < {z_to}']
        elif row_header == 'Average':
            z_from = 0
            z_to = 1
            row_data = [f'&nbsp;&nbsp;>= {z_from} and < {z_to}']
        elif row_header == 'Total - Average +':
            z_from = 0
            row_data = [f'&nbsp;&nbsp;>= {z_from}']
        else:
            row_data = [row_header]

        for column_header in column_headers[position]:
            dict_elem = f'{prefix}{column_header}'
            z_header = f'z_{column_header}'

            if column_header not in formatting_info[row_header]:
                format_string = formatting_info[row_header]['default']
            else:
                format_string = formatting_info[row_header][column_header]

            if row_header == 'Minimum':
                row_data.append(format_string.format(min_cat[dict_elem]))
            elif row_header == 'Maximum':
                row_data.append(format_string.format(max_cat[dict_elem]))
            elif row_header == 'Mean':
                row_data.append(format_string.format(mean_cat[dict_elem]))
            elif row_header == 'Std Dev':
                row_data.append(format_string.format(std_cat[dict_elem]))
            elif row_header == 'Z-score Counts':
                row_data.append('')
            elif row_header in ('Elite', 'Total - Average +'):
                row_data.append(format_string(z_header, z_from))
            elif row_header in ('Great', 'Good', 'Average'):
                row_data.append(format_string(z_header, z_from, z_to))

        data.append(row_data)

    if position == 'Goalies':
        df_stat_summary = pd.DataFrame(data, columns=['Agg Type', 'w', 'sv', 'gaa', 'sv%'])
    elif position == 'Forwards':
        df_stat_summary = pd.DataFrame(data, columns=['Agg Type', 'g', 'a', 'ppp', 'sog', 'tk', 'hits', 'blk', 'pim'])
    else: # position == 'Defensemen'
        df_stat_summary = pd.DataFrame(data, columns=['Agg Type', 'pts', 'g', 'a', 'ppp', 'sog', 'tk', 'hits', 'blk', 'pim'])

    styler = df_stat_summary.style.set_caption(f'<br /><b><u>{stat_type} Stats Summary for {str(len(df))} {position}</b></u><br />(minimum {minimum_games_filter}% of team games)<br /><br />')
    styler.set_table_attributes('style="display: inline-block; border-collapse:collapse"')
    styler.set_table_styles(setCSS_TableStyles())
    if position == 'Goalies':
        styler.set_properties(subset=['w', 'sv', 'gaa', 'sv%'], **{'text-align': 'center'})
    elif position == 'Forwards':
        styler.set_properties(subset=['g', 'a', 'ppp', 'sog', 'tk', 'hits', 'blk', 'pim'], **{'text-align': 'center'})
    else: # position == 'Defensemen'
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

    # get players on nhl team rosters
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

    df = pd.read_sql(f'{select_sql} {from_tables} {where_clause}', con=get_db_connection())

    # get inactive nhl players on pool team rosters
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
        'ptr.keeper'
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
        df_temp.loc[idx, 'pos'] = f'{primary_position}W' if primary_position in ('L', 'R') else primary_position
        df_temp.loc[idx, 'team_abbr'] = team_abbr


    # First, ensure that 'seasonID' and 'player_id' are set as the index for both dataframes
    df.set_index(['seasonID', 'player_id'], inplace=True)
    df_temp.set_index(['seasonID', 'player_id'], inplace=True)
    # Find the rows in df_temp that are not in df
    df_temp = df_temp.loc[~df_temp.index.isin(df.index)]
    # Concatenate df and df_temp
    df = pd.concat([df, df_temp])
    # Reset the index
    df.reset_index(inplace=True)

    # set None column values to empty
    df['poolteam_id'] = df['poolteam_id'].apply(lambda x: '' if x is None else x)
    df['pool_team'] = df['pool_team'].apply(lambda x: '' if x is None else x)
    df['status'] = df['status'].apply(lambda x: '' if x is None else x)
    df['keeper'] = df['keeper'].apply(lambda x: 'Yes' if x == 'y' else ('MIN' if x == 'm' else ''))

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
        f_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Forwards'),
        f_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Forwards'),
        d_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Defensemen'),
        d_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Defensemen'),
        g_cumulative_stat_summary_table=create_stat_summary_table(df=df_cumulative, max_cat=cumulative_max_cat, min_cat=cumulative_min_cat, mean_cat=cumulative_mean_cat, std_cat=cumulative_std_cat, stat_type='Cumulative', position='Goalies'),
        g_per_game_stat_summary_table=create_stat_summary_table(df=df_per_game, max_cat=per_game_max_cat, min_cat=per_game_min_cat, mean_cat=per_game_mean_cat, std_cat=per_game_std_cat, stat_type='Per Game', position='Goalies'),
    )

    with open(stats_summary_html_file, 'w', encoding="utf-8-sig") as f:
        f.write(stat_summary_tables_html)

    url = 'file:{}'.format(pathname2url(path.abspath(stats_summary_html_file)))
    webbrowser.open(url)

    return
