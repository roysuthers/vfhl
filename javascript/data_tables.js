// heatmaps toggle
var heatmaps = true

// flag variable to track if the ColVis button was clicked
var colvisClicked = false;
var manually_hidden_columns = [];
var manually_unhidden_columns = [];

const getStatsButton = document.querySelector('#getStatsButton');

/////////////////////////////////////////////////////////////////////////////////////////
// global variables for Draft
var draft_picks;
var draft_manager;
var auto_assign_picks = false;
// global variables to include managers that have reached their position maximium limits, during auto assignment
var f_limit_reached;
var d_limit_reached;
var g_limit_reached;
var maxCategoryValues = {'values': {}, 'zScores': {}};
/////////////////////////////////////////////////////////////////////////////////////////

var fOffenseCategories = ['goals', 'assists', 'powerplayPoints', 'shotsOnGoal'];
var dOffenseCategories = ['points'].concat(fOffenseCategories);
var sktrPeripheralCategories = ['hits', 'blockedShots', 'takeaways', 'penaltyMinutes'];
var fAllCategories = fOffenseCategories.concat(sktrPeripheralCategories);
var dAllCategories = dOffenseCategories.concat(sktrPeripheralCategories);
var gCountCategories = ['wins', 'saves'];
var gRatioCategories = ['gaa', 'savePercent'];
var gAllCategories = gCountCategories.concat(gRatioCategories);



