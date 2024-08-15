// heatmaps toggle
var heatmaps = true
var executePlayerStatsTableSortDrawCallbackCode = false;
var playerStatsTableIsInitialized = false;

// flag variable to track if the ColVis button was clicked
var colvisClicked = false;
var manually_hidden_columns = [];
var manually_unhidden_columns = [];

/////////////////////////////////////////////////////////////////////////////////////////
// global variables for Draft
var remaining_draft_picks;
var draft_order_picks;
var completed_draft_picks = [];
var draft_manager;
var auto_assign_picks = false;
var manually_select_my_picks = false;
var draft_in_progress = false;
var draft_completed = false;
var draft_order;
var writeToDraftSimulationsTable = false;
// global variables to include managers that have reached their position maximium limits, during auto assignment
var f_limit_reached = [];
var d_limit_reached = [];
var g_limit_reached = [];
/////////////////////////////////////////////////////////////////////////////////////////

var fOffenseCategories = ['goals', 'assists', 'powerplayPoints', 'shotsOnGoal'];
var dOffenseCategories = ['points'].concat(fOffenseCategories);
var sktrPeripheralCategories = ['hits', 'blockedShots', 'takeaways', 'penaltyMinutes'];
var fAllCategories = fOffenseCategories.concat(sktrPeripheralCategories);
var dAllCategories = dOffenseCategories.concat(sktrPeripheralCategories);
var gCountCategories = ['wins', 'saves'];
var gRatioCategories = ['gaa', 'savePercent'];

var nameToIndex = {};

// datatables
var managerSearchPaneDataTable;
var injurySearchPaneDataTable;
var positionSearchPaneDataTable;
var additionalFiltersSearchPaneDataTable;
var playerStatsDataTable;
var managerSummaryDataTable;

var managerSummaryScores;

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

// Get only the controls with the 'trigger-control' class
var controls_getRawData = document.querySelectorAll('.trigger_getRawData');
var controls_aggregateData = document.querySelectorAll('.trigger_aggregateData');
var controls_calculateScores = document.querySelectorAll('.trigger_calculateScores');

window.onload = function() {
    // Set the data-default-index attribute to the index of the initially selected option
    controls_getRawData.forEach(function(control) {
        control.previousValue = undefined;
    });
    controls_aggregateData.forEach(function(control) {
        control.previousValue = undefined;
    });
    controls_calculateScores.forEach(function(control) {
        control.previousValue = undefined;
    });
};

var generationType = 'full'

$('#gameType').on('change', function() {
    // save current gameType (i.e., 'Regular Season')
    $('#gameType').data('current', gameType.value);

    // hide\display startDraftButton as appropriate
    if (gameType.value === 'Projected Season' && $.fn.dataTable.isDataTable('#player_stats')) {
        $('#startDraftButton').removeClass('hidden').css('display', 'inline-block');
    } else {
        $('#startDraftButton').addClass('hidden').css('display', 'none');
    }
})

$('#dateRange').on('apply.daterangepicker', function(ev, picker) {
    dateRangePickerSelection = picker.chosenLabel;
});

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

