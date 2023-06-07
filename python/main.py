from flask import Flask, request, jsonify
from flask_cors import CORS

from get_player_data import rank_players
from fantrax import scrape_draft_picks

app = Flask(__name__)
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

    # Call your get_player_data function with the specified parameters
    data_dict = rank_players(season_or_date_radios, from_season, to_season, from_date, to_date, pool_id, game_type, stat_type)

    # Return the player data as JSON
    return jsonify(data_dict).get_json()

@app.route('/draft-order')
def draft_order():

    data_dict = scrape_draft_picks()

    # Return the data as JSON
    return jsonify(data_dict).get_json()

if __name__ == '__main__':
    app.run()
