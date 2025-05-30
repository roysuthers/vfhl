# Import Python modules
import io
# import json
import os
import sqlite3
import webbrowser
from urllib.request import urlopen

import cairosvg
import flatten_json as fj
import jmespath as j
import numpy as np
import pandas as pd
import PySimpleGUI as sg
import requests
import ujson as json
from PIL import Image

# Import NHL Pool classes
from constants import NHL_API_BASE_URL, NHL_API_URL, NHL_ASSETS_BASE_URL
from utils import get_db_connection, get_db_cursor


class Player:

    def __init__(self):
        self.id = 0
        self.fantrax_id = 0
        self.first_name = ''
        self.last_name = ''
        self.full_name = ''
        self.birth_date = ''
        self.height = ''
        self.weight = 0
        self.active = False
        # self.rookie = False
        self.roster_status = ''
        self.current_team_id = 0
        self.current_team_abbr = ''
        self.primary_position = ''
        self.games = 0
        self.injury_status = ''
        self.injury_note = ''

    def check(self):

        errMsg = ''
        if self.first_name is None:
            errMsg += '\tPlayer''s first name is mandatory.\n'
        if self.last_name is None:
            errMsg += '\tPlayer''s last name is mandatory.\n'
        if self.id is None:
            errMsg += '\tPlayer ID is mandatory.\n'
        if errMsg:
            print(f'Player could not be persisted. Reason(s) are:\n{errMsg}')
            return False

        return True

    def fetch(self, **kwargs):

        sql = 'select * from Player where'
        values = []
        count = 0
        for key, value in kwargs.items():
            if count > 0: sql += ' and'
            sql += ' {0}=?'.format(key)
            # Make case insensitive
            sql += ' COLLATE NOCASE'
            values.append(value)
            count += 1

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            if row:
                for key in self.__dict__.keys():
                    setattr(self, key, row[key])
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            # print(sql)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            # print(sql)
        finally:
            cursor.close()

        return self

    def fetch_many(self, **kwargs):

        if 'Columns' in kwargs is True:
            sql = 'select {0}'.format(', '.join(kwargs['Columns']))
        else:
            sql = 'select *'

        sql = f'{sql} from Player'

        values = []
        count = 0
        if 'Criteria' in kwargs:
            for criterion in kwargs['Criteria']:
                (property, opcode, value) = criterion
                if count > 0: sql = f'{sql} and'
                sql = f'{sql} where {property} {opcode} ?'
                if type(value) == str:
                    sql = f'{sql} COLLATE NOCASE'
                values.append(value)
                count += 1

        count = 0
        if 'Sort' in kwargs:
            for sort_properties in kwargs['Sort']:
                (property, seq) = sort_properties
                if count == 0:
                    sql = f'{sql} order by {property} {seq}'
                else:
                    sql = f'{sql}, {property} {seq}'
                count += 1

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            rows = cursor.fetchall()
            players = []
            for row in rows:
                player = Player()
                for key in self.__dict__.keys():
                    setattr(player, key, row[key])
                players.append(player)
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return players

    def layout(self, season_id: int):

        # Mug shot
        # https://assets.nhle.com/mugs/nhl/default-skater.png
        url = f'{NHL_ASSETS_BASE_URL}/mugs/nhl/{season_id}/{self.current_team_abbr}/{self.id}.png'
        # img = Image.open(urlopen(url))
        # mug_shot = io.BytesIO()
        # img.save(mug_shot, format='GIF')
        # Download the image
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        # Convert the image to a format that PySimpleGUI can display
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        img_data = bio.getvalue()

        player = requests.get(f'{NHL_API_URL}/player/{self.id}/landing').json()

        date = player.get('birthDate')
        city = player.get('birthCity').get('default')
        province_state = player.get('birthStateProvince').get('default') if 'birthStateProvince' in player else None
        country = player.get('birthCountry')
        if province_state is None:
            birth_info = ''.join([date, ' in ', city, ', ', country])
        else:
            birth_info = ''.join([date, ' in ', city, ', ', province_state, ', ', country])

        team_id = None
        team_name = None
        team_logo = None
        if 'currentTeamId' in player:
            current_team = player.get('currentTeamId')

            team_id = player.get('currentTeamId')
            team_abbr = player.get('currentTeamAbbrev')
            team_name = player.get('fullTeamName').get('default')

            url = player.get('teamLogo')
            team_logo = io.BytesIO()
            cairosvg.svg2png(url=url, write_to=team_logo, scale=0.035)
            team_logo = team_logo.getvalue()

        # primary_position = ''
        # if 'primaryPosition' in player:
        #     primary_position = j.search('primaryPosition.abbreviation', player)

        if team_logo is None:
            logo_visible = False
        else:
            logo_visible = True

        if team_name is None:
            team_visible = False
            logo_visible = False
        else:
            team_visible = True

        jersey_number = player.get('sweaterNumber')
        position = player.get('position')
        # if team_id is not None:
        #     for person in [fj.flatten(d, '_') for d in j.search('teams[0].roster.roster', requests.get(f'{NHL_API_URL}/teams/{team_id}?expand=team.roster').json())]:
        #         if person['person_id'] == self.id:
        #             break
        #     jersey_number = person['jerseyNumber']
        #     position = person['position_abbreviation']

        # twitter = j.search('people[0].social.twitter[0]', requests.get(f'{NHL_API_URL}/people/{self.id}?expand=person.social').json())
        # if twitter is not None:
        #     twitter = f'@{twitter}'

        layout = [
            [
                sg.Column(layout=
                    [
                        [
                            # sg.Image(data=mug_shot.getvalue(), enable_events=True, key='CLICK-MUG-SHOT', tooltip='Click to open NHL API player link'),
                            sg.Image(data=img_data),
                            # sg.Text(player['link'], visible=False, key='PLAYER-LINK'),
                        ],
                        # [
                        #     sg.Input(twitter, size=(20,1), readonly=True, disabled_readonly_background_color=sg.theme_background_color(), disabled_readonly_text_color=sg.theme_text_color(), border_width=0, justification='center'),
                        # ],
                    ], expand_x=True, expand_y=True),
                sg.Column(layout=
                    [
                        [
                            sg.Text(f"{player.get('firstName').get('default')} {player.get('lastName').get('default')}", auto_size_text=True),
                        ],
                        [
                            sg.Text('Born:', auto_size_text=True), sg.Text(birth_info, auto_size_text=True),
                        ],
                        [
                            # sg.Text('Age:', auto_size_text=True), sg.Text(player.get('currentAge'), auto_size_text=True),
                            sg.Text('Height:', auto_size_text=True), sg.Text(player.get('heightInInches'), auto_size_text=True),
                            sg.Text('Weight:', auto_size_text=True), sg.Text(player.get('weightInPounds'), auto_size_text=True),
                        ],
                        [
                            # sg.Text('Team:', auto_size_text=True, visible=team_visible), sg.Image(data=team_logo.im, visible=logo_visible), sg.Text(team_name, auto_size_text=True, visible=team_visible),
                            sg.Text('Team:', auto_size_text=True, visible=team_visible),
                            sg.Image(data=team_logo, visible=logo_visible), sg.Text(team_name, auto_size_text=True, visible=team_visible),
                        ],
                        [
                            sg.Text('Jersey:', auto_size_text=True, visible=team_visible), sg.Text(jersey_number, auto_size_text=True, visible=team_visible),
                            sg.Text('Position:', auto_size_text=True, visible=team_visible), sg.Text(position, auto_size_text=True, visible=team_visible),
                            # sg.Text('Natural:', auto_size_text=True, visible=team_visible), sg.Text(primary_position, auto_size_text=True, visible=team_visible),
                        ],
                    ], expand_x=True, expand_y=True),
            ],
            [
                sg.OK(),
            ]
        ]

        return layout

    def window(self, season_id: int):

        window = sg.Window(title='Player Biography', layout=self.layout(season_id), finalize=True, resizable=True)

        while True:

            event, values = window.read()

            if event in ('OK', None):
                window.close()
                return

            # if event == 'CLICK-MUG-SHOT':
            #     link = window.AllKeysDict['PLAYER-LINK'].get()
            #     webbrowser.open(f'{NHL_ASSETS_BASE_URL}/{link}')

        return

    def persist(self):

        if self.check() == False:
            return False

        connection = get_db_connection()

        values = [x for x in self.__dict__.values()]
        sql_columns = ', '.join(self.__dict__.keys())
        sql_values = ', '.join(['?' for i in range(0, len(values))])
        sql = f'''insert or replace into Player
                  ({sql_columns})
                  values ({sql_values})'''

        returnCode = True
        try:
            connection.execute(sql, tuple(values))
            connection.commit()

        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            # print(sql)
            connection.rollback()
            returnCode = False
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            # print(sql)
            connection.rollback()
            returnCode = False
        finally:
            connection.close()

        return returnCode
