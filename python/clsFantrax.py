import logging
import os
import re
import requests
import sys
import time
import traceback
from datetime import datetime
from textwrap import dedent
from typing import Dict, List

import pandas as pd
import PySimpleGUI as sg
from selenium.common.exceptions import NoSuchElementException, TimeoutException
# from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.expected_conditions import _find_element
from selenium.webdriver.support.ui import Select, WebDriverWait
from unidecode import unidecode

# Hockey Pool classes
from constants import NHL_API_URL
from clsBrowser import Browser
from clsNHL_API import NHL_API
from clsPlayer import Player
from clsPoolTeam import PoolTeam
from clsPoolTeamRoster import PoolTeamRoster
from clsSeason import Season
from clsTeam import Team
from utils import assign_player_ids, get_db_connection, get_player_id, inches_to_feet, load_nhl_team_abbr_and_id_dict, load_player_name_and_id_dict


# # Dataframe for player stats
# class value_regex_match(object):
#     def __init__(self, locator, regexp):
#         self.locator = locator
#         self.regexp = regexp

#     def __call__(self, driver):
#         value_text = _find_element(driver, self.locator).get_attribute('value')
#         return re.match(self.regexp, value_text)

# class presence_of_element(object):
#     def __init__(self, locator):
#         self.locator = locator

#     def __call__(self, driver):
#         element = _find_element(driver, self.locator)
#         return element

