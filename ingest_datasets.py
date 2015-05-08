import numpy as np
import astropy
from distutils.version import LooseVersion

if LooseVersion(astropy.__version__) < LooseVersion('1.0.0'):
    raise Exception("Your version of astropy is out of date.  Please update "
                    "to at least version >=1.0.")
if LooseVersion(np.__version__) < LooseVersion('1.6'):
    raise Exception("Your version of numpy is out of date.  Please update "
                    "to at least version >=1.6.")

from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy import units as u
from ingest_datasets_better import fix_logical,rename_columns,set_units,add_name_column,append_table,reorder_columns

jimdale = ascii.read('Sigma_sigma_R_jimdale.txt')
erickoch = fits.getdata('simsprops_expanded.fits')
andreagianetti = ascii.read('Gianetti_metadata_head.csv')
simonglover = ascii.read('simonglover.csv')
diederikkruijssen = ascii.read('kruijssen_Brick.csv')
stevelongmore = ascii.read('Longmore_CMZ_clouds.csv')

surfdens = table.Column(data=np.concatenate([(jimdale['surfdens']*u.g/u.cm**2).to(u.M_sun/u.pc**2).value,
                                             (andreagianetti['sigma']*u.g/u.cm**2).to(u.M_sun/u.pc**2).value,
                                             (np.array(erickoch['SurfDens'], dtype='float')*u.M_sun/u.pc**2).value,
                                             simonglover['surfdens'],
                                             diederikkruijssen['SurfDens'],
                                             stevelongmore['SurfDens']
                        ])*u.M_sun/u.pc**2
                       )
sigma = table.Column(data=np.concatenate([jimdale['velocitydispersion'],
                                          andreagianetti['velo_disp'],
                                          np.array(erickoch['VDisp'], dtype='float'),
                                          simonglover['vdisp'],
                                          diederikkruijssen['VDisp'],
                                          stevelongmore['VDisp']
                     ])*u.km/u.s
                    )
radius = table.Column(data=np.concatenate([jimdale['radius'],
                                           andreagianetti['radius'],
                                           np.array(erickoch['Radius'], dtype='float'),
                                           simonglover['radius'],
                                           diederikkruijssen['Rad'],
                                           stevelongmore['Rad']
                      ])*u.pc
                     )
ids = table.Column(data=list(jimdale['runid'])+
                    list(andreagianetti['Clump_name'])+
                    list(erickoch['Sim']+erickoch['TStep'])+
                    list(simonglover['id'])+
                    list(diederikkruijssen['ID'])+
                    list(stevelongmore['ID'])
                   )
names = table.Column(data=['JimDale']*len(jimdale) +
                     ['AndreaGianetti']*len(andreagianetti) + 
                     ['EricKoch']*len(erickoch) + 
                     ['SimonGlover']*len(simonglover) +
                     ['DiederikKruijssen']*len(diederikkruijssen) +
                     ['SteveLongmore']*len(stevelongmore)
                    )
is_sim = table.Column(data=[True]*len(jimdale) +
                     [False]*len(andreagianetti) + 
                     [True]*len(erickoch) + 
                     [True]*len(simonglover) +
                     [True]*len(diederikkruijssen) +
                     [False]*len(stevelongmore) # I don't believe you.  =) # Ha ha ;)
                    )


tbl = table.Table(data=[names,ids,surfdens,sigma,radius,is_sim],
                  names=['Names','IDs','SurfaceDensity','VelocityDispersion','Radius','IsSimulated'])

benoitcommercon = fix_logical(ascii.read('benoitcommercon.csv'))
rename_columns(benoitcommercon)
set_units(benoitcommercon)
add_name_column(benoitcommercon, 'BenoitCommercon')
benoitcommercon = reorder_columns(benoitcommercon, tbl.colnames)
append_table(tbl, benoitcommercon)

carabattersby = fix_logical(ascii.read('carabattersby.csv'))
rename_columns(carabattersby)
set_units(carabattersby)
add_name_column(carabattersby, 'CaraBattersby')
carabattersby = reorder_columns(carabattersby, tbl.colnames)
append_table(tbl, carabattersby)

adamginsburg = fix_logical(ascii.read('adamginsburg_bgps.csv'))
rename_columns(adamginsburg, mapping={'name':'IDs',
                                      'columndensity':'SurfaceDensity',
                                      'widthhcop':'VelocityDispersion',
                                      'radius_20':'Radius'})
set_units(adamginsburg, units={'SurfaceDensity':u.M_sun/u.pc**2,
                          'VelocityDispersion':u.km/u.s,
                          'Radius':u.pc})
add_name_column(adamginsburg, 'AdamGinsburg')
adamginsburg.add_column(table.Column(data=[False]*len(adamginsburg), name='IsSimulated'))
adamginsburg = reorder_columns(adamginsburg, tbl.colnames)
append_table(tbl, adamginsburg)

tbl.write("merged_table.ipac", format='ascii.ipac')

# Good ways to inspect the data:
# tbl.pprint()
# tbl.show_in_browser()
# tbl.show_in_browser(jsviewer=True)
