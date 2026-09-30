var now = new Date();
var current_page = 1;
var total_pages = 20;
var page_size = 20;
const defaults = {
    search_string: "",
    order_by: "newer",
    year: "",
    state: "",
    classification: "",
    category: "",
    current_page: 1,
    only_free: false,
    min_price: "",
    max_price: ""
};
var filters = { ...defaults }
var $pagination = $('#pagination-explorer');

var defaultOpts = {
    totalPages: total_pages,
    first: '<<',
    prev: '<',
    next: '>',
    last: '>>',
    visiblePages: 5
}
let list_years = []
let list_organizations = []
let list_categories = []
let startYear = 2020
let date_future_horizon = 262080

function reloadPage(){
    window.location.href = window.location.origin + window.location.pathname;
}

function countFilters(){
    var initial_filter = 0;
    var price_filter = 0
    for (const key in defaults) {
        if (key === "order_by"){
            continue;

        }else if (filters[key] != defaults[key]) {
            if (key === "only_free"){
                initial_filter++;
                price_filter++;
            }else  if (key === "min_price"){
                initial_filter++;
                price_filter++;
            }else if (key === "max_price"){
                initial_filter++;
                price_filter++;
            }else{
                let filter_name = `#${key}-filter`;
                $(`.filter-bar ${filter_name}`).show();
                $(`.filter-bar ${filter_name}`).text('1');
                initial_filter++;
            }
        }else{
            let filter_name = `#${key}-filter`;
            $(`.filter-bar ${filter_name}`).hide();
        }
    }
    if(price_filter > 0){
        $(`.filter-bar #price-filter`).show();
        $(`.filter-bar #price-filter`).text(price_filter);
    }else{
        $(`.filter-bar #price-filter`).hide();
    }
    return initial_filter
}
function createCheckboxOptions(container, object, facet) {
    const label = $('<label>')
        .addClass('list-group-item d-flex')
        .appendTo(container);

    $('<input>')
        .addClass('form-check-input me-1')
        .attr({
            type: 'checkbox',
            'data-facet': facet,
            'value':'',
            'data-value': object.id,
            'data-text': object.name
        })
        .appendTo(label);

    $('<span>').addClass('d-inline').text(object.name).appendTo(label);
}

function loadYears(){
    const today = new Date();
    const futureDate = new Date(today.getTime() + date_future_horizon * 60 * 1000);
    const endYear = futureDate.getFullYear();
    const years = Array.from({ length: endYear - startYear + 1 }, (_, i) => {
        const year = startYear + i;
        return { id: year, name: year.toString() };
    });
    const container = $("#years");
    container.empty();
    years.forEach(
        function(year) {
            list_years.push(String(year.id));
            createCheckboxOptions(container, year, 'year');
    });
}

async function loadInitialSettings() {
    return $.get("/course_classification/get_initial_settings")
        .done(function(data) {
            startYear = data.initial_year
            date_future_horizon = data.time_horizon
        })
        .fail(function() {
            console.error(gettext('ERROR loading initial settings'));
            emptyCoursesData(gettext('ERROR loading initial settings'));
            hideLoading();
        });
}

async function loadOrganizations() {
    return $.get("/course_classification/get_main_classifications")
        .done(function(data) {
            const container = $("#organizations");
            container.empty();
            data.forEach(
                function(classification) {
                    list_organizations.push(String(classification.id));
                    createCheckboxOptions(container, classification, 'classification')
            });
        })
        .fail(function() {
            console.error(gettext('ERROR loading organizations'));
            emptyCoursesData(gettext('ERROR loading organizations'));
            hideLoading();
        });
}

async function loadCategories() {
    return $.get("/course_classification/get_course_categories")
        .done(function(data) {
            const container = $("#categories");
            container.empty();
            data.forEach(
                function(category) {
                    list_categories.push(String(category.id));
                    createCheckboxOptions(container, category, 'category')
            });
        })
        .fail(function() {
            console.error(gettext('ERROR loading categories'));
            emptyCoursesData(gettext('ERROR loading categories'));
            hideLoading();
        });
}

