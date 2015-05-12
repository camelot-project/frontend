import os
import inspect
import numpy as np
from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy import units as u
from ingest_datasets_better import rename_columns, set_units, convert_units, add_name_column, add_generic_ids_if_needed, add_is_sim_if_needed, fix_bad_types
from flask import (Flask, request, redirect, url_for, render_template,
                   send_from_directory, jsonify)
from simple_plot import plotData, timeString
from werkzeug import secure_filename
import difflib

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['fits', 'csv', 'txt', 'ipac', 'dat', 'tsv'])
valid_column_names = ['Ignore', 'IDs', 'SurfaceDensity', 'VelocityDispersion',
                      'Radius', 'IsSimulated']

from astropy.io import registry
from astropy.table import Table
table_formats = registry.get_formats(Table)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Allow zipping in jinja templates: http://stackoverflow.com/questions/5208252/ziplist1-list2-in-jinja2
import jinja2
env = jinja2.Environment()
env.globals.update(zip=zip)

# http://stackoverflow.com/questions/21306134/iterating-over-multiple-lists-in-python-flask-jinja2-templates
@app.template_global(name='zip')
def _zip(*args, **kwargs): #to not overwrite builtin zip in globals
    return __builtins__.zip(*args, **kwargs)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    print 'filename:', filename
    return filename.rsplit('.', 1)[1]

@app.route('/')
def index():
    return render_template('upload_form.html')

@app.route('/upload', methods=['POST'])
@app.route('/upload/<fileformat>', methods=['POST'])
def upload_file(fileformat=None):
    """
    """

    if 'fileformat' in request.form and fileformat is None:
        fileformat = request.form['fileformat']
    print "in /upload: fileformat={0}".format(fileformat)
    print "in /upload: request.form: {0}".format(request.form)

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        print "Before uploaded_file redirect, filename={0}, fileformat={1}".format(filename,fileformat)
        return redirect(url_for('uploaded_file',
                                filename=filename,
                                fileformat=fileformat))
    else:
        return render_template("upload_form.html", error="File type not supported")

@app.route('/uploads/<filename>')
@app.route('/uploads/<filename>/<fileformat>')
def uploaded_file(filename, fileformat=None):
    print "In uploaded_file, filename={0}, fileformat={1}".format(filename, fileformat)
    print request.form
    print request
    try:
        table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                           format=fileformat)
        print "Successfully read table with fileformat={0}".format(fileformat)
    except Exception as ex:
        print "Did not read table with format={0}.  Trying to handle ambiguous version.".format(fileformat)
        return handle_ambiguous_table(filename, ex)

    best_matches = {difflib.get_close_matches(vcn, table.colnames,  n=1,
                                              cutoff=0.4)[0]: vcn
                    for vcn in valid_column_names
                    if any(difflib.get_close_matches(vcn, table.colnames, n=1, cutoff=0.4))
                   }
    print best_matches

    best_column_names = [best_matches[colname] if colname in best_matches else 'Ignore'
                         for colname in table.colnames]
    print 'best_column_names:', best_column_names

    return render_template("parse_file.html", table=table, filename=filename,
                           real_column_names=valid_column_names,
                           best_column_names=best_column_names,
                           fileformat=fileformat,
                          )
    #return send_from_directory(app.config['UPLOAD_FOLDER'],
    #                           filename)

def handle_ambiguous_table(filename, exception):
    """
    Deal with an uploaded file that doesn't autodetect
    """
    extension = os.path.splitext(filename)[-1]
    best_match = difflib.get_close_matches(extension[1:], table_formats, n=1, cutoff=0.05)
    if any(best_match):
        best_match = best_match[0]
    else:
        best_match = ""

    # This doesn't work right now - don't know why.
    return render_template('upload_form_filetype.html', filename=filename,
                           best_match_extension=best_match,
                           exception=exception)

@app.route('/autocomplete_units',methods=['GET'])
def autocomplete_units():
    search = request.args.get('term')
    print "search: ",search
    # print os.getcwd()
    allunits = set()
    for unitname,unit in inspect.getmembers(u):
        if isinstance(unit, u.UnitBase):
            try:
                for name in unit.names:
                    allunits.add(name)
            except AttributeError:
                continue
    app.logger.debug(search)
    return jsonify(json_list=list(allunits))

@app.route('/validate_units', methods=['GET', 'POST'])
def validate_units():
    try:
        unit_str = request.args.get('unit_str', 'error', type=str)
        u.Unit(unit_str)
        OK = True
    except:
        OK = False
    return jsonify(OK=OK)

@app.route('/autocomplete_filetypes',methods=['GET'])
def autocomplete_filetypes():
    #print formats
    search = request.args.get('term')
    readable_formats = table_formats[table_formats['Read']=='Yes']['Format']
    #print readable_formats
    return jsonify(json_list=list(readable_formats))

@app.route('/autocomplete_column_names',methods=['GET'])
def autocomplete_column_names():
    return jsonify(json_list=valid_column_names)

@app.route('/set_columns/<path:filename>', methods=['POST', 'GET'])
def set_columns(filename, fileformat=None):
    """
    """

    if fileformat is None and 'fileformat' in request.args:
        fileformat = request.args['fileformat']

    print "set_columns filename:{0}  fileformat:{1}".format(filename, fileformat)

    # This function needs to know about the filename or have access to the
    # table; how do we arrange that?
    table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename), format=fileformat)
    
    column_data = \
        {field:{'Name':value} for field,value in request.form.items() if '_units' not in field}
    for field,value in request.form.items():
        if '_units' in field:
            column_data[field[:-6]]['unit'] = value
    print "column_data: ",column_data
    
    units_data = {}
    for _, pair in column_data.items():
        if pair['Name'] != "Ignore" and pair['Name'] != "IsSimulated":
            units_data[pair['Name']] = pair['unit']

    print 'units_data:', units_data    
    # print table
    rename_columns(table, {k: v['Name'] for k,v in column_data.items()})
    # print 'renamed columns?:', table
    set_units(table, units_data)
    table = fix_bad_types(table)
    print(table)
    convert_units(table)
    print(table)
    # print 'units are set?:', table
    add_name_column(table, 'TEST - REPLACE')
    add_generic_ids_if_needed(table)
    add_is_sim_if_needed(table)
    myplot = plotData(timeString(), table, 'static/figures/'+filename)

    return render_template('show_plot.html', imagename='/'+myplot)#url_for('static',filename='figures/'+myplot))



def upload_to_github(filename):
    """
    WIP: Eventually, we want each file to be uploaded to github and submitted
    as a pull request when people submit their data

    This will be tricky: we need to have a "replace existing file" logic in
    addition to the original submission.  We also need an account + API_KEY
    etc, which may be the most challenging part.
    """
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
        content = f.read()
    data = {'path': 'data_files/',
            'content': content,
            'branch': 'master',
            'message': 'Upload a new data file {0}'.format(filename)}

    requests.post
    pass

if __name__ == '__main__':
    app.run(debug=True)
