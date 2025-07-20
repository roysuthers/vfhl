#import the libraries
import logging
import requests
import traceback
# from urllib.request import urlopen

import pandas as pd
import PySimpleGUI as sg
import ujson as json
from bs4 import BeautifulSoup
from openpyxl.utils.dataframe import dataframe_to_rows
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unicodedata import normalize
from unidecode import unidecode

from clsBrowser import Browser
from clsNHL_API import NHL_API
from utils import get_db_connection, get_player_id, load_nhl_team_abbr_and_id_dict, load_player_name_and_id_dict
import re


def main(dialog: sg.Window=None):

    # df = from_sports_reference(dialog=dialog)

    df = from_puckpedia(dialog=dialog)

    # df = from_covers(dialog=dialog)

    return df

def from_sports_reference(dialog: sg.Window=None) -> pd.DataFrame:

    try:

        logger = logging.getLogger(__name__)

        #specify the url
        hockey_reference_com = 'https://www.hockey-reference.com/friv/injuries.cgi'

        msg = f'Opening "{hockey_reference_com}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        # query the website and return the html to the variable 'page'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(hockey_reference_com, headers=headers)

        # page = urlopen(hockey_reference_com)
        page = response.content

        # parse the html using beautiful soup and store in variable 'tableData'
        soup = BeautifulSoup(page, "html.parser")

        msg = f'Scraping "{hockey_reference_com}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        table = soup.find(name="table", attrs={"id": "injuries"}).find(name='tbody')

        name = []
        team = []
        date_of_injury = []
        injury_type = []
        injury_note = []

        for row in table.findAll(name="tr"):
            cells = row.find_all(name=['th', "td"])
            if len(cells) == 5:
                name.append(cells[0].text.strip())
                team.append(cells[1].next.get('href').replace('/teams/', '').rstrip('/').strip())
                date_of_injury.append(cells[2].get('csk').strip())
                injury_type.append(cells[3].next.strip())
                injury_note.append(cells[4].next.strip())

        msg = f'Found "{name}" in injury list...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        df = pd.DataFrame(name,columns=["name"])
        df['team'] = team
        df['date'] = date_of_injury
        df['status'] = injury_type
        df['note'] = injury_note

    except Exception as e:
        if dialog:
            sg.PopupScrolled(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)), modal=True)
        else:
            logger.error(repr(e))

    return df