function hideLoading(){
        $("#loadingCircles").hide();
        $("#list-courses").show();
}

function show_total_filters(){
    if(countFilters() > 0){
        $(".filter-bar #total-filter").text("(" + countFilters() + ")")
    }else{
        $(".filter-bar #total-filter").text("")
    }
}

function readQueryParams(){
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    // get different types of url params
    if (urlParams.has('search_string')){
        filters["search_string"]=urlParams.get('search_string')
        $("#discovery-input").val(urlParams.get('search_string'))
    }
    if (urlParams.has('order')){
        if(['older','newer'].includes(urlParams.get('order'))){
            filters["order"]=urlParams.get('order')
            $(`input[type="radio"][data-facet="order_by"][data-value="${urlParams.get('order')}"]`).prop('checked', true);
            $("#order-select").val(urlParams.get('order'))
        }else{
            reloadPage();
        }
    }else{
        $(`input[type="radio"][data-facet="order_by"][data-value="newer"]`).prop('checked', true);
    }
    if (urlParams.has('year')){
        if(list_years.includes(urlParams.get('year'))){
            filters["year"]=urlParams.get('year')
            $(`input[type="checkbox"][data-facet="year"][data-value="${urlParams.get('year')}"]`).prop('checked', true);
        }else{
            reloadPage();
        }
    }
    if (urlParams.has('state')){
        if(['active','finished','coming_soon'].includes(urlParams.get('state'))){
            filters["state"]=urlParams.get('state')
            $(`input[type="checkbox"][data-facet="state"][data-value="${urlParams.get('state')}"]`).prop('checked', true);
        }else{
            reloadPage();
        }
    }
    if (urlParams.has('organization')){
        if(list_organizations.includes(urlParams.get('organization'))){
            const selectedOrganization = urlParams.get('organization');
            filters["classification"] = selectedOrganization;
            $(`input[type="checkbox"][data-facet="classification"][data-value="${selectedOrganization}"]`).prop('checked', true);
        }else{
            reloadPage();
        }
    }
    if (urlParams.has('category')){
        if(list_categories.includes(urlParams.get('category'))){
            const selectedCategory = urlParams.get('category');
            filters["category"] = selectedCategory;
            $(`input[type="checkbox"][data-facet="category"][data-value="${selectedCategory}"]`).prop('checked', true);
        }else{
            reloadPage();
        }
    }
    if (urlParams.has('page')){
        if(Number.isInteger(Number(urlParams.get('page'))) && Number(urlParams.get('page')) > 0){
            filters["current_page"] = Number(urlParams.get('page'));
            current_page = Number(urlParams.get('page')); 
        }else{
            reloadPage();
        }
    }
}

$(document).ready( function() {
    (async function () {

        await loadOrganizations();
        await loadCategories();
        await loadInitialSettings();
        loadYears();
        $(`input[type="radio"]`).prop('checked', false);
        $(`input[type="checkbox"]`).prop('checked', false);
        readQueryParams();
        initDiscovery();
        show_total_filters();
    })();
});

$('#freeCourses').on('change', function() {
    if ($(this).is(':checked')) {
        $('#min-input').prop('disabled', true);
        $('#max-input').prop('disabled', true);
        $('.range-slider').css('cursor', 'not-allowed');
        $('.range-slider').css('opacity', '50%');
        $('.slider-handle.handle-min').css('pointer-events', 'none');
        $('.slider-handle.handle-max').css('pointer-events', 'none');
        $('#min-input').val(undefined);
        $('#max-input').val(undefined);
        filters["only_free"] = true;
        filters["current_page"] = 1;
    } else {
        $('#min-input').prop('disabled', false);
        $('#max-input').prop('disabled', false);
        $('.range-slider').css('cursor', 'inherit');
        $('.range-slider').css('opacity', '100%');
        $('.slider-handle.handle-min').css('pointer-events', 'inherit');
        $('.slider-handle.handle-max').css('pointer-events', 'inherit');
        filters["only_free"] = false;
        filters["current_page"] = 1;
    }
    current_page = 1;
    filters["max_price"] = $('#max-input').val();
    filters["min_price"] = $('#min-input').val();
    show_total_filters();
});

