import os
import inspect
import numpy as np
from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy import units as u
from flask import (Flask, request, redirect, url_for, render_template,
                   send_from_directory, jsonify)
from wtforms.validators import ValidationError
import wtforms
from werkzeug import secure_filename

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['fits', 'csv', 'txt', 'ipac', 'dat', 'tsv'])
valid_column_names = ['Ignore', 'IDs', 'SurfaceDensity', 'VelocityDispersion',
                      'Radius', 'IsSimulated']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
def upload_file():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # print file_data
    return redirect(url_for('uploaded_file',
                            filename=filename))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from astropy.table import Table
    table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    return render_template("parse_file.html", table=table, filename=filename,
                           real_column_names=valid_column_names)
    #return send_from_directory(app.config['UPLOAD_FOLDER'],
    #                           filename)

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
#@app.route('/validate_units/<unit_str>', methods=['GET', 'POST'])
def validate_units(data):
    print request, dir(request), data
    unit_str = data
    try:
        u.Unit(unit_str)
        OK = True
    except:
        OK = False
    return jsonify(OK=OK)

@app.route('/autocomplete_filetypes',methods=['GET'])
def autocomplete_filetypes():
    from astropy.io import registry
    from astropy.table import Table
    formats = registry.get_formats(Table)
    #print formats
    search = request.args.get('term')
    readable_formats = formats[formats['Read']=='Yes']['Format']
    #print readable_formats
    return jsonify(json_list=list(readable_formats))

@app.route('/autocomplete_column_names',methods=['GET'])
def autocomplete_column_names():
    return jsonify(json_list=valid_column_names)

@app.route('/set_columns', methods=['POST', 'GET'])
def set_columns():
    print "ready to set columns", request.form
    # import IPython
    # IPython.embed()
    return 'Ok'

class MyForm(wtforms.Form):
    """
    Validate the units instead of using a dropdown
    """
    unit = wtforms.StringField('unit', [])

    def validate_unit(form, field):
        try:
            u.Unit(field.data)
        except ValueError,u.UnitsError:
            raise ValidationError('Invalid unit')

def upload_to_github(filename):
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
