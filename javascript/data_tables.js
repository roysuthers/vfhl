// heatmaps toggle
var heatmaps = true

// flag variable to track if the ColVis button was clicked
var colvisClicked = false;
var manually_hidden_columns = [];
var manually_unhidden_columns = [];

/////////////////////////////////////////////////////////////////////////////////////////
// global variables for Draft
var remaining_draft_picks;
var completed_draft_picks = [];
var draft_manager;
var auto_assign_picks = false;
// global variables to include managers that have reached their position maximium limits, during auto assignment
var f_limit_reached = [];
var d_limit_reached = [];
var g_limit_reached = [];
var maxCategoryValues = {'values': {}, 'zScores': {}};
/////////////////////////////////////////////////////////////////////////////////////////

var fOffenseCategories = ['goals', 'assists', 'powerplayPoints', 'shotsOnGoal'];
var dOffenseCategories = ['points'].concat(fOffenseCategories);
var sktrPeripheralCategories = ['hits', 'blockedShots', 'takeaways', 'penaltyMinutes'];
var fAllCategories = fOffenseCategories.concat(sktrPeripheralCategories);
var dAllCategories = dOffenseCategories.concat(sktrPeripheralCategories);
var gCountCategories = ['wins', 'saves'];
var gRatioCategories = ['gaa', 'savePercent'];

var nameToIndex = {};

var positionSearchPaneDataTable;
var additionalFiltersSearchPaneDataTable;

var managerSummaryZScores;

var dateRangePickerSelection;

var baseSearchBuilderCriteria = {
    "criteria": [
        {
            "condition": "!=",
            "data": "team",
            "type": "html",
            "value": ["(N/A)"]
        },
        {
            "condition": "<=",
            "data": "age",
            "type": "int",
            "value": []
        },
        {
            "condition": "contains",
            "data": "name",
            "type": "str",
            "value": []
        },
    ],
    "logic": "AND"
}

var lastSortIdx = null; // Declare lastSortIdx outside the function
var lastSortOrder = true; // Declare descending outside the function

$('#gameType').on('change', function() {
    // save current gameType (i.e., 'Regular Season')
    $('#gameType').data('current', gameType.value);

    // hide\display startDraftButton as appropriate
    let startDraftButton = document.getElementById('startDraftButton');
    if (gameType.value === 'Projected Season') {
        $('#startDraftButton').removeClass('hidden').css('display', 'inline-block');
    } else {
        $('#startDraftButton').addClass('hidden').css('display', 'none');
    }
})

$('#dateRange').on('apply.daterangepicker', function(ev, picker) {
    dateRangePickerSelection = picker.chosenLabel;
});

// $('#showAsVorpCheckbox').on('change', function() {

//     let playerStatsTable = $('#player_stats').DataTable();

//     if (document.getElementById('showAsVorpCheckbox').checked === true) {
//         let replacementPlayerZscores = calcPositionCategoryZScores(playerStatsTable.data().toArray());
//         calcPlayerVorpZsores(playerStatsTable, replacementPlayerZscores);
//     } else {
//         resetPlayerZsores(playerStatsTable, stats_data)
//     }

//     managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);
//     updateManagerSummaryTable(managerSummaryZScores);

//     // data = calcManagerCategoryNeedsData();
//     myCategoryNeeds = getMyCategoryNeeds();
//     updateMyCategoryNeedsTable(myCategoryNeeds);

//     let caption = updateCaption();
//     if (document.getElementById('showAsVorpCheckbox').checked === true) {
//         caption += ' (VORP)'
//     }

//     let tableCaption = document.querySelector('#player_stats caption');
//     tableCaption.textContent = caption;

//     tableCaption = document.querySelector('#managerSummary caption');
//     tableCaption.textContent = caption + ' - Manager Z-Scores';
//     tableCaption.style.fontWeight = 'bold';
//     tableCaption.style.textDecoration = 'underline';

//     tableCaption = document.querySelector('#managerCategoryNeedsContainerCaption');
//     tableCaption.textContent = 'Manager Category Needs';
//     tableCaption.style.fontWeight = 'bold';
//     tableCaption.style.textDecoration = 'underline';

//     playerStatsTable.columns.adjust().draw();

// })

$.fn.dataTable.Api.registerPlural( 'columns().names()', 'column().name()', function ( setter ) {
    return this.iterator( 'column', function ( settings, column ) {
        let col = settings.aoColumns[column];

        if ( setter !== undefined ) {
            col.sName = setter;
            return this;
        }
        else {
            return col.sName;
        }
    }, 1 );
})

document.getElementById('autoAssignDraftPicks').addEventListener('click', () => {

    autoAssignDraftPicks();

})

