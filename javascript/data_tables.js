// heatmaps toggle
var heatmaps = true

// flag variable to track if the ColVis button was clicked
var colvisClicked = false;
var manually_hidden_columns = [];
var manually_unhidden_columns = [];

// update stats
const updateButton = document.querySelector('#updateButton');

$(document).ready(function () {

    // Add "display" class to table
    $('#T_player_stats').addClass('display')
                        .addClass('cell-border')
                        .addClass('hover')
                        .addClass('compact');

    $('div.dtsb-inputCont').css('font-size', '32px');

    var seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();
    var fromSeason = $('#fromSeason').val();
    var toSeason = $('#toSeason').val();
    var fromDate = '"' + $('#dateControls').children()[0].value + '"';
    var toDate = '"' + $('#dateControls').children()[1].value + '"';
    var gameType = $('#gameType').val();
    var statType = $('#statType').val();
    var poolID = $('#poolID').val();

    getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType, function(playerData) {

        updateGlobalVariables(playerData);

        caption = updateCaption(fromSeason, toSeason, gameType);
        $('#T_player_stats').append('<caption><b><u>' + caption + '</u></b></caption>');

        if ( statType === 'Cumulative' ) {
            var stats_data = cumulative_stats_data;
            var columns = cumulative_column_titles;
        } else if ( statType === 'Per game' ) {
            var stats_data = per_game_stats_data;
            var columns = per_game_column_titles;
        } else if ( statType === 'Per 60 minutes' ) {
            var stats_data = per_60_stats_data;
            var columns = per_60_column_titles;
        }

        updateColumnIndexes(columns);

        updateHeatmapColumnLists();

        var table = $('#T_player_stats').DataTable( {

            data: stats_data,
            columns: columns,

            // iitial table order
            order: [[z_score_idx, "desc"]],

            // disable zebra strips on alternating rows; it messes with heatmap colours
            stripeClasses: [],

            // 'col-sm-4' is "Show x page entries"
            // 'col-sm-5' is "Export to Excel", "Column Visibility", "Hide Selected Rows", & "Toggle Heatmaps"
            // 'col-sm-7' is "Showing x to y of z entries" at the top of the table
            // 'col-sm-12' is "T_player_stats" able
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
                                    return rowData[$('#T_player_stats').DataTable().column(watch_idx).index()] === 'Yes';
                                },
                                className: 'watch_list'
                            },
                            {
                                label: 'On roster',
                                value: function(rowData, rowIdx) {
                                    return rowData[$('#T_player_stats').DataTable().column(minors_idx).index()] === '';
                                },
                                className: 'rostered'
                            },
                            {
                                label: 'In minors',
                                value: function(rowData, rowIdx) {
                                    return rowData[$('#T_player_stats').DataTable().column(minors_idx).index()] === 'Yes';
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
                        z_score_idx, z_offense_idx, z_peripheral_idx, z_combo_idx, z_hits_blk_idx, z_sog_hits_blk_idx, z_goals_hits_pim_idx, z_hits_pim_idx], searchBuilder: { defaultCondition: '>=' } },
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

                // custom sort for 'prj draft round' column
                { targets: [prj_draft_round_idx], type: "custom_pdr_sort", orderSequence: ['asc']},

                // custom sort for 'fantrax adp' column
                { targets: [adp_idx], type: "custom_adp_sort", orderSequence: ['asc']},

                // custom sort for 'line' and 'line prj' column
                // custom sort for 'pp unit' and 'pp unit prj' column
                // custom sort for 'athletic z-score rank' column
                // custom sort for 'athletic z-score rank' column
                // custom sort for 'dobber z-score rank' column
                // custom sort for 'dtz z-score rank' column
                // custom sort for 'fantrax z-score rank' column
                { targets: [line_idx, pp_unit_idx, athletic_zscore_rank_idx, dfo_zscore_rank_idx, dobber_zscore_rank_idx, dtz_zscore_rank_idx, fantrax_zscore_rank_idx], type: "custom_integer_sort", orderSequence: ['asc']},

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

                var table = $('#T_player_stats').DataTable();

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

                // show table
                $("#loadingSpinner").hide();
                $('#T_player_stats-div').show();
                table.searchPanes.rebuildPane();
                table.columns.adjust().draw();

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
                // $('#DataTables_Table_0').data('previous', $('#DataTables_Table_0').data('current'));
                // save "pos" searchPane selection as "current"
                if ( $('#DataTables_Table_0').data('previous') === cell.data() ) {
                    $('#DataTables_Table_0').data('current', '');
                } else {
                    $('#DataTables_Table_0').data('current', cell.data());
                }
                columnVisibility( 'position change' );
            }

        });

        // // *******************************************************************
        // // select rows
        // $('#T_player_stats tbody').on('click', 'tr', function () {
        //     // if ($(this).hasClass('selected')) {
        //     //     $(this).removeClass('selected');
        //     // } else {
        //     //     table.$('tr.selected').removeClass('selected');
        //     //     $(this).addClass('selected');
        //     // }
        //     $(this).toggleClass('selected');
        // });
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
        // // $('#T_player_stats').on('click', 'tbody tr', function() {
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
        // Rank-in-group column
        table.on('order.dt search.dt', function () {
            let i = 1;

            table.cells(null, 0, { search: 'applied', order: 'applied' }).every(function (cell) {
                this.data(i++);
            });
        }).draw();

        // set "name" as fixed column
        table.on('draw.dt column-visibility.dt', function () {

            // // load stats for stat type
            // var current_stat_type = $('#statType').data('current');
            // if ( current_stat_type === 'Cumulative' ) {
            //     var columns = cumulative_column_titles;
            // } else if ( current_stat_type === 'Per game' ) {
            //     var columns = per_game_column_titles;
            // } else if ( current_stat_type === 'Per 60 minutes' ) {
            //     var columns = per_60_column_titles;
            // }

            // // Loop through each header cell and set the text to the desired value
            // table.columns().every(function(index) {
            //     $(table.column(index).header()).text(columns[index].title);
            // });

            setFixedColumn( table );

        });

        // display stat type columns
        $('#statType').change( function(data) {

            // save current statType (i.e., 'Cumulative')
            $('#statType').data('current', $('#statType').val());
            columnVisibility( 'stat type change' );

            // show spinner & hide table
            $('#T_player_stats-div').hide();
            $("#loadingSpinner").show();

            // remove table data
            table.clear();

            // load stats for stat type
            if ( this.value === 'Cumulative' ) {
                table.rows.add(cumulative_stats_data);
            } else if ( this.value === 'Per game' ) {
                table.rows.add(per_game_stats_data);
            } else if ( this.value === 'Per 60 minutes' ) {
                table.rows.add(per_60_stats_data);
            }

            const tableCaption = document.querySelector('table caption');
            caption = updateCaption();
            tableCaption.textContent = caption;

            // hide spinner & show table
            $("#loadingSpinner").hide();
            $('#T_player_stats-div').show();
            // table.searchPanes.rebuildPane();
            table.columns.adjust().draw();

        } );

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

    });

});

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

