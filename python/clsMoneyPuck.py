import glob
import logging
import os
import requests
import sys
import time
import traceback
from typing import  List

import pandas as pd
import PySimpleGUI as sg
import sqlite3
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Hockey Pool classes
from clsBrowser import Browser
from clsSeason import Season
from utils import get_db_connection, unzip_file


class MoneyPuck:

    def __init__(self, season: Season):

        self.homePage = 'https://moneypuck.com/index.html'
        self.dataPage = 'https://moneypuck.com/data.htm'
        self.season = season
        # self.browser_download_dir = os.path.abspath(f'./python/input/moneyPuck/{season.id}')
        self.browser_download_dir = os.path.abspath(f'./input/moneyPuck/{season.id}')

        return

    def downloadData(self, season: Season, dialog: sg.Window=None, batch: bool=False):

        try:

            logger = logging.getLogger(__name__)

            msg = 'Waiting for web driver...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            with Browser(self.browser_download_dir) as browser:

                # Set default wait time
                wait = WebDriverWait(browser, 60)

                msg = f'Getting {self.dataPage}...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                attempts = 0
                while attempts < 3:
                    try:
                        # query the website
                        browser.get(self.dataPage)
                        # If the page loads successfully, the loop will break
                        break
                    except TimeoutException:
                        attempts += 1
                        if attempts >= 3:
                            msg = f"Timeout occurred for {self.dataPage} on the 3rd attempt. Returning without getting MoneyPuck data."
                            if dialog:
                                dialog['-PROG-'].update(msg)
                                event, values = dialog.read(timeout=2)
                                if event == 'Cancel' or event == sg.WIN_CLOSED:
                                    return
                            else:
                                logger.error(msg)
                            return
                        else:
                            if batch is True:
                                logger.debug(f"Timeout occurred for {self.dataPage}. Retrying...")

                        # Respectful scraping: sleep to avoid hitting the server with too many requests
                        time.sleep(10)

                msg = 'Getting data links...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                # skaters_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/table/tbody/tr[18]/td[2]/a')))
                # goalies_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/table/tbody/tr[18]/td[3]/a')))
                # lines_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/table/tbody/tr[18]/td[4]/a')))
                all_teams_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/h3[4]/a')))
                all_players_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/h3[7]/a')))
                shots_2024_link = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="page-content-wrapper"]/div[1]/h3[8]/div/a[20]')))

                msg = 'Downloading data...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)

                try:

                    # List of all links
                    # links = [skaters_link, goalies_link, lines_link, all_players_link, all_teams_link, shots_2024_link]
                    links = [all_players_link, all_teams_link, shots_2024_link]

                    # List to store all file paths
                    file_paths = []

                    shots_zip_file_path = ''
                    for link in links:

                        href = link.get_attribute('href')
                        if batch:
                            logger.debug(f'Scrolling "{href}" into view...')
                        # Scroll the element into view
                        browser.execute_script("arguments[0].scrollIntoView();", link)

                        # Check if the file exists and delete it before downloading
                        filename = os.path.basename(href)
                        file_path = os.path.join(self.browser_download_dir, filename)
                        if batch:
                            logger.debug(f'Checking existence of "{file_path}"...')
                        if filename.endswith('.zip'):
                            shots_zip_file_path = file_path
                        file_paths.append(file_path)
                        if os.path.exists(file_path):
                            if batch:
                                logger.debug(f'Removing "{filename}" from "{self.browser_download_dir}"...')
                            os.remove(file_path)

                        # Use JavaScript to click the element
                        if batch:
                            logger.debug(f'Clinking "{href}" to start download...')
                        browser.execute_script("arguments[0].click();", link)
                        if batch:
                            logger.debug(f'Download starting for "{href}"...')
                        # Add a delay to allow the download to start
                        time.sleep(1)

                    # Wait for all downloads to complete
                    if batch:
                        logger.debug('Waiting for all downloads to complete...')
                    for file_path in file_paths:
                        # Add a delay before checking if the file is still being downloaded
                        time.sleep(1)
                        while glob.glob(file_path.rsplit('.', 1)[0] + '*.part') or glob.glob(file_path.rsplit('.', 1)[0] + '*.download'):
                            time.sleep(1)

                except Exception as e:
                    if dialog:
                        sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')
                    else:
                        logger.error(repr(e))
                    return

            msg = 'Data download completed...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            if batch:
                logger.debug(f'Unzipping "{shots_zip_file_path}"...')
            # unzip shots file
            unzip_file(shots_zip_file_path)

            msg = 'Updating shots data...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            prefix = os.path.basename(self.browser_download_dir)[:4] + '0'
            if batch:
                logger.debug(f'Loading "{shots_zip_file_path}" into dataframe...')
            df = pd.read_csv(shots_zip_file_path)
            df['game_id'] = prefix + df['game_id'].astype(str)
            df['season'] = season.id
            df['playerPositionThatDidEvent'] = df['playerPositionThatDidEvent'].apply(lambda x: 'LW' if x == 'L' else ('RW' if x == 'R' else x))

            if batch:
                logger.debug(f'Aggregating "{shots_zip_file_path}" dataframe for skaters...')
            df_skaters = df.sort_values(['season','game_id']).groupby(['season','game_id','shooterPlayerId'], as_index=False).agg(
                season = ('season', 'first'),
                game_id = ('game_id', 'first'),
                player_id = ('shooterPlayerId', 'first'),
                name = ('shooterName', 'first'),
                pos = ('playerPositionThatDidEvent', 'first'),
                # shotGeneratedRebound = ('shotGeneratedRebound', 'sum'),
                # shotOnEmptyNet = ('shotOnEmptyNet', 'sum'),
                # shotsRebound = ('shotRebound', 'sum'),
                goals = ('goal', 'sum'),
                shotsOnGoal = ('shotWasOnGoal', 'sum'),
                lowDangerShots = ('xGoal', lambda x: (x < 0.08).sum()),
                mediumDangerShots = ('xGoal', lambda x: ((x >= 0.08) & (x < 0.2)).sum()),
                highDangerShots = ('xGoal', lambda x: (x >= 0.2).sum()),
                lowDangerShotsOnGoal = ('xGoal', lambda x: ((df.loc[x.index]['shotWasOnGoal'] == 1) & (x < 0.08)).sum()),
                mediumDangerShotsOnGoal = ('xGoal', lambda x: ((df.loc[x.index]['shotWasOnGoal'] == 1) & (x >= 0.08) & (x < 0.2)).sum()),
                highDangerShotsOnGoal = ('xGoal', lambda x: ((df.loc[x.index]['shotWasOnGoal'] == 1) & (x >= 0.2)).sum()),
                teamAbbr = ('teamCode', 'first'),
                xGoals = ('xGoal', 'sum'),
                xRebounds = ('xRebound', 'sum'),
            )

            # Drop the 'shooterPlayerId' column
            df_skaters = df_skaters.drop('shooterPlayerId', axis=1)
            # Convert the desired columns to integers
            cols_to_convert = ['season', 'game_id', 'player_id', 'goals', 'shotsOnGoal', 'lowDangerShots', 'mediumDangerShots', 'highDangerShots', 'lowDangerShotsOnGoal', 'mediumDangerShotsOnGoal', 'highDangerShotsOnGoal']
            for col in cols_to_convert:
                df_skaters[col] = df_skaters[col].astype(int)

            if batch:
                logger.debug(f'Aggregating "{shots_zip_file_path}" dataframe for goalies...')
            df_goalies = df[df['goalieIdForShot'] != 0].sort_values(['season','game_id']).groupby(['season','game_id','goalieIdForShot'], as_index=False).agg(
                season = ('season', 'first'),
                game_id = ('game_id', 'first'),
                player_id = ('goalieIdForShot', 'first'),
                name = ('goalieNameForShot', 'first'),
                # shotGeneratedRebound = ('shotGeneratedRebound', 'sum'),
                # shotOnEmptyNet = ('shotOnEmptyNet', 'sum'),
                # shotRebound = ('shotRebound', 'sum'),
                goalsAgainst = ('goal', 'sum'),
                shotsOnGoal = ('shotWasOnGoal', 'sum'),
                teamAbbr = ('teamCode', 'first'),
                xGoalsAgainst = ('xGoal', 'sum'),
                xRebounds = ('xRebound', 'sum'),
            )

            # Drop the 'goalieIdForShot' column
            df_goalies = df_goalies.drop('goalieIdForShot', axis=1)
            # Convert the desired columns to integers
            cols_to_convert = ['season', 'game_id', 'player_id', 'goalsAgainst', 'shotsOnGoal']
            for col in cols_to_convert:
                df_goalies[col] = df_goalies[col].astype(int)


            msg = 'Writing data to database...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            # save the shots data to the database
            if batch:
                logger.debug(f'Updating "MoneypuckShots" table...')
            with get_db_connection() as conn:
                table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MoneypuckShots';"
                table_exists = conn.execute(table_check_query).fetchone() is not None
                if table_exists:
                    conn.execute(f"DELETE FROM MoneypuckShots WHERE season = {season.id}")
                df.to_sql('MoneypuckShots', con=conn, if_exists='append', index=False)

            # save the skaters data to the database
            if batch:
                logger.debug(f'Updating "MoneypuckSkaterStats" table...')
            with get_db_connection() as conn:
                table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MoneypuckSkaterStats';"
                table_exists = conn.execute(table_check_query).fetchone() is not None
                if table_exists:
                    conn.execute(f"DELETE FROM MoneypuckSkaterStats WHERE season = {season.id}")
                df_skaters.to_sql('MoneypuckSkaterStats', con=conn, if_exists='append', index=False)

            # save the goalies data to the database
            if batch:
                logger.debug(f'Updating "MoneypuckGoalieStats" table...')
            with get_db_connection() as conn:
                table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MoneypuckGoalieStats';"
                table_exists = conn.execute(table_check_query).fetchone() is not None
                if table_exists:
                    conn.execute(f"DELETE FROM MoneypuckGoalieStats WHERE season = {season.id}")
                df_goalies.to_sql('MoneypuckGoalieStats', con=conn, if_exists='append', index=False)

            # if batch:
            #     logger.debug('Loading "skaters.csv" into dataframe...')
            # df = pd.read_csv(self.browser_download_dir + '\\skaters.csv')
            # df['season'] = season.id
            # # save the skaters data to the database
            # if batch:
            #     logger.debug(f'Updating "MoneypuckSkaters" table...')
            # with get_db_connection() as conn:
            #     table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MoneypuckSkaters';"
            #     table_exists = conn.execute(table_check_query).fetchone() is not None
            #     if table_exists:
            #         conn.execute(f"DELETE FROM MoneypuckSkaters WHERE season = {season.id}")
            #     df.to_sql('MoneypuckSkaters', con=conn, if_exists='append', index=False)

            # if batch:
            #     logger.debug('Loading "goalies.csv" into dataframe...')
            # df = pd.read_csv(self.browser_download_dir + '\\goalies.csv')
            # df['season'] = season.id
            # # save the goalies data to the database
            # if batch:
            #     logger.debug(f'Updating "MoneypuckGoalies" table...')
            # with get_db_connection() as conn:
            #     table_check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MoneypuckGoalies';"
            #     table_exists = conn.execute(table_check_query).fetchone() is not None
            #     if table_exists:
            #         conn.execute(f"DELETE FROM MoneypuckGoalies WHERE season = {season.id}")
            #     df.to_sql('MoneypuckGoalies', con=conn, if_exists='append', index=False)

        except Exception as e:
            if dialog:
                sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')
            else:
                logger.error(repr(e))

        return

    def getShotData(self, dialog: sg.Window=None, batch: bool=False):

        columns = ['event', 'game_id', 'goal', 'goalieIdForShot', 'goalieNameForShot', 'homeTeamCode', 'playerPositionThatDidEvent', 'season', 'shooterPlayerId', 'shooterName', 'teamCode', 'xGoal']

        # Create an empty DataFrame with the same columns
        df = pd.DataFrame(columns=columns)

        try:

            logger = logging.getLogger(__name__)

            msg = 'Getting shot data...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            # Construct the pattern for the shots*.csv file
            pattern = os.path.join(self.browser_download_dir, '20232024', '*2023*.csv')
            # Use glob to find file that matches the pattern
            matching_files = glob.glob(pattern)
            # matching_files is a list of file paths that match the pattern
            if len(matching_files) >= 1:
                filename = matching_files[0] # there should only be 1
            else:
                msg = 'A shots*.csv file was not found...'
                if dialog:
                    dialog['-PROG-'].update(msg)
                    event, values = dialog.read(timeout=2)
                    if event == 'Cancel' or event == sg.WIN_CLOSED:
                        return
                else:
                    logger.debug(msg)
                return df

            file_path = os.path.join(self.browser_download_dir, filename)

            df = pd.read_csv(file_path, usecols=columns)

            msg = 'Shots data loaded into dataframe...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

        except Exception as e:
            if dialog:
                sg.popup_error(f'Error in {sys._getframe().f_code.co_name}: {e}')
            else:
                logger.error(repr(e))

        return df