function initDiscovery(){
    getData().then(function() {
        createPagination();
    });
}

function addUrlParams(){
    const url = new URL(window.location);
    url.searchParams.set('page', current_page);
    window.history.replaceState({}, '', url);
}

function createPagination(){
    var $pagination = $('#pagination-explorer');
    $pagination.twbsPagination('destroy');
    if (total_pages !== 0 && current_page <= total_pages){
        $pagination.twbsPagination($.extend({}, defaultOpts, {
        startPage: current_page,
        totalPages: total_pages,
        initiateStartPageClick:false,
        onPageClick: function (event, page) {
            filters["current_page"] = page
            current_page = page;
            addUrlParams();
            cleanCourses();
            getData();
        }
        }));
    }
}
function emptyCoursesData(message){
    const container = document.getElementById("list-courses");
    const courseHtml = edx.HtmlUtils.HTML( '<div class="text-center font-italic" id="empty-courses-message"><p>'+message+'.</p><img id="empty-courses-image" src="'+window.themeAsset('images/empty_courses.svg')+'"></div>')
    row = document.createElement('div');
    row.className = 'row d-flex justify-content-center';
    container.appendChild(row);
    edx.HtmlUtils.append(row, courseHtml);
}
function getData(){
    $("#loadingCircles").show();
    $("#list-courses").hide();
    return $.post( "/course_classification/search/", filters )
    .done(function( data ) {
        if (data.results.length == 0){
            emptyCoursesData(gettext("No results were found for your search"));
        }
        const container = document.getElementById("list-courses");
        if (data.results.length != 1){
            for (let i = 0; i < data.results.length -1; i += 2) {
                const courseHtml = createCourse(data.results[i], data.results[i].extra_data);
                const courseHtml2 = createCourse(data.results[i+1], data.results[i+1].extra_data);
                row = document.createElement('div');
                row.className = 'row d-flex justify-content-center w-100';
                container.appendChild(row);
                edx.HtmlUtils.append(row, courseHtml);
                edx.HtmlUtils.append(row, courseHtml2);
            }
        }
        if (data.results.length % 2 !== 0){
            const courseHtml = createCourse(data.results[data.results.length - 1], data.results[data.results.length - 1].extra_data);
            const courseHtml2 = edx.HtmlUtils.HTML('<div class="col-xl-4 col-lg-10 col-md-12 col-sm-12 mb-3 mx-3 p-2"></div>')
            row = document.createElement('div');
            row.className = 'row d-flex justify-content-center w-100';
            container.appendChild(row);
            edx.HtmlUtils.append(row, courseHtml);
            edx.HtmlUtils.append(row, courseHtml2);
        }
        hideLoading();

        if(data.results.length > 0){
            $(".filter-bar #discovery-message").text(gettext("Showing") + " " + (data.page_size*(current_page-1)+1)+'-'+ (data.page_size*(current_page-1)+data.results.length)  + " " + gettext("out of") + " " + data.total + " " + gettext("courses") );
        }else{
            $(".filter-bar #discovery-message").text(gettext("Showing 0 courses"));
        }
        page_size = data.page_size;
        total_pages = Math.ceil(data.total/page_size);
        if(current_page > total_pages && total_pages != 0){
            reloadPage();
        }
    }).fail(function(xhr, status, error) {
       emptyCoursesData(gettext("No results were found for your search"));
        console.error("ERROR:" + xhr.responseText)
        hideLoading();
    })
}