$(document).ready(function () {

    var seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();
    var fromSeason = $('#fromSeason').val();
    var toSeason = $('#toSeason').val();
    var fromDate = '"' + $('#fromDate').val() + '"';
    var toDate = '"' + $('#toDate').val() + '"';
    var gameType = $('#gameType').val();
    var statType = $('#statType').val();
    var poolID = $('#poolID').val();

    getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType, function(playerData) {

        updateGlobalVariables(playerData);

        if ( statType === 'Cumulative' ) {
            var data = cumulative_stats_data;
            var columns = cumulative_column_titles;
        } else if ( statType === 'Per game' ) {
            var data = per_game_stats_data;
            var columns = per_game_column_titles;
        } else if ( statType === 'Per 60 minutes' ) {
            var data = per_60_stats_data;
            var columns = per_60_column_titles;
        }

        updateColumnIndexes(columns);

        updateHeatmapColumnLists();

        var table = $('#player_stats').DataTable( {

            data: data,
            columns: columns,

            // initial table order
            order: [[z_score_idx, "desc"]],

            // disable zebra strips on alternating rows; it messes with heatmap colours
            stripeClasses: [],

            // 'col-sm-4' is "Show x page entries"
            // 'col-sm-5' is "Export to Excel", "Column Visibility", "Hide Selected Rows", & "Toggle Heatmaps"
            // 'col-sm-7' is "Showing x to y of z entries" at the top of the table
            // 'col-sm-12' is "player_stats" able
            // 'col-sm-7' is "Showing x to y of z entries" at the botton of the table
            dom: "PQ" +
                "<'row'<'col-sm-4'l>>" +
                "<'row'<'col-sm-5'B>>" +
                "<'row'<'col-sm-6'ip>>" +
                "<'row'<'col-sm-12'tr>>" +
                "<'row'<'col-sm-7'ip>>",

            autoWidth: false,

            // search panes extension
            searchPanes: {
                columns: [position_idx, injury_idx, manager_idx],
                orderable: false,
                viewCount: false,
                clear: false,
                dtOpts: {
                    dom: 'ltp',
                    scrollY: '100px',
                    scrollCollapse: true,
                    searching: true,
                },
                panes: [
                    {
                        header: 'additional filters',
                        options: [
                            {
                                label: 'Rookies',
                                value: function(rowData, rowIdx) {
                                    return rowData[rookie_idx] === 'Yes';
                                },
                                className: 'rookie'
                            },
                            {
                                label: 'On watch list',
                                value: function(rowData, rowIdx) {
                                    return rowData[$('#player_stats').DataTable().column(watch_idx).index()] === 'Yes';
                                },
                                className: 'watch_list'
                            },
                            {
                                label: 'On roster',
                                value: function(rowData, rowIdx) {
                                    return rowData[$('#player_stats').DataTable().column(minors_idx).index()] === '';
                                },
                                className: 'rostered'
                            },
                            {
                                label: 'In minors',
                                value: function(rowData, rowIdx) {
                                    return rowData[$('#player_stats').DataTable().column(minors_idx).index()] === 'Yes';
                                },
                                className: 'minors'
                            },
                        ],
                        dtOpts: {
                            searching: false,
                            order: [[0, 'asc']],
                            select: 'single',
                        }
                    }
                ]
            },

            searchBuilder: {
                columns: [
                    age_idx,
                    assists_idx,
                    blk_idx,
                    breakout_threshold_idx,
                    draft_position_idx,
                    draft_round_idx,
                    fantrax_roster_status_idx,
                    gaa_idx,
                    game_today_idx,
                    games_idx,
                    goalie_starts_idx,
                    goals_idx,
                    hits_idx,
                    keeper_idx,
                    last_game_idx,
                    manager_idx,
                    minors_idx,
                    name_idx,
                    nhl_roster_status_idx,
                    picked_by_idx,
                    pim_idx,
                    points_idx,
                    position_idx,
                    pp_goals_p120_idx,
                    pp_points_p120_idx,
                    ppp_idx,
                    predraft_keeper_idx,
                    rookie_idx,
                    saves_idx,
                    saves_percent_idx,
                    sog_idx,
                    sog_pp_idx,
                    team_idx,
                    tk_idx,
                    toi_pp_percent_3gm_avg_idx,
                    toi_pp_percent_idx,
                    toi_seconds_idx,
                    watch_idx,
                    wins_idx,
                    z_assists_idx,
                    z_blk_idx,
                    z_combo_idx,
                    z_g_count_idx,
                    z_g_ratio_idx,
                    z_gaa_idx,
                    z_goals_hits_pim_idx,
                    z_goals_idx,
                    z_hits_blk_idx,
                    z_hits_idx,
                    z_hits_pim_idx,
                    z_offense_idx,
                    z_peripheral_idx,
                    z_pim_idx,
                    z_points_idx,
                    z_ppp_idx,
                    z_saves_idx,
                    z_saves_percent_idx,
                    z_score_idx,
                    z_sog_hits_blk_idx,
                    z_sog_idx,
                    z_tk_idx,
                    z_wins_idx,
                ],
            },

            columnDefs: [
                // first column, rank in group, is not orderable or searchable
                {searchable: false, orderable: false, targets: rank_in_group_idx},
                {type: 'num', targets: numeric_columns},
                {orderSequence: ['desc', 'asc'], targets: descending_columns},
                {
                    targets: fantrax_score_idx,
                    render: function(data, type, row, meta) {
                        if (type === 'sort' && auto_assign_picks === true && row[position_idx] === "G") {
                            return (data * 0.7).toFixed(2);
                        } else {
                            return data;
                        }
                    },
                },
                // default is center-align all colunns, header & body
                {className: 'dt-center', targets: '_all'},
                // left-align some colunns
                {className: 'dt-body-left', targets: [name_idx, injury_idx, injury_note_idx, manager_idx]},

                // "position" search pane
                {searchPanes: {
                    show: true,
                    options: [
                        {
                            label: 'Sktr',
                            value: function(rowData, rowIdx) {
                                return rowData[position_idx] === 'LW' ||
                                    rowData[position_idx] === 'C' ||
                                    rowData[position_idx] === 'RW' ||
                                    rowData[position_idx] === 'D';
                            }
                        },
                        {
                            label: 'F',
                            value: function(rowData, rowIdx) {
                                return rowData[position_idx] === 'LW' ||
                                    rowData[position_idx] === 'C' ||
                                    rowData[position_idx] === 'RW';
                            }
                        },
                        {
                            label: 'D',
                            value: function(rowData, rowIdx) {
                                return rowData[position_idx] === 'D';
                            }
                        },
                        {
                            label: 'G',
                            value: function(rowData, rowIdx) {
                                return rowData[position_idx] === 'G';
                            }
                        },
                    ]
                }, targets: position_idx},

                // "injury" search pane
                {searchPanes: {
                    show: true,
                    options: [
                        {
                            label: '<i>No data</i>',
                            value: function(rowData, rowIdx) {
                                return rowData[injury_idx]==='' ||
                                    (rowData[injury_idx].startsWith('DAY-TO-DAY - ') == false &&
                                    rowData[injury_idx].startsWith('IR - ') == false &&
                                    rowData[injury_idx].startsWith('IR-LT - ') == false &&
                                    rowData[injury_idx].startsWith('IR-NR - ') == false &&
                                    rowData[injury_idx].startsWith('OUT - ') == false);
                            }
                        },
                        {
                            label: 'DAY-TO-DAY',
                            value: function(rowData, rowIdx) {
                                return rowData[injury_idx].startsWith('DAY-TO-DAY - ');
                            }
                        },
                        {
                            label: 'IR',
                            value: function(rowData, rowIdx) {
                                return rowData[injury_idx].startsWith('IR - ') ||
                                    rowData[injury_idx].startsWith('IR-LT - ') ||
                                    rowData[injury_idx].startsWith('IR-NR - ');
                            }
                        },
                        {
                            label: 'OUT',
                            value: function(rowData, rowIdx) {
                                return rowData[injury_idx].startsWith('OUT - ');
                            }
                        },
                    ],
                    dtOpts: {
                        select: 'single',
                        columnDefs: [ {
                            targets: [0],
                            render: function ( data, type, row, meta ) {
                                if ( type === 'sort' ) {
                                        var injuryOptOrder;
                                        switch(data) {
                                            case '<i>No data</i>':
                                                injuryOptOrder = 1;
                                                break;
                                            case 'DAY-TO-DAY':
                                                injuryOptOrder = 2;
                                                break;
                                            case 'IR':
                                                injuryOptOrder = 3;
                                                break;
                                            case 'OUT':
                                                injuryOptOrder = 4;
                                                break;
                                        }
                                        return injuryOptOrder;
                                } else {
                                    return data;
                                }
                            }
                        } ],
                    },
                }, targets: [injury_idx]},

                // searchBuilder default conditions
                {targets: [name_idx], searchBuilder: { defaultCondition: 'contains' } },
                {targets: [games_idx, goalie_starts_idx, points_idx, goals_idx, pp_goals_p120_idx, assists_idx, ppp_idx,
                        sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx, pp_points_p120_idx,
                        toi_pp_percent_idx, toi_pp_percent_3gm_avg_idx, toi_seconds_idx,
                        z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_blk_idx, z_hits_idx, z_pim_idx, z_tk_idx,
                        z_wins_idx, z_saves_idx, z_saves_percent_idx, z_gaa_idx,
                        z_score_idx, z_offense_idx, z_peripheral_idx, z_combo_idx, z_hits_blk_idx, z_sog_hits_blk_idx, z_goals_hits_pim_idx, z_hits_pim_idx, z_g_count_idx, z_g_ratio_idx], searchBuilder: { defaultCondition: '>=' } },
                {targets: [age_idx], searchBuilder: { defaultCondition: '<=' } },
                {targets: [draft_position_idx, draft_round_idx, keeper_idx, last_game_idx, manager_idx, minors_idx, nhl_roster_status_idx, picked_by_idx, position_idx,
                        predraft_keeper_idx, rookie_idx, team_idx, watch_idx], searchBuilder: { defaultCondition: '=' } },
                {targets: [breakout_threshold_idx], searchBuilder: { defaultCondition: 'between' } },
                {targets: [game_today_idx], searchBuilder: { defaultCondition: '!null' } },

                // searchBuilder rename columns
                {targets: breakout_threshold_idx, searchBuilderTitle: 'breakout threshold' },
                {targets: points_idx, searchBuilderTitle: 'points' },
                {targets: goals_idx, searchBuilderTitle: 'goals' },
                {targets: assists_idx, searchBuilderTitle: 'assists' },
                {targets: ppp_idx, searchBuilderTitle: 'powerplay points' },
                {targets: sog_idx, searchBuilderTitle: 'shots on goal' },
                {targets: tk_idx, searchBuilderTitle: 'takeaways' },
                {targets: blk_idx, searchBuilderTitle: 'blocks' },
                {targets: wins_idx, searchBuilderTitle: 'wins' },
                {targets: saves_idx, searchBuilderTitle: 'saves' },
                {targets: saves_percent_idx, searchBuilderTitle: 'saves %' },

                // searchBuilder type columns
                {targets: breakout_threshold_idx, searchBuilderType: 'num' },

                // // custom sort for 'prj draft round' column
                // { targets: [prj_draft_round_idx], type: "custom_pdr_sort", orderSequence: ['asc']},

                // custom sort for 'fantrax adp' column
                { targets: [adp_idx], type: "custom_adp_sort", orderSequence: ['asc']},

                // custom sort for 'line' and 'line prj' column
                // custom sort for 'pp unit' and 'pp unit prj' column
                // custom sort for 'athletic z-score rank' column
                // custom sort for 'athletic z-score rank' column
                // custom sort for 'dobber z-score rank' column
                // custom sort for 'dtz z-score rank' column
                // custom sort for 'fantrax z-score rank' column
                { targets: [line_idx, pp_unit_idx, athletic_zscore_rank_idx, dfo_zscore_rank_idx, dobber_zscore_rank_idx, dtz_zscore_rank_idx, fantrax_zscore_rank_idx, draft_position_idx, draft_round_idx], type: "custom_integer_sort", orderSequence: ['asc']},

                // custom sort for ''toi pg (trend)' column
                // custom sort for 'toi even pg (trend)' column
                // custom sort for 'toi pp pg (trend)' column
                // custom sort for ''toi sh pg (trend)' column
                { targets: [toi_pg_trend_idx, toi_even_pg_trend_idx, toi_pp_pg_trend_idx, toi_sh_pg_trend_idx], type: "custom_time_delta_sort", orderSequence: ['asc', 'desc']},

                // custom sort for 'breakout threshold' column
                { targets: [breakout_threshold_idx], type: "custom_breakout_sort", orderSequence: ['asc']},

                // skater scoring category heatmaps
                { targets: sktr_category_heatmap_columns,
                    createdCell: function (td, cellData, rowData, row, col) {
                    if ( heatmaps == true && !( rowData[games_idx]== "" ) ) {
                            var statType = $('#statType').val();
                            if ( rowData[position_idx]!=='G' ) {
                                if ( col == points_idx && rowData[position_idx] === 'D' ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'points'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'pts_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'pts_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['d ' + cat],
                                        center: mean_cat['d ' + cat],
                                    });
                                } else if ( col == goals_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'goals'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'g_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'g_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == assists_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'assists'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'a_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'a_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == ppp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'points_pp'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'ppp_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'ppp_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == sog_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'shots'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'sog_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'sog_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == sog_pp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'shots_powerplay'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'sog_pp_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'sog_pp_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == tk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'takeaways'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'tk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'tk_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == hits_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'hits'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'hits_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'hits_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == blk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'blocked'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'blk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'blk_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                } else if ( col == pim_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'pim'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'pim_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'pim_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        center: mean_cat['sktr ' + cat],
                                    });
                                }
                            }
                        }
                    }
                },

                // goalie scoring category heatmaps
                { targets: goalie_category_heatmap_columns,
                    createdCell: function (td, cellData, rowData, row, col) {
                        if (heatmaps == true && !( rowData[games_idx]== "" ) ) {
                            var statType = $('#statType').val();
                            if ( rowData[position_idx]==='G' ) {
                                if ( col == wins_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'wins'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'wins_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'wins_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        center: mean_cat[cat],
                                    });
                                } else if ( col == saves_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'saves'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'saves_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'saves_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        center: mean_cat[cat],
                                    });
                                } else if ( col == gaa_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'gaa'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'gaa_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'gaa_p60'
                                    }
                                    $(td).colourize({
                                        min: min_cat[cat],
                                        max: max_cat[cat],
                                        center: mean_cat[cat],
                                        theme: 'cool-warm-reverse',
                                    });
                                } else if ( col == saves_percent_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'save%'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'save%_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'save%_p60'
                                    }
                                    $(td).colourize({
                                        min: min_cat[cat],
                                        max: max_cat[cat],
                                        center: mean_cat[cat],
                                    });
                                }
                            }
                        }
                    }
                },

                // skater scoring category z-score heatmaps
                { targets: sktr_category_z_score_heatmap_columns,
                    createdCell: function (td, cellData, rowData, row, col) {
                        if ( heatmaps == true && !( rowData[games_idx]== "" ) ) {
                            var statType = $('#statType').val();
                            if ( rowData[position_idx]!=='G' ) {
                                if ( col == z_points_idx && rowData[position_idx] === 'D' ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_points'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_pts_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_pts_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['d ' + cat],
                                        min: min_cat['d ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_goals_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_goals'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_g_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_g_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_assists_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_assists'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_a_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_a_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_ppp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_points_pp'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_ppp_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_ppp_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_sog_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_shots'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_sog_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_sog_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_tk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_takeaways'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_tk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_tk_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_hits_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_hits'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_hits_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_hits_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_blk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_blocked'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_blk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_blk_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_pim_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_pim'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_pim_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_pim_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat['sktr ' + cat],
                                        min: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                }
                            }
                        }
                    }
                },

                // goalie scoring category z-score heatmaps
                { targets: goalie_category_z_score_heatmap_columns,
                    createdCell: function (td, cellData, rowData, row, col) {
                        if (heatmaps == true && !( rowData[games_idx]== "" ) ) {
                            var statType = $('#statType').val();
                            if ( rowData[position_idx]==='G' ) {
                                if ( col == z_wins_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_wins'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_wins_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_wins_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        min: min_cat[cat],
                                        center: 0,
                                    });
                                } else if ( col == z_saves_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_saves'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_saves_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_saves_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        min: min_cat[cat],
                                        center: 0,
                                    });
                                } else if ( col == z_gaa_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_gaa'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_gaa_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_gaa_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        min: min_cat[cat],
                                        center: 0,
                                    });
                                } else if ( col == z_saves_percent_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_save%'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_save%_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_save%_p60'
                                    }
                                    $(td).colourize({
                                        max: max_cat[cat],
                                        min: min_cat[cat],
                                        center: 0,
                                    });
                                }
                            }
                        }
                    }
                },

                // z-score summary heatmaps
                { targets: z_score_summary_heatmap_columns,
                    createdCell: function (td, cellData, rowData, row, col) {
                        if ( heatmaps == true && !( rowData[games_idx]== "" ) ) {
                                var statType = $('#statType').val();
                                if ( col == z_score_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_score'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_score_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_score_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] === 'G' ? max_cat['g ' + cat]: max_cat['sktr ' + cat],
                                        min: rowData[position_idx] === 'G' ? min_cat['g ' + cat]: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( col == z_score_vorp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_score_vorp'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_score_pg_vorp'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_score_p60_vorp'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] === 'G' ? max_cat['g ' + cat]: max_cat['sktr ' + cat],
                                        min: rowData[position_idx] === 'G' ? min_cat['g ' + cat]: min_cat['sktr ' + cat],
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_offense_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_offense'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_offense_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_offense_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_offense_vorp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_offense_vorp'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_offense_pg_vorp'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_offense_p60_vorp'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_peripheral_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_peripheral'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_peripheral_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_peripheral_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_sog_hits_blk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_sog_hits_blk'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_sog_hits_blk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_sog_hits_blk_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_hits_blk_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_hits_blk'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_hits_blk_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_hits_blk_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_goals_hits_pim_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_goals_hits_pim'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_goals_hits_pim_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_goals_hits_pim_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_hits_pim_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_hits_pim'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_hits_pim_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_hits_pim_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]!=='G' && col == z_peripheral_vorp_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_peripheral_vorp'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_peripheral_pg_vorp'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_peripheral_p60_vorp'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] !== 'G' ? max_cat['sktr ' + cat] : 0,
                                        min: rowData[position_idx] !== 'G' ? min_cat['sktr ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]==='G' && col == z_g_count_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_g_count'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_g_count_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_g_count_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] === 'G' ? max_cat['g ' + cat] : 0,
                                        min: rowData[position_idx] === 'G' ? min_cat['g ' + cat] : 0,
                                        center: 0,
                                    });
                                } else if ( rowData[position_idx]==='G' && col == z_g_ratio_idx ) {
                                    if ( statType === 'Cumulative' ) {
                                        cat = 'z_g_ratio'
                                    } else if ( statType === 'Per game' ) {
                                        cat = 'z_g_ratio_pg'
                                    } else if ( statType === 'Per 60 minutes' ) {
                                        cat = 'z_g_ratio_p60'
                                    }
                                    $(td).colourize({
                                        max: rowData[position_idx] === 'G' ? max_cat['g ' + cat] : 0,
                                        min: rowData[position_idx] === 'G' ? min_cat['g ' + cat] : 0,
                                        center: 0,
                                    });
                                }
                            }
                        }
                }

            ],

            fixedHeader: true,
            fixedColumns: true,
            orderCellsTop: true,
            pagingType: 'full_numbers',

            lengthMenu: [
                [20, 50, 100, 250, 500, -1],
                ['20 per page', '50 per page', '100 per page', '250 per page', '500 per page', 'All']
            ],
            pageLength: 50,
            // use 'api' selection style; was using 'multi+shift'
            select: 'api',
            buttons: [
                {
                    extend: 'spacer',
                    style: 'bar',
                    text: ''
                },
                // 'createState',
                // 'savedStates',
                {
                    extend: 'excel',
                    text: 'Export to Excel'
                },
                {
                    extend: 'collection',
                    text: 'Column Visibility',
                    buttons: [
                        {
                            text: 'General Info',
                            popoverTitle: 'General Info Columns',
                            extend: 'colvis',
                            columns: general_info_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, general_info_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Skater Info',
                            popoverTitle: 'Skater Columns',
                            extend: 'colvis',
                            columns: sktr_info_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, sktr_info_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Goalie Info',
                            popoverTitle: 'Goalie Columns',
                            extend: 'colvis',
                            columns: goalie_info_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, goalie_info_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Skater Scoring Cats',
                            popoverTitle: 'Skater Scoring Category Columns',
                            extend: 'colvis',
                            columns: sktr_scoring_categories_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, sktr_scoring_categories_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Goalie Scoring Cats',
                            popoverTitle: 'Goalie Scoring Category Columns',
                            extend: 'colvis',
                            columns: goalie_scoring_categories_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, goalie_scoring_categories_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Skater Z-Scores',
                            popoverTitle: 'Skater Z-Score Columns',
                            extend: 'colvis',
                            columns: sktr_z_score_summary_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, sktr_z_score_summary_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Goalie Z-Scores',
                            popoverTitle: 'Goalie Z-Score Columns',
                            extend: 'colvis',
                            columns: goalie_z_score_summary_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, goalie_z_score_summary_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Skater Cat Z-Scores',
                            popoverTitle: 'Skater Category Z-Score Columns',
                            extend: 'colvis',
                            columns: sktr_z_score_categories_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, sktr_z_score_categories_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Goalie Cat Z-Scores',
                            popoverTitle: 'Goalie Category Z-Score Columns',
                            extend: 'colvis',
                            columns: goalie_z_score_categories_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, goalie_z_score_categories_column_names )
                                    }
                                }
                            ]
                        },
                        {
                            text: 'Draft Info',
                            popoverTitle: 'Draft Info Columns',
                            extend: 'colvis',
                            columns: draft_info_column_names,
                            collectionLayout: 'three-column',
                            postfixButtons: [
                                {
                                    text: 'Restore Columns',
                                    action: function (e, dt, node, config) {
                                        restoreColVisColumns( table, draft_info_column_names )
                                    }
                                }
                            ]
                        },
                    ]
                },
                {
                    text: 'Hide Selected Rows',
                    extend: 'selected',
                    action: function (e, dt, node, config) {
                        hideRows(table)
                    }
                },
                // {
                //     text: 'Restore Hidden Rows',
                //     action: function (e, dt, node, config) {
                //         showRows(table)
                //     }
                // },
                {
                    text: 'Toggle Heatmaps',
                    // extend: 'selected',
                    action: function (e, dt, node, config) {
                        toggleHeatmaps(table)
                    }
                },
            ],

            // footerCallback: function (row, data, start, end, display) {

            //     // Remove formatting to get numeric data for summation
            //     var intVal = function (i) {
            //         return typeof i === 'string' ? i.replace(/[\$,]/g, '') * 1 : typeof i === 'number' ? i : 0;
            //     };

            //     var api = this.api();

            //     // // Total over all pages
            //     // total = api
            //     //     .column(38)
            //     //     .data()
            //     //     .reduce(function (a, b) {
            //     //         return intVal(a) + intVal(b);
            //     //     }, 0);

            //     // Total D-only columns over current page
            //     var columns = scoring_categories_group;
            //     columns.forEach( function(idx) {
            //         var pageTotal = api
            //             .column(idx, { page: 'current' })
            //             .data()
            //             .reduce(function (a, b) {
            //                 // Find index of current value for accessing position value in same row
            //                 var cur_index = api.column(idx).data().indexOf(b);
            //                 if (api.column(position_column).data()[cur_index] == 'D') {
            //                     return intVal(a) + intVal(b);
            //                 } else {
            //                     return intVal(a);
            //                 }
            //             }, 0);

            //         // Update footer
            //         $('tr:eq(0) th:eq(' + idx + ')', api.table().footer()).html(pageTotal);
            //     });
            // },

            initComplete: function () {

                var table = $('#player_stats').DataTable();

                // hide columns that are to be hidden on initial display
                table.columns(initially_hidden_column_names).visible(show=false, redrawCalculations=false);

                // save current & initial previous statType (i.e., 'Cumulative')
                $('#statType').data('previous', '');
                $('#statType').data('current', $('#statType').val());
                // set current & previous "pos" searchPane selection to '' (i.e., no selection)
                $('#DataTables_Table_0').data('previous', '');
                $('#DataTables_Table_0').data('current', '');
                columnVisibility( 'stat type initialization'  );

                // set "name" as fixed column
                setFixedColumn( table );

                createManagerSummaryTable(table);

                createManagerNeedsTable();

                // Create the allPlayers array
                let allPlayers = getAllPlayers();

                // Filter out rows with no team manager
                var allAvailablePlayers = allPlayers.filter(function (row) {
                    return row['manager'] === "";
                });

                // create Category Scarcity table
                categoryScarcity = getCategoryScarcity(allAvailablePlayers);
                createCategoryScarcityTable(categoryScarcity);

                // create Category Scarcity by Z-score Range table
                categoryZScorePlayerCounts = calcCategoryScarcityByZScoreRange(allPlayers);
                createCategoryScarcityByZScoreRangeTable(categoryZScorePlayerCounts);

                // show tables
                hideSpinnerShowTables()
                $('#player_stats').DataTable().searchPanes.rebuildPane();

            },

        } );

        // // search panes
        // new $.fn.dataTable.SearchPanes(table, {});
        // table.searchPanes.container().prependTo(table.table().container());
        // table.searchPanes.resizePanes();

        // *******************************************************************
        // select searchPane options
        $('div.dtsp-searchPanes table').DataTable().on('user-select', function(e, dt, type, cell, originalEvent){
            // "DataTables_Table_0" is "pos" searchPane
            if (this.id == "DataTables_Table_0") {
                // hideTablesShowSpinner();
                // $('#DataTables_Table_0').data('previous', $('#DataTables_Table_0').data('current'));
                // save "pos" searchPane selection as "current"
                if ( $('#DataTables_Table_0').data('previous') === cell.data() ) {
                    $('#DataTables_Table_0').data('current', '');
                } else {
                    $('#DataTables_Table_0').data('current', cell.data());
                }
                columnVisibility( 'position change' );
                // hideSpinnerShowTables();
            }

        });

        // *******************************************************************
        // select rows
        $('#player_stats tbody').on('click', 'tr', function () {
            // if ($(this).hasClass('selected')) {
            //     $(this).removeClass('selected');
            // } else {
            //     table.$('tr.selected').removeClass('selected');
            //     $(this).addClass('selected');
            // }
            $(this).toggleClass('selected');
        });
        // *******************************************************************
        // remove() actually removes the rows. If you want to be able to restore
        // removed rows, maintain a list of removed rows
        // var removedRows = {};
        // $.fn.dataTable.Api.register('row().hide()', function(index) {
        // if (index && removedRows[index]) {
        //     // table.row.add($("<tr><td>1</td><td>2</td><td>3</td><td>4</td></tr>")).draw();
        //     var row = this.table().row.add(removedRows[index].html);
        //     delete removedRows[index]

        // } else {
        //     removedRows[this.index()] = { html: this.nodes().to$()[0] };
        //     this.remove()
        // }
        // return this
        // });
        // // *******************************************************************
        // // Remove selected row
        // $('#remove_selected_row').click(function () {
        //     table.row('.selected').hide().draw();
        // });
        // // // *******************************************************************
        // // $('#player_stats').on('click', 'tbody tr', function() {
        // //   table.row(this).hide().draw();
        // // })

        // $('#show_removed_rows').on('click', function() {
        //     Object.keys(removedRows).forEach(function(index) {
        //          table.row().hide(index).draw();
        //     })
        // });

        // // Hide & unhide rows
        // function hideRows(table) {
        //     let hidden_rows_count = 0;
        //     table.rows('.selected').every( function(index) {
        //         let adj_index = index - hidden_rows_count;
        //         table.row(adj_index).hide(adj_index).draw();
        //         ++hidden_rows_count;
        //     });
        // };
        // function showRows(table) {
        //     Object.keys(removedRows).forEach(function(index) {
        //         table.row(index).hide(index).draw();
        // })
        // };

        // *******************************************************************
        // custom ordering functions
        // return -1 if the first item is smaller, 0 if they are equal, and 1 if the first is greater.
        $.extend( $.fn.dataTable.ext.type.order, {
            // custom ascending & descending sorts for "prj draft round" column
            "custom_pdr_sort-asc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }

                if (val_1 == '') {
                    return 1;
                }

                if (val_2 == '') {
                    return -1;
                }

                if (val_1.includes('-')) {
                    const val_1_array = val_1.split(' - ');
                    var val_1_from = parseInt(val_1_array[0]);
                    var val_1_to = parseInt(val_1_array[1]);
                } else {
                    var val_1_from = parseInt(val_1);
                    var val_1_to = 0;
                }

                if (val_2.includes('-')) {
                    const val_2_array = val_2.split(' - ');
                    var val_2_from = parseInt(val_2_array[0]);
                    var val_2_to = parseInt(val_2_array[1]);
                } else {
                    var val_2_from = parseInt(val_2);
                    var val_2_to = 0;
                }

                if (val_1_from < val_2_from) {
                    return -1;
                }

                if (val_1_from > val_2_from) {
                    return 1;
                }

                // val_1_from == val_2_from
                if (val_1_to < val_2_to) {
                    return -1;
                }

                if (val_1_to > val_2_to) {
                    return 1;
                }

            },

            // custom ascending sort for "fantrax adp" column
            "custom_adp_sort-asc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }
                if (val_1 == '') {
                    return 1;
                }
                if (val_2 == '') {
                    return -1;
                }
                if (parseFloat(val_1) < parseFloat(val_2)) {
                    return -1;
                }
                if (parseFloat(val_1) > parseFloat(val_2)) {
                    return 1;
                }
            },

            // custom ascending sort for integer columns
            "custom_integer_sort-asc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }
                if (val_1 == '') {
                    return 1;
                }
                if (val_2 == '') {
                    return -1;
                }
                if (parseInt(val_1) < parseInt(val_2)) {
                    return -1;
                }
                if (parseInt(val_1) > parseInt(val_2)) {
                    return 1;
                }
            },

            // custom descending sort for delta time columns (e.g., toi trend)
            "custom_time_delta_sort-desc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }
                if (val_1 == '') {
                    return 1;
                }
                if (val_2 == '') {
                    return -1;
                }
                if (val_1.startsWith('-') && val_2.startsWith('+')) {
                    return 1;
                }
                if (val_1.startsWith('+') && val_2.startsWith('-')) {
                    return -1;
                }
                if (val_1.startsWith('-') && val_2.startsWith('-')) {
                    if (val_1.replace('-','') < val_2.replace('-','')) {
                        return -1;
                    } else if (val_1.replace('-','') > val_2.replace('-','')) {
                        return 1;
                    } else {
                        return 0;
                    }
                }
                if (val_1.startsWith('+') && val_2.startsWith('+')) {
                    if (val_1.replace('+','') < val_2.replace('+','')) {
                        return 1;
                    } else if (val_1.replace('-','') > val_2.replace('-','')) {
                        return -1;
                    } else {
                        return 0;
                    }
                }
            },

            // custom asscending sort for delta time columns (e.g., toi trend)
            "custom_time_delta_sort-asc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }
                if (val_1 == '') {
                    return 1;
                }
                if (val_2 == '') {
                    return -1;
                }
                if (val_1.startsWith('-') && val_2.startsWith('+')) {
                    return -1;
                }
                if (val_1.startsWith('+') && val_2.startsWith('-')) {
                    return 1;
                }
                if (val_1.startsWith('-') && val_2.startsWith('-')) {
                    if (val_1.replace('-','') < val_2.replace('-','')) {
                        return 1;
                    } else if (val_1.replace('-','') > val_2.replace('-','')) {
                        return -1;
                    } else {
                        return 0;
                    }
                }
                if (val_1.startsWith('+') && val_2.startsWith('+')) {
                    if (val_1.replace('+','') < val_2.replace('+','')) {
                        return -1;
                    } else if (val_1.replace('-','') > val_2.replace('-','')) {
                        return 1;
                    } else {
                        return 0;
                    }
                }
            },

            // custom ascending sort for "breakout threshold" column
            "custom_breakout_sort-asc": function (val_1, val_2) {

                if (val_1 == val_2) {
                    return 0;
                }
                if (val_1 == '') {
                    return 1;
                }
                if (val_2 == '') {
                    return -1;
                }

                // want to intermix -ve & +ve values, because -1 game under and -1 game over
                // imply the player is just as likely to readh his breakout (if he hasn't already)
                if (Math.abs(parseInt(val_1)) < Math.abs(parseInt(val_2))) {
                    return -1;
                }
                if (Math.abs(parseInt(val_1)) > Math.abs(parseInt(val_2))) {
                    return 1;
                }
            }

        });

        // *******************************************************************
        // Rank-in-group column using an event listener that listens for two events:
        // order.dt and search.dt.
        // These events are triggered when the user orders or searches the data in the table
        // When either of these events is triggered, the code will execute a function that selects all
        // cells in the first column of the table (column index 0) that are currently being displayed
        // (i.e., after filtering and ordering have been applied).
        // The every function is then called on these cells, which loops through each cell and updates
        // the data of each cell with an incrementing value (i++).
        // This means that after either a search or an order event, the first column of the table will
        // be updated to display a numbered list.
        table.on('order.dt search.dt', function () {
            let i = 1;

            table.cells(null, 0, { search: 'applied', order: 'applied' }).every(function (cell) {
                this.data(i++);
            });
        }).columns.adjust().draw();

        // // set "name" as fixed column
        // table.on('draw.dt column-visibility.dt', function () {

        //     // // load stats for stat type
        //     // var current_stat_type = $('#statType').data('current');
        //     // if ( current_stat_type === 'Cumulative' ) {
        //     //     var columns = cumulative_column_titles;
        //     // } else if ( current_stat_type === 'Per game' ) {
        //     //     var columns = per_game_column_titles;
        //     // } else if ( current_stat_type === 'Per 60 minutes' ) {
        //     //     var columns = per_60_column_titles;
        //     // }

        //     // // Loop through each header cell and set the text to the desired value
        //     // table.columns().every(function(index) {
        //     //     $(table.column(index).header()).text(columns[index].title);
        //     // });

        //     setFixedColumn( table );

        // });

        // the following is used to prevent table display when changing between positions; primarily G to unfiltered
        table.on('column-visibility.dt search.dt', function() {
            $('#col-sm-12').hide();
            setTimeout(function() {
                $('#col-sm-12').show();
            }, 1000);
        });

        // get the ColVis button element
        var colvisButton = document.querySelector('.buttons-collection');

        // add a click event listener to the ColVis button
        colvisButton.addEventListener('click', function () {
            // set the colvisClicked flag to true
            colvisClicked = true;
        });

        table.on('column-visibility', function (e, settings, column, state) {
            // check if the colvisClicked flag is true
            if (colvisClicked) {
                // column: index of the column whose visibility changed
                column_name =table.column(column).name() + ':name';
                // state: true if the column is now visible, false if it is now hidden
                // add your custom code here to handle the column visibility change
                if (state === false) { // not visible
                    if (manually_unhidden_columns.includes(column_name) === true) {
                        manually_unhidden_columns.pop(column_name);
                    } else {
                        if (manually_hidden_columns.includes(column_name) === false) {
                            manually_hidden_columns.push(column_name);
                        }
                    }
                } else { // visible
                    if (manually_hidden_columns.includes(column_name) === true) {
                        manually_hidden_columns.pop(column_name);
                    } else {
                        if (manually_unhidden_columns.includes(column_name) === false) {
                            manually_unhidden_columns.push(column_name);
                        }
                    }
                }
            }
        });

        // Create a Mutation Observer fpr searchBuilder input elements, to set proper font size
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.addedNodes.length > 0) {
                    // Check if any of the added nodes are input elements with both the dtsb-value and dtsb-input classes
                    mutation.addedNodes.forEach(function (node) {
                        if (node.nodeType === Node.ELEMENT_NODE && node.matches('input.dtsb-value.dtsb-input')) {
                            // Set the font size of the element
                            node.style.fontSize = '1em';
                        }
                    });
                }
            });
        });

        // Start observing the body element for child node additions
        observer.observe(document.body, { childList: true, subtree: true });

    });

})

