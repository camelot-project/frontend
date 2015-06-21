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
import re
import os
import inspect
import numpy as np
import subprocess
import requests
import json
from ingest_datasets_better import (rename_columns, set_units, convert_units,
                                    add_name_column, add_generic_ids_if_needed,
                                    add_is_sim_if_needed, fix_bad_types,
                                    add_filename_column, add_timestamp_column,
                                    reorder_columns, append_table,
                                    ignore_duplicates, update_duplicates,
                                    add_is_gal_if_needed, add_is_gal_column,
                                    fix_bad_colnames)
from flask import (Flask, request, redirect, url_for, render_template,
                   send_from_directory, jsonify)
from simple_plot import plotData, plotData_Sigma_sigma
from werkzeug import secure_filename
import difflib
import glob
import random
import keyring
import __builtin__
import time
import datetime
from datetime import datetime
from astropy.io import registry, ascii
from ipac_writer import ipac_writer
from astropy.table import Table, vstack
from astropy.table.jsviewer import write_table_jsviewer
from astropy import units as u
from astropy import log
if os.getenv('DEBUG'):
    log.setLevel(10)
import hashlib
import traceback

UPLOAD_FOLDER = 'uploads/'
DATABASE_FOLDER = 'database/'
MPLD3_FOLDER = 'static/mpld3/'
PNG_PLOT_FOLDER = 'static/figures/'
TABLE_FOLDER = 'static/jstables/'
ALLOWED_EXTENSIONS = set(['fits', 'csv', 'txt', 'ipac', 'dat', 'tsv'])
valid_column_names = ['Ignore', 'IDs', 'SurfaceDensity', 'VelocityDispersion',
                      'Radius', 'IsSimulated', 'IsGalactic', 'Username', 'Filename']
dimensionless_column_names = ['Ignore', 'IDs', 'IsSimulated', 'IsGalactic',
                              'Username', 'Filename', 'Email', 'ObsSim',
                              'GalExgal', "ADS_ID", "DOI_or_URL", 'doi', 'adsid']
use_column_names = ['SurfaceDensity', 'VelocityDispersion','Radius']
use_units = ['Msun/pc^2','km/s','pc']
FigureStrBase='Output_Sigma_sigma_r_'
TableStrBase='Output_Table_'
TooOld=300 # age in seconds of files to delete
git_user = 'SirArthurTheSubmitter'
submitter_gmail = '{0}@gmail.com'.format(git_user)

table_widths = [64, 64, 20, 20, 20, 12, 12, 26, 36, 20, 64]

table_formats = registry.get_formats(Table)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MPLD3_FOLDER'] = MPLD3_FOLDER
app.config['DATABASE_FOLDER'] = DATABASE_FOLDER
app.config['PNG_PLOT_FOLDER'] = PNG_PLOT_FOLDER
app.config['TABLE_FOLDER'] = TABLE_FOLDER
#app.config['DEBUG']=True

# this might be subject to a race condition?  How?!
for path in (MPLD3_FOLDER, PNG_PLOT_FOLDER, TABLE_FOLDER):
    try:
        log.debug("ls {0}".format(path))
        os.listdir(path)
        log.debug("Path {0} does too exist!".format(path))
    except OSError:
        log.debug("Path {0} does not exist.".format(path))
    while not os.path.isdir(path):
        # these should not exist and should definitely not be files
        if os.path.isfile(path):
            log.debug("Deleting regular file {0}".format(path))
            try:
                os.remove(path)
            except OSError as ex:
                log.debug("Failed to remove {0}: {1}".format(path, ex))
                continue
        log.debug("Making directory {0}".format(path))
        try:
            os.mkdir(path)
        except OSError as ex:
            log.debug("Failed to create {0}: {1}".format(path, ex))
            continue


# Allow zipping in jinja templates: http://stackoverflow.com/questions/5208252/ziplist1-list2-in-jinja2
import jinja2
env = jinja2.Environment()
env.globals.update(zip=zip)

