$SCRIPT_ROOT = {{ request.script_root|tojson|safe }};

$(function() {
    $.ajax({
        url: '{{ url_for(".autocomplete_units") }}'
    }).done(function (data) {
        $('.units').autocomplete({
            source: data.json_list,
            minLength: 2
        });
    });
});

$(function() {
    $.ajax({
        url: '{{ url_for(".autocomplete_column_names") }}'
    }).done(function (data) {
        $('.real_column_name').autocomplete({
            source: data.json_list,
            minLength: 2
        });
    });
});

$(function() {
    $.ajax({
        url: '{{ url_for(".autocomplete_filetypes") }}'
        }).done(function (data) {
            $('#file_format').autocomplete({
            source: data.json_list,
            minLength: 2
        });
    });
});