#import the libraries
import logging
import traceback
from urllib.request import urlopen

import pandas as pd
import PySimpleGUI as sg
import ujson as json
from bs4 import BeautifulSoup
from openpyxl.utils.dataframe import dataframe_to_rows
from unidecode import unidecode

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
            event, values = dialog.read(timeout=10)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        # query the website and return the html to the variable 'page'
        page = urlopen(hockey_reference_com)

        # parse the html using beautiful soup and store in variable 'tableData'
        soup = BeautifulSoup(page, "html.parser")

        msg = f'Scraping "{hockey_reference_com}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=10)
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
            event, values = dialog.read(timeout=10)
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
            event, values = dialog.read(timeout=10)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        # query the website and return the html to the variable 'page'
        page = urlopen(url)

        # parse the html using beautiful soup
        soup = BeautifulSoup(page, "html.parser")

        msg = f'Scraping "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=10)
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
                page = urlopen(f'{url}?page={page_number}')
                soup = BeautifulSoup(page, "html.parser")

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
                nhl_team = row.find(name=["a"]).get('href').rsplit('/', 1)[1]
                team.append(nhl_teams[nhl_team])
                date_of_injury.append(exp_return)
                injury_type.append(inj_type[0])
                injury_note.append(inj_desc)

            # msg = f'Found "{name}" in injury list...'
            # if dialog:
            #     dialog['-PROG-'].update(msg)
            #     event, values = dialog.read(timeout=10)
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
        if dialog:
            sg.PopupScrolled(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)), modal=True)
        else:
            logger.error(repr(e))
            raise

    return df

if __name__ == "__main__":

    main()

    exit()