class Fantrax:

    def __del__(self):

        # # Close browser
        # try: self.browser.close()
        # except: pass

        return

    def __init__(self, pool_id, league_id, season_id):

        self.homePage = f'https://www.fantrax.com/fantasy/league/{league_id}/home/'
        self.loginPage = 'https://www.fantrax.com/login'

        self.login_user_xpath = '//*[@id="mat-input-0"]'
        self.login_password_xpath = '//*[@id="mat-input-1"]'
        self.login_button_xpath = '/html/body/app-root/div/div[1]/div[1]/div/app-login/div/section/div[3]/form/div[2]/button/span[1]'

        self.statsPage = f'https://www.fantrax.com/fantasy/league/{league_id}/players'
        self.poolTeamPlayersPage = f'https://www.fantrax.com/fantasy/league/{league_id}/team/roster'
        self.poolStatsPage = f'https://www.fantrax.com/fantasy/league/{league_id}/standings'

        # self.playersPage = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=ALL;maxResultsPerPage=1500'

        self.all_taken_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=ALL_TAKEN;positionOrGroup=ALL;maxResultsPerPage=1500'
        # self.active_taken_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=ACTIVE_TAKEN;positionOrGroup=ALL;maxResultsPerPage=1500'
        # self.minors_taken_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=MINOR_INACTIVE_TAKEN;positionOrGroup=ALL;maxResultsPerPage=1500'

        self.all_available_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=ALL_AVAILABLE;positionOrGroup=ALL;maxResultsPerPage=1500'
        # self.active_available_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=ACTIVE_AVAILABLE;positionOrGroup=ALL;maxResultsPerPage=1500'
        # self.minors_available_players = f'https://www.fantrax.com/fantasy/league/{league_id}/players;statusOrTeamFilter=MINOR_INACTIVE_AVAILABLE;positionOrGroup=ALL;maxResultsPerPage=1500'

        self.watch_list = f'https://www.fantrax.com/fantasy/league/{league_id}/players;reload=3;statusOrTeamFilter=WATCH_LIST;maxResultsPerPage=500'

        self.nhl_team_transactions = 'https://www.fantrax.com/newui/NHL/transactions.go'

        self.manager_position_games_played = f'https://www.fantrax.com/fantasy/league/{league_id}/team/roster;teamId={{team_id}};view=GAMES_PER_POS'

        self.pool_id = pool_id
        self.user_name = 'Roy_Suthers'
        self.season = Season().getSeason(id=season_id)

        self.browser_download_dir = os.path.abspath(f'./python/input/fantrax/{season_id}')

        return

    # def login(self, driver, wait):

    #     count = 0
    #     while True and count < 3:
    #         count += 1

    #         user_id = wait.until(EC.presence_of_element_located((By.XPATH, self.login_user_xpath)))
    #         password = driver.find_element(By.XPATH, self.login_password_xpath)
    #         login_button = driver.find_element(By.XPATH, self.login_button_xpath)

    #         user_id.send_keys(self.user_name)
    #         password.send_keys('in35HenES7')
    #         login_button.click()

    #         try:
    #             errorMsgElem = driver.find_element(By.XPATH, '/html/body/app-root/div/div[1]/div[1]/div/app-login/div/section/form/div[1]/div[2]')
    #             print(errorMsgElem.text)
    #             return False
    #         except:
    #             if driver.current_url==f'https://www.fantrax.com/error/{league_id}':
    #                 # alert_msg = driver.find_element(By.XPATH, '//html/body/app-root/div/div[1]/div[1]/div/app-error/div/section/alert/div/article/div/div/p')
    #                 # print(f'Alert: {alert_msg.text}')
    #                 home_button = driver.find_element(By.XPATH, '/html/body/app-root/div/div[1]/div[1]/div/app-error/div/section/alert/div/article/div/div/div/a/span[1]')
    #                 home_button.click()
    #             break

    #         if count >= 3:
    #             print('3 attempts to log in have failed...')
    #             return False

        return True

    def scrapeNHLTeamTransactions(self, dialog: sg.Window=None):

        try:

            logger = logging.getLogger(__name__)

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            dfNHLTeamTransactions = pd.DataFrame()

            with Browser() as browser:

                # Set default wait time
                wait = WebDriverWait(browser, 60)

                browser.get(self.nhl_team_transactions)

                # for now, only wnat the first table, for the most recent date
                # I may want to change this, if it seems I'm missing some days
                table = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'sport-transactions-table')))[0]

                msg = 'Scraping NHL team transactions...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                try:
                    # skip first row that is for the table column headings
                    rows = table.find_elements(By.CLASS_NAME, 'supertable__row')
                    transactions = []
                    # Define a regex pattern to match the date in the comment, and capture the text after it
                    pattern = r'(\b\w{3} \d{1,2}, \d{4}\b)(.*)'
                    for row in rows:
                        data = row.text.splitlines()
                        player_name = data[0]
                        pos = data[1]
                        team_abbr = data[2].lstrip(' - ')

                        # Use re.search to find the pattern in the text
                        match = re.search(pattern, data[4])
                        # Check if a match was found
                        if match:
                            comment = match.group(2).strip()  # This is the text after the date
                        else:
                            comment = data[4]

                        transactions.append({'player_name': player_name, 'pos': pos, 'team_abbr': team_abbr, 'comment': comment})
                except Exception as e:
                    msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                    if dialog:
                        dialog.close()
                        sg.popup_error(msg)
                    else:
                        logger.error(msg)
                    return

            msg = 'Scraping NHL team transactions completed...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            dfNHLTeamTransactions = pd.DataFrame.from_dict(data=transactions)

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            if dialog:
                dialog.close()
                sg.popup_error(msg)
            else:
                logger.error(msg)

        return dfNHLTeamTransactions

    def scrapePlayerInfo(self, dialog: sg.Window=None, watchlist: bool=False):

        try:

            logger = logging.getLogger(__name__)

            dfPlayers = pd.DataFrame(columns=[
                'player_id',
                'fantrax_id',
                'player_name',
                'nhl_team',
                'pos',
                'minors',
                'watch_list',
                'score',
                'next_opp',
                'rookie',
            ])

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            # Get team IDs, player names & id dictionary, and NHL_API
            team_ids = load_nhl_team_abbr_and_id_dict()
            player_ids = load_player_name_and_id_dict()
            nhl_api = NHL_API()

            with Browser() as browser:

                if watchlist is True:
                    urls_for_player_lists = {'Watch List': self.watch_list}
                else:
                    # need to process minor league lists first to get collection of player ids for those in the minors
                    # for some reason, I was getting the "self.all_taken_players" list rather than the "self.active_taken_players", which
                    # seems to be an overlap of lists; otherwise, why wouldn't just get all available & all taken players, using 2 lists rather than 4
                    # urls_for_player_lists = {
                    #     'Active - Available': self.active_available_players,
                    #     'Minors - Availiable': self.minors_available_players,
                    #     'Active - Taken': self.active_taken_players,
                    #     'Minors - Taken': self.minors_taken_players,
                    # }
                    # Need these lists for lookikng back at previous years info
                    urls_for_player_lists = {
                        'All - Available': self.all_available_players,
                        'All - Taken': self.all_taken_players,
                    }

                # Set default wait time
                wait = WebDriverWait(browser, 60)

                players = []
                for list_type, url in urls_for_player_lists.items():

                    msg = f'Getting "{list_type}" players'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return
                    else:
                        logger.debug(msg)

                    try:
                        browser.get(url)
                        elem = browser.find_element(By.XPATH, "//*[contains(text(), 'There were no results found for the specified criteria.')]")
                        if elem:
                            continue

                    except NoSuchElementException:
                        pass

                    except TimeoutException as e:
                        msg = f'TimeoutException getting "{list_type}" web page.'
                        if dialog:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                            if event == 'Cancel' or event == sg.WIN_CLOSED:
                                return
                        else:
                            logger.debug(msg)
                        continue

                    except AttributeError as e:
                        msg = f'AttributeError:{3} getting "{list_type}" web page.'
                        if dialog:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                            if event == 'Cancel' or event == sg.WIN_CLOSED:
                                return
                        else:
                            logger.debug(msg)
                        continue

                    # first: get player names, teams, and positions
                    try:
                        table1 = wait.until(EC.presence_of_element_located((By.CLASS_NAME, '_ut__aside')))
                    except TimeoutException as e:
                        msg = f'TimeoutException getting "{list_type}" player table.'
                        if dialog:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                            if event == 'Cancel' or event == sg.WIN_CLOSED:
                                return
                        else:
                            logger.debug(msg)
                        continue

                    # second: get player scores and watchlist status
                    table2 = wait.until(EC.presence_of_element_located((By.CLASS_NAME, '_ut__content')))

                    msg = 'Scraping player names, teams, and positions...'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return
                    else:
                        logger.debug(msg)

                    try:
                        rows1 = table1.find_elements(By.TAG_NAME, 'td')
                        rows2 = table2.find_elements(By.TAG_NAME, 'tr')
                        for row1, row2 in zip(rows1, rows2):

                            try:

                                score = row2.find_element(By.CLASS_NAME, 'cell--accent').text
                                # if url == self.minors_available_players and score == '0':
                                # if list_type in ('Active - Available', 'Minors - Availiable') and score == '0':
                                # if list_type in ('Minors - Availiable') and score == '0':
                                if list_type == 'All - Available' and score == '0':
                                    break

                                text_parts = row1.text.splitlines()

                                i = 0
                                if text_parts[0] in ('add', 'swap_horiz'):
                                    i = 1

                                name = text_parts[i]
                                nhl_team = text_parts[-1].strip().lstrip('-').lstrip('(').rstrip(')').strip()
                                team_id = 0
                                if 'N/A' not in nhl_team:
                                    if '/' in nhl_team:
                                        nhl_team = nhl_team.split('/')[-1]
                                    # get nhl team
                                    # kwargs = {'Criteria': [['abbr', '==', nhl_team]]}
                                    # team = Team().fetch(**kwargs)
                                    team_id = team_ids[nhl_team]
                                    if team_id == 0 and nhl_team != 'N/A':
                                        msg = f'NHL team "{nhl_team}" not found for "{name}".'
                                        if dialog:
                                            sg.popup_error(msg, title='scrapePlayerInfo()')
                                        else:
                                            logger.error(msg)
                                        # continue

                                rookie = 1 if '(R)' in text_parts else 0
                                pos = text_parts[i + 1]

                                fantrax_id = ''
                                s = row1.find_element(By.CLASS_NAME, 'scorer__image').get_attribute('style')
                                match = re.search(r'hs(.*?)_', s)
                                if match:
                                    fantrax_id = match.group(1)

                                # get player id
                                # kwargs = get_player_id_from_name(name=name, team_id=team.id, pos=pos)
                                player_id = get_player_id(team_ids, player_ids, nhl_api, name, nhl_team, pos, fantrax_id)

                                kwargs = {'id': player_id}
                                player = Player().fetch(**kwargs)
                                if player.id == 0 and player_id != 0:
                                    player_json = requests.get(f'{NHL_API_URL}/player/{player_id}/landing').json()
                                    player.id = player_id
                                    player.fantrax_id = fantrax_id
                                    player.first_name = player_json['firstName']['default']
                                    player.last_name = player_json['lastName']['default']
                                    player.full_name = f'{player.first_name} {player.full_name}'
                                    player.birth_date = player_json['birthDate']
                                    player.height = inches_to_feet(player_json.get('heightInInches')) if 'heightInInches' in player_json else ''
                                    player.weight = player_json['weightInPounds']
                                    player.active = player_json['isActive']
                                    player.roster_status = 'Y' if 'currentTeamId' in player_json else 'N'
                                    player.current_team_id = player_json['currentTeamId'] if 'currentTeamId' in player_json else 0
                                    player.current_team_abbr = player_json['currentTeamAbbrev'] if 'currentTeamAbbrev' in player_json else ''
                                    position_code = player_json['position']
                                    player.primary_position = 'LW' if position_code == 'L' else ('RW' if position_code == 'R' else position_code)
                                    player.games = player_json['careerTotals']['regularSeason']['gamesPlayed'] if 'careerTotals' in player_json else 0

                                    if player.persist() is False:
                                        msg = f'Pesist failed for player "{name}"'
                                        if dialog:
                                            sg.popup_error(msg, title='scrapePlayerInfo()')
                                        else:
                                            logger.error(msg)

                                    else:
                                        with get_db_connection() as connection:
                                            sql = dedent(f'''\
                                            insert into TeamRosters
                                                (seasonID, player_id, team_abbr, name, pos)
                                                values ({self.season.id}, {player.id}, "{player.current_team_abbr}", "{player.full_name}", "{player.primary_position}")
                                            ''')
                                            connection.execute(sql)
                                            connection.commit()
                                else:
                                    # I would usually persist the player, but trying something new.
                                    # persist only the new data to change
                                    if player.fantrax_id == '' and fantrax_id != '':
                                        with get_db_connection() as connection:
                                            sql = f'UPDATE Player SET fantrax_id = "{fantrax_id}" WHERE id == {player.id}'
                                            connection.execute(sql)
                                            connection.commit()

                                # don't add to players if already in list
                                if any(p.get('player_id') == player.id for p in players):
                                    continue

                                minors = row1.find_elements(By.CLASS_NAME, 'scorer-icon--MINORS')
                                if len(minors) == 1:
                                    minors = True
                                else:
                                    minors = False

                            except NoSuchElementException:
                                # some rows are empty
                                continue

                            try:
                                player_actions = row2.find_elements(By.TAG_NAME, 'button')
                                # if watchlist_star.get_attribute('title') == 'Trade':
                                #     watchlist_star = rows2.find_element(By.XPATH, f'/html/body/app-root/div/div[1]/div[1]/div/app-league-players/div/section/ultimate-table/div/section/div/table/tr[{idx+1}]/td/player-actions/div/button[2]')
                            except NoSuchElementException:
                                # some rows may be empty
                                continue

                            try:
                                next_opp = row2.find_element(By.CLASS_NAME, 'cell--small').text
                                if next_opp:
                                    next_opp = next_opp.split()[0]
                            except NoSuchElementException:
                                # next opponent is only for games scheduled for today
                                next_opp = ''

                            # leaving this here in case I want to get other player info e.g., RkOv
                            # could also use to get Score or Ppp
                            # # get average draft position
                            # try:
                            #     adp = rows2[idx].text.split(' ')[6]
                            # except NoSuchElementException:
                            #     adp = ''

                            players.append(
                                {
                                    'player_id':  0 if player.id == 0 else player.id,
                                    'fantrax_id': fantrax_id,
                                    'player_name': name if player.id == 0 else player.full_name,
                                    'nhl_team': nhl_team,
                                    'pos': pos,
                                    'minors': minors,
                                    'rookie': rookie,
                                    'watch_list': 1 if 'Remove from Watch List' in [player_action.get_attribute('title') for player_action in player_actions] else 0,
                                    'score': float(score),
                                    'next_opp': next_opp,
                                }
                            )

                            # idx += 1

                    except Exception as e:
                        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                        if dialog:
                            dialog.close()
                            sg.popup_error(msg)
                        else:
                            logger.error(msg)
                        return dfPlayers

            if len(players) > 0:
                dfPlayers = pd.DataFrame.from_dict(data=players)
                # drop rows without valid player_id
                dfPlayers = dfPlayers[dfPlayers.player_id != 0]

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            if dialog:
                dialog.close()
                sg.popup_error(msg)
            else:
                logger.error(msg)

        return dfPlayers

    def scrapePoolTeamPeriodRosters(self, season_id, pool_teams: List=[], dialog: sg.Window=None):

        try:

            logger = logging.getLogger(__name__)

            with get_db_connection() as connection:
                league_id = connection.cursor().execute(f'select league_id from HockeyPool hp where id={self.pool_id}').fetchone()['league_id']

            # Dataframe for pool team roster entry
            dfPoolTeamPeriodRoster = pd.DataFrame(columns=['season', 'pool_team', 'period', 'date', 'illegal_period', 'player_name', 'fantrax_id', 'nhl_team', 'pos', 'status', 'gp', 'pt_d', 'g', 'a', 'pim', 'sog', 'ppp', 'hit', 'blk', 'tk', 'w', 'gaa', 'sv', 'sv_pc', 'g_toi_sec', 'ga', 'sa'])

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            # Get pool teams
            kwargs = {'Criteria': [['pool_id', '==', self.pool_id]], 'Sort': [['name', 'asc']]}
            teams = PoolTeam().fetch_many(**kwargs)
            if pool_teams:
                teams = [team for team in teams if team.name in pool_teams]

            # Iterate through pool teams to extract roster players
            if not dialog:
                logger.debug('Iterating through pool teams to extract roster players by periods')

            season = Season().getSeason(id=season_id)

            # Map month names to their numeric values
            month_mapping = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }

            for team in teams:

                seasonID, period, date, illegal_period, poolTeam, name, id, nhl_team, pos, status, gp, pt_d, g, a, pim, sog, ppp, hit, blk, tk, g_toi_sec, w, sv, gaa, sv_pc, ga, sa = ([] for _ in range(27))

                period_number = 1

                with Browser(self.browser_download_dir) as browser:

                    # Set default wait time
                    wait = WebDriverWait(browser, 60)

                    while True:

                        # Uncomment the following when testing
                        if period_number == 2:
                            period_number = 192

                        for position in ('Skaters', 'Goalies'):

                            scoringCategoryType = 5 if position == 'Skaters' else 1 # position == 'Goalies'

                            url = f'https://www.fantrax.com/fantasy/league/{league_id}/team/roster;teamId={team.fantrax_id};scoringCategoryType={scoringCategoryType};timeframeTypeCode=BY_PERIOD;period={period_number}'

                            for attempt in range(3):
                                try:
                                    browser.get(url)
                                    break
                                except TimeoutException as e:
                                    if attempt == 2:
                                        msg = f'Unable to get period "{period_number}" url after 3 attempts.'
                                        if dialog:
                                            dialog['-PROG-'].update(msg)
                                            event, values = dialog.read(timeout=10)
                                        else:
                                            logger.debug(msg)
                                        return dfPoolTeamPeriodRoster

                                    # Respectful scraping: sleep to avoid hitting the server with too many requests
                                    time.sleep(10)
                                    continue

                            if position == 'Skaters':

                                # get alert section
                                alert_section = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'content__main')))

                                # get period date
                                period_and_date = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="mat-select-value-5"]/span/span')))
                                formatted_date = get_date_info(period_and_date, period_number, season_id, month_mapping)

                                # break if date is today
                                if formatted_date is not None:
                                    today = datetime.today().date()
                                    formatted_date_obj = datetime.strptime(formatted_date, '%Y-%m-%d').date()
                                if formatted_date is None or formatted_date_obj == today:
                                    period_number = 0
                                    break

                                # get alerts
                                illegal_roster_alert = check_for_alerts(alert_section)

                            # Get tables for skaters & goalies
                            msg = f'Getting period {period_number} {position} roster for "{team.name}"'
                            if dialog:
                                dialog['-PROG-'].update(msg)
                                event, values = dialog.read(timeout=10)
                                if event == 'Cancel' or event == sg.WIN_CLOSED:
                                    return dfPoolTeamPeriodRoster
                            else:
                                logger.debug(msg)

                            # Check if the file exists and delete it before downloading
                            filename = os.path.basename('Fantrax-Team-Roster-Vikings Fantasy Hockey League.csv')
                            file_path = os.path.join(self.browser_download_dir, filename)
                            if not dialog:
                                logger.debug(f'Checking existence of "{file_path}"...')
                            for attempt in range(3):
                                if os.path.exists(file_path):
                                    if not dialog:
                                        logger.debug(f'Attempt #{attempt} to remove "{filename}" from "{self.browser_download_dir}".')
                                    os.remove(file_path)
                                    if attempt == 2 and os.path.exists(file_path):
                                        msg = f'Unable to delete "{file_path}" after 3 attempts. Terminating'
                                        if dialog:
                                            dialog['-PROG-'].update(msg)
                                            event, values = dialog.read(timeout=10)
                                        else:
                                            logger.debug(msg)
                                        return dfPoolTeamPeriodRoster
                                    time.sleep(1)
                                    continue

                            button = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/app-root/section/app-league-team-roster/section/div[1]/filter-panel/div/div/div[4]/div[2]/button[2]')))
                            button.click()

                            if not dialog:
                                logger.debug(f'Loading "{file_path}" into dataframe...')

                            skip_rows = get_skip_rows(file_path, position)
                            if len(skip_rows) == 0:
                                msg = f'Problem reading {position} csv fle for "{team.name}" in period {period_number}.'
                                if dialog:
                                    dialog['-PROG-'].update(msg)
                                    event, values = dialog.read(timeout=10)
                                else:
                                    logger.debug(msg)
                                return dfPoolTeamPeriodRoster

                            df = pd.read_csv(file_path, skiprows=skip_rows)

                            if position == 'Skaters':
                                df = df[df['Pos'].isin(['F', 'D', 'Skt'])]
                            else: # position == 'Goalies
                                df = df[df['Pos'] == 'G']
                                # Convert time strings to timedeltas
                                df['Min'] = pd.to_timedelta("00:" + df['Min'])
                                # Extract total seconds
                                df['Min'] = df['Min'].dt.total_seconds()
                                # Replace NaN with 0
                                df['Min'].fillna(0, inplace=True)

                            # Extend the lists with the new data
                            seasonID.extend([season_id] * len(df))
                            poolTeam.extend([team.name] * len(df))
                            period.extend([period_number] * len(df))
                            date.extend([formatted_date] * len(df))
                            illegal_period.extend([illegal_roster_alert] * len(df))
                            name.extend(df['Player'].tolist())
                            id.extend(df['ID'].tolist())
                            nhl_team.extend(df['Team'].tolist())
                            pos.extend(df['Pos'].tolist())
                            status.extend(df['Status'].tolist())
                            gp.extend(df['GP'].tolist())

                            # Use vectorized operations for complex operations
                            pt_d.extend(df['Pt-D'] if position == 'Skaters' else [''] * len(df))
                            g.extend(df['G'] if position == 'Skaters' else [''] * len(df))
                            a.extend(df['A'] if position == 'Skaters' else [''] * len(df))
                            pim.extend(df['PIM'] if position == 'Skaters' else [''] * len(df))
                            sog.extend(df['SOG'] if position == 'Skaters' else [''] * len(df))
                            ppp.extend(df['PPP'] if position == 'Skaters' else [''] * len(df))
                            hit.extend(df['Hit'] if position == 'Skaters' else [''] * len(df))
                            blk.extend(df['Blk'] if position == 'Skaters' else [''] * len(df))
                            tk.extend(df['Tk'] if position == 'Skaters' else [''] * len(df))
                            g_toi_sec.extend(df['Min'] if position == 'Goalies' else [''] * len(df))
                            w.extend(df['W'] if position == 'Goalies' else [''] * len(df))
                            sv.extend(df['SV'] if position == 'Goalies' else [''] * len(df))
                            gaa.extend(df['GAA'] if position == 'Goalies' else [''] * len(df))
                            sv_pc.extend(df['SV%'] if position == 'Goalies' else [''] * len(df))
                            ga.extend(df['GA'] if position == 'Goalies' else [''] * len(df))
                            sa.extend(df['SA'] if position == 'Goalies' else [''] * len(df))

                        if period_number == 0:
                            break

                        period_number += 1

                df_temp = pd.DataFrame(data = {'season': seasonID, 'pool_team': poolTeam, 'period': period, 'date':date, 'illegal_period': illegal_period, 'player_name': name, 'fantrax_id': id, 'nhl_team': nhl_team, 'pos': pos, 'status': status, 'gp': gp, 'pt_d': pt_d, 'g': g, 'a': a, 'pim': pim, 'sog': sog, 'ppp': ppp, 'hit': hit, 'blk': blk, 'tk': tk, 'w': w, 'gaa': gaa, 'sv': sv, 'sv_pc': sv_pc, 'g_toi_sec': g_toi_sec, 'ga': ga, 'sa': sa})
                dfPoolTeamPeriodRoster = pd.concat([dfPoolTeamPeriodRoster, df_temp])

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            if dialog:
                dialog.close()
                sg.popup_error(msg)
            else:
                logger.error(msg)

        return dfPoolTeamPeriodRoster

    def scrapePoolTeamRosters(self, pool_teams: List=[], dialog: sg.Window=None):

        try:

            logger = logging.getLogger(__name__)

            with get_db_connection() as connection:
                league_id = connection.cursor().execute(f'select * from HockeyPool hp where id={self.pool_id}').fetchone()['league_id']

            # Dataframe for pool team roster entry
            dfPoolTeamPlayers = pd.DataFrame(columns=['pool_team', 'nhl_team', 'player_name', 'rookie', 'status', 'fantrax_id'])

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            with Browser() as browser:

                # Set default wait time
                wait = WebDriverWait(browser, 60)

                # Get pool teams
                kwargs = {'Criteria': [['pool_id', '==', self.pool_id]], 'Sort': [['name', 'asc']]}
                teams = PoolTeam().fetch_many(**kwargs)
                if pool_teams:
                    teams = [team for team in teams if team.name in pool_teams]

                # Iterate through pool teams to extract roster players
                if not dialog:
                    logger.debug('Iterating through pool teams to extract roster players')

                status = []
                name = []
                pos = []
                rookie = []
                nhl_team = []
                pool_team = []
                fantrax_id = []
                for team in teams:

                    if team.name.startswith('Open Team'):
                        continue

                    # The first pool team's roster will display (e.g. )
                    url = f'https://www.fantrax.com/fantasy/league/{league_id}/team/roster;teamId={team.fantrax_id}'

                    msg = f'Getting "{team.name}" page "{url}"'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return
                    else:
                        logger.debug(msg)

                    try_count = 1
                    while True:
                        try:
                            browser.get(url)
                            break
                        except TimeoutException as e:
                            pass
                        if try_count < 3:
                            try_count += 1
                            continue
                        else:
                            msg = f'Unable to get url "{url}" on 3 attempts.'
                            if dialog:
                                dialog['-PROG-'].update(msg)
                                event, values = dialog.read(timeout=10)
                                if event == 'Cancel' or event == sg.WIN_CLOSED:
                                    return
                            else:
                                logger.debug(msg)
                            return

                    # Get table for skaters & goalies
                    msg = f'Getting skaters & goalies tables for "{team.name}"'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return
                    else:
                        logger.debug(msg)

                    tables = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, '_ut__aside')))

                    for idx, table in enumerate(tables):

                        position = 'skaters'
                        if idx == 1:
                            position = 'goalies'
                        msg = f'Getting {position} for "{team.name}"'
                        if dialog:
                            dialog['-PROG-'].update(msg)
                            event, values = dialog.read(timeout=10)
                            if event == 'Cancel' or event == sg.WIN_CLOSED:
                                return
                        else:
                            logger.debug(msg)

                        players = table.find_elements(By.TAG_NAME, 'td')
                        for player in players:

                            # some rows are not specific to a player
                            try:
                                player_name = player.find_element(By.TAG_NAME, 'a').text
                            except Exception as e:
                                continue

                            pool_team.append(team.name)
                            name.append(player_name)

                            text_parts = player.text.splitlines()
                            player_pos = text_parts[2]
                            nhlteam = text_parts[-1].strip().lstrip('-').lstrip('(').rstrip(')').strip()
                            if '/' in nhlteam and nhlteam != 'N/A':
                                nhlteam = nhlteam.split('/')[-1]
                            nhl_team.append(nhlteam)
                            pos.append(player_pos)
                            rookie.append(1 if '(R)' in text_parts else 0)
                            status.append(text_parts[0])

                            id = ''
                            s = player.find_element(By.CLASS_NAME, 'scorer__image').get_attribute('style')
                            match = re.search(r'hs(.*?)_', s)
                            if match:
                                id = match.group(1)
                            fantrax_id.append(id)

            dfPoolTeamPlayers = pd.DataFrame(data = {'pool_team': pool_team, 'player_name': name, 'pos': pos, 'nhl_team': nhl_team, 'rookie': rookie, 'status': status, 'fantrax_id': fantrax_id})

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            if dialog:
                dialog.close()
                sg.popup_error(msg)
                raise e
            else:
                logger.error(msg)
                raise e

        return dfPoolTeamPlayers

    def scrapePoolTeams(self, pool_team: str=None, dialog: sg.Window=None) -> pd.DataFrame:

        try:

            dfPoolTeams = pd.DataFrame()

            logger = logging.getLogger(__name__)

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            with Browser() as browser:

                # Set default wait time
                wait = WebDriverWait(browser, 60)

                if not dialog:
                    logger.debug(f'Getting "{self.homePage}"')

                browser.get(self.homePage)

                table = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/app-root/section/app-league-home/section/div[2]/div[1]/league-home-standings/pane/section/div[2]/div/league-home-standings-content/table')))

                msg = 'Scraping pool team names...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=10)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                try:

                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    teams = []
                    for row in rows[1:]: # Skip the first header row
                        # row.text = '1\nOne Man Gang Bang\n131.5'
                        team, points = map(unidecode, row.text.splitlines()[1:])

                        # get pool team manager's Fantrax id
                        fantrax_id = row.find_element(By.TAG_NAME, 'a').get_attribute('href').split(';teamId=')[1]

                        teams.append({'name': team, 'points': points, 'fantrax_id': fantrax_id})

                except Exception as e:
                    msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                    if dialog:
                        dialog.close()
                        sg.popup_error(msg)
                    else:
                        logger.error(msg)
                    return

                # iterate through pool teams & get games played by position
                for team in teams:
                    url = self.manager_position_games_played.replace('{team_id}', team['fantrax_id'])

                    if not dialog:
                            logger.debug(f'Getting games played by position for {team["name"]}')

                    browser.get(url)

                    table = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/app-root/section/app-league-team-roster/section/div[2]/div[2]')))

                    msg = 'Scraping pool team games played per position...'
                    if dialog:
                        dialog['-PROG-'].update(msg)
                        event, values = dialog.read(timeout=10)
                        if event == 'Cancel' or event == sg.WIN_CLOSED:
                            return
                    else:
                        logger.debug(msg)

                    try:
                        rows = table.find_elements(By.CLASS_NAME, 'supertable__row')
                        for row in rows:
                            # row.text = 'Forward (F) 103 855(+117) 635 No min 738'
                            # row.text = 'Games Started - Goalies (GS) 0 0 82 No max'
                            position, pos_abbr, games_played, _, _, _, _, maximum = map(unidecode, row.text.split())
                            pos_abbr = pos_abbr.lstrip('(').rstrip(')')

                            # team[f'{pos_abbr}_position'] = position
                            team[f'{pos_abbr}_games_played'] = games_played
                            team[f'{pos_abbr}_maximum_games'] = maximum
                            if position == 'Goalie':
                                table2 = browser.find_element(By.XPATH, '/html/body/app-root/section/app-league-team-roster/section/div[3]/div[2]')
                                min_games_cell = table2.find_elements(By.CLASS_NAME, 'supertable__cell')[4]
                                # 'Games Started - Goalies (GS) 22 183 82 No max'
                                team[f'{pos_abbr}_minimum_starts'] = unidecode(min_games_cell.text)

                    except Exception as e:
                        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                        if dialog:
                            dialog.close()
                            sg.popup_error(msg)
                        else:
                            logger.error(msg)
                        return

            # save to dataframe & return
            dfPoolTeams = pd.DataFrame.from_dict(data=teams)

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            if dialog:
                dialog.close()
                sg.popup_error(msg)
            else:
                logger.error(msg)

        return dfPoolTeams

    def updatePoolTeamRosters(self, pool, df, pool_teams: List=[], batch: bool=False):

        if batch:
            logger = logging.getLogger(__name__)

        if batch:
            logger.debug('Get current rosters, and remove players not in new rosters')

        # # add player ids to pool team rosters scraped from Fantrax
        # for idx, roster_player in df.iterrows():
        #     # get team_id from team_abbr
        #     team_id = Team().get_team_id_from_team_abbr(team_abbr=roster_player['nhl_team'], suppress_error=True)
        #     kwargs = get_player_id_from_name(name=roster_player['player_name'], team_id=team_id)
        #     player = Player().fetch(**kwargs)
        #     df.loc[idx, 'player_id'] = player.id

        # add player_id
        df['player_id'] = assign_player_ids(df=df, player_name='player_name', nhl_team='nhl_team', pos_code='pos', fantrax_id='fantrax_id')

        # Get current rosters, and remove players not in new rosters
        kwargs = {'Criteria': [['pool_id', '==', pool.id]]}
        teams = PoolTeam().fetch_many(**kwargs)
        for poolie in teams:
            if len(pool_teams) != 0 and poolie.name not in pool_teams:
                continue
            kwargs = {'Criteria': [['poolteam_id', '==', poolie.id]]}
            roster = PoolTeamRoster().fetch_many(**kwargs)
            for roster_player in roster:
                # get player
                kwargs = {'id': roster_player.player_id}
                player = Player().fetch(**kwargs)
                # dfTemp = df.query('pool_team==@poolie.name and player_name.str.lower()==@player.full_name.lower()')
                # if len(dfTemp) == 0:
                if len(df.query('pool_team==@poolie.name and player_id==@player.id')) == 0:
                    kwargs = {'poolteam_id': poolie.id, 'player_id': roster_player.player_id}
                    if roster_player.destroy(**kwargs) is False:
                        msg = f'Delete failed for pool team "{poolie.name}" roster player "{roster_player.player_id}"'
                        if batch:
                            logger.error(msg)
                        else:
                            sg.popup_error(msg, title='updatePoolTeamRosters()')


        if batch:
            logger.debug('Insert/update rosters in database')
        # Insert/update rosters
        for idx in df.index:

            try:

                poolie = df.loc[idx, 'pool_team']
                nhl_team = df.loc[idx, 'nhl_team']
                player_name = df.loc[idx, 'player_name']
                player_id = df.loc[idx, 'player_id']
                # headshot_url = df.loc[idx, 'headshot_url']
                status = df.loc[idx, 'status']
                rookie = df.loc[idx, 'rookie']
                fantrax_id = df.loc[idx, 'fantrax_id']

                # get pool team
                kwargs = {'Criteria': [['pool_id', '==', self.pool_id], ['name', '==', unidecode(poolie)]]}
                pool_team = PoolTeam().fetch(**kwargs)
                if pool_team.id == 0:
                    msg = f'Pool team "{poolie}"not found.'
                    if batch:
                        logger.error(msg)
                    else:
                        sg.popup_error(msg, title='updatePoolTeamRosters()')
                    continue

                # get nhl team
                kwargs = {'Criteria': [['abbr', '==', nhl_team]]}
                team = Team().fetch(**kwargs)
                if team.id == 0 and nhl_team != 'N/A':
                    msg = f'NHL team "{nhl_team}" not found for "{player_name}" in "{poolie}" pool team.'
                    if batch:
                        logger.error(msg)
                    else:
                        sg.popup_error(msg, title='updatePoolTeamRosters()')
                    # continue

                # # get player id
                # kwargs = get_player_id_from_name(name=player_name, team_id=team.id)
                # Add new NHL Player if it wasn't set earlier. Not even sure that this is possible!!!
                kwargs = {'id': player_id}
                player = Player().fetch(**kwargs)
                if player.id == 0 and player_id != 0:
                    player_json = requests.get(f'{NHL_API_URL}/player/{player_id}/landing').json()
                    player.id = player_id
                    player.fantrax_id = fantrax_id
                    player.first_name = player_json['firstName']['default']
                    player.last_name = player_json['lastName']['default']
                    player.full_name = f'{player.first_name} {player.full_name}'
                    player.birth_date = player_json['birthDate']
                    player.height = inches_to_feet(player_json.get('heightInInches')) if 'heightInInches' in player_json else ''
                    player.weight = player_json['weightInPounds']
                    player.active = player_json['isActive']
                    player.roster_status = 'Y' if 'currentTeamId' in player_json else 'N'
                    player.current_team_id = player_json['currentTeamId']
                    player.current_team_abbr = player_json['currentTeamAbbrev']
                    position_code = player_json['position']
                    player.primary_position = 'LW' if position_code == 'L' else ('RW' if position_code == 'R' else position_code)
                    player.games = player_json['careerTotals']['regularSeason']['gamesPlayed'] if 'careerTotals' in player_json else 0

                    if player.persist() is False:
                        msg = 'Pesist failed for player "{1}"'.format(df.loc[idx, 'player_name'])
                        if batch:
                            logger.error(msg)
                        else:
                            sg.popup_error(msg, title='updatePoolTeamRosters()')
                    else:
                        with get_db_connection() as connection:
                            sql = dedent(f'''\
                            insert into TeamRosters
                                (seasonID, player_id, team_abbr, name, pos)
                                values ({pool.season_id}, {player.id}, "{team.abbr}", "{player.full_name}", "{player.primary_position}")
                            ''')
                            connection.execute(sql)
                            connection.commit()
                # else:
                #     # I would usually persist the player, but trying something new.
                #     # persist only the new data to change
                #     if player.fantrax_id == '' and fantrax_id != '':
                #         with get_db_connection() as connection:
                #             sql = f'UPDATE Player SET fantrax_id = "{fantrax_id}") WHERE id == {player.id}'
                #             connection.execute(sql)
                #             connection.commit()

                kwargs = {'poolteam_id': pool_team.id, 'player_id': player_id}
                roster_player = PoolTeamRoster().fetch(**kwargs)
                roster_player.poolteam_id = pool_team.id
                roster_player.player_id = player.id
                roster_player.status = status

                if roster_player.persist() == False:
                    msg = 'Pesist failed for pool team "{0}" roster player "{1}"'.format(df.loc[idx, 'pool_team'], df.loc[idx, 'player_name'])
                    if batch:
                        logger.error(msg)
                    else:
                        sg.popup_error(msg, title='updatePoolTeamRosters()')

            except Exception as e:
                msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                if not batch:
                    sg.popup_error(msg)
                else:
                    logger.error(msg)
                return

        return

    def updatePoolTeams(self, pool, df, batch: bool=False):

        if batch:
            logger = logging.getLogger(__name__)

        if batch:
            logger.debug('Get pool teams...')

        if batch:
            logger.debug('Insert/update pool teams in database')

        # Insert/update pool teams
        for idx in df.index:

            try:

                poolie = df.loc[idx, 'name']

                # get pool team
                kwargs = {'Criteria': [['pool_id', '==', self.pool_id], ['name', '==', unidecode(poolie)]]}
                pool_team = PoolTeam().fetch(**kwargs)
                if pool_team.id == 0:
                    pool_team.pool_id = pool.id
                    pool_team.name = poolie

                pool_team.points = df.loc[idx, 'points']
                pool_team.fantrax_id = df.loc[idx, 'fantrax_id']
                pool_team.F_games_played = df.loc[idx, 'F_games_played']
                pool_team.F_maximum_games = df.loc[idx, 'F_maximum_games']
                pool_team.D_games_played = df.loc[idx, 'D_games_played']
                pool_team.D_maximum_games = df.loc[idx, 'D_maximum_games']
                pool_team.Skt_games_played = df.loc[idx, 'Skt_games_played']
                pool_team.Skt_maximum_games = df.loc[idx, 'Skt_maximum_games']
                pool_team.G_games_played = df.loc[idx, 'G_games_played']
                pool_team.G_maximum_games = df.loc[idx, 'G_maximum_games']
                pool_team.G_minimum_starts = df.loc[idx, 'G_minimum_starts']
                if pool_team.persist() == False:
                    msg = 'Pesist failed for pool team "{0}"'.format(df.loc[idx, 'name'])
                    if batch:
                        logger.error(msg)
                    else:
                        sg.popup_error(msg, title='updatePoolTeams()')

            except Exception as e:
                msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                if not batch:
                    sg.popup_error(msg)
                else:
                    logger.error(msg)
                return

        return

