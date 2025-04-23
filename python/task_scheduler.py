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
            grace_period_end_date = season.end_date + timedelta(days=3)
            if season.SEASON_HAS_STARTED is True and (season.SEASON_HAS_ENDED is False or season.SEASON_HAS_STARTED is True and date.today() <= grace_period_end_date):
                try:
                    nhl_api.get_player_stats(season=season, batch=True)
                except Exception as e:
                    logger.error(f'Exception in call to nhl_api.get_player_stats(). \nException: {repr(e)}')
                logger.info('Call to nhl_api.get_player_stats() returned.')
            elif season.SEASON_HAS_STARTED is False:
                logger.info(f'nhl_api.get_player_stats() not executed because "{season.id}{season.type}" has not started.')
            elif season.SEASON_HAS_ENDED is True:
                logger.info(f'nhl_api.get_player_stats() not executed because "{season.id}{season.type}" has completed.')
        # I think I need to get the players after player stats, because get_players()
        # will add missing roster players, irrespective of having stats, while the
        # get_player_stats clears the TeamRosters table, and re-outputs based on stats, or being on a
        # pool team roster.
        logger.info('Calling nhl_api.get_players().')
        try:
            nhl_api.get_players(season=seasons[0], batch=True)
        except Exception as e:
            logger.error(f'Exception in call to nhl_api.get_players() returned. \nException: {repr(e)}')
        logger.info('Call to nhl_api.get_players() returned.')

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

                logger.info('Calling hp.updatePoolTeams().')
                try:
                    hp.updatePoolTeams(suppress_prompt=True, batch=True)
                except Exception as e:
                    logger.error(f'Exception in call to hp.updatePoolTeams() returned. \nException: {repr(e)}')
                logger.info('Call to hp.updatePoolTeams() returned.')

                logger.info('Calling hp.updatePoolTeamRosters().')
                try:
                    hp.updatePoolTeamRosters(suppress_prompt=True, batch=True)
                except Exception as e:
                    logger.error(f'Exception in call to hp.updatePoolTeamRosters() returned. \nException: {repr(e)}')
                logger.info('Call to hp.updatePoolTeamRosters() returned.')

                if season.SEASON_HAS_STARTED is True and season.SEASON_HAS_ENDED is False:
                    logger.info('Calling hp.getMoneyPuckData().')
                    try:
                        hp.getMoneyPuckData(season=season, batch=True)
                    except Exception as e:
                        logger.error(f'Exception in call to hp.getMoneyPuckData() returned. \nException: {repr(e)}')
                    logger.info('Call to hp.getMoneyPuckData() returned.')

        logger.info('Calling hp.updatePlayerInjuries().')
        try:
            hp.updatePlayerInjuries(suppress_prompt=True, batch=True)
        except Exception as e:
            logger.error(f'Exception in call to hp.updatePlayerInjuries() returned. \nException: {repr(e)}')
        logger.info('Call to hp.updatePlayerInjuries() returned.')

        logger.info('Calling hp.updateFantraxPlayerInfo() for active_available_players, minors_available_players, active_taken_players, minors_taken_players')
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

        # send email for team transactions
        logger.info('Calling hp.email_nhl_team_transactions().')
        try:
            hp.email_nhl_team_transactions(batch=True)
        except Exception as e:
            logger.error(f'Exception in call to hp.email_nhl_team_transactions() returned. \nException: {repr(e)}')
        logger.info('Call to hp.email_nhl_team_transactions() returned.')

        # # send email starting goalie projections
        # logger.info('Calling hp.email_starting_goalie_projections().')
        # try:
        #     hp.email_starting_goalie_projections(pool_id=hp.id, batch=True)
        # except Exception as e:
        #     logger.error(f'Exception in call to hp.email_starting_goalie_projections() returned. \nException: {repr(e)}')
        # logger.info('Call to hp.email_starting_goalie_projections() returned.')

        # for season in seasons:
        #     # only for regular season
        #     if season.type == 'R':

        #         logger.info('Calling hp.updatePoolStandingsGainLoss().')
        #         try:
        #             hp.updatePoolStandingsGainLoss(batch=True)
        #         except Exception as e:
        #             logger.error(f'Exception in call to hp.updatePoolStandingsGainLoss() returned. \nException: {repr(e)}')
        #         logger.info('Call to hp.updatePoolStandingsGainLoss() returned.')

        #         logger.info('Calling hp.updatePoolTeamServiceTimes().')
        #         try:
        #             hp.updatePoolTeamServiceTimes(batch=True)
        #         except Exception as e:
        #             logger.error(f'Exception in call to hp.updatePoolTeamServiceTimes() returned. \nException: {repr(e)}')
        #         logger.info('Call to hp.updatePoolTeamServiceTimes() returned.')

        #         logger.info('Calling hp.updateFullTeamPlayerScoring().')
        #         try:
        #             hp.updateFullTeamPlayerScoring(batch=True)
        #         except Exception as e:
        #             logger.error(f'Exception in call to hp.updateFullTeamPlayerScoring() returned. \nException: {repr(e)}')
        #         logger.info('Call to hp.updateFullTeamPlayerScoring() returned.')

        logger.debug('Formatting & sending "Daily VFHL Scheduled Task" notification email...')
        caption = f'Task Scheduler: "Daily VFHL Scheduled Task" notification'
        recipients = ['rsuthers@cogeco.ca']
        email_sent = hp.formatAndSendEmail(html_tables=[], message='"Daily VFHL Scheduled Task" notification', recipients=recipients, subject=caption, show_sent_msg=False, batch=True, dialog=None)
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
