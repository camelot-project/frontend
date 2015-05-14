"""
This is the main python tool (the "backend") for uploading, processing, and
ingesting data files.  It will call the plotter to make plots too.

You can start up the web server with:

    python upload_form.py

Please try to keep lines to 80 characters where possible

Print statements will show up in the terminal.  Feel free to use them for
debugging, but try to remove them when you're done.

"""
from __future__ import print_function
import os
import inspect
import numpy as np
from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy.table.jsviewer import write_table_jsviewer
from astropy import units as u
from ingest_datasets_better import (rename_columns, set_units, convert_units,
                                    add_name_column, add_generic_ids_if_needed,
                                    add_is_sim_if_needed, fix_bad_types,
                                    add_filename_column, add_timestamp_column,
                                    reorder_columns, append_table,
                                    ignore_duplicates, update_duplicates)
from flask import (Flask, request, redirect, url_for, render_template,
                   send_from_directory, jsonify)
from simple_plot import plotData, plotData_Sigma_sigma
from werkzeug import secure_filename
import difflib

UPLOAD_FOLDER = 'uploads/'
OUTPUT_FOLDER = 'generated/'
ALLOWED_EXTENSIONS = set(['fits', 'csv', 'txt', 'ipac', 'dat', 'tsv'])
valid_column_names = ['Ignore', 'IDs', 'SurfaceDensity', 'VelocityDispersion',
                      'Radius', 'IsSimulated', 'Username']
use_column_names = ['SurfaceDensity', 'VelocityDispersion','Radius']
use_units = ['Msun/pc^2','km/s','pc']
FigureStrBase='Output_Sigma_sigma_r_'
TooOld=300

import glob
import random
import time
import datetime
from datetime import datetime
import matplotlib
import matplotlib.pylab as plt

from astropy.io import registry
from astropy.table import Table
table_formats = registry.get_formats(Table)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


# Allow zipping in jinja templates: http://stackoverflow.com/questions/5208252/ziplist1-list2-in-jinja2
import jinja2
env = jinja2.Environment()
env.globals.update(zip=zip)

# http://stackoverflow.com/questions/21306134/iterating-over-multiple-lists-in-python-flask-jinja2-templates
@app.template_global(name='zip')
def _zip(*args, **kwargs): #to not overwrite builtin zip in globals
    """ This function allows the use of "zip" in jinja2 templates """
    return __builtins__.zip(*args, **kwargs)

def allowed_file(filename):
    """
    For a given filename, check if it is in the allowed set of file types
    """
    return ('.' in filename and filename.rsplit('.', 1)[1] in
            ALLOWED_EXTENSIONS)

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_form')
def upload_form():
    return render_template('upload_form.html')

@app.route('/upload', methods=['POST'])
@app.route('/upload/<fileformat>', methods=['POST'])
def upload_file(fileformat=None):
    """
    Main upload form.  Accepts a posted file object (which is accessed via
    request.files) and an optional file format.
    """

    if 'fileformat' in request.form and fileformat is None:
        fileformat = request.form['fileformat']

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        return redirect(url_for('uploaded_file',
                                filename=filename,
                                fileformat=fileformat))
    else:
        return render_template("upload_form.html", error="File type not supported")

@app.route('/uploads/<filename>')
@app.route('/uploads/<filename>/<fileformat>')
def uploaded_file(filename, fileformat=None):
    """
    Handle an uploaded file.  Takes a filename, which points to a file on disk
    in the UPLOAD_FOLDER directory, and an optional file format.

    If this fails, it will load the ambiguous file format loader
    """
    try:
        table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                           format=fileformat)
    except Exception as ex:
        print("Did not read table with format={0}.  Trying to handle ambiguous version.".format(fileformat))
        return handle_ambiguous_table(filename, ex)

    best_matches = {difflib.get_close_matches(vcn, table.colnames,  n=1,
                                              cutoff=0.4)[0]: vcn
                    for vcn in valid_column_names
                    if any(difflib.get_close_matches(vcn, table.colnames, n=1, cutoff=0.4))
                   }

    best_column_names = [best_matches[colname] if colname in best_matches else 'Ignore'
                         for colname in table.colnames]

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

    return render_template('upload_form_filetype.html', filename=filename,
                           best_match_extension=best_match,
                           exception=exception)