$(document).on('click', '#advance-button', function(e) {
    const $div_filter = $('#filter-bar');
    const $div_courses = $('#section-courses');

    if ($div_filter.css('display') === 'none' || $div_filter.css('display') === '') {
        $div_filter.css('display', 'block');
        $div_filter.addClass("col-xl-3");
        $div_courses.removeClass("col-xl-12");
        $div_courses.addClass("col-xl-9");
    } else {
        $div_filter.css('display', 'none');
        $div_filter.removeClass("col-xl-3");
        $div_courses.removeClass("col-xl-9");
        $div_courses.addClass("col-xl-12");
    }
});

$(document).on('change', '[data-facet="category"], [data-facet="classification"], [data-facet="year"], [data-facet="state"], [data-facet="order_by"]', function() {
    let facet = $(this).data("facet");
    if (this.checked){
        filters[facet] = $(this).data("value");
        $('.filter-bar .search-facets-lists input[data-facet="'+facet+'"]').not(this).prop( "checked", false );
        if (facet =="order_by"){
            $("#order-select").val($(this).data("value"))
        }
    }
    else{
        filters[facet] = "";
    }
    filters["current_page"] = 1;
    current_page = 1;
    show_total_filters();
});

$(document).on('change', '[id="min-input"], [id="max-input"]', function() {
    filters["min_price"] = $('#min-input').val();
    filters["max_price"] = $('#max-input').val();
    filters["current_page"] = 1;
    current_page = 1;
    show_total_filters();
});

$('#order-select').on('change', function(e) {
    e.preventDefault();
    let facet = $(this).data("facet");
    filters[facet] = gettext($(this)[0].value);
    filters["current_page"] = 1;
    current_page = 1;
    $(`input[type="radio"][data-facet="order_by"]`).prop('checked', false);
    $(`input[type="radio"][data-facet="order_by"][data-value="${gettext($(this)[0].value)}"]`).prop('checked', true);
    show_total_filters();
});

function clearFilter(){
     filters = { ...defaults };
    $("#order-select").val('newer')
    $(`input[type="radio"][data-facet="order_by"][data-value="newer"]`).prop('checked', true);
    $("#discovery-input").val("")
    $("#min-input").val("")
    $("#max-input").val("")
    show_total_filters();
}

$('.filter-bar #clear-filters').live('click', function(e) {
    e.preventDefault();
    $('.filter-bar #filter-bar').css("display", "none");
    $(".filter-bar #active-filters").html('');
    $('.filter-bar .search-facets-lists input').prop( "checked", false );
    clearFilter();
    cleanCourses();
    getCourses();
});

$('.filter-bar #apply-filters').live('click', function(e) {
    e.preventDefault();
    $('.filter-bar #filter-bar').css("display", "none");
    cleanCourses();
    getCourses();
});

$('.order-by-btn').live('click', function(e) {
    e.preventDefault();
    let value = $(this).data("value");
    $(`input[type="checkbox"][data-facet="order_by"][data-value="${value}"]`).prop('checked', true);
});
$('.filter-bar #filter-bar #active-filters span.fa-times').live('click', function(e) {
    e.preventDefault();
    let btnType = this.parentElement.dataset.type;
    $(this.parentElement).remove();
    if ( $('.filter-bar #active-filters').children().length == 0 ) $('.filter-bar #filter-bar').css("display", "none");
    filters[btnType] = "";
    $('.filter-bar .search-facets-lists input[data-facet="'+btnType+'"]').not(this).prop( "checked", false );
});

$(document).on('click', '#discovery-submit', function(e) {
    e.preventDefault();
    filters["search_string"] = $("#discovery-input").val();
    getCourses();
});

$('#discovery-input').keypress(function(event){
    var keycode = (event.keyCode ? event.keyCode : event.which);
    if(keycode == '13'){
        filters["search_string"] = $("#discovery-input").val();
        getCourses();
    }
});