getStatsButton.addEventListener('click', async () => {

    // show spinner & hide tables
    hideTablesShowSpinner()

    var seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();
    var fromSeason = $('#fromSeason').val();
    var toSeason = $('#toSeason').val();
    var fromDate = $('#dateControls').children()[0].value;
    var toDate = $('#dateControls').children()[1].value;
    var gameType = $('#gameType').val();
    var statType = $('#statType').val();
    var poolID = $('#poolID').val();

    getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType, function(playerData) {

        caption = updateCaption();
        let tableCaption = document.querySelector('#player_stats caption');
        tableCaption.textContent = caption;
        tableCaption = document.querySelector('#managerSummary caption');
        tableCaption.textContent = caption + ' - Manager Z-Scores';
        tableCaption = document.querySelector('#managerCategoryNeeds caption');
        tableCaption.textContent = caption + ' - Manager Needs';
        tableCaption = document.querySelector('#managerCategoryNeedsContainerCaption');
        tableCaption.textContent = caption + ' - Manager Needs';
        tableCaption = document.querySelector('#categoryScarcity caption');
        tableCaption.textContent = caption + ' - Category Scarcity';
        tableCaption = document.querySelector('#categoryScarcityByZScoreRange caption');
        tableCaption.textContent = caption + ' - Category Scarcity By Z-score Range';

        updateGlobalVariables(playerData);

        if ( statType === 'Cumulative' ) {
            var data = cumulative_stats_data;
            var columns = cumulative_column_titles;
        } else if ( statType === 'Per game' ) {
            var data = per_game_stats_data;
            var columns = per_game_column_titles;
        } else if ( statType === 'Per 60 minutes' ) {
            var data = per_60_stats_data;
            var columns = per_60_column_titles;
        }

        updateColumnIndexes(columns);

        updateHeatmapColumnLists();

        updatePlayerStatsTable(data);

        // show tables
        hideSpinnerShowTables()

    } );

})

// Add event listeners to the radio buttons to listen for changes
$('input[name="weightedScoreOpts"]').on('change', function() {

    var weightedAvailablePlayer = updatePlayerValueAndZScores();
    updateTableWithWeightedZScores(weightedAvailablePlayer);

})

// display stat type columns
$('#statType').on('change', function() {

    // save current statType (i.e., 'Cumulative')
    $('#statType').data('current', $('#statType').val());
    columnVisibility( 'stat type change' );

    // remove table data
    let table = $('#player_stats').DataTable();
    table.clear();

    // load stats for stat type
    if ( this.value === 'Cumulative' ) {
        table.rows.add(cumulative_stats_data);
    } else if ( this.value === 'Per game' ) {
        table.rows.add(per_game_stats_data);
    } else if ( this.value === 'Per 60 minutes' ) {
        table.rows.add(per_60_stats_data);
    }

    data = calcManagerSummaryData(table);
    updateManagerSummaryTable(data);

    data = calcManagerCategoryNeedsData();
    updateManagerCategoryNeedsTable(data);

   let caption = updateCaption();
    let tableCaption = document.querySelector('#player_stats caption');
    tableCaption.textContent = caption;
    tableCaption = document.querySelector('#managerSummary caption');
    tableCaption.textContent = caption + ' - Manager Z-Scores';
    tableCaption = document.querySelector('#managerCategoryNeeds caption');
    tableCaption.textContent = caption + ' - Manager Needs';
    tableCaption = document.querySelector('#managerCategoryNeedsContainerCaption');
    tableCaption.textContent = caption + ' - Manager Needs';
    tableCaption = document.querySelector('#categoryScarcity caption');
    tableCaption.textContent = caption + ' - Category Scarcity';
tableCaption = document.querySelector('#categoryScarcityByZScoreRange caption');
    tableCaption.textContent = caption + ' - Category Scarcity By Z-score Range';

    table.columns.adjust().draw();

})

$.fn.dataTable.Api.registerPlural( 'columns().names()', 'column().name()', function ( setter ) {
    return this.iterator( 'column', function ( settings, column ) {
        var col = settings.aoColumns[column];

        if ( setter !== undefined ) {
            col.sName = setter;
            return this;
        }
        else {
            return col.sName;
        }
    }, 1 );
})

// event listener to the "Weight Player Z-Scores" button
document.getElementById('startDraftButton').addEventListener('click', () => {

    $("#loadingSpinner").show();

    getDraftPicks(draft_order => {

        draft_picks = draft_order;
        draft_manager = draft_picks[0].manager;

        clearDraftColumns();

        let table = $('#player_stats').DataTable();
        data = calcManagerSummaryData(table);
        updateManagerSummaryTable(data);

        data = calcManagerCategoryNeedsData();
        updateManagerCategoryNeedsTable(data);

            // trigger click event on weightplayerZScoresButton
        document.querySelector('#weightplayerZScoresButton').dispatchEvent(new Event('click'));

        let caption = updateCaption();
        let tableCaption = document.querySelector('#managerSummary caption');
        tableCaption.textContent = caption + ' - Manager Z-Scores';
        tableCaption = document.querySelector('#managerCategoryNeeds caption');
        tableCaption.textContent = caption + ' - Manager Needs';
        tableCaption = document.querySelector('#managerCategoryNeedsContainerCaption');
        tableCaption.textContent = caption + ' - Manager Needs';
        tableCaption = document.querySelector('#categoryScarcity caption');
        tableCaption.textContent = caption + ' - Category Scarcity';
        tableCaption = document.querySelector('#categoryScarcityByZScoreRange caption');
        tableCaption.textContent = caption + ' - Category Scarcity By Z-score Range';

        document.getElementById("draftMessage").innerHTML = "Round: " + draft_picks[0].draft_round + "; Pick: " + draft_picks[0].round_pick + "; Manager: " + draft_manager;

        // hide not-useful columns
        columns_to_hide = [manager_idx, line_idx, pp_unit_idx, toi_even_pg_idx, corsi_for_percent_idx, toi_pp_pg_idx, pp_percent_idx, shooting_percent_idx, goalie_starts_idx, qualtity_starts_idx, qualtity_starts_percent_idx, really_bad_starts_idx];
        table.columns(columns_to_hide).visible(show=false, redrawCalculations=false);

        // columns to show
        columns_to_be_visible = [fantrax_score_idx, weightedZScore_idx, weightedZOffense_idx, weightedZPeripheral_idx, weightedGZCount_idx, weightedGZRatio_idx];
        table.columns(columns_to_be_visible).visible(show=true, redrawCalculations=false);

        // $('#startDraftButton').hide();
        $("#loadingSpinner").hide();
        $('#managerSummary').show();
        // $('#managerCategoryNeeds').show();
        $('#managerCategoryNeedsContainer').show();
        $('#categoryScarcityContainer').show();
        $('#draftMessage').show();
        // $('#categoryScarcityByZScoreRange').show();

        initDraftContextMenu();

    });
})

// event listener to the "Weight Player Z-Scores" button
document.getElementById('autoAssignDraftPicks').addEventListener('click', () => {

    autoAssignDraftPicks();

})

// event listener to the "Weight Player Z-Scores" button
document.getElementById('weightplayerZScoresButton').addEventListener('click', () => {

    var weightedAvailablePlayer = updatePlayerValueAndZScores();
    updateTableWithWeightedZScores(weightedAvailablePlayer);

})

// Assign manager
function assignManager(table, rowIndex, manager) {

    table.cell(rowIndex, manager_idx).data(manager);
    table.cell(rowIndex, draft_round_idx).data(draft_picks[0].draft_round);
    table.cell(rowIndex, draft_position_idx).data(draft_picks[0].round_pick);
    // table.cell(rowIndex, draft_overall_pick_idx).data(draft_picks[0].draft_round);

    data = calcManagerSummaryData(table);
    updateManagerSummaryTable(data);

    data = calcManagerCategoryNeedsData();
    updateManagerCategoryNeedsTable(data);

    draft_picks.shift();
    if (draft_picks.length > 0) {
        draft_manager = draft_picks[0].manager;
    }

    var weightedAvailablePlayer = updatePlayerValueAndZScores();
    updateTableWithWeightedZScores(weightedAvailablePlayer);

    if (draft_picks.length > 0) {
        document.getElementById("draftMessage").innerHTML = "Round: " + draft_picks[0].draft_round + "; Pick: " + draft_picks[0].round_pick + "; Manager: " + draft_manager;
        return true;
    } else {
        document.getElementById("draftMessage").innerHTML = "All rounds are completed.";
        destroyDraftContextMenu();
        return false;
    }

};

// the autoAssignDraftPick function performs one iteration of the while loop from your original code.
// After each iteration, it calls itself again using setTimeout, with a delay of 0 milliseconds.
// This allows the browser to update the page and respond to user input between each iteration.
function autoAssignDraftPick() {

    let managerSummaryData = $('#managerSummary').DataTable().data().filter(row => row['manager']===draft_manager)[0];
    let fCount = managerSummaryData['fCount'];
    let dCount = managerSummaryData['dCount'];
    let gCount = managerSummaryData['gCount'];

    var table = $('#player_stats').DataTable();

    // probably only a maximum of 12 forwards & 9 defensemen, or 9 defensement & 11 forwards, to ensure 4 goalies drafted
    if ((fCount === 11 && dCount === 9) || (fCount === 12 && dCount === 8)) {
        if (!f_limit_reached.includes(draft_manager)) {
            f_limit_reached.push(draft_manager);
        }
        if (!d_limit_reached.includes(draft_manager)) {
            d_limit_reached.push(draft_manager);
        }
        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex) {
                if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
                    return (['LW', 'C', 'RW', 'D'].includes(data[position_idx]) && f_limit_reached.includes(draft_manager) && d_limit_reached.includes(draft_manager)) ? false: true;
                }
                return true;
            }
        );
        // table.draw();
    }

    // probably only a maximum of 12 forwards
    if (fCount === 12) {
        if (!f_limit_reached.includes(draft_manager)) {
            f_limit_reached.push(draft_manager);
        }
        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex) {
                if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
                    return (['LW', 'C', 'RW'].includes(data[position_idx]) && f_limit_reached.includes(draft_manager)) ? false: true;
                }
                return true;
            }
        );
        // table.draw();
    }

    // probably only a maximum of 9 defensemen
    if (dCount === 9) {
        if (!d_limit_reached.includes(draft_manager)) {
            d_limit_reached.push(draft_manager);
        }
        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex) {
                if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
                    return (data[position_idx] === 'D' && d_limit_reached.includes(draft_manager)) ? false: true;
                }
                return true;
            }
        );
        // table.draw();
    }

    // can only a maximum of 4 goalies
    if (gCount === 4) {
        if (!g_limit_reached.includes(draft_manager)) {
            g_limit_reached.push(draft_manager);
        }
        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex) {
                if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
                    return (data[position_idx] === 'G' && g_limit_reached.includes(draft_manager)) ? false: true;
                }
                return true;
            }
        );
        // table.draw();
    }

    // Apply sort
    if (draft_manager === 'Banshee') {
        if ((fCount + dCount + gCount) <= 16) {
            table.order([weightedZOffense_idx, 'desc']);
        } else if ((fCount + dCount + gCount) <= 20) {
            table.order([weightedZPeripheral_idx, 'desc']);
        } else if ((fCount + dCount + gCount) <= 21) {
            table.order([weightedZScore_idx, 'desc']);
        } else {
            table.order([weightedGZCount_idx, 'desc']);
        }
    } else {
        table.order([fantrax_score_idx, 'desc']);
    }
    table.draw();

    // Get row indexes in filtered and sorted order
    var filteredSortedIndexes = table.rows({order: 'current', search: 'applied'}).indexes().toArray();

    // if (draft_manager === "Banshee") {
    //     // Hide the context menu
    //     // options.$menu.trigger('contextmenu:hide');
    //     $.contextMenu('hide');
    //     return;
    // }

    if (assignManager(table, filteredSortedIndexes[0], draft_manager) === false) {
        auto_assign_picks = false;
        return;
    }

    setTimeout(autoAssignDraftPick, 0);

}

// break up autoAssignDraftPicks(), a long-running operation, into smaller chunks by wrapping it and the subsequent operations with autoAssignDraftPick(),
// and then calling autoAssignDraftPick() repeatedly using setTimeout
function autoAssignDraftPicks() {

    auto_assign_picks = true; // global
    f_limit_reached = [];
    d_limit_reached = [];
    g_limit_reached = [];

    // remove rows with manager
    $.fn.dataTable.ext.search.push(
        function(settings, data, dataIndex) {
            if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
                return (data[manager_idx] === '') ? true : false;
            }
            return true;
        }
    );

    // dont' want goalies with less than 20 starts
    $.fn.dataTable.ext.search.push(
        function(settings, data, dataIndex) {
            if (settings.nTable.id === 'player_stats' && auto_assign_picks === true && data[position_idx] === 'G') {
                return (data[goalie_starts_idx] >= 20) ? true : false;
            }
            return true;
        }
    );

    autoAssignDraftPick();

}