# http://stackoverflow.com/questions/21306134/iterating-over-multiple-lists-in-python-flask-jinja2-templates
@app.template_global(name='zip')
def _zip(*args, **kwargs): #to not overwrite builtin zip in globals
    """ This function allows the use of "zip" in jinja2 templates """
    return __builtin__.zip(*args, **kwargs)

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

    # column names can't have non-letters in them or javascript fails
    fix_bad_colnames(table)

    # read units and keywords from table
    column_units=[table[cln].unit for cln in table.colnames]
    tab_metadata={'Author':'','ADS_ID':'','DOI or URL':'','Submitter':'',
                  'IsObserved':False,'IsSimulated':False,
                  'IsGalactic':False,'IsExtragalactic':False}
    mydict = {'author': 'Author',
              'ads': 'ADS_ID', 'asd_id': 'ADS_ID',
              'doi': 'DOI or URL', 'url': 'DOI or URL',
              'email': 'Submitter', 'submitter': 'Submitter',
              'isobserved': 'IsObserved', 'issimulated': 'IsSimulated',
              'isgalactic': 'IsGalactic', 'isextragalactic': 'IsExtragalactic'}
    if len(table.meta) > 0:
        for name, keyword in table.meta['keywords'].items():
            if name.lower() in mydict:
                outkey = mydict[name.lower()]
                tab_metadata[outkey] = keyword['value']

    return render_template("parse_file.html", table=table, filename=filename,
                           real_column_names=valid_column_names,
                           best_column_names=best_column_names,
                           default_units=column_units,
                           tab_metadata=tab_metadata,
                           fileformat=fileformat,
                          )

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
    log.debug("Beginning set_columns.")

    if fileformat is None and 'fileformat' in request.args:
        fileformat = request.args['fileformat']

    log.debug("Reading table {0}".format(filename))
    try:
        table = Table.read(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                           format=fileformat)
    except Exception as ex:
        return render_template('error.html', error=str(ex),
                               traceback=traceback.format_exc(ex))

    # Have to fix the column reading twice
    fix_bad_colnames(table)

    log.debug("Parsing column data.")
    log.debug("form: {0}".format(request.form))
    column_data = {field:{'Name':value}
                   for field,value in request.form.items()
                   if '_units' not in field}
    log.debug("Looping through form items.")
    for field,value in request.form.items():
        if '_units' in field:
            column_data[field[:-6]]['unit'] = value

    log.debug("Looping through column_data.")
    units_data = {}
    for key, pair in column_data.items():
        if key not in dimensionless_column_names and pair['Name'] not in dimensionless_column_names:
            units_data[pair['Name']] = pair['unit']

    log.debug("Created mapping.")
    mapping = {filename: [column_data, units_data]}

    log.debug("Further table handling.")
    # Parse the table file, step-by-step
    rename_columns(table, {k: v['Name'] for k,v in column_data.items()})
    set_units(table, units_data)
    table = fix_bad_types(table)
    try:
        convert_units(table)
    except Exception as ex:
        return render_template('error.html', error=str(ex), traceback=traceback.format_exc(ex))
    add_name_column(table, column_data.get('Username')['Name'])
    if 'ADS_ID' not in table.colnames:
        table.add_column(table.Column(name='ADS_ID', data=[request.form['adsid']]*len(table)))
    if 'DOI_or_URL' not in table.colnames:
        table.add_column(table.Column(name='DOI_or_URL', data=[request.form['doi']]*len(table)))
    timestamp = datetime.now()
    add_timestamp_column(table, timestamp)

    add_generic_ids_if_needed(table)
    if column_data.get('ObsSim')['Name'] == 'IsObserved':
        add_is_sim_if_needed(table, False)
    else:
        add_is_sim_if_needed(table, True)

    if column_data.get('GalExgal')['Name'] == 'IsExtragalactic':
        add_is_gal_if_needed(table, False)
    else:
        add_is_gal_if_needed(table, True)

    # Rename the uploaded file to something unique, and store this name in the table
    extension = os.path.splitext(filename)[-1]
    full_filename_old = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(full_filename_old) as file:
        unique_filename = hashlib.sha1(file.read()).hexdigest()[0:36-len(extension)] + extension
    full_filename_new = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    os.rename(full_filename_old, full_filename_new)
    add_filename_column(table, unique_filename)
    log.debug("Table column names after add_filename_column: ",table.colnames)

    handle_email(request.form['Email'], unique_filename)

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

    merged_table_name = os.path.join(app.config['DATABASE_FOLDER'], 'merged_table.ipac')
    if os.path.isfile(merged_table_name):
        merged_table = Table.read(merged_table_name,
                                  converters={'Names':
                                              [ascii.convert_numpy('S64')],
                                              'IDs':
                                              [ascii.convert_numpy('S64')],
                                              'IsSimulated':
                                              [ascii.convert_numpy('S5')],
                                              'IsGalactic':
                                              [ascii.convert_numpy('S5')],
                                              'Filename':
                                              [ascii.convert_numpy('S36')]},
                                  format='ascii.ipac')
        if 'IsGalactic' not in merged_table.colnames:
            # Assume that anything we didn't already tag as Galactic is probably Galactic
            add_is_gal_column(merged_table, True)

        if 'Timestamp' not in merged_table.colnames:
            # Create a fake timestamp for the previous entries if they don't already have one
            fake_timestamp = datetime.min
            add_timestamp_column(merged_table, fake_timestamp)

        if 'Filename' not in merged_table.colnames:
            # If we don't know the filename, flag it as unknown
            add_filename_column(merged_table, 'Unknown'+' '*29)

        if 'ADS_ID' not in merged_table.colnames:
            # If we don't know the filename, flag it as unknown
            merged_table.add_column(table.Column(name='ADS_ID', data=['Unknown'+' '*13]*len(merged_table)))

        if 'DOI_or_URL' not in merged_table.colnames:
            # If we don't know the filename, flag it as unknown
            merged_table.add_column(table.Column(name='DOI_or_URL', data=['Unknown'+' '*57]*len(merged_table)))

    else:
        # Maximum string length of 64 for username, ID -- larger strings are silently truncated
        # TODO: Adjust these numbers to something more reasonable, once we figure out what that is,
        #       and verify that submitted data obeys these limits
        merged_table = Table(data=None, names=['Names','IDs','SurfaceDensity',
                       'VelocityDispersion','Radius','IsSimulated', 'IsGalactic', 'Timestamp', 'Filename',
                                              'ADS_ID', 'DOI_or_URL'],
                       dtype=[('str', 64),('str', 64),'float','float','float','bool','bool',
                              ('str', 26),('str', 36), ('str',20), ('str',64)])
        dts = merged_table.dtype
        # Hack to force fixed-width: works only on strings
        # merged_table.add_row(["_"*dts[ind].itemsize if dts[ind].kind=='S'
        #                       else False if dts[ind].kind == 'b'
        #                       else np.nan
        #                       for ind in range(len(dts))])
        set_units(merged_table)

    table = reorder_columns(table, merged_table.colnames)
    print("Table column names after reorder_columns: ",table.colnames)
    print("Merged table column names after reorder_columns: ",merged_table.colnames)

    # Detect whether any username, ID pairs match entries already in the merged table
    duplicates = {}
    for row in merged_table:
        name = row['Names']
        id = row['IDs']
        if id in seen:
            if name == seen[id]:
                duplicates[id] = name

    handle_duplicates(table, merged_table, duplicates)

    append_table(merged_table, table)

    username = column_data.get('Username')['Name']

    # go to appropriate branches in the database gits
    print("Re-fetching the databases.")
    try:
        check_authenticate_with_github()
        branch_database, timestamp = setup_submodule(username,
                                                     workingdir='database/',
                                                     database='database')
        branch_uploads, timestamp = setup_submodule(username,
                                                    workingdir='uploads/',
                                                    database='uploads',
                                                    timestamp=timestamp,
                                                    branch=branch_database,
                                                   )
    except Exception as ex:
        return render_template('error.html', error=str(ex),
                               traceback=traceback.format_exc(ex))

    # write the modified table
    ipac_writer(merged_table, merged_table_name, widths=table_widths)

    print("Committing changes")
    # Add merged data to database
    try:
        branch_database,timestamp = commit_change_to_database(username,
                                                              branch=branch_database,
                                                              timestamp=timestamp)
    except Exception as ex:
        cleanup_git_directory('database/', allow_fail=False)
        return render_template('error.html', error=str(ex),
                               traceback=traceback.format_exc(ex))
    try:
        # Adding raw file to uploads
        branch_uploads,timestamp = commit_change_to_database(username,
                                                             tablename=unique_filename,
                                                             workingdir='uploads/',
                                                             database='uploads',
                                                             branch=branch_database,
                                                             timestamp=timestamp)
    except Exception as ex:
        cleanup_git_directory('uploads/', allow_fail=False)
        return render_template('error.html', error=str(ex),
                               traceback=traceback.format_exc(ex))


    try:
        log.debug("Creating pull requests")
        response_database, link_pull_database = pull_request(branch_database,
                                                             username,
                                                             timestamp)
        response_uploads, link_pull_uploads = pull_request(branch_database,
                                                           username,
                                                           timestamp,
                                                           database='uploads')
    except Exception as ex:
        cleanup_git_directory('uploads/', allow_fail=False)
        cleanup_git_directory('database/', allow_fail=False)
        return render_template('error.html', error=str(ex),
                               traceback=traceback.format_exc(ex))

    log.debug("Creating plot.")
    outfilename = os.path.splitext(filename)[0]
    myplot_html, myplot_png = \
        plotData_Sigma_sigma(timeString(), table, outfilename,
                             html_dir=app.config['MPLD3_FOLDER'],
                             png_dir=app.config['PNG_PLOT_FOLDER'])

    log.debug("Creating table.")
    tablecss = "table,th,td,tr,tbody {border: 1px solid black; border-collapse: collapse;}"
    write_table_jsviewer(table,
                         os.path.join(TABLE_FOLDER, '{fn}.html'.format(fn=outfilename)),
                         css=tablecss,
                         jskwargs={'use_local_files':False},
                         table_id=outfilename)

    return render_template('show_plot.html', imagename='/'+myplot_html,
                           png_imagename="/"+myplot_png,
                           tablefile='{fn}.html'.format(fn=outfilename),
                           link_pull_uploads=link_pull_uploads,
                           link_pull_database=link_pull_database,
                          )


