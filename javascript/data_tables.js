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
var draft_completed = true;
var draft_order;
var writeToDraftSimulationsTable = false;
var clearDraftSimulationsTable = false;
var managerAutoDraftScoreColumns = [];

// Define the base array
const baseArray = [1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3, 1, 1, 1, 1];

// Function to generate a series
function generateSeries(a, d, length) {
    let series = [];
    for (let i = 0; i < length; i++) {
        series.push(a + i * d);
    }
    return series;
}

// Construct the multipliers array
const multipliers = [
    baseArray, // 0 element
    generateSeries(1 / 4, (1 - 1 / 4) / 3, 3).concat(baseArray.slice(0, 10)), // 1 element
    generateSeries(1 / 7, (1 - 1 / 7) / 6, 6).concat(baseArray.slice(0, 7)), // 2 element
    generateSeries(1 / 10, (1 - 1 / 10) / 9, 9).concat(baseArray.slice(0, 4)), // 3 element
    Array(13).fill(1) // 4 element
];

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

var skippedCells = 0;

var nameToIndex = {};

// datatables
var managerSearchPaneDataTable;
var injurySearchPaneDataTable;
var positionSearchPaneDataTable;
var additionalFiltersSearchPaneDataTable;
var playerStatsDataTable;
var managerSummaryDataTable;

var managerSummaryScores;
var managerSummaryColumns;

var dateRangePickerSelection;