// // Function to get player data from the Pyodide API endpoint
// function getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType) {

//     // Load Pyodide
//     loadPyodide({ indexURL : "https://cdn.jsdelivr.net/pyodide/v0.18.1/full/" }).then((pyodide) => {
//         // Define the pyodide object in the global scope
//         window.pyodide = pyodide;

//         // Run your Python code using Pyodide
//         pyodide.runPythonAsync(`
//             # Import your rank_players function
//             from get_player_data import rank_players

//             # Call your rank_players function with the specified parameters
//             data_dict = rank_players(${seasonOrDateRadios}, ${fromSeason}, ${toSeason}, ${fromDate}, ${toDate}, ${poolID}, ${gameType}, ${statType})

//             # Return the result as a Python dictionary
//             data_dict
//         `).then((data_dict) => {
//             // Convert the Python dictionary to a JavaScript object
//             let playerData = pyodide.pyProxyToJs(data_dict);

//             // Do something with the player data (e.g. update your UI)
//             return playerData;
//             });
//     })
//     .catch((error) => {
//         // Handle any errors that occur while loading Pyodide
//         console.error('Error loading Pyodide:', error);
//     });
// }

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

}

function updateColumnIndexes(columns) {

    // column indexes
    adp_idx = columns.findIndex(column => column.title === 'fantrax adp');
    age_idx = columns.findIndex(function(column) { return column.title == 'age' });
    assists_idx = columns.findIndex(column => ['a', 'a pg', 'a p60', 'a prj'].includes(column.title));
    athletic_zscore_rank_idx = columns.findIndex(column => column.title === 'athletic z-score rank');
    blk_idx = columns.findIndex(column => ['blk', 'blk pg', 'blk p60', 'blk prj'].includes(column.title));
    breakout_threshold_idx = columns.findIndex(column => column.title === 'bt');
    dfo_zscore_rank_idx = columns.findIndex(column => column.title === 'dfo z-score rank');
    dobber_zscore_rank_idx = columns.findIndex(column => column.title === 'dobber z-score rank');
    draft_position_idx = columns.findIndex(column => column.title === 'draft position');
    draft_round_idx = columns.findIndex(column => column.title === 'draft round');
    dtz_zscore_rank_idx = columns.findIndex(column => column.title === 'dtz z-score rank');
    fantrax_roster_status_idx = columns.findIndex(column => column.title === 'fantrax roster status');
    fantrax_zscore_rank_idx = columns.findIndex(column => column.title === 'fantrax z-score rank');
    gaa_idx = columns.findIndex(column => ['gaa', 'gaa pg', 'gaa p60', 'gaa prj'].includes(column.title));
    game_today_idx = columns.findIndex(column => column.title === 'game today');
    games_idx = columns.findIndex(column => column.title === 'games');
    goalie_starts_idx = columns.findIndex(column => column.title === 'goalie starts');
    goals_idx = columns.findIndex(column => ['g', 'g pg', 'g p60', 'g prj'].includes(column.title));
    hits_idx = columns.findIndex(column => ['hits', 'hits pg', 'hits p60', 'hits prj'].includes(column.title));
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
    pp_unit_idx = columns.findIndex(column => column.title === 'pp unit');
    ppp_idx = columns.findIndex(column => ['ppp', 'ppp pg', 'ppp p60', 'ppp prj'].includes(column.title));
    predraft_keeper_idx = columns.findIndex(column => column.title === 'pre-draft keeper');
    prj_draft_round_idx = columns.findIndex(column => column.title === 'prj draft round');
    rank_in_group_idx = columns.findIndex(column => column.title === 'rank in group');
    rookie_idx = columns.findIndex(column => column.title === 'rookie');
    saves_idx = columns.findIndex(column => ['sv', 'sv pg', 'sv p60', 'sv prj'].includes(column.title));
    saves_percent_idx = columns.findIndex(column => ['sv%', 'sv% pg', 'sv% p60', 'sv% prj'].includes(column.title));
    sog_idx = columns.findIndex(column => ['sog', 'sog pg', 'sog p60', 'sog prj'].includes(column.title));
    sog_pp_idx = columns.findIndex(column => column.title === 'pp sog');
    team_idx = columns.findIndex(column => column.title === 'team');
    tk_idx = columns.findIndex(column => ['tk', 'tk pg', 'tk p60', 'tk prj'].includes(column.title));
    toi_even_pg_trend_idx = columns.findIndex(column => column.title === 'toi even pg (trend)');
    toi_pg_trend_idx = columns.findIndex(column => column.title === 'toi pg (trend)');
    toi_pp_percent_3gm_avg_idx = columns.findIndex(column => column.title === 'toi pp % (rolling avg)');
    toi_pp_percent_idx = columns.findIndex(column => column.title === 'toi pp %');
    toi_pp_pg_trend_idx = columns.findIndex(column => column.title === 'toi pp pg (trend)');
    toi_seconds_idx = columns.findIndex(column => column.title === 'toi (sec)');
    toi_sh_pg_trend_idx = columns.findIndex(column => column.title === 'toi sh pg (trend)');
    watch_idx = columns.findIndex(column => column.title === 'watch');
    wins_idx = columns.findIndex(column => ['w', 'w pg', 'w p60', 'w prj'].includes(column.title));
    z_assists_idx = columns.findIndex(column => ['z-a', 'z-a pg', 'z-a p60', 'z-a prj'].includes(column.title));
    z_blk_idx = columns.findIndex(column => ['z-blk', 'z-blk pg', 'z-blk p60', 'z-blk prj'].includes(column.title));
    z_combo_idx = columns.findIndex(column => ['z-combo', 'z-combo pg', 'z-combo p60', 'z-combo prj'].includes(column.title));
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

}