def setup_submodule(username, remote='origin', workingdir='database/',
                    database='database', branch=None, timestamp=None):
    """
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat().replace(":","_")

    if branch is None:
        branch = '{0}_{1}'.format(username, timestamp)

    check_upstream = subprocess.check_output(['git', 'config', '--get',
                                              'remote.{remote}.url'.format(remote=remote)],
                                             cwd=workingdir)
    name = os.path.split(check_upstream)[1][:-5]
    if name != database:
        raise Exception("Error: the remote URL {0} (which is really '{2}') does not match the expected one '{1}'"
                        .format(check_upstream, database, name))

    branch_result = subprocess.call(['git','branch', '-a'], cwd=workingdir)
    print("git branch -a: ",branch_result)

    checkout_master_result = subprocess.call(['git','checkout',
                                              '{remote}/master'.format(remote=remote)],
                                             cwd=workingdir)

    if checkout_master_result != 0:
        raise Exception("Checking out the {remote}/master branch in the database failed.  "
                        "Try 'cd {workingdir}; git checkout {remote}/master'"
                        .format(remote=remote, workingdir=workingdir))

    checkout_result = subprocess.call(['git','checkout','-b', branch,
                                       '{remote}/master'.format(remote=remote)],
                                      cwd=workingdir)
    if checkout_result != 0:
        raise Exception("Checking out a new branch in the database failed.  "
                        "Attempted to checkout branch {0} in {1}"
                        .format(branch, workingdir))

    return branch, timestamp

def commit_change_to_database(username, remote='origin',
                              tablename='merged_table.ipac',
                              workingdir='database/', database='database',
                              branch=None, timestamp=None, retry=10):
    """
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat().replace(":","_")

    if branch is None:
        re.compile('[A-Za-z0-9]_')
        branch = '{0}_{1}'.format(re.sub("", username), timestamp)

    check_upstream = subprocess.check_output(['git', 'config', '--get',
                                              'remote.{remote}.url'.format(remote=remote)],
                                             cwd=workingdir)
    name = os.path.split(check_upstream)[1][:-5]
    if name != database:
        raise Exception("Error: the remote URL {0} (which is really '{2}') does not match the expected one '{1}'"
                        .format(check_upstream, database, name))

    add_result = subprocess.call(['git','add',tablename], cwd=workingdir)
    if add_result != 0:
        raise Exception("Adding {tablename} to the commit failed in {cwd}."
                        .format(tablename=tablename, cwd=workingdir))

    print("Staged diff")
    # diff checking with --cached includes staged files
    diff_result = subprocess.check_output(['git','diff', '--cached'],
                                          cwd=workingdir)
    # if there is no difference, it is not possible to commit
    if diff_result == '':
        checkout_master(remote, workingdir)
        raise Exception("No difference was detected between the input branch "
                        "of {0} ard the master after staging."
                        "  Possibly the submitted data "
                        "file contains no data.".format(workingdir))

    commit_result = subprocess.call(['git','commit','-m',
                      'Add changes to table from {0} at {1}'.format(username,
                                                                    timestamp)],
                     cwd=workingdir)
    if commit_result != 0:
        raise Exception("Committing the new branch failed")

    push_result = subprocess.call(['git','push', remote, branch,], cwd=workingdir)
    if push_result != 0:
        raise Exception("Pushing to the remote {0} folder failed".format(workingdir))

    # Check that pushing succeeded
    api_url_branch = 'https://api.github.com/repos/camelot-project/{0}/branches/{1}'.format(database,branch)
    for ii in range(retry):
        branch_exists = requests.get(api_url_branch)
        if branch_exists.ok:
            break
        else:
            time.sleep(0.1)
    branch_exists.raise_for_status()

    checkout_master(remote, workingdir)

    return branch,timestamp

