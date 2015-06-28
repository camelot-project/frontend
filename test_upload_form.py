import os
import json
import ast
import requests
from bs4 import BeautifulSoup
import github_helpers

def test_upload_file(email,
                     filename='benoitcommercon.csv',
                     username='test_BenoitCommercon', adsid='unknown_adsid',
                     doi='unknown_doi',
                     base_url='http://camelot-project.herokuapp.com'):
    """
    Submit the benoitcommercon test dataset

    Your e-mail is REQUIRED here: please submit either your email address, your
    name, or your github id.
    """

    S = requests.Session()
    r1 = S.get(base_url+"/upload_form")
    r1.raise_for_status()

    with open(filename, 'rb') as f:
        r2 = S.post(base_url+'/upload', files={'file':f, 'filename':filename})
    r2.raise_for_status()

    data = """
    {{"id":"IDs",
    "id_units":"",
    "vdisp":"VelocityDispersion",
    "vdisp_units":"km/s",
    "surfdens":"SurfaceDensity",
    "surfdens_units":"M_sun/pc^2",
    "radius":"Radius",
    "radius_units":"pc",
    "is_sim":"Ignore",
    "is_sim_units":"",
    "ObsSim":"IsObserved",
    "GalExgal":"IsGalactic",
    "Username":"{username}",
    "Email":"{email}",
    "adsid":"{adsid}",
    "doi":"{doi}",}}
    """.format(username=username, email=email, adsid=adsid, doi=doi).strip()

    dictdata = ast.literal_eval(data)
    jsondata = json.dumps(dictdata)
    print("JSON data: ",jsondata)

    r3 = S.post(base_url+'/set_columns/{filename}?testmode=True'.format(filename=filename),
                data=dictdata)
    r3.raise_for_status()

    soup = BeautifulSoup(r3.content)
    dbpull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'database/pull' in str(x)][0]
    uppull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'uploads/pull' in str(x)][0]

    db_sc = github_helpers.close_pull_request('database', dbpull)
    up_sc = github_helpers.close_pull_request('uploads', uppull)

    return S,r1,r2,r3

def test_upload_rathborne(email,
                          filename='rathborne2009_table2.ecsv',
                          username='JillRathborne',
                          adsid='2009ApJS..182..131R',
                          doi='10.1088/0067-0049/182/1/131',
                          base_url='http://camelot-project.herokuapp.com'):
    """
    Submit the Rathborne test dataset

    Your e-mail is REQUIRED here: please submit either your email address, your
    name, or your github id.
    """

    S = requests.Session()
    r1 = S.get(base_url+"/upload_form")
    r1.raise_for_status()

    with open(filename, 'rb') as f:
        r2 = S.post(base_url+'/upload', files={'file':f,
                                                          'filename':filename},
                    data={'fileformat':'ascii.ecsv'})
    r2.raise_for_status()

    data = """
    {{
    "GRSMC":"IDs",
    "GRSMC_units":"",
    "DeltaV":"VelocityDispersion",
    "DeltaV_units":"km/s",
    "NH2":"SurfaceDensity",
    "NH2_units":"2.8Da/cm^2",
    "radius":"Radius",
    "radius_units":"pc",
    "GLON":"Ignore",
    "GLON_units":"deg",
    "GLAT":"Ignore",
    "GLAT_units":"deg",
    "Vlsr":"Ignore",
    "Vlsr_units":"km / s",
    "Tmb":"Ignore",
    "Tmb_units":"K",
    "GLONc":"Ignore",
    "GLONc_units":"deg",
    "GLATc":"Ignore",
    "GLATc_units":"deg",
    "a":"Ignore",
    "a_units":"deg",
    "b":"Ignore",
    "b_units":"deg",
    "pa":"Ignore",
    "pa_units":"deg",
    "Area":"Ignore",
    "Area_units":"deg2",
    "Tav":"Ignore",
    "Tav_units":"K",
    "Ipeak":"Ignore",
    "Ipeak_units":"K km / s",
    "Itot":"Ignore",
    "Itot_units":"K km / (deg2 s)",
    "Flag":"Ignore",
    "Flag_units":"None",
    "Dist":"Ignore",
    "Dist_units":"kpc",
    "ObsSim":"IsObserved",
    "GalExgal":"IsGalactic",
    "Username":"{username}",
    "Email":"{email}",
    "adsid":"{adsid}",
    "doi":"{doi}",}}
    """.format(username=username, email=email, adsid=adsid, doi=doi).strip()

    dictdata = ast.literal_eval(data)
    jsondata = json.dumps(dictdata)
    print("JSON data: ",jsondata)

    #/set_columns/rathborne2009_table2.ecsv?fileformat=ascii.ecsv
    r3 = S.post(base_url+'/set_columns/{filename}?fileformat=ascii.ecsv&testmode=True'.format(filename=filename),
                data=dictdata)
    r3.raise_for_status()

    soup = BeautifulSoup(r3.content)
    dbpull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'database/pull' in str(x)][0]
    uppull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'uploads/pull' in str(x)][0]

    db_sc = github_helpers.close_pull_request('database', dbpull)
    up_sc = github_helpers.close_pull_request('uploads', uppull)

    return S,r1,r2,r3
