# import python modules
import sqlite3
from PySimpleGUI.PySimpleGUI import Tree

import numpy as np
import PySimpleGUI as sg
import pandas as pd

# import Hockey Pool classes
from clsPlayer import Player
from clsTeam import Team
from utils import get_db_connection, get_db_cursor
from constants import calendar


class PoolTeamRoster:

    def __init__(self):
        self.poolteam_id = 0
        self.player_id = 0
        self.status = ''
        self.keeper = ''
        self.date_added = ''
        self.date_removed = ''

        return

    def check(self):

        errMsg = ''
        if self.poolteam_id is None or self.poolteam_id == 0:
            errMsg += '\tPool team reference is mandatory.\n'
        if self.player_id is None or self.player_id == 0:
            errMsg += '\tHockey player reference is mandatory.\n'
        if errMsg:
            print(f'Pool Team Player could not be persisted. Reason(s) are:\n{errMsg}')
            return False

        return True

    def destroy(self, connection=None, **kwargs):

        if self.check() == False:
            return False

        ret = True

        sql = 'delete from PoolTeamRoster where'
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
            if not connection:
                connection = get_db_connection()
                outer_connection = False
            else:
                outer_connection = True
            connection.execute(sql, tuple(values))
            connection.commit()

        except sqlite3.Error as e:
            ret = False
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            ret = False
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            if outer_connection is False:
                connection.close()

        return ret

    def dialog(self):

        dialog = sg.Window(title='Pool Team Player', layout=self.layout(), finalize=True, resizable=True)

        while True:

            event, values = dialog.read()

            if event in ('Cancel', None):
                dialog.close()
                return

            if event == '_PLAYER_SEARCH':
                chars = values['_PLAYER_SEARCH']
                idx = df_active_players.query('last_name.str.lower().str.startswith(@chars.lower())').copy().index
                if len(idx) > 0:
                    row = idx[0]
                else:
                    row = 0
                dialog['_SELECT_PLAYERS_'].Widget.focus(row + 1)
                dialog['_SELECT_PLAYERS_'].Widget.see(row + dialog['_SELECT_PLAYERS_'].NumRows)
                continue

            if event == 'OK':
                if self.player_id == 0:
                    self.player_id = df_active_players['id'][values['_SELECT_PLAYERS_'][0]]
                self.date_added = values['_START_DATE_']
                self.date_removed = values['_END_DATE_']

                self.persist()

                dialog.close()

        return

    def fetch(self, **kwargs):

        sql = 'select * from PoolTeamRoster where'
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
                self.poolteam_id = row['poolteam_id']
                self.player_id = row['player_id']
                self.status = row['status']
                self.keeper = row['keeper']
                self.date_added = row['date_added']
                self.date_removed = row['date_removed']

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

        if 'Columns' in kwargs:
            sql = 'select {0}'.format(', '.join(kwargs['Columns']))
        else:
            sql = 'select *'

        sql = f'{sql} from PoolTeamRoster'

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
            roster = []
            for row in rows:
                player = PoolTeamRoster()
                player.poolteam_id = row['poolteam_id']
                player.player_id = row['player_id']
                player.status = row['status']
                player.keeper = row['keeper']
                player.date_added = row['date_added']
                player.date_removed = row['date_removed']
                roster.append(player)
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return roster

    def layout(self):

        global df_active_players

        with get_db_connection() as connection:
            sql = 'select p.id, p.last_name, p.first_name, t.abbr from Player p join Team t on t.id=p.current_team_id where p.active=1 order by p.last_name, p.first_name'
            df_active_players = pd.read_sql(sql=sql, con=connection)

        active_players = df_active_players.to_dict('split')
        active_players_data = active_players.get('data')
        active_players_columms = [x.replace('_', ' ') for x in active_players.get('columns')]
        visible_column_map = [False if x=='id' else True for x in active_players_columms]

        if self.player_id == 0:
            player_data_readonly = False
            selection_listbox_visible = True
            player_name = ''
            team_name = ''
        else:
            player_data_readonly = True
            selection_listbox_visible = False
            # get player name
            kwargs = {'id': self.player_id}
            player = Player().fetch(**kwargs)
            player_name = player.full_name
            current_team_id = player.current_team_id
            kwargs = {'Criteria': [['id', '==', current_team_id]]}
            team = Team().fetch(**kwargs)
            team_name = team.name

        layout = [
            [
                sg.Column(layout=
                    [
                        [
                            sg.Text('Player:', size=(17, 1)),
                            sg.Text(player_name, size=(25, 1), visible=player_data_readonly),
                            sg.Input('', size=(25, 1), visible=(not player_data_readonly), enable_events=True, focus=True, key='_PLAYER_SEARCH'),
                        ],
                        [
                            sg.pin(
                                sg.Column(layout=[
                                    [
                                        sg.Text('', size=(17, 1)),
                                        sg.Table(values=active_players_data, headings=active_players_columms, visible_column_map=visible_column_map, enable_events=True, select_mode='extended', justification='left', num_rows=5, selected_row_colors=('red', 'yellow'), key='_SELECT_PLAYERS_')
                                    ],
                                ], expand_y=True, visible=selection_listbox_visible, key='_SELECT_PLAYERS_PANE_')
                            , expand_y=True)
                        ],
                        [
                            sg.Text('Team:', size=(17, 1), visible=player_data_readonly),
                            sg.Text(team_name, size=(25, 1), visible=player_data_readonly),
                        ],
                    ], expand_y=True),
            ],
            [
                sg.Text('Stats Start Date:', size=(17, 1)),
                sg.Input(self.date_added, size=(12, 1), key='_START_DATE_'),
                sg.CalendarButton(
                    begin_at_sunday_plus=1,
                    button_text='',
                    close_when_date_chosen=True,
                    format='%Y-%m-%d',
                    image_filename=calendar,
                    image_subsample=5,
                    key='_START_DATE_CALENDAR_',
                    no_titlebar=False,
                    target='_START_DATE_',
                ),
            ],
            [
                sg.Text('Stats End Date:', size=(17, 1)),
                sg.Input(self.date_removed, size=(12, 1), key='_END_DATE_'),
                sg.CalendarButton(
                    begin_at_sunday_plus=1,
                    button_text='',
                    close_when_date_chosen=True,
                    format='%Y-%m-%d',
                    image_filename=calendar,
                    image_subsample=5,
                    key='_END_DATE_CALENDAR_',
                    no_titlebar=False,
                    target='_END_DATE_',
                ),
            ],
            [
                sg.OK(bind_return_key=True),
                sg.Cancel(),
            ]
        ]

        return layout

    def persist(self):

        if self.check() == False:
            return False

        connection = get_db_connection()

        values = [self.poolteam_id, self.player_id, self.status, self.keeper, self.date_added, self.date_removed]
        sql_columns = ', '.join(self.__dict__.keys())
        sql_values = ', '.join(['?' for i in range(0, len(values))])
        sql = f'''insert or replace into PoolTeamRoster
                        ({sql_columns})
                        values ({sql_values})'''

        returnCode = True
        try:
            connection.execute(sql, tuple(values))
            connection.commit()
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            returnCode = False
            connection.rollback()
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            connection.rollback()
            returnCode = False
        finally:
            connection.close()

        return returnCode