@app.route('/autocomplete_units',methods=['GET'])
def autocomplete_units():
    """
    Autocompletion for units.  NOT USED ANY MORE.
    """
    search = request.args.get('term')

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
    """
    Validate the units: try to interpret the passed string as an astropy unit. 
    """
    try:
        unit_str = request.args.get('unit_str', 'error', type=str)
        u.Unit(unit_str)
        OK = True
    except:
        OK = False
    return jsonify(OK=OK)

@app.route('/autocomplete_filetypes',methods=['GET'])
def autocomplete_filetypes():
    """
    Autocompletion for filetypes.  Used, but presently not working.  =(
    """
    search = request.args.get('term')
    readable_formats = table_formats[table_formats['Read']=='Yes']['Format']
    return jsonify(json_list=list(readable_formats))

@app.route('/autocomplete_column_names',methods=['GET'])
def autocomplete_column_names():
    """
    NOT USED
    """
    return jsonify(json_list=valid_column_names)

@app.route('/set_columns/<path:filename>', methods=['POST', 'GET'])
def set_columns(filename, fileformat=None):
    """
    Meat of the program: takes the columns from the input table and matches
    them to the columns provided by the user in the column form.
    Then, assigns units and column information and does all the proper file
    ingestion work.

    """

    if fileformat is None and 'fileformat' in request.args:
        fileformat = request.args['fileformat']


    # This function needs to know about the filename or have access to the
    # table; how do we arrange that?
    table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                       format=fileformat)
    
    column_data = \
        {field:{'Name':value} for field,value in request.form.items() if '_units' not in field}
    for field,value in request.form.items():
        if '_units' in field:
            column_data[field[:-6]]['unit'] = value
    
    units_data = {}
    for key, pair in column_data.items():
        if pair['Name'] != "Ignore" and pair['Name'] != "IsSimulated" and key != "Username":
            units_data[pair['Name']] = pair['unit']

    # Parse the table file, step-by-step
    rename_columns(table, {k: v['Name'] for k,v in column_data.items()})
    set_units(table, units_data)
    table = fix_bad_types(table)
    convert_units(table)
    add_name_column(table, column_data.get('Username')['Name'])
    add_filename_column(table, filename)
    timestamp = datetime.now()
    add_timestamp_column(table, timestamp)

    add_generic_ids_if_needed(table)
    if column_data.get('issimulated') is None:
        add_is_sim_if_needed(table, False)
    else:
        add_is_sim_if_needed(table, True)