def get_skip_rows(file_path, position):
    skaters_start_line = goalies_start_line = None
    totals_lines = []
    skip_rows = []

    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if skaters_start_line is None and '"","Skaters"' in line:
                skaters_start_line = line_number - 1
            if goalies_start_line is None and '"","Goalies"' in line:
                goalies_start_line = line_number - 1
            if line.startswith('"","Totals"'):
                totals_lines.append(line_number - 1)

            if skaters_start_line is not None and goalies_start_line is not None and len(totals_lines) == 2:
                break

    if skaters_start_line is None or goalies_start_line is None or len(totals_lines) == 0:
        return skip_rows

    if position == 'Skaters':
        skip_rows.extend([skaters_start_line, totals_lines[0]])
        skip_rows.extend(range(goalies_start_line, totals_lines[1]))
        skip_rows.append(totals_lines[1])
    else: # position == 'Goalies
        skip_rows.extend(range(skaters_start_line, totals_lines[0]))
        skip_rows.extend([totals_lines[0], goalies_start_line, totals_lines[1]])

    return skip_rows

def get_date_info(period_and_date, period_number, season_id, month_mapping):
    # Extract the month and day from the period
    roster_period, _, month, day = period_and_date.text.split()
    if period_number > int(roster_period):
        return None
    month = month.lower()  # Convert month to lowercase for consistency
    day = day.replace(')', '') # Remove trailing bracket
    # Get the numeric month value
    numeric_month = month_mapping.get(month, None)
    if numeric_month >= 10:
        year = season_id // 10000
    else:
        year = season_id % 10000
    # Construct the date in 'YYYY-MM-DD' format
    formatted_date = f"{year}-{numeric_month:02d}-{day}"
    return formatted_date

def check_for_alerts(alert_section):
    illegal_roster_alert = False
    alerts = alert_section.find_elements(By.TAG_NAME, 'alert')
    for alert in alerts:
        if 'lineup period is illegal' in alert.text:
            illegal_roster_alert = True
            break
    return illegal_roster_alert
