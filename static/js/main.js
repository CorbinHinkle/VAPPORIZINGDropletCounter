// ============================================================
// DROPLET COUNTER WEB APPLICATION
// FRONTEND JAVASCRIPT
// ============================================================


// ============================================================
// GET PAGE ELEMENTS
// ============================================================

const analysisForm = document.getElementById("analysisForm");

const imageInput = document.getElementById("images");

const micronPerPixelInput =
    document.getElementById("micron_per_pixel");

const minDiameterInput =
    document.getElementById("min_diam");

const maxDiameterInput =
    document.getElementById("max_diam");

const runButton =
    document.getElementById("runButton");

const loadingSection =
    document.getElementById("loading");

const loadingText =
    document.getElementById("loadingText");

const resultsSection =
    document.getElementById("results");

const errorBox =
    document.getElementById("errorBox");

const errorMessage =
    document.getElementById("errorMessage");

const fileInfo =
    document.getElementById("fileInfo");

const selectedFileCount =
    document.getElementById("selectedFileCount");


// ============================================================
// RESULT ELEMENTS
// ============================================================

const imagesProcessed =
    document.getElementById("imagesProcessed");

const dropletsDetected =
    document.getElementById("dropletsDetected");

const minimumDiameter =
    document.getElementById("minimumDiameter");

const maximumDiameter =
    document.getElementById("maximumDiameter");

const meanDiameter =
    document.getElementById("meanDiameter");

const totalArea =
    document.getElementById("totalArea");


// ============================================================
// DOWNLOAD ELEMENTS
// ============================================================

const downloadsSection =
    document.getElementById("downloadsSection");

const csvDownload =
    document.getElementById("csvDownload");

const countGraphDownload =
    document.getElementById("countGraphDownload");

const areaGraphDownload =
    document.getElementById("areaGraphDownload");

const teflonGraphDownload =
    document.getElementById("teflonGraphDownload");


// ============================================================
// GRAPH ELEMENTS
// ============================================================

const graphsSection =
    document.getElementById("graphsSection");

const countGraph =
    document.getElementById("countGraph");

const areaGraph =
    document.getElementById("areaGraph");

const teflonGraph =
    document.getElementById("teflonGraph");

const countGraphContainer =
    document.getElementById("countGraphContainer");

const areaGraphContainer =
    document.getElementById("areaGraphContainer");

const teflonGraphContainer =
    document.getElementById("teflonGraphContainer");


// ============================================================
// FILE SELECTION
// ============================================================

imageInput.addEventListener("change", function () {

    const fileCount = imageInput.files.length;


    if (fileCount > 0) {

        selectedFileCount.textContent = fileCount;

        fileInfo.classList.remove("hidden");

    } else {

        selectedFileCount.textContent = "0";

        fileInfo.classList.add("hidden");

    }

});


// ============================================================
// FORM SUBMISSION
// ============================================================

