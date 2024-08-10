import json
import os
import pandas as pd
import re
import sqlite3
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from io import StringIO
from pathlib import Path

from get_player_data import rank_players, calc_z_scores, min_cat, max_cat, mean_cat
from fantrax import scrape_draft_picks
from utils import get_db_connection, process_dict


def create_app():
    # app = Flask(__name__)
    app = Flask(__name__, static_folder='./json')
    CORS(app)

    @app.route('/player-data')
    def player_data():
        """Return the player data as a JSON object based on the request arguments."""

        generation_type = request.args.get('generationType')

        z_points = True if request.args.get('points') == 'true' else False
        z_goals = True if request.args.get('goals') == 'true' else False
        z_assists = True if request.args.get('assists') == 'true' else False
        z_points_pp = True if request.args.get('powerplayPoints') == 'true' else False
        z_shots = True if request.args.get('shotsOnGoal') == 'true' else False
        z_blocked = True if request.args.get('blockedShots') == 'true' else False
        z_hits = True if request.args.get('hits') == 'true' else False
        z_takeaways = True if request.args.get('takeaways') == 'true' else False
        z_pim = True if request.args.get('penaltyMinutes') == 'true' else False
        z_wins = True if request.args.get('wins') == 'true' else False
        z_saves = True if request.args.get('saves') == 'true' else False
        z_gaa = True if request.args.get('gaa') == 'true' else False
        z_save_percent = True if request.args.get('savePercent') == 'true' else False

        season_or_date_radios = request.args.get('seasonOrDateRadios')
        from_season = request.args.get('fromSeason')
        to_season = request.args.get('toSeason')
        from_date = request.args.get('fromDate')
        to_date = request.args.get('toDate')
        game_type = request.args.get('gameType')
        stat_type = request.args.get('statType')
        ewma_span = int(request.args.get('ewmaSpan'))
        pool_id = request.args.get('poolID')
        projection_source = request.args.get('projectionSource')
        positional_scoring = True if request.args.get('positionalScoring') == 'true' else False

        # Create a list with the variable names that correspond to False values
        categories_to_exclude = [var_name if var_name != 'z_save_percent' else 'z_save%' for var_name, var_value in locals().items() if isinstance(var_value, bool) and not var_value and var_name.startswith('z_')]


        player_data = rank_players(generation_type, season_or_date_radios, from_season, to_season, from_date, to_date, pool_id, game_type, stat_type, ewma_span, projection_source, categories_to_exclude, positional_scoring)
        if player_data is None:
            return jsonify({})

        ##########################################################################################################
        # Upon returning to jquery datatables, if getPlayerData(seasonOrDateRadios, function(playerData) {...} does call back,
        # it's likely because some stats_data columns have np.nan values, which don't jasonify.
        ##########################################################################################################

        return jsonify(player_data).get_json()

    @app.route('/draft-order')
    def draft_order():
        """Returns the draft order data as JSON."""

        pool_id = request.args.get('poolID')

        ###################################################################
        # Create the absolute path to the parent directory
        parent_dir = os.getcwd()
        json_folder = os.path.join(parent_dir, 'json')
        file_path = os.path.join(json_folder, 'draft_picks.json')

        # Check if draft_picks.json file exists
        try:
            # Try to open and read the file
            with open(file_path, 'r') as f:
                # Load the data from file
                draft_picks = json.load(f)

        except FileNotFoundError:
            # If the file does not exist, scrape the data and save it to the file
            draft_picks = scrape_draft_picks(pool_id)
            if len(draft_picks) == 0:
                # raise Exception('main::draft_order(): No draft picks scraped.')
                return

            with open(file_path, 'w') as f:
                json.dump(draft_picks, f)

        # Return the data as JSON
        return jsonify(draft_picks)

    @app.route('/draft-board')
    def draft_board():
        """Writes the draft board to the database."""

        try:
            ret_val = jsonify({'status': 'success'})

            data = request.args.get('draft_board')
            projection_source = request.args.get('projectionSource')
            positional_scoring = 'Yes' if request.args.get('positionalScoring') == 'true' else 'No'

            # Create a DataFrame
            df = pd.read_json(StringIO(data))

            with get_db_connection() as connection:
                cursor = connection.cursor()
                overall_pick = 0
                for index, row in df.iterrows():
                    # Skip every other row, starting with the second row
                    if index % 2 != 0:
                        round_num = row['Rnd']
                        for col in df.columns[1:]:
                            player_info = row[col]
                            if player_info:
                                match = re.match(r'(.+?) \((.+?)/(.+?)\)', player_info)
                                if match:
                                    player_name, pos, team = match.groups()
                                    overall_pick += 1
                                    cursor.execute('''
                                    INSERT INTO DraftSimulations (player_name, pos, team, projection_source, positional_scoring, round, overall_pick)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ''', (player_name, pos, team, projection_source, positional_scoring, round_num, overall_pick))
                cursor.close()

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            ret_val = jsonify({f'status': 'error: {msg}'})

        return ret_val

    return app

if __name__ == '__main__':

    app = create_app()
    app.run()