document.getElementById('getStatsButton').addEventListener('click', async () => {

    // show pulsing bar & hide tables
    hideTablesShowPulsingBar()

    const seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();
    const statType = document.querySelector('#statType');

    // Check if DataTable instance exists
    if ($.fn.dataTable.isDataTable('#player_stats')) {
        // Get DataTable instance
        var table = $('#player_stats').DataTable();
        // // Get player_ids of selected rows
        // var selectedPlayerIds = table.rows('.selected').data().toArray().map(function(row) {
        //     return row[id_idx].match(/>(\d+)</)[1];
        // });
        // // Save selected player_ids
        // localStorage.setItem('selectedPlayerIds', JSON.stringify(selectedPlayerIds));

        // Save searchPane selections
        var selectedOptions = {};
        $('#player_stats-div .dtsp-searchPanes table.dataTable').filter(function() {
            return this.id.indexOf('DataTables_Table_') === 0;
        }).each(function() {
            var table = $(this).DataTable();
            var selectedRows = table.rows('.selected');
            selectedOptions[this.id] = selectedRows.data().toArray().map(function(row) {
                return row.display;
            });
        });

    }

    getPlayerData(seasonOrDateRadios, function(playerData) {

        if (Object.keys(playerData).length === 0) {
            alert('No data returned from server.');
            // show tables
            hidePulsingBarShowTables()
            return;
        } else {
            caption = updateCaption();
            let tableCaption = document.querySelector('#player_stats caption');
            tableCaption.textContent = caption;

            tableCaption = document.querySelector('#managerSummary caption');
            tableCaption.textContent = caption + ' - Manager Z-Scores';
            tableCaption.style.fontWeight = 'bold';
            tableCaption.style.textDecoration = 'underline';

            updateGlobalVariables(playerData);

            // In JavaScript, when you assign an array to another variable using let data = stats_data, both data and stats_data point to the same array
            // in memory. So, if you modify data, it will also modify stats_data and vice versa.
            // These methods only create a shallow copy of the array. If your array contains objects or other arrays, you may need to create a deep copy instead
            let data = JSON.parse(JSON.stringify(stats_data));
            let columns = JSON.parse(JSON.stringify(column_titles));

            updateColumnIndexes(columns);

            // If #player_stats is already a DataTable, update it
            if ($.fn.DataTable.isDataTable('#player_stats')) {

                updatePlayerStatsTable(data);

            } else {

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
                                            return rowData[this.column(watch_idx).index()] === 'Yes';
                                        },
                                        className: 'watch_list'
                                    },
                                    {
                                        label: 'On roster',
                                        value: function(rowData, rowIdx) {
                                            return rowData[this.column(minors_idx).index()] === '';
                                        },
                                        className: 'rostered'
                                    },
                                    {
                                        label: 'Minors',
                                        value: function(rowData, rowIdx) {
                                            return rowData[this.column(minors_idx).index()] === 'Yes';
                                        },
                                        className: 'minors'
                                    },
                                    {
                                        label: 'Minors (Fantasy)',
                                        value: function(rowData, rowIdx) {
                                            return (rowData[this.column(position_idx).index()] !== 'G' && rowData[this.column(career_games_idx).index()] < 160) ||
                                                   (rowData[this.column(position_idx).index()] === 'G' && rowData[this.column(career_games_idx).index()] < 80);
                                        },
                                        className: 'mfCount'
                                    },
                                    {
                                        label: 'Selected Players',
                                        value: function(rowData, rowIdx) {
                                            // var table = $('#player_stats').DataTable();
                                            // var selectedPlayerIds = table.rows('.selected').data().toArray().map(function(row) {
                                            //     return row[id_idx].match(/>(\d+)</)[1];
                                            // });
                                            var selectedPlayerIds = localStorage.getItem('selectedPlayerIds');
                                            // var playerId = rowData[id_idx].match(/>(\d+)</)[1];
                                            var playerId = rowData[id_idx];
                                            if (selectedPlayerIds) {
                                                return  selectedPlayerIds.includes(playerId);
                                            }
                                        },
                                        className: 'selections'
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
                        columns: search_builder_column_names,
                        // preDefined: {
                        //     criteria: [
                        //         {
                        //             condition: '!=',
                        //             data: 'team',
                        //             value: ['(N/A)']
                        //         }
                        //     ],
                        //     logic: 'AND',
                        // }
                    },

                    columnDefs: [
                        // first column, rank in group, is not orderable or searchable
                        {searchable: false, orderable: false, targets: rank_in_group_idx},
                        // {type: 'num', targets: numeric_columns},
                        {type: 'num', targets: [z_score_calc_idx]}, // z_score_calc_idx; otherwise doesn't sort numerically
                        {orderSequence: ['desc', 'asc'], targets: descending_columns},
                        // {targets: fantrax_score_idx,
                        //  render: function(data, type, row, meta) {
                        //         if (type === 'sort' && auto_assign_picks === true && row[position_idx] === "G") {
                        //             return (data * 0.7).toFixed(2);
                        //         } else {
                        //             return data;
                        //         }
                        //     },
                        // },
                        {targets: position_idx,
                            render: function(data, type, row) {
                                if (type === 'filter' || type === 'display') {
                                    if (['LW', 'C', 'RW'].includes(data)) {
                                        return 'F';
                                    }
                                    else {
                                        return data;
                                    }
                                }
                                return data;
                            }
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
                                    value: rowData => ['LW', 'C', 'RW', 'D'].includes(rowData[position_idx])
                                },
                                {
                                    label: 'F',
                                    value: rowData => ['LW', 'C', 'RW'].includes(rowData[position_idx])
                                },
                                {
                                    label: 'D',
                                    value: rowData => rowData[position_idx] === 'D'
                                },
                                {
                                    label: 'G',
                                    value: rowData => rowData[position_idx] === 'G'
                                },
                            ]
                        }, targets: position_idx},

                        // "injury" search pane
                        {searchPanes: {
                            show: true,
                            options: [
                                {
                                    label: '<i>No data</i>',
                                    value: rowData => {
                                        const injury_text = `${rowData[injury_idx]}`;
                                        return injury_text === '' ||
                                            !injury_text.startsWith('DAY-TO-DAY - ') &&
                                            !injury_text.startsWith('IR - ') &&
                                            !injury_text.startsWith('IR-LT - ') &&
                                            !injury_text.startsWith('IR-NR - ') &&
                                            !injury_text.startsWith('OUT - ');
                                    }
                                },
                                {
                                    label: 'DAY-TO-DAY',
                                    value: rowData => `${rowData[injury_idx]}`.startsWith('DAY-TO-DAY - ')
                                },
                                {
                                    label: 'IR',
                                    value: rowData => {
                                        const injury_text = `${rowData[injury_idx]}`;
                                        return injury_text.startsWith('IR - ') ||
                                            injury_text.startsWith('IR-LT - ') ||
                                            injury_text.startsWith('IR-NR - ');
                                    }
                                },
                                {
                                    label: 'OUT',
                                    value: rowData => `${rowData[injury_idx]}`.startsWith('OUT - ')
                                },
                            ],
                            dtOpts: {
                                select: 'single',
                                columnDefs: [
                                {
                                    targets: [0],
                                    render: (data, type, row, meta) => {
                                        if (type === 'sort') {
                                            const injuryOptOrder = {
                                            '<i>No data</i>': 1,
                                            'DAY-TO-DAY': 2,
                                            'IR': 3,
                                            'OUT': 4,
                                            }[data];
                                            return injuryOptOrder;
                                        } else {
                                            return data;
                                        }
                                    },
                                },
                                ],
                            },
                        }, targets: [injury_idx]},

                        // searchBuilder default conditions
                        {targets: [name_idx], searchBuilder: { defaultCondition: 'contains' } },
                        {targets: [
                                games_idx, goalie_starts_idx,
                                points_idx, goals_idx, pp_goals_p120_idx, assists_idx, ppp_idx,
                                sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx, pp_points_p120_idx,
                                toi_pp_percent_idx, toi_pp_percent_3gm_avg_idx, toi_minutes_idx,
                                z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_blk_idx, z_hits_idx, z_pim_idx, z_tk_idx,
                                z_wins_idx, z_saves_idx, z_saves_percent_idx, z_gaa_idx,
                                z_score_idx, z_offense_idx, z_peripheral_idx, z_combo_idx, z_g_count_idx, z_g_ratio_idx
                            ], searchBuilder: { defaultCondition: '>=' } },
                            {targets: [last_game_idx], searchBuilder: { defaultCondition: '>' } },
                        {targets: [age_idx, career_games_idx], searchBuilder: { defaultCondition: '<=' } },
                        {targets: [draft_position_idx, draft_round_idx, keeper_idx, manager_idx, minors_idx, nhl_roster_status_idx, picked_by_idx, position_idx, predraft_keeper_idx, prj_draft_round_idx, rookie_idx, team_idx, watch_idx], searchBuilder: { defaultCondition: '=' } },
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
                        {targets: career_games_idx, searchBuilderTitle: 'career games' },

                        // searchBuilder type columns
                        {targets: breakout_threshold_idx, searchBuilderType: 'num' },

                        // custom sort for 'prj draft round' column
                        // { targets: [prj_draft_round_idx], type: "custom_pdr_sort", orderSequence: ['asc']},

                        // custom sort for 'fantrax adp' column
                        // custom sort for 'line' and 'line prj' column
                        // custom sort for 'pp unit' and 'pp unit prj' column
                        // custom sort for 'athletic z-score rank' column
                        // custom sort for 'athletic z-score rank' column
                        // custom sort for 'dobber z-score rank' column
                        // custom sort for 'dtz z-score rank' column
                        // custom sort for 'fantrax z-score rank' column
                        { targets: [adp_idx, line_idx, pp_unit_idx, pp_unit_prj_idx, athletic_zscore_rank_idx, dfo_zscore_rank_idx, dobber_zscore_rank_idx, dtz_zscore_rank_idx, fantrax_zscore_rank_idx, draft_position_idx, draft_round_idx], type: "custom_integer_sort", orderSequence: ['asc']},

                        // custom sort for ''toi pg (trend)' column
                        // custom sort for 'toi even pg (trend)' column
                        // custom sort for 'toi pp pg (trend)' column
                        // custom sort for ''toi sh pg (trend)' column
                        { targets: [toi_pg_trend_idx, toi_even_pg_trend_idx, toi_pp_pg_trend_idx, toi_sh_pg_trend_idx], type: "custom_time_delta_sort", orderSequence: ['desc']},

                        // custom sort for 'breakout threshold' column
                        { targets: [breakout_threshold_idx], type: "custom_breakout_sort", orderSequence: ['asc']},

                        // skater scoring category heatmaps
                        { targets: Array.from(sktr_category_heatmap_columns),
                            createdCell: function (td, cellData, rowData, row, col) {
                                colourizeCell(td, col, rowData);

                            }
                        },

                        // goalie scoring category heatmaps
                        { targets: Array.from(goalie_category_heatmap_columns),
                            createdCell: function (td, cellData, rowData, row, col) {
                                colourizeCell(td, col, rowData);
                            }
                        },

                        // skater scoring category z-score heatmaps
                        { targets: Array.from(sktr_category_z_score_heatmap_columns),
                            createdCell: function (td, cellData, rowData, row, col) {
                                colourizeCell(td, col, rowData);
                            }
                        },

                        // goalie scoring category z-score heatmaps
                        { targets: Array.from(goalie_category_z_score_heatmap_columns),
                            createdCell: function (td, cellData, rowData, row, col) {
                                colourizeCell(td, col, rowData);
                            }
                        },

                        // z-score summary heatmaps
                        { targets: Array.from(z_score_summary_heatmap_columns),
                            createdCell: function (td, cellData, rowData, row, col) {
                                colourizeCell(td, col, rowData);
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
                            extend: 'excelHtml5',
                            text: 'Export to Excel',
                            exportOptions: {columns: ':visible'}
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
                                    text: 'Skater Summary Z-Scores',
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
                                    text: 'Goalie Summary Z-Scores',
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
                        // {
                        //     text: 'Hide Selected Rows',
                        //     extend: 'selected',
                        //     action: function (e, dt, node, config) {
                        //         hideRows(table)
                        //     }
                        // },
                        // {
                        //     text: 'Restore Hidden Rows',
                        //     action: function (e, dt, node, config) {
                        //         showRows(table)
                        //     }
                        // },
                        {
                            text: 'Toggle Heatmaps',
                            action: function (e, dt, node, config) {
                                toggleHeatmaps(table)
                            }
                        },
                        {
                            text: 'Unselect Rows',
                            action: function () {
                                // $(table.rows().nodes()).removeClass('selected');
                                $('.row-checkbox').prop('checked', false);
                                localStorage.setItem('selectedPlayerIds', JSON.stringify([]));

                                // Reapply the ""Selected Players" search pane filter
                                // Find the row that corresponds to the "Selected Players" option
                                var selectedPlayersRow = additionalFiltersSearchPaneDataTable.rows().indexes().filter(function(idx) {
                                    var row = additionalFiltersSearchPaneDataTable.row(idx).node();
                                    return $(row).hasClass('selected') && $(row).text() === 'Selected Players';
                                });
                                // If the "Selected Players" option is selected
                                if (selectedPlayersRow.length > 0) {
                                    additionalFiltersSearchPaneDataTable.row(selectedPlayersRow).select();
                                }
                            }
                        },
                    ],

                    initComplete: function () {

                        let playerStatsTable = $('#player_stats').DataTable();

                        lastSortIdx = playerStatsTable.order()[0][0];
                        lastSortOrder = true; // Always start with 1 to n ranking

                        // hide columns that are to be hidden on initial display
                        playerStatsTable.columns(initially_hidden_column_names).visible(show=false, redrawCalculations=false);

                        // save current & initial previous gameType (i.e., 'Regular Season')
                        $('#gameType').data('previous', '');
                        $('#gameType').data('current', gameType.value);
                        // set current & previous "pos" searchPane selection to '' (i.e., no selection)
                        $('#DataTables_Table_0').data('previous', '');
                        $('#DataTables_Table_0').data('current', '');
                        columnVisibility();

                        // set "name" as fixed column
                        setFixedColumn( playerStatsTable );

                        createManagerSummaryTable(playerStatsTable);

                        createMyCategoryNeedsTable();

                        // Create the allPlayers array
                        let allPlayers = getAllPlayers();

                        // create Category Scarcity by Z-score Range table
                        categoryScarcityByZScoreRange = calcCategoryScarcityByZScoreRange(allPlayers);
                        createCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);

                        // Filter out rows with no team manager
                        let allAvailablePlayers = allPlayers.filter(function (row) {
                            return row['manager'] === "";
                        });
                        // create Category Scarcity table
                        categoryScarcity = getCategoryScarcity(allAvailablePlayers);
                        createCategoryScarcityTable(categoryScarcity);

                        // updatePlayerStatsTable(data);

                        let api = this.api();
                        api.rows().every(function() {
                            let data = this.data();
                            let name = data[name_idx].match(/>(.*?)</)[1];
                            let index = this.index();
                            if (!nameToIndex[name]) {
                                nameToIndex[name] = [];
                            }
                            nameToIndex[name].push(index);
                        });
                    },

                    drawCallback: function() {

                        // get current sort columns
                        const table = $('#player_stats').DataTable();
                        let sort_idx = table.order()[0][0];
                        let sort_order = table.order()[0][1];

                        var api = this.api();
                        var prevSortValue = null;
                        var rank = 1;
                        var rankIncrement = 0;
                        // Loop through all rows and update the rank column
                        api.rows().every(function(rowIdx, tableLoop, rowLoop) {
                            var data = this.data();
                            var sortValue = data[sort_idx]; // Get the value of the sorted column
                            // If the sorted column value changes, increment the rank
                            if (prevSortValue != null && sortValue != prevSortValue) {
                                rank += rankIncrement;
                                rankIncrement = 1;
                            } else {
                                rankIncrement++;
                            }
                            data[rank_sort_idx] = lastSortOrder ? api.rows().count() - rank + 1 : rank; // Assign the rank
                            prevSortValue = sortValue; // Update the previous sorted column value
                            this.invalidate(); // Invalidate the data to refresh the table
                        });

                        // Restore the state of the checkboxes
                        // Get saved selected player_ids
                        var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds'));
                        api.rows().every(function(rowIdx, tableLoop, rowLoop) {
                            var row = this.data();
                            // var playerId = row[id_idx].match(/>(\d+)</)[1];
                            var playerId = row[id_idx];
                            var checkbox = $(this.node()).find('.row-checkbox');
                            if (selectedPlayerIds.includes(playerId)) {
                                checkbox.prop('checked', true);
                            } else {
                                checkbox.prop('checked', false);
                            }
                        });
                    }

                });

                // Use the order event to update lastSortIdx and lastSortOrder when the table is sorted
                $('#player_stats').on('order.dt', function() {
                    var table = $('#player_stats').DataTable();
                    lastSortIdx = table.order()[0][0];
                    lastSortOrder = table.order()[0][1] === 'desc' ? false : true;
                });

                // Display the checkboxes, calc z-score options, stat type & VORP checkbox
                document.getElementById('toggleCheckboxContainer').style.display = 'block';
                document.getElementById('calcZScoresContainer').style.display = 'block';
                // document.getElementById('showAsVorpContainer').style.display = 'block';

                // // search panes
                // new $.fn.dataTable.SearchPanes(table, {});
                // table.searchPanes.container().prependTo(table.table().container());
                // table.searchPanes.resizePanes();

                // *******************************************************************
                // select rows
                // $('#player_stats tbody').on('click', 'tr', function () {

                //     // $(this).toggleClass('selected');
                //     var checkbox = $(this).find('.row-checkbox');
                //     checkbox.prop('checked', !checkbox.prop('checked'));

                //     var playerId = $('#player_stats').DataTable().row(this).data()[id_idx].match(/>(\d+)</)[1];
                //     var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds')) || [];

                //     if (checkbox.prop('checked')) {
                //         // If the checkbox is checked, add the player ID to the array
                //         selectedPlayerIds.push(playerId);
                //     } else {
                //         // If the checkbox is unchecked, remove the player ID from the array
                //         selectedPlayerIds = selectedPlayerIds.filter(function(id) {
                //             return id !== playerId;
                //         });
                //     }

                $('#player_stats tbody').on('click', '.row-checkbox', function (event) {

                    var checkbox = $(this);
                    // checkbox.prop('checked', !checkbox.prop('checked'));

                    // var playerId = $('#player_stats').DataTable().row($(this).parents('tr')).data()[id_idx].match(/>(\d+)</)[1];
                    var playerId = $('#player_stats').DataTable().row($(this).parents('tr')).data()[id_idx];
                    var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds')) || [];

                    if (checkbox.prop('checked')) {
                        // If the checkbox is checked, add the player ID to the array
                        selectedPlayerIds.push(playerId);
                    } else {
                        // If the checkbox is unchecked, remove the player ID from the array
                        selectedPlayerIds = selectedPlayerIds.filter(function(id) {
                            return id !== playerId;
                        });
                    }

                    // Prevent the row click event from being triggered
                    event.stopPropagation();

                    // Save the updated array back to localStorage
                    localStorage.setItem('selectedPlayerIds', JSON.stringify(selectedPlayerIds));

                    // Reapply the ""Selected Players" search pane filter
                    // Find the row that corresponds to the "Selected Players" option
                    var selectedPlayersRow = additionalFiltersSearchPaneDataTable.rows().indexes().filter(function(idx) {
                        var row = additionalFiltersSearchPaneDataTable.row(idx).node();
                        return $(row).hasClass('selected') && $(row).text() === 'Selected Players';
                    });
                    // If the "Selected Players" option is selected
                    if (selectedPlayersRow.length > 0) {
                        additionalFiltersSearchPaneDataTable.row(selectedPlayersRow).select();
                    }

                });

                // *******************************************************************
                // remove() actually removes the rows. If you want to be able to restore
                // removed rows, maintain a list of removed rows
                // let removedRows = {};
                // $.fn.dataTable.Api.register('row().hide()', function(index) {
                // if (index && removedRows[index]) {
                //     // table.row.add($("<tr><td>1</td><td>2</td><td>3</td><td>4</td></tr>")).draw();
                //     let row = this.table().row.add(removedRows[index].html);
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
                    "custom_pdr_sort-asc": function (val1, val2) {

                        function getRange(val) {
                            const parts = val.split(/[ -]+/);
                            const [from, to] = parts.map(Number);
                            return [from, to || from];
                        }

                        if (val1 === '') {
                            return 1;
                        }

                        if (val2 === '') {
                            return -1;
                        }

                        let [from1, to1] = getRange(val1);
                        let [from2, to2] = getRange(val2);
                        if (from1 !== from2) {
                            return from1 - from2;
                        }
                        return to1 - to2;

                    },

                    // custom ascending sort for integer columns
                    "custom_integer_sort-asc": function (val1, val2) {

                        if (val1 === val2) {
                            return 0;
                        }
                        const num1 = parseFloat(val1);
                        const num2 = parseFloat(val2);
                        if (isNaN(num1)) {
                            // val1 is not a valid number, sort it to the bottom
                            return 1;
                        }
                        if (isNaN(num2)) {
                            // val2 is not a valid number, sort it to the bottom
                            return -1;
                        }
                        return num1 - num2;
                    },

                    // custom descending sort for delta time columns (e.g., toi trend)
                    "custom_time_delta_sort-desc": function (val1, val2) {
                        if (val1 === val2) {
                            return 0;
                        }
                        if (!val1) {
                            return 1;
                        }
                        if (!val2) {
                            return -1;
                        }

                        const prefix1 = val1.charAt(0);
                        const prefix2 = val2.charAt(0);

                        let timeParts = val1.substring((prefix1 === '+' || prefix1 === '-') ? 1 : 0).split(":");
                        let minutes = parseInt(timeParts[0]);
                        let seconds = parseInt(timeParts[1]);
                        const time1 = (prefix1 === '-' ? -1 : 1) * (minutes * 60 + seconds);

                        timeParts = val2.substring((prefix2 === '+' || prefix2 === '-') ? 1 : 0).split(":");
                        minutes = parseInt(timeParts[0]);
                        seconds = parseInt(timeParts[1]);
                        const time2 = (prefix2 === '-' ? -1 : 1) * (minutes * 60 + seconds);

                        if (time1 < time2) {
                            return 1;
                        } else if (time1 > time2) {
                            return -1;
                        } else {
                            return 0;
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

                    table.cells(null, rank_in_group_idx, { search: 'applied', order: 'applied' }).every(function (cell) {
                        this.data(i++);
                    });
                }).columns.adjust().draw();

                // // set "name" as fixed column
                // table.on('draw.dt column-visibility.dt', function () {

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
                const colvisButton = document.querySelector('.buttons-collection');

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

            }

            let calculatedPlayerSummaryZScores = calculatePlayerSummaryZScores();
            updatePlayerTableWithCalculatedSummaryZScores(calculatedPlayerSummaryZScores);

            const current_game_type =  $('#gameType').data('current');
            const previous_game_type = $('#gameType').data('previous');
            const regularOrPlayoffs = ['Regular Season', 'Playoffs'];
            if ((current_game_type === 'Projected Season' && regularOrPlayoffs.includes(previous_game_type))
                || (previous_game_type === 'Projected Season' && regularOrPlayoffs.includes(current_game_type))) {
                columnVisibility();
            }

            // show tables
            hidePulsingBarShowTables()

            // *******************************************************************
            $('#player_stats').DataTable().searchPanes.rebuildPane();

            // Reapply searchPane selections
            $.each(selectedOptions, function(id, options) {
                var table = $('#' + id).DataTable();
                table.rows().every(function(rowIdx) {
                    var optionText = this.data().display
                    if (options.includes(optionText)) {
                        this.select();
                    }
                });
            });

            positionSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[1]).DataTable();
            additionalFiltersSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[7]).DataTable();
            // "DataTables_Table_0" is "pos" searchPane
            $('#DataTables_Table_0').DataTable().on('user-select', function(e, dt, type, cell, originalEvent){
                // save "pos" searchPane selection as "current"
                if ( $('#DataTables_Table_0').data('previous') === cell.data() ) {
                    $('#DataTables_Table_0').data('current', '');
                } else {
                    $('#DataTables_Table_0').data('current', cell.data());
                }
                columnVisibility();
            });
            // *******************************************************************

            // Get saved selected player_ids
            var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds'));
            // Reapply 'selected' class
            if (selectedPlayerIds) {
                let table = $('#player_stats').DataTable();
                table.rows().every(function() {
                    var row = this.data();
                    // var playerId = row[id_idx].match(/>(\d+)</)[1];
                    var playerId = row[id_idx];
                    // if (selectedPlayerIds.includes(playerId)) {
                    //     $(this.node()).addClass('selected');
                    // }
                    var checkbox = $(this.node()).find('.row-checkbox');
                    if (selectedPlayerIds.includes(playerId)) {
                        checkbox.prop('checked', true);
                    } else {
                        checkbox.prop('checked', false);
                    }
                });
            }

        }
    } );

})