function calcCategoryScarcityByZScoreRange(players) {

    let zScoreMinimum = 6.5;
    let zScoreMaximum = zScoreMinimum + 0.49;
    let categoryZScorePlayerCounts = [];
    while (zScoreMinimum >= 0) {

        // This code counts the number of elements in players that meet the specified conditions and stores the result in the count variable.
        // players is the array to count the elements of, zScoreMinimum and zScoreMaximum are the minimum and maximum values for the cateegory (e.g., ‘goals’)
        // within ‘categoryZScores’, and count is the resulting count of elements that meet the specified conditions.
        // The reduce method takes a callback function and an initial value as arguments.
        // The callback function takes two arguments: an accumulator (acc) and the current element (row).
        // The callback function returns the sum of the accumulator and a boolean value indicating whether the current element meets the specified conditions.
        // The initial value of the accumulator is set to 0.
        dPointsZScorePlayerCounts = players.reduce((acc, row) => acc + (row['position'] === 'D' && row['categoryZScores']['points'] >= zScoreMinimum && row['categoryZScores']['points'] < zScoreMaximum), 0);
        dPointsZScorePlayerCounts = dPointsZScorePlayerCounts === 0 ? '' : dPointsZScorePlayerCounts

        goalsZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['goals'] >= zScoreMinimum && row['categoryZScores']['goals'] < zScoreMaximum), 0);
        goalsZScorePlayerCounts = goalsZScorePlayerCounts === 0 ? '' : goalsZScorePlayerCounts

        assistsZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['assists'] >= zScoreMinimum && row['categoryZScores']['assists'] < zScoreMaximum), 0);
        assistsZScorePlayerCounts = assistsZScorePlayerCounts === 0 ? '' : assistsZScorePlayerCounts

        powerplayPointsZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['powerplayPoints'] >= zScoreMinimum && row['categoryZScores']['powerplayPoints'] < zScoreMaximum), 0);
        powerplayPointsZScorePlayerCounts = powerplayPointsZScorePlayerCounts === 0 ? '' : powerplayPointsZScorePlayerCounts

        shotsOnGoalZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['shotsOnGoal'] >= zScoreMinimum && row['categoryZScores']['shotsOnGoal'] < zScoreMaximum), 0);
        shotsOnGoalZScorePlayerCounts = shotsOnGoalZScorePlayerCounts === 0 ? '' : shotsOnGoalZScorePlayerCounts

        hitsZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['hits'] >= zScoreMinimum && row['categoryZScores']['hits'] < zScoreMaximum), 0);
        hitsZScorePlayerCounts = hitsZScorePlayerCounts === 0 ? '' : hitsZScorePlayerCounts

        blockedShotsZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['blockedShots'] >= zScoreMinimum && row['categoryZScores']['blockedShots'] < zScoreMaximum), 0);
        blockedShotsZScorePlayerCounts = blockedShotsZScorePlayerCounts === 0 ? '' : blockedShotsZScorePlayerCounts

        takeawaysZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['takeaways'] >= zScoreMinimum && row['categoryZScores']['takeaways'] < zScoreMaximum), 0);
        takeawaysZScorePlayerCounts = takeawaysZScorePlayerCounts === 0 ? '' : takeawaysZScorePlayerCounts

        penaltyMinutesZScorePlayerCounts = players.reduce((acc, row) => acc + (['LW', 'C', 'RW', 'D'].includes(row['position']) && row['categoryZScores']['penaltyMinutes'] >= zScoreMinimum && row['categoryZScores']['penaltyMinutes'] < zScoreMaximum), 0);
        penaltyMinutesZScorePlayerCounts = penaltyMinutesZScorePlayerCounts === 0 ? '' : penaltyMinutesZScorePlayerCounts

        winsZScorePlayerCounts = players.reduce((acc, row) => acc + (row['position'] === 'G' && row['categoryZScores']['wins'] >= zScoreMinimum && row['categoryZScores']['wins'] < zScoreMaximum), 0);
        winsZScorePlayerCounts = winsZScorePlayerCounts === 0 ? '' : winsZScorePlayerCounts

        savesZScorePlayerCounts = players.reduce((acc, row) => acc + (row['position'] === 'G' && row['categoryZScores']['saves'] >= zScoreMinimum && row['categoryZScores']['saves'] < zScoreMaximum), 0);
        savesZScorePlayerCounts = savesZScorePlayerCounts === 0 ? '' : savesZScorePlayerCounts

        gaaZScorePlayerCounts = players.reduce((acc, row) => acc + (row['position'] === 'G' && row['categoryZScores']['gaa'] >= zScoreMinimum && row['categoryZScores']['gaa'] < zScoreMaximum), 0);
        gaaZScorePlayerCounts = gaaZScorePlayerCounts === 0 ? '' : gaaZScorePlayerCounts

        savePercentZScorePlayerCounts = players.reduce((acc, row) => acc + (row['position'] === 'G' && row['categoryZScores']['savePercent'] >= zScoreMinimum && row['categoryZScores']['savePercent'] < zScoreMaximum), 0);
        savePercentZScorePlayerCounts = savePercentZScorePlayerCounts === 0 ? '' : savePercentZScorePlayerCounts


        if (dPointsZScorePlayerCounts > 0 || goalsZScorePlayerCounts > 0 || assistsZScorePlayerCounts > 0 || powerplayPointsZScorePlayerCounts > 0 || shotsOnGoalZScorePlayerCounts > 0 || hitsZScorePlayerCounts > 0 || blockedShotsZScorePlayerCounts > 0 || takeawaysZScorePlayerCounts > 0 || penaltyMinutesZScorePlayerCounts > 0 || winsZScorePlayerCounts > 0 || savesZScorePlayerCounts > 0 || gaaZScorePlayerCounts > 0 || savePercentZScorePlayerCounts > 0) {
            var zScoreRange = `${zScoreMinimum} - ${zScoreMaximum}`;
            // the square brackets ([]) around the zScoreRange variable tell JavaScript to use the value of the zScoreRange variable as the property name.
            // This means that the property name will be "5 - 5.49", for example, instead of "zScoreRange"
            categoryZScorePlayerCounts.push({[zScoreRange]: {'points': dPointsZScorePlayerCounts, 'goals': goalsZScorePlayerCounts, 'assists': assistsZScorePlayerCounts, 'powerplayPoints': powerplayPointsZScorePlayerCounts, 'shotsOnGoal': shotsOnGoalZScorePlayerCounts, 'hits': hitsZScorePlayerCounts, 'blockedShots': blockedShotsZScorePlayerCounts, 'takeaways': takeawaysZScorePlayerCounts, 'penaltyMinutes': penaltyMinutesZScorePlayerCounts, 'wins': winsZScorePlayerCounts, 'saves': savesZScorePlayerCounts, 'gaa': gaaZScorePlayerCounts, 'savePercent': savePercentZScorePlayerCounts, }});
        }

        zScoreMinimum -= 0.5;
        zScoreMaximum = zScoreMinimum + 0.49;
    }

    // This code calculates the totals for each category across all elements in categoryZScorePlayerCounts and stores the result in the totals variable.
    // Then, a new element is added to the end of myArray with a property named "Totals" and a value equal to the totals object.
    // The reduce method takes a callback function and an initial value as arguments.
    // The callback function takes two arguments: an accumulator (acc) and the current element (curr).
    // The callback function uses two nested forEach loops to iterate over the keys of the current element
    // and the keys of the categories object within the current element.
    // For each category, the value is added to the accumulator object, creating a new property if it doesn’t already exist.
    // The initial value of the accumulator is set to an empty object.
    let totals = categoryZScorePlayerCounts.reduce((acc, curr) => {
        Object.keys(curr).forEach(key => {
            let categories = curr[key];
            Object.keys(categories).forEach(category => {
                if (typeof categories[category] === 'number') {
                    acc[category] = (acc[category] || 0) + parseInt(categories[category]);
                } else {
                    acc[category] = 0;
                }
            });
        });
        return acc;
    }, {});

    categoryZScorePlayerCounts.push({'Totals': totals});

    return categoryZScorePlayerCounts;

}

function calcManagerCategoryNeedsData() {

    let table = $('#managerSummary').DataTable();

    // Get data from player stats table
    var data = table.data().toArray();

    let keysToRemove = ["picks", "fCount", "dCount", "gCount", "zCountG", "zOffense", "zPeripheral", "zRatioG", "zScoreG", "zScoreSktr", "zScore"];
    let newDataArray = data.map(obj => {
        let newObj = {};
        for(let key in obj) {
          if(!keysToRemove.includes(key)) { // Only copy keys not in the list of keys to remove
            newObj[key] = obj[key];
          }
        }
        return newObj;
      });

    let allPlayers = getAllPlayers();
    // Filter out rows with team manager
    var allTeamPlayers = allPlayers.filter(function (row) {
        return row['manager'] !== "";
    });
    let teamCategoryValuesAndZScores = getTeamCategoryValuesAndZScores(allTeamPlayers);

      // Loop through original data and calculate sums for each team manager
    for (var i = 0; i < newDataArray.length; i++) {

        let managerTeamCategoryValuesAndZScores = teamCategoryValuesAndZScores[newDataArray[i]['manager']];

        // get category weights represnting the manager's category needs
        let managerCategoryNeeds = getManagerCategoryNeeds(managerTeamCategoryValuesAndZScores, maxCategoryValues);

        // Team manager exists in new data, update row
        newDataArray[i].points = parseFloat(managerCategoryNeeds['points']).toFixed(2);
        newDataArray[i].goals = parseFloat(managerCategoryNeeds['goals']).toFixed(2);
        newDataArray[i].assists = parseFloat(managerCategoryNeeds['assists']).toFixed(2);
        newDataArray[i].powerplayPoints = parseFloat(managerCategoryNeeds['powerplayPoints']).toFixed(2);
        newDataArray[i].shotsOnGoal = parseFloat(managerCategoryNeeds['shotsOnGoal']).toFixed(2);
        newDataArray[i].blockedShots = parseFloat(managerCategoryNeeds['blockedShots']).toFixed(2);
        newDataArray[i].hits = parseFloat(managerCategoryNeeds['hits']).toFixed(2);
        newDataArray[i].takeaways = parseFloat(managerCategoryNeeds['takeaways']).toFixed(2);
        newDataArray[i].penaltyMinutes = parseFloat(managerCategoryNeeds['penaltyMinutes']).toFixed(2);
        newDataArray[i].wins = parseFloat(managerCategoryNeeds['wins']).toFixed(2);
        newDataArray[i].saves = parseFloat(managerCategoryNeeds['saves']).toFixed(2);
        newDataArray[i].gaa = parseFloat(managerCategoryNeeds['gaa']).toFixed(2);
        newDataArray[i].savePercent = parseFloat(managerCategoryNeeds['savePercent']).toFixed(2);
    }

    return newDataArray;

}

function calcManagerSummaryData(table) {

    // Get data from player stats table
    var originalData = table.data().toArray();

    // Filter out rows with no team manager
    var filteredData = originalData.filter(function (row) {
        return row[manager_idx] !== "";
        // return row[manager_idx] !== "" && row[keeper_idx] === 'Yes';
    });

    // Create new data source for new table
    var data = [];

    // Loop through original data and calculate sums for each team manager
    for (var i = 0; i < filteredData.length; i++) {
        var row = filteredData[i];

        var manager = row[manager_idx];

        var position = row[position_idx];

        var zScore = parseFloat(row[z_score_idx]);
        if (isNaN(zScore)) {zScore = 0;}

        var zScoreSktr = parseFloat(row[z_score_idx]);
        if (isNaN(zScoreSktr) || row[position_idx] === 'G') {zScoreSktr = 0;}

        var zOffense = parseFloat(row[z_offense_idx]);
        if (isNaN(zOffense)) {zOffense = 0;}

        var zPeripheral = parseFloat(row[z_peripheral_idx]);
        if (isNaN(zPeripheral)) {zPeripheral = 0;}

        var points = parseFloat(row[z_points_idx]);
        if (isNaN(points) || points < 0 || row[position_idx] !== 'D') {points = 0;}

        var goals = parseFloat(row[z_goals_idx]);
        if (isNaN(goals) || goals < 0) {goals = 0;}

        var assists = parseFloat(row[z_assists_idx]);
        if (isNaN(assists) || assists < 0) {assists = 0;}

        var powerplayPoints = parseFloat(row[z_ppp_idx]);
        if (isNaN(powerplayPoints) || powerplayPoints < 0) {powerplayPoints = 0;}

        var shotsOnGoal = parseFloat(row[z_sog_idx]);
        if (isNaN(shotsOnGoal) || shotsOnGoal < 0) {shotsOnGoal = 0;}

        var blockedShots = parseFloat(row[z_blk_idx]);
        if (isNaN(blockedShots) || blockedShots < 0) {blockedShots = 0;}

        var hits = parseFloat(row[z_hits_idx]);
        if (isNaN(hits) || hits < 0) {hits = 0;}

        var takeaways = parseFloat(row[z_tk_idx]);
        if (isNaN(takeaways) || takeaways < 0) {takeaways = 0;}

        var penaltyMinutes = parseFloat(row[z_pim_idx]);
        if (isNaN(penaltyMinutes) || penaltyMinutes < 0) {penaltyMinutes = 0;}

        var zScoreG = parseFloat(row[z_score_idx]);
        if (isNaN(zScoreG) || row[position_idx] !== 'G') {zScoreG = 0;}

        var zCountG = parseFloat(row[z_g_count_idx]);
        if (isNaN(zCountG) || row[position_idx] !== 'G') {zCountG = 0;}

        var zRatioG = parseFloat(row[z_g_ratio_idx]);
        if (isNaN(zRatioG) || row[position_idx] !== 'G') {zRatioG = 0;}

       var wins = parseFloat(row[z_wins_idx]);
        if (isNaN(wins) || wins < 0) {wins = 0;}

        var saves = parseFloat(row[z_saves_idx]);
        if (isNaN(saves) || saves < 0) {saves = 0;}

        var gaa = parseFloat(row[z_gaa_idx]);
        if (isNaN(gaa)) {gaa = 0;}

        var savePercent = parseFloat(row[z_saves_percent_idx]);
        if (isNaN(savePercent)) {savePercent = 0;}

        // Check if team manager already exists in new data
        var index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        if (index === -1) {
            // Team manager does not exist in new data, add new row
            data.push({
                manager: manager,
                picks: 23,
                fCount: (position !== 'G' && position !== 'D') ? 1 : 0,
                dCount: (position === 'D') ? 1 : 0,
                gCount: (position === 'G') ? 1 : 0,
                zScore: zScore,
                zScoreSktr: zScoreSktr,
                zOffense: zOffense,
                zPeripheral: zPeripheral,
                points: points,
                goals: goals,
                assists: assists,
                powerplayPoints: powerplayPoints,
                shotsOnGoal: shotsOnGoal,
                blockedShots: blockedShots,
                hits: hits,
                takeaways: takeaways,
                penaltyMinutes: penaltyMinutes,
                zScoreG: zScoreG,
                zCountG: zCountG,
                zRatioG: zRatioG,
                wins: wins,
                saves: saves,
                gaa: gaa,
                savePercent: savePercent,
            });
        } else {
            // Team manager exists in new data, update row
            data[index].fCount += (position !== 'G' && position !== 'D') ? 1 : 0;
            data[index].dCount += (position === 'D') ? 1 : 0;
            data[index].gCount += (position === 'G') ? 1 : 0;
            data[index].picks -= 1
            data[index].zScore += zScore;
            data[index].zScoreSktr += zScoreSktr;
            data[index].zOffense += zOffense;
            data[index].zPeripheral += zPeripheral;
            data[index].points += points;
            data[index].goals += goals;
            data[index].assists += assists;
            data[index].powerplayPoints += powerplayPoints;
            data[index].shotsOnGoal += shotsOnGoal;
            data[index].blockedShots += blockedShots;
            data[index].hits += hits;
            data[index].takeaways += takeaways;
            data[index].penaltyMinutes += penaltyMinutes;
            data[index].zScoreG += zScoreG;
            data[index].zCountG += zCountG;
            data[index].zRatioG += zRatioG;
            data[index].wins += wins;
            data[index].saves += saves;
            data[index].gaa += gaa;
            data[index].savePercent += savePercent;
        }
    }

    // Loop through new data and set floats to 2 decimal places
    for (var i = 0; i < data.length; i++) {
        var row = data[i];
        data[i].zScore = row.zScore.toFixed(1);
        data[i].zScoreSktr = row.zScoreSktr.toFixed(1);
        data[i].zOffense = row.zOffense.toFixed(1);
        data[i].zPeripheral = row.zPeripheral.toFixed(1);
        data[i].points = row.points.toFixed(2);
        data[i].goals = row.goals.toFixed(2);
        data[i].assists = row.assists.toFixed(2);
        data[i].powerplayPoints = row.powerplayPoints.toFixed(2);
        data[i].shotsOnGoal = row.shotsOnGoal.toFixed(2);
        data[i].blockedShots = row.blockedShots.toFixed(2);
        data[i].hits = row.hits.toFixed(2);
        data[i].takeaways = row.takeaways.toFixed(2);
        data[i].penaltyMinutes = row.penaltyMinutes.toFixed(2);
        data[i].zScoreG = row.zScoreG.toFixed(1);
        data[i].zCountG = row.zCountG.toFixed(1);
        data[i].zRatioG = row.zRatioG.toFixed(1);
        data[i].wins = row.wins.toFixed(2);
        data[i].saves = row.saves.toFixed(2);
        data[i].gaa = row.gaa.toFixed(2);
        data[i].savePercent = row.savePercent.toFixed(2);
    };

    return data;

}

