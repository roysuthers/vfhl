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

from get_player_data import aggregate_draft_simulations, rank_players, calc_z_scores, min_cat, max_cat, mean_cat
from fantrax import scrape_draft_picks
from utils import assign_player_ids, get_db_connection, process_dict


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
        #
        # The following code can help find the pd.Series elements in player_data['stats_data']
        #
        # for player in player_data['stats_data']:
        #     for item in player:
        #         if isinstance(item, pd.Series):
        #             print(f"Player: {player}, Series: {item}")
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

        ###################################################################
        # draft order
        draft_order = [
            "One Man Gang Bang", "Open Team 1", "El Paso Pirates", "Urban Legends",
            "Avovocado", "Open Team 2", "Camaro SS", "WhatA LoadOfIt", "Banshee",
            "Horse Palace 26", "CanDO Know Huang", "Fowler's Flyers", "Wheels On Meals"
        ]

        # New draft order
        new_order = [
            "One Man Gang Bang", "Open Team 1", "El Paso Pirates", "Urban Legends",
            "Avovocado", "Open Team 2", "Camaro SS", "WhatA LoadOfIt", "Banshee",
            "Horse Palace 26", "CanDO Know Huang", "Fowler's Flyers", "Wheels On Meals"
        ]

        # Create a dictionary to map manager to their original pick number
        original_pick_number = {name: index for index, name in enumerate(draft_order)}

        # Create a table representation of the draft list
        table = [[None for _ in range(13)] for _ in range(12)]
        for entry in draft_picks:
            round_num = entry["draft_round"] - 1
            pick_num = entry["round_pick"] - 1
            table[round_num][pick_num] = entry

        # Rearrange the columns based on the new order
        rearranged_table = [[None for _ in range(13)] for _ in range(12)]
        for i, manager in enumerate(new_order):
            old_pick_num = original_pick_number[manager]
            for round_num in range(12):
                rearranged_table[round_num][i] = table[round_num][old_pick_num]

        # # Reverse the order for each manager in every even-numbered round
        # for round_num in range(1, 12, 2):  # 1, 3, 5, ..., 11 (0-based index for even rounds)
        #     rearranged_table[round_num].reverse()

        # Update the draft list with new pick numbers and adjust round_pick and overall_pick
        draft_picks = []
        overall_pick = 0
        draft_round = 0
        for round_num in range(12):
            draft_round += 1
            round_pick = 0
            for pick_num in range(13):
                entry = rearranged_table[round_num][pick_num]
                if rearranged_table[round_num][pick_num]['manager'] in ('Open Team 1', 'Open Team 2'):
                    entry["draft_round"] = draft_round
                    entry["round_pick"] = 0
                    entry["overall_pick"] = 0
                else:
                    round_pick += 1
                    overall_pick += 1
                    entry["draft_round"] = draft_round
                    entry["round_pick"] = round_pick
                    entry["overall_pick"] = overall_pick
                draft_picks.append(entry)

        # Update the managers_pick_number
        manager_pick_count = {manager: 0 for manager in new_order}
        for entry in draft_picks:
            manager = entry["manager"]
            if manager in ('Open Team 1', 'Open Team 2'):
                entry["managers_pick_number"] = 0
            else:
                manager_pick_count[manager] += 1
                entry["managers_pick_number"] = manager_pick_count[manager]
        ###################################################################

        # Return the data as JSON
        return jsonify(draft_picks)

    @app.route('/draft-board')
    def draft_board():
        """Writes the draft board to the database."""

        try:
            ret_val = jsonify({'status': 'success'})

            projection_source = request.args.get('projectionSource')
            # positional_scoring = 'Yes' if request.args.get('positionalScoring') == 'true' else 'No'
            writeToDraftSimulationsTable = True if request.args.get('writeToDraftSimulationsTable') == 'true' else False
            clearDraftSimulationsTable = True if request.args.get('clearDraftSimulationsTable') == 'true' else False
            draft_board = request.args.get('draft_board')
            manager_summary_scores = request.args.get('managerSummaryScores')

            if writeToDraftSimulationsTable is True:

                # Create DataFrames
                df_draft_board = pd.read_json(StringIO(draft_board))
                df_manager_summary_scores = pd.read_json(StringIO(manager_summary_scores))

                with get_db_connection() as connection:

                    if clearDraftSimulationsTable is True:
                        connection.execute('DELETE FROM DraftSimulations')
                        connection.execute('DELETE FROM DraftSimulationsManagerScores')
                        simulation_number = 1
                    else:
                        max_simulation_number = connection.execute('SELECT MAX(simulation_number) FROM DraftSimulations').fetchone()[0]
                        if max_simulation_number is None:
                            simulation_number = 1
                        else:
                            simulation_number = max_simulation_number + 1

                    #################################################################################################################
                    # output DraftSimulations table
                    data = []
                    # Iterate through each even & odd row pair
                    for i in range(0, len(df_draft_board), 2):
                        even_row = df_draft_board.iloc[i]
                        odd_row = df_draft_board.iloc[i + 1]

                        for col in df_draft_board.columns:
                            if col == 'Rnd':
                                round_num = int(even_row[col])
                                continue
                            else:
                                manager_info = even_row[col]
                                player_info = odd_row[col]

                                match = re.match(r"^(.*?)\s*\((\d+)/(\d+)\)$", manager_info)
                                if match:
                                    manager = match.group(1)
                                    managers_pick_number = int(match.group(2))
                                    overall_pick = int(match.group(3))

                                    match = re.match(r'(.+?) \((.+?)/(.+?)\)', player_info)
                                    if match:
                                        player_name, pos, team = match.groups()

                                        data.append({
                                            'simulation_number': simulation_number,
                                            'projection_source': projection_source,
                                            'round': round_num,
                                            'overall_pick': overall_pick,
                                            'manager': manager,
                                            'managers_pick_number': managers_pick_number,
                                            'player_name': player_name,
                                            'pos': pos,
                                            'team': team
                                        })

                    # Create a DataFrame from the collected data
                    df = pd.DataFrame(data)

                    # add playre ids
                    df.insert(6, 'player_id', assign_player_ids(df=df, player_name='player_name', nhl_team='team', pos_code='pos'))

                    # Write the DataFrame to the database
                    df.to_sql('DraftSimulations', con=connection, if_exists='append', index=False)
                    #################################################################################################################

                    #################################################################################################################
                    # output DraftSimulationsManagerScores table
                    df_manager_summary_scores.insert(0, 'simulation_number', simulation_number)
                    df_manager_summary_scores.insert(1, 'projection_source', projection_source)
                    df_manager_summary_scores.insert(2, 'rank', df_manager_summary_scores['score'].rank(method='min', na_option='bottom', ascending=False))
                    df_manager_summary_scores.to_sql('DraftSimulationsManagerScores', con=connection, index=False, if_exists='append')
                    #################################################################################################################

                    # the following line is for debugging, to bypass the 'with block' code
                    ...

           # the following line is for debugging, to bypass the 'try block' code
            ...

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            ret_val = jsonify({f'status': 'error: {msg}'})

        return ret_val

    @app.route('/draft-summaries')
    def draft_summaries():
        """Writes the draft summaries to html."""

        try:
            ret_val = jsonify({'status': 'success'})

            draftProjectionSource = request.args.get('draftProjectionSource')

            with get_db_connection() as connection:

                #################################################################################################################
                # output DraftSimulations_agg table

                # read DraftSimulationsManagerScores table
                if draftProjectionSource == '':
                    df_DraftSimulations = pd.read_sql('select * from DraftSimulations', con=connection)
                else:
                    df_DraftSimulations = pd.read_sql(f'select * from DraftSimulations where projection_source="{draftProjectionSource}"', con=connection)

                df_DraftSimulations_agg = aggregate_draft_simulations(df=df_DraftSimulations)

                df_DraftSimulations_agg.to_sql('DraftSimulations_agg', con=connection, index=False, if_exists='replace')
                #################################################################################################################

                #################################################################################################################
                # output DraftSimulationsManagerScores_agg table

                # read DraftSimulationsManagerScores table
                if draftProjectionSource == '':
                    df_DraftSimulationsManagerScores = pd.read_sql('select * from DraftSimulationsManagerScores', con=connection)
                else:
                    df_DraftSimulationsManagerScores = pd.read_sql(f'select * from DraftSimulationsManagerScores where projection_source="{draftProjectionSource}"', con=connection)

                # Select only numeric columns
                columns_to_drop = ['simulation_number', 'picks', 'fCount', 'dCount', 'gCount', 'mfCount', 'mfgmCount', 'mCount', 'irCount']
                df_DraftSimulationsManagerScores.drop(columns=columns_to_drop, inplace=True)
                numeric_columns  = df_DraftSimulationsManagerScores.select_dtypes(include=['number']).columns

                # Group by 'manager' and calculate the mean for each numeric column
                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores.groupby('manager')[numeric_columns].mean().reset_index()

                # Round the mean columns to 1 decimal place
                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores_agg.round(1)

                # calculated min & max 'rank'
                min_ranks = df_DraftSimulationsManagerScores.groupby('manager')[numeric_columns].min().reset_index()
                max_ranks = df_DraftSimulationsManagerScores.groupby('manager')[numeric_columns].max().reset_index()

                # Merge min_ranks and max_ranks into df_DraftSimulationsManagerScores_agg
                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores_agg.merge(min_ranks, on='manager', suffixes=('', '_min'))
                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores_agg.merge(max_ranks, on='manager', suffixes=('', '_max'))

                # Reorder columns
                ordered_columns = ['manager']
                for col in numeric_columns:
                    ordered_columns.append(col)
                    if col + '_min' in df_DraftSimulationsManagerScores_agg.columns:
                        ordered_columns.append(col + '_min')
                    if col + '_max' in df_DraftSimulationsManagerScores_agg.columns:
                        ordered_columns.append(col + '_max')

                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores_agg[ordered_columns]

                df_DraftSimulationsManagerScores_agg = df_DraftSimulationsManagerScores_agg.sort_values(by=['rank'], ascending=True).reset_index(drop=True)

                df_DraftSimulationsManagerScores_agg.to_sql('DraftSimulationsManagerScores_agg', con=connection, index=False, if_exists='replace')
                #################################################################################################################

                ret_val = jsonify({
                    'status': 'success',
                    'draft_simulations_agg': df_DraftSimulations_agg.to_dict(orient='records'),
                    'draft_simulations_agg_columns': df_DraftSimulations_agg.columns.tolist(),
                    'draft_simulations_manager_scores_agg': df_DraftSimulationsManagerScores_agg.to_dict(orient='records'),
                    'draft_simulations_manager_scores_agg_columns': df_DraftSimulationsManagerScores_agg.columns.tolist()
                })

           # the following line is for debugging, to bypass the 'try block' code
            ...

        except Exception as e:
            msg = ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__))
            ret_val = jsonify({f'status': 'error: {msg}'})

        return ret_val

    return app

if __name__ == '__main__':

    app = create_app()
    app.run()