document.getElementById('startDraftButton').addEventListener('click', () => {

    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

    let playerStatsTable = $('#player_stats').DataTable();
    playerStatsTable.searchBuilder.rebuild(baseSearchBuilderCriteria);

    getDraftPicks(draft_order => {

        remaining_draft_picks = draft_order;
        draft_manager = remaining_draft_picks[0].manager;

        clearDraftColumns();

        // let playerStatsTable = $('#player_stats').DataTable();
        managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);
        updateManagerSummaryTable(managerSummaryZScores);

        // data = calcManagerCategoryNeedsData();
        myCategoryNeeds = getMyCategoryNeeds()
        updateMyCategoryNeedsTable(myCategoryNeeds);

        // trigger click event on calcSummaryZScoresButton
        document.querySelector('#calcSummaryZScoresButton').dispatchEvent(new Event('click'));

        let caption = updateCaption();
        let tableCaption = document.querySelector('#managerSummary caption');

        tableCaption = document.querySelector('#managerSummary caption');
        tableCaption.textContent = caption + ' - Manager Z-Scores';
        tableCaption.style.fontWeight = 'bold';
        tableCaption.style.textDecoration = 'underline';

        tableCaption = document.querySelector('#managerCategoryNeedsContainerCaption');
        tableCaption.textContent = 'Manager Category Needs';
        tableCaption.style.fontWeight = 'bold';
        tableCaption.style.textDecoration = 'underline';

        document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';

        createDraftBoardTable(remaining_draft_picks)

        // hide not-useful columns
        columns_to_hide = [manager_idx, line_idx, pp_unit_idx, toi_even_pg_idx, corsi_for_percent_idx, toi_pp_pg_idx, pp_percent_idx, shooting_percent_idx, goalie_starts_idx, qualtity_starts_idx, qualtity_starts_percent_idx, really_bad_starts_idx];
        playerStatsTable.columns(columns_to_hide).visible(show=false, redrawCalculations=false);

        // columns to show
        columns_to_be_visible = [fantrax_score_idx, z_score_calc_idx, z_offense_calc_idx, z_peripheral_calc_idx, z_g_count_calc_idx, z_g_ratio_calc_idx];
        playerStatsTable.columns(columns_to_be_visible).visible(show=true, redrawCalculations=false);

        // Hide pulsing bar
        document.getElementById('pulsing-bar').style.display = 'none';

        $('#draftMessage').show();
        $('#draftBoard').show();

        // need to remove the `.hidden` class from the element first, as `display: none` takes precedence over any other `display`
        // declaration, even if it is added dynamically with JavaScript.
        $('#autoAssignDraftPicksContainer').removeClass('hidden').css('display', 'inline-block');
        $('#undoDraftPick').removeClass('hidden').css('display', 'inline-block');

        let managerSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[5]).DataTable();
        managerSearchPaneDataTable.rows(function(idx, data, node) {
            return data.display.includes('No data');
        }).select();

        initDraftContextMenu();

    });
})

document.getElementById('undoDraftPick').addEventListener('click', () => {

    undoDraftPick();

})

document.getElementById('calcSummaryZScoresButton').addEventListener('click', () => {

    let calculatedPlayerSummaryZScores = calculatePlayerSummaryZScores();
    updatePlayerTableWithCalculatedSummaryZScores(calculatedPlayerSummaryZScores);

})

// the assignDraftPick function performs one iteration of the while loop from your original code.
// After each iteration, it calls itself again using setTimeout, with a delay of 0 milliseconds.
// This allows the browser to update the page and respond to user input between each iteration.
function assignDraftPick(playerStatsTable, managerSummaryDataTable, managerSearchPaneDataTable) {

    // Reset search panes
    playerStatsTable.searchPanes.clearSelections();
    managerSearchPaneDataTable.rows(function(idx, data, node) {
        return data.display.includes('No data');
    }).select();

    // Reset search builder selections
    let currentSearchBuilderDetails = playerStatsTable.searchBuilder.getDetails();
    if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
        playerStatsTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
    }

    let managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];
    let fCount = managerSummaryData['fCount'];
    let dCount = managerSummaryData['dCount'];
    let gCount = managerSummaryData['gCount'];
    let mfCount = managerSummaryData['mfCount'];
    let picks = managerSummaryData['picks'];

    // probably only a maximum of 12 forwards & 8 defensemen, or 11 forwards & 9 defensemen, to ensure 4 goalies drafted
    if ((fCount === 11 && dCount === 9) || (fCount === 12 && dCount === 8)) {
        if (!f_limit_reached.includes(draft_manager)) {
            f_limit_reached.push(draft_manager);
        }
        if (!d_limit_reached.includes(draft_manager)) {
            d_limit_reached.push(draft_manager);
        }
    // probably only a maximum of 12 forwards
    } else if (fCount === 12) {
        if (!f_limit_reached.includes(draft_manager)) {
            f_limit_reached.push(draft_manager);
        }
    // probably only a maximum of 9 defensemen
    } else if (dCount === 9) {
        if (!d_limit_reached.includes(draft_manager)) {
            d_limit_reached.push(draft_manager);
        }
    }

    // can only a maximum of 4 goalies
    if (gCount === 4) {
        if (!g_limit_reached.includes(draft_manager)) {
            g_limit_reached.push(draft_manager);
        }
    }

    let overall_pick = remaining_draft_picks[0].overall_pick;
    let managers_pick_number = remaining_draft_picks[0].managers_pick_number;

    // if (draft_manager === 'Shawsome1' && managers_pick_number === 2) {
    //     positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
    //         posOpt = this.data().display;
    //         if (posOpt === 'G') {
    //             this.select();
    //         }
    //     });
    // }

    // force Jason's preference for 1F & 4D before a goalie is picked
    if (draft_manager === "Fowler's Flyers" && managers_pick_number < 6) {
        // Clear position search pane selections
        positionSearchPaneDataTable.searchPanes.clearSelections();
        // Jason started draft with 8 Fs & 3 Ds
        let position = 'Sktr';
        if (fCount === 9) {
            position = 'D';
        } else if (dCount === 7) {
            position = 'F';
        }
        positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
            posOpt = this.data().display;
            if (posOpt === position) {
                this.select();
            }
        });
    // force goalie selection if not at "acceptable" level by specific pick numbers
    } else if ((gCount === 0 && managers_pick_number === 3) || (gCount === 1 && managers_pick_number === 6) || (gCount === 2 && managers_pick_number === 9) || (gCount === 3 && managers_pick_number === 12)) {
        // Clear position search pane selections
        positionSearchPaneDataTable.searchPanes.clearSelections();
        positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
            posOpt = this.data().display;
            if (posOpt === 'G') {
                this.select();
            }
        });
    } else if (f_limit_reached.includes(draft_manager) || d_limit_reached.includes(draft_manager) || g_limit_reached.includes(draft_manager)) {
        positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
            posOpt = this.data().display;
            if (!f_limit_reached.includes(draft_manager) && !d_limit_reached.includes(draft_manager)) {
                if (posOpt === 'Sktr') {
                    this.select();
                }
            }
            else if (!f_limit_reached.includes(draft_manager)) {
                if (posOpt === 'F') {
                    this.select();
                }
            }
            else if (!d_limit_reached.includes(draft_manager)) {
                if (posOpt === 'D') {
                    this.select();
                }
            }
            if (!g_limit_reached.includes(draft_manager)) {
                if (posOpt === 'G') {
                    if ((gCount === 0) || (gCount === 1 && managers_pick_number > 5) || (gCount === 2 && managers_pick_number >= 8) || (gCount === 3 && managers_pick_number >= 11)) {
                        this.select();
                    }
                }
            // } else if (f_limit_reached.includes(draft_manager) && d_limit_reached.includes(draft_manager)) {
            //     if (posOpt === 'Sktr') {
            //         this.select();
            //     }
            }
        });
    }

    // // Get data for selected rows
    // var selectedPositions = positionSearchPaneDataTable.rows({ selected: true }).data();
    // var dSelected = false;
    // var fSelected = false;
    // var gSelected = false;
    // var sktrSelected = false;
    // for (var i = 0; i < selectedPositions.length; i++) {
    //     // the value is in the first column
    //     var value = selectedPositions[i].display;
    //     if (value === 'D') {
    //         dSelected = true;
    //     } else if (value === 'F') {
    //         fSelected = true;
    //     } else if (value === 'G') {
    //         gSelected = true;
    //     } else if (value === 'Sktr') {
    //         sktrSelected = true;
    //     }
    // }

    // let count = positionSearchPaneDataTable.rows({ selected: true }).count();

    // // force Jason's preference for 1F & 4D before a goalie is picked
    // if (draft_manager === "Fowler's Flyers" && managers_pick_number < 6) {
    //     // Clear position search pane selections
    //     positionSearchPaneDataTable.searchPanes.clearSelections();
    //     // Jason started draft with 8 Fs & 3 Ds
    //     let position = 'Sktr';
    //     if (fCount === 9) {
    //         position = 'D';
    //     } else if (dCount === 7) {
    //         position = 'F';
    //     }
    //     positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
    //         posOpt = this.data().display;
    //         if (posOpt === position) {
    //             this.select();
    //         }
    //     });
    // // force non-goalie selection if not at "acceptable" level by specific pick numbers
    // } else if (((gCount === 1 && managers_pick_number < 3) || (gCount === 2 && managers_pick_number < 6) || (gCount === 3 && managers_pick_number < 9))
    //             && count === 0) {
    //     positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
    //         posOpt = this.data().display;
    //         if (posOpt === 'Sktr') {
    //             this.select();
    //         }
    //     });
    // // force goalie selection if not at "acceptable" level by specific pick numbers
    // } else if ((gCount === 0 && managers_pick_number === 3) || (gCount === 1 && managers_pick_number === 6) || (gCount === 2 && managers_pick_number === 9) || (gCount === 3 && managers_pick_number === 12)) {
    //     // Clear position search pane selections
    //     positionSearchPaneDataTable.searchPanes.clearSelections();
    //     positionSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
    //         posOpt = this.data().display;
    //         if (posOpt === 'G') {
    //             this.select();
    //         }
    //     });
    // }

    // // the following is for debug purposes; should never have 'D' & 'Sktr" or 'F' & 'Sktr' selected, or 'G' & 'Sktr'
    // let count = positionSearchPaneDataTable.rows({ selected: true }).count();

    if ((managers_pick_number === 13 && mfCount === 0) || (managers_pick_number === 14 && mfCount === 1)) {
        additionalFiltersSearchPaneDataTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
            filterOpt = this.data().display;
            if (filterOpt === 'Minors (Fantasy)') {
                this.select();
            }
        });
    }

    if (draft_manager === 'Banshee') {
        playerStatsTable.order([z_score_calc_idx, 'desc'], [z_score_idx, 'desc']);

        // Manually select player
        // mySearchBuilderCriteria = {
        //     "criteria": [
        //         {
        //             "condition": "!=",
        //             "data": "team",
        //             "type": "html",
        //             "value": ["(N/A)"]
        //         },
        //         {
        //             "condition": "<=",
        //             "data": "age",
        //             "type": "num",
        //             "value": [
        //                 "27"
        //             ]
        //         }
        //     ],
        //     "logic": "AND"
        // }
        // playerStatsTable.searchBuilder.rebuild(mySearchBuilderCriteria);

        let manuallySelectMyPicks = document.getElementById('manuallySelectMyPicks').checked;
        if (manuallySelectMyPicks === true) {
            playerStatsTable.draw();
            return;
        }

    } else if (draft_manager === "Fowler's Flyers") {
        playerStatsTable.order([z_score_idx, 'desc']);
    } else {
        // playerStatsTable.order([fantrax_score_idx, 'desc']);
        // playerStatsTable.order([adp_idx, 'asc']); // This will generally keep players with few project games from being auto-picked
        // playerStatsTable.order([prj_draft_round_idx, 'asc'], [fantrax_score_idx, 'desc']);
        playerStatsTable.order([prj_draft_round_idx, 'asc'], [fantrax_score_idx, 'desc']);
    }

    playerStatsTable.draw();

    // Get row indexes in filtered and sorted order
    // randomly select one of first x rows
    let filteredSortedIndexes = playerStatsTable.rows({order: 'current', search: 'applied'}).indexes().toArray();
    let randomIndex = Math.floor(Math.random() * 5);
    let selectedRow = filteredSortedIndexes[randomIndex];

    let player_name;
    if (draft_manager === 'Horse Palace 26' && overall_pick === 1 ) {
        player_name = 'Connor Bedard';
    } else if (draft_manager === 'Shawsome1' && overall_pick === 2 ) {
        player_name = 'Clayton Keller';
    } else if (draft_manager === 'WhatA LoadOfIt' && overall_pick === 3 ) {
        player_name = 'Cole Caufield';
    } else if (draft_manager === 'Horse Palace 26' && overall_pick === 4 ) {
        player_name = 'Dylan Cozens';
    } else if (draft_manager === 'Shawsome1' && overall_pick === 5 ) {
        player_name = 'Adam Fantilli';
    }

    if (player_name) {
        var playerIndex = nameToIndex[player_name];

        // draftSearchBuilderCriteria = {
        //     "criteria": [
        //         {
        //             "condition": "=",
        //             "data": "name",
        //             "type": "str",
        //             "value": [player_name]
        //         }
        //     ],
        //     "logic": "AND"
        // }
        // playerStatsTable.searchBuilder.rebuild(draftSearchBuilderCriteria);
        // selectedRow = playerStatsTable.rows({order: 'current', search: 'applied'}).indexes().toArray()[0];
        if (playerIndex.length === 1) {
            selectedRow = playerIndex[0];
        }
    }

    if (assignManager(playerStatsTable, selectedRow, draft_manager, managerSummaryDataTable) === false) {
        auto_assign_picks = false;
        return;
    }

    setTimeout(function() {
        assignDraftPick(playerStatsTable, managerSummaryDataTable, managerSearchPaneDataTable);
    }, 0);

}