# Detect duplicate IDs in uploaded data and bail out if found
    seen = {}
    for row in table:
        name = row['Names']
        id = row['IDs']
        if id in seen:
            raise InvalidUsage("Duplicate ID detected in table: username = {0}, id = {1}. All IDs must be unique.".format(name, id))
        else:
            seen[id] = name

    # If merged table already exists, then append the new entries.
    # Otherwise, create the table

    merged_table_name = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_table.ipac')
    if os.path.isfile(merged_table_name):
        merged_table = Table.read(merged_table_name, converters={'Names': [ascii.convert_numpy('S64')], 
        'IDs': [ascii.convert_numpy('S64')], 'IsSimulated': [ascii.convert_numpy('S5')]}, format='ascii.ipac')
        if 'Timestamp' not in merged_table.colnames:
            # Create a fake timestamp for the previous entries if they don't already have one
            fake_timestamp = datetime.min
            add_timestamp_column(merged_table, fake_timestamp)
    else:
    # Maximum string length of 64 for username, ID -- larger strings are silently truncated
    # TODO: Adjust these numbers to something more reasonable, once we figure out what that is,
    #       and verify that submitted data obeys these limits
        merged_table = Table(data=None, names=['Names','IDs','SurfaceDensity',
                       'VelocityDispersion','Radius','IsSimulated', 'Timestamp'], 
                       dtype=[('str', 64),('str', 64),'float','float','float','bool',('str', 26)])
        set_units(merged_table)

    table = reorder_columns(table, merged_table.colnames)

    # Detect whether any username, ID pairs match entries already in the merged table
    duplicates = {}
    for row in merged_table:
        name = row['Names']
        id = row['IDs']
        if id in seen:
            if name == seen[id]:
                print("Found duplicate! {0}, {1}".format(name, id))
                duplicates[id] = name

    #ignore_duplicates(table, duplicates)
    #update_duplicates(merged_table, duplicates)

    append_table(merged_table, table)
    Table.write(merged_table, merged_table_name, format='ascii.ipac')

    if not os.path.isdir('static/figures/'):
        os.mkdir('static/figures')
    if not os.path.isdir('static/jstables/'):
        os.mkdir('static/jstables')

    outfilename = os.path.splitext(filename)[0]
    myplot = plotData_Sigma_sigma(timeString(), table, 'static/figures/'+outfilename)

    tablecss = "table,th,td,tr,tbody {border: 1px solid black; border-collapse: collapse;}"
    write_table_jsviewer(table,
                         'static/jstables/{fn}.html'.format(fn=outfilename),
                         css=tablecss,
                         jskwargs={'use_local_files':False},
                         table_id=outfilename)

    return render_template('show_plot.html', imagename='/'+myplot,
                           tablefile='{fn}.html'.format(fn=outfilename))



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


@app.route('/query_form')
def query_form():
    
    filename = "merged_table.ipac"
    table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename), format='ascii.ipac')
    
    usetable = table[use_column_names]
    
    best_matches = {difflib.get_close_matches(vcn, usetable.colnames,  n=1,
                                              cutoff=0.4)[0]: vcn
                    for vcn in use_column_names
                    if any(difflib.get_close_matches(vcn, usetable.colnames, n=1, cutoff=0.4))
                   }

    best_column_names = [best_matches[colname] if colname in best_matches else 'Ignore'
                         for colname in usetable.colnames]

    return render_template("query_form.html", table=table, usetable=usetable, use_units=use_units, filename=filename,
                           use_column_names=use_column_names,
                           best_column_names=best_column_names,
                          )

def clearPlotOutput(FigureStrBase,TooOld) :
    
    for fl in glob.glob(FigureStrBase+"*.png") + glob.glob(FigureStrBase+"*.pdf"):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

def timeString():
    
    TimeString=datetime.now().strftime("%Y%m%d%H%M%S%f")
    return TimeString
                          
@app.route('/query/<path:filename>', methods=['POST'])
def query(filename, fileformat=None):
    SurfMin = float(request.form['SurfaceDensity_min'])*u.M_sun/u.pc**2
    SurfMax = float(request.form['SurfaceDensity_max'])*u.M_sun/u.pc**2
    VDispMin = float(request.form['VelocityDispersion_min'])*u.km/u.s
    VDispMax = float(request.form['VelocityDispersion_max'])*u.km/u.s
    RadMin = float(request.form['Radius_min'])*u.pc
    RadMax = float(request.form['Radius_max'])*u.pc
#    print(np.type(SurfMin))
    print(SurfMin,SurfMax,VDispMin,VDispMax,RadMin,RadMax)

    NQuery=timeString()
    clearPlotOutput(FigureStrBase,TooOld)
    
    print(NQuery)
        
    table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename), format='ascii.ipac')
    set_units(table)
    Author = table['Names']
    Run = table['IDs']
    SurfDens = table['SurfaceDensity']
    VDisp = table['VelocityDispersion']
    Rad = table['Radius']
    IsSim = (table['IsSimulated'] == 'True')