def from_puckpedia(dialog: sg.Window=None) -> pd.DataFrame:

    try:

        # create dictionary to map team names to code
        df_teams = pd.read_sql(f'select name, abbr from Team', con=get_db_connection())
        # df_teams['name'] = df_teams['name'].apply(lambda x: x.lower().replace(' ', '-').replace('.', ''))
        # df_teams['name'] = df_teams['name'].apply(lambda x: unidecode(x))

        # Function to normalize strings
        def normalize_string(input_str):
            return normalize('NFKD', input_str).encode('ascii', 'ignore').decode('utf-8')

        # Apply normalization to the 'name' column
        df_teams['name'] = df_teams['name'].apply(normalize_string)

        nhl_teams = dict(zip(df_teams.name, df_teams.abbr))

        logger = logging.getLogger(__name__)

        #specify the url
        url = 'https://puckpedia.com/injuries'

        msg = f'Opening "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        with Browser() as browser, Browser() as browser2:

            # Set default wait time
            wait = WebDriverWait(browser, 60)

            browser.get(url)

            # Wait for the 'Team' tab to be clickable and then click it
            team_tab = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[@data-tab='Team']")))
            team_tab.click()

            msg = f'Scraping "{url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            name = []
            id = []
            pos = []
            team = []
            timeline = []
            expected_return = []
            injury_type = []
            injury_note = []

            # Get team IDs, player names & id dictionary, and NHL_API
            team_ids = load_nhl_team_abbr_and_id_dict()
            player_ids = load_player_name_and_id_dict()
            nhl_api = NHL_API()

            # Find all rows in the table
            rows = browser.find_elements(By.XPATH, '//*[@id="salary-cap"]/div/div/div[1]/div[2]/div/div[2]/table/tbody/tr')
            for idx, row in enumerate(rows):

                try:
                    html_tag = row.find_element(By.TAG_NAME, 'i')
                except NoSuchElementException:
                    player_team = row.text.strip()
                    continue

                player_name, timeline, status_reason = row.text.splitlines()

                last_name, first_name = player_name.split(', ')
                player_name = f'{first_name} {last_name}'

                html_content = html_tag.get_attribute('data-content')

                soup = BeautifulSoup(html_content, "html.parser")

                # # Extract player name and href
                player_tag = soup.find('a', class_='pp_link')
                # player_name = player_tag.text.strip()

                # get player team
                # if player_team == 'utah-hc':
                #     nhl_team = 'UTA'
                # else:
                #     nhl_team = nhl_teams[player_team]
                nhl_team = nhl_teams[player_team]

                # team_id = team_ids[nhl_team] if nhl_team != 'N/A' else 0
                player_id = get_player_id(team_ids, player_ids, nhl_api, player_name, nhl_team)
                if player_id == 0:
                    player_href = player_tag.get('href')
                    player_page = f'https://puckpedia.com{player_href}'
                    browser2.get(player_page)
                    soup2 = BeautifulSoup(browser2.page_source , "html.parser")
                    player_pos = soup2.find('div', attrs={'class': 'statsrow gap-1 sm:gap-2.5 text-[12px] sm:text-[13px] mt-1.5'}).text.splitlines()[2].strip('pos')
                    player_pos = 'F' if player_pos not in ['D', 'G'] else player_pos
                    player_id = get_player_id(team_ids, player_ids, nhl_api, player_name, nhl_team, player_pos)
                else:
                    player_pos = player_ids[player_name.lower()][0]['pos']

                try:
                    inj_type, inj_short_desc = status_reason.split(' ', 1)
                except ValueError:
                    inj_type, inj_short_desc = soup.find('div', class_='uppercase tracking-widest text-sm').text.strip().split('|', 1)

                # injury description
                inj_desc = soup.find('p', class_='mt-2 mb-2 min-w-[200px]').text.strip()
                if inj_desc == '':
                    inj_desc = inj_short_desc

                # Extract estimated return date
                exp_return = soup.find('div', class_='text-sm font-sans').text.strip()

                name.append(player_name)
                id.append(player_id)
                pos.append(player_pos)
                team.append(nhl_team)
                expected_return.append(exp_return)
                injury_type.append(inj_type)
                injury_note.append(inj_desc)

            df = pd.DataFrame(name,columns=["name"])
            df['id'] = id
            df['pos'] = pos
            df['team'] = team
            df['date'] = expected_return
            df['status'] = injury_type
            df['note'] = injury_note

    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        if dialog:
            sg.PopupScrolled(msg, modal=True)
        else:
            logger.error(msg)
            raise

    return df

