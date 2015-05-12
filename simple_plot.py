import os
import glob
import numpy as np
import scipy
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
matplotlib.use('Agg')
import datetime
import time
import random
import astropy
from astropy.io import fits
from astropy import units as u
from astropy import table
#import bokeh.mpl
#import mpld3
matplotlib.rcParams['figure.figsize'] = (12,8)

def plotData(NQuery, table, FigureStrBase, SurfMin=1e-1*u.M_sun/u.pc**2,
             SurfMax=1e5*u.M_sun/u.pc**2, VDispMin=1e-1*u.km/u.s,
             VDispMax=3e2*u.km/u.s, RadMin=1e-2*u.pc, RadMax=1e3*u.pc,
             interactive=True):
 
    """
    This is where documentation needs to be added

    Parameters
    ----------
    NQuery
    FigureStrBase : str
        The start of the output filename, e.g. for "my_file.png" it would be
        my_file
    SurfMin
    SurfMax
    VDispMin
    VDispMax
    RadMin
    RadMax
    """
    
    figure = matplotlib.figure.Figure()
    canvas = FigureCanvasAgg(figure)
    ax = figure.gca()

    # d = table.Table.read("merged_table.ipac", format='ascii.ipac')
    d = table
    Author = d['Names']
    Run = d['IDs']
    SurfDens = d['SurfaceDensity']
    VDisp = d['VelocityDispersion']
    Rad = d['Radius']
    if d['IsSimulated'].dtype == 'bool':
        IsSim = d['IsSimulated']
    else:
        IsSim = d['IsSimulated'] == 'True'
    
    UseSurf = (SurfDens > SurfMin) & (SurfDens < SurfMax)
    UseVDisp = (VDisp > VDispMin) & (VDisp < VDispMax)
    UseRad = (Rad > RadMin) & (Rad < RadMax)
    Use = UseSurf & UseVDisp & UseRad
    Obs = (~IsSim) & Use
    Sim = IsSim & Use
    
    UniqueAuthor = set(Author[Use])
    NUniqueAuthor = len(UniqueAuthor)
    
    #print d
    #print d[Use]
    #print 'Authors:', UniqueAuthor
    
    #colors = random.sample(matplotlib.colors.cnames, NUniqueAuthor)
    colors = list(matplotlib.cm.jet(np.linspace(0,1,NUniqueAuthor)))
    random.shuffle(colors)
    
    ax.loglog()
    markers = ['o','s']
    for iAu,color in zip(UniqueAuthor,colors) :
        UsePlot = (Author == iAu) & Use
        ObsPlot = ((Author == iAu) & (~IsSim)) & Use 
        SimPlot = ((Author == iAu) & (IsSim)) & Use
        if any(ObsPlot):
            ax.scatter(SurfDens[ObsPlot], VDisp[ObsPlot], marker=markers[0],
                        s=(np.log(np.array(Rad[ObsPlot]))-np.log(np.array(RadMin))+0.5)**3.,
                        color=color, alpha=0.5)
        if any(SimPlot):
            ax.scatter(SurfDens[SimPlot], VDisp[SimPlot], marker=markers[1],
                        s=(np.log(np.array(Rad[SimPlot]))-np.log(np.array(RadMin))+0.5)**3.,
                        color=color, alpha=0.5)
    if any(Obs):
        ax.scatter(SurfDens[Obs], VDisp[Obs], marker=markers[0],
                    s=(np.log(np.array(Rad[Obs]))-np.log(np.array(RadMin))+0.5)**3.,
                    facecolors='none', edgecolors='black',
                    alpha=0.5)
    if any(Sim):
        ax.scatter(SurfDens[Sim], VDisp[Sim], marker=markers[1],
                    s=(np.log(np.array(Rad[Sim]))-np.log(np.array(RadMin))+0.5)**3.,
                    facecolors='none', edgecolors='black',
                    alpha=0.5)
    ax.set_xlabel('$\Sigma$ [M$_{\odot}$ pc$^{-2}$]', fontsize=16)
    ax.set_ylabel('$\sigma$ [km s$^{-1}$]', fontsize=16)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    #html_bokeh = bokeh.mpl.to_bokeh(fig=figure, name="bokeh_"+FigureStrBase+NQuery)
    #html = mpld3.fig_to_html(figure)
    #with open("mpld3_"+FigureStrBase+NQuery+'.html','w') as f:
    #    f.write(html)

    ax.set_xlim((SurfMin.to(u.M_sun/u.pc**2).value,SurfMax.to(u.M_sun/u.pc**2).value))
    ax.set_ylim((VDispMin.to(u.km/u.s).value,VDispMax.to(u.km/u.s).value))

    # Put a legend to the right of the current axis
    ax.legend(UniqueAuthor, loc='center left', bbox_to_anchor=(1.0, 0.5), prop={'size':12}, markerscale = .7, scatterpoints = 1)

    figure.savefig(FigureStrBase+NQuery+'.png',bbox_inches='tight',dpi=150)
    figure.savefig(FigureStrBase+NQuery+'.pdf',bbox_inches='tight',dpi=150)

    if interactive:
        from matplotlib import pyplot as plt
        plt.ion()
        plt.show()

    return FigureStrBase+NQuery+'.png'
    
def clearPlotOutput(FigureStrBase,TooOld) :
    
    for fl in glob.glob(FigureStrBase+"*.png") + glob.glob(FigureStrBase+"*.pdf"):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)
    
def timeString() :
    
    TimeString=datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return TimeString

# NQuery=timeString()
# FigureStrBase='Output_Sigma_sigma_r_'
# TooOld=300
# 
# clearPlotOutput(FigureStrBase,TooOld)
# 
# plotData(NQuery,FigureStrBase,SurfMin,SurfMax,VDispMin,VDispMax,RadMin,RadMax)
# 
# #d.show_in_browser(jsviewer=True)
# 
# 