function getCourses(){
    cleanCourses();
    // returns a promise
    return new Promise(function (resolve, reject) {
        getData().then(function() {
            createPagination();
        });
        resolve('Promise success');
        reject('Promise rejected');
    });
}

function createCourse(data, extra_data){
    /*
    "data": {
        "id": "course-v1:eol+NA303+2022",
        "course": "course-v1:eol+NA303+2022",
        "content": {
            "display_name": "Test202",
            "overview": " About This Course Include your long course description here. The long course description should contain 150-400 words. This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in paragraph tags. Requirements Add information about the skills and knowledge students need to take this course. Course Staff Staff Member #1 Biography of instructor/staff member #1 Staff Member #2 Biography of instructor/staff member #2 Frequently Asked Questions What web browser should I use? The Open edX platform works best with current versions of Chrome, Edge, Firefox, Internet Explorer, or Safari. See our list of supported browsers for the most up-to-date information. Question #2 Your answer would be displayed here. ",
            "number": "NA303"
        },
        "image_url": "/asset-v1:eol+NA303+2022+type@asset+block@images_course_image.jpg",
        "start": "2022-01-01T00:00:00+00:00",
        "end": "2023-11-30T00:00:00+00:00",
        "number": "NA303",
        "enrollment_start": "2021-01-01T00:00:00+00:00",
        "enrollment_end": "2021-12-31T00:00:00+00:00",
        "org": "eol",
        "modes": [
            "audit"
        ],
        "language": "en",
        'short_description', 'advertised_start', 'display_org_with_default', 'main_classification'
        }
    */
    let button_html = '<button type="button" class="dark-blue-button w-100 mb-0 '
    if (data.course_state == 'ongoing_enrollable' || data.course_state == 'upcoming_enrollable'){
        button_html = button_html + data.course_state +'_color">'+gettext('Enroll now')
    }else if(data.course_state == 'upcoming_notenrollable'){
        button_html = button_html + data.course_state +'_color">'+gettext('Coming soon')
    }else if(data.course_state == 'ongoing_notenrollable'){
        button_html = button_html + data.course_state +'_color">'+gettext('See more')
    }else if (data.course_state == 'completed'){
        button_html = button_html + data.course_state +'_color">'+gettext('Finished')
    }

    button_html =button_html +'</button>'
    const coursehtml = 
    '<div class="col-xl-4 col-lg-10 col-md-12 col-sm-12 mb-3 mx-3 p-2">'+
        '<div class="card {is_active} h-100" data-about="/courses/{course}/about" data-state="{state}" style="cursor: pointer;" onclick="window.location.href = this.dataset.about">'+
            '<div class="row g-0 p-0">'+
                '<div class="col-md-12">'+
                    '<div class="card-body">'+
                        '<div class="row g-0 p-0">'+
                            '<figure><img src="{image_url}" class="card-img-top img-fluid rounded-start" alt="{course_display_name}" onerror="this.onerror=null; this.src=show_default_image()" ></figure>'+
                        '</div>'+
                        '<strong><h5 class="card-title fw-bold my-2" title="{course_display_name}">{course_display_name}</h5></strong>'+
                        '{course_date_html}'+
                        '<div class="card-button mt-2 p-0 mb-0">'+
                            '<a href="/courses/{course}/about">'+ button_html +'</a>'+
                        '</div>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>'+
    '</div>';
    data['course_date_html'] = create_course_date_html(data.start, data.advertised_start, extra_data.self_paced, extra_data.effort, extra_data.price)
    data["course_display_name"] = data.content.display_name;
    data["is_active"] = course_is_active(data.end);
    data["state"] = data.course_state || '';
    return edx.HtmlUtils.interpolateHtml(edx.HtmlUtils.HTML(coursehtml), data);
}

function course_is_active(end){
    if (end !== undefined){
        var end_date = new Date(end);
        if(end_date < now) return 'inactive';
    }
    return ''
}

