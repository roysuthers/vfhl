import logging.config
import os
import sys
import traceback
from datetime import date, timedelta

import ujson as json

from clsHockeyPool import HockeyPool
from clsSeason import Season
from utils import get_db_connection

# Get the directory of the current script
dir_path = os.path.dirname(os.path.realpath(__file__))
# Join the directory path with your file name
file_path = os.path.join(dir_path, 'logging_config.json')

with open(file_path, 'r') as logging_config_file:
    logging_config = json.load(logging_config_file)
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

def main():

    try:

        this_function = sys._getframe().f_code.co_name

        logger.info('"Task scheduler 2" started')

        seasons = Season().getCurrent()
        if len(seasons) == 0:
            return

        hp = HockeyPool()

        with get_db_connection() as connection:
            cursor = connection.cursor()
            # if there multiple, it doesn't matter at this point since only interested in season id
            sql = f'select * from HockeyPool hp where season_id={seasons[0].id}'
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                row = rows[0]
                for key in row.keys():
                    setattr(hp, key, row[key])
            cursor.close()

        # send email for team transactions
        logger.info('Calling hp.email_nhl_team_transactions().')
        try:
            hp.email_nhl_team_transactions(batch=True)
        except Exception as e:
            logger.error(f'Exception in call to hp.email_nhl_team_transactions() returned. \nException: {repr(e)}')
        logger.info('Call to hp.email_nhl_team_transactions() returned.')

        logger.info('Calling hp.updatePlayerInjuries().')
        try:
            hp.updatePlayerInjuries(suppress_prompt=True, batch=True)
        except Exception as e:
            logger.error(f'Exception in call to hp.updatePlayerInjuries() returned. \nException: {repr(e)}')
        logger.info('Call to hp.updatePlayerInjuries() returned.')

        # line & pp unit projections
        for season in seasons:

           # only for regular season
            if season.type == 'R':

                # update season constants
                season.set_season_constants()

                if season.SEASON_HAS_STARTED is True and season.SEASON_HAS_ENDED is False:
                    logger.info('Calling hp.update_player_lines().')
                    today = date.strftime(date.today(), '%Y-%m-%d')
                    try:
                        hp.update_player_lines(season=season, batch=True, game_date=today)
                    except Exception as e:
                        logger.error(f'Exception in call to hp.update_player_lines() returned. \nException: {repr(e)}')
                    logger.info('Call to hp.update_player_lines() returned.')

                logger.info('Calling hp.updatePoolTeamRosters().')
                try:
                    hp.updatePoolTeamRosters(suppress_prompt=True, batch=True)
                except Exception as e:
                    logger.error(f'Exception in call to hp.updatePoolTeamRosters() returned. \nException: {repr(e)}')
                logger.info('Call to hp.updatePoolTeamRosters() returned.')

                logger.info('Calling hp.updateFantraxPlayerInfo() for minors_available_players, minors_taken_players, active_available_players, all_taken_players')
                try:
                    hp.updateFantraxPlayerInfo(batch=True)
                except Exception as e:
                    logger.error(f'Exception in call to hp.updateFantraxPlayerInfo() returned. \nException: {repr(e)}')
                logger.info('Call to hp.updateFantraxPlayerInfo() returned.')

                logger.info('Calling hp.updateFantraxPlayerInfo() for watch_list.')
                try:
                    hp.updateFantraxPlayerInfo(batch=True, watchlist=True)
                except Exception as e:
                    logger.error(f'Exception in call to hp.updateFantraxPlayerInfo() returned. \nException: {repr(e)}')
                logger.info('Call to hp.updateFantraxPlayerInfo() returned.')

        logger.info('"Task scheduler 2" completed')

    except Exception as e:
        # trace_back = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
        logger.error(repr(e))
        return

    return

if __name__ == "__main__":

    main()

    exit()