def checkout_master(remote, workingdir):
    checkout_master_result = subprocess.call(['git','checkout',
                                              '{remote}/master'.format(remote=remote)],
                                             cwd=workingdir)
    if checkout_master_result != 0:
        raise Exception("Checking out the {remote}/master branch in the database failed.  "
                        "This will prevent future uploads from working, which is bad!!"
                        .format(remote=remote, workingdir=workingdir))

def pull_request(branch, user, timestamp, database='database', retry=5):
    """
    WIP: Eventually, we want each file to be uploaded to github and submitted
    as a pull request when people submit their data

    This will be tricky: we need to have a "replace existing file" logic in
    addition to the original submission.  We also need an account + API_KEY
    etc, which may be the most challenging part.

    https://developer.github.com/v3/pulls/#create-a-pull-request
    """


    S = requests.Session()
    S.headers['User-Agent']= 'camelot-project '+S.headers['User-Agent']
    password = keyring.get_password('github', git_user)
    if password is None:
        password = os.getenv('GITHUB_PASSWORD')
    if password is None:
        raise Exception("No password specified for the submitter account.  "
                        "Configure your server to use either keyring or the "
                        "appropriate environmental variable")
    #S.get('https://api.github.com/', data={'access_token':'e4942f7d7cc9468ffd0e'})

    data = {
      "title": "New data table from {user}".format(user=user),
      "body": "Data table added by {user} at {timestamp}".format(user=user, timestamp=timestamp),
      "head": "camelot-project:{0}".format(branch),
      "base": "master"
    }


    api_url_branch = 'https://api.github.com/repos/camelot-project/{0}/branches/{1}'.format(database,branch)
    branch_exists = S.get(api_url_branch)
    if (not branch_exists.ok):
        for ii in range(retry):
            branch_exists = S.get(api_url_branch)
            if branch_exists.ok:
                break

    branch_exists.raise_for_status()

    api_url = 'https://api.github.com/repos/camelot-project/{0}/pulls'.format(database)
    response = S.post(url=api_url, data=json.dumps(data), auth=(git_user, password))
    response.raise_for_status()
    pull_url = response.json()['html_url']

    return response, pull_url

