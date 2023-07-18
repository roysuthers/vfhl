from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

from get_player_data import rank_players
from fantrax import scrape_draft_picks

app = Flask(__name__, static_folder='./json')
CORS(app)

@app.route('/player-data')
def player_data():

    # Get the values for the request parameters
    season_or_date_radios = request.args.get('seasonOrDateRadios')
    from_season = request.args.get('fromSeason')
    to_season = request.args.get('toSeason')
    from_date = request.args.get('fromDate')
    to_date = request.args.get('toDate')
    game_type = request.args.get('gameType')
    stat_type = request.args.get('statType')
    pool_id = request.args.get('poolID')
    projection_source = request.args.get('projectionSource')

    if season_or_date_radios == 'date':
        file_name = 'player_data_from_{}_to_{}_for_{}{}_to_{}{}_seasons'.format(from_date.replace('"', ''), to_date.replace('"', ''), from_season, game_type, to_season, game_type)

    else:
        if game_type == 'Prj':
            file_name = f'player_data_for_{from_season}{game_type}_to_{to_season}{game_type}-{projection_source}_seasons'
        else:
            file_name = f'player_data_for_{from_season}{game_type}_to_{to_season}{game_type}_seasons'

    file_incl_path = f'./json/{file_name}.json'

   # Check if draft_picks.json file exists
    if os.path.isfile(file_incl_path):

        with open(file_incl_path, 'r') as f:
            # Load the data from file
            player_data = json.load(f)

        return player_data

    else:

        # Call your get_player_data function with the specified parameters
        player_data = rank_players(season_or_date_radios, from_season, to_season, from_date, to_date, pool_id, game_type, stat_type, projection_source)

        with open(file_incl_path, 'w') as f:
            json.dump(player_data, f)

        # Return the player data as JSON
        return jsonify(player_data).get_json()

@app.route('/draft-order')
def draft_order():

    file_incl_path = './json/draft_picks.json'

   # Check if draft_picks.json file exists
    if os.path.isfile(file_incl_path):

        with open(file_incl_path, 'r') as f:
            # Load the data from file
            draft_picks = json.load(f)

        return draft_picks

    else:

        draft_picks = scrape_draft_picks()

        with open(file_incl_path, 'w') as f:
            json.dump(draft_picks, f)

        # Return the data as JSON
        return jsonify(draft_picks).get_json()

if __name__ == '__main__':
    app.run()
