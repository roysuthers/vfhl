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

        # parse the html using beautiful soup and store in variable 'tableData'
        soup = BeautifulSoup(page, "html.parser")

        msg = f'Scraping "{url}"...'
        if dialog:
            dialog['-PROG-'].update(msg)
            event, values = dialog.read(timeout=10)
            if event == 'Cancel' or event == sg.WIN_CLOSED:
                return
        else:
            logger.debug(msg)

        table = soup.find(name="table", attrs={"class": "table"})

        name = []
        team = []
        date_of_injury = []
        injury_type = []
        injury_note = []

        for row in table.findAll(name="tr"):
            cells = row.find_all(name=["td"])
            if len(cells) == 3:
                td_cells = cells[2].text.strip().split('\n')
                player_name, inj_type = td_cells[1].split(' - ', 1)
                if player_name.strip() == '':
                    continue
                name.append(player_name.strip())
                nhl_team = cells[0].next.get('href').replace('/team/', '').strip()
                if nhl_team:
                    team.append(nhl_teams[nhl_team])
                else:
                    team.append('')
                if len(td_cells) > 3:
                    date_of_injury.append(td_cells[3].strip())
                elif len(td_cells) > 2:
                    date_of_injury.append(td_cells[2].strip())
                else:
                    date_of_injury.append('')
                injury_type.append(inj_type.strip())
                injury_note.append(td_cells[0])

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
            raise

    return df

if __name__ == "__main__":

    main()

    exit()