def handle_duplicates(table, merged_table, duplicates):
    print("TODO: DO SOMETHING HERE (handle duplicates)")

@app.route('/query_form')
def query_form(filename="merged_table.ipac"):

    table = Table.read(os.path.join(app.config['DATABASE_FOLDER'], filename), format='ascii.ipac')

    tolerance=1.2

    sd = np.ma.masked_where(table['SurfaceDensity']==0, table['SurfaceDensity'])
    vd = np.ma.masked_where(table['VelocityDispersion']==0, table['VelocityDispersion'])
    rd = np.ma.masked_where(table['Radius']==0, table['Radius'])

    min_values=[np.round(min(sd)/tolerance,4),
                np.round(min(vd)/tolerance,4),
                np.round(min(rd)/tolerance,4)]

    max_values=[np.round(max(table['SurfaceDensity'])*tolerance,1),
                np.round(max(table['VelocityDispersion'])*tolerance,1),
                np.round(max(table['Radius'])*tolerance,1)]

    usetable = table[use_column_names]

    best_matches = {difflib.get_close_matches(vcn, usetable.colnames,  n=1,
                                              cutoff=0.4)[0]: vcn
                    for vcn in use_column_names
                    if any(difflib.get_close_matches(vcn, usetable.colnames, n=1, cutoff=0.4))
                   }

    best_column_names = [best_matches[colname] if colname in best_matches else 'Ignore'
                         for colname in usetable.colnames]

    return render_template("query_form.html", table=table, usetable=usetable,
                           use_units=use_units, filename=filename,
                           use_column_names=use_column_names,
                           best_column_names=best_column_names,
                           min_values=min_values,
                           max_values=max_values
                          )

