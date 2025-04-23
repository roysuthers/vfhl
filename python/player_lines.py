#import the libraries
import logging
import textwrap
import time
import traceback
import re
from typing  import Dict, List
from datetime import date

import numpy as np
import pandas as pd
import PySimpleGUI as sg
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from clsBrowser import Browser
from utils import assign_player_ids, get_db_connection


def main(dialog: sg.Window=None):

    # df = from_daily_fantasy_fuel(dialog=dialog)
    df = from_daily_faceoff(dialog=dialog)

    return df

def from_daily_fantasy_fuel(dialog: sg.Window=None, game_date: str=date.strftime(date.today(), '%Y-%m-%d')) -> pd.DataFrame:

    try:

        logger = logging.getLogger(__name__)

        #specify the url
        daily_fantasy_fuel_com = f'https://www.dailyfantasyfuel.com/nhl/projections/draftkings/{game_date}/'

        msg = f'Opening "{daily_fantasy_fuel_com}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return pd.DataFrame.from_dict([])
        else:
            logger.debug(msg)

        if dialog is None:
            logger.debug('Getting browser...')

        with Browser() as browser:

            if dialog is None:
                logger.debug(f'Browser = {browser}')

            # Set default wait time
            wait = WebDriverWait(browser, 60)

            if dialog is None:
                logger.debug(f'Getting "{daily_fantasy_fuel_com}"')

            # query the website and return the html to the variable 'page'
            browser.get(daily_fantasy_fuel_com)

            if dialog is None:
                logger.debug(f'Returned from "{daily_fantasy_fuel_com}"')

            if 'No Projections Found' in browser.page_source:
                if dialog:
                    sg.popup('TimeoutException: No line projections to report for {game_date} games.')
                else:
                    logger.error('TimeoutException: No line projections to report for {game_date} games.')
                return pd.DataFrame.from_dict([])

            try:
                show_more_players = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="projections-show-more"]/div/div/span')))
            except TimeoutException as e:
                if dialog:
                    sg.popup(f'TimeoutException: No line projections to report for {game_date} games.')
                else:
                    logger.error(repr(e))
                    logger.error(f'TimeoutException: No line projections to report for {game_date} games.')
                return pd.DataFrame.from_dict([])

            # 1st, click the "Show More Players" link
            show_more_players.click()

            msg = f'Scraping "{daily_fantasy_fuel_com}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return pd.DataFrame.from_dict([])
            else:
                logger.debug(msg)

            try:
                table = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="projections"]/div[1]/div[2]/div/div/table')))
            except TimeoutException as e:
                if dialog:
                    sg.popup('TimeoutException: No line projections to report for {game_date} games.')
                else:
                    logger.error(repr(e))
                    logger.error('TimeoutException: No line projections to report for {game_date} games.')
                return pd.DataFrame.from_dict([])

            players: List[Dict] = []
            trs = table.find_elements(By.CLASS_NAME, 'projections-listing')
            for tr in trs:
                players.append(
                    {
                        'name': tr.get_attribute('data-name'),
                        'first_name': tr.get_attribute('data-fn'),
                        'last_name': tr.get_attribute('data-ln'),
                        'pos': tr.get_attribute('data-pos'),
                        'rest': tr.get_attribute('data-rest'),
                        'team': tr.get_attribute('data-team'),
                        'line': tr.get_attribute('data-reg_line'),
                        'pp_line': tr.get_attribute('data-pp_line'),
                    }
                )

    except Exception as e:
        if dialog:
            sg.PopupScrolled(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)), modal=True)
        else:
            logger.error(repr(e))
        return pd.DataFrame.from_dict([])

    return pd.DataFrame.from_dict(players)