document.getElementById('applyButton').addEventListener('click', () => {

    var hasChanged_controls_getRawData = Array.from(controls_getRawData).some(function(control) {
        if (control.id === 'seasonRadioButton' || control.id === 'dateRadioButton') {
            return control.checked !== control.previousValue;
        } else {
            return control.value !== control.previousValue;
        }
    });
    var hasChanged_controls_aggregateData = Array.from(controls_aggregateData).some(function(control) {
        return control.value !== control.previousValue;
    });
    var hasChanged_controls_calculateScores = Array.from(controls_calculateScores).some(function(control) {
        return control.checked !== control.previousValue;
    });

    // Set all values as previousValue
    Array.from(controls_getRawData).forEach(function(control) {
        if (control.id === 'seasonRadioButton' || control.id === 'dateRadioButton') {
            control.previousValue = control.checked;
        } else {
            control.previousValue = control.value;
        }
    });
    Array.from(controls_aggregateData).forEach(function(control) {
        control.previousValue = control.value;
    });
    Array.from(controls_calculateScores).forEach(function(control) {
        control.previousValue = control.checked;
    });

    generationType = 'calculateScores';
    if (hasChanged_controls_getRawData || document.querySelector('#gameType').value === 'Projected Season') {
        generationType = 'full';
    } else if (hasChanged_controls_aggregateData) {
        generationType = 'aggregateData';
    }

    hideTablesShowPulsingBar()

    const seasonOrDateRadios = $('input[name="seasonOrDate"]:checked').val();

    // Check if DataTable instance exists
    if ($.fn.dataTable.isDataTable('#player_stats')) {

        // Save searchPane selections
        var selectedOptions = {};
        $('#player_stats-div .dtsp-searchPanes table.dataTable').filter(function() {
            return this.id.indexOf('DataTables_Table_') === 0;
        }).each(function() {
            var table = $(this).DataTable();
            var selectedRows = playerStatsDataTable.rows('.selected');
            selectedOptions[this.id] = selectedRows.data().toArray().map(function(row) {
                return row.display;
            });
        });

    }

    const scoringCategoryCheckboxes = getScoringCategoryCheckboxes();

    getPlayerData(generationType, seasonOrDateRadios, scoringCategoryCheckboxes, function(playerData) {

        if (Object.keys(playerData).length === 0) {
            alert('No data returned from server.');
            // show tables
            hidePulsingBarShowTables()
            return;
        } else {
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

                if ($.fn.dataTable.isDataTable('#managerSummary') === true) {
                    managerSummaryScores = calcManagerSummaryScores();
                    updateManagerSummaryTable(managerSummaryScores);
                }

            } else {

                var table = $('#player_stats').DataTable( {

                    // deferRender: true tells DataTables to delay the creation of table cells and rows until they are actually needed for a requested display
                    deferRender: true,

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
                                            var selectedPlayerIds = localStorage.getItem('selectedPlayerIds');
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

                    columnDefs: [
                        // first column, rank in group, is not orderable or searchable
                        {searchable: false, orderable: false, targets: list_rank_idx},
                        // {type: 'num', targets: numeric_columns},
                        // z_score_idx; otherwise doesn't sort numerically
                        {type: 'num', targets: [z_score_idx, line_idx, pp_unit_idx]},
                        // custom data type for id_idx, to be used in searchBuilder
                        {type: 'playerId', targets: id_idx},
                        {orderSequence: ['desc', 'asc'], targets: descending_columns},
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
                        {searchBuilder: { defaultCondition: 'contains' }, targets: [name_idx]},
                        {searchBuilder: { defaultCondition: '>=' }, targets: [
                            games_idx, goalie_starts_idx,
                            points_idx, goals_idx, pp_goals_p120_idx, assists_idx, ppp_idx,
                            sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx, pp_points_p120_idx,
                            toi_pp_percent_idx, toi_pp_percent_3gm_avg_idx, toi_minutes_idx,
                            ev_ipp_idx, pp_ipp_idx, corsi_for_percent_idx,
                            z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_blk_idx, z_hits_idx, z_pim_idx, z_tk_idx,
                            z_wins_idx, z_saves_idx, z_saves_percent_idx, z_gaa_idx,
                            score_idx, offense_score_idx, peripheral_score_idx, z_combo_idx, g_count_score_idx, g_ratio_score_idx
                        ]},
                        {targets: [last_game_idx], searchBuilder: { defaultCondition: '>' } },
                        {searchBuilder: { defaultCondition: '<=' }, targets: [age_idx, career_games_idx, pdo_idx, shooting_percent_idx]},
                        {searchBuilder: { defaultCondition: '=' }, targets: [
                            draft_position_idx,
                            draft_round_idx,
                            keeper_idx,
                            line_idx,
                            manager_idx,
                            minors_idx,
                            nhl_roster_status_idx,
                            picked_by_idx,
                            position_idx,
                            pp_unit_idx,
                            predraft_keeper_idx,
                            prj_draft_round_idx,
                            rookie_idx,
                            team_idx,
                            watch_idx
                        ]},
                        {searchBuilder: { defaultCondition: '!null' }, targets: [breakout_threshold_idx, game_today_idx]},
                        {searchBuilder: { defaultCondition: 'selectedPlayers' }, targets: [id_idx]},

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
                        {targets: breakout_threshold_idx, shooting_percent_idx, searchBuilderType: 'num' },

                        // custom data type for id_idx, to be used in searchBuilder
                        {targets: id_idx, searchBuilderType: 'playerId'},

                        // custom sort for 'fantrax adp', 'line', 'line prj', 'pp unit', 'pp unit prj', 'athletic z-score rank', 'dobber z-score rank', 'fantrax z-score rank' columns
                        {targets: [adp_idx, line_idx, pp_unit_idx, pp_unit_prj_idx, athletic_zscore_rank_idx, dobber_zscore_rank_idx, fantrax_zscore_rank_idx, draft_position_idx, draft_round_idx, breakout_threshold_idx],
                         type: "custom_integer_sort",
                         orderSequence: ['asc']
                        },

                        // custom sort for 'toi pg (trend)', 'toi even pg (trend)', 'toi pp pg (trend)', 'toi sh pg (trend)' columns
                        {targets: [toi_pg_trend_idx, toi_even_pg_trend_idx, toi_pp_pg_trend_idx, toi_sh_pg_trend_idx],
                         type: "custom_time_delta_sort",
                         orderSequence: ['desc']
                        },

                    ],

                    fixedHeader: true,
                    fixedColumns: true,
                    orderCellsTop: true,
                    pagingType: 'full_numbers',

                    lengthMenu: [
                        [20, 50, 100, 250, 500, -1],
                        ['20 per page', '50 per page', '100 per page', '250 per page', '500 per page', 'All']
                    ],
                    pageLength: 20,
                    // use 'api' selection style; was using 'multi+shift'
                    select: 'api',
                    buttons: [
                        {
                            extend: 'spacer',
                            style: 'bar',
                            text: ''
                        },
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
                                // Reset search builder selections
                                // let playerStatsTable = $('#player_stats').DataTable();
                                let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                                if (JSON.stringify(currentSearchBuilderDetails).includes('selectedPlayers') || JSON.stringify(currentSearchBuilderDetails).includes('unselectedPlayers')) {
                                    playerStatsDataTable.searchBuilder.rebuild(currentSearchBuilderDetails);
                                }
                            }
                        },
                    ],

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
                        preDefined: {
                            criteria: [
                                {
                                    condition: '>=',
                                    data: 'gp',
                                    value: [1]
                                }
                            ],
                            logic: 'AND',
                        },
                        conditions: {
                            playerId: {
                                'selectedPlayers': {
                                    conditionName: 'Selected Players',
                                    init: function(that, fn, preDefined = null) {
                                        let el = jQuery('<input>')
                                        .attr('type','hidden')
                                        .on('input', function() {
                                            fn(that, this);
                                        });

                                        setTimeout(function() {
                                            $(el).val(' ').trigger("input");
                                        }, 0);

                                        return el;
                                    },
                                    inputValue: function (el, that) {
                                    // console.log('inputValue')
                                    return $(el[0]).val();
                                    },
                                    isInputValid: function (el, that) {
                                    // console.log('isInputValid')
                                    return $(el[0]).val();
                                    },
                                    search: function(value, comparison) {
                                        var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds'));
                                        playerId = 0;
                                        if (value) {
                                            playerId = parseInt(value);
                                        }
                                        return selectedPlayerIds.includes(playerId);
                                    },
                                },
                                'unselectedPlayers': {
                                    conditionName: 'Unselected Players',
                                    init: function(that, fn, preDefined = null) {
                                        let el = jQuery('<input>')
                                        .attr('type','hidden')
                                        .on('input', function() {
                                            fn(that, this);
                                        });

                                        setTimeout(function() {
                                            $(el).val(' ').trigger("input");
                                        }, 0);

                                        return el;
                                    },
                                    inputValue: function (el, that) {
                                    // console.log('inputValue')
                                    return $(el[0]).val();
                                    },
                                    isInputValid: function (el, that) {
                                    // console.log('isInputValid')
                                    return $(el[0]).val();
                                    },
                                    search: function(value, comparison) {
                                        var selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds'));
                                        playerId = 0;
                                        if (value) {
                                            playerId = parseInt(value);
                                        }
                                        return !selectedPlayerIds.includes(playerId);
                                    },
                                },
                            }
                        }
                    },

                    initComplete: function () {

                        playerStatsDataTable = $('#player_stats').DataTable();

                        const api = this.api();

                        lastSortIdx = api.order()[0][0];
                        lastSortOrder = true; // Always start with 1 to n ranking

                        // hide columns that are to be hidden on initial display
                        api.columns(initially_hidden_column_names).visible(show=false, redrawCalculations=false);

                        // save current & initial previous gameType (i.e., 'Regular Season')
                        $('#gameType').data('previous', '');
                        $('#gameType').data('current', gameType.value);
                        // set current & previous "pos" searchPane selection to '' (i.e., no selection)
                        $('#DataTables_Table_0').data('previous', '');
                        $('#DataTables_Table_0').data('current', '');
                        columnVisibility();

                        api.rows().every(function() {
                            let data = this.data();
                            let match = data[name_idx].match(/>(.*?)</);
                            let name = match ? match[1] : data[name_idx];
                            let index = this.index();
                            if (!nameToIndex[name]) {
                                nameToIndex[name] = [];
                            }
                            nameToIndex[name].push(index);
                        });

                        playerStatsTableIsInitialized = true;

                    },

                    drawCallback: function() {

                        if (playerStatsTableIsInitialized) {

                            const api = this.api();

                            // set "name" as fixed column
                            setFixedColumn(api);

                            const selectedPlayerIds = JSON.parse(localStorage.getItem('selectedPlayerIds'));

                            // get current sort columns
                            let sort_idx = api.order()[0][0];
                            // let sort_order = api.order()[0][1];
                            let prevSortValue = null;
                            let rank = 1;
                            let rankIncrement = 0;
                            api.rows().every(function(rowIdx, tableLoop, rowLoop) {

                                let rowData = this.data();

                                if (executePlayerStatsTableSortDrawCallbackCode == true) {
                                    // If the sorted column value changes, increment the rank
                                    let sortValue = rowData[sort_idx];
                                    if (prevSortValue != null && sortValue != prevSortValue) {
                                        rank += rankIncrement;
                                        rankIncrement = 1;
                                    } else {
                                        rankIncrement++;
                                    }
                                    // Assign the rank
                                    rowData[sort_rank_idx] = lastSortOrder ? api.rows().count() - rank + 1 :
                                    rank;
                                    // Update the previous sorted column value
                                    prevSortValue = sortValue;

                                    this.invalidate(); // Invalidate the rowData to refresh the table

                                }

                            });

                            prevSortValue = null;
                            rank = 1;
                            rankIncrement = 0;
                            // Only iterate over rows that pass the current search
                            api.rows({ search: 'applied' }).every(function(rowIdx, tableLoop, rowLoop) {

                                let rowData = this.data();

                                // If the sorted column value changes, increment the rank
                                let sortValue = rowData[sort_idx];
                                if (prevSortValue != null && sortValue != prevSortValue) {
                                    rank += rankIncrement;
                                    rankIncrement = 1;
                                } else {
                                    rankIncrement++;
                                }
                                // Assign the rank
                                rowData[list_rank_idx] = lastSortOrder ? api.rows().count() - rank + 1 :
                                rank;
                                // Update the previous sorted column value
                                prevSortValue = sortValue;

                                this.invalidate(); // Invalidate the rowData to refresh the table

                                // Restore the state of the selected player checkboxes
                                if (selectedPlayerIds) {
                                    let playerId = rowData[id_idx];
                                    let checkbox = $(this.node()).find('.row-checkbox');
                                    checkbox.prop('checked', selectedPlayerIds.includes(playerId));
                                }

                            });

                            if (executePlayerStatsTableSortDrawCallbackCode == true) {
                                executePlayerStatsTableSortDrawCallbackCode = false;
                            }

                        }

                    },

                    rowCallback: function(row, rowData) {

                        const api = this.api();

                        // heatmaps
                        let column_idx;
                        for (let i = 0; i < heatmap_columns.length; i++) {
                            column_idx = heatmap_columns[i];
                            let cellNode = api.cell(row._DT_RowIndex, column_idx).node();
                            if (heatmaps) {
                                colourizeCell(cellNode, column_idx, rowData);
                            } else {
                                // Remove background color
                                $(cellNode).css('background-color', '');
                            }
                        }

                    }

                });

                // Use the order event to update lastSortIdx and lastSortOrder when the table is sorted
                $('#player_stats').on('order.dt', function() {
                    executePlayerStatsTableSortDrawCallbackCode = true;
                    lastSortIdx = playerStatsDataTable.order()[0][0];
                    lastSortOrder = playerStatsDataTable.order()[0][1] === 'desc' ? false : true;
                });

                // Display the checkboxes & calc z-score options
                document.getElementById('toggleCheckboxContainer').style.display = 'block';

                // *******************************************************************
                $('#player_stats tbody').on('click', '.row-checkbox', function (event) {

                    var checkbox = $(this);

                    var playerId = playerStatsDataTable.row($(this).parents('tr')).data()[id_idx];
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

                    // Reset search builder selections
                    let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                    if (JSON.stringify(currentSearchBuilderDetails).includes('selectedPlayers') || JSON.stringify(currentSearchBuilderDetails).includes('unselectedPlayers')) {
                        playerStatsDataTable.searchBuilder.rebuild(currentSearchBuilderDetails);
                    }

                });

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

                });

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
                        column_name = table.column(column).name() + ':name';
                        // state: true if the column is now visible, false if it is now hidden
                        // custom code to handle the column visibility change
                        if (state === false) { // not visible
                            if (manually_unhidden_columns.includes(column_name) === true) {
                                manually_unhidden_columns.pop(column_name);
                            }
                            if (manually_hidden_columns.includes(column_name) === false) {
                                manually_hidden_columns.push(column_name);
                            }
                        } else { // visible
                            if (manually_hidden_columns.includes(column_name) === true) {
                                manually_hidden_columns.pop(column_name);
                            }
                            if (manually_unhidden_columns.includes(column_name) === false) {
                                manually_unhidden_columns.push(column_name);
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

            caption = updateCaption();
            let tableCaption = document.querySelector('#player_stats caption');
            tableCaption.textContent = caption;

            tableCaption = document.querySelector('#managerSummary caption');
            tableCaption.textContent = caption + ' - Manager Scores';
            tableCaption.style.fontWeight = 'bold';
            tableCaption.style.textDecoration = 'underline';

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
            playerStatsDataTable.searchPanes.rebuildPane();

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

            // search panes
            positionSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[1]).DataTable();
            injurySearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[3]).DataTable();
            managerSearchPaneDataTable = $(document.querySelectorAll('.dtsp-searchPanes table.dataTable')[5]).DataTable();
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
                playerStatsDataTable.rows().every(function() {
                    var row = this.data();
                    var playerId = row[id_idx];
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

document.getElementById('autoAssignDraftPicks').addEventListener('click', async () => {

    manually_select_my_picks = document.getElementById('manuallySelectMyPicks').checked;

    // Check if DataTable instance exists
    if ($.fn.dataTable.isDataTable('#managerSummary') == false) {
        createManagerSummaryTable();
    }

    let heatmaps_previously_enabled = heatmaps;
    // disable heatmaps
    if (heatmaps === true) {
        toggleHeatmaps();
    }

    let iterations = parseInt(document.getElementById('iterations').value, 10);
    for (let i = 0; i < iterations; i++) {
        await autoAssignDraftPicks();
        // $('#draftMessage').show();
        clearDraftSimulationsTable = false;
        if (i < iterations - 1) {
            simulateStartDraftButtonClick();
        }
    }

    if ($('#clearDraftSimulationsTable')[0].checked) {
        clearDraftSimulationsTable = true;
    }

    // enable heatmaps
    if (heatmaps_previously_enabled === true) {
        toggleHeatmaps();
    }

})

document.getElementById('clearDraftSimulationsTable').addEventListener('click', () => {

    if ($('#clearDraftSimulationsTable')[0].checked) {
        clearDraftSimulationsTable = true;
    }
    else {
        clearDraftSimulationsTable = false;
    }

})

document.getElementById('startDraftButton').addEventListener('click', () => {

    draft_in_progress = true;
    draft_completed = false;
    writeToDraftSimulationsTable = document.querySelector('#writeToDraftSimulationsTable').checked;

    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

    // reset draft limits per position
    f_limit_reached = [];
    d_limit_reached = [];
    g_limit_reached = [];

    getDraftPicks(draft_order => {

        if (draft_order.error) {
            // Hide pulsing bar
            document.getElementById('pulsing-bar').style.display  = 'none';
            alert(draft_order.error)
            return
        }

        remaining_draft_picks = [...draft_order];
        draft_order_picks = [...draft_order];
        draft_manager = remaining_draft_picks[0].manager;

        clearDraftColumns();

        // Check if DataTable instance exists
        if ($.fn.dataTable.isDataTable('#managerSummary') == false) {
            createManagerSummaryTable();
            let caption = updateCaption();
            let tableCaption = document.querySelector('#managerSummary caption');
            tableCaption.textContent = caption + ' - Manager Scores';
            tableCaption.style.fontWeight = 'bold';
            tableCaption.style.textDecoration = 'underline';
        } else {
            managerSummaryScores = calcManagerSummaryScores();
            updateManagerSummaryTable(managerSummaryScores);
        }

        // myCategoryNeeds = getMyCategoryNeeds()
        // updateMyCategoryNeedsTable(myCategoryNeeds);

        document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';

        createDraftBoardTable(remaining_draft_picks)

        // hide not-useful columns
        columns_to_hide = [manager_idx, line_idx, pp_unit_idx, toi_even_pg_idx, corsi_for_percent_idx, toi_pp_pg_idx, pp_percent_idx, shooting_percent_idx, goalie_starts_idx, qualtity_starts_idx, qualtity_starts_percent_idx, really_bad_starts_idx];
        playerStatsDataTable.columns(columns_to_hide).visible(show=false, redrawCalculations=false);

        // columns to show
        columns_to_be_visible = [fantrax_score_idx, z_score_idx, z_offense_idx, z_peripheral_idx, z_g_count_idx, z_g_ratio_idx];
        playerStatsDataTable.columns(columns_to_be_visible).visible(show=true, redrawCalculations=false);

        // Hide pulsing bar
        document.getElementById('pulsing-bar').style.display = 'none';

        $('#draftMessage').show();
        $('#draftBoard').show();

        // need to remove the `.hidden` class from the element first, as `display: none` takes precedence over any other `display`
        // declaration, even if it is added dynamically with JavaScript.
        $('#autoAssignDraftPicksContainer').removeClass('hidden').css('display', 'inline-block');
        $('#undoDraftPick').removeClass('hidden').css('display', 'inline-block');

        // Reset search panes
        playerStatsDataTable.searchPanes.clearSelections();

        managerSearchPaneDataTable.rows(function(idx, data, node) {
            return data.display.includes('No data');
        }).select();

        playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);

        initDraftContextMenu();

    });
})

document.getElementById('statType').addEventListener('change', function() {
    var ewmaElements = document.getElementsByClassName('ewma');
    for (var i = 0; i < ewmaElements.length; i++) {
        ewmaElements[i].style.display = this.value === 'EWMA' ? 'flex' : 'none';
    }
});

document.getElementById('toggleScarcity').addEventListener('click', () => {

    if ($('#toggleScarcity')[0].checked) {

        // Check if DataTable instance exists
        if ($.fn.dataTable.isDataTable('#managerSummary') == false) {
            createManagerSummaryTable()
        }

        if ($.fn.dataTable.isDataTable('#myCategoryNeeds') == false) {
            createMyCategoryNeedsTable()
        }

        // Create the allPlayers array
        let allPlayers = getAllPlayers();

        if ($.fn.dataTable.isDataTable('#categoryScarcityByZScoreRange') == false) {
            // create Category Scarcity by Z-score Range table
            categoryScarcityByZScoreRange = calcCategoryScarcityByZScoreRange(allPlayers);
            createCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);
        }

        if ($.fn.dataTable.isDataTable('#categoryScarcity') == false) {
            // Filter out rows with no team manager
            let allAvailablePlayers = allPlayers.filter(function (row) {
                return row['manager'] === "";
            });
            // create Category Scarcity table
            categoryScarcity = getCategoryScarcity(allAvailablePlayers);
            createCategoryScarcityTable(categoryScarcity);
        }

    }
    // else if (!draft_in_progress) {
    else {

        if ($('#toggleSummary')[0].checked == false) {
            managerSummaryDataTable.destroy();
        }

        let myCategoryNeeds = $('#myCategoryNeeds').DataTable();
        myCategoryNeeds.destroy();
        // Remove the table element from the DOM
        $('#myCategoryNeeds').remove();

        let categoryScarcityByZScoreRange = $('#categoryScarcityByZScoreRange').DataTable();
        categoryScarcityByZScoreRange.destroy();

        let categoryScarcity = $('#categoryScarcity').DataTable();
        categoryScarcity.destroy();
    }

})

