#import the libraries
import logging
import time
import traceback
from typing  import Dict, List
from datetime import date

import numpy as np
import pandas as pd
import PySimpleGUI as sg
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from clsBrowser import Browser

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
            event, values = dialog.read(timeout=10)
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
                event, values = dialog.read(timeout=10)
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
        daily_faceoff_com = 'https://www.dailyfaceoff.com/teams'

        msg = f'Opening "{daily_faceoff_com}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=10)
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
            wait = WebDriverWait(browser, 60)

            if batch is True:
                logger.debug(f'Getting "{daily_faceoff_com}"')

            attempts = 0
            while attempts < 3:
                try:
                    # query the website
                    browser.get(daily_faceoff_com)
                    # If the page loads successfully, the loop will break
                    break
                except TimeoutException:
                    attempts += 1
                    if batch is True:
                        if attempts >= 3:
                            logger.info(f"Timeout occurred for {daily_faceoff_com} on the 3rd attempt. Returning without getting player lines.")
                            return pd.DataFrame.from_dict([])
                        else:
                            logger.info(f"Timeout occurred for {daily_faceoff_com}. Retrying...")

                    # Respectful scraping: sleep to avoid hitting the server with too many requests
                    time.sleep(10)

            if batch is True:
                logger.debug(f'Returned from "{daily_faceoff_com}"')

            msg = f'Scraping "{daily_faceoff_com}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=10)
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
            'winnipeg-jets': 'WPG'
        }

        with Browser() as browser:

            wait = WebDriverWait(browser, 60)

            players = []
            for url in team_urls:

                attempts = 0
                while attempts < 3:
                    try:
                        browser.get(url)
                        # If the page loads successfully, the loop will break
                        break
                    except TimeoutException:
                        attempts += 1
                        if batch is True:
                            if attempts >= 3:
                                logger.info(f"Timeout occurred for {url} on the 3rd attempt. Returning without getting player lines.")
                                return pd.DataFrame.from_dict([])
                            else:
                                logger.info(f"Timeout occurred for {url}. Retrying...")

                        # Respectful scraping: sleep to avoid hitting the server with too many requests
                        time.sleep(10)

                section = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="line_combos"]')))

                lines = section.text.splitlines()

                sections = ['Forwards', 'Defensive Pairings', '1st Powerplay Unit', '2nd Powerplay Unit']
                player_data = {}
                for section in sections:
                    start_index = lines.index(section)
                    if section == 'Forwards':
                        start_index += 4  # Skip the positions
                        end_index = lines.index('Defensive Pairings')
                        names = [lines[i:i+3] for i in range(start_index, end_index, 3)]
                        for i, line in enumerate(names):
                            for player in line:
                                if player not in player_data:
                                    player_data[player] = {'Line': f'{i+1}'}
                    elif section == 'Defensive Pairings':
                        end_index = lines.index('1st Powerplay Unit')
                        names = [lines[i:i+2] for i in range(start_index+1, end_index, 2)]
                        for i, pair in enumerate(names):
                            for player in pair:
                                if player not in player_data:
                                    player_data[player] = {'Line': f'{i+1}'}
                    elif section == '1st Powerplay Unit':
                        end_index = lines.index('2nd Powerplay Unit')
                        names = lines[start_index+1:end_index]
                        for player in names:
                            if player in player_data:  # Only add if player is in 'Forwards' or 'Defensive Pairings'
                                player_data[player]['PP Unit'] = '1'
                    elif section == '2nd Powerplay Unit':
                        end_index = lines.index('1st Penalty Kill Unit')
                        names = lines[start_index+1:end_index]
                        for player in names:
                            if player in player_data:  # Only add if player is in 'Forwards' or 'Defensive Pairings'
                                player_data[player]['PP Unit'] = '2'

                # 'https://www.dailyfaceoff.com/teams/anaheim-ducks/line-combinations'
                team_name = url.split('/')[-2]
                team_abbr = team_abbrs[team_name]

                for player_name, data in player_data.items():
                    players.append(
                        {
                            'name': player_name,
                            # 'first_name': '',
                            # 'last_name': '',
                            # 'pos': '',
                            # 'rest': np.nan,
                            'team': team_abbr,
                            'line': data['Line'],
                            'pp_line': data['PP Unit'] if 'PP Unit' in data else '',
                        }
                    )

            # Respectful scraping: sleep to avoid hitting the server with too many requests
            time.sleep(10)

    except Exception as e:
        if dialog:
            sg.PopupScrolled(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)), modal=True)
        else:
            logger.error(repr(e))
        return pd.DataFrame.from_dict([])

    return pd.DataFrame.from_dict(players)

if __name__ == "__main__":

    main()

    exit()
