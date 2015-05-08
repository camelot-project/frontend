import numpy as np
from astropy.io import fits
from astropy.io import ascii
from astropy import table
from astropy import units as u

jimdale = ascii.read('Sigma_sigma_R_jimdale.txt')
erikkoch = fits.getdata('simsprops_expanded.fits')
andreagianetti = ascii.read('Gianetti_metadata_head.csv')
simonglover = ascii.read('simonglover.csv')

surfdens = table.Column(data=np.concatenate([(jimdale['surfdens']*u.g/u.cm**2).to(u.M_sun/u.pc**2).value,
                                             (andreagianetti['sigma']*u.g/u.cm**2).to(u.M_sun/u.pc**2).value,
                                             (np.array(erikkoch['SurfDens'], dtype='float')*u.M_sun/u.pc**2).value,
                                             simonglover['surfdens'],
                        ])*u.M_sun/u.pc**2
                       )
sigma = table.Column(data=np.concatenate([jimdale['velocitydispersion'],
                                          andreagianetti['velo_disp'],
                                          np.array(erikkoch['VDisp'], dtype='float'),
                                          simonglover['vdisp'],
                     ])*u.km/u.s
                    )
radius = table.Column(data=np.concatenate([jimdale['radius'],
                                           andreagianetti['radius'],
                                           np.array(erikkoch['Radius'], dtype='float'),
                                           simonglover['radius'],
                      ])*u.pc
                     )
ids = table.Column(data=list(jimdale['runid'])+
                    list(andreagianetti['Clump_name'])+
                    list(erikkoch['Sim']+erikkoch['TStep'])+
                    list(simonglover['id'])
                   )
names = table.Column(data=['JimDale']*len(jimdale) +
                     ['AndreaGianetti']*len(andreagianetti) + 
                     ['ErikKoch']*len(erikkoch) + 
                     ['SimonGlover']*len(simonglover)
                    )

tbl = table.Table(data=[names,ids,surfdens,sigma,radius],
                  names=['Names','IDs','SurfaceDensity','VelocityDispersion','Radius'])

tbl.write("merged_table.ipac", format='ascii.ipac')

# Good ways to inspect the data:
# tbl.pprint()
# tbl.show_in_browser()
# tbl.show_in_browser(jsviewer=True)