var baseSearchBuilderCriteria = {
    "criteria": [
        {
            "condition": "contains",
            "data": "name",
            "type": "html",
            "value": []
        },
        {
            "condition": "!=",
            "data": "team",
            "type": "string",
            "value": ["(N/A)"]
        },
        {
            "condition": "<=",
            "data": "age",
            "type": "num",
            "value": []
        },
        {
            "criteria": [
                {
                    "condition": ">=",
                    "data": "z-offense",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-peripheral",
                    "type": "num",
                    "value": []
                },
            ],
            "logic": "OR"
        },
        {
            "criteria": [
                {
                    "condition": ">=",
                    "data": "z-pts",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-g",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-a",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-ppp",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-sog",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-tk",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-hits",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-blk",
                    "type": "num",
                    "value": []
                },
                {
                    "condition": ">=",
                    "data": "z-pim",
                    "type": "num",
                    "value": []
                },
            ],
            "logic": "OR"
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

var mappedIndex = -1; // Declare a variable to store mappedIndex

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

    // hide\display draftButtonsWrapper, as appropriate
    if (gameType.value === 'Projected Season' && $.fn.dataTable.isDataTable('#player_stats')) {
        $('#draftButtonsWrapper').removeClass('hidden').css('display', 'inline-block');
    } else {
        $('#draftButtonsWrapper').addClass('hidden').css('display', 'none');
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
            var selectedRows = table.rows('.selected');
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

            /////////////////////////////////////////////////////////////////////////////////////////////////////////////
            // // make trade with Jason
            // for (let i = 0; i < stats_data.length; i++) {
            //     if (stats_data[i][9] === 8477960) {
            //         // Kempe
            //         stats_data[i][33] = "Banshee";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8480193) {
            //         // Tarasov
            //         stats_data[i][33] = "Fowler's Flyers";
            //         stats_data[i][21] = "";
            //     } else if (stats_data[i][9] === 8482087) {
            //         // Guhle
            //         stats_data[i][21] = "";
            //     }
            // }
            /////////////////////////////////////////////////////////////////////////////////////////////////////////////

            ///////////////////////////////////////////////////////////////////////////////////////////////////////////
            // // dispersal draft result
            // for (let i = 0; i < stats_data.length; i++) {
            //     if (stats_data[i][9] === 8479325) {
            //         // McAvoy
            //         stats_data[i][33] = "Banshee";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8475786) {
            //         // Hyman
            //         stats_data[i][33] = "Avovocado";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8476459) {
            //         // Zibanejad
            //         stats_data[i][33] = "Camaro SS";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8476454) {
            //         // Nugent-Hopkins
            //         stats_data[i][33] = "Horse Palace 26";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8471724) {
            //         // Letang
            //         stats_data[i][33] = "El Paso Pirates";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8482684) {
            //         // Luke Hughes
            //         stats_data[i][33] = "Urban Legends";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8478439) {
            //         // Konecny
            //         stats_data[i][33] = "One Man Gang Bang";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8478366) {
            //         // Vatrano
            //         stats_data[i][33] = "CanDO Know Huang";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8476462) {
            //         // Hamilton
            //         stats_data[i][33] = "Fowler's Flyers";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][9] === 8471215) {
            //         // Malkin
            //         stats_data[i][33] = "Wheels On Meals";
            //         stats_data[i][21] = "Yes";
            //     } else if (stats_data[i][33] === 'Open Team 1' || stats_data[i][33] === 'Open Team 2') {
            //         stats_data[i][33] = "";
            //     }
            // }

            ///////////////////////////////////////////////////////////////////////////////////////////////////////////

            // In JavaScript, when you assign an array to another variable using let data = stats_data, both data and stats_data point to the same array
            // in memory. So, if you modify data, it will also modify stats_data and vice versa.
            // These methods only create a shallow copy of the array. If your array contains objects or other arrays, you may need to create a deep copy instead
            let data = JSON.parse(JSON.stringify(stats_data));
            let columns = JSON.parse(JSON.stringify(column_titles));

            updateColumnIndexes(columns);

            // If #player_stats is already a DataTable, update it
            if ($.fn.DataTable.isDataTable('#player_stats')) {

                updatePlayerStatsTable(data);

                // Check if DataTable instance exists
                if ($.fn.dataTable.isDataTable('#managerSummary') == false) {
                    createManagerSummaryTable();
                }

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
                                        label: 'Minors Fantasy Eligible',
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

                        // custom sort for 'tier' column
                        {targets: [tier_idx],
                            type: "custom_goalie_tier_sort",
                            orderSequence: ['asc']
                        },

                        // custom sort for 'prj adp', 'line', 'line prj', 'pp unit', 'pp unit prj', 'athletic z-score rank', 'dobber z-score rank', 'fantrax z-score rank' columns
                        {targets: [adp_idx, line_idx, pp_unit_idx, pp_unit_prj_idx, athletic_zscore_rank_idx, dobber_zscore_rank_idx, fantrax_zscore_rank_idx, draft_position_idx, draft_round_idx, prj_draft_round_idx, dobber_rank_idx],
                            type: "custom_integer_sort",
                            orderSequence: ['asc']
                        },

                        // custom sort for breakout_threshold_idx
                        {targets: [breakout_threshold_idx],
                            type: "custom_breakout_threshold_sort",
                            orderSequence: ['asc']
                        },

                        // custom sort for 'toi pg (trend)', 'toi even pg (trend)', 'toi pp pg (trend)', 'toi sh pg (trend)' columns
                        {targets: [toi_pg_trend_idx, toi_even_pg_trend_idx, toi_pp_pg_trend_idx, toi_sh_pg_trend_idx],
                         type: "custom_time_delta_sort",
                         orderSequence: ['desc']
                        },

                        // custom sort for 'height' column
                        {targets: [height_idx],
                            type: "custom_height_sort",
                        },

                        // custom sort for 'height' column
                        {targets: [shooting_percent_idx],
                            type: "custom_float_sort",
                        },

                    ],

                    fixedHeader: true,
                    fixedColumns: true,
                    orderCellsTop: true,
                    pagingType: 'full_numbers',

                    lengthMenu: [
                        [25, 50, 100, 250, 500, -1],
                        ['25 per page', '50 per page', '100 per page', '250 per page', '500 per page', 'All']
                    ],
                    pageLength: 25,
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
                            exportOptions: {
                                columns: ':visible', // Export visible columns
                                // custom export function
                                format: {
                                    body: function (data, row, column, node) {
                                        // Reuse precomputed mappedIndex
                                        if (column === mappedIndex) {
                                            // Extract name from HTML in 'data'
                                            let tempDiv = document.createElement("div");
                                            tempDiv.innerHTML = data; // Set the HTML content

                                            // Find the anchor and return its text
                                            let anchor = tempDiv.querySelector("a");
                                            return anchor ? anchor.textContent : ""; // Anchor text or empty string
                                        }

                                        // Return the original data for other columns
                                        return data;
                                    }
                                }
                            },
                            action: function (e, dt, button, config) {
                                // Precompute `mappedIndex`
                                let api = dt; // Get the DataTable instance
                                let visibleColumns = api.columns(':visible').indexes();

                                for (let i = 0; i < visibleColumns.length; i++) {
                                    if (visibleColumns[i] === name_idx) {
                                        mappedIndex = i;
                                        break;
                                    }
                                }

                                // Call the default action (export)
                                $.fn.dataTable.ext.buttons.excelHtml5.action.call(this, e, dt, button, config);
                            }
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
                            text: 'Toggle Name Colours',
                            action: function (e, dt, node, config) {
                                dt.rows().every(function() {
                                    var rowData = this.data();
                                    var rowId = this.index();
                                    if ($(this.node()).hasClass('colors-off')) {
                                        rowData[name_idx] = originalColors[rowId];
                                        $(this.node()).removeClass('colors-off');
                                    } else {
                                        // Save the original color if not already saved
                                        if (!originalColors[rowId]) {
                                            originalColors[rowId] = rowData[name_idx];
                                        }
                                        rowData[name_idx] = rowData[name_idx].replace(/style="color:.*?"/, 'style="color: green"')
                                        $(this.node()).addClass('colors-off');
                                    }
                                    this.data(rowData);
                                });
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

                        // Check if DataTable instance exists
                        if ($.fn.dataTable.isDataTable('#managerSummary') == false) {
                            createManagerSummaryTable();
                        }

                        if ($.fn.dataTable.isDataTable('#managerSummary') === true) {
                            managerSummaryScores = calcManagerSummaryScores();
                            updateManagerSummaryTable(managerSummaryScores);
                        }

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

                        // Cache the visibleColumns and mappedIndex
                        visibleColumns = playerStatsDataTable.columns(':visible').indexes();
                        mappedIndex = visibleColumns.indexOf(name_idx); // Map the actual name index to the visible index

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

                    },

                    // createdRow: function(row, data, dataIndex) {
                    //     if (data[watch_idx] === "Yes") {
                    //         $(row).css('color', 'red');
                    //     }
                    // }

                });

                // Store the original colours using row indices
                var originalColors = {};
                table.rows().every(function() {
                    var rowId = this.index();
                    originalColors[rowId] = this.data()[name_idx];
                });

                // Use the order event to update lastSortIdx and lastSortOrder when the table is sorted
                $('#player_stats').on('order.dt', function() {
                    executePlayerStatsTableSortDrawCallbackCode = true;
                    lastSortIdx = playerStatsDataTable.order()[0][0];
                    lastSortOrder = playerStatsDataTable.order()[0][1] === 'desc' ? false : true;
                });

                // Display the Show Manager Summary & checkboxes
                document.getElementById('toggleSummaryCheckboxContainer').style.display = 'block';
                document.getElementById('toggleScarcityCheckboxContainer').style.display = 'block';

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
                    // custom ascending sorts for "tier" column
                    "custom_goalie_tier_sort-asc": function (val1, val2) {

                        if (val1 === '' || val1 === null || val1 === undefined) {
                            return 1;
                        }
                        if (val2 === '' || val2 === null || val2 === undefined) {
                            return -1;
                        }

                        // Extract the numeric part of the tier values and compare them
                        var num1 = parseInt(val1.replace('Tier ', ''), 10);
                        var num2 = parseInt(val2.replace('Tier ', ''), 10);

                        return num1 - num2;
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

                    // custom ascending sort for breakout threshold columns
                    "custom_breakout_threshold_sort-asc": function (val1, val2) {

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
                        return Math.abs(num1) - Math.abs(num2);
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

                    // Custom sort for player heights
                    "custom_height_sort-asc": function (val1, val2) {
                        return compareHeights(val1, val2);
                    },

                    // Custom sort for player heights
                    "custom_height_sort-desc": function (val1, val2) {
                        return compareHeights(val2, val1); // Reverse comparison for descending
                    },

                    // Custom sort for player heights
                    "custom_float_sort-asc": function (val1, val2) {
                        return compareFloatValues(val1, val2, 'asc');
                    },

                    // Custom sort for player heights
                    "custom_float_sort-desc": function (val1, val2) {
                        return compareFloatValues(val1, val2, 'desc'); // Reverse comparison for descending
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
                            if (!initially_hidden_column_names.includes(column_name) && !manually_hidden_columns.includes(column_name)) {
                                manually_hidden_columns.push(column_name);
                            }
                        } else { // visible
                            if (manually_hidden_columns.includes(column_name) === true) {
                                manually_hidden_columns.pop(column_name);
                            }
                            if (initially_hidden_column_names.includes(column_name) && !manually_unhidden_columns.includes(column_name)) {
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
            tableCaption.textContent = caption + ' - Strengths & Weaknesses for Current Roster';
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

    /////////////////////////////////////////////////////////////////////////////////////////
    // These are executed when the "Start Draft" button is clicked, but can be manually
    // changed prior to clicking "Auto-assign Draft Picks" button

    // clear all filters on the entire table
    playerStatsDataTable.column(position_idx).search('');

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
    /////////////////////////////////////////////////////////////////////////////////////////

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

    // Hide draft message
    $('#draftMessage').hide();

    let iterations = parseInt(document.getElementById('iterations').value, 10);
    for (let i = 0; i < iterations; i++) {
        await autoAssignDraftPicks();
        // $('#draftMessage').show();
        clearDraftSimulationsTable = false;
        if (i < iterations - 1) {
            simulateStartDraftButtonClick();
        }
    }

    document.getElementById("draftMessage").innerHTML = iterations + " simulation(s) completed";
    $('#draftMessage').show();

    // if ($('#clearDraftSimulationsTable')[0].checked) {
    //     clearDraftSimulationsTable = true;
    // }

    // Get initial draft values from HTML
    let initialClearDraftSimulationsTable = $('#clearDraftSimulationsTable').prop('defaultChecked');
    clearDraftSimulationsTable = initialClearDraftSimulationsTable;

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

document.getElementById('draftSummariesButton').addEventListener('click', () => {

    return new Promise((resolve, reject) => {

        writeDraftSummariesToDatabase().then(results => {

            if (results.status === 'error') {
                alert(results.error)
                reject(new Error(results.error));
            }
            else {
                openDataTablesInNewTab(results.draft_simulations_agg, results.draft_simulations_agg_columns, results.draft_simulations_manager_scores_agg, results.draft_simulations_manager_scores_agg_columns);
                resolve(false);
            }

        }).catch(error => {
            reject(error);
        });
    });

})

document.getElementById('startDraftButton').addEventListener('click', () => {

    // Get initial draft values from HTML
    let initialManuallySelectMyPicks = $('#manuallySelectMyPicks').prop('defaultChecked');
    let initialIterations = $('#iterations').prop('defaultValue');
    let initialWriteToDraftSimulationsTable = $('#writeToDraftSimulationsTable').prop('defaultChecked');
    let initialClearDraftSimulationsTable = $('#clearDraftSimulationsTable').prop('defaultChecked');

    // Set properties to initial draft values
    $('#manuallySelectMyPicks').prop('checked', initialManuallySelectMyPicks);
    $('#iterations').val(initialIterations);
    $('#writeToDraftSimulationsTable').prop('checked', initialWriteToDraftSimulationsTable);
    $('#clearDraftSimulationsTable').prop('checked', initialClearDraftSimulationsTable);

    auto_assign_picks = false;
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
            tableCaption.textContent = caption + ' - Strengths & Weaknesses for Current Roster';
            tableCaption.style.fontWeight = 'bold';
            tableCaption.style.textDecoration = 'underline';
        } else {
            managerSummaryScores = calcManagerSummaryScores();
            updateManagerSummaryTable(managerSummaryScores);
        }

        getManagerAutoDraftScoreColumnIndexes()

        // myCategoryNeeds = getMyCategoryNeeds()
        // updateMyCategoryNeedsTable(myCategoryNeeds);

        managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];

        document.getElementById("draftMessage").innerHTML =
            "Round: " + remaining_draft_picks[0].draft_round +
            "; Pick: " + remaining_draft_picks[0].round_pick +
            "; Overall: " + remaining_draft_picks[0].overall_pick +
            "; Manager: " + draft_manager +
            ' (' + getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)' +
            "<br>" +
            "Currently has " + managerSummaryData.fCount +
            " Fs; " + managerSummaryData.dCount +
            " Ds; " + managerSummaryData.gCount +
            " Gs";

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
        // $('#undoDraftPick').removeClass('hidden').css('display', 'inline-block');

        // clear all filters on the entire table
        playerStatsDataTable.column(position_idx).search('');

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

        initDraftContextMenu();

    });
})

document.getElementById('statType').addEventListener('change', function() {
    var ewmaElements = document.getElementsByClassName('ewma');
    for (var i = 0; i < ewmaElements.length; i++) {
        ewmaElements[i].style.display = this.value === 'EWMA' ? 'flex' : 'none';
    }
})

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

        // if ($.fn.dataTable.isDataTable('#categoryScarcityByZScoreRange') == false) {
        //     // create Category Scarcity by Z-score Range table
        //     categoryScarcityByZScoreRange = calcCategoryScarcityByZScoreRange(allPlayers);
        //     createCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);
        // }

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

        // if ($('#toggleSummary')[0].checked == false) {
        //     managerSummaryDataTable.destroy();
        // }

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

document.getElementById('ManagerSummaryPositions').addEventListener('change', function() {

    layoutManagerSummaryTable()

})

document.getElementById('rosterInfoCheckbox').addEventListener('click', () => {

    layoutManagerSummaryTable()

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

        let selectedRow;

        if (draft_manager !== 'Open Team 1' && draft_manager !== 'Open Team 2') {

            // clear all filters on the entire table
            playerStatsDataTable.column(position_idx).search('');

            let managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager'] === draft_manager)[0];
            let fCount = managerSummaryData['fCount'];
            let dCount = managerSummaryData['dCount'];
            let gCount = managerSummaryData['gCount'];
            // let mfCount = managerSummaryData['mfCount'];
            let mfgmCount = managerSummaryData['mfgmCount']; // minors fantasy goalies in minors
            // let mCount = managerSummaryData['mCount']; // minors
            let gCount_adj = gCount - mfgmCount;
            let picks_remaining = managerSummaryData['picks'];

            let player_name;
            let overall_pick = remaining_draft_picks[0].overall_pick;
            if (overall_pick === 1 ) {
                player_name = 'Macklin Celebrini';
            }
            else if (overall_pick === 3 ) {
                player_name = 'Ivan Demidov';
            }


            if (player_name) {
                var playerIndex = nameToIndex[player_name];
                if (playerIndex.length === 1) {
                    selectedRow = playerIndex[0];
                }
            }
            else {
                // Define the weights for each position
                let fWeight = 13 - fCount;
                let dWeight = 10 - dCount;
                let gWeight = 4 - gCount_adj;

                if (gCount_adj >= 0 && gCount_adj <= 4) {
                    if (picks_remaining >= 1 && picks_remaining <= 13) {
                        gWeight *= multipliers[gCount_adj][13 - picks_remaining];
                    }
                    if (picks_remaining <= (gCount_adj === 0 ? 4 : gCount_adj === 1 ? 3 : gCount_adj === 2 ? 2 : gCount_adj === 3 ? 1: 0)) {
                        fWeight = 0;
                        dWeight = 0;
                    }
                    else if (draft_manager === 'Banshee') {
                        if (picks_remaining >= (gCount_adj === 0 ? 13 : gCount_adj === 1 ? 9 : gCount_adj === 2 ? 7 : gCount_adj === 3 ? 2: 1)) {
                            gWeight = 0;
                        }
                    }
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
                if (draft_manager === "Fowler's Flyers" && (overall_pick === 11 || overall_pick === 14)) {
                    selectedPosition = 'D';
                }

                // Use the selected position to filter the playerStatsDataTable
                playerStatsDataTable.column(position_idx).search(selectedPosition);

                // Determine the column index based on draft_manager and selectedPosition
                // Find the manager in managerSummaryScores
                let managersAutoDraftScoreColumn = managerAutoDraftScoreColumns.find(summary => summary.manager === draft_manager);
                // Get the autoDraftScoreColumnIndex value for the current draft_manager
                let sortColumnIndexAndSeq = managersAutoDraftScoreColumn ? managersAutoDraftScoreColumn['autoDraftScoreColumnIndex'] : null;
                let sortColumnIndexes;
                if (draft_manager === 'Banshee') {
                    // sortColumnIndexAndSeq = selectedPosition === 'G' ? score_idx : score_idx;
                    // sortColumnIndexes = selectedPosition === 'G' ? [[tier_idx, 'asc'], sortColumnIndexAndSeq] : sortColumnIndexAndSeq;
                    sortColumnIndexes = selectedPosition === 'G' ? [[dobber_rank_idx, 'asc']] : sortColumnIndexAndSeq;
                } else if (draft_manager === "Fowler's Flyers") {
                    // sortColumnIndexAndSeq = selectedPosition === 'G' ? z_score_idx : z_score_idx;
                    sortColumnIndexes = selectedPosition === 'G' ? sortColumnIndexAndSeq : sortColumnIndexAndSeq;
                // } else if (writeToDraftSimulationsTable === false) {
                //     // sortColumnIndexAndSeq = selectedPosition === 'G' ? z_score_idx : z_score_idx;
                //     sortColumnIndexes = selectedPosition === 'G' ? [[adp_idx, 'asc'], sortColumnIndexAndSeq] : [[adp_idx, 'asc'], sortColumnIndexAndSeq];
                } else {
                    // sortColumnIndexAndSeq = selectedPosition === 'G' ? z_score_idx : z_score_idx;
                    sortColumnIndexes = selectedPosition === 'G' ? sortColumnIndexAndSeq : sortColumnIndexAndSeq;
                }

                playerStatsDataTable.order(sortColumnIndexes).draw();

                if (manually_select_my_picks === true && draft_manager === 'Banshee') {

                    // Show pulsing bar
                    document.getElementById('pulsing-bar').style.display = 'block';

                    // Need a timeout for the pulsing bar display
                    setTimeout(function() {

                        playerStatsDataTable.columns.adjust().draw();

                    // clear all filters on the entire table
                        playerStatsDataTable.column(position_idx).search('').draw();

                        // Reset search panes
                        playerStatsDataTable.searchPanes.clearSelections();
                        managerSearchPaneDataTable.rows(function(idx, data, node) {
                            return data.display.includes('No data');
                        }).select();

                        // additionalFiltersSearchPaneDataTable.rows(function(idx, data, node) {
                        //     return data.display.includes('On watch list');
                        // }).select();

                        // Reset search builder selections
                        let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                        if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                            playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
                        }
                        // currentSearchBuilderDetails.criteria[2].criteria[0].value = [27];
                        // currentSearchBuilderDetails.criteria[2].criteria[1].value = ["Yes"];
                        // playerStatsDataTable.searchBuilder.rebuild(currentSearchBuilderDetails);

                        // // show "Undo Previous Pick" button
                        // if ($('#undoDraftPick').hasClass('hidden')) {
                        //     $('#undoDraftPick').removeClass('hidden').css('display', 'inline-block');
                        // }

                        // Hide pulsing bar
                        document.getElementById('pulsing-bar').style.display = 'none';

                    }, 2000);

                    resolve();
                    return;

                }

                if (draft_manager === 'Banshee') {
                    additionalFiltersSearchPaneDataTable.rows(function(idx, data, node) {
                        return data.display.includes('On watch list');
                    }).select();
                }

                let filteredSortedIndexes = playerStatsDataTable.rows({ order: 'current', search: 'applied' }).indexes().toArray();

                // Get the value of the first row's score, adp, and games
                let firstRowScore = parseFloat(playerStatsDataTable.cell(filteredSortedIndexes[0], sortColumnIndexAndSeq[0]).data());
                // let firstADP = parseFloat(playerStatsDataTable.cell(filteredSortedIndexes[0], adp_idx).data());
                let firstRowGames = parseFloat(playerStatsDataTable.cell(filteredSortedIndexes[0], games_idx).data());

                let score_delta = 0.1;
                if (selectedPosition === 'G') {
                    score_delta = 0.2;
                }
                let filteredIndexes = filteredSortedIndexes.filter(index => {
                    // // Filter on players within 13 or adp, which hopefully means they are relatively close in value
                    // if (writeToDraftSimulationsTable === false) {
                    //     let adp = parseFloat(playerStatsDataTable.cell(index, adp_idx).data());
                    //     return ((index === filteredSortedIndexes[0]) || ((firstADP + 13) >= adp));
                    // }
                    // else {
                    //     // Filter the indexes to include the first row and rows within 10% of the first row's score
                    //     // Additionally, if selectedPosition is 'G', filter based on games within 8 of firstRowGames
                    //     let score = parseFloat(playerStatsDataTable.cell(index, sortColumnIndexAndSeq[0]).data());
                    //     if (selectedPosition === 'G') {
                    //         let games = playerStatsDataTable.cell(index, games_idx).data();
                    //         return ((index === filteredSortedIndexes[0]) || (score >= firstRowScore) || ((Math.abs(score - firstRowScore) <= (score_delta * firstRowScore)) &&
                    //             (Math.abs(games - firstRowGames) <= 8)));
                    //     } else {
                    //         return ((index === filteredSortedIndexes[0]) || (score >= firstRowScore) || (Math.abs(score - firstRowScore) <= (score_delta * firstRowScore)));
                    //     }
                    // }
                    // Filter the indexes to include the first row and rows within percentage (as defined by score_delta) of the first row's score
                    // Additionally, if selectedPosition is 'G', filter based on games within 8 of firstRowGames
                    let score = parseFloat(playerStatsDataTable.cell(index, sortColumnIndexAndSeq[0]).data());
                    let sortColumnSeq = sortColumnIndexAndSeq[1];
                    let is1stRow = index === filteredSortedIndexes[0];
                    let scoreIsSameOrBetter = score >= firstRowScore;
                    let scoreWithinDelta = Math.abs(score - firstRowScore) <= (score_delta * firstRowScore);
                    if (sortColumnSeq === 'asc') {
                        scoreIsSameOrBetter = score <= firstRowScore;
                        scoreWithinDelta = Math.abs(score - firstRowScore) <= 10;
                    }
                    let games = playerStatsDataTable.cell(index, games_idx).data();
                    let gamesWithinDelta = Math.abs(games - firstRowGames) <= 8;
                    if (selectedPosition === 'G') {
                        return (is1stRow || scoreIsSameOrBetter || (scoreWithinDelta && gamesWithinDelta));
                    } else {
                        return (is1stRow || scoreIsSameOrBetter || scoreWithinDelta);
                    }
                });

                // Calculate a random index from the filtered indexes
                let randomIndex = Math.floor(Math.random() * filteredIndexes.length);
                selectedRow = filteredIndexes[randomIndex];
            }

        }

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

    // show "Undo Previous Pick" button
    if (auto_assign_picks === false && $('#undoDraftPick').hasClass('hidden')) {
        $('#undoDraftPick').removeClass('hidden').css('display', 'inline-block');
    }

    return new Promise((resolve, reject) => {

        if (draft_manager !== 'Open Team 1' && draft_manager !== 'Open Team 2') {

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
            if (pick === 1) {
                skippedCells = 0;
            }

            let rowIdx = (round - 1) * 2;
            let colIdx = pick + skippedCells;

            if (round % 2 === 0) {
                // For even rounds, start from the right
                colIdx = tableData.columns().count() - 1 - (pick - 1) - skippedCells;
            }

            let managerCell = tableData.cell(rowIdx, colIdx).data();
            while (managerCell === '') {
                skippedCells = skippedCells + 1;
                if (round % 2 === 0) {
                    // For even rounds, start from the right
                    colIdx = tableData.columns().count() - 1 - (pick - 1) - skippedCells;
                } else {
                    // For odd rounds, start from the left
                    colIdx = pick + skippedCells;
                }
                managerCell = tableData.cell(rowIdx, colIdx).data();
            }
            let cell = tableData.cell(rowIdx + 1, colIdx); // Get the cell object
            cell.data(playerName);

            // Check if playerName contains '(G/' and set background color
            if (playerName.includes('(G/')) {
                $(cell.node()).css('background-color', '#1E90FF'); // DodgerBlue
            }
            else if (playerName.includes('(D/')) {
                $(cell.node()).css('background-color', '#BA55D3'); // MediumOrchid
            }
            else if (playerName.includes('(F/')) {
                $(cell.node()).css('background-color', '#228B22'); // ForestGreen
            }

            managerSummaryScores = calcManagerSummaryScores();
            updateManagerSummaryTable(managerSummaryScores);

            // myCategoryNeeds = getMyCategoryNeeds()
            // updateMyCategoryNeedsTable(myCategoryNeeds);

            // remove the first element from remaining_draft_picks and return that element removed

        }

        if (manager === 'Banshee') {
            additionalFiltersSearchPaneDataTable.rows(function(idx, data, node) {
                return data.display.includes('On watch list');
            }).deselect();
        }

        let completedPick = remaining_draft_picks.shift();
        completed_draft_picks.push(completedPick);
        if (remaining_draft_picks.length > 0) {
            draft_manager = remaining_draft_picks[0].manager;
            while (remaining_draft_picks.length > 0 && (draft_manager === 'Open Team 1' || draft_manager === 'Open Team 2')) {
                completedPick = remaining_draft_picks.shift();
                completed_draft_picks.push(completedPick);
                if (remaining_draft_picks.length > 0) {
                    draft_manager = remaining_draft_picks[0].manager;
                }
            }
        }

        if (remaining_draft_picks.length > 0) {

            managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];

            document.getElementById("draftMessage").innerHTML =
                "Round: " + remaining_draft_picks[0].draft_round +
                "; Pick: " + remaining_draft_picks[0].round_pick +
                "; Overall: " + remaining_draft_picks[0].overall_pick +
                "; Manager: " + draft_manager +
                ' (' + getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)' +
                "<br>" +
                "Currently has " + managerSummaryData.fCount +
                " Fs; " + managerSummaryData.dCount +
                " Ds; " + managerSummaryData.gCount +
                " Gs";

            resolve(true);

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

            // Convert dictionaries to JSON format
            let jsonDataDict1 = JSON.stringify(draftBoardDataDict);
            let jsonDataDict2 = JSON.stringify(managerSummaryScores);

            writeDraftBoardToDatabase(jsonDataDict1, jsonDataDict2).then(results => {

                if (results.status === 'error') {
                    alert(results.error)
                    reject(new Error(results.error));
                }

                // hide draft parameters
                $('#autoAssignDraftPicksContainer').hide();

                destroyDraftContextMenu();
                draft_in_progress = false;
                draft_completed = true;

                // // Reset search panes
                // playerStatsDataTable.searchPanes.clearSelections();

                // clear all filters on the entire table
                playerStatsDataTable.column(position_idx).search('');

                // // Reset search builder selections
                // let currentSearchBuilderDetails = playerStatsDataTable.searchBuilder.getDetails();
                // if (JSON.stringify(currentSearchBuilderDetails) !== JSON.stringify(baseSearchBuilderCriteria)) {
                //     playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);
                // }

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
                } else if (acc[category] === undefined) {
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
            return row[manager_idx] !== "" && row[manager_idx] !== null;
        } else {
            return row[manager_idx] !== "" && row[manager_idx] !== null && (row[keeper_idx] === 'Yes' || row[keeper_idx] === 'MIN');
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
        let fantrax_roster_status = row[fantrax_roster_status_idx]
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
                mfCount: ((draft_completed === false && keeper === 'MIN') || (draft_completed === true && fantrax_roster_status === 'Min')) ? 1 : 0, // minors (fantasy)
                mfgmCount: (position === 'G' && ((draft_completed === false && keeper === 'MIN') || (draft_completed === true && fantrax_roster_status === 'Min')) && minors === "Yes") ? 1 : 0, // minors (fantasy) - goalie in minors
                mCount: (minors === "Yes") ? 1 : 0, // minors (fantasy) - goalie in minors
                irCount: (ir === 'IR') ? 1 : 0,
                score: 0,
                scoreSktr: 0,
                scoreSktrOffense: 0,
                scoreSktrPeripheral: 0,
                scoreF: 0,
                scoreFOffense: 0,
                scoreFPeripheral: 0,
                scoreD: 0,
                scoreDOffense: 0,
                scoreDPeripheral: 0,
                points: 0,
                goals: 0,
                assists: 0,
                powerplayPoints: 0,
                shotsOnGoal: 0,
                blockedShots: 0,
                hits: 0,
                takeaways: 0,
                penaltyMinutes: 0,
                goals_f: 0,
                assists_f: 0,
                powerplayPoints_f: 0,
                shotsOnGoal_f: 0,
                blockedShots_f: 0,
                hits_f: 0,
                takeaways_f: 0,
                penaltyMinutes_f: 0,
                points_d: 0,
                goals_d: 0,
                assists_d: 0,
                powerplayPoints_d: 0,
                shotsOnGoal_d: 0,
                blockedShots_d: 0,
                hits_d: 0,
                takeaways_d: 0,
                penaltyMinutes_d: 0,
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
            data[index].mfCount += ((draft_completed === false && keeper === 'MIN') || (draft_completed === true && fantrax_roster_status === 'Min')) ? 1 : 0,
            data[index].mfgmCount += (position === 'G' && ((draft_completed === false && keeper === 'MIN') || (draft_completed === true && fantrax_roster_status === 'Min')) && minors === "Yes") ? 1 : 0,
            data[index].mCount += (minors === "Yes") ? 1 : 0,
            data[index].irCount += (ir === 'IR') ? 1 : 0
            data[index].picks -= 1
        }
    }

    for(let i = 0; i < data.length; i++) {
        if (draft_completed === true) {
            data[i].picks = 0;
        }
        else {
            if(data[i].picks < 0) {
                data[i].picks = 0;
            }
            // adjust for managers without MIN players
            if(data[i].mfCount < 2) {
                data[i].picks = data[i].picks - (2 - data[i].mfCount);
            }
        }
    }

    // Group data by manager_idx and position_idx
    let groupedData = rosteredPlayers.reduce(function (r, a) {

        // When using season projections, exclude rows with 'IR' in fantrax roster status, or player is in minors
        if (gameType.value !== 'Projected Season' && (a[fantrax_roster_status_idx] === 'IR' || a[minors_idx] === 'Yes')) {
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
            // Sort data based on score_idx in descending order
            groupedData[manager][position].sort(function(a, b) {
                return b[score_idx] - a[score_idx];
            });

            // Filter top rows based on position
            if (position === 'F') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 10));
            } else if (position === 'D') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 7));
            } else if (position === 'G') {
                rosteredPlayers.push(...groupedData[manager][position].slice(0, 3));
            }
        }

        // // Add the top row from either 'F' or 'D' that is not already in the top 9 for 'F' or top 6 for 'D'
        // let additionalRow = ['F', 'D'].map(pos => groupedData[manager][pos]).flat().sort((a, b) => b[score_idx] - a[score_idx]).find(item => !rosteredPlayers.includes(item));
        // if (additionalRow) {
        //     rosteredPlayers.push(additionalRow);
        // }

    }

    // Loop through original data and calculate sums for each team manager
    for (let i = 0; i < rosteredPlayers.length; i++) {
        let row = rosteredPlayers[i];

        let position = row[position_idx];
        if (position === "C" || position === "LW" || position === "RW") {
            position = "F";
        }

        let manager = row[manager_idx];

        let points = 0;
        let goals = 0;
        let assists = 0;
        let powerplayPoints = 0;
        let shotsOnGoal = 0;
        let blockedShots = 0;
        let hits = 0;
        let takeaways = 0;
        let penaltyMinutes = 0;
        let goals_f = 0;
        let assists_f = 0;
        let powerplayPoints_f = 0;
        let shotsOnGoal_f = 0;
        let blockedShots_f = 0;
        let hits_f = 0;
        let takeaways_f = 0;
        let penaltyMinutes_f = 0;
        let points_d = 0;
        let goals_d = 0;
        let assists_d = 0;
        let powerplayPoints_d = 0;
        let shotsOnGoal_d = 0;
        let blockedShots_d = 0;
        let hits_d = 0;
        let takeaways_d = 0;
        let penaltyMinutes_d = 0;
        let wins = 0;
        let saves = 0;
        let gaa = 0;
        let savePercent = 0;

        points = parseFloat(row[points_score_idx]);
        goals = parseFloat(row[goals_score_idx]);
        assists = parseFloat(row[assists_score_idx]);
        powerplayPoints = parseFloat(row[ppp_score_idx]);
        shotsOnGoal = parseFloat(row[sog_score_idx]);
        blockedShots = parseFloat(row[blk_score_idx]);
        hits = parseFloat(row[hits_score_idx]);
        takeaways = parseFloat(row[tk_score_idx]);
        penaltyMinutes = parseFloat(row[pim_score_idx]);
        goals_f = parseFloat(row[goals_score_idx]);
        assists_f = parseFloat(row[assists_score_idx]);
        powerplayPoints_f = parseFloat(row[ppp_score_idx]);
        shotsOnGoal_f = parseFloat(row[sog_score_idx]);
        blockedShots_f = parseFloat(row[blk_score_idx]);
        hits_f = parseFloat(row[hits_score_idx]);
        takeaways_f = parseFloat(row[tk_score_idx]);
        penaltyMinutes_f = parseFloat(row[pim_score_idx]);
        points_d = parseFloat(row[points_score_idx]);
        goals_d = parseFloat(row[goals_score_idx]);
        assists_d = parseFloat(row[assists_score_idx]);
        powerplayPoints_d = parseFloat(row[ppp_score_idx]);
        shotsOnGoal_d = parseFloat(row[sog_score_idx]);
        blockedShots_d = parseFloat(row[blk_score_idx]);
        hits_d = parseFloat(row[hits_score_idx]);
        takeaways_d = parseFloat(row[tk_score_idx]);
        penaltyMinutes_d = parseFloat(row[pim_score_idx]);
        wins = parseFloat(row[wins_scoreidx]);
        saves = parseFloat(row[saves_score_idx]);
        gaa = parseFloat(row[gaa_score_idx]);
        savePercent = parseFloat(row[save_percent_score_idx]);

        if (isNaN(points) || position !== 'D') {points = 0;}
        if (isNaN(goals) || position === 'G') {goals = 0;}
        if (isNaN(assists) || position === 'G') {assists = 0;}
        if (isNaN(powerplayPoints) || position === 'G') {powerplayPoints = 0;}
        if (isNaN(shotsOnGoal) || position === 'G') {shotsOnGoal = 0;}
        if (isNaN(blockedShots) || position === 'G') {blockedShots = 0;}
        if (isNaN(hits) || position === 'G') {hits = 0;}
        if (isNaN(takeaways) || position === 'G') {takeaways = 0;}
        if (isNaN(penaltyMinutes) || position === 'G') {penaltyMinutes = 0;}
        if (isNaN(goals_f) || position !== 'F') {goals_f = 0;}
        if (isNaN(assists_f) || position !== 'F') {assists_f = 0;}
        if (isNaN(powerplayPoints_f) || position !== 'F') {powerplayPoints_f = 0;}
        if (isNaN(shotsOnGoal_f) || position !== 'F') {shotsOnGoal_f = 0;}
        if (isNaN(blockedShots_f) || position !== 'F') {blockedShots_f = 0;}
        if (isNaN(hits_f) || position !== 'F') {hits_f = 0;}
        if (isNaN(takeaways_f) || position !== 'F') {takeaways_f = 0;}
        if (isNaN(penaltyMinutes_f) || position !== 'F') {penaltyMinutes_f = 0;}
        if (isNaN(points_d) || position !== 'D') {points_d = 0;}
        if (isNaN(goals_d) || position !== 'D') {goals_d = 0;}
        if (isNaN(assists_d) || position !== 'D') {assists_d = 0;}
        if (isNaN(powerplayPoints_d) || position !== 'D') {powerplayPoints_d = 0;}
        if (isNaN(shotsOnGoal_d) || position !== 'D') {shotsOnGoal_d = 0;}
        if (isNaN(blockedShots_d) || position !== 'D') {blockedShots_d = 0;}
        if (isNaN(hits_d) || position !== 'D') {hits_d = 0;}
        if (isNaN(takeaways_d) || position !== 'D') {takeaways_d = 0;}
        if (isNaN(penaltyMinutes_d) || position !== 'D') {penaltyMinutes_d = 0;}
        if (isNaN(wins) || position !== 'G') {wins = 0;}
        if (isNaN(saves) || position !== 'G') {saves = 0;}
        if (isNaN(gaa) || position !== 'G') {gaa = 0;}
        if (isNaN(savePercent) || position !== 'G') {savePercent = 0;}

        // Find team manager row index
        let index = data.findIndex(function (item) {
            return item.manager === manager;
        });

        // Team manager exists in new data, update row
        data[index].points += points;
        data[index].goals += goals;
        data[index].assists += assists;
        data[index].powerplayPoints += powerplayPoints;
        data[index].shotsOnGoal += shotsOnGoal;
        data[index].blockedShots += blockedShots;
        data[index].hits += hits;
        data[index].takeaways += takeaways;
        data[index].penaltyMinutes += penaltyMinutes;
        data[index].goals_f += goals_f;
        data[index].assists_f += assists_f;
        data[index].powerplayPoints_f += powerplayPoints_f;
        data[index].shotsOnGoal_f += shotsOnGoal_f;
        data[index].blockedShots_f += blockedShots_f;
        data[index].hits_f += hits_f;
        data[index].takeaways_f += takeaways_f;
        data[index].penaltyMinutes_f += penaltyMinutes_f;
        data[index].points_d += points_d;
        data[index].goals_d += goals_d;
        data[index].assists_d += assists_d;
        data[index].powerplayPoints_d += powerplayPoints_d;
        data[index].shotsOnGoal_d += shotsOnGoal_d;
        data[index].blockedShots_d += blockedShots_d;
        data[index].hits_d += hits_d;
        data[index].takeaways_d += takeaways_d;
        data[index].penaltyMinutes_d += penaltyMinutes_d;
        data[index].wins += wins;
        data[index].saves += saves;
        data[index].gaa += gaa;
        data[index].savePercent += savePercent;

    }

    // rank catetores
    const categories = ["points", "goals", "assists", "powerplayPoints", "shotsOnGoal", "blockedShots", "hits", "takeaways", "penaltyMinutes", "goals_f", "assists_f", "powerplayPoints_f", "shotsOnGoal_f", "blockedShots_f", "hits_f", "takeaways_f", "penaltyMinutes_f", "points_d", "goals_d", "assists_d", "powerplayPoints_d", "shotsOnGoal_d", "blockedShots_d", "hits_d", "takeaways_d", "penaltyMinutes_d", "wins", "saves", "gaa", "savePercent"];
    // const categories = ["points", "goals", "assists", "powerplayPoints", "shotsOnGoal", "blockedShots", "hits", "takeaways", "penaltyMinutes", "wins", "saves", "gaa", "savePercent"];
    categories.forEach(category => {
        data.sort((a, b) => b[category] - a[category]);

        // Temporary array to store ranks before applying them
        let tempRanks = new Array(data.length);

        data.forEach((manager, index) => {
            const sameRankManagers = data.filter(m => m[category] === manager[category]);
            const rankSum = sameRankManagers.reduce((sum, m) => sum + (11 - data.indexOf(m)), 0);
            const averageRank = rankSum / sameRankManagers.length;

            sameRankManagers.forEach(m => {
                tempRanks[data.indexOf(m)] = averageRank;
            });
        });

        // Apply the calculated ranks to the actual data
        data.forEach((manager, index) => {
            manager[`${category}`] = tempRanks[index];
        });
    });

    data.forEach(manager => {
        manager.score = ["points", "goals", "assists", "powerplayPoints", "shotsOnGoal", "blockedShots", "hits", "takeaways", "penaltyMinutes", "wins", "saves", "gaa", "savePercent"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreSktr = ["points", "goals", "assists", "powerplayPoints", "shotsOnGoal", "blockedShots", "hits", "takeaways", "penaltyMinutes"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreSktrOffense = ["points", "goals", "assists", "powerplayPoints", "shotsOnGoal"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreSktrPeripheral = ["blockedShots", "hits", "takeaways", "penaltyMinutes"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreF = ["goals_f", "assists_f", "powerplayPoints_f", "shotsOnGoal_f", "blockedShots_f", "hits_f", "takeaways_f", "penaltyMinutes_f"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreFOffense = ["goals_f", "assists_f", "powerplayPoints_f", "shotsOnGoal_f"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreFPeripheral = ["blockedShots_f", "hits_f", "takeaways_f", "penaltyMinutes_f"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreD = ["points_d", "goals_d", "assists_d", "powerplayPoints_d", "shotsOnGoal_d", "blockedShots_d", "hits_d", "takeaways_d", "penaltyMinutes_d"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreDOffense = ["points_d", "goals_d", "assists_d", "powerplayPoints_d", "shotsOnGoal_d"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreDPeripheral = ["blockedShots_d", "hits_d", "takeaways_d", "penaltyMinutes_d"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreG = ["wins", "saves", "gaa", "savePercent"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreCountG = ["wins", "saves"].reduce((sum, category) => sum + manager[`${category}`], 0);
        manager.scoreRatioG = ["gaa", "savePercent"].reduce((sum, category) => sum + manager[`${category}`], 0);
    });

    return data;

}

// function calcPositionCategoryZScores(player_stats) {
//     // Define the positions and their respective z-scores
//     const positionCategories = {
//         'Forward': {'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Defence': {'z_points': z_points_idx, 'z_goals': z_goals_idx, 'z_assists': z_assists_idx, 'z_ppp': z_ppp_idx, 'z_sog': z_sog_idx, 'z_tk': z_tk_idx, 'z_hits': z_hits_idx, 'z_blk': z_blk_idx, 'z_pim': z_pim_idx},
//         'Goalie': {'z_wins': z_wins_idx, 'z_saves': z_saves_idx, 'z_saves_percent': z_saves_percent_idx, 'z_gaa': z_gaa_idx}
//     };

//     // Initialize the result array
//     let replacementPlayerZscores = {};

//     // Iterate over each position
//     for (let position in positionCategories) {
//         replacementPlayerZscores[position] = {};

//         // Filter the players based on the position and whether they are drafted
//         let poolTeamPlayers = player_stats.filter(player => {
//             if (position === "Forward") {
//                 return ["LW", "C", "RW"].includes(player[position_idx]) && player[manager_idx];
//             } else if (position === "Defence") {
//                 return player[position_idx] === "D" && player[manager_idx];
//             } else if (position === "Goalie") {
//                 return player[position_idx] === "G" && player[manager_idx];
//             }
//         });

//         // Filter the players based on the position
//         let allPlayers = player_stats.filter(player => {
//             if (position === "Forward") {
//                 return ["LW", "C", "RW"].includes(player[position_idx]);
//             } else if (position === "Defence") {
//                 return player[position_idx] === "D";
//             } else if (position === "Goalie") {
//                 return player[position_idx] === "G";
//             }
//         });

//         // Iterate over each category for the current position
//         for (let category in positionCategories[position]) {
//             let tableIndex = positionCategories[position][category];
//             // Filter out rows where column with index = tableIndex has a non-blank value
//             let filteredPlayers = allPlayers.filter(player => player[tableIndex] !== '');
//             // Sort the players based on the category
//             // The subtraction operation (b[tableIndex] - a[tableIndex]) in the sort function ensures that JavaScript treats the values as numbers, not strings
//             filteredPlayers.sort((a, b) => b[tableIndex] - a[tableIndex]);
//             // Find the "count + 1" value in category
//             replacementPlayerZscores[position][category] = filteredPlayers[poolTeamPlayers.length] ? parseFloat(filteredPlayers[poolTeamPlayers.length][tableIndex]) : null;
//         }
//     }

//     return replacementPlayerZscores;
// }

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
        if (goalie_category_score_heatmap_columns.has(column_idx)) {
            if ( position === 'G' ) {
                const min = min_cat[`${category}`];
                const max = max_cat[`${category}`];
                const center = mean_cat[`${category}`];
                $(cellNode).colourize({ min, max, center });
            }
        }
        // if (goalie_score_summary_heatmap_columns.has(column_idx)) {
        //     if ( position === 'G' ) {
        //         const min = min_cat[`${category}`];
        //         const max = max_cat[`${category}`];
        //         const center = mean_cat[`${category}`];
        //         $(cellNode).colourize({ min, max, center });
        //     }
        // }
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
        if (sktr_category_score_heatmap_columns.has(column_idx)) {
            if (position !== 'G') {
                if (column_idx === points_score_idx) {
                    if (position === 'D') {
                        const min = min_cat[`d ${category}`];
                        const max = max_cat[`d ${category}`];
                        const center = mean_cat[`d ${category}`];
                        $(cellNode).colourize({ min, max, center });
                    }
                } else {
                    const min = min_cat[`sktr ${category}`];
                    const max = max_cat[`sktr ${category}`];
                    const center = mean_cat[`sktr ${category}`];
                    $(cellNode).colourize({ min, max, center });
                }
            }
        }
        // if (sktr_score_summary_heatmap_columns.has(column_idx)) {
        //     if (position !== 'G') {
        //         const min = min_cat[`${category}`];
        //         const max = max_cat[`${category}`];
        //         const center = mean_cat[`${category}`];
        //         $(cellNode).colourize({ min, max, center });
        //     }
        // }
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
        if (sktr_time_heatmap_columns.has(column_idx)) {
            if (position !== 'G') {
                const min = 0;
                const max = max_cat[`sktr ${category}`];
                const center = mean_cat[`sktr ${category}`];
                $(cellNode).colourize({ min, max, center });
            }
        }
        if (sktr_percent_heatmap_columns.has(column_idx)) {
            if (position !== 'G') {
                const min = 0;
                const max = max_cat[`sktr ${category}`];
                const center = mean_cat[`sktr ${category}`];
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

// Function to compare floats
function compareFloatValues(val1, val2, order) {
    // Trim the strings to handle white spaces
    let trimmedVal1 = $.trim(val1);
    let trimmedVal2 = $.trim(val2);

    // Handle empty cell cases
    if (trimmedVal1 === '' && trimmedVal2 === '') {
        return 0; // both are empty, considered equal
    }
    if (trimmedVal1 === '') {
        return 1; // val1 (empty) goes to the end
    }
    if (trimmedVal2 === '') {
        return -1; // val2 (empty) goes to the end
    }

    // Parse the floats
    let float1 = parseFloat(trimmedVal1);
    let float2 = parseFloat(trimmedVal2);

    // Handle NaN cases (if the values are not numbers)
    if (isNaN(float1) && isNaN(float2)) {
        return 0; // both are non-numeric, considered equal
    }
    if (isNaN(float1)) {
        return 1; // non-numeric goes to the end
    }
    if (isNaN(float2)) {
        return -1; // non-numeric goes to the end
    }

    // Numeric comparison
    if (order === 'asc') {
        return float1 - float2; // will return negative if float1 < float2, positive if float1 > float2
    } else {
        return float2 - float1; // will return negative if float2 < float1, positive if float2 > float1
    }
}

// Function to compare heights
function compareHeights(val1, val2) {
    let height1InInches = extractHeightInInches(val1);
    let height2InInches = extractHeightInInches(val2);

    // Handle cases where one or both heights are invalid
    if (isNaN(height1InInches)) return 1; // Sort invalid height to bottom
    if (isNaN(height2InInches)) return -1; // Sort invalid height to bottom

    // Return the difference for comparison
    return height1InInches - height2InInches;
}

// Function to extract height in inches from a string
function extractHeightInInches(heightString) {
    const match = heightString.match(/(\d+)' *(\d+)"/);
    if (match) {
        const feet = parseInt(match[1], 10);
        const inches = parseInt(match[2], 10);
        return (feet * 12) + inches; // convert to total inches
    }
    return NaN; // Return NaN for invalid formats
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
                        theme: "cool-warm",
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
    var rowIndex = 0;  // Initialize row index counter

    // Create a mapping of original manager names to new names
    // Names are ordered by the manager's draft position
    var managerMapping = {
        "One Man Gang Bang": "OMGB",
        "Open Team 1": "OT1",
        "El Paso Pirates": "EPP",
        "Urban Legends": "UL",
        "Avovocado": "Avocado",
        "Open Team 2": "OT2",
        "Camaro SS": "Camaro",
        "WhatA LoadOfIt": "WhatA",
        "Banshee": "Banshee",
        "Horse Palace 26": "Horsey",
        "CanDO Know Huang": "CanDO",
        "Fowler's Flyers": "FF",
        "Wheels On Meals": "Wheels",
    };

    for (var i = 0; i < remaining_draft_picks.length; i++) {
        if (remaining_draft_picks[i].draft_round !== currentRound) {

            // Reverse the order of the cells in playerRowData except for the first column
            if ((rowIndex + 1) % 4 === 3) {
                reversedRowData = [playerRowData[0]].concat(rowData.slice(1).reverse());
                tableData.push(reversedRowData);
            } else {
                tableData.push(rowData);
            }

            tableData.push(playerRowData);

            currentRound = remaining_draft_picks[i].draft_round;
            rowData = [currentRound];
            playerRowData = [currentRound];
            rowIndex += 2;  // Increment row index by 2 since we are adding two rows each time
        }
        let manager = remaining_draft_picks[i].manager;
        let shortManager = managerMapping[manager];  // Get the new manager name from the mapping
        if (manager === 'Open Team 1' || manager === 'Open Team 2') {
            rowData.push('');
        }
        else {
            rowData.push(shortManager  + " (" + remaining_draft_picks[i].managers_pick_number + "/" + remaining_draft_picks[i].overall_pick + ")");
        }
        playerRowData.push('');  // Add an empty string for the player in the new row
    }
    // Reverse the order of the cells in the last playerRowData except for the first column
    if ((rowIndex + 1) % 4 === 3) {
        reversedRowData = [playerRowData[0]].concat(rowData.slice(1).reverse());
        tableData.push(reversedRowData);
    } else {
        tableData.push(rowData);
    }

    tableData.push(playerRowData);  // Push the last player row

    // build column titles
    column_titles = [{title: "Rnd"}].concat(Object.keys(managerMapping).map((key, i) => ({
        title: '<div style="text-align: center;">' + (i + 1) + '<br>(' + managerMapping[key] + ')</div>'
    })));

    // Initialize DataTable
    $('#draftBoard').DataTable({
        data: tableData,
        columns: column_titles, // Generate column titles
        ordering: false,
        autoWidth: false,
        // stripeClasses: ['odd-row', 'even-row'],
        dom: 't',
        pageLength: 28,
        createdRow: function(row, data, dataIndex) {
            // Loop through each cell in the row
            $('td', row).each(function(colIndex) {
                // Center the text in each cell
                $(this).css('text-align', 'center');

                // If the cell contains "Banshee", change its color
                if (this.innerText.includes('Avocado')) {
                    $(this).css('color', '#00ffcc');
                }
                else if (this.innerText.includes('Banshee')) {
                    $(this).css('color', '#ffff00');
                }
                else if (this.innerText.includes('CanDO')) {
                    $(this).css('color', '#00cc00');
                }
                else if (this.innerText.includes('Camaro')) {
                    $(this).css('color', '#ff0000');
                }
                else if (this.innerText.includes('EPP')) {
                    $(this).css('color', '#800080');
                }
                else if (this.innerText.includes('FF')) {
                    $(this).css('color', '#FFA07A');
                }
                else if (this.innerText.includes('Horsey')) {
                    $(this).css('color', '#663300');
                }
                else if (this.innerText.includes('OMGB')) {
                    $(this).css('color', '#0099ff');
                }
                else if (this.innerText.includes('WhatA')) {
                    $(this).css('color', '#003399');
                }
                else if (this.innerText.includes('Wheels')) {
                    $(this).css('color', '#99ffcc');
                }
                else if (this.innerText.includes('UL')) {
                    $(this).css('color', '#6600cc');
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

    managerSummaryScores = calcManagerSummaryScores();

    // Determine the title for 'picks' column based on draft_completed
    let picksTitle = draft_completed ? 'players' : 'picks';

    data = managerSummaryScores;

    managerSummaryColumns = [
        // Here's the complete list of keys you can use when defining a jQuery DataTable:
        //     data: Specifies the data source for the column.
        //     title: Sets the column's title.
        //     render: Allows custom rendering of column data.
        //     className: Assigns a CSS class to the column.
        //     defaultContent: Defines default content for the column when data is null.
        //     visible: Controls column visibility (true or false).
        //     orderable: Allows sorting on the column (true or false).
        //     searchable: Enables searching on the column (true or false).
        //     width: Sets the width of the column.
        //     type: Defines the column's type, like num, date, etc.
        //     createdCell: Executes a function when a cell is created.
        //     contentPadding: Adds padding to the column’s content.
        //     cellType: Defines the cell type (td or th).
        //     name: Sets a name for the column, which can be useful for column visibility toggling.
        //     orderData: Specifies alternative data to be used for ordering.
        //     orderDataType: Sets the data type for ordering purposes.
        //     orderSequence: Defines the sorting order (asc, desc).
        //     orderFixed: Fixes the ordering of this column.
        //     autoWidth: Auto-adjusts the width of the column based on content.
        { data: 'manager', title: 'manager', name: 'manager', group: 'all' },
        { data: 'score', title: 'score', name: 'score', group: 'compact' },
        { data: 'scoreSktr', title: 'score', name: 'scoreSktr', group: 'summaryScoreSktr' },
        { data: 'scoreSktrOffense', title: 'offense', name: 'scoreSktrOffense', group: 'summaryScoreSktr' },
        { data: 'scoreSktrPeripheral', title: 'peripheral', name: 'scoreSktrPeripheral', group: 'summaryScoreSktr' },
        { data: 'scoreF', title: 'score', name: 'scoreF', group: 'summaryScoreF' },
        { data: 'scoreFOffense', title: 'offense', name: 'scoreFOffense', group: 'summaryScoreF' },
        { data: 'scoreFPeripheral', title: 'peripheral', name: 'scoreFPeripheral', group: 'summaryScoreF' },
        { data: 'scoreD', title: 'score', name: 'scoreD', group: 'summaryScoreD' },
        { data: 'scoreDOffense', title: 'offense', name: 'scoreDOffense', group: 'summaryScoreD' },
        { data: 'scoreDPeripheral', title: 'peripheral', name: 'scoreDPeripheral', group: 'summaryScoreD' },
        { data: 'scoreG', title: 'score', name: 'scoreG', group: 'summaryScoreG' },
        { data: 'scoreCountG', title: 'count', name: 'scoreCountG', group: 'summaryScoreG' },
        { data: 'scoreRatioG', title: 'ratio', name: 'scoreRatioG', group: 'summaryScoreG' },
        {
            data: null,
            title: picksTitle,
            name: 'picksPlayersCount',
            render: function(data, type, row) {
                return draft_completed ? row['fCount'] + row['dCount'] + row['gCount'] : row['picks'];
            },
            group: 'roster'
        },
        { data: 'fCount', title: 'f', name: 'fCount', group: 'roster' },
        { data: 'dCount', title: 'd', name: 'dCount', group: 'roster' },
        { data: 'gCount', title: 'g', name: 'gCount', group: 'roster' },
        { data: 'mfCount', title: 'mf', name: 'mfCount', group: 'roster' },
        // { data: 'mfgmCount', title: 'mfgm\'s', name: 'mfgmCount', group: 'roster' },
        { data: 'mCount', title: 'minors', name: 'mCount', group: 'roster' },
        { data: 'irCount', title: 'ir', name: 'irCount', group: 'roster' },
        { data: 'points', title: 'pts', name: 'points', group: 'categoryScoreSktr' },
        { data: 'goals', title: 'g', name: 'goals', group: 'categoryScoreSktr' },
        { data: 'assists', title: 'a', name: 'assists', group: 'categoryScoreSktr' },
        { data: 'powerplayPoints', title: 'ppp', name: 'powerplayPoints', group: 'categoryScoreSktr' },
        { data: 'shotsOnGoal', title: 'sog', name: 'shotsOnGoal', group: 'categoryScoreSktr' },
        { data: 'blockedShots', title: 'blk', name: 'blockedShots', group: 'categoryScoreSktr' },
        { data: 'hits', title: 'hits', name: 'hits', group: 'categoryScoreSktr' },
        { data: 'takeaways', title: 'tk', name: 'takeaways', group: 'categoryScoreSktr' },
        { data: 'penaltyMinutes', title: 'pim', name: 'penaltyMinutes', group: 'categoryScoreSktr' },
        { data: 'goals_f', title: 'g', name: 'goals_f', group: 'categoryScoreF' },
        { data: 'assists_f', title: 'a', name: 'assists_f', group: 'categoryScoreF' },
        { data: 'powerplayPoints_f', title: 'ppp', name: 'powerplayPoints_f', group: 'categoryScoreF' },
        { data: 'shotsOnGoal_f', title: 'sog', name: 'shotsOnGoal_f', group: 'categoryScoreF' },
        { data: 'blockedShots_f', title: 'blk', name: 'blockedShots_f', group: 'categoryScoreF' },
        { data: 'hits_f', title: 'hits', name: 'hits_f', group: 'categoryScoreF' },
        { data: 'takeaways_f', title: 'tk', name: 'takeaways_f', group: 'categoryScoreF' },
        { data: 'penaltyMinutes_f', title: 'pim', name: 'penaltyMinutes_f', group: 'categoryScoreF' },
        { data: 'points_d', title: 'pts', name: 'points_d', group: 'categoryScoreD' },
        { data: 'goals_d', title: 'g', name: 'goals_d', group: 'categoryScoreD' },
        { data: 'assists_d', title: 'a', name: 'assists_d', group: 'categoryScoreD' },
        { data: 'powerplayPoints_d', title: 'ppp', name: 'powerplayPoints_d', group: 'categoryScoreD' },
        { data: 'shotsOnGoal_d', title: 'sog', name: 'shotsOnGoal_d', group: 'categoryScoreD' },
        { data: 'blockedShots_d', title: 'blk', name: 'blockedShots_d', group: 'categoryScoreD' },
        { data: 'hits_d', title: 'hits', name: 'hits_d', group: 'categoryScoreD' },
        { data: 'takeaways_d', title: 'tk', name: 'takeaways_d', group: 'categoryScoreD' },
        { data: 'penaltyMinutes_d', title: 'pim', name: 'penaltyMinutes_d', group: 'categoryScoreD' },
        { data: 'wins', title: 'w', name: 'wins', group: 'categoryScoreG' },
        { data: 'saves', title: 'sv', name: 'saves', group: 'categoryScoreG' },
        { data: 'gaa', title: 'gaa', name: 'gaa', group: 'categoryScoreG' },
        { data: 'savePercent', title: 'sv%', name: 'savePercent', group: 'categoryScoreG' }
    ];

    // Initialize new DataTable with calculated managerSummaryScores
    $('#managerSummary').DataTable({
        data: data,
        dom: 't',
        columns: managerSummaryColumns,
        order: [[1, "desc"]],
        pageLength: 11,
        autoWidth: false,
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

            const properties = managerSummaryColumns.filter(column => column.name !== 'manager').map(column => column.name);

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

            let header = `<tr></tr>`;
            if ($("#managerSummary thead tr").length === 1) {
                $("#managerSummary thead").prepend(header);
            }

            managerSummaryDataTable = $('#managerSummary').DataTable();

            layoutManagerSummaryTable();

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

// Function to extract height in inches from string
function extractHeightInInches(heightString) {
    const match = heightString.match(/(\d+)' *(\d+)"/);
    if (match) {
        const feet = parseInt(match[1], 10);
        const inches = parseInt(match[2], 10);
        // Convert everything to inches for comparison
        return (feet * 12) + inches;
    }
    return NaN; // Return NaN for invalid formats
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
            // categoryValues: {
            //     points: parseFloat(rowData[points_idx]),
            //     goals: parseFloat(rowData[goals_idx]),
            //     assists: parseFloat(rowData[assists_idx]),
            //     powerplayPoints: parseFloat(rowData[ppp_idx]),
            //     shotsOnGoal: parseFloat(rowData[sog_idx]),
            //     hits: parseFloat(rowData[hits_idx]),
            //     blockedShots: parseFloat(rowData[blk_idx]),
            //     takeaways: parseFloat(rowData[tk_idx]),
            //     penaltyMinutes: parseFloat(rowData[pim_idx]),
            //     wins: parseFloat(rowData[wins_idx]),
            //     saves: parseFloat(rowData[saves_idx]),
            //     goalsAgainst: parseFloat(rowData[goals_against_idx]),
            //     toiSec: parseFloat(rowData[toi_sec_idx]),
            //     shotsAgainst: parseFloat(rowData[shots_against_idx]),
            // }
        };

        allPlayers.push(player);

    }

    return allPlayers;

}

function getManagerAutoDraftScoreColumnIndexes() {

    // Iterate through managerSummaryScores
    // Include `fantrax_score_idx` if fantrax projections have been released; otherwise use only `z_score_idx` & `score_idx`
    // let draft_player_score_columns = [fantrax_score_idx, z_score_idx, score_idx];
    // let draft_player_score_columns = [z_score_idx, score_idx];
    // Jason thinks everyone used the fantrax projections
    let draft_player_score_columns = [[fantrax_score_idx, 'desc']];
    managerSummaryScores.forEach(function(managerSummary) {
        let autoDraftScoreColumnIndex;
        if (managerSummary.manager === 'Banshee') {
            autoDraftScoreColumnIndex = [z_score_idx, 'desc'];
        } else if (managerSummary.manager === "Fowler's Flyers") {
            // autoDraftScoreColumnIndex = score_idx;
            autoDraftScoreColumnIndex = [dobber_rank_idx, 'asc'];
        } else {
            // Randomly select an element from draft_player_score_columns
            let randomIndex = Math.floor(Math.random() * draft_player_score_columns.length);
            autoDraftScoreColumnIndex = draft_player_score_columns[randomIndex];
        }
        // Push the dictionary to the array
        managerAutoDraftScoreColumns.push({
            manager: managerSummary.manager,
            autoDraftScoreColumnIndex: autoDraftScoreColumnIndex
        });
    });

}

function getCategoryScarcity(availablePlayers) {

    let categoryScarcityByZScoreRange = calcCategoryScarcityByZScoreRange(availablePlayers);
    // updateCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);
    createCategoryScarcityByZScoreRangeTable(categoryScarcityByZScoreRange);

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
        categoryScarcities[key] = maxCategoryScarcity / categoryScarcities[key];
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
        // // Get all scores for the current category
        // const allZScores = managerSummaryScores.map(manager => manager[category]);
        // // Sort the scores in descending order
        // allZScores.sort((a, b) => b - a);
        // // Find the rank of mySummaryZScores[category] in allZScores
        // acc[category] = allZScores.indexOf(mySummaryZScores[category]);
        acc[category] = mySummaryZScores[category];
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

// function getTeamCategoryValuesAndZScores(teamPlayers) {

//     let teamCategoryValuesAndZScores = {};

//     // Sum the z-scores for each player on each team
//     teamPlayers.forEach(player => {
//         let manager = player.manager;
//         if (!teamCategoryValuesAndZScores[manager]) {
//             teamCategoryValuesAndZScores[manager] = {'values': {}, 'zScores': {}};
//         }
//         for (let category in player.categoryValues) {
//             if (!teamCategoryValuesAndZScores[manager]['values'][category]) {
//                 teamCategoryValuesAndZScores[manager]['values'][category] = 0;
//             }
//             if (!isNaN(player.categoryValues[category])) {
//                 if ((category !== 'points' && category !== 'toiSec') || (category === 'points' && player.position === 'D') || (category === 'toiSec' && player.position === 'G')) {
//                     teamCategoryValuesAndZScores[manager]['values'][category] += player.categoryValues[category];
//                 }
//             }
//         }
//         for (let category in player.categoryZScores) {
//             if (category !== 'gaa' && category !== 'savePercent') {
//                 if (!teamCategoryValuesAndZScores[manager]['zScores'][category]) {
//                     teamCategoryValuesAndZScores[manager]['zScores'][category] = 0;
//                 }
//                 if (!isNaN(player.categoryZScores[category])) {
//                     if (includePlayerCategoryZScore(player, category) === true || (category === 'toiSec' && player.position === 'G')) {
//                         teamCategoryValuesAndZScores[manager]['zScores'][category] += player.categoryZScores[category];
//                     }
//                 }
//             }
//         }

//     });

//     // need to calculate gaa & save %
//     for (let manager in teamCategoryValuesAndZScores) {
//         teamCategoryValuesAndZScores[manager]['values']['gaa'] = teamCategoryValuesAndZScores[manager]['values']['goalsAgainst'] / teamCategoryValuesAndZScores[manager]['values']['toiSec'] * 3600
//         teamCategoryValuesAndZScores[manager]['values']['savePercent'] = teamCategoryValuesAndZScores[manager]['values']['saves'] / teamCategoryValuesAndZScores[manager]['values']['shotsAgainst']

//         teamCategoryValuesAndZScores[manager]['zScores']['gaa'] = (mean_cat['gaa'] - teamCategoryValuesAndZScores[manager]['values']['gaa']) / std_cat['gaa']
//         teamCategoryValuesAndZScores[manager]['zScores']['savePercent'] = (teamCategoryValuesAndZScores[manager]['values']['savePercent'] - mean_cat['save%']) / std_cat['save%']
//     }

//     return teamCategoryValuesAndZScores;
// }

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
        $('#draftButtonsWrapper').removeClass('hidden').css('display', 'inline-block');
    }

    // $('#player_stats').DataTable().columns.adjust().draw();
    playerStatsDataTable.columns.adjust().draw();
    $('#player_stats-div').show();

}

function hideTablesShowPulsingBar() {

    if (gameType.value === 'Projected Season') {
        $('#draftButtonsWrapper').addClass('hidden').css('display', 'none');
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

function openDataTablesInNewTab(draftSimulationsAgg, draftSimulationsAggColumns, draftSimulationsManagerScoresAgg, draftSimulationsManagerScoresAggColumns) {
    const newTab = window.open();
    const draftSimulationsAggTableColumns = draftSimulationsAggColumns.map(col => ({ title: col, data: col }));
    const draftSimulationsManagerScoresAggTableColumns = draftSimulationsManagerScoresAggColumns.map(col => ({ title: col, data: col }));

    const htmlContent = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Draft Summaries</title>
            <link href="https://cdn.datatables.net/v/ju/jszip-3.10.1/dt-1.13.6/b-2.4.2/b-colvis-2.4.2/b-html5-2.4.2/date-1.5.1/fc-4.3.0/fh-3.4.0/sb-1.6.0/sp-2.2.0/sl-1.7.0/datatables.min.css" rel="stylesheet">
            <script type="text/javascript" src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script src="https://cdn.datatables.net/v/ju/jszip-3.10.1/dt-1.13.6/b-2.4.2/b-colvis-2.4.2/b-html5-2.4.2/date-1.5.1/fc-4.3.0/fh-3.4.0/sb-1.6.0/sp-2.2.0/sl-1.7.0/datatables.min.js"></script>
        </head>
        <body>
            <h1>Draft Simulations Manager Scores Aggregated</h1>
            <table id="draftSimulationsManagerScoresAggTable" class="display" style="width:100%"></table>
            <h1>Draft Simulations Aggregated</h1>
            <table id="draftSimulationsAggTable" class="display" style="width:100%"></table>
            <script>
                $(document).ready(function() {
                    $('#draftSimulationsManagerScoresAggTable').DataTable({
                        data: ${JSON.stringify(draftSimulationsManagerScoresAgg)},
                        columns: ${JSON.stringify(draftSimulationsManagerScoresAggTableColumns)},
                        order: [[2, "asc"]],
                        pageLength: 13,
                    });
                    $('#draftSimulationsAggTable').DataTable({
                        data: ${JSON.stringify(draftSimulationsAgg)},
                        columns: ${JSON.stringify(draftSimulationsAggTableColumns)},
                        order: [[4, "asc"]],
                        lengthMenu: [
                            [25, 50, 100, 250, 500, -1],
                            ['25 per page', '50 per page', '100 per page', '250 per page', '500 per page', 'All']
                        ],
                        pageLength: 25,
                    });
                });
            </script>
        </body>
        </html>
    `;

    newTab.document.write(htmlContent);
    newTab.document.close();

}

function layoutManagerSummaryTable() {

    let managerSummaryPositionsSelection = $('#ManagerSummaryPositions')[0].value;
    let rosterInfoCheckbox = $('#rosterInfoCheckbox')[0];

    let managerSummaryTable = $('#managerSummary').DataTable();
    let columns = managerSummaryColumns;
    let rosterInfoColumns = columns.filter(column => ['roster'].includes(column.group)).map(column => column.name);

    let visibleColumns = [];
    let hiddenColumns = [];
    let header = '';
    let managerScoreColspan2 = '<th colspan="2"></th>';
    let managerScoreColspan4 = '<th colspan="4"></th>';
    let rosterColspan7 = '<th colspan="7" style="background-color: cyan;">Roster</th>';
    let skatersColspan9 = '<th colspan="9" style="background-color: darkcyan;">Skaters</th>';
    let skatersColspan11 = '<th colspan="11" style="background-color: darkcyan;">Skaters</th>';
    let forwardsColspan11 = '<th colspan="11" style="background-color: darkcyan;">Forwards</th>';
    let defenseColspan11 = '<th colspan="11" style="background-color: darkcyan;">Defense</th>';
    let goaliesColspan4 = '<th colspan="4" style="background-color: lightgreen;">Goalies</th>';
    let goaliesColspan7 = '<th colspan="7" style="background-color: lightgreen;">Goalies</th>';

    // Change the sort column and order dynamically
    let sortColumnName = '';

    if (managerSummaryPositionsSelection === 'Sktr&G') {
        visibleColumns = columns.filter(column => ['all', 'compact', 'categoryScoreSktr', 'summaryScoreG', 'categoryScoreG'].includes(column.group)).map(column => column.name);
        hiddenColumns = columns.filter(column => ['summaryScoreSktr', 'summaryScoreF', 'categoryScoreF', 'summaryScoreD', 'categoryScoreD', 'summaryScoreG'].includes(column.group)).map(column => column.name);
        if (rosterInfoCheckbox.checked === true) {
            header = `${managerScoreColspan2}${rosterColspan7}${skatersColspan9}${goaliesColspan4}`;
        } else {
            header = `${managerScoreColspan2}${skatersColspan9}${goaliesColspan4}`;
        }
        sortColumnName = 'score';
    }
    else if (managerSummaryPositionsSelection === 'Sktr') {
        visibleColumns = columns.filter(column => ['all', 'summaryScoreSktr', 'categoryScoreSktr'].includes(column.group)).map(column => column.name);
        hiddenColumns = columns.filter(column => ['compact', 'summaryScoreF', 'categoryScoreF', 'summaryScoreD', 'categoryScoreD', 'summaryScoreG', 'categoryScoreG'].includes(column.group)).map(column => column.name);
        if (rosterInfoCheckbox.checked === true) {
            header = `${managerScoreColspan4}${rosterColspan7}${skatersColspan11}`;
        } else {
            header = `${managerScoreColspan4}${skatersColspan11}`;
        }
        sortColumnName = 'scoreSktr';
    }
    else if (managerSummaryPositionsSelection === 'F') {
        visibleColumns = columns.filter(column => ['all', 'summaryScoreF', 'categoryScoreF'].includes(column.group)).map(column => column.name);
        hiddenColumns = columns.filter(column => ['compact', 'summaryScoreSktr', 'categoryScoreSktr', 'summaryScoreD', 'categoryScoreD', 'summaryScoreG', 'categoryScoreG'].includes(column.group)).map(column => column.name);
        if (rosterInfoCheckbox.checked === true) {
            header = `${managerScoreColspan4}${rosterColspan7}${forwardsColspan11}`;
        } else {
            header = `${managerScoreColspan4}${forwardsColspan11}`;
        }
        sortColumnName = 'scoreF';
    }
    else if (managerSummaryPositionsSelection === 'D') {
        visibleColumns = columns.filter(column => ['all', 'summaryScoreD', 'categoryScoreD'].includes(column.group)).map(column => column.name);
        hiddenColumns = columns.filter(column => ['compact', 'summaryScoreSktr', 'categoryScoreSktr', 'summaryScoreF', 'categoryScoreF', 'summaryScoreG', 'categoryScoreG'].includes(column.group)).map(column => column.name);
        if (rosterInfoCheckbox.checked === true) {
            header = `${managerScoreColspan4}${rosterColspan7}${defenseColspan11}`;
        } else {
            header = `${managerScoreColspan4}${defenseColspan11}`;
        }
        sortColumnName = 'scoreD';
    }
    else if (managerSummaryPositionsSelection === 'G') {
        visibleColumns = columns.filter(column => ['all', 'summaryScoreG', 'categoryScoreG'].includes(column.group)).map(column => column.name);
        hiddenColumns = columns.filter(column => ['compact', 'summaryScoreSktr', 'categoryScoreSktr', 'summaryScoreF', 'categoryScoreF', 'summaryScoreD', 'categoryScoreD'].includes(column.group)).map(column => column.name);
        if (rosterInfoCheckbox.checked === true) {
            header = `${managerScoreColspan4}${rosterColspan7}${goaliesColspan7}`;
        } else {
            header = `${managerScoreColspan4}${goaliesColspan7}`;
        }
        sortColumnName = 'scoreG';
    }

    if (rosterInfoCheckbox.checked === true) {
        visibleColumns = [... visibleColumns, ...rosterInfoColumns]
    } else {
        hiddenColumns = [... hiddenColumns, ...rosterInfoColumns]
    }

    visibleColumns.forEach(function(name) {
        managerSummaryTable.columns(name + ':name').visible(true);
    });

    hiddenColumns.forEach(function(name) {
        managerSummaryTable.columns(name + ':name').visible(false);
    });

    $('#managerSummary thead tr:first-child').html(header);

    // Find the index of the column by its name
    let columnIdx = managerSummaryDataTable.column(sortColumnName + ':name').index();
    // Set the sorting order for the specified column
    managerSummaryDataTable.order([columnIdx, 'desc']);

    managerSummaryTable.columns.adjust().draw();

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

    managerAutoDraftScoreColumns = [];
    getManagerAutoDraftScoreColumnIndexes()

    // myCategoryNeeds = getMyCategoryNeeds()
    // updateMyCategoryNeedsTable(myCategoryNeeds);

    // document.getElementById("draftMessage").innerHTML = "Round: " + remaining_draft_picks[0].draft_round + "; Pick: " + remaining_draft_picks[0].round_pick + "; Overall: " + remaining_draft_picks[0].overall_pick + "; Manager: " + draft_manager + ' (' +  getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)';
    // $('#draftMessage').show();

    let draftBoardTable = $('#draftBoard').DataTable();
    draftBoardTable.destroy();
    createDraftBoardTable(remaining_draft_picks);

    // // Reset search panes
    // playerStatsDataTable.searchPanes.clearSelections();

    // managerSearchPaneDataTable.rows(function(idx, data, node) {
    //     return data.display.includes('No data');
    // }).select();

    // playerStatsDataTable.searchBuilder.rebuild(baseSearchBuilderCriteria);

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
    assists_score_idx = columns.findIndex(column => column.title === 'a score');
    adp_idx = columns.findIndex(column => column.title === 'prj adp');
    age_idx = columns.findIndex(function(column) { return column.title == 'age' });
    assists_idx = columns.findIndex(column => column.title === 'a');
    athletic_zscore_rank_idx = columns.findIndex(column => column.title === 'athletic z-score rank');
    bandaid_boy_idx = columns.findIndex(column => column.title === 'bandaid boy');
    blk_idx = columns.findIndex(column => column.title === 'blk');
    blk_score_idx = columns.findIndex(column => column.title === 'blk score');
    breakout_threshold_idx = columns.findIndex(column => column.title === 'bt');
    career_games_idx = columns.findIndex(column => column.title === 'career games');
    corsi_for_percent_idx = columns.findIndex(column => column.title === 'cf%');
    dobber_rank_idx = columns.findIndex(column => column.title === 'dobber rank');
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
    goals_score_idx = columns.findIndex(column => column.title === 'g score');
    gaa_idx = columns.findIndex(column => column.title === 'gaa');
    gaa_score_idx = columns.findIndex(column => column.title === 'gaa score');
    game_today_idx = columns.findIndex(column => column.title === 'game today');
    games_idx = columns.findIndex(column => column.title === 'gp');
    goalie_starts_idx = columns.findIndex(column => column.title === 'goalie starts');
    goals_against_idx = columns.findIndex(column => column.title === 'goals against');
    goals_idx = columns.findIndex(column => column.title === 'g');
    height_idx = columns.findIndex(column => column.title === 'height');
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
    pp_percent_ewm_idx = columns.findIndex(column => column.title === '%pp (ewm)');
    pp_points_p120_idx = columns.findIndex(column => column.title === 'pp pts/120');
    pp_unit_idx = columns.findIndex(column => column.title === 'pp unit');
    pp_unit_prj_idx = columns.findIndex(column => column.title === 'pp unit prj');
    ppp_idx = columns.findIndex(column => column.title === 'ppp');
    ppp_score_idx = columns.findIndex(column => column.title === 'ppp score');
    predraft_keeper_idx = columns.findIndex(column => column.title === 'pre-draft keeper');
    prj_draft_round_idx = columns.findIndex(column => column.title === 'prj draft round');
    points_score_idx = columns.findIndex(column => column.title === 'pts score');
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
    saves_score_idx = columns.findIndex(column => column.title === 'sv score');
    team_idx = columns.findIndex(column => column.title === 'team');
    three_yp_idx = columns.findIndex(column => column.title === '3yp');
    tier_idx = columns.findIndex(column => column.title === 'tier');
    tk_idx = columns.findIndex(column => column.title === 'tk');
    tk_score_idx = columns.findIndex(column => column.title === 'tk score');
    toi_even_pg_idx = columns.findIndex(column => column.title === 'toi even pg');
    toi_even_pg_ewm_idx = columns.findIndex(column => column.title === 'toi even pg (ewm)');
    toi_pp_pg_ewm_idx = columns.findIndex(column => column.title === 'toi pp pg (ewm)');
    toi_sh_pg_ewm_idx = columns.findIndex(column => column.title === 'toi sh pg (ewm)');
    toi_even_pg_trend_idx = columns.findIndex(column => column.title === 'toi even pg (trend)');
    toi_minutes_idx = columns.findIndex(column => column.title === 'toi (min)');
    toi_pg_idx = columns.findIndex(column => column.title === 'toi pg');
    toi_pg_ewm_idx = columns.findIndex(column => column.title === 'toi pg (ewm)');
    toi_pg_trend_idx = columns.findIndex(column => column.title === 'toi pg (trend)');
    toi_pp_percent_3gm_avg_idx = columns.findIndex(column => column.title === 'toi pp % (rolling avg)');
    toi_pp_percent_idx = columns.findIndex(column => column.title === 'toi pp %');
    toi_pp_pg_idx = columns.findIndex(column => column.title === 'toi pp pg');
    toi_pp_pg_trend_idx = columns.findIndex(column => column.title === 'toi pp pg (trend)');
    // toi_sec_idx = columns.findIndex(column => column.title === 'toi (sec)');
    toi_sh_pg_trend_idx = columns.findIndex(column => column.title === 'toi sh pg (trend)');
    upside_idx = columns.findIndex(column => column.title === 'upside');
    weight_idx = columns.findIndex(column => column.title === 'weight');
    wins_scoreidx = columns.findIndex(column => column.title === 'w score');
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

    sktr_category_score_heatmap_columns = new Set([points_score_idx, goals_score_idx, assists_score_idx, ppp_score_idx, sog_score_idx, tk_score_idx, hits_score_idx, blk_score_idx, pim_score_idx, penalties_score_idx]);
    goalie_category_score_heatmap_columns = new Set([wins_scoreidx, saves_score_idx, gaa_score_idx, save_percent_score_idx]);

    sktr_score_summary_heatmap_columns = new Set([score_idx, offense_score_idx, peripheral_score_idx, z_score_idx, z_offense_idx, z_peripheral_idx]);
    goalie_score_summary_heatmap_columns = new Set([score_idx, g_count_score_idx, g_ratio_score_idx, z_score_idx, z_g_count_idx, z_g_ratio_idx]);
    score_summary_heatmap_columns = new Set([...sktr_score_summary_heatmap_columns, ...goalie_score_summary_heatmap_columns]);

    sktr_time_heatmap_columns = new Set([toi_pg_idx, toi_pg_ewm_idx, toi_even_pg_ewm_idx, toi_pp_pg_ewm_idx, toi_sh_pg_ewm_idx]);

    sktr_percent_heatmap_columns = new Set([corsi_for_percent_idx, pp_percent_ewm_idx]);

    heatmap_columns = [...Array.from(score_summary_heatmap_columns), ...Array.from(sktr_category_heatmap_columns), ...Array.from(goalie_category_heatmap_columns), ...Array.from(sktr_category_z_score_heatmap_columns), ...Array.from(goalie_category_z_score_heatmap_columns), ...Array.from(sktr_category_score_heatmap_columns), ...Array.from(goalie_category_score_heatmap_columns), ...Array.from(sktr_time_heatmap_columns), ...Array.from(sktr_percent_heatmap_columns)]

    combo_columns = [z_combo_idx, z_offense_combo_idx, z_peripheral_combo_idx, z_g_count_combo_idx, z_g_ratio_combo_idx];

    categoryLookup = {
        [assists_idx]: 'assists',
        [assists_score_idx]: 'assists_score',
        [blk_idx]: 'blocked',
        [blk_score_idx]: 'blocked_score',
        [corsi_for_percent_idx]: 'corsi_for_%',
        [g_count_score_idx]: 'g_count',
        [g_ratio_score_idx]: 'g_ratio',
        [gaa_idx]: 'gaa',
        [gaa_score_idx]: 'gaa_score',
        [goals_idx]: 'goals',
        [goals_score_idx]: 'goals_score',
        [hits_idx]: 'hits',
        [hits_score_idx]: 'hits_score',
        [offense_score_idx]: 'offense',
        [penalties_idx]: 'penalties',
        [penalties_score_idx]: 'penalties_score',
        [peripheral_score_idx]: 'peripheral',
        [pim_idx]: 'pim',
        [pim_score_idx]: 'pim_score',
        [points_idx]: 'points',
        [points_score_idx]: 'points_score',
        [ppp_idx]: 'points_pp',
        [pp_percent_ewm_idx]: 'toi_pp_pg_ratio_ewm',
        [ppp_score_idx]: 'points_pp_score',
        [save_percent_score_idx]: 'save%_score',
        [saves_idx]: 'saves',
        [saves_percent_idx]: 'save%',
        [saves_score_idx]: 'saves_score',
        [score_idx]: 'score',
        [sog_idx]: 'shots',
        [sog_pp_idx]: 'shots_powerplay',
        [sog_score_idx]: 'shots_score',
        [tk_idx]: 'takeaways',
        [tk_score_idx]: 'takeaways_score',
        [toi_even_pg_ewm_idx]: 'toi_even_pg_ewm',
        [toi_pg_ewm_idx]: 'toi_pg_ewm',
        [toi_pg_idx]: 'toi_pg',
        [toi_pp_pg_ewm_idx]: 'toi_pp_pg_ewm',
        [toi_sh_pg_ewm_idx]: 'toi_sh_pg_ewm',
        [wins_idx]: 'wins',
        [wins_scoreidx]: 'wins_score',
        [z_assists_idx]: 'z_assists',
        [z_blk_idx]: 'z_blocked',
        [z_g_count_idx]: 'z_g_count',
        [z_g_ratio_idx]: 'z_g_ratio',
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

        // need to skip managers that have left the league
        while (completed_draft_picks.length > 0 && (last_pick.manager === 'Open Team 1' || last_pick.manager === 'Open Team 2')) {
            remaining_draft_picks.unshift(last_pick);
            last_pick = completed_draft_picks.pop();
        }

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

                playerStatsDataTable.draw();

                // add the last drafted player back to remaining_draft_picks array
                last_pick.drafted_player = '';
                remaining_draft_picks.unshift(last_pick);

                let round = last_pick.draft_round;  // The round number
                let pick = last_pick.round_pick;  // The pick number
                let tableData = $('#draftBoard').DataTable();

                // Filter the completed_draft_picks array to get the elements that match the criteria
                let filteredPicks = completed_draft_picks.filter(pick =>
                    pick.draft_round === round &&
                    (pick.manager === "Open Team 1" || pick.manager === "Open Team 2")
                );
                // Get the count of the filtered elements
                let skippedCells = filteredPicks.length;

                // Find the corresponding cell in tableData and update it
                let cell;
                if (round % 2 === 1) { // Check if round is odd
                    cell = tableData.cell((round - 1) * 2 + 1, (pick + skippedCells)); // Get the cell object for odd rounds
                } else { // round is even
                    cell = tableData.cell((round - 1) * 2 + 1, (14 - (pick + skippedCells))); // Get the cell object for even rounds
                }
                cell.data('');

                // remove background colour from cell
                $(cell.node()).css('background-color', '');
                // Redraw the table to ensure the changes take effect
                tableData.draw();

                managerSummaryScores = calcManagerSummaryScores();
                updateManagerSummaryTable(managerSummaryScores);

                // myCategoryNeeds = getMyCategoryNeeds()
                // updateMyCategoryNeedsTable(myCategoryNeeds);

                draft_manager = remaining_draft_picks[0].manager;
                managerSummaryData = managerSummaryDataTable.data().filter(row => row['manager']===draft_manager)[0];

                document.getElementById("draftMessage").innerHTML =
                    "Round: " + remaining_draft_picks[0].draft_round +
                    "; Pick: " + remaining_draft_picks[0].round_pick +
                    "; Overall: " + remaining_draft_picks[0].overall_pick +
                    "; Manager: " + draft_manager +
                    ' (' + getOrdinalString(remaining_draft_picks[0].managers_pick_number) + ' selection)' +
                    "<br>" +
                    "Currently has " + managerSummaryData.fCount +
                    " Fs; " + managerSummaryData.dCount +
                    " Ds; " + managerSummaryData.gCount +
                    " Gs";

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

    nameToIndex = {}
    playerStatsDataTable.rows().every(function() {
        let data = this.data();
        let match = data[name_idx].match(/>(.*?)</);
        let name = match ? match[1] : data[name_idx];
        let index = this.index();
        if (!nameToIndex[name]) {
            nameToIndex[name] = [];
        }
        nameToIndex[name].push(index);
    });

    // Redraw the table
    playerStatsDataTable.columns.adjust().draw();

}

function writeDraftBoardToDatabase(draftBoardDataDict, managerSummaryScoresDataDict, callback) {

    return new Promise((resolve, reject) => {

        // Set the base URL for the Flask API endpoint
        const baseUrl = 'http://localhost:5000/draft-board';

        const queryParams = `projectionSource=${projectionSource.value}&positionalScoring=${positionalScoringCheckbox.checked}&writeToDraftSimulationsTable=${writeToDraftSimulationsTable}&clearDraftSimulationsTable=${clearDraftSimulationsTable}&draft_board=${draftBoardDataDict}&managerSummaryScores=${managerSummaryScoresDataDict}`;

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

function writeDraftSummariesToDatabase() {

    return new Promise((resolve, reject) => {

        // Set the base URL for the Flask API endpoint
        const baseUrl = 'http://localhost:5000/draft-summaries';

        const queryParams = `draftProjectionSource=${draftProjectionSource.value}`;

        // Send a GET request to the Flask API endpoint with the specified query parameters
        $.get(baseUrl + '?' + queryParams, function(draft_summaries) {
            // Call the callback function with the draft order
            resolve(draft_summaries);
        })
        .fail(function(jqXHR, textStatus, errorThrown) {
            // Reject the promise with an error message
            reject(new Error("An error occurred while writing draft summaries to database: " + errorThrown));
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
                var text = e.html();
                if (text.includes(':')) {
                    var time = text.split(':');
                    var minutes = parseInt(time[0], 10);
                    var seconds = parseInt(time[1], 10);
                    return (minutes * 60) + seconds;
                } else {
                    var value = parseFloat(text);
                    if (isNaN(value) || !isFinite(value)) {
                        return 0;
                    } else {
                        return value;
                    }
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