// heatmap columns
function updateHeatmapColumnLists() {

    sktr_category_heatmap_columns = [points_idx, goals_idx, assists_idx, ppp_idx, sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx];
    goalie_category_heatmap_columns = [wins_idx, saves_idx, gaa_idx, saves_percent_idx];
    sktr_category_z_score_heatmap_columns = [z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_tk_idx, z_hits_idx, z_blk_idx, z_pim_idx];
    goalie_category_z_score_heatmap_columns = [z_wins_idx, z_saves_idx, z_gaa_idx, z_saves_percent_idx];
    z_score_summary_heatmap_columns = [z_score_idx, z_offense_idx, z_peripheral_idx, z_sog_hits_blk_idx, z_hits_blk_idx, z_goals_hits_pim_idx, z_hits_pim_idx, z_score_vorp_idx, z_offense_vorp_idx, z_peripheral_vorp_idx];

}

// Function to update the table with new data
function updateTable(stats_data) {

    let table = $('#T_player_stats').DataTable();
    // Clear the existing data in the table
    table.clear();

    // Add the new data to the table
    table.rows.add(stats_data);

    // hide spinner & show table
    $("#loadingSpinner").hide();
    $('#T_player_stats-div').show();

    // Redraw the table
    table.columns.adjust().draw();
}

