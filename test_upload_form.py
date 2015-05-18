import requests
import upload_form

def test_upload_file(filename='benoitcommercon.csv',
                     username='BenoitCommercon', adsid='unknown',
                     doi='unknown', email='tester',
                     base_url='http://camelot-project.herokuapp.com'):

    S = requests.Session()
    r = S.get(base_url+"/upload_form")
    r.raise_for_status()

    with open(filename, 'rb') as f:
        r = S.post(base_url+'/upload', files={'filename':f})
    r.raise_for_status()

    jsondata = """
    id:IDs
    id_units:
    vdisp:VelocityDispersion
    vdisp_units:km/s
    surfdens:SurfaceDensity
    surfdens_units:M_sun/pc^2
    radius:Radius
    radius_units:pc
    is_sim:Ignore
    is_sim_units:
    ObsSim:IsObserved
    GalExgal:IsGalactic
    Username:{username}
    Email:{email}
    adsid:{adsid}
    doi:{doi}
    """.format(username=username, email=email, adsid=adsid, doi=doi)

    r = S.post(base_url+'/set_columns/{filename}'.format(filename), data=jsondata)
    r.raise_for_status()