document.getElementById('undoDraftPick').addEventListener('click', () => {

    undoDraftPick();

})

document.getElementById('writeToDraftSimulationsTable').addEventListener('click', () => {

    if ($('#writeToDraftSimulationsTable')[0].checked) {
        writeToDraftSimulationsTable = true;
    }
    else {
        writeToDraftSimulationsTable = false;
    }

})

function assignDraftPick() {

    return new Promise((resolve, reject) => {

        if (auto_assign_picks === true) {
            // clear all filters on the entire table
            playerStatsDataTable.column(position_idx).search('').draw();
        }

        if (auto_assign_picks === false || (manually_select_my_picks === true && draft_manager === 'Banshee')) {
            // Reset search panes
            playerStatsDataTable.searchPanes.clearSelections();
            managerSearchPaneDataTable.rows(function(idx, data, node) {
                return data.display.includes('No data');
            }).select();

            // Reset search builder selections
            let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
            if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
            }
        }

        let managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager'] === draft_manager)[0];
        let fCount = managerSummaryData['fCount'];
        let dCount = managerSummaryData['dCount'];
        let gCount = managerSummaryData['gCount'];
        // let mfCount = managerSummaryData['mfCount'];
        let mfgmCount = managerSummaryData['mfgmCount']; // minors fantasy goalies in minors
        let gCount_adj = gCount - mfgmCount;
        let picks = managerSummaryData['picks'];

        // picks_remaining = picks - remaining_draft_picks[0].managers_pick_number + 1;

        // Define the weights for each position
        let fWeight = 13 - fCount;
        let dWeight = 10 - dCount;
        let gWeight = 4 - gCount_adj;
        if ((picks === 1 && gCount_adj === 3) || (picks === 2 && gCount_adj === 2) || (picks === 3 && gCount_adj === 1) || (picks === 4 && gCount_adj === 0)) {
            fWeight = 0;
            dWeight = 0;
        }
        if (gCount_adj === 4 && gWeight !== 0) {
            gWeight = 0;
        }

        // Calculate the total weight
        let totalWeight = fWeight + dWeight + gWeight;

        // Calculate the probabilities for each position
        let fProbability = fWeight / totalWeight;
        let dProbability = dWeight / totalWeight;
        let gProbability = gWeight / totalWeight;

        // Create an array to hold the 100 entries
        let positionsArray = [];

        // Calculate the number of 'F', 'D', and 'G' codes based on the probabilities
        let fs = Math.round(fProbability * 100);
        let ds = Math.round(dProbability * 100);
        let gs = Math.round(gProbability * 100);

        // Adjust the counts to ensure the sum is exactly 100
        let total = fs + ds + gs;
        if (total > 100) {
            let excess = total - 100;
            if (fProbability >= dProbability && fProbability >= gProbability) {
                fs -= excess;
            } else if (dProbability >= fProbability && dProbability >= gProbability) {
                ds -= excess;
            } else {
                gs -= excess;
            }
        } else if (total < 100) {
            let deficit = 100 - total;
            if (gProbability >= dProbability && gProbability >= fProbability) {
                gs += deficit;
            } else if (dProbability >= fProbability && dProbability >= gProbability) {
                ds += deficit;
            } else {
                fs += deficit;
            }
        }

        // Fill the array with 'F', 'D', and 'G' codes
        for (let i = 0; i < fs; i++) {
            positionsArray.push('F');
        }
        for (let i = 0; i < ds; i++) {
            positionsArray.push('D');
        }
        for (let i = 0; i < gs; i++) {
            positionsArray.push('G');
        }

        // Shuffle the array to randomize the order of 'F', 'D', and 'G' codes
        positionsArray = positionsArray.sort(() => Math.random() - 0.5);

        // Generate a random number between 0 and 99
        let randomValue = Math.floor(Math.random() * 100);

        let selectedPosition = positionsArray[randomValue]

        // Use the selected position to filter the playerStatsDataTable
        playerStatsDataTable.column(position_idx).search(selectedPosition);

        // The rest of your code remains the same
        if (draft_manager === 'Banshee') {
            if (selectedPosition === 'G') {
                playerStatsDataTable.order([[tier_idx, 'asc'], [z_combo_idx, 'desc']])
            }
            else {
                playerStatsDataTable.order([z_combo_idx, 'desc']);
            }
            if (manually_select_my_picks === true) {
                playerStatsDataTable.draw();
                return;
            }
        } else if (draft_manager === "Fowler's Flyers") {
            if (selectedPosition === 'G') {
                playerStatsDataTable.order([[games_idx, 'desc'], [score_idx, 'desc']])
            }
            else {
                playerStatsDataTable.order([score_idx, 'desc']);
            }
        } else {
            if (selectedPosition === 'G') {
                playerStatsDataTable.order([[games_idx, 'desc'], [score_idx, 'desc']])
            }
            else {
                playerStatsDataTable.order([score_idx, 'desc']);
            }
        }

        playerStatsDataTable.draw();

        let filteredSortedIndexes = playerStatsDataTable.rows({ order: 'current', search: 'applied' }).indexes().toArray();
        let randomIndex = Math.floor(Math.random() * 5);
        let selectedRow = filteredSortedIndexes[randomIndex];

        assignManager(selectedRow, draft_manager).then(result => {
            if (result === false) {
                auto_assign_picks = false;
                resolve();
                return;
            }

            setTimeout(function () {
                assignDraftPick().then(resolve);
            }, 0);
        }).catch(error => {
            reject(error);
        });
    });
}