def clearOutput() :

    for fl in glob.glob(os.path.join(app.config['MPLD3_FOLDER'], FigureStrBase+"*.png")):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

    for fl in glob.glob(os.path.join(app.config['TABLE_FOLDER'], TableStrBase+"*.ipac")):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

    for fl in glob.glob(os.path.join(app.config['MPLD3_FOLDER'], FigureStrBase+"*.html")):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

def timeString():
    TimeString=datetime.now().strftime("%Y%m%d%H%M%S%f")
    return TimeString

@app.route('/query/<path:filename>', methods=['POST'])
def query(filename, fileformat=None):
    SurfMin = float(request.form['SurfaceDensity_min'])*u.Unit(request.form['SurfaceDensity_unit'])
    SurfMax = float(request.form['SurfaceDensity_max'])*u.Unit(request.form['SurfaceDensity_unit'])
    VDispMin = float(request.form['VelocityDispersion_min'])*u.Unit(request.form['VelocityDispersion_unit'])
    VDispMax = float(request.form['VelocityDispersion_max'])*u.Unit(request.form['VelocityDispersion_unit'])
    RadMin = float(request.form['Radius_min'])*u.Unit(request.form['Radius_unit'])
    RadMax = float(request.form['Radius_max'])*u.Unit(request.form['Radius_unit'])

    ShowObs=(request.form['ObsSimBoth'] == 'IsObserved') or (request.form['ObsSimBoth'] == 'IsObsSim')
    ShowSim=(request.form['ObsSimBoth'] == 'IsSimulated') or (request.form['ObsSimBoth'] == 'IsObsSim')
    ShowGal=(request.form['GalExgalBoth'] == 'IsGalactic') or (request.form['GalExgalBoth'] == 'IsGalExgal')
    ShowExgal=(request.form['GalExgalBoth'] == 'IsExtragalactic') or (request.form['GalExgalBoth'] == 'IsGalExgal')

    NQuery=timeString()

    clearOutput()

    table = Table.read(os.path.join(app.config['DATABASE_FOLDER'], filename), format='ascii.ipac')
    set_units(table)
    Author = table['Names']
    Run = table['IDs']
    SurfDens = table['SurfaceDensity']
    VDisp = table['VelocityDispersion']
    Rad = table['Radius']
    IsSim = (table['IsSimulated'] == 'True')

    temp_table = [table[index].index for index, (surfdens, vdisp, radius) in
                  enumerate(zip(table['SurfaceDensity'],
                                table['VelocityDispersion'],
                                table['Radius']))
                  if (SurfMin < surfdens*table['SurfaceDensity'].unit < SurfMax
                      and VDispMin < vdisp*table['VelocityDispersion'].unit < VDispMax
                      and RadMin < radius*table['Radius'].unit < RadMax)
                 ]
    use_table = table[temp_table]

    if not ShowObs :
        temp_table = [use_table[h].index for h,i in
                      zip(range(len(use_table)),use_table['IsSimulated'])
                      if i == 'False']
        use_table.remove_rows(temp_table)

    if not ShowSim :
        temp_table = [use_table[h].index for h,i in
                      zip(range(len(use_table)),use_table['IsSimulated'])
                      if i == 'True']
        use_table.remove_rows(temp_table)

    if not ShowGal :
        temp_table = [use_table[h].index for h,i in
                      zip(range(len(use_table)),use_table['IsGalactic'])
                      if i == 'True']
        use_table.remove_rows(temp_table)

    if not ShowExgal :
        temp_table = [use_table[h].index for h,i in
                      zip(range(len(use_table)),use_table['IsGalactic'])
                      if i == 'False']
        use_table.remove_rows(temp_table)

    tablefile = os.path.join(app.config['TABLE_FOLDER'], TableStrBase+NQuery+'.ipac')

    use_table.write(tablefile, format='ipac')

    myplot_html, myplot_png = \
        plotData_Sigma_sigma(NQuery, use_table, FigureStrBase,
                             SurfMin=SurfMin, SurfMax=SurfMax,
                             VDispMin=VDispMin, VDispMax=VDispMax,
                             RadMin=RadMin, RadMax=RadMax,
                             html_dir=app.config['MPLD3_FOLDER'],
                             png_dir=app.config['PNG_PLOT_FOLDER'])

    # It is possible to create an empty query
    if myplot_html is None or myplot_png is None:
        return render_template('error.html',
                               error="No data were found matching your query.",
                               traceback="",
                              )

    return render_template('show_plot.html', imagename='/'+myplot_html,
                           png_imagename="/"+myplot_png,
                           tablefile=tablefile)

