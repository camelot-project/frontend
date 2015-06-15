import json
import ast
import requests
from bs4 import BeautifulSoup
import github_helpers

def test_upload_file(filename='benoitcommercon.csv',
                     username='test_BenoitCommercon', adsid='unknown_adsid',
                     doi='unknown_doi', email='tester_adamginsburg@gmail.com',
                     base_url='http://camelot-project.herokuapp.com'):

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

    r3 = S.post(base_url+'/set_columns/{filename}'.format(filename=filename),
               data=dictdata)
    r3.raise_for_status()

    soup = BeautifulSoup(r.content)
    dbpull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'database/pull' in str(x)][0]
    uppull = [os.path.split(x.attrs['href'])[-1]
              for x in soup.find_all('a',href=True)
              if 'uploads/pull' in str(x)][0]

    db_sc = github_helpers.close_pull_request('database', dbpull)
    up_sc = github_helpers.close_pull_request('uploads', uppull)

    return S,r1,r2,r3