def from_daily_faceoff(dialog: sg.Window=None, batch: bool=False) -> pd.DataFrame:

    try:

        logger = logging.getLogger(__name__)

        #specify the url
        url = 'https://www.dailyfaceoff.com/teams'

        msg = f'Opening "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return pd.DataFrame.from_dict([])
        else:
            logger.debug(msg)

        if batch is True:
            logger.debug('Getting browser...')

        with Browser() as browser:

            if batch is True:
                logger.debug(f'Browser = {browser}')

            # Set default wait time
            wait = WebDriverWait(browser, 2)

            if batch is True:
                logger.debug(f'Getting "{url}"')

            attempts = 0
            while attempts < 3:
                try:
                    # query the website
                    browser.get(url)
                    # If the page loads successfully, the loop will break
                    break
                except TimeoutException:
                    attempts += 1
                    if batch is True:
                        if attempts >= 3:
                            logger.error(f"Timeout occurred for {url} on the 3rd attempt. Returning without getting player lines.")
                            return pd.DataFrame.from_dict([])
                        else:
                            logger.debug(f"Timeout occurred for {url}. Retrying...")

                    # Respectful scraping: sleep to avoid hitting the server with too many requests
                    time.sleep(10)

            if batch is True:
                logger.debug(f'Returned from "{url}"')

            msg = f'Scraping "{url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return pd.DataFrame.from_dict([])
            else:
                logger.debug(msg)

            section = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="all_teams"]')))

            a_tags = section.find_elements(By.TAG_NAME, 'a')
            team_urls = []
            for a_tag in a_tags:
                team_urls.append(a_tag.get_attribute('href'))

            team_abbrs = {
                'anaheim-ducks': 'ANA',
                'arizona-coyotes': 'ARI',
                'boston-bruins': 'BOS',
                'buffalo-sabres': 'BUF',
                'calgary-flames': 'CGY',
                'carolina-hurricanes': 'CAR',
                'chicago-blackhawks': 'CHI',
                'colorado-avalanche': 'COL',
                'columbus-blue-jackets': 'CBJ',
                'dallas-stars': 'DAL',
                'detroit-red-wings': 'DET',
                'edmonton-oilers': 'EDM',
                'florida-panthers': 'FLA',
                'los-angeles-kings': 'LAK',
                'minnesota-wild': 'MIN',
                'montreal-canadiens': 'MTL',
                'nashville-predators': 'NSH',
                'new-jersey-devils': 'NJD',
                'new-york-islanders': 'NYI',
                'new-york-rangers': 'NYR',
                'ottawa-senators': 'OTT',
                'philadelphia-flyers': 'PHI',
                'pittsburgh-penguins': 'PIT',
                'san-jose-sharks': 'SJS',
                'seattle-kraken': 'SEA',
                'st-louis-blues': 'STL',
                'tampa-bay-lightning': 'TBL',
                'toronto-maple-leafs': 'TOR',
                'vancouver-canucks': 'VAN',
                'vegas-golden-knights': 'VGK',
                'washington-capitals': 'WSH',
                'winnipeg-jets': 'WPG',
                'utah-hockey-club': 'UTA'
            }

            html_for_teams = []
            for url in team_urls:

                # 'https://www.dailyfaceoff.com/teams/anaheim-ducks/line-combinations'
                team_name = url.split('/')[-2]
                try:
                    team_abbr = team_abbrs[team_name]
                except Exception as e:
                    continue

                msg = f"Getting page for {team_abbr}: {url}"
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=1)
                else:
                    logger.debug(msg)

                try:
                    browser.get(url)
                except TimeoutException as e:
                    pass # seems that the web page is actually persent, but waiting on something else

                forwards = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="line_combos"]/div[1]/div')))
                forwards_html = forwards.get_attribute('innerHTML')

                defense = browser.find_element(By.XPATH, '//*[@id="line_combos"]/div[4]')
                defense_html = defense.get_attribute('innerHTML')

                pp1 = browser.find_element(By.XPATH, '//*[@id="line_combos"]/div[6]')
                pp1_html = pp1.get_attribute('innerHTML')

                pp2 = browser.find_element(By.XPATH, '//*[@id="line_combos"]/div[8]')
                pp2_html = pp2.get_attribute('innerHTML')

                html_for_teams.append({'team': team_abbr, 'Sections': {'Forwards': forwards_html, 'Defensive Pairings': defense_html, '1st Powerplay Unit': pp1_html, '2nd Powerplay Unit': pp2_html}})

            players = []
            for element in html_for_teams:

                team_abbr, sections = element.values()

                msg = f'Getting line combinations for "{team_abbr}"'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                try:

                    # Extract player names for each section
                    player_data = {}
                    for section, html in sections.items():

                        line = 0
                        pos = ''
                        if section == 'Forwards':
                            pos = 'F'
                        elif section == 'Defensive Pairings':
                            pos = 'D'

                        soup = BeautifulSoup(html, 'html.parser')

                        div_tags = soup.findAll('div', attrs={'class': 'justify-evenly'})
                        for element in div_tags:
                            # for some reason, element.get_attribute('text') and element.text don't retrive the text, though I know it's
                            # there when I debug. Getting the innerText works!
                            element_text = element.getText()
                            if element_text in ('LWCRW'):
                                continue
                            line += 1
                            player_elements = element.findAll('a')
                            for player_element in player_elements:
                                player_name = player_element.getText()
                                if player_name == '':
                                    continue
                                if section in ('Forwards', 'Defensive Pairings'):
                                    if player_name not in player_data:
                                        player_data[player_name] = {'pos': pos, 'line': line}
                                elif section == '1st Powerplay Unit':
                                    if player_name in player_data:  # Only add if player is in 'Forwards' or 'Defensive Pairings'
                                        player_data[player_name]['pp unit'] = '1'
                                elif section == '2nd Powerplay Unit':
                                    if player_name in player_data:  # Only add if player is in 'Forwards' or 'Defensive Pairings'
                                        player_data[player_name]['pp unit'] = '2'

                except Exception as e:
                    msg = f'Scraping "{url}" failed for "{team_name}". Reason: {repr(e)}...'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=2)
                    else:
                        logger.error(msg)
                    return pd.DataFrame.from_dict([])

                for player_name, data in player_data.items():
                    players.append(
                        {
                            'name': player_name,
                            # 'first_name': '',
                            # 'last_name': '',
                            'pos': data['pos'],
                            # 'rest': np.nan,
                            'team': team_abbr,
                            'line': data['line'],
                            'pp_line': data['pp unit'] if 'pp unit' in data else '',
                        }
                    )

            # Respectful scraping: sleep to avoid hitting the server with too many requests
            time.sleep(10)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        if dialog:
            sg.PopupScrolled(msg, modal=True)
        else:
            logger.error(msg)
        return pd.DataFrame.from_dict([])

    return pd.DataFrame.from_dict(players)

