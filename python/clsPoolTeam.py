# Import Python modules
import sqlite3

import numpy as np

import PySimpleGUI as sg

# Import Hockey Pool classes
from utils import get_db_connection, get_db_cursor

class PoolTeam:

    def __init__(self):

        self.id = 0
        self.pool_id = 0
        self.name = ''
        self.points = 0
        self.email = ''
        self.draft_pos = 0
        self.paid = 0
        self.won = 0
        self.fantrax_id = ''
        self.F_games_played = 0
        self.F_maximum_games = 0
        self.D_games_played = 0
        self.D_maximum_games = 0
        self.Skt_games_played = 0
        self.Skt_maximum_games = 0
        self.G_games_played = 0
        self.G_maximum_games = 0
        self.G_minimum_starts = 0

        return

    def check(self):

        # errMsg = ''
        # if self.firstName is None:
        #     errMsg += '\tPlayer''s first name is mandatory.\n'
        # if self.lastName is None:
        #     errMsg += '\tPlayer''s last name is mandatory.\n'
        # if self.pid is None:
        #     errMsg += '\tPlayer ID is mandatory.\n'
        # if errMsg:
        #     print 'NHLPlayer could not be persisted. Reason(s) are:\n%s'%errMsg
        #     return False

        return True

    def countOfPoolTeams(self):

        count = 0
        values = [str(self.pool_id)]
        if self.pool_id == 0:
            print('Cannot determine number of pool teams')
            return count
        else:
            sql = 'select count(*) from PoolTeam \
                    where pool_id=?'
        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            if row:
                count = row[0]
            # lastRowID = connection.lastrowid
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return count

    def dialog(self):

        layout = [
            [
                sg.Text(self.id, visible=False, key='OID'),
                sg.Text('Team Name:', size=(15,1)),
                sg.Input(default_text=self.name, size=(25,1), key='Team_Name')
            ],
            [
                sg.Text('Email:', size=(15,1)),
                sg.Input(default_text=self.email, size=(25,1), key='Email')
            ],
            [
                sg.Text('Draft Position:', size=(15,1)),
                sg.Input(default_text=self.draft_pos, size=(25,1), key='Draft_Pos')
            ],
            [
                sg.Text('Entry Fee Paid:', size=(15,1)),
                sg.Input(default_text=self.paid, size=(25,1), key='Entry_Fee')
            ],
            [
                sg.Text('Amount Won:', size=(15,1)),
                sg.Input(default_text=self.won, size=(25,1), key='Won')
            ],
            [
                sg.Button('OK'), sg.Button('Cancel')
            ]
        ]

        dialog = sg.Window('Pool Team', layout=layout)

        while True:

            event, values = dialog.Read()

            if event in (None, 'Cancel'):
                dialog.Close()
                break

            if event == 'OK':
                self.name = values['Team_Name']
                self.email = values['Email']
                self.draft_pos = values['Draft_Pos']
                self.paid = values['Entry_Fee']
                self.won = values['Won']

                self.persist()

                dialog.Close()
                break

        return

    def destroy(self, connection=None, **kwargs):

        if self.check() == False:
            return False

        ret = True

        sql = 'delete from PoolTeam'
        values = []
        count = 0
        for criterion in kwargs['Criteria']:
            (property, opcode, value) = criterion
            if count > 0: sql = f'{sql} and'
            sql = f'{sql} where {property} {opcode} ?'
            if type(value) == str:
                sql = f'{sql} COLLATE NOCASE'
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

    def fetch(self, **kwargs):

        sql = 'select * from PoolTeam'
        values = []
        count = 0
        for criterion in kwargs['Criteria']:
            (property, opcode, value) = criterion
            if count > 0:
                sql = f'{sql} and {property} {opcode} ?'
            else:
                sql = f'{sql} where {property} {opcode} ?'
            if type(value) == str:
                sql = f'{sql} COLLATE NOCASE'
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

        sql = f'{sql} from PoolTeam'

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
            pool_teams = []
            for row in rows:
                pool_team = PoolTeam()
                pool_team.id = row['id']
                pool_team.name = row['name']
                pool_team.points = row['points']
                pool_team.email = row['email']
                pool_team.draft_pos = row['draft_pos']
                pool_team.paid = row['paid']
                pool_team.won = row['won']
                pool_team.fantrax_id = row['fantrax_id']
                pool_team.F_games_played = row['F_games_played']
                pool_team.F_maximum_gameson = row['F_maximum_games']
                pool_team.D_games_played = row['D_games_played']
                pool_team.D_maximum_games = row['D_maximum_games']
                pool_team.Skt_games_played = row['Skt_games_played']
                pool_team.Skt_maximum_games = row['Skt_maximum_games']
                pool_team.G_games_played = row['G_games_played']
                pool_team.G_maximum_games = row['G_maximum_games']
                pool_team.G_minimum_starts = row['G_minimum_starts']
                pool_teams.append(pool_team)
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return pool_teams

    def persist(self, connection=None):

        if self.check() == False:
            return False

        if not connection:
            connection = get_db_connection()

        columns = dict.fromkeys(self.__dict__)
        if self.id == 0:
            values = [self.pool_id, self.name, self.points, self.email, self.draft_pos, self.paid, self.won, self.fantrax_id, self.F_games_played, self.F_maximum_games, self.D_games_played, self.D_maximum_games, self.Skt_games_played, self.Skt_maximum_games, self.G_games_played, self.G_maximum_games, self.G_minimum_starts]
            del columns['id']
        else:
            values = [self.id, self.pool_id, self.name, self.points, self.email, self.draft_pos, self.paid, self.won, self.fantrax_id, self.F_games_played, self.F_maximum_games, self.D_games_played, self.D_maximum_games, self.Skt_games_played, self.Skt_maximum_games, self.G_games_played, self.G_maximum_games, self.G_minimum_starts]
        sql_columns = ', '.join(columns)
        sql_values = ', '.join(['?' for i in range(0, len(values))])
        sql = f'''insert or replace into PoolTeam
                        ({sql_columns})
                        values ({sql_values})'''

        returnCode = True
        try:
            connection.execute(sql, tuple(values))
            connection.commit()
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            connection.rollback()
            returnCode = False
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
            connection.rollback()
            returnCode = False

        return returnCode