analysisForm.addEventListener("submit", async function (event) {

    // Prevent normal HTML form submission
    event.preventDefault();


    // --------------------------------------------------------
    // RESET PAGE STATE
    // --------------------------------------------------------

    hideError();

    resultsSection.classList.add("hidden");

    graphsSection.classList.add("hidden");

    downloadsSection.classList.add("hidden");


    // --------------------------------------------------------
    // VALIDATE FILES
    // --------------------------------------------------------

    if (imageInput.files.length === 0) {

        showError(
            "Please select at least one image."
        );

        return;

    }


    // --------------------------------------------------------
    // VALIDATE NUMERICAL INPUTS
    // --------------------------------------------------------

    const micronPerPixel =
        parseFloat(micronPerPixelInput.value);

    const minDiameter =
        parseFloat(minDiameterInput.value);

    const maxDiameter =
        parseFloat(maxDiameterInput.value);


    if (
        isNaN(micronPerPixel) ||
        micronPerPixel <= 0
    ) {

        showError(
            "Microns per pixel must be greater than zero."
        );

        return;

    }


    if (
        isNaN(minDiameter) ||
        minDiameter < 0
    ) {

        showError(
            "Minimum diameter must be zero or greater."
        );

        return;

    }


    if (
        isNaN(maxDiameter) ||
        maxDiameter <= minDiameter
    ) {

        showError(
            "Maximum diameter must be greater than the minimum diameter."
        );

        return;

    }


    // --------------------------------------------------------
    // SHOW LOADING STATE
    // --------------------------------------------------------

    loadingSection.classList.remove("hidden");

    loadingText.textContent =
        `Uploading ${imageInput.files.length} image(s) and running analysis...`;


    runButton.disabled = true;

    runButton.textContent =
        "Processing...";


    // --------------------------------------------------------
    // CREATE FORMDATA
    // --------------------------------------------------------

    const formData = new FormData();


    // Add all selected image files
    for (const file of imageInput.files) {

        formData.append(
            "images",
            file
        );

    }


    // Add numerical analysis parameters

    formData.append(
        "micron_per_pixel",
        micronPerPixel
    );


    formData.append(
        "min_diam",
        minDiameter
    );


    formData.append(
        "max_diam",
        maxDiameter
    );


    // --------------------------------------------------------
    // SEND REQUEST TO FLASK
    // --------------------------------------------------------

    try {

        const response =
            await fetch("/analyze", {

                method: "POST",

                body: formData

            });


        // ----------------------------------------------------
        // READ RESPONSE SAFELY
        // ----------------------------------------------------

        const responseText =
            await response.text();


        let data;


        try {

            data = JSON.parse(responseText);

        }

        catch (jsonError) {

            console.error(
                "Server returned non-JSON response:"
            );

            console.error(responseText);


            throw new Error(
                "The server returned an invalid response. " +
                "Check the Flask terminal for errors."
            );

        }


        // ----------------------------------------------------
        // CHECK HTTP STATUS
        // ----------------------------------------------------

        if (!response.ok) {

            throw new Error(
                data.error ||
                data.message ||
                "Analysis failed."
            );

        }


        // ----------------------------------------------------
        // CHECK APPLICATION ERROR
        // ----------------------------------------------------

        if (data.error) {

            throw new Error(
                data.error
            );

        }


        // ----------------------------------------------------
        // DISPLAY RESULTS
        // ----------------------------------------------------

        displayResults(data);


    }


    // --------------------------------------------------------
    // HANDLE ERRORS
    // --------------------------------------------------------

    catch (error) {

        console.error(
            "Analysis error:",
            error
        );


        showError(
            error.message ||
            "An unknown error occurred during analysis."
        );

    }


    // --------------------------------------------------------
    // RESTORE BUTTON
    // --------------------------------------------------------

    finally {

        loadingSection.classList.add("hidden");

        runButton.disabled = false;

        runButton.textContent =
            "Run Analysis";

    }

});


// ============================================================
// DISPLAY RESULTS
// ============================================================