def from_covers(dialog: sg.Window=None) -> pd.DataFrame:

    try:

        # create dictionary to map team names to code
        df_teams = pd.read_sql(f'select name, abbr from Team', con=get_db_connection())
        # df_teams['name'] = df_teams['name'].apply(lambda x: x.lower().replace(' ', '-').replace('.', ''))
        # df_teams['name'] = df_teams['name'].apply(lambda x: unidecode(x))

        # Function to normalize strings
        def normalize_string(input_str):
            return normalize('NFKD', input_str).encode('ascii', 'ignore').decode('utf-8')

        # Apply normalization to the 'name' column
        df_teams['name'] = df_teams['name'].apply(normalize_string)

        nhl_teams = dict(zip(df_teams.name, df_teams.abbr))

        logger = logging.getLogger(__name__)

        #specify the url
        url = 'https://www.covers.com/sport/hockey/nhl/injuries'

        msg = f'Opening "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        msg = f'Scraping "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=2)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        name = []
        id = []
        pos = []
        team = []
        date_of_injury = []
        injury_type = []
        injury_note = []

        # Get team IDs, player names & id dictionary, and NHL_API
        team_ids = load_nhl_team_abbr_and_id_dict()
        player_ids = load_player_name_and_id_dict()
        nhl_api = NHL_API()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        injuries_by_team = []

        # Each <section> contains one team's block
        for section in soup.find_all('section'):
            team_block = section.find(
                class_='covers-CoversSeasonInjuries-blockContainer'
            )
            if not team_block:
                continue

            # Extract team name
            team_name_div = team_block.select_one(
                '.covers-CoversMatchups-teamName a'
            )
            if not team_name_div:
                continue

            # Example: <a href="/sport/hockey/nhl/teams/main/columbus-blue-jackets/2023-2024">Columbus Blue Jackets</a>
            team_href = team_name_div.get('href', '')
            player_team = team_href.split('/')[-1].replace('-', ' ').title()

            if player_team == 'utah-hc':
                nhl_team = 'UTA'
            else:
                nhl_team = nhl_teams[player_team]            # Find the table of injuries
            tbl = team_block.select_one(
                '.covers-CoversMatchups-Table'
            )
            if not tbl:
                continue

            # Parse header order to identify columns
            headers = [th.get_text(strip=True).lower() for th in tbl.select('thead th')]

            # Walk through rows in tbody
            rows = tbl.select('tbody > tr')
            team_injuries = []
            i = 0
            while i < len(rows):
                row = rows[i]
                cols = row.find_all('td')
                # skip any row that isn't a data row
                if len(cols) < 3:
                    i += 1
                    continue

                # Extract player name from the 'href' in the 'a' tag
                player_link = cols[0].find('a')
                if player_link and player_link.has_attr('href'):
                    # Example href: /sport/hockey/nhl/players/12345/john-doe
                    href_parts = player_link['href'].strip('/').split('/')
                    if len(href_parts) >= 5:
                        player_name = href_parts[5].replace('-', ' ').title()
                    else:
                        player_name = player_link.get_text(strip=True)
                else:
                    player_name = cols[0].get_text(strip=True)

                player_pos  = cols[1].get_text(strip=True)

                # team_id = team_ids[nhl_team] if nhl_team != 'N/A' else 0
                player_id = get_player_id(team_ids, player_ids, nhl_api, player_name, nhl_team, player_pos)
                if player_id == 0:
                    pass
                #     player_href = player_tag.get('href')
                #     player_page = f'https://puckpedia.com{player_href}'
                #     browser2.get(player_page)
                #     soup2 = BeautifulSoup(browser2.page_source , "html.parser")
                #     player_pos = soup2.find('div', attrs={'class': 'statsrow gap-1 sm:gap-2.5 text-[12px] sm:text-[13px] mt-1.5'}).text.splitlines()[2].strip('pos')
                #     player_id = get_player_id(team_ids, player_ids, nhl_api, player_name, nhl_team, player_pos)
                # else:
                #     player_pos = player_ids[player_name.lower()][0]['pos']

                # status text may include <b> and a date in <br>
                status = ' '.join(cols[2].get_text(separator=' ', strip=True).split())
                type_of_injury_type, injury_date = status.split('(')
                inj_type = type_of_injury_type.strip()
                inj_date = injury_date.strip(')').strip()

                # look ahead for description in the next sibling
                inj_desc = ''
                if i + 1 < len(rows) and 'collapse' in rows[i+1].get('class', []):
                    desc_div = rows[i+1].find('div', class_='covers-CoversMatchups-injuryCopy')
                    if desc_div:
                        inj_desc = desc_div.get_text(strip=True)
                    i += 2
                else:
                    i += 1

                name.append(player_name)
                id.append(player_id)
                pos.append(player_pos)
                team.append(nhl_team)
                date_of_injury.append(inj_date)
                injury_type.append(inj_type)
                injury_note.append(inj_desc)

        df = pd.DataFrame(name,columns=["name"])
        df['id'] = id
        df['pos'] = pos
        df['team'] = team
        df['date'] = date_of_injury
        df['status'] = injury_type
        df['note'] = injury_note


    except Exception as e:
        msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        if dialog:
            sg.PopupScrolled(msg, modal=True)
        else:
            logger.error(msg)
            raise

    return df

if __name__ == "__main__":

    main()

    exit()