// // custom filtering to search data columns; e.g., in rookie, watchlist, in_nhl
// $.fn.dataTable.ext.search.push(function (settings, data, dataIndex) {

    //     // rookies-only checkbox
//     var rookies_checkbox = $('#rookies').is(':checked');
//     // watchlist checkbox
//     var watchlist_checkbox = $('#watchlist').is(':checked');
//     // in_nhl checkbox
//     var in_nhl_checkbox = $('#in_nhl').is(':checked');

//     // display all rows if nothing entered
//     if (rookies_checkbox == false && watchlist_checkbox == false && in_nhl_checkbox == false) {
//             return true;
//     }

//     var table = $('#T_player_stats').DataTable();
//     var max_col_index =table.columns().count() - 1;
//     var rookies_index = 0;
//     var watchlist_index = 0;
//     var in_nhl_index = 0;
//     for (var i = 0; i < max_col_index; i++) {
//         var title = table.column( i ).header().innerText;
//         if ( rookies_index == 0 ) {
//             if ( title.match('rookie')) {
//                 rookies_index = i ;
//             }
//         }
//         if ( watchlist_index == 0 ) {
//             if ( title.match('watch')) {
//                 watchlist_index = i ;
//             }
//         }
//         if ( in_nhl_index == 0 ) {
//             if ( title.match('minors')) {
//                 in_nhl_index = i ;
//             }
//         }
//         if (rookies_index > 0 && watchlist_index > 0 && in_nhl_index > 0){
//             break
//         }
//     }

//     var show_rookies = false;
//     var show_watchlist = false;
//     var show_in_nhl = false;