// Assign manager
function assignManager(playerStatsTable, rowIndex, manager, managerSummaryDataTable) {

    playerStatsTable.cell(rowIndex, manager_idx).data(manager);
    playerStatsTable.cell(rowIndex, draft_round_idx).data(remaining_draft_picks[0].draft_round);
    playerStatsTable.cell(rowIndex, draft_position_idx).data(remaining_draft_picks[0].round_pick);
    playerStatsTable.cell(rowIndex, draft_overall_pick_idx).data(remaining_draft_picks[0].overall_pick);
    playerStatsTable.cell(rowIndex, picked_by_idx).data(manager);

    // When a player is drafted...
    let round = remaining_draft_picks[0].draft_round;  // The round number
    let pick = remaining_draft_picks[0].round_pick;  // The pick number

    let playerName = playerStatsTable.cell(rowIndex, name_idx).data().match(/>(.*?)</)[1];  // The name of the drafted player

    // add the player to remaining_draft_picks
    remaining_draft_picks[0].drafted_player = playerName;

    let position = playerStatsTable.cell(rowIndex, position_idx).data(); // postion for the drafted player
    if (['LW', 'C', 'RW'].includes(position)) {
        position = 'F'
    }
    playerName = playerName + ' (' + position + ')';
    let tableData = $('#draftBoard').DataTable();
    // Find the corresponding cell in tableData and update it
    let cell = tableData.cell((round - 1) * 2 + 1, pick); // Get the cell object
    cell.data(playerName);
    // // Redraw the table
    // tableData.draw();

    managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);
    updateManagerSummaryTable(managerSummaryZScores);

    // data = calcManagerCategoryNeedsData();
    myCategoryNeeds = getMyCategoryNeeds()
    updateMyCategoryNeedsTable(myCategoryNeeds);

    // remove the first element from remaining_draft_picks and return that element removed
    let completedPick = remaining_draft_picks.shift();
    completed_draft_picks.push(completedPick);
    if (remaining_draft_picks.length > 0) {
        draft_manager = remaining_draft_picks[0].manager;
    }

    let calculatedPlayerSummaryZScores = calculatePlayerSummaryZScores();
    updatePlayerTableWithCalculatedSummaryZScores(calculatedPlayerSummaryZScores);

    if (remaining_draft_picks.length > 0) {
        managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];
        // manager_selection_number = (15 - managerSummaryData.picks);
        document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';
        return true;
    } else {
        document.getElementById("draftMessage").innerHTML = "All rounds are completed.";
        destroyDraftContextMenu();
        return false;
    }

}

// break up autoAssignDraftPicks(), a long-running operation, into smaller chunks by wrapping it and the subsequent operations with assignDraftPick(),
// and then calling assignDraftPick() repeatedly using setTimeout
function autoAssignDraftPicks() {

    auto_assign_picks = true; // global

    // remove rows with manager
    // $.fn.dataTable.ext.search.push(
    //     function(settings, data, dataIndex) {
    //         if (settings.nTable.id === 'player_stats' && auto_assign_picks === true) {
    //             return (data[manager_idx] === '') ? true : false;
    //         }
    //         return true;
    //     }
    // );
    let managerSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[5]).DataTable();
    managerSearchPaneDataTable.rows(function(idx, data, node) {
        return data.display.includes('No data');
    }).select();

    // // don't want goalies with less than 20 starts
    // $.fn.dataTable.ext.search.push(
    //     function(settings, data, dataIndex) {
    //         if (settings.nTable.id === 'player_stats' && auto_assign_picks === true && data[position_idx] === 'G') {
    //             return (data[games_idx] >= 20) ? true : false;
    //         }
    //         return true;
    //     }
    // );

    // // Clear all search pane & serach builder selections, which may have been set manually
    // let table = $('#player_stats').DataTable();
    // table.searchPanes.clearSelections();
    // table.searchBuilder.rebuild();
    let playerStatsTable = $('#player_stats').DataTable();
    let managerSummaryDataTable = $('#managerSummary').DataTable();
    assignDraftPick(playerStatsTable, managerSummaryDataTable, managerSearchPaneDataTable);

    // // Clear all search pane & serach builder selections, which may have been set programatically
    // table.searchPanes.clearSelections();
    // table.searchBuilder.rebuild();

}

function calcCategoryScarcityByZScoreRange(players) {

    let zScoreMinimum = 6.5;
    let zScoreMaximum = zScoreMinimum + 0.49;
    let categoryScarcityByZScoreRange = [];
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
            let zScoreRange = `${zScoreMinimum} - ${zScoreMaximum}`;
            // the square brackets ([]) around the zScoreRange variable tell JavaScript to use the value of the zScoreRange variable as the property name.
            // This means that the property name will be "5 - 5.49", for example, instead of "zScoreRange"
            categoryScarcityByZScoreRange.push({[zScoreRange]: {'points': dPointsZScorePlayerCounts, 'goals': goalsZScorePlayerCounts, 'assists': assistsZScorePlayerCounts, 'powerplayPoints': powerplayPointsZScorePlayerCounts, 'shotsOnGoal': shotsOnGoalZScorePlayerCounts, 'hits': hitsZScorePlayerCounts, 'blockedShots': blockedShotsZScorePlayerCounts, 'takeaways': takeawaysZScorePlayerCounts, 'penaltyMinutes': penaltyMinutesZScorePlayerCounts, 'wins': winsZScorePlayerCounts, 'saves': savesZScorePlayerCounts, 'gaa': gaaZScorePlayerCounts, 'savePercent': savePercentZScorePlayerCounts, }});
        }

        zScoreMinimum -= 0.5;
        zScoreMaximum = zScoreMinimum + 0.49;
    }

    // This code calculates the totals for each category across all elements in categoryScarcityByZScoreRange and stores the result in the totals variable.
    // Then, a new element is added to the end of myArray with a property named "Totals" and a value equal to the totals object.
    // The reduce method takes a callback function and an initial value as arguments.
    // The callback function takes two arguments: an accumulator (acc) and the current element (curr).
    // The callback function uses two nested forEach loops to iterate over the keys of the current element
    // and the keys of the categories object within the current element.
    // For each category, the value is added to the accumulator object, creating a new property if it doesn’t already exist.
    // The initial value of the accumulator is set to an empty object.
    let totals = categoryScarcityByZScoreRange.reduce((acc, curr) => {
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

    categoryScarcityByZScoreRange.push({'Totals': totals});

    return categoryScarcityByZScoreRange;

}

function calcManagerSummaryZScores(playerStatsTable) {

    // Get data from player stats table
    let originalPlayerStatsTableData = playerStatsTable.data().toArray();

    // Filter out rows with no team manager
    let rosteredPlayers = originalPlayerStatsTableData.filter(function (row) {
        return row[manager_idx] !== "";
        // return row[manager_idx] !== "" && row[keeper_idx] === 'Yes';
    });

    // Create new data source for new table
    let data = [];

    // Loop through original data and calculate sums for each team manager
    for (let i = 0; i < rosteredPlayers.length; i++) {
        let row = rosteredPlayers[i];

        let manager = row[manager_idx];

        let position = row[position_idx];

        let careerGames = row[career_games_idx];

        // Check if team manager already exists in new data
        let index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        if (index === -1) {
            // Team manager does not exist in new data, add new row
            data.push({
                manager: manager,
                picks: 25, // 25 because loop starts with 0; actual picks will start at 14, during draft simulation, but to start include 12 keepers
                fCount: (position !== 'G' && position !== 'D') ? 1 : 0,
                dCount: (position === 'D') ? 1 : 0,
                gCount: (position === 'G') ? 1 : 0,
                mfCount: (position !== 'G' && careerGames < 160) || (position === 'G' && careerGames < 80) ? 1 : 0,
                zScore: 0,
                zScoreSktr: 0,
                zOffense: 0,
                zPeripheral: 0,
                points: 0,
                goals: 0,
                assists: 0,
                powerplayPoints: 0,
                shotsOnGoal: 0,
                blockedShots: 0,
                hits: 0,
                takeaways: 0,
                penaltyMinutes: 0,
                zScoreG: 0,
                zCountG: 0,
                zRatioG: 0,
                wins: 0,
                saves: 0,
                gaa: 0,
                savePercent: 0,
            });
        } else {
            // Team manager exists in new data, update row
            data[index].fCount += (position !== 'G' && position !== 'D') ? 1 : 0;
            data[index].dCount += (position === 'D') ? 1 : 0;
            data[index].gCount += (position === 'G') ? 1 : 0;
            data[index].mfCount += (position !== 'G' && careerGames < 160) || (position === 'G' && careerGames < 80) ? 1 : 0,
            data[index].picks -= 1
        }
    }

    for(let i = 0; i < data.length; i++) {
        if(data[i]['picks'] < 0) {
            data[i]['picks'] = 0;
        }
    }

    // Group data by manager_idx and position_idx
    let groupedData = rosteredPlayers.reduce(function (r, a) {
        // Exclude rows with 'IR' or 'Min' in fantrax_roster_status_idx
        if (a[fantrax_roster_status_idx] === 'IR' || a[fantrax_roster_status_idx] === 'Min') {
            return r;
        }

        r[a[manager_idx]] = r[a[manager_idx]] || {};
        let position = ['LW', 'C', 'RW'].includes(a[position_idx]) ? 'F' : a[position_idx];
        r[a[manager_idx]][position] = r[a[manager_idx]][position] || [];
        r[a[manager_idx]][position].push(a);
        return r;
    }, {});

    // Sort and filter data within each group
    rosteredPlayers = [];
    for (let manager in groupedData) {
        for (let position in groupedData[manager]) {
            // Sort data based on z_score_idx in descending order
            groupedData[manager][position].sort(function(a, b) {
                return b[z_score_idx] - a[z_score_idx];
            });

            // Filter top rows based on position
            if (position === 'F') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 9));
            } else if (position === 'D') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 6));
            } else if (position === 'G') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 2));
            }
        }

        // Add the top row from either 'F' or 'D' that is not already in the top 9 for 'F' or top 6 for 'D'
        let additionalRow = ['F', 'D'].map(pos => groupedData[manager][pos]).flat().sort((a, b) => b[z_score_idx] - a[z_score_idx]).find(item => !rosteredPlayers.includes(item));
        if (additionalRow) {
            rosteredPlayers.push(additionalRow);
        }

    }

    // Loop through original data and calculate sums for each team manager
    for (let i = 0; i < rosteredPlayers.length; i++) {
        let row = rosteredPlayers[i];

        // let player_id = row[id_idx].match(/>(\d+)</)[1];;
        let player_id = row[id_idx];
        let player_position = row[position_idx];

        let manager = row[manager_idx];

        let zScore = parseFloat(row[z_score_idx]);
        if (isNaN(zScore)) {zScore = 0;}

        let zScoreSktr = parseFloat(row[z_score_idx]);
        if (isNaN(zScoreSktr) || row[position_idx] === 'G') {zScoreSktr = 0;}

        let zOffense = parseFloat(row[z_offense_idx]);
        if (isNaN(zOffense)) {zOffense = 0;}

        let zPeripheral = parseFloat(row[z_peripheral_idx]);
        if (isNaN(zPeripheral)) {zPeripheral = 0;}

        let points = parseFloat(row[z_points_idx]);
        if (isNaN(points) || points < 0 || row[position_idx] !== 'D') {points = 0;}

        let goals = parseFloat(row[z_goals_idx]);
        if (isNaN(goals) || goals < 0) {goals = 0;}

        let assists = parseFloat(row[z_assists_idx]);
        if (isNaN(assists) || assists < 0) {assists = 0;}

        let powerplayPoints = parseFloat(row[z_ppp_idx]);
        if (isNaN(powerplayPoints) || powerplayPoints < 0) {powerplayPoints = 0;}

        let shotsOnGoal = parseFloat(row[z_sog_idx]);
        if (isNaN(shotsOnGoal) || shotsOnGoal < 0) {shotsOnGoal = 0;}

        let blockedShots = parseFloat(row[z_blk_idx]);
        if (isNaN(blockedShots) || blockedShots < 0) {blockedShots = 0;}

        let hits = parseFloat(row[z_hits_idx]);
        if (isNaN(hits) || hits < 0) {hits = 0;}

        let takeaways = parseFloat(row[z_tk_idx]);
        if (isNaN(takeaways) || takeaways < 0) {takeaways = 0;}

        let penaltyMinutes = parseFloat(row[z_pim_idx]);
        if (isNaN(penaltyMinutes) || penaltyMinutes < 0) {penaltyMinutes = 0;}

        let zScoreG = parseFloat(row[z_score_idx]);
        if (isNaN(zScoreG) || row[position_idx] !== 'G') {zScoreG = 0;}

        let zCountG = parseFloat(row[z_g_count_idx]);
        if (isNaN(zCountG) || row[position_idx] !== 'G') {zCountG = 0;}

        let zRatioG = parseFloat(row[z_g_ratio_idx]);
        if (isNaN(zRatioG) || row[position_idx] !== 'G') {zRatioG = 0;}

        let wins = parseFloat(row[z_wins_idx]);
        if (isNaN(wins) || wins < 0) {wins = 0;}

        let saves = parseFloat(row[z_saves_idx]);
        if (isNaN(saves) || saves < 0) {saves = 0;}

        let gaa = parseFloat(row[z_gaa_idx]);
        if (isNaN(gaa)) {gaa = 0;}

        let savePercent = parseFloat(row[z_saves_percent_idx]);
        if (isNaN(savePercent)) {savePercent = 0;}

        // Find team manager row index
        let index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        // Team manager exists in new data, update row
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

    // Loop through new data and set floats to 1 & 2 decimal places
    for (let i = 0; i < data.length; i++) {
        let row = data[i];
        data[i].zScore = (row.zScoreSktr + row.zScoreG).toFixed(1);
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
        data[i].gaa = (row.gaa/row.gCount).toFixed(2);
        data[i].savePercent = (row.savePercent/row.gCount).toFixed(2);
    };

    // get maximum category z-scores
    maxCategoryValues['zScores']['points'] = Math.max.apply(Math, data.map(function(item) { return item.points; }))
    maxCategoryValues['zScores']['goals'] = Math.max.apply(Math, data.map(function(item) { return item.goals; }))
    maxCategoryValues['zScores']['assists'] = Math.max.apply(Math, data.map(function(item) { return item.assists; }))
    maxCategoryValues['zScores']['powerplayPoints'] = Math.max.apply(Math, data.map(function(item) { return item.powerplayPoints; }))
    maxCategoryValues['zScores']['shotsOnGoal'] = Math.max.apply(Math, data.map(function(item) { return item.shotsOnGoal; }))
    maxCategoryValues['zScores']['hits'] = Math.max.apply(Math, data.map(function(item) { return item.hits; }))
    maxCategoryValues['zScores']['blockedShots'] = Math.max.apply(Math, data.map(function(item) { return item.blockedShots; }))
    maxCategoryValues['zScores']['takeaways'] = Math.max.apply(Math, data.map(function(item) { return item.takeaways; }))
    maxCategoryValues['zScores']['penaltyMinutes'] = Math.max.apply(Math, data.map(function(item) { return item.penaltyMinutes; }))
    maxCategoryValues['zScores']['wins'] = Math.max.apply(Math, data.map(function(item) { return item.wins; }))
    maxCategoryValues['zScores']['saves'] = Math.max.apply(Math, data.map(function(item) { return item.saves; }))
    maxCategoryValues['zScores']['gaa'] = Math.max.apply(Math, data.map(function(item) { return item.gaa; }))
    maxCategoryValues['zScores']['savePercent'] = Math.max.apply(Math, data.map(function(item) { return item.savePercent; }))

    return data;

}

