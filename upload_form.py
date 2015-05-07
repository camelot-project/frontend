import os
import numpy as np
from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy import units as u
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, jsonify
from werkzeug import secure_filename

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['fits', 'csv', 'txt'])

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

    file_ext = get_file_extension(file.filename)
    if file_ext is 'fits':
        print 'WILL READ FROM:', os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_data = fits.getdata(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print 'file_data:', file_data
    elif file_ext is 'cvs' or file_ext is 'txt':
        print 'WILL READ FROM:', os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_data = ascii.read(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print 'file_data:', file_data
    # print file_data
    return redirect(url_for('uploaded_file',
                            filename=filename))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/autocomplete',methods=['GET'])
def autocomplete():
    search = request.args.get('term')
    print os.getcwd()
    allunits = set()
    for unit in dir(u):
        if isinstance(unit, u.Unit):
            for name in unit.names:
                allunits.add(name)
    app.logger.debug(search)
    return jsonify(json_list=list(allunits))

if __name__ == '__main__':
    app.run(debug=True)