function columnVisibility( trigger ) {

    // 'trigger' values: 'stat type initialization', 'stat type change', 'position change'

    var table = $('#player_stats').DataTable();

    // reset the colvisClicked flag to false
    colvisClicked = false;

    // get stat type & "pos" search pane, previous & current values
    var current_stat_type = $('#statType').data('current');
    var current_positon = $('#DataTables_Table_0').data('current');

    // get currently hidden  & visilble columns
    // table.columns().visible().toArray() gives boolean array for true\false values
    // using reduce() to get indexes for false values
    // table.columns().visible().toArray(): This gets an array of boolean values representing the visibility of each column in the table. A value of true means the column is visible, and a value of false means the column is hidden.
    // .reduce( (out, bool, index) => !bool ? out.concat(table.column(index).name() + ':name') : out, []): This uses the reduce() method to iterate over the array of boolean values and build a new array containing the names of all hidden columns. The reduce() method takes two arguments: a callback function and an initial value for the accumulator.
    // The callback function takes three arguments: out, bool, and index. out is the accumulator, which starts as an empty array and is built up over each iteration. bool is the current boolean value being processed, and index is its index in the array.
    // The callback function uses a ternary operator to check if the current boolean value is false (i.e. if the column is hidden). If it is, it concatenates the name of the column (retrieved using table.column(index).name()) to the accumulator using the concat() method. If the current boolean value is true, it simply returns the accumulator unchanged.
    // The result of the reduce() method is an array containing the names of all hidden columns in the table.
    // The final result is stored in the currently_hidden_columns variable.
    var currently_hidden_columns = table.columns().visible().toArray().reduce( (out, bool, index) => !bool ? out.concat(table.column(index).name() + ':name') : out, []);
    var currently_visible_columns = table.columns().visible().toArray().reduce( (out, bool, index) => bool ? out.concat(table.column(index).name() + ':name') : out, []);

    var all_table_columns = table.columns()[0].reduce( (out, index) => out.concat(table.column(index).name() + ':name'), []);

    var position_columns_to_hide = [];
    var position_columns_to_be_visible = [];

    var sktr_columns = sktr_scoring_categories_column_names.concat(sktr_info_column_names).concat(sktr_z_score_summary_column_names);
    var goalie_columns = goalie_scoring_categories_column_names.concat(goalie_info_column_names).concat(goalie_z_score_summary_column_names);
    var sktr_and_goalie_columns = sktr_columns.concat(goalie_columns);

    if ( trigger === 'position change') {

        // Note: There can be only one selection, because I used dtOpts on the "position" seachPane,
        //       to set selection to 'single'
        if ( current_positon === 'G' ) {
            position_columns_to_hide = position_columns_to_hide.concat(sktr_columns);
            position_columns_to_be_visible = position_columns_to_be_visible.concat(goalie_columns).filter(elem => !initially_hidden_column_names.includes(elem) && !manually_hidden_columns.includes(elem)).concat(goalie_columns.filter(elem => manually_unhidden_columns.includes(elem)));

        } else if ( current_positon === 'D' || current_positon === 'F' || current_positon === 'Sktr' ) {
            position_columns_to_hide = position_columns_to_hide.concat(goalie_columns);
            position_columns_to_be_visible = position_columns_to_be_visible.concat(sktr_columns).filter(elem => !initially_hidden_column_names.includes(elem) && !manually_hidden_columns.includes(elem)).concat(sktr_columns.filter(elem => manually_unhidden_columns.includes(elem)));

        } else {
            position_columns_to_be_visible = position_columns_to_be_visible.concat(sktr_and_goalie_columns).filter(elem => !initially_hidden_column_names.includes(elem) && !manually_hidden_columns.includes(elem)).concat(sktr_and_goalie_columns.filter(elem => manually_unhidden_columns.includes(elem)));
        }

        // don't hide position columns if already hidden
        position_columns_to_hide = position_columns_to_hide.filter(elem => !currently_hidden_columns.includes(elem));

        // don't make position columns visible if already visible
        position_columns_to_be_visible = position_columns_to_be_visible.filter(elem => !currently_visible_columns.includes(elem));

        // hide columns
        table.columns(position_columns_to_hide).visible(show=false, redrawCalculations=false);
        // unhide columns
        table.columns(position_columns_to_be_visible).visible(show=true, redrawCalculations=false);

    }

    // get current sort columns
    var sort_columns = table.order();
    for ( let sort_info of sort_columns ) {
        if ( sort_info[0] == 0 || table.column( sort_info[0] ).visible() == false ) {
            sort_columns = [z_score_idx, "desc"];
            break;
        }
    }
    // sort columns
    table.order(sort_columns);

    // save current statType as previous
    $('#statType').data('previous', current_stat_type);
    $('#DataTables_Table_0').data('previous', current_positon);

}

function createCategoryScarcityTable(data_dict) {

    // create an array of the categories and their values
    var categories = [];
    for (var key in data_dict) {
        label = key;
        if (key === 'points') {
            label = 'd-pts';
        } else if (key === 'powerplayPoints') {
            label = 'ppp';
        } else if (key === 'penaltyMinutes') {
            label = 'pim';
        } else if (key === 'savePercent') {
            label = 'save%';
        } else if (key === 'shotsOnGoal') {
            label = 'sog';
        } else if (key === 'blockedShots') {
            label = 'blk';
        }
        categories.push({category: label, value: data_dict[key].toFixed(2)});
    }

    let properties = ['points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways' ,'penaltyMinutes', 'wins', 'saves', 'gaa', 'savePercent'];

    // Initialize new DataTable with calculated data
    $('#categoryScarcity').DataTable({
        data: categories,
        dom: 't',
        columns: [
            { data: 'category', title: 'category' },
            { data: 'value', title: 'std dev' },
        ],
        order: [[1, "desc"]],
        pageLength: 13,
        columnDefs: [
            // default is center-align all colunns, header & body
            {className: 'dt-center', targets: '_all'},
            // left-align some colunns
            {className: 'dt-body-left', targets: [0]},
            {orderSequence: ['desc', 'asc'], targets: '_all'},
            // {
            //     targets: 1,
            //     render: function(data, type, row, meta) {
            //         if (type === 'display') {
            //             return data.toFixed(2);
            //         } else {
            //             return data;
            //         }
            //     },
            // },
    ],
            // heatmaps
            drawCallback: function(settings) {
                let api = this.api();
                let data = api.rows({ page: 'current' }).data().toArray();

                let values = data.map(function(row) {
                    return parseFloat(row['value']);
                });
                let min = Math.min.apply(null, values);
                let max = Math.max.apply(null, values);
                let sum = values.reduce(function(a, b) { return a + b; }, 0);
                let mean = sum / values.length;

                // update colourize with new values
                api.rows().nodes().to$().find('td').each(function(i) {
                    if (i % 2 === 1) { // only update value cells
                        $(this).colourize({
                            min: min,
                            max: max,
                            center: mean,
                            theme: "cool-warm-reverse",
                        });
                    }
                });
            },
            // initComplete: function () {
            //     var headers = '<tr><th colspan="2" style="white-space: nowrap;">' + managerData.manager + '</th></tr>';
            //     managerTable.find('thead').prepend(headers);
            // },

    });

}

function createCategoryScarcityByZScoreRangeTable(data_dict) {

    let data = data_dict.map((item) => {
        const key = Object.keys(item)[0];
        const values = Object.values(item)[0];
        return { key, ...values };
    });

    // Initialize new DataTable with calculated data
    $('#categoryScarcityByZScoreRange').DataTable({
        data: data,
        dom: 't',
        columns: [
            { data: 'key', title: 'z-score range' },
            { data: 'points', title: 'd-points' },
            { data: 'goals', title: 'goals' },
            { data: 'assists', title: 'assists' },
            { data: 'powerplayPoints', title: 'ppp' },
            { data: 'shotsOnGoal', title: 'sog' },
            { data: 'blockedShots', title: 'blk' },
            { data: 'hits', title: 'hits' },
            { data: 'takeaways', title: 'tk' },
            { data: 'penaltyMinutes', title: 'pim' },
            { data: 'wins', title: 'wins' },
            { data: 'saves', title: 'saves' },
            { data: 'gaa', title: 'gaa' },
            { data: 'savePercent', title: 'save%' },
        ],
        order: [[0, "desc"]],
        pageLength: 15,
        columnDefs: [
            // default is center-align all colunns, header & body
            {className: 'dt-center', targets: '_all'},
            // left-align some colunns
            {className: 'dt-body-left', targets: [0]},
            {orderSequence: ['desc', 'asc'], targets: '_all'},
            {orderable: false, targets: ['_all']},
        ],
        initComplete: function () {
            var headers = '<tr><th colspan="1"></th><th colspan="9">Skaters</th><th colspan="4">Goalies</th></tr>';
            $("#categoryScarcityByZScoreRange thead").prepend(headers);
        },
    });
}

function createManagerSummaryTable(table) {

    getMaxCategoryValuesAndZScores();

    data = calcManagerSummaryData(table);

    let properties = ['picks', 'fCount', 'dCount', 'gCount', 'zScore', 'zScoreSktr', 'zOffense', 'zPeripheral', 'points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways' ,'penaltyMinutes', 'zScoreG', 'zCountG', 'zRatioG', 'wins', 'saves', 'gaa', 'savePercent'];

    // Initialize new DataTable with calculated data
    $('#managerSummary').DataTable({
        data: data,
        dom: 't',
        columns: [
            { data: 'manager', title: 'manager' },
            { data: 'picks', title: 'picks' },
            { data: 'fCount', title: 'f\'s' },
            { data: 'dCount', title: 'd\'s' },
            { data: 'gCount', title: 'g\'s' },
            { data: 'zScore', title: 'z-score' },
            { data: 'zScoreSktr', title: 'z-score' },
            { data: 'zOffense', title: 'z-offense' },
            { data: 'zPeripheral', title: 'z-peripheral' },
            { data: 'points', title: 'z-pts' },
            { data: 'goals', title: 'z-g' },
            { data: 'assists', title: 'z-a' },
            { data: 'powerplayPoints', title: 'z-ppp' },
            { data: 'shotsOnGoal', title: 'z-sog' },
            { data: 'blockedShots', title: 'z-blk' },
            { data: 'hits', title: 'z-hits' },
            { data: 'takeaways', title: 'z-tk' },
            { data: 'penaltyMinutes', title: 'z-pim' },
            { data: 'zScoreG', title: 'z-score' },
            { data: 'zCountG', title: 'z-count' },
            { data: 'zRatioG', title: 'z-ratio' },
            { data: 'wins', title: 'z-w' },
            { data: 'saves', title: 'z-sv' },
            { data: 'gaa', title: 'z-gaa' },
            { data: 'savePercent', title: 'z-sv%' },
        ],
        order: [[5, "desc"]],
        pageLength: 13,
        columnDefs: [
            // default is center-align all colunns, header & body
            {className: 'dt-center', targets: '_all'},
            // left-align some colunns
            {className: 'dt-body-left', targets: [0]},
            {orderSequence: ['desc', 'asc'], targets: '_all'},
        ],
            // heatmaps
            drawCallback: function(settings) {
            let api = this.api();
            let data = api.rows({ page: 'current' }).data().toArray();

            properties.forEach(function(property, index) {
                let values = data.map(function(obj) { return parseFloat(obj[property]); });
                let min = Math.min.apply(null, values);
                let max = Math.max.apply(null, values);
                let sum = values.reduce(function(a, b) { return a + b; }, 0);
                let mean = sum / values.length;

                // update colourize with new values
                api.column(index + 1).nodes().to$().colourize({
                    min: min,
                    max: max,
                    center: mean
                });
            });
        },
        initComplete: function () {
            var headers = '<tr><th>Target Z-scores</th><th colspan="8"></th><th>points</4th><th>goals</th><th>assists</th><th>ppp</th><th>sog</th><th>hits</th><th>blocks</th><th>takeaways</th><th>pim</th><th colspan="3"></th><th>wins</th><th>saves</th><th>gaa</th><th>save%</th</tr>';
            headers = headers.replace('points', maxCategoryValues['zScores']['points'].toFixed(2))
                             .replace('goals', maxCategoryValues['zScores']['goals'].toFixed(2))
                             .replace('assists', maxCategoryValues['zScores']['assists'].toFixed(2))
                             .replace('ppp', maxCategoryValues['zScores']['powerplayPoints'].toFixed(2))
                             .replace('sog', maxCategoryValues['zScores']['shotsOnGoal'].toFixed(2))
                             .replace('hits', maxCategoryValues['zScores']['hits'].toFixed(2))
                             .replace('blocks', maxCategoryValues['zScores']['blockedShots'].toFixed(2))
                             .replace('takeaways', maxCategoryValues['zScores']['takeaways'].toFixed(2))
                             .replace('pim', maxCategoryValues['zScores']['penaltyMinutes'].toFixed(2))
                             .replace('wins', maxCategoryValues['zScores']['wins'].toFixed(2))
                             .replace('saves', maxCategoryValues['zScores']['saves'].toFixed(2))
                             .replace('gaa', maxCategoryValues['zScores']['gaa'].toFixed(2))
                             .replace('save%', maxCategoryValues['zScores']['savePercent'].toFixed(2));
            $("#managerSummary thead").prepend(headers);
            headers = '<tr><th>Std Dev</th><th colspan="8"></th><th>points</4th><th>goals</th><th>assists</th><th>ppp</th><th>sog</th><th>hits</th><th>blocks</th><th>takeaways</th><th>pim</th><th colspan="3"></th><th>wins</th><th>saves</th><th>gaa</th><th>save%</th</tr>';
            headers = headers.replace('points', parseFloat(std_cat['d points']).toFixed(2))
                             .replace('goals', parseFloat(std_cat['sktr goals']).toFixed(2))
                             .replace('assists', parseFloat(std_cat['sktr assists']).toFixed(2))
                             .replace('ppp', parseFloat(std_cat['sktr points_pp']).toFixed(2))
                             .replace('sog', parseFloat(std_cat['sktr shots']).toFixed(2))
                             .replace('hits', parseFloat(std_cat['sktr hits']).toFixed(2))
                             .replace('blocks', parseFloat(std_cat['sktr blocked']).toFixed(2))
                             .replace('takeaways', parseFloat(std_cat['sktr takeaways']).toFixed(2))
                             .replace('pim', parseFloat(std_cat['sktr pim']).toFixed(2))
                             .replace('wins', parseFloat(std_cat['wins']).toFixed(2))
                             .replace('saves', parseFloat(std_cat['saves']).toFixed(2))
                             .replace('gaa', parseFloat(std_cat['gaa']).toFixed(2))
                             .replace('save%', parseFloat(std_cat['save%']).toFixed(2));
            $("#managerSummary thead").prepend(headers);
            headers = '<tr><th>Mean</th><th colspan="8"></th><th>points</4th><th>goals</th><th>assists</th><th>ppp</th><th>sog</th><th>hits</th><th>blocks</th><th>takeaways</th><th>pim</th><th colspan="3"></th><th>wins</th><th>saves</th><th>gaa</th><th>save%</th</tr>';
            headers = headers.replace('points', parseFloat(mean_cat['d points']).toFixed(2))
                             .replace('goals', parseFloat(mean_cat['sktr goals']).toFixed(2))
                             .replace('assists', parseFloat(mean_cat['sktr assists']).toFixed(2))
                             .replace('ppp', parseFloat(mean_cat['sktr points_pp']).toFixed(2))
                             .replace('sog', parseFloat(mean_cat['sktr shots']).toFixed(2))
                             .replace('hits', parseFloat(mean_cat['sktr hits']).toFixed(2))
                             .replace('blocks', parseFloat(mean_cat['sktr blocked']).toFixed(2))
                             .replace('takeaways', parseFloat(mean_cat['sktr takeaways']).toFixed(2))
                             .replace('pim', parseFloat(mean_cat['sktr pim']).toFixed(2))
                             .replace('wins', parseFloat(mean_cat['wins']).toFixed(2))
                             .replace('saves', parseFloat(mean_cat['saves']).toFixed(2))
                             .replace('gaa', parseFloat(mean_cat['gaa']).toFixed(2))
                             .replace('save%', parseFloat(mean_cat['save%']).toFixed(2));
            $("#managerSummary thead").prepend(headers);
            headers = '<tr><th>Target Values</th><th colspan="8"></th><th>points</4th><th>goals</th><th>assists</th><th>ppp</th><th>sog</th><th>hits</th><th>blocks</th><th>takeaways</th><th>pim</th><th colspan="3"></th><th>wins</th><th>saves</th><th>gaa</th><th>save%</th</tr>';
            headers = headers.replace('points', maxCategoryValues['values']['points'])
                             .replace('goals', maxCategoryValues['values']['goals'])
                             .replace('assists', maxCategoryValues['values']['assists'])
                             .replace('ppp', maxCategoryValues['values']['powerplayPoints'])
                             .replace('sog', maxCategoryValues['values']['shotsOnGoal'])
                             .replace('hits', maxCategoryValues['values']['hits'])
                             .replace('blocks', maxCategoryValues['values']['blockedShots'])
                             .replace('takeaways', maxCategoryValues['values']['takeaways'])
                             .replace('pim', maxCategoryValues['values']['penaltyMinutes'])
                             .replace('wins', maxCategoryValues['values']['wins'])
                             .replace('saves', maxCategoryValues['values']['saves'])
                             .replace('gaa', maxCategoryValues['values']['gaa'].toFixed(2))
                             .replace('save%', maxCategoryValues['values']['savePercent'].toFixed(3));
            $("#managerSummary thead").prepend(headers);
            headers = '<tr><th colspan="6"></th><th colspan="12">Skaters</th><th colspan="7">Goalies</th>';
            $("#managerSummary thead").prepend(headers);
        },
    });

}

