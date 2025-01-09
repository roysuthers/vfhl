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
from selenium.webdriver.support.ui import Select, WebDriverWait
from unidecode import unidecode

from clsBrowser import Browser
from utils import get_db_connection


def main(dialog: sg.Window=None):

    # df = from_sports_reference(dialog=dialog)

    df = from_puckpedia(dialog=dialog)

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
        df_teams['name'] = df_teams['name'].apply(lambda x: x.lower().replace(' ', '-').replace('.', ''))
        df_teams['name'] = df_teams['name'].apply(lambda x: unidecode(x))
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

        # # query the website and return the html to the variable 'page'
        # # page = urlopen(url)
        # headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        # response = requests.get(url, headers=headers)
        # page = response.content

        with Browser() as browser:

            # Set default wait time
            wait = WebDriverWait(browser, 60)

            browser.get(url)

            # parse the html using beautiful soup
            soup = BeautifulSoup(browser.page_source, "html.parser")

            msg = f'Scraping "{url}"...'
            if dialog:
                dialog['-PROG-'].update(msg)
                event, values = dialog.read(timeout=2)
                if event == 'Cancel' or event == sg.WIN_CLOSED:
                    return
            else:
                logger.debug(msg)

            name = []
            team = []
            date_of_injury = []
            injury_type = []
            injury_note = []

            # subtract 2 for "Next" & "Last" links
            pages_count = len(soup.find_all(name="li", attrs={"class": "pager__item"})) - 2

            # page numbers start at 0
            for page_number in range(pages_count):

                if page_number >= 1:
                    # # page = urlopen(f'{url}?page={page_number}')
                    # response = requests.get(f'{url}?page={page_number}', headers=headers)
                    # page = response.content

                    browser.get(f'{url}?page={page_number}')
                    soup = BeautifulSoup(browser.page_source, "html.parser")

                table = soup.find(name="div", attrs={"class": "pp_layout_main"})

                for row in table.findAll(name="div", attrs={"class": "border-b"}):
                    elements = [item for item in row.text.splitlines() if item not in ('', ' ')]
                    # for some reason, elements do not identify a player; i.e. "['OUT | Upper Body', 'Expected Return: Sep 15, 2024']"
                    if len(elements) == 2:
                        continue
                    inj_type = elements[0].split(' | ', 1)
                    player_name = elements[1]
                    # for some reason, elements do not provide an injury description; i.e. "['DAY-TO-DAY | Upper Body', 'Spencer Stastney', 'Expected Return: Sep 15, 2024']"
                    if len(elements) == 3:
                        inj_desc = ''
                        exp_return = elements[2].replace('Expected Return', 'Expected Return ')
                    else:
                        inj_desc = elements[2]
                        exp_return = elements[3].replace('Expected Return', 'Expected Return ')

                    name.append(player_name)

                    player_info = row.find(name=["a"]).get('href').rsplit('/')
                    if player_info[1] == 'team':
                        nhl_team = player_info[2]
                        if nhl_team == 'utah-hc':
                            team.append('UTA')
                        else:
                            team.append(nhl_teams[nhl_team])
                    else:
                        team.append('N/A')

                    date_of_injury.append(exp_return)
                    injury_type.append(inj_type[0])
                    injury_note.append(inj_desc)

                # msg = f'Found "{name}" in injury list...'
                # if dialog:
                #     dialog['-PROG-'].update(msg)
                #     event, values = dialog.read(timeout=2)
                #     if event == 'Cancel' or event == sg.WIN_CLOSED:
                #         return
                # else:
                #     logger.debug(msg)

            df = pd.DataFrame(name,columns=["name"])
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
