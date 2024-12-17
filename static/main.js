import { $ } from "/static/jquery/src/jquery.js";

function say_hi(elt) {
    console.log("Welcome to", elt.text());
}

say_hi($("h1"));

function make_table_sortable($table) {
    let $headerCells = $table.find("thead th.sort-column");

    // Click Event
    $headerCells.on("click", (event) => {
        let $headerCell = $(event.currentTarget);
        let columnIndex = $headerCell.index();

        // check which state it is in
        let isAscending = $headerCell.hasClass("sort-asc");
        let isDescending = $headerCell.hasClass("sort-desc");

        // remove either of these now
        $headerCells.removeClass("sort-asc sort-desc");

        // add the new one
        let sortAscending = false
        let restoreOriginal = false;

        // original  ->  ascending
        if (!isAscending && !isDescending) {
            sortAscending = true

        // ascending  ->  descending
        } else if (isAscending) {
            sortAscending = false

        // descending  ->  original
        } else if (!isAscending) {
            restoreOriginal = true;
        }

        // make the switch
        if (restoreOriginal) {
            $headerCell.removeClass("sort-asc sort-desc").attr("aria-sort", "none");
        } else if (sortAscending) {
            $headerCell.addClass("sort-asc").attr("aria-sort", "ascending");
        } else {
            $headerCell.addClass("sort-desc").attr("aria-sort", "descending");
        }

        // get the rows
        let $rows = $table.find("tbody tr");
        let sortedRows;

        // sort in the original order
        if (restoreOriginal) {
            sortedRows = $rows.toArray().sort((rowA, rowB) => {
                let indexA = $(rowA).data("index");
                let indexB = $(rowB).data("index");

                return indexA - indexB;
            });

        // sort in an ascending/descending order
        } else {
            sortedRows = $rows.toArray().sort((rowA, rowB) => {
                let cellA = parseFloat($(rowA).children().eq(columnIndex).data("value")) || -1;
                let cellB = parseFloat($(rowB).children().eq(columnIndex).data("value")) || -1;

                if (sortAscending) {
                    return cellB - cellA; // Ascending order
                } else {
                    return cellA - cellB; // Descending order
                }
            });
        }

        // append the rows
        $table.find("tbody").empty().append(sortedRows);
    })
}

// call the table sorting function
$(".sortable").toArray().forEach((element)  => {
    let $table = $(element);
    make_table_sortable($table);
});


function make_form_async($form) {
    $form.on("submit", (event) => {
        event.preventDefault();

        // get the form data
        let formData = new FormData(event.currentTarget);
        let mimeType = $form.attr("enctype");

        // disable the form inputs
        let $fileInput = $form.find('input[type="file"]');
        let $submitButton = $form.find('button[type="submit"]');
        $fileInput.prop('disabled', true);
        $submitButton.prop('disabled', true);

        $.ajax({
            url: $form.attr('action'),
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            mimeType: mimeType,
            success: function () {
                $form.replaceWith("<p>Upload succeeded</p>");
            },
            error: function () {
                console.log("An error occurred while submitting the assignment");
                $fileInput.prop("disabled", false);
                $submitButton.prop("disabled", false);
            }
        })
    })
}

let $form = $(".async");
if ($form.length > 0) {
    make_form_async($form);
}



function make_grade_hypothesized($table) {

    // insert the hypothesize button
    let $button = $('<button>Hypothesize</button>');
    $table.before($button);

    $button.on("click", function () {

        // actual grades
        if ($table.hasClass("hypothesized")) {

            //adjust button
            $table.removeClass("hypothesized");
            $button.text("Hypothesize");

            // restore original values
            $table.find("td.hypothetical").toArray().forEach((element)  => {
                let $cell = $(element);
                let originalText = $cell.data("value");
                $cell.removeClass("hypothetical");
                $cell.text(originalText);
            });

        // hypothesized grades
        } else {

            // adjust button
            $table.addClass("hypothesized");
            $button.text("Actual grades");

            // replace with input fields
            $table.find("td").toArray().forEach((element)  => {
                let $cell = $(element);
                let text = $cell.data("value");

                if (text === "Not due" || text === "Pending") {
                    $cell.addClass("hypothetical")
                    $cell.html('<input type="number" min="0" max="100" class="hypothetical">');
                }
            });
        }

        // recalculate upon state switch
        recalculate_grade($table);
    });

    // recalculate any time a value is entered
    $table.on("keyup", ".hypothetical", function () {
        recalculate_grade($table);
    });
}

function recalculate_grade($table) {
    let totalWeight = 0;
    let weightedScore = 0;

    // get all the rows
    $table.find("tbody tr").toArray().forEach((element)  => {
        // get the data
        let $row = $(element);
        let $gradeCell = $row.find("td:last-child");
        let $input = $gradeCell.find(".hypothetical");
        let weight = parseFloat($gradeCell.data("weight"));

        // check for a valid weight
        if (!weight || isNaN(weight)) return;

        // if value has been entered
        if ($input.length > 0) {
            let inputValue = parseFloat($input.val());
            if (!isNaN(inputValue)) {
                weightedScore += (inputValue / 100) * weight;
                totalWeight += weight;
            }

        // non value cases
        } else {
            let cellValue = $gradeCell.data("value");

            // missing - counts as zero
            if (cellValue === "Missing") {
                weightedScore += 0; // Treat Missing as 0
                totalWeight += weight;

            // graded values - counts toward grade
            // ungraded or not due will be caught with the isNaN check and not be counted
            } else {
                let numericGrade = parseFloat(cellValue);
                if (!isNaN(numericGrade)) {
                    weightedScore += (numericGrade / 100) * weight;
                    totalWeight += weight;
                }
            }
        }
    });

    // update the grade
    let finalGrade = "N/A"
    if (totalWeight > 0) {
        finalGrade = ((weightedScore / totalWeight) * 100).toFixed(2);
    }
    $table.find("tfoot .numberColumn").text(`${finalGrade}%`);
}

let $profileTable = $(".studentGrades");
make_grade_hypothesized($profileTable);