def _5v5_hockey_goalies(pool_id: int, dialog: sg.Window=None, batch: bool=False) -> pd.DataFrame:

    try:

        df = pd.DataFrame()

        if batch is True:
            logger = logging.getLogger(__name__)

        #specify the urls
        login_url = 'https://5v5hockey.com/login/'
        goalies_url = 'https://5v5hockey.com/daily-fantasy/goalies/'

        msg = 'Getting browser...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return df
        else:
            logger.debug(msg)

        with Browser() as browser:

            if batch is True:
                logger.debug(f'Browser = {browser}')

            # Set default wait time
            wait = WebDriverWait(browser, 2)

            msg = f'Loging in at "{login_url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return df
            else:
                logger.debug(msg)

            try:

                browser.get(login_url)

                user_name = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="id_username"]')))
                password = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="id_password"]')))
                login_button = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="submit-login-form-btn"]')))

                user_name.send_keys('Snickman')
                password.send_keys('l2eH!HJFf(')
                login_button.click()

            except TimeoutException as e:
                if batch is True:
                    if attempts >= 3:
                        logger.error(f"Timeout occurred for {goalies_url} on the 3rd attempt. Returning without getting starting goalie projections.")
                        return df
                    else:
                        logger.debug(f"Timeout occurred for {goalies_url}. Retrying...")
                return df

            time.sleep(2)

            attempts = 0
            while attempts < 3:
                try:

                    msg = f'Opening "{goalies_url}"...'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=2)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return df
                    else:
                        logger.debug(msg)

                    # query the website
                    browser.get(goalies_url)

                    matchup_goalies_container = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="hockeyDataGrid"]/div/div[1]/div[2]/div[3]/div[1]/div/div[1]')))
                    matchup_goalie_stats_container = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="hockeyDataGrid"]/div/div[1]/div[2]/div[3]/div[1]/div/div[2]/div/div')))
                    dfs_goalies_container = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="goaliesTool"]/div/div[1]/div[2]/div[3]/div[1]/div/div[1]')))
                    dfs_goalie_stats_container = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="goaliesTool"]/div/div[1]/div[2]/div[3]/div[1]/div/div[2]')))

                    # If the page loads successfully, and the dfs_goalies_container is not empty, the loop will break
                    if dfs_goalies_container.get_attribute('innerText') == '':

                        attempts += 1
                        if batch is True:
                            if attempts >= 3:
                                logger.error(f'URL "{goalies_url}" not loaded, on the 3rd attempt. Returning without getting starting goalie projections.')
                                return df
                            else:
                                logger.debug(f'URL "{goalies_url}" not loaded. Retrying...')

                        # Respectful scraping: sleep to avoid hitting the server with too many requests
                        time.sleep(120)

                        continue

                    break

                except TimeoutException:
                    attempts += 1
                    if batch is True:
                        if attempts >= 3:
                            logger.error(f"Timeout occurred for {goalies_url} on the 3rd attempt. Returning without getting starting goalie projections.")
                            return df
                        else:
                            logger.debug(f"Timeout occurred for {goalies_url}. Retrying...")

                    # Respectful scraping: sleep to avoid hitting the server with too many requests
                    time.sleep(120)

            msg = f'Scraping "{goalies_url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return df
            else:
                logger.debug(msg)

            tool_date = browser.find_element(By.XPATH, '//*[@id="datepicker_to"]').get_attribute('value')
            if tool_date  != date.strftime(date.today(), '%Y-%m-%d'):
                msg = f"Date mismatch: expected {date.strftime(date.today(), '%Y-%m-%d')}, got {tool_date }"
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                else:
                    logger.error(msg)
                return df

            ###########################################################################################
            # get Matchups table data
            matchup_goalies_container_html = matchup_goalies_container.get_attribute('innerHTML')
            matchup_goalie_stats_container_html = matchup_goalie_stats_container.get_attribute('innerHTML')
            matchup_goalies_container_soup = BeautifulSoup(matchup_goalies_container_html, 'html.parser')
            matchup_goalie_stats_container_soup = BeautifulSoup(matchup_goalie_stats_container_html, 'html.parser')

            matchup_goalies = [item.getText() for item in matchup_goalies_container_soup.findAll('div', attrs={'col-id': 'goalie'})]
            teams = [item.getText() for item in matchup_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'team'})]
            opponents = [item.getText() for item in matchup_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'opponent'})]
            statuses = [item.getText() for item in matchup_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'status'})]

            ###########################################################################################
            # get DFS table data
            dfs_goalies_container_html = dfs_goalies_container.get_attribute('innerHTML')
            dfs_goalie_stats_container_html = dfs_goalie_stats_container.get_attribute('innerHTML')
            dfs_goalies_container_soup = BeautifulSoup(dfs_goalies_container_html, 'html.parser')
            dfs_goalie_stats_container_soup = BeautifulSoup(dfs_goalie_stats_container_html, 'html.parser')

            dfs_goalies = [item['src'].split('/')[-1].split('-logo')[0].replace('_', ' ') for item in dfs_goalies_container_soup.findAll('img', attrs={'class': 'table-team-logo'}) if 'src' in item.attrs]
            ranks = [int(item.getText()) for item in dfs_goalies_container_soup.findAll('div', attrs={'col-id': 'rank'})]
            overall_scores = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'overall_score'})]
            win_percents = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'win_percent'})]
            xgas = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'xga'})]
            xsas = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'xsa'})]
            xsvs = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'xsv'})]
            xsv_percents = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'xsv_percent'})]
            qs_percents = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'qs_percent'})]
            xsv_percent_1s = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'xsv_percent_1'})]
            gaas = [item.getText() for item in dfs_goalie_stats_container_soup.findAll('div', attrs={'col-id': 'gaa'})]

        ###########################################################################################
        # put Matchups table data into dataframe
        data = {
            'Goalie': matchup_goalies,
            'Team': teams,
            'Opponent': opponents,
            'Status': statuses,
        }
        df_matchups = pd.DataFrame(data)

        ###########################################################################################
        # put DFS table data into dataframe
        data = {
            'Goalie': dfs_goalies,
            'Rank': ranks,
            'Score': overall_scores,
            'Win%': win_percents,
            'xGA': xgas,
            'xSA': xsas,
            'xSV': xsvs,
            'xSV%': xsv_percents,
            'QS%': qs_percents,
            'SV%': xsv_percent_1s,
            'GAA': gaas
        }
        df_dfs = pd.DataFrame(data)

        ###########################################################################################
        # get pool team managers
        columns = ' '.join(textwrap.dedent(f'''\
            ptr.player_id,
            p.full_name as name,
            pt.name as pool_team,
            ptr.status
        ''').splitlines())

        select_sql = f'select {columns}'

        # build table joins
        from_tables = textwrap.dedent('''\
            from PoolTeamRoster ptr
            left outer join Player p on p.id=ptr.player_id
            left outer join PoolTeam pt ON pt.id=ptr.poolteam_id
        ''')

        where_clause = f'where pt.pool_id=? and p.primary_position="G"'

        sql = textwrap.dedent(f'''\
            {select_sql}
            {from_tables}
            {where_clause}
        ''')

        params = (pool_id,)

        df_managers = pd.read_sql(sql, params=params, con=get_db_connection())

        manager_abbrs = {
            'Avovocado': 'Avo',
            'Banshee': 'Banshee',
            'Camaro SS': 'Camaro',
            'CanDO Know Huang': 'CanDO',
            'El Paso Pirates': 'EPP',
            "Fowler's Flyers": 'FF',
            'Horse Palace 26': 'Horsey',
            'One Man Gang Bang': 'OMGB',
            'Urban Legends': 'UL',
            'WhatA LoadOfIt': 'WhatA',
            'Wheels On Meals': 'Wheels',
        }
        df_managers['pool_team'] = df_managers['pool_team'].map(manager_abbrs)

        # Combine 'pool_team' and 'status' columns into one column 'Manager'
        df_managers['Manager'] = df_managers['pool_team'] + ' (' + df_managers['status'] + ')'

        # Drop 'pool_team' and 'status' columns
        df_managers.drop(columns=['pool_team', 'status'], inplace=True)

        df_managers.rename(columns={'name': 'Goalie'}, inplace=True)

        ###########################################################################################
        # merge Matchups & DFS dataframes
        df = pd.merge(df_matchups, df_dfs, on='Goalie', how='outer')

        # Replace team and opponent names with abbreviations
        team_abbrs = {
            'Avalanche': 'COL',
            'Blackhawks': 'CHI',
            'Blue Jackets': 'CBJ',
            'Blues': 'STL',
            'Bruins': 'BOS',
            'Canadiens': 'MTL',
            'Canucks': 'VAN',
            'Capitals': 'WSH',
            'Devils': 'NJD',
            'Ducks': 'ANA',
            'Flames': 'CGY',
            'Flyers': 'PHI',
            'Hurricanes': 'CAR',
            'Islanders': 'NYI',
            'Jets': 'WPG',
            'Kings': 'LAK',
            'Knights': 'VGK',
            'Kraken': 'SEA',
            'Lightning': 'TBL',
            'Maple Leafs': 'TOR',
            'Oilers': 'EDM',
            'Panthers': 'FLA',
            'Penguins': 'PIT',
            'Predators': 'NSH',
            'Rangers': 'NYR',
            'Red Wings': 'DET',
            'Sabres': 'BUF',
            'Senators': 'OTT',
            'Sharks': 'SJS',
            'Stars': 'DAL',
            'Utah': 'UTA',
            'Wild': 'MIN',
        }
        df['Team'] = df['Team'].map(team_abbrs)
        df['Opponent'] = df['Opponent'].map(team_abbrs)

        ###########################################################################################
        # merge Matchups/DFS & Pool Team Manager dataframes
        df['pos'] = 'G'
        df['player_id'] = assign_player_ids(df=df, player_name='Goalie', nhl_team='Team', pos_code='pos')
        df.drop(columns=['pos'], inplace=True)

        df = pd.merge(df, df_managers, on='player_id', how='left')

        ###########################################################################################
        # clean up dataframe
        df.rename(columns={'Goalie_x': 'Goalie'}, inplace=True)
        df.drop(columns=['player_id', 'Goalie_y'], inplace=True)

        # Reorder columns
        reorder_columns = ['Rank', 'Goalie', 'Team', 'Manager', 'Score', 'Status', 'Opponent']
        columns_order = reorder_columns + [col for col in df.columns if col not in reorder_columns]
        df = df[columns_order]

        # Fill NaN values in 'Rank' column with the maximum of the other 'Rank' values
        max_rank = df['Rank'].max() + 1
        df['Rank'].fillna(max_rank, inplace=True)

        # Convert 'Rank' column to integer type
        df['Rank'] = df['Rank'].astype(int)

        # Fill NaN values in 'Score' column with 0
        numeric_columns = ['Score', 'Win%', 'xGA', 'xSA', 'xSV', 'xSV%', 'QS%', 'SV%', 'GAA']
        df[numeric_columns] = df[numeric_columns].fillna(0)

        # Fill NaN values in 'Status' column with empty string
        df['Status'].fillna('', inplace=True)
        df['Manager'].fillna('', inplace=True)

        ###########################################################################
        # assign unique game number to each pair of teams playing each other
        #
        # Step 1: Create an order-invariant game pair column
        df["game_pair"] = df.apply(
            lambda row: tuple(sorted([row["Team"], row["Opponent"]])), axis=1
        )

        # Step 2: Factorize the game pair to assign a unique game number
        df["Game"] = pd.factorize(df["game_pair"])[0] + 1

        # (Optional) If you prefer not to keep the auxiliary column:
        df.drop(columns="game_pair", inplace=True)

        # Get the list of all columns.
        cols = df.columns.tolist()
        # Create a new column ordering: start with 'game_number' and then the rest.
        new_order = ["Game"] + [col for col in cols if col != "Game"]
        # Reassign the DataFrame to have this new column order.
        df = df[new_order]
        ###########################################################################

        df.sort_values(by=['Rank'], inplace=True)
        df.set_index('Rank', inplace=True, drop=False)
        df.index = range(len(df))

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
        else:
            logger.error(msg)

    return df