function createManagerNeedsTable() {

    data = calcManagerCategoryNeedsData();

    let properties = ['points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways' ,'penaltyMinutes', 'wins', 'saves', 'gaa', 'savePercent'];

    // Initialize new DataTable with calculated data
    $('#managerCategoryNeeds').DataTable({
        data: data,
        dom: 't',
        columns: [
            { data: 'manager', title: 'manager' },
            { data: 'points', title: 'd-pts' },
            { data: 'goals', title: 'g' },
            { data: 'assists', title: 'a' },
            { data: 'powerplayPoints', title: 'ppp' },
            { data: 'shotsOnGoal', title: 'sog' },
            { data: 'blockedShots', title: 'blk' },
            { data: 'hits', title: 'hits' },
            { data: 'takeaways', title: 'tk' },
            { data: 'penaltyMinutes', title: 'pim' },
            { data: 'wins', title: 'w' },
            { data: 'saves', title: 'sv' },
            { data: 'gaa', title: 'gaa' },
            { data: 'savePercent', title: 'sv%' },
        ],
        order: [[0, "asc"]],
        pageLength: 13,
        columnDefs: [
            // default is center-align all colunns, header & body
            {className: 'dt-center', targets: '_all'},
            // left-align some colunns
            {className: 'dt-body-left', targets: [0]},
            {orderSequence: ['desc', 'asc'], targets: '_all'},
            // {orderable: false, targets: [0]},
            // heatmaps
            // properties.map(function(property, index) {
            //     return {
            //         targets: index,
            //         createdCell: function(td, cellData, rowData, row, col) {
            //             // initialize colourize with default values
            //             $(rowData).colourize({
            //                 min: 0,
            //                 max: 0,
            //                 center: 0,
            //                 theme: "cool-warm-reverse",
            //             });
            //         }
            //     };
            // }),
        ],
        // heatmaps
        drawCallback: function(settings) {
            let api = this.api();
            let data = api.rows({ page: 'current' }).data().toArray();

            data.forEach(function(row, index) {
                let values = properties.map(function(property) {
                    return parseFloat(row[property]);
                });
                let min = Math.min.apply(null, values);
                let max = Math.max.apply(null, values);
                let sum = values.reduce(function(a, b) { return a + b; }, 0);
                let mean = sum / values.length;

                // update colourize with new values
                api.row(index).nodes().to$().find('td').each(function(i) {
                    if (i > 0) { // skip the manager cell
                        $(this).colourize({
                            min: min,
                            max: max,
                            center: mean,
                            theme: "cool-warm-reverse",
                        });
                    }
                });
            });
        },
        initComplete: function () {
            var headers = '<tr><th colspan="1"></th><th colspan="9">Skaters</th><th colspan="4">Goalies</th></tr>';
            $("#managerCategoryNeeds thead").prepend(headers);
        },
    });

    // create a new table for each manager, and within each table, create rows for each subcategory with the
    // corresponding values sorted in descending order
    // first, sort the data array by the manager property in ascending order
    data.sort(function(a, b) {
        if (a.manager < b.manager) {
            return -1;
        } else if (a.manager > b.manager) {
            return 1;
        } else {
            return 0;
        }
    });

    data.forEach(function(managerData) {

        // Create a new table for each manager
        var managerTable = $('<table>').css('margin', '10px').appendTo('#managerCategoryNeedsContainer');

        // set the class of the table
        managerTable.addClass('display cell-border hover compact');

        // create an array of the categories and their values
        var categories = [];
        for (var key in managerData) {
            if (key !== 'manager') {
                label = key;
                if (key === 'points') {
                    label = 'd-pts';
                } else if (key === 'powerplayPoints') {
                    label = 'ppp';
                } else if (key === 'penaltyMinutes') {
                    label = 'pim';
                } else if (key === 'savePercent') {
                    label = 'save%';
                } else if (key === 'shotsOnGoal') {
                    label = 'sog';
                } else if (key === 'blockedShots') {
                    label = 'blk';
                }
                categories.push({category: label, value: managerData[key]});
            }
        }

        // initialize the datatable
        var dataTable = managerTable.DataTable({
            data: categories,
            dom: 't',
            columns: [
                { data: 'category', title: 'category' },
                { data: 'value', title: 'value' },
            ],
            order: [[1, "desc"]],
            pageLength: 13,
            columnDefs: [
                // default is center-align all colunns, header & body
                {className: 'dt-center', targets: '_all'},
                // left-align some colunns
                {className: 'dt-body-left', targets: [0]},
                {orderSequence: ['desc', 'asc'], targets: '_all'},
            ],
            // heatmaps
            drawCallback: function(settings) {
                let api = this.api();
                let data = api.rows({ page: 'current' }).data().toArray();

                let values = data.map(function(row) {
                    return parseFloat(row['value']);
                });
                let min = Math.min.apply(null, values);
                let max = Math.max.apply(null, values);
                let sum = values.reduce(function(a, b) { return a + b; }, 0);
                let mean = sum / values.length;

                // update colourize with new values
                api.rows().nodes().to$().find('td').each(function(i) {
                    if (i % 2 === 1) { // only update value cells
                        $(this).colourize({
                            min: min,
                            max: max,
                            center: mean,
                            theme: "cool-warm-reverse",
                        });
                    }
                });
            },
            initComplete: function () {
                var headers = '<tr><th colspan="2" style="white-space: nowrap;">' + managerData.manager + '</th></tr>';
                managerTable.find('thead').prepend(headers);
            },

        });

        // store a reference to the DataTable object
        managerTable.data('CategoryNeedsTableFor', managerData.manager);

    });

}

// Function to update the table with new data
function clearDraftColumns() {

    var table = $('#player_stats').DataTable();

    // Get the data for all rows in the table
    let allPlayers = table.rows().data().toArray();

    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        var rowData = this.data();
        var id = rowData[id_idx].match(/>(\d+)</)[1]; // assuming the "id" column is the first column
        var newDataItem = allPlayers.find(function(item) {
            return item[id_idx].match(/>(\d+)</)[1] === id;
        });

        if (newDataItem) {
            // update rowData with data from newDataItem
            rowData[draft_round_idx] = '';
            rowData[draft_position_idx] = '';
            this.data(rowData);
        }
    } );

    // Filter out rows with no team manager
    var availablePlayersWithManager = allPlayers.filter(function (row) {
        return row[keeper_idx] !== 'Yes' && row[manager_idx] !== '';
    });


    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        var rowData = this.data();
        var id = rowData[id_idx].match(/>(\d+)</)[1]; // assuming the "id" column is the first column
        var newDataItem = availablePlayersWithManager.find(function(item) {
            return item[id_idx].match(/>(\d+)</)[1] === id;
        });

        if (newDataItem) {
            // update rowData with data from newDataItem
            rowData[manager_idx] = '';
            this.data(rowData);
        }
    } );

    table.columns.adjust().draw();

}

function destroyDraftContextMenu() {
    // Destroy the existing context menu
    $.contextMenu('destroy', '#player_stats td');
}

function getAllPlayers() {

        // Get the data for all rows in the table
    let allPlayerTableRows = $('#player_stats').DataTable().rows().data().toArray();

    // Create the allPlayers array
    let allPlayers = [];
    for (let i = 0; i < allPlayerTableRows.length; i++) {
        let rowData = allPlayerTableRows[i];
        let player = {
            id: rowData[id_idx].match(/>(\d+)</)[1],
            name: rowData[name_idx],
            position: rowData[position_idx],
            manager: rowData[manager_idx],
            categoryZScores: {
                points: parseFloat(rowData[z_points_idx]),
                goals: parseFloat(rowData[z_goals_idx]),
                assists: parseFloat(rowData[z_assists_idx]),
                powerplayPoints: parseFloat(rowData[z_ppp_idx]),
                shotsOnGoal: parseFloat(rowData[z_sog_idx]),
                hits: parseFloat(rowData[z_hits_idx]),
                blockedShots: parseFloat(rowData[z_blk_idx]),
                takeaways: parseFloat(rowData[z_tk_idx]),
                penaltyMinutes: parseFloat(rowData[z_pim_idx]),
                wins: parseFloat(rowData[z_wins_idx]),
                saves: parseFloat(rowData[z_saves_idx]),
                gaa: parseFloat(rowData[z_gaa_idx]),
                savePercent: parseFloat(rowData[z_saves_percent_idx]),
            },
            categoryValues: {
                points: parseFloat(rowData[points_idx]),
                goals: parseFloat(rowData[goals_idx]),
                assists: parseFloat(rowData[assists_idx]),
                powerplayPoints: parseFloat(rowData[ppp_idx]),
                shotsOnGoal: parseFloat(rowData[sog_idx]),
                hits: parseFloat(rowData[hits_idx]),
                blockedShots: parseFloat(rowData[blk_idx]),
                takeaways: parseFloat(rowData[tk_idx]),
                penaltyMinutes: parseFloat(rowData[pim_idx]),
                wins: parseFloat(rowData[wins_idx]),
                saves: parseFloat(rowData[saves_idx]),
                goalsAgainst: parseFloat(rowData[goals_against_idx]),
                toiSec: parseFloat(rowData[toi_sec_idx]),
                shotsAgainst: parseFloat(rowData[shots_against_idx]),
            }
        };

        allPlayers.push(player);

    }

    return allPlayers;

}

function getCategoryScarcity(availablePlayers) {

    // A higher standard deviation indicates that there is more variation in the z-scores for that category,
    // which means that there are fewer players that are exceptional in that category.

    let categoryScarcity = {};
    let categoryZScores = {};

    // Calculate the mean z-score for each category
    availablePlayers.forEach(player => {
        for (let category in player.categoryZScores) {
            if (!categoryZScores[category]) {
                categoryZScores[category] = [];
            }
            categoryZScores[category].push(player.categoryZScores[category]);
        }
    });
    for (let category in categoryZScores) {
        let filteredValues = categoryZScores[category].filter(value => !isNaN(value));
        let sum = filteredValues.reduce((a, b) => a + b);
        let mean = sum / filteredValues.length;
        categoryZScores[category] = { mean: mean, values: categoryZScores[category]  };
    }

    // Calculate the standard deviation of the z-scores for each category
    for (let category in categoryZScores) {
        let filteredValues = categoryZScores[category].values.filter(value => !isNaN(value));
        let squaredDiffs = filteredValues.map(value => Math.pow(value - categoryZScores[category].mean, 2));
        let avgSquaredDiff = squaredDiffs.reduce((a, b) => a + b) / squaredDiffs.length;
        let stdDev = Math.sqrt(avgSquaredDiff);
        categoryScarcity[category] = stdDev;
    }

    return categoryScarcity;
}

function getDraftPicks(callback) {

    // Set the base URL for the Flask API endpoint
    let baseUrl = 'http://localhost:5000/draft-order';

    let queryParams = '';

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + queryParams, function(draft_order) {
        // Call the callback function with the draft order
        callback(draft_order);
    });

}

function getManagerCategoryNeeds(managerTeamCategoryValuesAndZScores, maxCategoryValues) {

    let managerCategoryNeeds = {};
    for (let category in managerTeamCategoryValuesAndZScores['zScores']) {
        if (!['goalsAgaints', 'shotsAgainst', 'toiSec'].includes(category)) {
            if (managerTeamCategoryValuesAndZScores['zScores'][category] > maxCategoryValues['zScores'][category]) {
                managerCategoryNeeds[category] = 0;
            } else {
                managerCategoryNeeds[category] = 1 - (managerTeamCategoryValuesAndZScores['zScores'][category] / maxCategoryValues['zScores'][category]);
            }
        }
    }

    return managerCategoryNeeds

}

function getMaxCategoryValuesAndZScores() {

    // these are averages for last 2 seasons I have been in pool
    // should update prior to upcoming season
    maxCategoryValues['values'] = {
        'points': 315,
        'goals': 387,
        'assists': 682,
        'powerplayPoints': 329,
        'shotsOnGoal': 3361,
        'hits': 2030,
        'blockedShots': 1375,
        'takeaways': 774,
        'penaltyMinutes': 893,
        'wins': 96,
        'saves': 4585,
        'gaa': 2.43,
        'savePercent': 0.921,
    };

    maxCategoryValues['zScores'] = {
        'points': (maxCategoryValues['values']['points'] - mean_cat['d points']) / std_cat['d points'],
        'goals': (maxCategoryValues['values']['goals'] - mean_cat['sktr goals']) / std_cat['sktr goals'],
        'assists': (maxCategoryValues['values']['assists'] - mean_cat['sktr assists']) / std_cat['sktr assists'],
        'powerplayPoints': (maxCategoryValues['values']['powerplayPoints'] - mean_cat['sktr points_pp']) / std_cat['sktr points_pp'],
        'shotsOnGoal': (maxCategoryValues['values']['shotsOnGoal'] - mean_cat['sktr shots']) / std_cat['sktr shots'],
        'hits': (maxCategoryValues['values']['hits'] - mean_cat['sktr hits']) / std_cat['sktr hits'],
        'blockedShots': (maxCategoryValues['values']['blockedShots'] - mean_cat['sktr blocked']) / std_cat['sktr blocked'],
        'takeaways': (maxCategoryValues['values']['takeaways'] - mean_cat['sktr takeaways']) / std_cat['sktr takeaways'],
        'penaltyMinutes': (maxCategoryValues['values']['penaltyMinutes'] - mean_cat['sktr pim']) / std_cat['sktr pim'],
        'wins': (maxCategoryValues['values']['wins'] - mean_cat['wins']) / std_cat['wins'],
        'saves': (maxCategoryValues['values']['saves'] - mean_cat['saves']) / std_cat['saves'],
        'gaa': (mean_cat['gaa'] - maxCategoryValues['values']['gaa']) / std_cat['gaa'],
        'savePercent': (maxCategoryValues['values']['savePercent'] - mean_cat['save%']) / std_cat['save%'],
    };

}

function getTeamCategoryValuesAndZScores(teamPlayers) {

    let teamCategoryValuesAndZScores = {};

    // Sum the z-scores for each player on each team
    teamPlayers.forEach(player => {
        let manager = player.manager;
        if (!teamCategoryValuesAndZScores[manager]) {
            teamCategoryValuesAndZScores[manager] = {'values': {}, 'zScores': {}};
        }
        for (let category in player.categoryValues) {
            if (!teamCategoryValuesAndZScores[manager]['values'][category]) {
                teamCategoryValuesAndZScores[manager]['values'][category] = 0;
            }
            if (!isNaN(player.categoryValues[category])) {
                if ((category !== 'points' && category !== 'toiSec') || (category === 'points' && player.position === 'D') || (category === 'toiSec' && player.position === 'G')) {
                    teamCategoryValuesAndZScores[manager]['values'][category] += player.categoryValues[category];
                }
            }
        }
        for (let category in player.categoryZScores) {
            if (!teamCategoryValuesAndZScores[manager]['zScores'][category]) {
                teamCategoryValuesAndZScores[manager]['zScores'][category] = 0;
            }
            if (!isNaN(player.categoryZScores[category])) {
                if (includePlayerCategoryZScore(player, category) === true || (category === 'toiSec' && player.position === 'G')) {
                    teamCategoryValuesAndZScores[manager]['zScores'][category] += player.categoryZScores[category];
                }
            }
        }

        // need to calculate gaa & save %
        teamCategoryValuesAndZScores[manager]['values']['gaa'] = teamCategoryValuesAndZScores[manager]['values']['goalsAgainst'] / teamCategoryValuesAndZScores[manager]['values']['toiSec'] * 3600
        teamCategoryValuesAndZScores[manager]['values']['savePercent'] = teamCategoryValuesAndZScores[manager]['values']['saves'] / teamCategoryValuesAndZScores[manager]['values']['shotsAgainst']

        teamCategoryValuesAndZScores[manager]['zScores']['gaa'] = (mean_cat['gaa'] - teamCategoryValuesAndZScores[manager]['values']['gaa']) / std_cat['gaa']
        teamCategoryValuesAndZScores[manager]['zScores']['savePercent'] = (teamCategoryValuesAndZScores[manager]['values']['savePercent'] - mean_cat['save%']) / std_cat['save%']

    });

    return teamCategoryValuesAndZScores;
}

// Function to get player data from the Flask API endpoint
function getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType, callback) {
    // Set the base URL for the Flask API endpoint
    let baseUrl = 'http://localhost:5000/player-data';

    // Set the query parameters for the from-season, to-season, and season-type
    if (gameType === 'Regular Season') {
        gameType = 'R';
    } else { // gameType === 'Playoffs'
        gameType = 'P';
    }
    let queryParams = `?seasonOrDateRadios=${seasonOrDateRadios}&fromSeason=${fromSeason}&toSeason=${toSeason}&fromDate=${fromDate}&toDate=${toDate}&poolID=${poolID}&gameType=${gameType}&statType=${statType}`;

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + queryParams, function(playerData) {
        // Call the callback function with the player data
        callback(playerData);
    });
}

function hideSpinnerShowTables() {

    $("#loadingSpinner").hide();

    if ($('#gameType').val() === 'Regular Season') {
        // $('#managerSummary').show();
        // $('#managerSummary').DataTable().columns.adjust().draw();
        $('#startDraftButton').show();
        // $('#weightplayerZScoresButton').show();
        $('#weightedScoreOptions').show();
    }

    $('#player_stats').DataTable().columns.adjust().draw();
    $('#player_stats-div').show();
    // $('#player_stats').DataTable().searchPanes.rebuildPane();

}

function hideTablesShowSpinner() {

    $('#player_stats-div').hide();
    $('#managerSummary').hide();
    $('#managerCategoryNeeds').hide();
    $('#managerCategoryNeedsContainer').hide();
    $('#categoryScarcityContainer').hide();
    // $('#categoryScarcityByZScoreRange').hide();
    $('#startDraftButton').hide();
    // $('#weightplayerZScoresButton').hide();
    $('#draftMessage').hide();
    $("#loadingSpinner").show();
}

function initDraftContextMenu() {

    $.contextMenu({
        selector: '#player_stats td',
        build: function($trigger, e) {
            // Update the context menu options before the menu is shown
            return {
                callback: function(key, options) {
                    let table = $('#player_stats').DataTable();
                    let rowIndex = table.row(this).index();
                    switch(key) {
                    case "Draft player":
                        assignManager(table, rowIndex, draft_manager);
                        // Resume auto processing
                        if (auto_assign_picks === true) {
                            autoAssignDraftPick();
                        }
                        break;
                    default:
                        break;
                    }
                },
                items: {
                    "Draft player": {name: "Assign to " + draft_manager},
                }
            };
        }
    });
}