function calcPositionCategoryZScores(player_stats) {
    // Define the positions and their respective z-scores
    const positionCategories = {
        'Forward': {'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
        'Defence': {'z_points': z_points_idx, 'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
        'Goalie': {'z_wins': z_wins_idx, 'z_saves': z_saves_idx, 'z_saves_percent': z_saves_percent_idx, 'z_gaa': z_gaa_idx}
    };

    // Initialize the result array
    let replacementPlayerZscores = {};

    // Iterate over each position
    for (let position in positionCategories) {
        replacementPlayerZscores[position] = {};

        // Filter the players based on the position and whether they are drafted
        let poolTeamPlayers = player_stats.filter(player => {
            if (position === "Forward") {
                return ["LW", "C", "RW"].includes(player[position_idx]) && player[manager_idx];
            } else if (position === "Defence") {
                return player[position_idx] === "D" && player[manager_idx];
            } else if (position === "Goalie") {
                return player[position_idx] === "G" && player[manager_idx];
            }
        });

        // Filter the players based on the position
        let allPlayers = player_stats.filter(player => {
            if (position === "Forward") {
                return ["LW", "C", "RW"].includes(player[position_idx]);
            } else if (position === "Defence") {
                return player[position_idx] === "D";
            } else if (position === "Goalie") {
                return player[position_idx] === "G";
            }
        });

        // Iterate over each category for the current position
        for (let category in positionCategories[position]) {
            let tableIndex = positionCategories[position][category];
            // Filter out rows where column with index = tableIndex has a non-blank value
            let filteredPlayers = allPlayers.filter(player => player[tableIndex] !== '');
            // Sort the players based on the category
            // The subtraction operation (b[tableIndex] - a[tableIndex]) in the sort function ensures that JavaScript treats the values as numbers, not strings
            filteredPlayers.sort((a, b) => b[tableIndex] - a[tableIndex]);
            // Find the "count + 1" value in category
            replacementPlayerZscores[position][category] = filteredPlayers[poolTeamPlayers.length] ? parseFloat(filteredPlayers[poolTeamPlayers.length][tableIndex]) : null;
        }
    }

    return replacementPlayerZscores;
}

// function calcPlayerVorpZsores(playerStatsTable, replacementPlayerZscores) {
//     // Define the positions and their respective z-scores
//     const positionCategories = {
//         'Forward': {'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Defence': {'z_points': z_points_idx, 'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Goalie': {'z_wins': z_wins_idx, 'z_saves': z_saves_idx, 'z_saves_percent': z_saves_percent_idx, 'z_gaa': z_gaa_idx}
//     };

//     const forwardOffenseCategories = ['z_goals', 'z_assists', 'z_ppp', 'z_sog'];
//     const defenceOffenseCategories = ['z_points', 'z_goals', 'z_assists', 'z_ppp', 'z_sog'];
//     const peripheralCategories = ['z_tk', 'z_hits', 'z_blk', 'z_pim'];

//     // Iterate over each player
//     playerStatsTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
//         var player = this.data();
//         // Determine the player's position
//         let position;
//         if (["LW", "C", "RW"].includes(player[position_idx])) {
//             position = "Forward";
//         } else if (player[position_idx] === "D") {
//             position = "Defence";
//         } else if (player[position_idx] === "G") {
//             position = "Goalie";
//         }

//         player[z_score_calc_idx] = 0;
//         player[z_offense_calc_idx] = 0;
//         player[z_peripheral_calc_idx] = 0;
//         player[z_g_count_calc_idx] = 0;
//         player[z_g_ratio_calc_idx] = 0;
//         // If the player's position is one of the positions in replacementPlayerZscores
//         if (position && replacementPlayerZscores[position]) {
//             // Iterate over each z-score for the current position
//             categories = positionCategories[position];
//             for (let category in categories) {
//                 // takeaways are not estimated for rookies, and player[categories[category]] will be ''
//                 let vorp_score = 0;
//                 if (player[categories[category]]) {
//                     // Subtract the corresponding category z-score from the player's z-score
//                     vorp_score = parseFloat(player[categories[category]]) - replacementPlayerZscores[position][category];
//                     // Assign the new value to a property with the same name as in "replacementPlayerZscores" but suffixed with "_vorp"
//                     this.cell(rowIdx, categories[category]).data(vorp_score.toFixed(2));
//                 } else {
//                     this.cell(rowIdx, categories[category]).data(vorp_score);
//                 }

//                 // calculate z-score, z-offense, & z-peripheral
//                 if (!['z_gaa', 'z_saves_percent'].includes(category === "") && vorp_score < 0) {
//                     vorp_score = 0;
//                 }

//                 player[z_score_calc_idx] += vorp_score;
//                 if (position === 'Goalie') {
//                     if (['z_gaa', 'z_saves_percent'].includes(category)) {
//                         player[z_g_ratio_calc_idx] += vorp_score;
//                     } else {
//                         player[z_g_count_calc_idx] += vorp_score;
//                     }
//                 } else if (((position === 'Forward' && forwardOffenseCategories.includes(category)) ||
//                             (position === 'Defence' && defenceOffenseCategories.includes(category)))) {
//                     player[z_offense_calc_idx] += vorp_score;
//                 } else if ((position === 'Forward' || position === 'Defence') && peripheralCategories.includes(category)) {
//                     player[z_peripheral_calc_idx] += vorp_score;
//                 }
//             }

//             this.cell(rowIdx, z_score_calc_idx).data(player[z_score_calc_idx].toFixed(1));
//             this.cell(rowIdx, z_offense_calc_idx).data(player[z_offense_calc_idx].toFixed(1));
//             this.cell(rowIdx, z_peripheral_calc_idx).data(player[z_peripheral_calc_idx].toFixed(1));
//             this.cell(rowIdx, z_g_count_calc_idx).data(player[z_g_count_calc_idx].toFixed(1));
//             this.cell(rowIdx, z_g_ratio_calc_idx).data(player[z_g_ratio_calc_idx].toFixed(1));

//         }

//     });

//     return playerStatsTable;
// }

function colourizeCell(cell, idx, rowData) {
    if (heatmaps == true && !(rowData[games_idx] == "")) {
        const position = rowData[position_idx];
        const category = categoryLookup[idx];
        if (goalie_category_heatmap_columns.has(idx)) {
            if (position === 'G') {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = mean_cat[`${category}`];
                if (idx === gaa_idx) {
                    $(cell).colourize({ min, max, center, theme: 'cool-warm-reverse' });
                } else {
                    $(cell).colourize({ min, max, center });
                }
            }
        }
        if (goalie_category_z_score_heatmap_columns.has(idx)) {
            const category = categoryLookup[idx];
            if ( position === 'G' ) {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = 0;
                $(cell).colourize({ min, max, center });
            }
        }
        if (sktr_category_heatmap_columns.has(idx)) {
            const category = categoryLookup[idx];
            if (position !== 'G') {
                if (idx === points_idx) {
                    if (position === 'D') {
                        const max = max_cat[`d ${category}`];
                        const center = mean_cat[`d ${category}`];
                        $(cell).colourize({ max, center });
                    }
                } else {
                    const max = max_cat[`sktr ${category}`];
                    const center = mean_cat[`sktr ${category}`];
                    $(cell).colourize({ max, center });
                }
            }
        }
        if (sktr_category_z_score_heatmap_columns.has(idx)) {
            const category = categoryLookup[idx];
            if (position !== 'G') {
                if (idx === z_points_idx) {
                    if (position === 'D') {
                        const min = min_cat[`d ${category}`];
                        const max = max_cat[`d ${category}`];
                        const center = 0;
                        $(cell).colourize({ min, max, center });
                    }
                } else {
                    const min = min_cat[`sktr ${category}`];
                    const max = max_cat[`sktr ${category}`];
                    const center = 0;
                    $(cell).colourize({ min, max, center });
                }
            }
        }
        if (z_score_summary_heatmap_columns.has(idx)) {
            const category = categoryLookup[idx];
            if ( idx === z_score_idx ) {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = mean_cat[`${category}`];
                $(cell).colourize({ min, max, center });
            } else if ( position !== 'G' && sktr_z_score_summary_heatmap_columns.has(idx) ) {
                const min = min_cat[`sktr ${category}`];
                const max = max_cat[`sktr ${category}`];
                const center = mean_cat[`sktr ${category}`];
                $(cell).colourize({ min, max, center });
            } else if ( position === 'G'  && goalie_z_score_summary_heatmap_columns.has(idx) ) {
                const min = min_cat[`g ${category}`];
                const max = max_cat[`g ${category}`];
                const center = mean_cat[`g ${category}`];
                $(cell).colourize({ min, max, center });
            }
}
    }
}

function columnVisibility() {

    function getColumnNames(table, array) {
        let colIndices = table.columns()[0];
        if (array) {
            colIndices = array;
        }
        return colIndices.reduce((resultArray, index) => {
            resultArray.push(table.column(index).name() + ':name');
            return resultArray;
        }, []);
    }

    // reset the colvisClicked flag to false
    colvisClicked = false;

    const table = $('#player_stats').DataTable();
    // get game type & "pos" search pane, previous & current values
    const current_game_type = $('#gameType').data('current');
    const current_positon = $('#DataTables_Table_0').data('current');

    // get currently hidden  & visilble columns
    // const all_table_columns =  getColumnNames(table);
    const currently_hidden_columns = getColumnNames(table).filter((name) => !table.column(name).visible());
    const currently_visible_columns = getColumnNames(table).filter((name) => table.column(name).visible());

    let columns_to_hide = [];
    let columns_to_show = [];

    const sktr_columns = [...sktr_scoring_categories_column_names, ...sktr_info_column_names, ... sktr_z_score_categories_column_names, ...sktr_z_score_summary_column_names];
    const goalie_columns = [...goalie_scoring_categories_column_names, ...goalie_info_column_names, ...goalie_z_score_categories_column_names, ...goalie_z_score_summary_column_names];
    const sktr_and_goalie_columns = [... sktr_columns, ... goalie_columns];

    // Note: There can be only one selection, because I used dtOpts on the "position" seachPane,
    //       to set selection to 'single'
    sktr_manually_hidden_columns = sktr_columns.filter(column => manually_hidden_columns.includes(column));
    goalie_manually_hidden_columns = goalie_columns.filter(column => manually_hidden_columns.includes(column));
    sktr_manually_unhidden_columns = sktr_columns.filter(column => manually_unhidden_columns.includes(column));
    goalie_manually_unhidden_columns = goalie_columns.filter(column => manually_unhidden_columns.includes(column));
    if ( current_positon === 'G' ) {
        columns_to_hide = sktr_columns.filter(column => !goalie_columns.includes(column));
        columns_to_show = goalie_columns.filter(column => !goalie_manually_hidden_columns.includes(column));

    } else if ( current_positon === 'D' || current_positon === 'F' || current_positon === 'Sktr' ) {
        columns_to_hide = goalie_columns.filter(column => !sktr_columns.includes(column));
        columns_to_show = sktr_columns.filter(column => !sktr_manually_hidden_columns.includes(column));

    } else {
        columns_to_show = sktr_and_goalie_columns.filter(column => !manually_hidden_columns.includes(column));
    }

    if ( current_positon === 'G' ) {
        columns_to_hide = [... columns_to_hide.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_show.includes(column)), ... sktr_manually_unhidden_columns, ... goalie_manually_hidden_columns];
        columns_to_show = [... columns_to_show.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_hide.includes(column)), ... goalie_manually_unhidden_columns];
    } else if ( current_positon === 'D' || current_positon === 'F' || current_positon === 'Sktr' ) {
        columns_to_hide = [... columns_to_hide.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_show.includes(column)), ... goalie_manually_unhidden_columns, ... sktr_manually_hidden_columns];
        columns_to_show = [... columns_to_show.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_hide.includes(column)), ... sktr_manually_unhidden_columns];
    } else {
        columns_to_hide = [... columns_to_hide.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_show.includes(column)), ... manually_hidden_columns];
        columns_to_show = [... columns_to_show.filter((column) => !initially_hidden_column_names.includes(column) && !columns_to_hide.includes(column)), ... manually_unhidden_columns];
    }

    // if draft round column has values, the draft is completed, and no need to sho projected columns
    let data = table.column(draft_round_idx).data().toArray();
    let draft_completed = data.some(function(value) {
        return value.trim() !== '';
    });
    let prj_season_columns = [];
    let prj_season_sktr_columns = [];
    let prj_season_goalie_columns = [];
    if (!draft_completed) {
        prj_season_columns = getColumnNames(table, [adp_idx, fantrax_score_idx, injury_note_idx, prj_draft_round_idx, watch_idx]);
        prj_season_sktr_columns = getColumnNames(table, [breakout_threshold_idx, pp_unit_prj_idx]);
        prj_season_goalie_columns = getColumnNames(table, [tier_idx]);
    }

    if (current_game_type === 'Projected Season') {
        if ( current_positon === 'G' ) {
            columns_to_hide = [... columns_to_hide, ... prj_season_sktr_columns];
            columns_to_show = [... columns_to_show, ... prj_season_columns, ... prj_season_goalie_columns];
        } else if ( current_positon === 'D' || current_positon === 'F' || current_positon === 'Sktr' ) {
            columns_to_hide = [... columns_to_hide, ... prj_season_goalie_columns];
            columns_to_show = [... columns_to_show, ... prj_season_columns, ... prj_season_sktr_columns];
        } else {
            columns_to_show = [... columns_to_show, ... prj_season_columns, ... prj_season_sktr_columns, ... prj_season_goalie_columns];
        }
    } else {
        columns_to_hide = [... columns_to_hide, ... prj_season_columns, ... prj_season_sktr_columns, ... prj_season_goalie_columns];
    }

    // don't hide position columns if already hidden
    columns_to_hide = columns_to_hide.filter(column => !currently_hidden_columns.includes(column));

    // don't make position columns visible if already visible
    columns_to_show = columns_to_show.filter(column => !currently_visible_columns.includes(column));

    // hide columns
    table.columns(columns_to_hide).visible(show=false, redrawCalculations=false);
    // unhide columns
    table.columns(columns_to_show).visible(show=true, redrawCalculations=false);

    // get current sort columns
    let sort_columns = table.order();
    for ( let sort_info of sort_columns ) {
        if ( sort_info[0] == 0 || table.column( sort_info[0] ).visible() == false ) {
            sort_columns = [z_score_idx, "desc"];
            break;
        }
    }
    // sort columns
    table.order(sort_columns);

    // save current gameType & position as previous values
    $('#gameType').data('previous', current_game_type);
    $('#DataTables_Table_0').data('previous', current_positon);

}