// Assign manager
function assignManager(rowIndex, manager) {

    return new Promise((resolve, reject) => {

        playerStatsDataTable.cell(rowIndex, manager_idx).data(manager);
        playerStatsDataTable.cell(rowIndex, draft_round_idx).data(remaining_draft_picks[0].draft_round);
        playerStatsDataTable.cell(rowIndex, draft_position_idx).data(remaining_draft_picks[0].round_pick);
        playerStatsDataTable.cell(rowIndex, draft_overall_pick_idx).data(remaining_draft_picks[0].overall_pick);
        playerStatsDataTable.cell(rowIndex, picked_by_idx).data(manager);

        // When a player is drafted...
        let round = remaining_draft_picks[0].draft_round;  // The round number
        let pick = remaining_draft_picks[0].round_pick;  // The pick number

        let playerName = playerStatsDataTable.cell(rowIndex, name_idx).data().match(/>(.*?)</)[1];  // The name of the drafted player

        // add the player to remaining_draft_picks
        remaining_draft_picks[0].drafted_player = playerName;

        let team = playerStatsDataTable.cell(rowIndex, team_idx).data();

        let position = playerStatsDataTable.cell(rowIndex, position_idx).data(); // postion for the drafted player
        if (['LW', 'C', 'RW'].includes(position)) {
            position = 'F'
        }
        playerName = playerName + ' (' + position + '/' + team + ')';

        let tableData = $('#draftBoard').DataTable();
        // Find the corresponding cell in tableData and update it
        let cell = tableData.cell((round - 1) * 2 + 1, pick); // Get the cell object
        cell.data(playerName);

        managerSummaryScores = calcManagerSummaryScores();
        updateManagerSummaryTable(managerSummaryScores);

        // myCategoryNeeds = getMyCategoryNeeds()
        // updateMyCategoryNeedsTable(myCategoryNeeds);

        // remove the first element from remaining_draft_picks and return that element removed
        let completedPick = remaining_draft_picks.shift();
        completed_draft_picks.push(completedPick);
        if (remaining_draft_picks.length > 0) {
            draft_manager = remaining_draft_picks[0].manager;
        }

        if (remaining_draft_picks.length > 0) {

            managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];
            document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';
            resolve(true);;

        } else {

            let draftBoardTable = $('#draftBoard').DataTable();
            // Extract column names
            let columnNames = draftBoardTable.columns().header().toArray().map(header => $(header).text());
            // Extract row data
            let rowData = draftBoardTable.rows().data().toArray();
            // Create a dictionary with column names as keys
            let draftBoardDataDict = rowData.map(row => {
                let rowDict = {};
                columnNames.forEach((col, index) => {
                    rowDict[col] = row[index];
                });
                return rowDict;
            });

            // Convert dictionary to JSON format
            let jsonDataDict = JSON.stringify(draftBoardDataDict);

            writeDraftBoardToDatabase(jsonDataDict).then(results => {

                if (results.status === 'error') {
                    alert(results.error)
                    reject(new Error(results.error));
                }

                document.getElementById("draftMessage").innerHTML = "All rounds are completed.";
                destroyDraftContextMenu();
                draft_in_progress = false;
                draft_completed = true;

                // Reset search panes
                playerStatsDataTable.searchPanes.clearSelections();

                // clear all filters on the entire table
                playerStatsDataTable.column(position_idx).search('').draw();

                // Reset search builder selections
                let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                    playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
                }

                resolve(false);

            }).catch(error => {
                reject(error);
            });
        }
    });
}