function includePlayerCategoryZScore(player, category) {

    let addToWeightedScores = false;
    if (player.position === 'D' && dAllCategories.includes(category) && player.categoryZScores[category] > 0) {
        addToWeightedScores = true;
    } else if (['LW', 'C', 'RW'].includes(player.position) && fAllCategories.includes(category) && player.categoryZScores[category] > 0) {
        addToWeightedScores = true;
    } else if (player.position === 'G' && gCountCategories.includes(category) && player.categoryZScores[category] > 0) {
        addToWeightedScores = true;
    } else if (player.position === 'G' && gRatioCategories.includes(category)) {
        addToWeightedScores = true;
    }

    return addToWeightedScores;

}

function restoreColVisColumns( table, columns ){
    // hide columns
    columns_to_hide = columns.filter(elem => initially_hidden_column_names.includes(elem) && manually_unhidden_columns.includes(elem));
    table.columns(columns_to_hide).visible(show=false, redrawCalculations=false);

    // unhide columns
    columns_to_be_visible = columns.filter(elem => !initially_hidden_column_names.includes(elem) && manually_hidden_columns.includes(elem));
    table.columns(columns_to_be_visible).visible(show=true, redrawCalculations=false);

}

function setFixedColumn( table ) {

    // get "name" column index
    var name_idx = table.column('name:name')[0][0];
    var name_visible_idx = name_idx;
    for (var i = 0; i < name_idx; i++) {
        if ( table.column(i).visible() === false ) {
            name_visible_idx = name_visible_idx - 1;
        }
    }
    table.fixedColumns().left( name_visible_idx + 1 );

}

function toggleHeatmaps(table) {

    heatmaps = !heatmaps;

    // remove table data
    table.clear();

    var statType = $('#statType').val();
    // load stats for stat type
    if ( statType === 'Cumulative' ) {
        table.rows.add(cumulative_stats_data);
    } else if ( statType === 'Per game' ) {
        table.rows.add(per_game_stats_data);
    } else if ( statType === 'Per 60 minutes' ) {
        table.rows.add(per_60_stats_data);
    }

    table.columns.adjust().draw();

}

function updateCaption() {

    var fromSeason = $('#fromSeason').val();
    let seasonFrom = fromSeason.substring(0, 4) + '-' + fromSeason.substring(4);

    var toSeason = $('#toSeason').val();
    let seasonTo = toSeason.substring(0, 4) + '-' + toSeason.substring(4);

    var gameType = $('#gameType').val();
    var statType = $('#statType').val();

    if (fromSeason === toSeason){
        if (gameType === 'Regular Season') {
            caption = statType + ' Statistics for the ' + seasonFrom + ' Season';
        } else {
            caption = statType + ' Statistics for the ' + seasonFrom + ' Playoffs';
        }
    } else {
        if (gameType === 'Regular Season') {
            caption = statType + ' Statistics for the ' + seasonFrom + ' to ' + seasonTo + ' Seasons';
        } else {
            caption = statType + ' Statistics for the ' + seasonFrom + ' to ' + seasonTo + ' Playoffs';
        }
    }

    return caption
}

function updateCategoryScarcityTable(data_dict) {

    let table = $('#categoryScarcity').DataTable();
    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    // create an array of the categories and their values
    var categories = [];
    for (var key in data_dict) {
        label = key;
        if (key === 'points') {
            label = 'd-pts';
        } else if (key === 'powerplayPoints') {
            label = 'ppp';
        } else if (key === 'penaltyMinutes') {
            label = 'pim';
        } else if (key === 'savePercent') {
            label = 'save%';
        } else if (key === 'shotsOnGoal') {
            label = 'sog';
        } else if (key === 'blockedShots') {
            label = 'blk';
        }
        categories.push({category: label, value: data_dict[key].toFixed(2)});
    }

    // Add the new data to the table
    table.rows.add(categories);

    // table.columns.adjust().draw();
    table.draw();

}

function updateCategoryScarcityByZScoreRangeTable(data_dict) {

    let data = data_dict.map((item) => {
        const key = Object.keys(item)[0];
        const values = Object.values(item)[0];
        return { key, ...values };
    });

   let table = $('#categoryScarcityByZScoreRange').DataTable();
    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    table.rows.add(data);

    // table.columns.adjust().draw();
    table.draw();

}

function updateColumnIndexes(columns) {

    // column indexes
    adp_idx = columns.findIndex(column => column.title === 'fantrax adp');
    age_idx = columns.findIndex(function(column) { return column.title == 'age' });
    assists_idx = columns.findIndex(column => ['a', 'a pg', 'a p60', 'a prj'].includes(column.title));
    athletic_zscore_rank_idx = columns.findIndex(column => column.title === 'athletic z-score rank');
    blk_idx = columns.findIndex(column => ['blk', 'blk pg', 'blk p60', 'blk prj'].includes(column.title));
    breakout_threshold_idx = columns.findIndex(column => column.title === 'bt');
    corsi_for_percent_idx = columns.findIndex(column => column.title === 'cf%');
    dfo_zscore_rank_idx = columns.findIndex(column => column.title === 'dfo z-score rank');
    dobber_zscore_rank_idx = columns.findIndex(column => column.title === 'dobber z-score rank');
    draft_overall_pick_idx = columns.findIndex(column => column.title === 'overall');
    draft_position_idx = columns.findIndex(column => column.title === 'draft position');
    draft_round_idx = columns.findIndex(column => column.title === 'draft round');
    dtz_zscore_rank_idx = columns.findIndex(column => column.title === 'dtz z-score rank');
    fantrax_score_idx = columns.findIndex(column => column.title === 'fantrax score');
    fantrax_roster_status_idx = columns.findIndex(column => column.title === 'fantrax roster status');
    fantrax_zscore_rank_idx = columns.findIndex(column => column.title === 'fantrax z-score rank');
    gaa_idx = columns.findIndex(column => ['gaa', 'gaa pg', 'gaa p60', 'gaa prj'].includes(column.title));
    game_today_idx = columns.findIndex(column => column.title === 'game today');
    games_idx = columns.findIndex(column => column.title === 'games');
    goalie_starts_idx = columns.findIndex(column => column.title === 'goalie starts');
    goals_idx = columns.findIndex(column => ['g', 'g pg', 'g p60', 'g prj'].includes(column.title));
    hits_idx = columns.findIndex(column => ['hits', 'hits pg', 'hits p60', 'hits prj'].includes(column.title));
    id_idx = columns.findIndex(column => column.title === 'id');
    injury_idx = columns.findIndex(column => column.title === 'injury');
    injury_note_idx = columns.findIndex(column => column.title === 'injury note');
    keeper_idx = columns.findIndex(column => column.title === 'keeper');
    last_game_idx = columns.findIndex(column => column.title === 'last game');
    line_idx = columns.findIndex(column => column.title === 'line');
    manager_idx = columns.findIndex(column => column.title === 'manager');
    minors_idx = columns.findIndex(column => column.title === 'minors');;
    name_idx = columns.findIndex(column => column.title === 'name');;
    nhl_roster_status_idx = columns.findIndex(column => column.title === 'nhl roster status');
    picked_by_idx = columns.findIndex(column => column.title === 'picked by');
    pim_idx = columns.findIndex(column => ['pim', 'pim pg', 'pim p60', 'pim prj'].includes(column.title));
    points_idx = columns.findIndex(column => ['pts', 'pts pg', 'pts p60', 'pts prj'].includes(column.title));
    position_idx = columns.findIndex(column => column.title === 'pos');
    pp_goals_p120_idx = columns.findIndex(column => column.title === 'pp g/120');
    pp_points_p120_idx = columns.findIndex(column => column.title === 'pp pts/120');
    goals_against_idx = columns.findIndex(column => column.title === 'goals against');
    pp_percent_idx = columns.findIndex(column => column.title === '%pp');
    pp_unit_idx = columns.findIndex(column => column.title === 'pp unit');
    ppp_idx = columns.findIndex(column => ['ppp', 'ppp pg', 'ppp p60', 'ppp prj'].includes(column.title));
    predraft_keeper_idx = columns.findIndex(column => column.title === 'pre-draft keeper');
    // prj_draft_round_idx = columns.findIndex(column => column.title === 'prj draft round');
    qualtity_starts_idx = columns.findIndex(column => column.title === 'qs');
    qualtity_starts_percent_idx = columns.findIndex(column => column.title === 'qs %');
    rank_in_group_idx = columns.findIndex(column => column.title === 'rank in group');
    really_bad_starts_idx = columns.findIndex(column => column.title === 'rbs');
    rookie_idx = columns.findIndex(column => column.title === 'rookie');
    saves_idx = columns.findIndex(column => ['sv', 'sv pg', 'sv p60', 'sv prj'].includes(column.title));
    saves_percent_idx = columns.findIndex(column => ['sv%', 'sv% pg', 'sv% p60', 'sv% prj'].includes(column.title));
    shooting_percent_idx = columns.findIndex(column => column.title === 'sh%');
    sog_idx = columns.findIndex(column => ['sog', 'sog pg', 'sog p60', 'sog prj'].includes(column.title));
    shots_against_idx = columns.findIndex(column => column.title === 'shots against');
    sog_pp_idx = columns.findIndex(column => column.title === 'pp sog');
    team_idx = columns.findIndex(column => column.title === 'team');
    tk_idx = columns.findIndex(column => ['tk', 'tk pg', 'tk p60', 'tk prj'].includes(column.title));
    toi_even_pg_idx = columns.findIndex(column => column.title === 'toi even pg');
    toi_even_pg_trend_idx = columns.findIndex(column => column.title === 'toi even pg (trend)');
    toi_pg_trend_idx = columns.findIndex(column => column.title === 'toi pg (trend)');
    toi_pp_percent_3gm_avg_idx = columns.findIndex(column => column.title === 'toi pp % (rolling avg)');
    toi_pp_percent_idx = columns.findIndex(column => column.title === 'toi pp %');
    toi_pp_pg_idx = columns.findIndex(column => column.title === 'toi pp pg');
    toi_pp_pg_trend_idx = columns.findIndex(column => column.title === 'toi pp pg (trend)');
    toi_seconds_idx = columns.findIndex(column => column.title === 'toi (sec)');
    toi_sh_pg_trend_idx = columns.findIndex(column => column.title === 'toi sh pg (trend)');
    toi_sec_idx = columns.findIndex(column => column.title === 'toi (sec)');
    watch_idx = columns.findIndex(column => column.title === 'watch');
    wins_idx = columns.findIndex(column => ['w', 'w pg', 'w p60', 'w prj'].includes(column.title));
    z_assists_idx = columns.findIndex(column => ['z-a', 'z-a pg', 'z-a p60', 'z-a prj'].includes(column.title));
    z_blk_idx = columns.findIndex(column => ['z-blk', 'z-blk pg', 'z-blk p60', 'z-blk prj'].includes(column.title));
    z_combo_idx = columns.findIndex(column => ['z-combo', 'z-combo pg', 'z-combo p60', 'z-combo prj'].includes(column.title));
    z_g_count_idx = columns.findIndex(column => ['z-count', 'z-count pg', 'z-count p60', 'z-count prj'].includes(column.title));
    z_g_ratio_idx = columns.findIndex(column => ['z-ratio', 'z-ratio pg', 'z-ratio p60', 'z-ratio prj'].includes(column.title));
    z_gaa_idx = columns.findIndex(column => ['z-gaa', 'z-gaa pg', 'z-gaa p60', 'z-gaa prj'].includes(column.title));
    z_goals_hits_pim_idx = columns.findIndex(column => ['z-goals +hits +penalties', 'z-goals +hits +penalties pg', 'z-goals +hits +penalties p60', 'z-goals +hits +penalties prj'].includes(column.title));
    z_goals_idx = columns.findIndex(column => ['z-g', 'z-g pg', 'z-g p60', 'z-g prj'].includes(column.title));
    z_hits_blk_idx = columns.findIndex(column => ['z-hits +blks', 'z-hits +blks pg', 'z-hits +blks p60', 'z-hits +blks prj'].includes(column.title));
    z_hits_idx = columns.findIndex(column => ['z-hits', 'z-hits pg', 'z-hits p60', 'z-hits prj'].includes(column.title));
    z_hits_pim_idx = columns.findIndex(column => ['z-hits +penalties', 'z-hits +penalties pg', 'z-hits +penalties p60', 'z-hits +penalties prj'].includes(column.title));
    z_offense_idx = columns.findIndex(column => ['z-offense', 'z-offense pg', 'z-offense p60', 'z-offense prj'].includes(column.title));
    z_offense_vorp_idx = columns.findIndex(column => ['z-offense vorp', 'z-offense vorp pg', 'z-offense vorp p60', 'z-offense vorp prj'].includes(column.title));
    z_peripheral_idx = columns.findIndex(column => ['z-peripheral', 'z-peripheral pg', 'z-peripheral p60', 'z-peripheral prj'].includes(column.title));
    z_peripheral_vorp_idx = columns.findIndex(column => ['z-peripheral vorp', 'z-peripheral vorp pg', 'z-peripheral vorp p60', 'z-peripheral vorp prj'].includes(column.title));
    z_pim_idx = columns.findIndex(column => ['z-pim', 'z-pim pg', 'z-pim p60', 'z-pim prj'].includes(column.title));
    z_points_idx = columns.findIndex(column => ['z-pts', 'z-pts pg', 'z-pts p60', 'z-pts prj'].includes(column.title));
    z_ppp_idx = columns.findIndex(column => ['z-ppp', 'z-ppp pg', 'z-ppp p60', 'z-ppp prj'].includes(column.title));
    z_saves_idx = columns.findIndex(column => ['z-sv', 'z-sv pg', 'z-sv p60', 'z-sv prj'].includes(column.title));
    z_saves_percent_idx = columns.findIndex(column => ['z-sv%', 'z-sv% pg', 'z-sv% p60', 'z-sv% prj'].includes(column.title));
    z_score_idx = columns.findIndex(column => ['z-score', 'z-score pg', 'z-score p60', 'z-score prj'].includes(column.title));
    z_score_vorp_idx = columns.findIndex(column => ['z-score vorp', 'z-score vorp pg', 'z-score vorp p60', 'z-score vorp prj'].includes(column.title));
    z_sog_hits_blk_idx = columns.findIndex(column => ['z-sog +hits +blk', 'z-sog +hits +blk pg', 'z-sog +hits +blk p60', 'z-sog +hits +blk prj'].includes(column.title));
    z_sog_idx = columns.findIndex(column => ['z-sog', 'z-sog pg', 'z-sog p60', 'z-sog prj'].includes(column.title));
    z_tk_idx = columns.findIndex(column => ['z-tk', 'z-tk pg', 'z-tk p60', 'z-tk prj'].includes(column.title));
    z_wins_idx = columns.findIndex(column => ['z-w', 'z-w pg', 'z-w p60', 'z-w prj'].includes(column.title));

    weightedZScore_idx = columns.findIndex(column => ['z-score weighted', 'z-score pg weighted', 'z-score p60 weighted'].includes(column.title));
    weightedZOffense_idx = columns.findIndex(column => ['z-offense weighted', 'z-offense pg weighted', 'z-offense p60 weighted'].includes(column.title));
    weightedZPeripheral_idx = columns.findIndex(column => ['z-peripheral weighted', 'z-peripheral pg weighted', 'z-peripheral p60 weighted'].includes(column.title));
    weightedGZCount_idx = columns.findIndex(column => ['z-count weighted', 'z-count pg weighted', 'z-count p60 weighted'].includes(column.title));
    weightedGZRatio_idx = columns.findIndex(column => ['z-ratio weighted', 'z-ratio pg weighted', 'z-ratio p60 weighted'].includes(column.title));

}

function updateGlobalVariables(playerData) {

    // caption = playerData['caption'];
    cumulative_column_titles = playerData['cumulative_column_titles'];
    per_game_column_titles = playerData['per_game_column_titles'];
    per_60_column_titles = playerData['per_60_column_titles'];
    numeric_columns = playerData['numeric_columns'];
    descending_columns = playerData['descending_columns'];

    cumulative_stats_data = playerData['cumulative_stats_data'];
    per_game_stats_data = playerData['per_game_stats_data'];
    per_60_stats_data = playerData['per_60_stats_data'];

    draft_info_column_names = playerData['draft_info_column_names'];
    general_info_column_names = playerData['general_info_column_names'];
    goalie_info_column_names = playerData['goalie_info_column_names'];
    goalie_scoring_categories_column_names = playerData['goalie_scoring_categories_column_names'];
    goalie_z_score_categories_column_names = playerData['goalie_z_score_categories_column_names'];
    goalie_z_score_summary_column_names = playerData['goalie_z_score_summary_column_names'];
    sktr_info_column_names = playerData['sktr_info_column_names'];
    sktr_scoring_categories_column_names = playerData['sktr_scoring_categories_column_names'];
    sktr_z_score_categories_column_names = playerData['sktr_z_score_categories_column_names'];
    sktr_z_score_summary_column_names = playerData['sktr_z_score_summary_column_names'];

    cumulative_stat_column_names = playerData['cumulative_stat_column_names'];
    per_game_stat_column_names = playerData['per_game_stat_column_names'];
    per_60_stat_column_names = playerData['per_60_stat_column_names'];

    initially_hidden_column_names = playerData['initially_hidden_column_names'];

    max_cat = playerData['max_cat_dict'];
    min_cat = playerData['min_cat_dict'];
    mean_cat = playerData['mean_cat_dict'];
    std_cat = playerData['std_cat_dict'];

}

