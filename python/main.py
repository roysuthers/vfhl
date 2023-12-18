from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from pathlib import Path

from get_player_data import rank_players
from fantrax import scrape_draft_picks

app = Flask(__name__, static_folder='./json')
CORS(app)

# Constant
JSON_FOLDER = Path('./json')

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def hello():
        return 'Hello, World!'

    return app

@app.route('/player-data')
def player_data():
    """Return the player data as a JSON object based on the request arguments."""

    season_or_date_radios = request.args.get('seasonOrDateRadios')
    from_season = request.args.get('fromSeason')
    to_season = request.args.get('toSeason')
    from_date = request.args.get('fromDate')
    to_date = request.args.get('toDate')
    game_type = request.args.get('gameType')
    stat_type = request.args.get('statType')
    pool_id = request.args.get('poolID')
    projection_source = request.args.get('projectionSource')

    player_data = rank_players(season_or_date_radios, from_season, to_season, from_date, to_date, pool_id, game_type, stat_type, projection_source)
    if player_data is None:
        return jsonify({})

    ##########################################################################################################
    # Upon returning to jquery datatables, if getPlayerData(seasonOrDateRadios, function(playerData) {...} does call back,
    # it's likely because some stats_data columns have np.nan values, which don't jasonify.
    ##########################################################################################################

    return jsonify(player_data).get_json()

def generate_file_name(season_or_date_radios: str, from_season: str, to_season: str, from_date: str, to_date: str, game_type: str, projection_source: str) -> str:
    """Generate a file name based on the arguments."""

    if season_or_date_radios == 'date':
        file_name = f"player_data_from_{from_date}_to_{to_date}_for_{from_season}{game_type}_to_{to_season}{game_type}_seasons"

    else:
        if game_type == 'Prj':
            file_name = f"player_data_for_{from_season}{game_type}_to_{to_season}{game_type}-{projection_source}_seasons"
        else:
            file_name = f"player_data_for_{from_season}{game_type}_to_{to_season}{game_type}_seasons"

    return file_name

@app.route('/draft-order')
def draft_order():
    """Returns the draft order data as JSON."""

    file_path = JSON_FOLDER / "draft_picks.json"

   # Check if draft_picks.json file exists
    try:
        # Try to open and read the file
        with open(file_path, 'r') as f:
            # Load the data from file
            draft_picks = json.load(f)

    except FileNotFoundError:
        # If the file does not exist, scrape the data and save it to the file
        draft_picks = scrape_draft_picks()
        with open(file_path, 'w') as f:
            json.dump(draft_picks, f)

    # Return the data as JSON
    return jsonify(draft_picks)

if __name__ == '__main__':

    app.run()