// break up autoAssignDraftPicks(), a long-running operation, into smaller chunks by wrapping it and the subsequent operations with assignDraftPick(),
// and then calling assignDraftPick() repeatedly using setTimeout
async function autoAssignDraftPicks() {

    auto_assign_picks = true; // global
    await assignDraftPick();

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

function calcManagerSummaryScores() {

    // Get data from player stats table
    let originalPlayerStatsTableData = playerStatsDataTable.data().toArray();

    // Filter out rows with no team manager
    let rosteredPlayers = originalPlayerStatsTableData.filter(function (row) {
        if (draft_in_progress === true || draft_completed === true) {
            return row[manager_idx] !== "";
        } else {
            return row[manager_idx] !== "" && (row[keeper_idx] === 'Yes' || row[keeper_idx] === 'MIN');
        }
    });

    // Create new data source for new table
    let data = [];

    // Loop through original data and calculate sums for each team manager
    for (let i = 0; i < rosteredPlayers.length; i++) {
        let row = rosteredPlayers[i];

        let manager = row[manager_idx];

        let position = row[position_idx];

        let careerGames = parseInt(row[career_games_idx], 10);
        if (isNaN(careerGames)) {
            careerGames = 0;
        }

        let keeper = row[keeper_idx];
        let minors = row[minors_idx];
        let ir = row[fantrax_roster_status_idx];

        // Check if team manager already exists in new data
        let index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        if (index === -1) {
            // Team manager does not exist in new data, add new row
            data.push({
                manager: manager,
                picks: 25, // 25 because loop starts with 0; actual picks will start at 14, during draft simulation, but to start include 11 Keepers & 2 Minors Eligible
                fCount: (position !== 'G' && position !== 'D') ? 1 : 0,
                dCount: (position === 'D') ? 1 : 0,
                gCount: (position === 'G') ? 1 : 0,
                // mfCount: (position !== 'G' && careerGames < 160) || (position === 'G' && careerGames < 80) ? 1 : 0,
                mfCount: (keeper === 'MIN') ? 1 : 0, // minors (fantasy)
                mfgmCount: (keeper === 'MIN' && minors === "Yes") ? 1 : 0, // minors (fantasy) - goalie in minors
                irCount: (ir === 'IR') ? 1 : 0,
                score: 0,
                scoreSktr: 0,
                scoreOffense: 0,
                scorePeripheral: 0,
                points: 0,
                goals: 0,
                assists: 0,
                powerplayPoints: 0,
                shotsOnGoal: 0,
                blockedShots: 0,
                hits: 0,
                takeaways: 0,
                penaltyMinutes: 0,
                scoreG: 0,
                scoreCountG: 0,
                scoreRatioG: 0,
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
            // data[index].mfCount += (position !== 'G' && careerGames < 160) || (position === 'G' && careerGames < 80) ? 1 : 0,
            data[index].mfCount += (keeper === 'MIN') ? 1 : 0,
            data[index].mfgmCount += (keeper === 'MIN' && minors === "Yes") ? 1 : 0,
            data[index].irCount += (ir === 'IR') ? 1 : 0
            data[index].picks -= 1
        }
    }

    for(let i = 0; i < data.length; i++) {
        if(data[i].picks < 0) {
            data[i].picks = 0;
        }
        // adjust for managers without MIN players
        if(data[i].mfCount < 2) {
            data[i].picks = data[i].picks - (2 - data[i].mfCount);
        }
    }

    // Group data by manager_idx and position_idx
    let groupedData = rosteredPlayers.reduce(function (r, a) {

        // I think 'IR' & 'Min' players should be included in player counts, so comnenting this out for now
        // // When using season projections, exclude rows with 'IR' or 'Min' in fantrax_roster_status_idx
        // if (gameType.value !== 'Projected Season' && (a[fantrax_roster_status_idx] === 'IR' || a[fantrax_roster_status_idx] === 'Min')) {
        //     return r;
        // }

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
            // Sort data based on score_idx in descending order
            groupedData[manager][position].sort(function(a, b) {
                return b[score_idx] - a[score_idx];
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
        let additionalRow = ['F', 'D'].map(pos => groupedData[manager][pos]).flat().sort((a, b) => b[score_idx] - a[score_idx]).find(item => !rosteredPlayers.includes(item));
        if (additionalRow) {
            rosteredPlayers.push(additionalRow);
        }

    }

    // Loop through original data and calculate sums for each team manager
    for (let i = 0; i < rosteredPlayers.length; i++) {
        let row = rosteredPlayers[i];

        let player_id = row[id_idx];
        let player_position = row[position_idx];

        let manager = row[manager_idx];

        let score = 0;
        let scoreSktr = 0;
        let scoreOffense = 0;
        let scorePeripheral = 0;
        let points = 0;
        let goals = 0;
        let assists = 0;
        let powerplayPoints = 0;
        let shotsOnGoal = 0;
        let blockedShots = 0;
        let hits = 0;
        let takeaways = 0;
        let penaltyMinutes = 0;
        let scoreG = 0;
        let scoreCountG = 0;
        let scoreRatioG = 0;
        let wins = 0;
        let saves = 0;
        let gaa = 0;
        let savePercent = 0;

        if (gameType.value === 'Projected Season') {
            score = parseFloat(row[score_idx]);
            scoreSktr = parseFloat(row[score_idx]);
            scoreOffense = parseFloat(row[offense_score_idx]);
            scorePeripheral = parseFloat(row[peripheral_score_idx]);
            points = parseFloat(row[pts_score_idx]);
            goals = parseFloat(row[g_score_idx]);
            assists = parseFloat(row[a_score_idx]);
            powerplayPoints = parseFloat(row[ppp_score_idx]);
            shotsOnGoal = parseFloat(row[sog_score_idx]);
            blockedShots = parseFloat(row[blk_score_idx]);
            hits = parseFloat(row[hits_score_idx]);
            takeaways = parseFloat(row[tk_score_idx]);
            penaltyMinutes = parseFloat(row[pim_score_idx]);
            scoreG = parseFloat(row[score_idx]);
            scoreCountG = parseFloat(row[g_count_score_idx]);
            scoreRatioG = parseFloat(row[g_ratio_score_idx]);
            wins = parseFloat(row[w_score_idx]);
            saves = parseFloat(row[sv_score_idx]);
            gaa = parseFloat(row[gaa_score_idx]);
            savePercent = parseFloat(row[save_percent_score_idx]);
        }

        if (isNaN(score)) {score = 0;}
        if (isNaN(scoreSktr) || row[position_idx] === 'G') {scoreSktr = 0;}
        if (isNaN(scoreOffense)) {scoreOffense = 0;}
        if (isNaN(scorePeripheral)) {scorePeripheral = 0;}
        if (isNaN(points) || row[position_idx] !== 'D') {points = 0;}
        if (isNaN(goals)) {goals = 0;}
        if (isNaN(assists)) {assists = 0;}
        if (isNaN(powerplayPoints)) {powerplayPoints = 0;}
        if (isNaN(shotsOnGoal)) {shotsOnGoal = 0;}
        if (isNaN(blockedShots)) {blockedShots = 0;}
        if (isNaN(hits)) {hits = 0;}
        if (isNaN(takeaways)) {takeaways = 0;}
        if (isNaN(penaltyMinutes)) {penaltyMinutes = 0;}
        if (isNaN(scoreG) || row[position_idx] !== 'G') {scoreG = 0;}
        if (isNaN(scoreCountG) || row[position_idx] !== 'G') {scoreCountG = 0;}
        if (isNaN(scoreRatioG) || row[position_idx] !== 'G') {scoreRatioG = 0;}
        if (isNaN(wins)) {wins = 0;}
        if (isNaN(saves)) {saves = 0;}
        if (isNaN(gaa)) {gaa = 0;}
        if (isNaN(savePercent)) {savePercent = 0;}

        // Find team manager row index
        let index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        // Team manager exists in new data, update row
        data[index].score += score;
        data[index].scoreSktr += scoreSktr;
        data[index].scoreOffense += scoreOffense;
        data[index].scorePeripheral += scorePeripheral;
        data[index].points += points;
        data[index].goals += goals;
        data[index].assists += assists;
        data[index].powerplayPoints += powerplayPoints;
        data[index].shotsOnGoal += shotsOnGoal;
        data[index].blockedShots += blockedShots;
        data[index].hits += hits;
        data[index].takeaways += takeaways;
        data[index].penaltyMinutes += penaltyMinutes;
        data[index].scoreG += scoreG;
        data[index].scoreCountG += scoreCountG;
        data[index].scoreRatioG += scoreRatioG;
        data[index].wins += wins;
        data[index].saves += saves;
        data[index].gaa += gaa;
        data[index].savePercent += savePercent;

    }

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

function colourizeCell(cellNode, column_idx, rowData) {
    if (heatmaps == true && !(rowData[games_idx] == "")) {
        const position = rowData[position_idx];
        const category = categoryLookup[column_idx];
        if (goalie_category_heatmap_columns.has(column_idx)) {
            if (position === 'G') {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = mean_cat[`${category}`];
                if (column_idx === gaa_idx) {
                    $(cellNode).colourize({ min, max, center, theme: 'cool-warm-reverse' });
                } else {
                    $(cellNode).colourize({ min, max, center });
                }
            }
        }
        if (goalie_category_z_score_heatmap_columns.has(column_idx)) {
            // const category = categoryLookup[column_idx];
            if ( position === 'G' ) {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = 0;
                $(cellNode).colourize({ min, max, center });
            }
        }
        if (sktr_category_heatmap_columns.has(column_idx)) {
            // const category = categoryLookup[column_idx];
            if (position !== 'G') {
                if (column_idx === points_idx) {
                    if (position === 'D') {
                        const max = max_cat[`d ${category}`];
                        const center = mean_cat[`d ${category}`];
                        $(cellNode).colourize({ max, center });
                    }
                } else {
                    const max = max_cat[`sktr ${category}`];
                    const center = mean_cat[`sktr ${category}`];
                    $(cellNode).colourize({ max, center });
                }
            }
        }
        if (sktr_category_z_score_heatmap_columns.has(column_idx)) {
            // const category = categoryLookup[column_idx];
            if (position !== 'G') {
                if (column_idx === z_points_idx) {
                    if (position === 'D') {
                        const min = min_cat[`d ${category}`];
                        const max = max_cat[`d ${category}`];
                        const center = 0;
                        $(cellNode).colourize({ min, max, center });
                    }
                } else {
                    const min = min_cat[`sktr ${category}`];
                    const max = max_cat[`sktr ${category}`];
                    const center = 0;
                    $(cellNode).colourize({ min, max, center });
                }
            }
        }
        if (score_summary_heatmap_columns.has(column_idx)) {
            // const category = categoryLookup[column_idx];
            if ( column_idx === score_idx || column_idx == z_score_idx ) {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = mean_cat[`${category}`];
                $(cellNode).colourize({ min, max, center });
            } else if ( position !== 'G' && sktr_score_summary_heatmap_columns.has(column_idx) ) {
                const min = min_cat[`sktr ${category}`];
                const max = max_cat[`sktr ${category}`];
                const center = mean_cat[`sktr ${category}`];
                $(cellNode).colourize({ min, max, center });
            } else if ( position === 'G'  && goalie_score_summary_heatmap_columns.has(column_idx) ) {
                const min = min_cat[`g ${category}`];
                const max = max_cat[`g ${category}`];
                const center = mean_cat[`g ${category}`];
                $(cellNode).colourize({ min, max, center });
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

    // get game type & "pos" search pane, previous & current values
    const current_game_type = $('#gameType').data('current');
    const current_positon = $('#DataTables_Table_0').data('current');

    // get currently hidden  & visilble columns
    const currently_hidden_columns = getColumnNames(playerStatsDataTable).filter((name) => !playerStatsDataTable.column(name).visible());
    const currently_visible_columns = getColumnNames(playerStatsDataTable).filter((name) => playerStatsDataTable.column(name).visible());

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

    // don't hide position columns if already hidden
    columns_to_hide = columns_to_hide.filter(column => !currently_hidden_columns.includes(column));

    // don't make position columns visible if already visible
    columns_to_show = columns_to_show.filter(column => !currently_visible_columns.includes(column));

    // hide columns
    playerStatsDataTable.columns(columns_to_hide).visible(show=false, redrawCalculations=false);
    // unhide columns
    playerStatsDataTable.columns(columns_to_show).visible(show=true, redrawCalculations=false);

    // get current sort columns
    let sort_columns = playerStatsDataTable.order();
    for ( let sort_info of sort_columns ) {
        if ( sort_info[0] == 0 || playerStatsDataTable.column( sort_info[0] ).visible() == false ) {
            sort_columns = [score_idx, "desc"];
            break;
        }
    }
    // sort columns
    executePlayerStatsTableSortDrawCallbackCode = true;
    playerStatsDataTable.order(sort_columns);

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
        "Avovocado": "Avovocado",
        "Open Team 1": "Open Team"
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
            let header = '<tr><th colspan="1"></th><th colspan="9">Skaters</th><th colspan="4">Goalies</th></tr>';
            if ($("#categoryScarcityByZScoreRange thead tr").length === 1) {
                $("#categoryScarcityByZScoreRange thead").prepend(header);
            }
        },
    });
}

function createManagerSummaryTable() {

    // getMaxCategoryValuesAndZScores();

    managerSummaryScores = calcManagerSummaryScores();

    const properties = ['picks', 'fCount', 'dCount', 'gCount', 'mfCount', 'mfgmCount', 'irCount', 'score', 'scoreSktr', 'scoreOffense', 'scorePeripheral', 'points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways' ,'penaltyMinutes', 'scoreG', 'scoreCountG', 'scoreRatioG', 'wins', 'saves', 'gaa', 'savePercent'];

    // Initialize new DataTable with calculated managerSummaryScores
    $('#managerSummary').DataTable({
        data: managerSummaryScores,
        dom: 't',
        columns: [
            { data: 'manager', title: 'manager' },
            { data: 'picks', title: 'picks' },
            { data: 'fCount', title: 'f\'s' },
            { data: 'dCount', title: 'd\'s' },
            { data: 'gCount', title: 'g\'s' },
            { data: 'mfCount', title: 'mf\'s' },
            { data: 'mfgmCount', title: 'mfgm\'s' },
            { data: 'irCount', title: 'ir\'s' },
            { data: 'score', title: 'score' },
            { data: 'scoreSktr', title: 'score' },
            { data: 'scoreOffense', title: 'offense' },
            { data: 'scorePeripheral', title: 'peripheral' },
            { data: 'points', title: 'pts' },
            { data: 'goals', title: 'g' },
            { data: 'assists', title: 'a' },
            { data: 'powerplayPoints', title: 'ppp' },
            { data: 'shotsOnGoal', title: 'sog' },
            { data: 'blockedShots', title: 'blk' },
            { data: 'hits', title: 'hits' },
            { data: 'takeaways', title: 'tk' },
            { data: 'penaltyMinutes', title: 'pim' },
            { data: 'scoreG', title: 'score' },
            { data: 'scoreCountG', title: 'count' },
            { data: 'scoreRatioG', title: 'ratio' },
            { data: 'wins', title: 'w' },
            { data: 'saves', title: 'sv' },
            { data: 'gaa', title: 'gaa' },
            { data: 'savePercent', title: 'sv%' },
        ],
        order: [[8, "desc"]],
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

        },
        initComplete: function () {
            let header = '<tr><th colspan="2"></th><th colspan="6"></th><th colspan="1"></th><th colspan="12">Skaters</th><th colspan="7">Goalies</th>';
            if ($("#managerSummary thead tr").length === 1) {
                $("#managerSummary thead").prepend(header);
            }
            managerSummaryDataTable = $('#managerSummary').DataTable();
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

        const managerTable = $('<table>').css('margin', '10px').appendTo('#myCategoryNeedsContainer')

        managerTable.attr('id', 'myCategoryNeeds')
                    .addClass('display cell-border hover compact');

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

                // Check if values is an array and has a non-zero length
                if (!Array.isArray(values) || !values.length) {
                    // Exit the function
                    return;
                }

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

    playerStatsDataTable.rows().every(function (rowIdx, tableLoop, rowLoop) {
        let rowData = this.data();
        rowData[draft_round_idx] = '';
        rowData[draft_position_idx] = '';
        rowData[draft_overall_pick_idx] = '';
        if (rowData[keeper_idx] !== 'Yes' && rowData[keeper_idx] !== 'MIN') {
            rowData[manager_idx] = '';
        }
        this.data(rowData);
    });

    playerStatsDataTable.columns.adjust().draw();

}

function destroyDraftContextMenu() {
    // Destroy the existing context menu
    $.contextMenu('destroy', '#player_stats td');
}

function getAllPlayers() {

    // Get the data for all rows in the table
    let allPlayerTableRows = playerStatsDataTable.rows().data().toArray();

    // Create the allPlayers array
    let allPlayers = [];
    for (let i = 0; i < allPlayerTableRows.length; i++) {
        let rowData = allPlayerTableRows[i];
        let player = {
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

    const queryParams = `poolID=${poolID.value}`;

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + '?' + queryParams, function(draft_order) {
        // Call the callback function with the draft order
        callback(draft_order);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        // // Handle the error here
        // console.error("Error occurred: ", textStatus, errorThrown);
        // You can also call the callback function with an error message
        callback({ error: "An error occurred while fetching the draft order: " + errorThrown });
    });
}

function getMyCategoryNeeds() {
    const categories = ['points', 'goals', 'assists', 'powerplayPoints', 'shotsOnGoal', 'blockedShots', 'hits', 'takeaways', 'penaltyMinutes', 'wins', 'saves', 'gaa', 'savePercent'];
    const mySummaryZScores = managerSummaryScores.find(item => item.manager === 'Banshee');

    // Check if mySummaryZScores is empty or not
    if (!mySummaryZScores || Object.keys(mySummaryZScores).length == 0) {
        // If it is empty, set categoryNeeds to an empty dictionary
        const categoryNeeds = {};
        return [{ manager: 'Banshee', ...categoryNeeds }];
    }

    // Otherwise, proceed with the original code
    const categoryNeeds = categories.reduce((acc, category) => {
        // Get all z-scores for the current category
        const allZScores = managerSummaryScores.map(manager => manager[category]);
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

function getScoringCategoryCheckboxes() {

    // Get all the checkbox elements within the calcZScoresContainer
    const checkboxes = document.querySelectorAll('#calcZScoresContainer input[type="checkbox"]');

    // Create an empty object to store the checkbox values
    const checkboxValues = {};

    // Loop through each checkbox and store its value (checked or unchecked)
    checkboxes.forEach((checkbox) => {
        checkboxValues[checkbox.name] = checkbox.checked;
    });

    // Convert the object to a query string
    const scoringCategoryCheckboxes = Object.keys(checkboxValues)
        .map((key) => `${key}=${checkboxValues[key]}`)
        .join('&');

    return scoringCategoryCheckboxes;

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

function getPlayerData(generationType, seasonOrDateRadios, scoringCategoryCheckboxes, callback) {
    // Set the base URL for the Flask API endpoint
    const baseUrl = 'http://localhost:5000/player-data';

    const queryParams = `generationType=${generationType}&${scoringCategoryCheckboxes}&seasonOrDateRadios=${seasonOrDateRadios}&fromSeason=${fromSeason.value}&toSeason=${toSeason.value}&fromDate=${fromDate.value}&toDate=${toDate.value}&poolID=${poolID.value}&gameType=${gameType.value==='Regular Season' ? 'R' : gameType.value==='Playoffs' ? 'P' : 'Prj'}&statType=${statType.value}&ewmaSpan=${ewmaSpan.value}&projectionSource=${projectionSource.value}&positionalScoring=${positionalScoringCheckbox.checked}`;

    // Send a GET request to the Flask API endpoint with the specified query parameters
    $.get(baseUrl + '?' + queryParams, function(playerData) {
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

    // $('#player_stats').DataTable().columns.adjust().draw();
    playerStatsDataTable.columns.adjust().draw();
    $('#player_stats-div').show();

}

function hideTablesShowPulsingBar() {

    if (gameType.value === 'Projected Season') {
        $('#startDraftButton').addClass('hidden').css('display', 'none');
    }
    $('#autoAssignDraftPicksContainer').hide();
    $('#undoDraftPick').hide();
    $('#draftMessage').hide();
    $('#draftBoard').hide();

    // Hide pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

}

function initDraftContextMenu() {

    $.contextMenu({
        selector: '#player_stats td',
        build: function($trigger, e) {
            // Update the context menu options before the menu is shown
            return {
                callback: function(key, options) {
                    let rowIndex = playerStatsDataTable.row(this).index();
                    switch(key) {
                        case "Draft player":

                            assignManager(rowIndex, draft_manager);

                            // Reset search panes
                            playerStatsDataTable.searchPanes.clearSelections();
                            managerSearchPaneDataTable.rows(function(idx, data, node) {
                                return data.display.includes('No data');
                            }).select();

                            // Reset search builder selections
                            let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                            if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                                playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
                            }

                            // Resume auto processing
                            if (auto_assign_picks === true) {

                                assignDraftPick();
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
    let name_idx = table.column('name:name')[0][0];
    let name_visible_idx = name_idx;
    for (let i = 0; i < name_idx; i++) {
        if ( table.column(i).visible() === false ) {
            name_visible_idx = name_visible_idx - 1;
        }
    }
    table.fixedColumns().left( name_visible_idx + 1 );

}

function simulateStartDraftButtonClick() {
    // document.getElementById('startDraftButton').click();
    draft_in_progress = true;
    draft_completed = false;

    // reset draft limits per position
    f_limit_reached = [];
    d_limit_reached = [];
    g_limit_reached = [];

    remaining_draft_picks = [...draft_order_picks];
    draft_manager = remaining_draft_picks[0].manager;

    clearDraftColumns();

    managerSummaryScores = calcManagerSummaryScores();
    updateManagerSummaryTable(managerSummaryScores);

    // myCategoryNeeds = getMyCategoryNeeds()
    // updateMyCategoryNeedsTable(myCategoryNeeds);

    document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';
    $('#draftMessage').show();

    let draftBoardTable = $('#draftBoard').DataTable();
    draftBoardTable.destroy();
    createDraftBoardTable(remaining_draft_picks);

    // Reset search panes
    playerStatsDataTable.searchPanes.clearSelections();

    managerSearchPaneDataTable.rows(function(idx, data, node) {
        return data.display.includes('No data');
    }).select();

    playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);

}

function toggleHeatmaps() {

    heatmaps = !heatmaps;

    // Show pulsing bar
    document.getElementById('pulsing-bar').style.display = 'block';

    // Need a timeout for the pulsing bar display
    setTimeout(function() {

        playerStatsDataTable.columns.adjust().draw();

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

    table.draw();

}

function updateColumnIndexes(columns) {

    // column indexes
    a_score_idx = columns.findIndex(column => column.title === 'a score');
    adp_idx = columns.findIndex(column => column.title === 'fantrax adp');
    age_idx = columns.findIndex(function(column) { return column.title == 'age' });
    assists_idx = columns.findIndex(column => column.title === 'a');
    athletic_zscore_rank_idx = columns.findIndex(column => column.title === 'athletic z-score rank');
    bandaid_boy_idx = columns.findIndex(column => column.title === 'bandaid boy');
    blk_idx = columns.findIndex(column => column.title === 'blk');
    blk_score_idx = columns.findIndex(column => column.title === 'blk score');
    breakout_threshold_idx = columns.findIndex(column => column.title === 'bt');
    career_games_idx = columns.findIndex(column => column.title === 'career games');
    corsi_for_percent_idx = columns.findIndex(column => column.title === 'cf%');
    dobber_zscore_rank_idx = columns.findIndex(column => column.title === 'dobber z-score rank');
    draft_overall_pick_idx = columns.findIndex(column => column.title === 'overall');
    draft_position_idx = columns.findIndex(column => column.title === 'draft position');
    draft_round_idx = columns.findIndex(column => column.title === 'draft round');
    ev_ipp_idx = columns.findIndex(column => column.title === 'ev ipp');
    fantrax_roster_status_idx = columns.findIndex(column => column.title === 'fantrax roster status');
    fantrax_score_idx = columns.findIndex(column => column.title === 'fantrax score');
    fantrax_zscore_rank_idx = columns.findIndex(column => column.title === 'fantrax z-score rank');
    g_count_score_idx = columns.findIndex(column => column.title === 'count score');
    g_ratio_score_idx = columns.findIndex(column => column.title === 'ratio score');
    g_score_idx = columns.findIndex(column => column.title === 'g score');
    gaa_idx = columns.findIndex(column => column.title === 'gaa');
    gaa_score_idx = columns.findIndex(column => column.title === 'gaa score');
    game_today_idx = columns.findIndex(column => column.title === 'game today');
    games_idx = columns.findIndex(column => column.title === 'gp');
    goalie_starts_idx = columns.findIndex(column => column.title === 'goalie starts');
    goals_against_idx = columns.findIndex(column => column.title === 'goals against');
    goals_idx = columns.findIndex(column => column.title === 'g');
    hits_idx = columns.findIndex(column => column.title === 'hits');
    hits_score_idx = columns.findIndex(column => column.title === 'hits score');
    id_idx = columns.findIndex(column => column.title === 'id');
    injury_idx = columns.findIndex(column => column.title === 'injury');
    injury_note_idx = columns.findIndex(column => column.title === 'injury note');
    keeper_idx = columns.findIndex(column => column.title === 'keeper');
    last_game_idx = columns.findIndex(column => column.title === 'last game');
    line_idx = columns.findIndex(column => column.title === 'line');
    list_rank_idx = columns.findIndex(column => column.title === 'list rank');
    manager_idx = columns.findIndex(column => column.title === 'manager');
    minors_idx = columns.findIndex(column => column.title === 'minors');;
    name_idx = columns.findIndex(column => column.title === 'name');;
    nhl_roster_status_idx = columns.findIndex(column => column.title === 'nhl roster status');
    offense_score_idx = columns.findIndex(column => column.title === 'offense score');
    pdo_idx = columns.findIndex(column => column.title === 'pdo');
    penalties_idx = columns.findIndex(column => column.title === 'penalties');
    penalties_score_idx = columns.findIndex(column => column.title === 'penalties score');
    peripheral_score_idx = columns.findIndex(column => column.title === 'peripheral score');
    picked_by_idx = columns.findIndex(column => column.title === 'picked by');
    pim_idx = columns.findIndex(column => column.title === 'pim');
    pim_score_idx = columns.findIndex(column => column.title === 'pim score');
    points_idx = columns.findIndex(column => column.title === 'pts');
    position_idx = columns.findIndex(column => column.title === 'pos');
    pp_goals_p120_idx = columns.findIndex(column => column.title === 'pp g/120');
    pp_ipp_idx = columns.findIndex(column => column.title === 'pp ipp');
    pp_percent_idx = columns.findIndex(column => column.title === '%pp');
    pp_points_p120_idx = columns.findIndex(column => column.title === 'pp pts/120');
    pp_unit_idx = columns.findIndex(column => column.title === 'pp unit');
    pp_unit_prj_idx = columns.findIndex(column => column.title === 'pp unit prj');
    ppp_idx = columns.findIndex(column => column.title === 'ppp');
    ppp_score_idx = columns.findIndex(column => column.title === 'ppp score');
    predraft_keeper_idx = columns.findIndex(column => column.title === 'pre-draft keeper');
    prj_draft_round_idx = columns.findIndex(column => column.title === 'prj draft round');
    pts_score_idx = columns.findIndex(column => column.title === 'pts score');
    qualtity_starts_idx = columns.findIndex(column => column.title === 'qs');
    qualtity_starts_percent_idx = columns.findIndex(column => column.title === 'qs %');
    really_bad_starts_idx = columns.findIndex(column => column.title === 'rbs');
    rookie_idx = columns.findIndex(column => column.title === 'rookie');
    save_percent_score_idx = columns.findIndex(column => column.title === 'sv% score');
    saves_idx = columns.findIndex(column => column.title === 'sv');
    saves_percent_idx = columns.findIndex(column => column.title === 'sv%');
    score_idx = columns.findIndex(column => column.title === 'score');
    score_rank_idx = columns.findIndex(column => column.title === 'score rank');
    sel_idx = columns.findIndex(column => column.title === 'sel');
    shooting_percent_idx = columns.findIndex(column => column.title === 'sh%');
    shots_against_idx = columns.findIndex(column => column.title === 'shots against');
    sleeper_idx = columns.findIndex(column => column.title === 'sleeper');
    sog_idx = columns.findIndex(column => column.title === 'sog');
    sog_pp_idx = columns.findIndex(column => column.title === 'pp sog');
    sog_score_idx = columns.findIndex(column => column.title === 'sog score');
    sort_rank_idx = columns.findIndex(column => column.title === 'sort rank');
    sv_score_idx = columns.findIndex(column => column.title === 'sv score');
    team_idx = columns.findIndex(column => column.title === 'team');
    three_yp_idx = columns.findIndex(column => column.title === '3yp');
    tier_idx = columns.findIndex(column => column.title === 'tier');
    tk_idx = columns.findIndex(column => column.title === 'tk');
    tk_score_idx = columns.findIndex(column => column.title === 'tk score');
    toi_even_pg_idx = columns.findIndex(column => column.title === 'toi even pg');
    toi_even_pg_trend_idx = columns.findIndex(column => column.title === 'toi even pg (trend)');
    toi_minutes_idx = columns.findIndex(column => column.title === 'toi (min)');
    toi_pg_trend_idx = columns.findIndex(column => column.title === 'toi pg (trend)');
    toi_pp_percent_3gm_avg_idx = columns.findIndex(column => column.title === 'toi pp % (rolling avg)');
    toi_pp_percent_idx = columns.findIndex(column => column.title === 'toi pp %');
    toi_pp_pg_idx = columns.findIndex(column => column.title === 'toi pp pg');
    toi_pp_pg_trend_idx = columns.findIndex(column => column.title === 'toi pp pg (trend)');
    toi_sec_idx = columns.findIndex(column => column.title === 'toi (sec)');
    toi_sh_pg_trend_idx = columns.findIndex(column => column.title === 'toi sh pg (trend)');
    upside_idx = columns.findIndex(column => column.title === 'upside');
    w_score_idx = columns.findIndex(column => column.title === 'w score');
    watch_idx = columns.findIndex(column => column.title === 'watch');
    wins_idx = columns.findIndex(column => column.title === 'w');
    z_assists_idx = columns.findIndex(column => column.title === 'z-a');
    z_blk_idx = columns.findIndex(column => column.title === 'z-blk');
    z_combo_idx = columns.findIndex(column => column.title === 'z-combo');
    z_g_count_combo_idx = columns.findIndex(column => column.title === 'z-count combo');
    z_g_count_idx = columns.findIndex(column => column.title === 'z-count');
    z_g_ratio_combo_idx = columns.findIndex(column => column.title === 'z-ratio combo');
    z_g_ratio_idx = columns.findIndex(column => column.title === 'z-ratio');
    z_gaa_idx = columns.findIndex(column => column.title === 'z-gaa');
    z_goals_idx = columns.findIndex(column => column.title === 'z-g');
    z_hits_idx = columns.findIndex(column => column.title === 'z-hits');
    z_offense_combo_idx = columns.findIndex(column => column.title === 'z-offense combo');
    z_offense_idx = columns.findIndex(column => column.title === 'z-offense');
    z_offense_rank_idx = columns.findIndex(column => column.title === 'z-offense rank');
    z_penalties_idx = columns.findIndex(column => column.title === 'z-penalties');
    z_peripheral_combo_idx = columns.findIndex(column => column.title === 'z-peripheral combo');
    z_peripheral_idx = columns.findIndex(column => column.title === 'z-peripheral');
    z_peripheral_rank_idx = columns.findIndex(column => column.title === 'z-peripheral rank');
    z_pim_idx = columns.findIndex(column => column.title === 'z-pim');
    z_points_idx = columns.findIndex(column => column.title === 'z-pts');
    z_ppp_idx = columns.findIndex(column => column.title === 'z-ppp');
    z_saves_idx = columns.findIndex(column => column.title === 'z-sv');
    z_saves_percent_idx = columns.findIndex(column => column.title === 'z-sv%');
    z_score_idx = columns.findIndex(column => column.title === 'z-score');
    z_score_rank_idx = columns.findIndex(column => column.title === 'z-score rank');
    z_sog_idx = columns.findIndex(column => column.title === 'z-sog');
    z_tk_idx = columns.findIndex(column => column.title === 'z-tk');
    z_wins_idx = columns.findIndex(column => column.title === 'z-w');

    sktr_category_heatmap_columns = new Set([points_idx, goals_idx, assists_idx, ppp_idx, sog_idx, sog_pp_idx, tk_idx, hits_idx, blk_idx, pim_idx, penalties_idx]);
    goalie_category_heatmap_columns = new Set([wins_idx, saves_idx, gaa_idx, saves_percent_idx]);
    sktr_category_z_score_heatmap_columns = new Set([z_points_idx, z_goals_idx, z_assists_idx, z_ppp_idx, z_sog_idx, z_tk_idx, z_hits_idx, z_blk_idx, z_pim_idx, z_penalties_idx]);
    goalie_category_z_score_heatmap_columns = new Set([z_wins_idx, z_saves_idx, z_gaa_idx, z_saves_percent_idx]);
    score_summary_heatmap_columns = new Set([z_score_idx, z_offense_idx, z_peripheral_idx, z_g_count_idx, z_g_ratio_idx]);
    sktr_score_summary_heatmap_columns = new Set([score_idx, offense_score_idx, peripheral_score_idx, z_score_idx, z_offense_idx, z_peripheral_idx]);
    goalie_score_summary_heatmap_columns = new Set([score_idx, g_count_score_idx, g_ratio_score_idx, z_score_idx, z_g_count_idx, z_g_ratio_idx]);

    heatmap_columns = [...Array.from(score_summary_heatmap_columns), ...Array.from(sktr_category_heatmap_columns), ...Array.from(goalie_category_heatmap_columns), ...Array.from(sktr_category_z_score_heatmap_columns), ...Array.from(goalie_category_z_score_heatmap_columns)]
    combo_columns = [z_combo_idx, z_offense_combo_idx, z_peripheral_combo_idx, z_g_count_combo_idx, z_g_ratio_combo_idx];

    categoryLookup = {
        [assists_idx]: 'assists',
        [blk_idx]: 'blocked',
        [g_count_score_idx]: 'g_count',
        [g_ratio_score_idx]: 'g_ratio',
        [gaa_idx]: 'gaa',
        [goals_idx]: 'goals',
        [hits_idx]: 'hits',
        [offense_score_idx]: 'offense',
        [penalties_idx]: 'penalties',
        [peripheral_score_idx]: 'peripheral',
        [pim_idx]: 'pim',
        [points_idx]: 'points',
        [ppp_idx]: 'points_pp',
        [saves_idx]: 'saves',
        [saves_percent_idx]: 'save%',
        [score_idx]: 'score',
        [sog_idx]: 'shots',
        [sog_pp_idx]: 'shots_powerplay',
        [tk_idx]: 'takeaways',
        [wins_idx]: 'wins',
        [z_assists_idx]: 'z_assists',
        [z_blk_idx]: 'z_blocked',
        [z_g_count_idx]: 'z_count',
        [z_g_ratio_idx]: 'z_ratio',
        [z_gaa_idx]: 'z_gaa',
        [z_goals_idx]: 'z_goals',
        [z_hits_idx]: 'z_hits',
        [z_offense_idx]: 'z_offense',
        [z_penalties_idx]: 'z_penalties',
        [z_peripheral_idx]: 'z_peripheral',
        [z_pim_idx]: 'z_pim',
        [z_points_idx]: 'z_points',
        [z_ppp_idx]: 'z_points_pp',
        [z_saves_idx]: 'z_saves',
        [z_saves_percent_idx]: 'z_save%',
        [z_score_idx]: 'z_score',
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

    scores = playerData['scores_dict'];

}

function updateManagerSummaryTable(data) {

    // Clear the existing data in the table
    managerSummaryDataTable.clear();

    // Add the new data to the table
    managerSummaryDataTable.rows.add(data);

    // table.columns.adjust().draw();
    managerSummaryDataTable.draw();

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
        // let playerStatsTable = $('#player_stats').DataTable();

        // get most reacent draft pick
        let last_pick = completed_draft_picks.pop();
        if (last_pick) {
            var playerIndex = nameToIndex[last_pick.drafted_player];
            if (playerIndex.length === 1) {
                rowIndex = playerIndex[0];
                // clear draft information from table row for the drafted player
                playerStatsDataTable.cell(rowIndex, manager_idx).data('');
                playerStatsDataTable.cell(rowIndex, draft_round_idx).data('');
                playerStatsDataTable.cell(rowIndex, draft_position_idx).data('');
                playerStatsDataTable.cell(rowIndex, draft_overall_pick_idx).data('');
                playerStatsDataTable.cell(rowIndex, picked_by_idx).data('');

                // add the last drafted player back to remaining_draft_picks array
                last_pick.drafted_player = '';
                remaining_draft_picks.unshift(last_pick);

                let round = remaining_draft_picks[0].draft_round;  // The round number
                let pick = remaining_draft_picks[0].round_pick;  // The pick number
                let tableData = $('#draftBoard').DataTable();
                // Find the corresponding cell in tableData and update it
                let cell = tableData.cell((round - 1) * 2 + 1, pick); // Get the cell object
                cell.data('');

                managerSummaryScores = calcManagerSummaryScores();
                updateManagerSummaryTable(managerSummaryScores);

                // myCategoryNeeds = getMyCategoryNeeds()
                // updateMyCategoryNeedsTable(myCategoryNeeds);

                draft_manager = remaining_draft_picks[0].manager;
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

    // Clear the existing data in the table
    playerStatsDataTable.clear();

    // Add the new data to the table
    playerStatsDataTable.rows.add(data);

    // Redraw the table
    playerStatsDataTable.columns.adjust().draw();

}

function writeDraftBoardToDatabase(draftBoardDataDict, callback) {

    return new Promise((resolve, reject) => {

        // Set the base URL for the Flask API endpoint
        const baseUrl = 'http://localhost:5000/draft-board';

        const queryParams = `draft_board=${draftBoardDataDict}&projectionSource=${projectionSource.value}&positionalScoring=${positionalScoringCheckbox.checked}&clearDraftSimulationsTable=${clearDraftSimulationsTable.checked}`;

        // Send a GET request to the Flask API endpoint with the specified query parameters
        $.get(baseUrl + '?' + queryParams, function(draft_board) {
            // Call the callback function with the draft order
            resolve(draft_board);
        })
        .fail(function(jqXHR, textStatus, errorThrown) {
            // Reject the promise with an error message
            reject(new Error("An error occurred while writing draft board to database: " + errorThrown));
        });
    });
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