function displayResults(data) {


    console.log(
        "Analysis response:",
        data
    );


    // --------------------------------------------------------
    // BASIC RESULTS
    // --------------------------------------------------------

    imagesProcessed.textContent =
        data.image_count ??
        data.images_processed ??
        "--";


    dropletsDetected.textContent =
        data.droplet_count ??
        data.droplets_detected ??
        "--";


    // --------------------------------------------------------
    // DIAMETER RESULTS
    // --------------------------------------------------------

    if (
        data.min_diameter !== undefined &&
        data.min_diameter !== null
    ) {

        minimumDiameter.textContent =
            Number(data.min_diameter).toFixed(3) +
            " µm";

    }

    else {

        minimumDiameter.textContent =
            "-- µm";

    }


    if (
        data.max_diameter !== undefined &&
        data.max_diameter !== null
    ) {

        maximumDiameter.textContent =
            Number(data.max_diameter).toFixed(3) +
            " µm";

    }

    else {

        maximumDiameter.textContent =
            "-- µm";

    }


    if (
        data.mean_diameter !== undefined &&
        data.mean_diameter !== null
    ) {

        meanDiameter.textContent =
            Number(data.mean_diameter).toFixed(3) +
            " µm";

    }

    else {

        meanDiameter.textContent =
            "-- µm";

    }


    // --------------------------------------------------------
    // TOTAL AREA
    // --------------------------------------------------------

    if (
        data.total_area_mm2 !== undefined &&
        data.total_area_mm2 !== null
    ) {

        totalArea.textContent =
            Number(data.total_area_mm2).toFixed(6) +
            " mm²";

    }

    else {

        totalArea.textContent =
            "-- mm²";

    }


    // --------------------------------------------------------
    // CSV DOWNLOAD
    // --------------------------------------------------------

    let hasDownloads = false;


    if (data.csv_url) {

        csvDownload.href =
            data.csv_url;

        csvDownload.classList.remove("hidden");

        hasDownloads = true;

    }

    else {

        csvDownload.classList.add("hidden");

    }


    // --------------------------------------------------------
    // COUNT GRAPH
    // --------------------------------------------------------

    if (data.count_graph_url) {

        countGraph.src =
            data.count_graph_url +
            "?t=" +
            Date.now();


        countGraphDownload.href =
            data.count_graph_url;


        countGraphContainer.classList.remove("hidden");

        countGraphDownload.classList.remove("hidden");

        hasDownloads = true;

    }

    else {

        countGraphContainer.classList.add("hidden");

        countGraphDownload.classList.add("hidden");

    }


    // --------------------------------------------------------
    // AREA GRAPH
    // --------------------------------------------------------

    if (data.area_graph_url) {

        areaGraph.src =
            data.area_graph_url +
            "?t=" +
            Date.now();


        areaGraphDownload.href =
            data.area_graph_url;


        areaGraphContainer.classList.remove("hidden");

        areaGraphDownload.classList.remove("hidden");

        hasDownloads = true;

    }

    else {

        areaGraphContainer.classList.add("hidden");

        areaGraphDownload.classList.add("hidden");

    }


    // --------------------------------------------------------
    // TEFLON GRAPH
    // --------------------------------------------------------

    if (data.teflon_graph_url) {

        teflonGraph.src =
            data.teflon_graph_url +
            "?t=" +
            Date.now();


        teflonGraphDownload.href =
            data.teflon_graph_url;


        teflonGraphContainer.classList.remove("hidden");

        teflonGraphDownload.classList.remove("hidden");

        hasDownloads = true;

    }

    else {

        teflonGraphContainer.classList.add("hidden");

        teflonGraphDownload.classList.add("hidden");

    }


    // --------------------------------------------------------
    // SHOW/HIDE DOWNLOAD SECTION
    // --------------------------------------------------------

    if (hasDownloads) {

        downloadsSection.classList.remove("hidden");

    }

    else {

        downloadsSection.classList.add("hidden");

    }


    // --------------------------------------------------------
    // SHOW GRAPH SECTION
    // --------------------------------------------------------

    const hasGraphs =

        data.count_graph_url ||
        data.area_graph_url ||
        data.teflon_graph_url;


    if (hasGraphs) {

        graphsSection.classList.remove("hidden");

    }

    else {

        graphsSection.classList.add("hidden");

    }


    // --------------------------------------------------------
    // SHOW RESULTS
    // --------------------------------------------------------

    resultsSection.classList.remove("hidden");


    // Scroll to results

    resultsSection.scrollIntoView({

        behavior: "smooth",

        block: "start"

    });

}


// ============================================================
// SHOW ERROR
// ============================================================

function showError(message) {

    errorMessage.textContent =
        message;


    errorBox.classList.remove("hidden");


    errorBox.scrollIntoView({

        behavior: "smooth",

        block: "center"

    });

}


// ============================================================
// HIDE ERROR
// ============================================================

function hideError() {

    errorBox.classList.add("hidden");

    errorMessage.textContent = "";

}