function createCategoryScarcityTable(data_dict) {

    // create an array of the categories and their values
    let categories = [];
    for (let key in data_dict) {
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

    // Initialize new DataTable with calculated data
    $('#categoryScarcity').DataTable({
        data: categories,
        dom: 't',
        columns: [
            { data: 'category', title: 'category' },
            { data: 'value', title: 'weight' },
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
            const api = this.api();
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
        //     let headers = '<tr><th colspan="2" style="white-space: nowrap;">' + managerData.manager + '</th></tr>';
        //     managerTable.find('thead').prepend(headers);
        // },

    });

}

function createDraftBoardTable(remaining_draft_picks) {

    // Check if the table already exists
    if ($.fn.dataTable.isDataTable('#draftBoard')) {
        // If the table already exists, destroy it
        $('#draftBoard').DataTable().destroy();
    }

    // Prepare data for DataTables
    var tableData = [];
    var currentRound = 1;
    var rowData = [currentRound];
    var playerRowData = [currentRound];  // Initialize player row data with an empty string for the "Round" column

    // Create a mapping of original manager names to new names
    var managerMapping = {
        "Fowler's Flyers": "FF",
        "CanDO Know Huang": "CanDO",
        "One Man Gang Bang": "One Man",
        "Wheels On Meals": "Wheels",
        "Urban Legends": "UL",
        "Camaro SS": "Camaro",
        "Witch King": "Witchy",
        "El Paso Pirates": "El Paso",
        "WhatA LoadOfIt": "WhatA",
        "Banshee": "Banshee",
        "Horse Palace 26": "Horsey",
        "Shawsome1": "Shawsome",
        "High Cheese Chedsie": "Chedsie"
    };

    for (var i = 0; i < remaining_draft_picks.length; i++) {
        if (remaining_draft_picks[i].draft_round !== currentRound) {
            tableData.push(rowData);
            tableData.push(playerRowData);
            currentRound = remaining_draft_picks[i].draft_round;
            rowData = [currentRound];
            playerRowData = [currentRound];
        }
        var shortManager = managerMapping[remaining_draft_picks[i].manager];  // Get the new manager name from the mapping
        rowData.push(shortManager  + " (" + remaining_draft_picks[i].managers_pick_number + "\\" + remaining_draft_picks[i].overall_pick + ")");
        playerRowData.push('');  // Add an empty string for the player in the new row
    }
    tableData.push(rowData);  // Push the last row
    tableData.push(playerRowData);  // Push the last player row

    // Initialize DataTable
    $('#draftBoard').DataTable({
        data: tableData,
        columns: [{title: "Rnd"}].concat(Array.from({length: 13}, (_, i) => ({title: "Pick " + (i + 1)}))),  // Generate column titles
        ordering: false,
        autoWidth: false,
        stripeClasses: ['odd-row', 'even-row'],
        dom: 't',
        pageLength: 28,
        createdRow: function(row, data, dataIndex) {
            // Loop through each cell in the row
            $('td', row).each(function(colIndex) {
                // If the cell contains "Banshee", change its color
                if (this.innerText.includes('Banshee')) {
                    $(this).css('background-color', 'yellow');  // Change 'yellow' to your desired color
                }

                // If it's a player row, hide the round number
                if (dataIndex % 2 === 1) {
                    $('td:first', row).text('');
                }

            });
        }
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
            let headers = '<tr><th colspan="1"></th><th colspan="9">Skaters</th><th colspan="4">Goalies</th></tr>';
            $("#categoryScarcityByZScoreRange thead").prepend(headers);
        },
    });
}

function createManagerSummaryTable(playerStatsTable) {

    // getMaxCategoryValuesAndZScores();

    managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);

    const properties = ['picks', 'fCount', 'dCount', 'gCount', 'mfCount', 'zScore', 'zScoreSktr', 'zOffense', 'zPeripheral', 'points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways' ,'penaltyMinutes', 'zScoreG', 'zCountG', 'zRatioG', 'wins', 'saves', 'gaa', 'savePercent'];

    // Initialize new DataTable with calculated managerSummaryZScores
    $('#managerSummary').DataTable({
        data: managerSummaryZScores,
        dom: 't',
        columns: [
            { data: 'manager', title: 'manager' },
            { data: 'picks', title: 'picks' },
            { data: 'fCount', title: 'f\'s' },
            { data: 'dCount', title: 'd\'s' },
            { data: 'gCount', title: 'g\'s' },
            { data: 'mfCount', title: 'm\'s' },
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
        order: [[6, "desc"]],
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
            const api = this.api();
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

            $("#managerSummary thead tr:contains('Maximum Z-scores')").remove();
            let header = '<tr class="centered-header"><th>Maximum Z-scores</th><th colspan="9"></th><th>points</4th><th>goals</th><th>assists</th><th>ppp</th><th>sog</th><th>blocks</th><th>hits</th><th>takeaways</th><th>pim</th><th colspan="3"></th><th>wins</th><th>saves</th><th>gaa</th><th>save%</th</tr>';
            header = header.replace('points', maxCategoryValues['zScores']['points'].toFixed(2))
                           .replace('goals', maxCategoryValues['zScores']['goals'].toFixed(2))
                           .replace('assists', maxCategoryValues['zScores']['assists'].toFixed(2))
                           .replace('ppp', maxCategoryValues['zScores']['powerplayPoints'].toFixed(2))
                           .replace('sog', maxCategoryValues['zScores']['shotsOnGoal'].toFixed(2))
                           .replace('blocks', maxCategoryValues['zScores']['blockedShots'].toFixed(2))
                           .replace('hits', maxCategoryValues['zScores']['hits'].toFixed(2))
                           .replace('takeaways', maxCategoryValues['zScores']['takeaways'].toFixed(2))
                           .replace('pim', maxCategoryValues['zScores']['penaltyMinutes'].toFixed(2))
                           .replace('wins', maxCategoryValues['zScores']['wins'].toFixed(2))
                           .replace('saves', maxCategoryValues['zScores']['saves'].toFixed(2))
                           .replace('gaa', maxCategoryValues['zScores']['gaa'].toFixed(2))
                           .replace('save%', maxCategoryValues['zScores']['savePercent'].toFixed(2));
            $("#managerSummary thead tr:first-child").after(header);
        },
        initComplete: function () {
            let header = '<tr><th colspan="2"></th><th colspan="5"></th><th colspan="12">Skaters</th><th colspan="7">Goalies</th>';
            $("#managerSummary thead").prepend(header);
        },
    });

}

function createMyCategoryNeedsTable() {
    const categoryLabels = {
        points: 'd-pts',
        powerplayPoints: 'ppp',
        penaltyMinutes: 'pim',
        savePercent: 'save%',
        shotsOnGoal: 'sog',
        blockedShots: 'blk'
    };

    const managerData = getMyCategoryNeeds().find(data => data.manager === 'Banshee');
    if (managerData) {
        const managerTable = $('<table>').css('margin', '10px').appendTo('#myCategoryNeedsContainer');
        managerTable.addClass('display cell-border hover compact');

        const categories = Object.entries(managerData)
            .filter(([key]) => key !== 'manager')
            .map(([key, value]) => ({category: categoryLabels[key] || key, value}));

        const dataTable = managerTable.DataTable({
            data: categories,
            dom: 't',
            columns: [
                { data: 'category', title: 'category' },
                { data: 'value', title: 'rank' },
            ],
            order: [[1, "asc"]],
            pageLength: 13,
            columnDefs: [
                {className: 'dt-center', targets: '_all'},
                {className: 'dt-body-left', targets: [0]},
                {orderSequence: ['desc', 'asc'], targets: '_all'},
            ],
            drawCallback(settings) {
                const api = this.api();
                const values = api.rows({ page: 'current' }).data().toArray().map(row => parseFloat(row.value));
                const min = Math.min(...values);
                const max = Math.max(...values);
                const mean = values.reduce((a, b) => a + b) / values.length;

                api.rows().nodes().to$().find('td').each(function(i) {
                    if (i % 2 === 1) {
                        $(this).colourize({
                            min,
                            max,
                            center: mean,
                            theme: "cool-warm",
                        });
                    }
                });
            },
            initComplete() {
                managerTable.append('<caption style="caption-side: top; text-align: center; margin-bottom: 10px;"><b><u>My Category Needs</b></u></caption>');
            }
        });
    }
}

function clearDraftColumns() {

    let table = $('#player_stats').DataTable();

    // Get the data for all rows in the table
    let allPlayers = table.rows().data().toArray();

    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        let rowData = this.data();
        // let id = rowData[id_idx].match(/>(\d+)</)[1];
        let id = rowData[id_idx];
        let newDataItem = allPlayers.find(function(item) {
            // return item[id_idx].match(/>(\d+)</)[1] === id;
            return item[id_idx] === id;
        });

        if (newDataItem) {
            // update rowData with data from newDataItem
            rowData[draft_round_idx] = '';
            rowData[draft_position_idx] = '';
            rowData[draft_overall_pick_idx] = '';
            this.data(rowData);
        }
    } );

    // Filter out rows with no team manager
    let availablePlayersWithManager = allPlayers.filter(function (row) {
        return row[keeper_idx] !== 'Yes' && row[manager_idx] !== '';
    });


    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        let rowData = this.data();
        // let id = rowData[id_idx].match(/>(\d+)</)[1];
        let id = rowData[id_idx];
        let newDataItem = availablePlayersWithManager.find(function(item) {
            // return item[id_idx].match(/>(\d+)</)[1] === id;
            return item[id_idx] === id;
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
            // id: rowData[id_idx].match(/>(\d+)</)[1],
            id: rowData[id_idx],
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

    let categoryScarcityByZScoreRange = calcCategoryScarcityByZScoreRange(availablePlayers);
    updateCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);

    let categoryTotals = categoryScarcityByZScoreRange.find(obj => obj.hasOwnProperty('Totals')).Totals;
    let categories = Object.keys(categoryTotals);
    let categoryScarcities = categories.reduce((acc, key) => {
        acc[key] = 0;
        return acc;
    }, {});
    categoryScarcityByZScoreRange.forEach(obj => {
        let zScoreRange = Object.keys(obj)[0];
        // if (parseFloat(zScoreRange.split(' - ')[0]) >= 1.5) {
        if (parseFloat(zScoreRange.split(' - ')[0]) >= 0.0) {
            categories.forEach(k => {
                if (obj[zScoreRange][k] !== "") {
                    categoryScarcities[k] += obj[zScoreRange][k];
                }
            });
        }
    });

    let maxCategoryScarcity = Math.max(...Object.values(categoryScarcities).filter(val => val !== 0))
    categories.forEach(key => {
        categoryScarcities[key] = (1 - categoryScarcities[key] / maxCategoryScarcity) + 1;
    });

    return categoryScarcities;
}