def _5v5_todays_games(dialog: sg.Window=None, batch: bool=False) -> pd.DataFrame:

    try:

        df = pd.DataFrame()

        if batch is True:
            logger = logging.getLogger(__name__)

        #specify the url
        url = 'https://5v5hockey.com/daily-fantasy/todays-games/'

        msg = 'Getting browser...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return df
        else:
            logger.debug(msg)

        with Browser() as browser:

            if batch is True:
                logger.debug(f'Browser = {browser}')

            # Set default wait time
            wait = WebDriverWait(browser, 2)

            msg = f'Opening "{url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return df
            else:
                logger.debug(msg)

            attempts = 0
            while attempts < 3:
                try:
                    # query the website
                    browser.get(url)
                    # If the page loads successfully, the loop will break
                    break
                except TimeoutException:
                    attempts += 1
                    if batch is True:
                        if attempts >= 3:
                            logger.error(f"Timeout occurred for {url} on the 3rd attempt. Returning without getting starting goalie projections.")
                            return df
                        else:
                            logger.debug(f"Timeout occurred for {url}. Retrying...")

                    # Respectful scraping: sleep to avoid hitting the server with too many requests
                    time.sleep(10)

            msg = f'Scraping "{url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return df
            else:
                logger.debug(msg)

            games_container = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="hockeyDataGrid"]/div/div[1]/div[2]/div[3]/div[1]/div/div[2]/div/div')))
            games_container_html = games_container.get_attribute('innerHTML')
            games_container_soup = BeautifulSoup(games_container_html, 'html.parser')

            # dates = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'date'})]
            home_teams = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'home_team'})]
            away_teams = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'away_team'})]
            over_unders = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'over_under'})]
            expected_home_goals = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'home_implied'})]
            expected_away_goals = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'away_implied'})]
            home_ml_odds = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'home_ml'})]
            away_ml_odds = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'away_ml'})]
            home_win_percents = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'home_win_percent'})]
            away_win_percents = [item.getText() for item in games_container_soup.findAll('div', attrs={'col-id': 'away_win_percent'})]

        data = {
            # 'Date': dates,
            'Home Team': home_teams,
            'Away Team': away_teams,
            'Over/Under': over_unders,
            'xHomeG': expected_home_goals,
            'xAwayG': expected_away_goals,
            'Home ML': home_ml_odds,
            'Away ML': away_ml_odds,
            'Home Win %': home_win_percents,
            'Away Win %': away_win_percents,
        }
        df = pd.DataFrame(data)

        # Replace team and opponent names with abbreviations
        team_abbrs = {
            'Avalanche': 'COL',
            'Blackhawks': 'CHI',
            'Blue Jackets': 'CBJ',
            'Blues': 'STL',
            'Bruins': 'BOS',
            'Canadiens': 'MTL',
            'Canucks': 'VAN',
            'Capitals': 'WSH',
            'Devils': 'NJD',
            'Ducks': 'ANA',
            'Flames': 'CGY',
            'Flyers': 'PHI',
            'Hurricanes': 'CAR',
            'Islanders': 'NYI',
            'Jets': 'WPG',
            'Kings': 'LAK',
            'Knights': 'VGK',
            'Kraken': 'SEA',
            'Lightning': 'TBL',
            'Maple Leafs': 'TOR',
            'Oilers': 'EDM',
            'Panthers': 'FLA',
            'Penguins': 'PIT',
            'Predators': 'NSH',
            'Rangers': 'NYR',
            'Red Wings': 'DET',
            'Sabres': 'BUF',
            'Senators': 'OTT',
            'Sharks': 'SJS',
            'Stars': 'DAL',
            'Utah': 'UTA',
            'Wild': 'MIN',
        }
        df['Home Team'] = df['Home Team'].map(team_abbrs)
        df['Away Team'] = df['Away Team'].map(team_abbrs)

        # # Fill NaN values in 'Score' column with 0
        # numeric_columns = ['Score', 'Win%', 'xGA', 'xSA', 'xSV', 'xSV%', 'QS%', 'SV%', 'GAA']
        # df[numeric_columns] = df[numeric_columns].fillna(0)

        # # Fill NaN values in 'Status' column with empty string
        # df['Status'].fillna('', inplace=True)
        # df['Manager'].fillna('', inplace=True)

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
        else:
            logger.error(msg)

    return df

if __name__ == "__main__":

    main()

    exit()
