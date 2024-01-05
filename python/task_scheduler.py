import logging.config
import os
import smtplib
import sys
import traceback
from datetime import date, timedelta

import ujson as json
from pandas.io.formats.style import Styler

from clsHockeyPool import HockeyPool
from clsNHL_API import NHL_API
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
logger.handlers[0].doRollover()

def main():

    try:

        this_function = sys._getframe().f_code.co_name

        logger.info('"Task scheduler" started')

        nhl_api = NHL_API()

        seasons = Season().getCurrent()
        if len(seasons) == 0:
            return

        hp = HockeyPool()

        with get_db_connection() as connection:
            cursor = connection.cursor()
            sql = f'select * from HockeyPool hp where season_id={seasons[0].id}'
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                fantrax = [r for r in rows  if r['web_host']=='Fantrax']
                if fantrax:
                    row = fantrax[0]
                else:
                    row = rows[0]
                for key in row.keys():
                    setattr(hp, key, row[key])
            cursor.close()

        for season in seasons:
            logger.info(f'Calling nhl_api.get_player_stats() for {season.id}{season.type}.')
            # update season constants
            season.set_season_constants()
            if season.SEASON_HAS_STARTED is True and season.SEASON_HAS_ENDED is False:
                try:
                    nhl_api.get_player_stats(season=season, batch=True)
                except:
                    logger.info('Exception in call to nhl_api.get_player_stats().')
                logger.info('Call to nhl_api.get_player_stats() returned.')
            elif season.SEASON_HAS_STARTED is False:
                logger.info(f'{season.id}{season.type} has not started.')
            elif season.SEASON_HAS_ENDED is True:
                logger.info(f'{season.id}{season.type} has completed.')
        # I think I need to get the players after player stats, because get_players()
        # will add missing roster players, irrespective of having stats, while the
        # get_player_stats clears the TeamRosters table, and re-outputs based on stats, or being on a
        # pool team roster.
        logger.info('Calling nhl_api.get_players().')
        try:
            nhl_api.get_players(season=seasons[0], batch=True)
        except:
            logger.info('Exception in call to nhl_api.get_players() returned.')
        logger.info('Call to nhl_api.get_players() returned.')

        logger.info('Calling hp.updatePlayerInjuries().')
        try:
            hp.updatePlayerInjuries(suppress_prompt=True, batch=True)
        except:
            logger.info('Exception in call to hp.updatePlayerInjuries() returned.')
        logger.info('Call to hp.updatePlayerInjuries() returned.')

        # line line & pp unit projections
        # only for regular season
        # Note: this is also scheduled in task_scheduler_2.py, which is set to run starting at 12 None
        # This script is scheduled to run early in the morning, and (hopefully) shouldn't clash with
        # the  task_scheduler_2.py scheduled task
        for season in seasons:
            if season.type == 'R':
                logger.info('Calling hp.update_player_lines().')
                today = date.strftime(date.today(), '%Y-%m-%d')
                # yesterday = date.strftime(date.today() - timedelta(days=1), '%Y-%m-%d')
                # for game_date in (yesterday, today):
                    # hp.update_player_lines(season=season, batch=True, game_date=game_date)
                try:
                    hp.update_player_lines(season=season, batch=True, game_date=today)
                except:
                    logger.info('Exception in call to hp.update_player_lines() returned.')
                logger.info('Call to hp.update_player_lines() returned.')
                # break

                logger.info('Calling hp.updatePoolTeams().')
                try:
                    hp.updatePoolTeams(suppress_prompt=True, batch=True)
                except:
                    logger.info('Exception in call to hp.updatePoolTeams() returned.')
                logger.info('Call to hp.updatePoolTeams() returned.')

                logger.info('Calling hp.updatePoolTeamRosters().')
                try:
                    hp.updatePoolTeamRosters(suppress_prompt=True, batch=True)
                except:
                    logger.info('Exception in call to hp.updatePoolTeamRosters() returned.')
                logger.info('Call to hp.updatePoolTeamRosters() returned.')

                logger.info('Calling hp.updateFantraxPlayerInfo() for active_available_players, minors_available_players, active_taken_players, minors_taken_players')
                try:
                    hp.updateFantraxPlayerInfo(batch=True)
                except:
                    logger.info('Exception in call to hp.updateFantraxPlayerInfo() returned.')
                logger.info('Call to hp.updateFantraxPlayerInfo() returned.')

                logger.info('Calling hp.updateFantraxPlayerInfo() for watch_list.')
                try:
                    hp.updateFantraxPlayerInfo(batch=True, watchlist=True)
                except:
                    logger.info('Exception in call to hp.updateFantraxPlayerInfo() returned.')
                logger.info('Call to hp.updateFantraxPlayerInfo() returned.')

                logger.info('Calling hp.getMoneyPuckData().')
                try:
                    hp.getMoneyPuckData(season=season, batch=True)
                except:
                    logger.info('Exception in call to hp.getMoneyPuckData() returned.')
                logger.info('Call to hp.getMoneyPuckData() returned.')

        logger.debug('Formatting & sending "Daily VFHL Scheduled Task" notification email...')
        caption = f'Task Scheduler: "Daily VFHL Scheduled Task" notification'
        recipients = ['rsuthers@cogeco.ca']
        email_sent = hp.formatAndSendEmail(data_frames=[], html_tables=[], message='"Daily VFHL Scheduled Task" notification', recipients=recipients, subject=caption, show_sent_msg=False, batch=True, dialog=None)
        if email_sent is True:
            logger.debug('Email sent...')
        else:
            logger.debug('Email not sent...')

        logger.info('"Task scheduler" completed')

    except Exception as e:
        logger.error(repr(e))
        return

    return

if __name__ == "__main__":

    main()

    exit()