function getDraftPicks(callback) {

    // Set the base URL for the Flask API endpoint
    const baseUrl = 'http://localhost:5000/draft-order';

    const queryParams = '';

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + queryParams, function(draft_order) {
        // Call the callback function with the draft order
        callback(draft_order);
    });

}

function getMyCategoryNeeds() {
    const categories = ['points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways', 'penaltyMinutes', 'wins', 'saves', 'gaa', 'savePercent'];
    const mySummaryZScores = managerSummaryZScores.find(item => item.manager === 'Banshee');

    const categoryNeeds = categories.reduce((acc, category) => {
        // Get all z-scores for the current category
        const allZScores = managerSummaryZScores.map(manager => manager[category]);
        // Sort the z-scores in descending order
        allZScores.sort((a, b) => b - a);
        // Find the rank of mySummaryZScores[category] in allZScores
        acc[category] = 13 - allZScores.indexOf(mySummaryZScores[category]);
        return acc;
    }, {});

    return [{ manager: 'Banshee', ...categoryNeeds }];
}

function getOrdinalString(n) {
    const s = ["th", "st", "nd", "rd"];
    let v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
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
            if (category !== 'gaa' && category !== 'savePercent') {
                if (!teamCategoryValuesAndZScores[manager]['zScores'][category]) {
                    teamCategoryValuesAndZScores[manager]['zScores'][category] = 0;
                }
                if (!isNaN(player.categoryZScores[category])) {
                    if (includePlayerCategoryZScore(player, category) === true || (category === 'toiSec' && player.position === 'G')) {
                        teamCategoryValuesAndZScores[manager]['zScores'][category] += player.categoryZScores[category];
                    }
                }
            }
        }

    });

    // need to calculate gaa & save %
    for (let manager in teamCategoryValuesAndZScores) {
        teamCategoryValuesAndZScores[manager]['values']['gaa'] = teamCategoryValuesAndZScores[manager]['values']['goalsAgainst'] / teamCategoryValuesAndZScores[manager]['values']['toiSec'] * 3600
        teamCategoryValuesAndZScores[manager]['values']['savePercent'] = teamCategoryValuesAndZScores[manager]['values']['saves'] / teamCategoryValuesAndZScores[manager]['values']['shotsAgainst']

        teamCategoryValuesAndZScores[manager]['zScores']['gaa'] = (mean_cat['gaa'] - teamCategoryValuesAndZScores[manager]['values']['gaa']) / std_cat['gaa']
        teamCategoryValuesAndZScores[manager]['zScores']['savePercent'] = (teamCategoryValuesAndZScores[manager]['values']['savePercent'] - mean_cat['save%']) / std_cat['save%']
    }

    return teamCategoryValuesAndZScores;
}

function getPlayerData(seasonOrDateRadios, callback) {
    // Set the base URL for the Flask API endpoint
    const baseUrl = 'http://localhost:5000/player-data';

    const queryParams = `?seasonOrDateRadios=${seasonOrDateRadios}&fromSeason=${fromSeason.value}&toSeason=${toSeason.value}&fromDate=${fromDate.value}&toDate=${toDate.value}&poolID=${poolID.value}&gameType=${gameType.value==='Regular Season' ? 'R' : gameType.value==='Playoffs' ? 'P' : 'Prj'}&statType=${statType.value}&projectionSource=${projectionSource.value}`;

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + queryParams, function(playerData) {
        // Call the callback function with the player data
        callback(playerData);
    });
}

function hidePulsingBarShowTables() {

    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'none';

    if (gameType.value === 'Projected Season') {
        // need to remove the `.hidden` class from the element first, as `display: none` takes precedence over any other `display`
        // declaration, even if it is added dynamically with JavaScript.
        $('#startDraftButton').removeClass('hidden').css('display', 'inline-block');
    }

    $('#player_stats').DataTable().columns.adjust().draw();
    $('#player_stats-div').show();

}

function hideTablesShowPulsingBar() {

    // $('#player_stats-div').hide();
    if (gameType.value === 'Projected Season') {
        $('#startDraftButton').addClass('hidden').css('display', 'none');
    }
    $('#autoAssignDraftPicksContainer').hide();
    $('#undoDraftPick').hide();
    $('#draftMessage').hide();
    $('#draftBoard').hide();
    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

}