function create_course_date_html(start, advertised_start, self_paced, effort, course_price){
    let duration = '';
    let start_date = '';
    if (effort != undefined){
        duration =
        '<div class="row g-0 p-0">'+
            '<div class="col-2 m-0">'+
                '<div class="course-date-icon"><img src="'+window.themeAsset('images/fecha inicio.svg')+'"></div>'+
            '</div>'+
            '<div class="col-10">'+
                '<div class="course-date-text ml-3">'+
                    '<strong>'+
                        '<span>'+gettext("Duration")+'</span>'+
                    '</strong>'+
                    '<div class="course-date" aria-hidden="true">{effort}</div>'+
                '</div>'+
            '</div>'+
        '</div>'
    }

    if (advertised_start === null || advertised_start === undefined) {
        var aux_date = new Date(start)
        start_date = translate_date( aux_date);
    } else {
        start_date = advertised_start
    }

    const html_new = 
    '<div class="row ct3 my-2">'+
        '<div class="col-md-6 col-sm-12">'+
            '<div class="row g-0 p-0">'+
                '<div class="col-2 m-0">'+
                    '<div class="course-date-icon"><img src="'+window.themeAsset('images/fecha termino.svg')+'"></div>'+
                '</div>'+
                '<div class="col-10">'+
                    '<div class="course-date-text ml-3">'+
                        '<strong>'+
                            '<span>'+gettext("Classes Start")+'</span>'+
                        '</strong>'+
                        '<div class="course-date" aria-hidden="true">{start_date}</div>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>'+
         '<div class="col-md-6 col-sm-12">'+
            '<div class="row g-0 p-0">'+
                '<div class="col-2 m-0">'+
                    '<div class="course-date-icon"><img src="'+window.themeAsset('images/modalidad.svg')+'"></div>'+
                '</div>'+
                '<div class="col-10">'+
                    '<div class="course-date-text ml-3">'+
                        '<strong>'+
                            '<span>'+gettext("Pacing")+'</span>'+
                        '</strong>'+
                        '<div class="course-date" aria-hidden="true">{self_pace}</div>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>'+
    '</div>'+
    '<div class="row ct3 my-2">'+
        '<div class="col-md-6 col-sm-12">'+
            '<div class="row g-0 p-0">'+
                '<div class="col-2 m-0">'+
                    '<div class="course-date-icon"><img src="'+window.themeAsset('images/precio.svg')+'"></div>'+
                '</div>'+
                '<div class="col-10">'+
                    '<div class="course-date-text ml-3">'+
                        '<strong>'+
                            '<span>'+gettext("Price")+'</span>'+
                        '</strong>'+
                        '<div class="course-date" aria-hidden="true">{price}</div>'+
                    '</div>'+
                '</div>'+
            '</div>'+
        '</div>'+
        '<div class="col-md-6 col-sm-12">'+
            duration +
        '</div>'+
    '</div>';
    let price = course_price
    if (course_price !== 'Free' && course_price !== 'Gratis' && course_price !== 'None' && course_price !== undefined){  
        price_without_symbol =parseInt(course_price.slice(1));
        price = price_without_symbol.toLocaleString('es-CL');
        price = '$'+ price
    }
    else {
        price = gettext("Free")
    }

    var date_data = {
        'start_date': start_date,
        'self_pace': self_paced ? gettext('Student paced') : gettext('Instructor paced'),
        'effort': effort,
        'price': price
    };
    return edx.HtmlUtils.interpolateHtml(edx.HtmlUtils.HTML(html_new), date_data);
}

function translate_date(date){
    var options = { year: 'numeric', month: 'short', day: 'numeric' };
    if(document.documentElement.lang == "es-419" ){
    return date.toLocaleDateString("es-ES", options);
    }
    return date.toLocaleDateString("en-US", options);
}

function cleanCourses(){
    $(".filter-bar #discovery-message").text("");
    $("#list-courses").empty();
}