@app.route('/query/static/jstables/<path:path>')
def send_js(path):
    return send_from_directory('static/jstables/', path)

@app.before_first_request
def setup_authenticate_with_github():
    """
    Authenticate using https with github after configuring git locally to store
    credentials etc.
    """

    # Only run the configuration on the heroku app
    if os.getenv('HEROKU_SERVER') != 'camelot-project.herokuapp.com':
        # but do the checking no matter what
        return check_authenticate_with_github()

    import shutil
    shutil.rmtree('uploads')
    shutil.rmtree('database')
    clone_result_database = subprocess.call(['git', 'clone',
                                             'https://github.com/camelot-project/database.git',
                                             'database'])
    assert clone_result_database == 0
    clone_result_uploads = subprocess.call(['git', 'clone',
                                             'https://github.com/camelot-project/uploads.git',
                                             'uploads'])
    assert clone_result_uploads == 0

    config_result_1 = subprocess.call(['git', 'config', '--global',
                                       'credential.https://github.com.{user}'.format(user=git_user),
                                       git_user])
    assert config_result_1 == 0
    config_result_2 = subprocess.call(['git', 'config', '--global',
                                       'credential.helper',
                                       'store'])
    assert config_result_2 == 0
    config_result_3 = subprocess.call(['git', 'config', '--global',
                                       'user.email',
                                       submitter_gmail])
    assert config_result_3 == 0
    config_result_4 = subprocess.call(['git', 'config', '--global',
                                       'user.name',
                                       git_user])
    assert config_result_4 == 0

    import netrc
    nrcfile = os.path.join(os.environ['HOME'], ".netrc")
    if not os.path.isfile(nrcfile):
        # "touch" it
        with open(nrcfile, 'a'):
            os.utime(nrcfile, None)

    nrc = netrc.netrc(nrcfile)
    if not nrc.authenticators('https://github.com'):
        with open(nrcfile, 'r') as f:
            nrcdata = f.read()

        password = keyring.get_password('github', git_user)
        if password is None:
            password = os.getenv('GITHUB_PASSWORD')

        with open(nrcfile, 'w') as f:
            f.write(nrcdata)
            f.write("""
machine github.com
  login {gmail}
  password {password}
machine https://github.com
  login {gmail}
  password {password}""".format(password=password, gmail=submitter_gmail))

    nrc = netrc.netrc(nrcfile)
    print(nrc)

    return check_authenticate_with_github()

def check_authenticate_with_github():
    """
    Check that fetch permissions are set up for the upload and database
    directories
    """
    fetch_uploads = subprocess.call(['git', 'fetch'], cwd='uploads/')
    assert fetch_uploads == 0
    fetch_database = subprocess.call(['git', 'fetch'], cwd='database/')
    assert fetch_database == 0
    print("Fetching uploads and database worked.")