//     var rookie_val = data[rookies_index] || 0; // use data for the rookie column
//     if (rookies_checkbox == false || rookie_val == 'Yes') {
//         show_rookies = true;
//     }

//     var watchlist_val = data[watchlist_index] || 0; // use data for the watchlist column
//     if (watchlist_checkbox == false || watchlist_val == 'Yes') {
//         show_watchlist = true;
//     }

//     var in_nhl_val = data[in_nhl_index] || 0; // use data for the minors column
//     if (in_nhl_checkbox == false || in_nhl_val != 'Yes') {
//         show_in_nhl = true;
//     }

//     return show_rookies && show_watchlist && show_in_nhl;

// });

// // custom filtering event listeners
// $(document).ready(function () {

//     var table = $('#T_player_stats').DataTable();

//     // Event listener for row filtering rookies-only checkbos, & redraw on input
//     $('#rookies').click(function () {
//         table.draw();
//     });

//     // Event listener for row filtering watchlist checkbox, & redraw on input
//     $('#watchlist').click(function () {
//         table.draw();
//     });

//     // Event listener for row filtering in_nhl checkbox, & redraw on input
//     $('#in_nhl').click(function () {
//         table.draw();
//     });

// } );

function toggleHeatmaps(table) {

    heatmaps = !heatmaps;

    // show spinner & hide table
    $('#T_player_stats-div').hide();
    $("#loadingSpinner").show();
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

    // hide spinner & show table
    $("#loadingSpinner").hide();
    $('#T_player_stats-div').show();
    table.columns.adjust().draw();

};

function columnVisibility( trigger ) {

    // 'trigger' values: 'stat type initialization', 'stat type change', 'position change'

    var table = $('#T_player_stats').DataTable();

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

    // if I uncomment the following line, the web page hangs. Odd!
    table.columns.adjust().draw();

    // save current statType as previous
    $('#statType').data('previous', current_stat_type);
    $('#DataTables_Table_0').data('previous', current_positon);

};

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

};

function restoreColVisColumns( table, columns ){
    // hide columns
    columns_to_hide = columns.filter(elem => initially_hidden_column_names.includes(elem) && manually_unhidden_columns.includes(elem));
    table.columns(columns_to_hide).visible(show=false, redrawCalculations=false);

    // unhide columns
    columns_to_be_visible = columns.filter(elem => !initially_hidden_column_names.includes(elem) && manually_hidden_columns.includes(elem));
    table.columns(columns_to_be_visible).visible(show=true, redrawCalculations=false);

}

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
} );

// colourize function
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

}(jQuery));

updateButton.addEventListener('click', async () => {

    // show spinner & hide table
    $('#T_player_stats-div').hide();
    $("#loadingSpinner").show();

    const tableCaption = document.querySelector('table caption');

    var seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();
    var fromSeason = $('#fromSeason').val();
    var toSeason = $('#toSeason').val();
    var fromDate = $('#dateControls').children()[0].value;
    var toDate = $('#dateControls').children()[1].value;
    var gameType = $('#gameType').val();
    var statType = $('#statType').val();
    var poolID = $('#poolID').val();

    getPlayerData(seasonOrDateRadios, fromSeason, toSeason, fromDate, toDate, poolID, gameType, statType, function(playerData) {

        updateGlobalVariables(playerData);

        caption = updateCaption();
        tableCaption.textContent = caption;

        if ( statType === 'Cumulative' ) {
            var stats_data = cumulative_stats_data;
            var columns = cumulative_column_titles;
        } else if ( statType === 'Per game' ) {
            var stats_data = per_game_stats_data;
            var columns = per_game_column_titles;
        } else if ( statType === 'Per 60 minutes' ) {
            var stats_data = per_60_stats_data;
            var columns = per_60_column_titles;
        }

        updateColumnIndexes(columns);

        updateHeatmapColumnLists();

        updateTable(stats_data);

    } );

});

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