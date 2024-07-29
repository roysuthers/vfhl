# Import Python modules
import sqlite3

import PySimpleGUI as sg

# Import NHL Pool classes
from utils import get_db_connection, get_db_cursor


class Team:

    def __init__(self):

        self.id = 0
        self.name = ''
        self.abbr = ''

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
        #     print 'Player could not be persisted. Reason(s) are:\n%s'%errMsg
        #     return False

        return True

    def destroy(self, connection=None, **kwargs):

        if self.check() == False:
            return False

        ret = True


        # First: Delete team's relator table entry for season
        sql = 'delete from SeasonTeamRelator'
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
            connection.execute(sql, tuple(values))

            # Second: Delete team from Team if not in SeasonTeamRelator
            sql = 'delete from Team'
            values = []
            count = 0
            for criterion in kwargs['Criteria']:
                (property, opcode, value) = criterion
                if property == 'SeasonID':
                    continue
                if count > 0: sql = f'{sql} and'
                sql = f'{sql} where (select count(*) from SeasonTeamRelator where {property} {opcode} ?'
                if type(value) == str:
                    sql = f'{sql} COLLATE NOCASE'
                values.append(value)
                count += 1
            sql = f'{sql})'

            try:
                if not connection:
                    connection = get_db_connection()
                connection.execute(sql, tuple(values))

            except sqlite3.Error as e:
                ret = False
                msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                sg.popup_error(msg)
            except Exception as e:
                ret = False
                msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
                sg.popup_error(msg)

        except sqlite3.Error as e:
            ret = False
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            ret = False
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)

        return ret

    def fetch(self, **kwargs):

        sql = 'select * from Team'
        values = []
        count = 0
        for criterion in kwargs['Criteria']:
            (property, opcode, value) = criterion
            if count > 0: sql = f'{sql} and'
            sql = f'{sql} where {property} {opcode} ?'
            # Make case insensitive
            if type(value) == str:
                sql = f'{sql} COLLATE NOCASE'
            values.append(value)
            count += 1

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            row = cursor.fetchone()
            if row:
                self.id = row[0]
                self.name = row[1]
                self.abbr = row[2]
        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return self

    def fetch_many(self, **kwargs):

        sql = 'select {0}'.format(', '.join(kwargs['Columns']))
        sql = f'{sql} from Team'
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
        sql = f'{sql} order by ID'

        try:
            cursor = get_db_cursor()
            cursor.execute(sql, tuple(values))
            rows = cursor.fetchall()
            teams = []
            for row in rows:
                kwargs = {'Criteria': [['ID', '==', row]]}
                team = self.__init__().fetch(**kwargs)
                team.id = row[0]
                team.name = row[1]
                team.abbr = row[2]
                teams.append(team)

        except sqlite3.Error as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            sg.popup_error(msg)
        finally:
            cursor.close()

        return rows

    def get_team_id_from_team_abbr(self, team_abbr: str, suppress_error: bool=False) -> int:

        kwargs = {'Criteria': [['abbr', '==', team_abbr]]}
        team = self.fetch(**kwargs)

        if team.id == 0 and suppress_error is False:
            sg.popup(f'No id found for team "{team_abbr}"')

        return team.id

    def get_team_abbr_from_team_id(self, team_id: int) -> str:

        kwargs = {'Criteria': [['id', '==', team_id]]}
        team = self.fetch(**kwargs)

        if team.abbr == '':
            sg.popup(f'No id found for team "{team_id}"')

        return team.abbr

    def persist(self, seasonID, connection=None):

        if self.check() == False:
            return False

        if not connection:
            connection = get_db_connection()

        values1 = [self.id, self.name, self.abbr]
        values2 = [seasonID, self.id]
        # kwargs = {'Criteria': [['ID', '==', self.id]]}
        # team = Team().fetch(**kwargs)
        # if team.id == 0:
        sql1 = '''insert or replace into Team
                    (id, name, abbr)
                    values (?, ?, ?)'''
        sql2 = '''insert or replace into SeasonTeamRelator
                    (season_id, team_id)
                    values (?, ?)'''
        # else:
        #     values1.remove(self.id)
        #     values1.append(self.id)
        #     sql1 = '''update Team
        #              set Name=?, Abbr=?
        #              where ID=?'''
        #     sql2 = '''insert or replace into SeasonTeamRelator
        #              (season_id, team_id)
        #              values (?, ?)'''
        returnCode = True
        try:
            connection.execute(sql1, tuple(values1))
            connection.execute(sql2, tuple(values2))
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