// heatmap columns
function updateHeatmapColumnLists() {

    sktr_category_heatmap_columns = [points_idx, goals_idx, assists_idx, ppp_idx, sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx];
    goalie_category_heatmap_columns = [wins_idx, saves_idx, gaa_idx, saves_percent_idx];
    sktr_category_z_score_heatmap_columns = [z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_tk_idx, z_hits_idx, z_blk_idx, z_pim_idx];
    goalie_category_z_score_heatmap_columns = [z_wins_idx, z_saves_idx, z_gaa_idx, z_saves_percent_idx];
    z_score_summary_heatmap_columns = [z_score_idx, z_offense_idx, z_peripheral_idx, z_sog_hits_blk_idx, z_hits_blk_idx, z_goals_hits_pim_idx, z_hits_pim_idx, z_score_vorp_idx, z_offense_vorp_idx, z_peripheral_vorp_idx];

}

function updateManagerSummaryTable(data) {

    let table = $('#managerSummary').DataTable();
    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    table.rows.add(data);

    // table.columns.adjust().draw();
    table.draw();

}

function updateManagerCategoryNeedsTable(data) {

    let table = $('#managerCategoryNeeds').DataTable();

    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    table.rows.add(data);

    // table.columns.adjust().draw();
    table.draw();

    // get the  container element that contains all the manager tables
    var container = $('#managerCategoryNeedsContainer');

    data.forEach(function(managerData) {

        // find the table for a specific manager
        var managerCategoryNeedsTable = container.find('table').filter(function() {
            return $(this).data('CategoryNeedsTableFor') === managerData.manager;
        }).first();

        // retrieve the reference to the DataTable object
        var table = managerCategoryNeedsTable.DataTable();

        // Clear the existing data in the table
        table.clear();

        // Add the new data to the table
        // create an array of the categories and their values
        var categories = [];
        for (var key in managerData) {
            if (key !== 'manager') {
                label = key;
                if (key === 'points') {
                    label = 'd-pts';
                } else if (key === 'powerplayPoints') {
                    label = 'ppp';
                } else if (key === 'penaltyMinutes') {
                    label = 'pim';
                } else if (key === 'savePercent') {
                    label = 'save%';
                } else if (key === 'shotsOnGoal') {
                    label = 'sog';
                } else if (key === 'blockedShots') {
                    label = 'blk';
                }
                categories.push({category: label, value: managerData[key]});
            }
        }

        table.rows.add(categories);

        // table.columns.adjust().draw();
        table.draw();

    });

}

// Function to update the table with new data
function updatePlayerStatsTable(data) {

    let table = $('#player_stats').DataTable();
    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    table.rows.add(data);

    data = calcManagerSummaryData($('#player_stats').DataTable());
    updateManagerSummaryTable(data);

    data = calcManagerCategoryNeedsData();
    updateManagerCategoryNeedsTable(data);

    // Redraw the table
    table.columns.adjust().draw();

}

function updatePlayerValueAndZScores() {

    let allPlayers = getAllPlayers();

    // Filter out rows with no team manager
    var allAvailablePlayers = allPlayers.filter(function (row) {
        return row['manager'] === "";
    });

    // Filter out rows with team manager
    var allTeamPlayers = allPlayers.filter(function (row) {
        return row['manager'] !== "";
    });

    // Calculate the teamZScores and categoryScarcity objects
    let teamCategoryValuesAndZScores = getTeamCategoryValuesAndZScores(allTeamPlayers);
    let categoryScarcity = getCategoryScarcity(allAvailablePlayers);
    updateCategoryScarcityTable(categoryScarcity);

    // weight the players according to draft manager needs and category scarcity
    var weightedAvailablePlayers = updatePlayerWeights(allAvailablePlayers, teamCategoryValuesAndZScores, categoryScarcity);

    return weightedAvailablePlayers;

}

function updatePlayerWeights(availablePlayers, teamCategoryValuesAndZScores, categoryScarcity) {

    let managerTeamCategoryValuesAndZScores;
    if (draft_picks.length !== 0) {
        // Create an array of the scoring category values for manager with current daft selection
        managerTeamCategoryValuesAndZScores = teamCategoryValuesAndZScores[draft_manager];
    } else {
        managerTeamCategoryValuesAndZScores = [];
    }

    // get category weights represnting the current draft selection manager's category needs
    let managerCategoryNeeds = getManagerCategoryNeeds(managerTeamCategoryValuesAndZScores, maxCategoryValues);

    let selectedWeightedScoreOpt = $('input[name="weightedScoreOpts"]:checked').val();

    categoryZScorePlayerCounts = calcCategoryScarcityByZScoreRange(availablePlayers);
    updateCategoryScarcityByZScoreRangeTable(categoryZScorePlayerCounts);

    // Calculate the weighted z-score for each player
    availablePlayers.forEach(player => {

        let weightedZScore = 0;
        let weightedZOffense = 0;
        let weightedZPeripheral = 0;
        let weightedGZCount = 0;
        let weightedGZRatio = 0;

        for (let category in player.categoryZScores) {
            if (includePlayerCategoryZScore(player, category) === true) {
                let weightFactors = [];
                if (['need', 'both'].includes(selectedWeightedScoreOpt)) {
                    weightFactors.push(managerCategoryNeeds[category]);
                }
                if (['scarcity', 'both'].includes(selectedWeightedScoreOpt) && draft_manager === 'Banshee') {
                    weightFactors.push(categoryScarcity[category]);
                }
                catWeight = player.categoryZScores[category] * weightFactors.reduce((a, b) => a + b);
                // if (player.position === 'G') {
                //     catWeight = catWeight / 4;
                //     catWeight = catWeight * 2; // Do this simply to increase goalie importance in draft
                // } else if (player.position === 'D') {
                //     catWeight = catWeight / 9;
                // } else {
                //     catWeight = catWeight / 8;
                // }
                weightedZScore += catWeight;
                if ( (player.position === 'D' && dOffenseCategories.includes(category)) || (['LW', 'C', 'RW'].includes(player.position) && fOffenseCategories.includes(category)) ) {
                    weightedZOffense += catWeight;
                }
                if (['LW', 'C', 'RW', 'D'].includes(player.position) && sktrPeripheralCategories.includes(category) ) {
                    weightedZPeripheral += catWeight;
                }
                if (player.position === 'G') {
                    if (gCountCategories.includes(category)) {
                        weightedGZCount += catWeight;
                    } else { // gRatioCategories.includes(category)
                        weightedGZRatio += catWeight;
                    }
                }
            }
        }

        player.weightedZScore = weightedZScore;
        if (['LW', 'C', 'RW', 'D'].includes(player.position)) {
            player.weightedZOffense = weightedZOffense;
            player.weightedZPeripheral = weightedZPeripheral;
            player.weightedGZCount = 0;
            player.weightedGZRatio = 0;
        }
        if (player.position === 'G') {
            player.weightedZOffense = 0;
            player.weightedZPeripheral = 0;
            player.weightedGZCount = weightedGZCount;
            player.weightedGZRatio = weightedGZRatio;
        }

    });

    // Sort the available players by their weighted z-score
    availablePlayers.sort((a, b) => b.weightedZScore - a.weightedZScore);

    return availablePlayers;

}

function updateTableWithWeightedZScores(weightedAvailablePlayer) {

    var table = $('#player_stats').DataTable();

    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        var rowData = this.data();
        var id = rowData[id_idx].match(/>(\d+)</)[1]; // assuming the "id" column is the first column
        var newDataItem = weightedAvailablePlayer.find(function(item) {
            return item.id === id;
        });

        if (newDataItem) {
            // update rowData with data from newDataItem
            rowData[weightedZScore_idx] = newDataItem.weightedZScore.toFixed(1);
            rowData[weightedZOffense_idx] = newDataItem.weightedZOffense.toFixed(1);
            rowData[weightedZPeripheral_idx] = newDataItem.weightedZPeripheral.toFixed(1);
            rowData[weightedGZCount_idx] = newDataItem.weightedGZCount.toFixed(1);
            rowData[weightedGZRatio_idx] = newDataItem.weightedGZRatio.toFixed(1);
            this.data(rowData);
        }
    } );

    table.columns.adjust().draw();

}

// The code defines a "colourize" function as a jQuery plugin using a self-executing anonymous function to create a private scope
// and prevent interference with other scripts.
// The function takes an "oOptions" parameter for customization and is defined as a method of the jQuery object, allowing it to be
// used as part of a jQuery chain.
// This is a common way of defining jQuery plugins and promotes code modularity and conflict avoidance.
(function($) {

    $.fn.colourize = function(oOptions) {
        // parse - function to parse numerical value from each element
        // min - explicity set a minimum cap on the most negative colour
        // max - explicity set a maximum cap on the most positive colour
        // center - explicitly define the neutral value, defaults to mean of values
        // readable - invert text colour if background colour too dark
        // themes - object defining multiple themes
        // theme.x.colour_min - Most negative colour
        // theme.x.colour_mid - Neutral colour
        // theme.x.colour_max - Most positive colour
        // theme - theme to use
        // percent - set to true if min/max are percent values, defaults to false

        // pal = sns.color_palette('coolwarm')
        // pal.as_hex()
        //   0:'#6788EE'
        //   1:'#9ABBFF'
        //   2:'#C9D7F0'
        //   3:'#EDD1C2'
        //   4:'#F7A889'
        //   5:'#E26952'
        // pal = sns.color_palette('vlag')
        // pal.as_hex()
        //   0:'#6e90bf'
        //   1:'#aab8d0'
        //   2:'#e4e5eb'
        //   3:'#f2dfdd'
        //   4:'#d9a6a4'
        //   5:'#c26f6d'
        var settings = $.extend({
            parse: function(e) {
                if (isNaN(parseFloat(e.html())) || !isFinite(parseFloat(e.html()))) {
                    return 0;
                } else {
                    return parseFloat(e.html());
                }
            },
            min: 0,
            max: undefined,
            center: undefined,
            readable: false,
            themes: {
                "default": {
                    color_min: "#0075e7",
                    color_mid: "#FFFFFF",
                    color_max: "#d34800"
                },
                "default-reverse": {
                    color_min: "#d34800",
                    color_mid: "#FFFFFF",
                    color_max: "#0075e7"
                },
                "blue-white-red": {
                colour_min: "#312F9D",
                colour_mid: "#FFFFFF",
                colour_max: "#C80000"
                },
                "blue-white-red-reverse": {
                    colour_min: "#C80000",
                    colour_mid: "#FFFFFF",
                    colour_max: "#312F9D"
                },
                //   "cool-warm": {
                //     colour_min: "#6788EE",
                //     colour_mid: "#FFFFFF",
                //     colour_max: "#E26952"
                // },
                // "cool-warm-reverse": {
                //     colour_min: "#E26952",
                //     colour_mid: "#FFFFFF",
                //     colour_max: "#6788EE"
                // },
                "cool-warm": {
                    colour_coolest: "#6788EE",
                    colour_cooler: '#9ABBFF',
                    colour_cool: '#C9D7F0',
                    colour_mid: "#DBD4D9",
                    colour_warm: "#EDD1C2",
                    colour_warmer: "#F7A889",
                    colour_warmest: "#E26952"
                },
                "cool-warm-reverse": {
                    colour_coolest: "#E26952",
                    colour_cooler: '#F7A889',
                    colour_cool: '#EDD1C2',
                    colour_mid: "#DBD4D9",
                    colour_warm: "#C9D7F0",
                    colour_warmer: "#9ABBFF",
                    colour_warmest: "#6788EE"
                },
            },
            theme: "cool-warm",
            percent: false
        }, oOptions);

        // this doesn't really do much in my implementation, i.e., createdCell
        //
        var min = 0;
        var max = 0;
        this.each(function() {
            var value = parseFloat(settings.parse($(this)));
            if (!isNaN(value) && isFinite(value)) {
                min = Math.min(min, value);
                max = Math.max(max, value);
                $(this).data('colourize', value);
            }
        });

        if (settings.center === undefined) settings.center = mean(this);
        if (settings.min !== undefined) min = settings.min;
        var adj = settings.center - min;

        this.each(function() {
            var value = $(this).data('colourize');
            var ratio = value < settings.center ? (settings.center - value) / (settings.center - min): (value - settings.center) / (settings.max - settings.center);
            var colour1, colour2;

            if ( settings.theme.startsWith('cool-warm') ) {
                if (!settings.percent && value <= settings.min) {
                    colour1 = settings.themes[settings.theme].colour_coolest;
                    colour2 = settings.themes[settings.theme].colour_coolest;
                } else if (!settings.percent && value >= settings.max) {
                    colour1 = settings.themes[settings.theme].colour_warmest;
                    colour2 = settings.themes[settings.theme].colour_warmest;
                } else if (settings.percent && ratio <= settings.min) {
                    colour1 = settings.themes[settings.theme].colour_coolest;
                    colour2 = settings.themes[settings.theme].colour_coolest;
                } else if (settings.percent && ratio >= settings.max) {
                    colour1 = settings.themes[settings.theme].colour_warmest;
                    colour2 = settings.themes[settings.theme].colour_warmest;
                } else if ( value < settings.center ) {
                    ratio = Math.abs(ratio);
                    // if (ratio < -1) ratio = -1;
                    if (ratio > 1) ratio = 1;
                    if ( ratio >= 0.667 ) {
                        ratio = (ratio - 0.667) / 0.333
                        colour1 = settings.themes[settings.theme].colour_coolest;
                        colour2 = settings.themes[settings.theme].colour_cooler;
                    } else if ( ratio >= 0.333 ) {
                        ratio = (ratio - 0.333) / 0.333
                        colour1 = settings.themes[settings.theme].colour_cooler;
                        colour2 = settings.themes[settings.theme].colour_cool;
                    } else {
                        ratio = ratio / 0.333
                        colour1 = settings.themes[settings.theme].colour_cool;
                        colour2 = settings.themes[settings.theme].colour_mid;
                    }
                } else {
                    ratio = Math.abs(ratio);
                    if (ratio > 1) ratio = 1;
                    if ( ratio >= 0.667 ) {
                        ratio = (ratio - 0.667) / 0.333
                        colour1 = settings.themes[settings.theme].colour_warmest;
                        colour2 = settings.themes[settings.theme].colour_warmer;
                    } else if ( ratio >= 0.333 ) {
                        ratio = (ratio - 0.333) / 0.333
                        colour1 = settings.themes[settings.theme].colour_warmer;
                        colour2 = settings.themes[settings.theme].colour_warm;
                    } else {
                        ratio = ratio / 0.333
                        colour1 = settings.themes[settings.theme].colour_warm;
                        colour2 = settings.themes[settings.theme].colour_mid;
                    }
                }
            } else {
                if (!settings.percent && value <= settings.min) {
                    colour1 = settings.themes[settings.theme].colour_min;
                    colour2 = settings.themes[settings.theme].colour_min;
                } else if (!settings.percent && value >= settings.max) {
                    colour1 = settings.themes[settings.theme].colour_max;
                    colour2 = settings.themes[settings.theme].colour_max;
                } else if (settings.percent && ratio <= settings.min) {
                    colour1 = settings.themes[settings.theme].colour_min;
                    colour2 = settings.themes[settings.theme].colour_min;
                } else if (settings.percent && ratio >= settings.max) {
                    colour1 = settings.themes[settings.theme].colour_max;
                    colour2 = settings.themes[settings.theme].colour_max;
                } else if ( value < settings.center ) {
                    ratio = Math.abs(ratio);
                    if (ratio < -1) ratio = -1;
                    colour1 = settings.themes[settings.theme].colour_min;
                    colour2 = settings.themes[settings.theme].colour_mid;
                } else {
                    ratio = Math.abs(ratio);
                    if (ratio > 1) ratio = 1;
                    colour1 = settings.themes[settings.theme].colour_max;
                    colour2 = settings.themes[settings.theme].colour_mid;
                }
            }

            var colour = getColour(colour1, colour2, ratio);
            $(this).css('background-color', colour);
            if (settings.readable)
                $(this).css('color', getContrastYIQ(colour));
        });

        function getColour(colour1, colour2, ratio) {
            var hex = function(x) {
                x = x.toString(16);
                return (x.length == 1) ? '0' + x : x;
            }
            colour1 = (colour1.charAt(0) == "#") ? colour1.slice(1) : colour1
            colour2 = (colour2.charAt(0) == "#") ? colour2.slice(1) : colour2
            var r = Math.ceil(parseInt(colour1.substring(0,2), 16) * ratio + parseInt(colour2.substring(0,2), 16) * (1-ratio));
            var g = Math.ceil(parseInt(colour1.substring(2,4), 16) * ratio + parseInt(colour2.substring(2,4), 16) * (1-ratio));
            var b = Math.ceil(parseInt(colour1.substring(4,6), 16) * ratio + parseInt(colour2.substring(4,6), 16) * (1-ratio));
            return "#" + (hex(r) + hex(g) + hex(b)).toUpperCase();
        }

        function mean(arr) {
            var avg = 0;
            arr.each(function() {
                if ($(this).data('colourize') !== undefined) {
                    avg += $(this).data('colourize');
                }
            });
            return avg / arr.length;
        }

        // http://24ways.org/2010/calculating-colour-contrast/
        function getContrastYIQ(hexcolour) {
            var hex = (hexcolour.charAt(0) == "#") ? hexcolour.slice(1) : hexcolour;
            var r = parseInt(hex.substr(0,2),16);
            var g = parseInt(hex.substr(2,2),16);
            var b = parseInt(hex.substr(4,2),16);
            var yiq = ((r*299)+(g*587)+(b*114))/1000;
            return (yiq >= 128) ? 'black' : 'white';
        }

        return this;
    };

}(jQuery))