def cleanup_git_directory(directory='database/', delete_untracked=False,
                          allow_fail=True):

    uncommitted_files = subprocess.call(['git','diff-files','--quiet'], cwd=directory)
    if uncommitted_files:
        log.debug("Found uncommitted file changes in {0}.".format(directory))
        reset = subprocess.call(['git','reset','--hard','HEAD'], cwd=directory)
        if allow_fail:
            assert reset == 0

        if delete_untracked:
            untracked_deleted = subprocess.call(['git','clean','-f'], cwd=directory)
            if allow_fail:
                assert untracked_deleted == 0

    uncommited_staged_changes = subprocess.call(['git','diff-index','--quiet','--cached','HEAD'], cwd=directory)
    if uncommited_staged_changes:
        log.debug("Found uncommitted, staged changes in {0}.".format(directory))
        reset = subprocess.call(['git','reset','--hard','HEAD'], cwd=directory)
        if allow_fail:
            assert reset == 0

@app.route('/update_database')
def update_database():
    """
    Pull the latest database/master
    """
    fetch_database = subprocess.call(['git', 'fetch'], cwd='database/')
    assert fetch_database == 0
    pull_database = subprocess.call(['git', 'pull', 'origin', 'master'], cwd='database/')
    assert pull_database == 0
    commit_hash = subprocess.check_output(['git','rev-parse','HEAD'], cwd='database/').strip()
    commit_name = subprocess.check_output(['git','rev-parse','--abbrev-ref','HEAD'], cwd='database/').strip()

    cleanup_git_directory('database/')
    cleanup_git_directory('uploads/')

    S = requests.Session()
    S.headers['User-Agent']= 'camelot-project '+S.headers['User-Agent']

    apiroot = 'https://api.github.com/'
    api_pulls = '{apiroot}repos/camelot-project/database/pulls'.format(apiroot=apiroot)
    pulls_result = S.get(api_pulls, params={'state':'closed'})
    pulls_result.raise_for_status()

    api_commits = '{apiroot}repos/camelot-project/database/commits'.format(apiroot=apiroot)
    commits_result = S.get(api_commits)
    commits_result.raise_for_status()

    data = json.loads(pulls_result.content)
    data_commits = json.loads(commits_result.content)

    api_last_commit_url = data_commits[0]['commit']['url']
    api_last_commit_info = S.get(api_last_commit_url)
    data_last_commit = json.loads(api_last_commit_info.content)
    last_commit_url = data_last_commit['html_url']

    last_commit_hash = data_last_commit['sha']

    if last_commit_hash != commit_hash:
        commit_disagree_message = (
                                   "The hashes github: {0} and server: {1} "
                                   "don't match; the "
                                   "server database is not up to date with the "
                                   "github database.  This is a significant "
                                   "error and should be reported."
                                   .format(last_commit_hash, commit_hash))
        cls = 'red'
    else:
        commit_disagree_message = (
                                   "The server version of the database matches "
                                   "that on github.  All is well!")
        cls = 'green'

    return render_template("updated_database.html",
                           last_pull=data_commits[0]['commit']['message'],
                           last_commit_url=last_commit_url,
                           last_commit_hash=last_commit_hash,
                           last_pull_number=data[0]['number'],
                           commit_hash=commit_hash,
                           commit_name=commit_name,
                           commit_disagree_message=commit_disagree_message,
                           cls=cls,
                          )

def handle_email(email, filename):
    form_url = 'https://docs.google.com/forms/d/1nzdc8jOMlwZEYqdJSvNo6B60gNrUZ9trrhUeYRtUM8g/formResponse'

    S = requests.Session()
    S.headers['User-Agent']= 'camelot-project '+S.headers['User-Agent']

    response = S.post(form_url, params={'entry.151369084': email,
                                        'entry.1302661889': filename})
    response.raise_for_status()


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

@app.route('/version')
def version():
    # WIP: does not work because heroku's app is not a git repo
    git_id = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
    git_database_id = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd='database/')

    return git_id, git_database_id

if __name__ == '__main__':
    if os.getenv('HEROKU_SERVER'):
        app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT')))
    else:
        app.run(debug=True)