#    print(SurfDens)
    
    temp_table = [table[h].index for i,j,k,h in zip(table['SurfaceDensity'],table['VelocityDispersion'],table['Radius'], range(len(table))) if SurfMin < i*table['SurfaceDensity'].unit < SurfMax and VDispMin < j*table['VelocityDispersion'].unit < VDispMax and RadMin < k*table['Radius'].unit < RadMax]
    use_table = table[temp_table]
    use_table.write(os.path.join(app.config['OUTPUT_FOLDER'], 'output_table_'+NQuery+'.csv'), format='csv')	 		
    
    return plotData_Sigma_sigma(NQuery, use_table, FigureStrBase,
                         SurfMin, SurfMax,
                         VDispMin,
                         VDispMax, RadMin, RadMax,
                         interactive=False)
    
#    UseSurf = (SurfDens > SurfMin) & (SurfDens < SurfMax)
#    UseVDisp = (VDisp > VDispMin) & (VDisp < VDispMax)
#    UseRad = (Rad > RadMin) & (Rad < RadMax)
#    Use = UseSurf & UseVDisp & UseRad
#    Obs = (~IsSim) & Use
#    Sim = IsSim & Use
#    
#    UniqueAuthor = set(Author[Use])
#    NUniqueAuthor = len(UniqueAuthor)
#    
#    #colors = random.sample(matplotlib.colors.cnames, NUniqueAuthor)
#    colors = list(plt.cm.jet(np.linspace(0,1,NUniqueAuthor)))
#    random.shuffle(colors)
#    
#    plt.loglog()
#    markers = ['o','s']
#    for iAu,color in zip(UniqueAuthor,colors) :
#        UsePlot = (Author == iAu) & Use
#        ObsPlot = ((Author == iAu) & (~IsSim)) & Use 
#        SimPlot = ((Author == iAu) & (IsSim)) & Use
#        if any(ObsPlot):
#            plt.scatter(SurfDens[ObsPlot], VDisp[ObsPlot], marker=markers[0],
#                        s=(np.log(np.array(Rad[ObsPlot]))-np.log(np.array(RadMin))+0.5)**3.,
#                        color=color, alpha=0.5)
#        if any(SimPlot):
#            plt.scatter(SurfDens[SimPlot], VDisp[SimPlot], marker=markers[1],
#                        s=(np.log(np.array(Rad[SimPlot]))-np.log(np.array(RadMin))+0.5)**3.,
#                        color=color, alpha=0.5)
#    if any(Obs):
#        plt.scatter(SurfDens[Obs], VDisp[Obs], marker=markers[0],
#                    s=(np.log(np.array(Rad[Obs]))-np.log(np.array(RadMin))+0.5)**3.,
#                    facecolors='none', edgecolors='black',
#                    alpha=0.5)
#    if any(Sim):
#        plt.scatter(SurfDens[Sim], VDisp[Sim], marker=markers[1],
#                    s=(np.log(np.array(Rad[Sim]))-np.log(np.array(RadMin))+0.5)**3.,
#                    facecolors='none', edgecolors='black',
#                    alpha=0.5)
#    plt.xlabel('$\Sigma$ [M$_{\odot}$ pc$^{-2}$]', fontsize=16)
#    plt.ylabel('$\sigma$ [km s$^{-1}$]', fontsize=16)
#
#    ax = plt.gca()
#    box = ax.get_position()
#    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
#
#    # Put a legend to the right of the current axis
#    ax.legend(UniqueAuthor, loc='center left', bbox_to_anchor=(1.0, 0.5), prop={'size':12}, markerscale = .7, scatterpoints = 1)
#
##    plt.xlim((SurfMin.to(u.M_sun/u.pc**2).value,SurfMax.to(u.M_sun/u.pc**2).value))
##    plt.ylim((VDispMin.to(u.km/u.s).value,VDispMax.to(u.km/u.s).value))
#    plt.show()
#    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], FigureStrBase+NQuery+'.png'),bbox_inches='tight',dpi=150)
##    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], FigureStrBase+NQuery+'.pdf'),bbox_inches='tight',dpi=150)
#    
#    return render_template('show_plot.html', imagename='/'+FigureStrBase+NQuery+'.png')


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['Error'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == '__main__':
    app.run(debug=True)