function initDraftContextMenu() {

    let playerStatsTable = $('#player_stats').DataTable();
    let managerSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[5]).DataTable();
    let managerSummaryDataTable = $('#managerSummary').DataTable();

    $.contextMenu({
        selector: '#player_stats td',
        build: function($trigger, e) {
            // Update the context menu options before the menu is shown
            return {
                callback: function(key, options) {
                    let rowIndex = playerStatsTable.row(this).index();
                    switch(key) {
                        case "Draft player":

                            assignManager(playerStatsTable, rowIndex, draft_manager, managerSummaryDataTable);

                            // Reset search panes
                            playerStatsTable.searchPanes.clearSelections();
                            managerSearchPaneDataTable.rows(function(idx, data, node) {
                                return data.display.includes('No data');
                            }).select();

                            // Reset search builder selections
                            let currentSearchBuilderDetails = playerStatsTable.searchBuilder.getDetails();
                            if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                                playerStatsTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
                            }

                            // Resume auto processing
                            if (auto_assign_picks === true) {

                                // // Clear all search pane & serach builder selections
                                // table.searchPanes.clearSelections();
                                // table.searchBuilder.rebuild();

                                assignDraftPick(playerStatsTable, managerSummaryDataTable, managerSearchPaneDataTable);
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

// function resetPlayerZsores(playerStatsTable, originalPlayerStats) {
//     // Define the positions and their respective z-scores
//     const positionCategories = {
//         'Forward': {'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Defence': {'z_points': z_points_idx, 'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Goalie': {'z_wins': z_wins_idx, 'z_saves': z_saves_idx, 'z_saves_percent': z_saves_percent_idx, 'z_gaa': z_gaa_idx}
//     };

//     // Iterate over each player
//     playerStatsTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
//         var player = this.data();
//         // Determine the player's position
//         let position;
//         if (["LW", "C", "RW"].includes(player[position_idx])) {
//             position = "Forward";
//         } else if (player[position_idx] === "D") {
//             position = "Defence";
//         } else if (player[position_idx] === "G") {
//             position = "Goalie";
//         }

//         if (position) {
//             // Iterate over each category z-score
//             categories = positionCategories[position];
//             for (let category in categories) {
//                 this.cell(rowIdx, categories[category]).data(originalPlayerStats[rowIdx][categories[category]]);
//             }

//             this.cell(rowIdx, z_score_calc_idx).data(originalPlayerStats[rowIdx][z_score_calc_idx]);
//             if (position === 'Goalie') {
//                 this.cell(rowIdx, z_g_count_calc_idx).data(originalPlayerStats[rowIdx][z_g_count_calc_idx]);
//                 this.cell(rowIdx, z_g_ratio_calc_idx).data(originalPlayerStats[rowIdx][z_g_ratio_calc_idx]);
//             } else { // (position === 'Forward' || position === 'Defence')
//                 this.cell(rowIdx, z_offense_calc_idx).data(originalPlayerStats[rowIdx][z_offense_calc_idx]);
//                 this.cell(rowIdx, z_peripheral_calc_idx).data(originalPlayerStats[rowIdx][z_peripheral_calc_idx]);
//             }
//         }

//     });

//     return playerStatsTable;
// }

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
    let name_idx = table.column('name:name')[0][0];
    let name_visible_idx = name_idx;
    for (let i = 0; i < name_idx; i++) {
        if ( table.column(i).visible() === false ) {
            name_visible_idx = name_visible_idx - 1;
        }
    }
    table.fixedColumns().left( name_visible_idx + 1 );

}

function toggleHeatmaps(playerStatsTable) {

    heatmaps = !heatmaps;

    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

    // Delay the rest of your code
    setTimeout(function() {

        // Iterate over each player
        playerStatsTable.rows().every(function(rowIdx, tableLoop, rowLoop) {
            let column_idx;
            for (let i = 0; i < heatmap_columns.length; i++) {
                column_idx = heatmap_columns[i];
                let cellNode = this.cell(rowIdx, column_idx).node();
                if (heatmaps) {
                    colourizeCell(cellNode, column_idx, this.row(rowIdx).data());
                } else {
                    $(cellNode).css('background-color', ''); // Remove background color
                }
            }
        });

        playerStatsTable.columns.adjust().draw();

        // Hide pulsing bar
        document.getElementById('pulsing-bar').style.display = 'none';

    }, 2000);

}

function updateCaption() {

    const seasonFrom = fromSeason.value.substring(0, 4) + '-' + fromSeason.value.substring(4);
    const seasonTo = toSeason.value.substring(0, 4) + '-' + toSeason.value.substring(4);

    if (fromSeason.value === toSeason.value){
        caption = statType.value + ' Statistics for the ' + seasonFrom + ' ' + gameType.value;
    } else {
        caption = statType.value + ' Statistics for the ' + seasonFrom + ' to ' + seasonTo + ' ' + gameType.value + 's';
    }

    if (seasonOrDateRadios[1].checked){
        if (dateRangePickerSelection === 'Custom Range') {
            caption = caption + ' (' + $('#dateRange')[0].innerText.trim() + ' )';
        } else {
            caption = caption + ' (' + dateRangePickerSelection + ')';
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
    let categories = [];
    for (let key in data_dict) {
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
    assists_idx = columns.findIndex(column => column.title === 'a');
    athletic_zscore_rank_idx = columns.findIndex(column => column.title === 'athletic z-score rank');
    bandaid_boy_idx = columns.findIndex(column => column.title === 'bandaid boy');
    blk_idx = columns.findIndex(column => column.title === 'blk');
    breakout_threshold_idx = columns.findIndex(column => column.title === 'bt');
    career_games_idx = columns.findIndex(column => column.title === 'career games');
    corsi_for_percent_idx = columns.findIndex(column => column.title === 'cf%');
    dfo_zscore_rank_idx = columns.findIndex(column => column.title === 'dfo z-score rank');
    dobber_zscore_rank_idx = columns.findIndex(column => column.title === 'dobber z-score rank');
    draft_overall_pick_idx = columns.findIndex(column => column.title === 'overall');
    draft_position_idx = columns.findIndex(column => column.title === 'draft position');
    draft_round_idx = columns.findIndex(column => column.title === 'draft round');
    dtz_zscore_rank_idx = columns.findIndex(column => column.title === 'dtz z-score rank');
    fantrax_roster_status_idx = columns.findIndex(column => column.title === 'fantrax roster status');
    fantrax_score_idx = columns.findIndex(column => column.title === 'fantrax score');
    fantrax_zscore_rank_idx = columns.findIndex(column => column.title === 'fantrax z-score rank');
    gaa_idx = columns.findIndex(column => column.title === 'gaa');
    game_today_idx = columns.findIndex(column => column.title === 'game today');
    games_idx = columns.findIndex(column => column.title === 'gp');
    goalie_starts_idx = columns.findIndex(column => column.title === 'goalie starts');
    goals_against_idx = columns.findIndex(column => column.title === 'goals against');
    goals_idx = columns.findIndex(column => column.title === 'g');
    hits_idx = columns.findIndex(column => column.title === 'hits');
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
    penalties_idx = columns.findIndex(column => column.title === 'penalties');
    picked_by_idx = columns.findIndex(column => column.title === 'picked by');
    pim_idx = columns.findIndex(column => column.title === 'pim');
    points_idx = columns.findIndex(column => column.title === 'pts');
    position_idx = columns.findIndex(column => column.title === 'pos');
    pp_goals_p120_idx = columns.findIndex(column => column.title === 'pp g/120');
    pp_percent_idx = columns.findIndex(column => column.title === '%pp');
    pp_points_p120_idx = columns.findIndex(column => column.title === 'pp pts/120');
    pp_unit_idx = columns.findIndex(column => column.title === 'pp unit');
    pp_unit_prj_idx = columns.findIndex(column => column.title === 'pp unit prj');
    ppp_idx = columns.findIndex(column => column.title === 'ppp');
    predraft_keeper_idx = columns.findIndex(column => column.title === 'pre-draft keeper');
    prj_draft_round_idx = columns.findIndex(column => column.title === 'prj draft round');
    qualtity_starts_idx = columns.findIndex(column => column.title === 'qs');
    qualtity_starts_percent_idx = columns.findIndex(column => column.title === 'qs %');
    rank_in_group_idx = columns.findIndex(column => column.title === 'list rank');
    rank_overall_idx = columns.findIndex(column => column.title === 'score rank');
    rank_sort_idx = columns.findIndex(column => column.title === 'sort rank');
    really_bad_starts_idx = columns.findIndex(column => column.title === 'rbs');
    rookie_idx = columns.findIndex(column => column.title === 'rookie');
    saves_idx = columns.findIndex(column => column.title === 'sv');
    saves_percent_idx = columns.findIndex(column => column.title === 'sv%');
    shooting_percent_idx = columns.findIndex(column => column.title === 'sh%');
    shots_against_idx = columns.findIndex(column => column.title === 'shots against');
    sleeper_idx = columns.findIndex(column => column.title === 'sleeper');
    sog_idx = columns.findIndex(column => column.title === 'sog');
    sog_pp_idx = columns.findIndex(column => column.title === 'pp sog');
    team_idx = columns.findIndex(column => column.title === 'team');
    three_yp_idx = columns.findIndex(column => column.title === '3yp');
    tier_idx = columns.findIndex(column => column.title === 'tier');
    tk_idx = columns.findIndex(column => column.title === 'tk');
    toi_even_pg_idx = columns.findIndex(column => column.title === 'toi even pg');
    toi_even_pg_trend_idx = columns.findIndex(column => column.title === 'toi even pg (trend)');
    toi_pg_trend_idx = columns.findIndex(column => column.title === 'toi pg (trend)');
    toi_pp_percent_3gm_avg_idx = columns.findIndex(column => column.title === 'toi pp % (rolling avg)');
    toi_pp_percent_idx = columns.findIndex(column => column.title === 'toi pp %');
    toi_pp_pg_idx = columns.findIndex(column => column.title === 'toi pp pg');
    toi_pp_pg_trend_idx = columns.findIndex(column => column.title === 'toi pp pg (trend)');
    toi_sec_idx = columns.findIndex(column => column.title === 'toi (sec)');
    toi_minutes_idx = columns.findIndex(column => column.title === 'toi (min)');
    toi_sh_pg_trend_idx = columns.findIndex(column => column.title === 'toi sh pg (trend)');
    upside_idx = columns.findIndex(column => column.title === 'upside');
    watch_idx = columns.findIndex(column => column.title === 'watch');
    wins_idx = columns.findIndex(column => column.title === 'w');
    z_assists_idx = columns.findIndex(column => column.title === 'z-a');
    z_blk_idx = columns.findIndex(column => column.title === 'z-blk');
    z_combo_idx = columns.findIndex(column => column.title === 'z-combo');
    z_g_count_idx = columns.findIndex(column => column.title === 'g count score');
    z_g_count_combo_idx = columns.findIndex(column => column.title === 'z-count combo');
    z_g_count_calc_idx = columns.findIndex(column => column.title === 'z-count');
    z_g_ratio_idx = columns.findIndex(column => column.title === 'g ratio score');
    z_g_ratio_combo_idx = columns.findIndex(column => column.title === 'z-ratio combo');
    z_g_ratio_calc_idx = columns.findIndex(column => column.title === 'z-ratio');
    z_gaa_idx = columns.findIndex(column => column.title === 'z-gaa');
    // z_goals_hits_pim_idx = columns.findIndex(column => column.title === 'z-goals +hits +penalties');
    z_goals_idx = columns.findIndex(column => column.title === 'z-g');
    // z_hits_blk_idx = columns.findIndex(column => column.title === 'z-hits +blks');
    z_hits_idx = columns.findIndex(column => column.title === 'z-hits');
    // z_hits_pim_idx = columns.findIndex(column => column.title === 'z-hits +penalties');
    z_offense_idx = columns.findIndex(column => column.title === 'sktr offense score');
    z_offense_combo_idx = columns.findIndex(column => column.title === 'z-offense combo');
    z_offense_calc_idx = columns.findIndex(column => column.title === 'z-offense');
    z_penalties_idx = columns.findIndex(column => column.title === 'z-penalties');
    z_peripheral_idx = columns.findIndex(column => column.title === 'sktr peripheral score');
    z_peripheral_combo_idx = columns.findIndex(column => column.title === 'z-peripheral combo');
    z_peripheral_calc_idx = columns.findIndex(column => column.title === 'z-peripheral');
    z_pim_idx = columns.findIndex(column => column.title === 'z-pim');
    z_points_idx = columns.findIndex(column => column.title === 'z-pts');
    z_ppp_idx = columns.findIndex(column => column.title === 'z-ppp');
    z_saves_idx = columns.findIndex(column => column.title === 'z-sv');
    z_saves_percent_idx = columns.findIndex(column => column.title === 'z-sv%');
    z_score_idx = columns.findIndex(column => column.title === 'score');
    z_score_calc_idx = columns.findIndex(column => column.title === 'z-score');
    // z_sog_hits_blk_idx = columns.findIndex(column => column.title === 'z-sog +hits +blk');
    z_sog_idx = columns.findIndex(column => column.title === 'z-sog');
    z_tk_idx = columns.findIndex(column => column.title === 'z-tk');
    z_wins_idx = columns.findIndex(column => column.title === 'z-w');

    sktr_category_heatmap_columns = new Set([points_idx, goals_idx, assists_idx, ppp_idx, sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx, penalties_idx]);
    goalie_category_heatmap_columns = new Set([wins_idx, saves_idx, gaa_idx, saves_percent_idx]);
    sktr_category_z_score_heatmap_columns = new Set([z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_tk_idx, z_hits_idx, z_blk_idx, z_pim_idx, z_penalties_idx]);
    goalie_category_z_score_heatmap_columns = new Set([z_wins_idx, z_saves_idx, z_gaa_idx, z_saves_percent_idx]);
    z_score_summary_heatmap_columns = new Set([z_score_idx, z_offense_idx, z_peripheral_idx, z_g_count_idx, z_g_ratio_idx]);
    sktr_z_score_summary_heatmap_columns = new Set([z_score_idx, z_offense_idx, z_peripheral_idx]);
    goalie_z_score_summary_heatmap_columns = new Set([z_score_idx, z_g_count_idx, z_g_ratio_idx]);

    heatmap_columns = [...Array.from(z_score_summary_heatmap_columns), ...Array.from(sktr_category_heatmap_columns), ...Array.from(goalie_category_heatmap_columns), ...Array.from(sktr_category_z_score_heatmap_columns), ...Array.from(goalie_category_z_score_heatmap_columns)]
    combo_columns = [z_combo_idx, z_offense_combo_idx, z_peripheral_combo_idx, z_g_count_combo_idx, z_g_ratio_combo_idx];

    categoryLookup = {
        [assists_idx]: 'assists',
        [blk_idx]: 'blocked',
        [gaa_idx]: 'gaa',
        [goals_idx]: 'goals',
        [hits_idx]: 'hits',
        [penalties_idx]: 'penalties',
        [pim_idx]: 'pim',
        [points_idx]: 'points',
        [ppp_idx]: 'points_pp',
        [saves_idx]: 'saves',
        [saves_percent_idx]: 'save%',
        [sog_idx]: 'shots',
        [sog_pp_idx]: 'shots_powerplay',
        [tk_idx]: 'takeaways',
        [wins_idx]: 'wins',
        [z_assists_idx]: 'z_assists',
        [z_blk_idx]: 'z_blocked',
        [z_g_count_idx]: 'z_g_count',
        [z_g_ratio_idx]: 'z_g_ratio',
        [z_gaa_idx]: 'z_gaa',
        // [z_goals_hits_pim_idx]: 'z_goals_hits_pim',
        [z_goals_idx]: 'z_goals',
        // [z_hits_blk_idx]: 'z_hits_blk',
        [z_hits_idx]: 'z_hits',
        // [z_hits_pim_idx]: 'z_hits_pim',
        [z_offense_idx]: 'z_offense',
        [z_penalties_idx]: 'z_penalties',
        [z_peripheral_idx]: 'z_peripheral',
        [z_pim_idx]: 'z_pim',
        [z_points_idx]: 'z_points',
        [z_ppp_idx]: 'z_points_pp',
        [z_saves_idx]: 'z_saves',
        [z_saves_percent_idx]: 'z_save%',
        [z_score_idx]: 'z_score',
        // [z_sog_hits_blk_idx]: 'z_sog_hits_blk',
        [z_sog_idx]: 'z_shots',
        [z_tk_idx]: 'z_takeaways',
        [z_wins_idx]: 'z_wins',
    };
}

function updateGlobalVariables(playerData) {

    // caption = playerData['caption'];
    column_titles = playerData['column_titles'];
    // numeric_columns = playerData['numeric_columns'];
    descending_columns = playerData['descending_columns'];

    stats_data = playerData['stats_data'];

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

    stat_column_names = playerData['stat_column_names'];

    initially_hidden_column_names = playerData['initially_hidden_column_names'];
    search_builder_column_names = playerData['search_builder_column_names'];

    max_cat = playerData['max_cat_dict'];
    min_cat = playerData['min_cat_dict'];
    mean_cat = playerData['mean_cat_dict'];
    std_cat = playerData['std_cat_dict'];

    z_scores = playerData['z_scores_dict'];

}

function updateManagerSummaryTable(data) {

    let managerSummaryTable = $('#managerSummary').DataTable();
    // Clear the existing data in the table
    managerSummaryTable.clear();

    // Add the new data to the table
    managerSummaryTable.rows.add(data);

    // table.columns.adjust().draw();
    managerSummaryTable.draw();

}

function updateMyCategoryNeedsTable(myCategoryNeeds) {
    const categoryLabels = {
        points: 'd-pts',
        powerplayPoints: 'ppp',
        penaltyMinutes: 'pim',
        savePercent: 'save%',
        shotsOnGoal: 'sog',
        blockedShots: 'blk'
    };

    const managerData = myCategoryNeeds.find(data => data.manager === 'Banshee');
    if (managerData) {
        const container = $('#myCategoryNeedsContainer');
        const managerCategoryNeedsTable = container.find(`table[data-CategoryNeedsTableFor=${managerData.manager}]`).first();
        const table = managerCategoryNeedsTable.DataTable();
        table.clear();

        const categories = Object.entries(managerData)
            .filter(([key]) => key !== 'manager')
            .map(([key, value]) => ({category: categoryLabels[key] || key, value}));

        table.rows.add(categories);
        table.draw();
    }
}

function undoDraftPick() {

    if (completed_draft_picks) {
        let playerStatsTable = $('#player_stats').DataTable();

        // get most reacent draft pick
        let last_pick = completed_draft_picks.pop();
        if (last_pick) {
            var playerIndex = nameToIndex[last_pick.drafted_player];
            if (playerIndex.length === 1) {
                rowIndex = playerIndex[0];
                // clear draft information from table row for the drafted player
                playerStatsTable.cell(rowIndex, manager_idx).data('');
                playerStatsTable.cell(rowIndex, draft_round_idx).data('');
                playerStatsTable.cell(rowIndex, draft_position_idx).data('');
                playerStatsTable.cell(rowIndex, draft_overall_pick_idx).data('');
                playerStatsTable.cell(rowIndex, picked_by_idx).data('');

                // add the last drafted player back to remaining_draft_picks array
                last_pick.drafted_player = '';
                remaining_draft_picks.unshift(last_pick);

                let round = remaining_draft_picks[0].draft_round;  // The round number
                let pick = remaining_draft_picks[0].round_pick;  // The pick number
                let tableData = $('#draftBoard').DataTable();
                // Find the corresponding cell in tableData and update it
                let cell = tableData.cell((round - 1) * 2 + 1, pick); // Get the cell object
                cell.data('');

                managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);
                updateManagerSummaryTable(managerSummaryZScores);

                myCategoryNeeds = getMyCategoryNeeds()
                updateMyCategoryNeedsTable(myCategoryNeeds);

                draft_manager = remaining_draft_picks[0].manager;
                let managerSummaryDataTable = $('#managerSummary').DataTable();
                managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];

                document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';

            } else {
                alert('Undo of most recent draft pick failed! "' + last_pick.drafted_player + '" not found in nameToIndex array.')
            }
        } else {
            alert('Undo of most recent draft pick failed! The completed_draft_picks array is empty.')
        }
    }

}

function updatePlayerStatsTable(data) {

    let playerStatsTable = $('#player_stats').DataTable();

    // Clear the existing data in the table
    playerStatsTable.clear();

    // Add the new data to the table
    playerStatsTable.rows.add(data);

    managerSummaryZScores = calcManagerSummaryZScores(playerStatsTable);
    updateManagerSummaryTable(managerSummaryZScores);

    // data = calcManagerCategoryNeedsData();
    myCategoryNeeds = getMyCategoryNeeds()
    updateMyCategoryNeedsTable(myCategoryNeeds);

    let calculatedPlayerSummaryZScores = calculatePlayerSummaryZScores();
    updatePlayerTableWithCalculatedSummaryZScores(calculatedPlayerSummaryZScores);

    // Redraw the table
    playerStatsTable.columns.adjust().draw();

}

function calculatePlayerSummaryZScores() {

    let allPlayers = getAllPlayers();

    // calculate z-score for each player
    allPlayers.forEach(player => {

        let zScore = 0;
        let zOffense = 0;
        let zPeripheral = 0;
        let zGCount = 0;
        let zGRatio = 0;

        for (let category in player.categoryZScores) {
            if (includePlayerCategoryZScore(player, category) === true) {
                let weightFactors = [];

                if (['points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways', 'penaltyMinutes', 'wins', 'saves', 'gaa', 'savePercent'].includes(category) === false) {
                    alert('category is ' + category);
                }

                let categoryZScore = 0;
                let categoryIsIncluded = document.getElementById(category).checked;
                if (categoryIsIncluded) {
                    categoryZScore = player.categoryZScores[category];
                }
                if (!isNaN(categoryZScore)) {
                    zScore += categoryZScore;
                    if ( (player.position === 'D' && dOffenseCategories.includes(category)) || (['LW', 'C', 'RW'].includes(player.position) && fOffenseCategories.includes(category)) ) {
                        zOffense += categoryZScore;
                    }
                    if (['LW', 'C', 'RW', 'D'].includes(player.position) && sktrPeripheralCategories.includes(category) ) {
                        zPeripheral += categoryZScore;
                    }
                    if (player.position === 'G') {
                        if (gCountCategories.includes(category)) {
                            zGCount += categoryZScore;
                        } else { // gRatioCategories.includes(category)
                            zGRatio += categoryZScore;
                        }
                    }
                }
            }
        }

        player.ZScoreCalc = zScore;
        if (['LW', 'C', 'RW', 'D'].includes(player.position)) {
            player.ZOffenseCalc = zOffense;
            player.ZPeripheralCalc = zPeripheral;
            player.zGCountCalc = 0;
            player.zGRatioCalc = 0;
        }
        if (player.position === 'G') {
            player.ZOffenseCalc = 0;
            player.ZPeripheralCalc = 0;
            player.zGCountCalc = zGCount;
            player.zGRatioCalc = zGRatio;
        }

    });

    return allPlayers;

}

function updatePlayerTableWithCalculatedSummaryZScores(calculatedPlayerSummaryZScores) {

    let table = $('#player_stats').DataTable();

    table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
        let rowData = this.data();
        // let id = rowData[id_idx].match(/>(\d+)</)[1];
        let id = rowData[id_idx];
        let newDataItem = calculatedPlayerSummaryZScores.find(function(item) {
            return item.id === id;
        });

        if (newDataItem) {
            // update rowData with data from newDataItem
            rowData[z_score_calc_idx] = newDataItem.ZScoreCalc.toFixed(1);
            rowData[z_offense_calc_idx] = newDataItem.ZOffenseCalc.toFixed(1);
            rowData[z_peripheral_calc_idx] = newDataItem.ZPeripheralCalc.toFixed(1);
            rowData[z_g_count_calc_idx] = newDataItem.zGCountCalc.toFixed(1);
            rowData[z_g_ratio_calc_idx] = newDataItem.zGRatioCalc.toFixed(1);
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
