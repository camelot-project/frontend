import os
import glob
import numpy as np
import scipy
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import datetime
import time
import random
import astropy
from astropy.io import fits
from astropy import units as u
from astropy import table
import mpld3
from mpld3 import plugins
import pdb
matplotlib.rcParams['figure.figsize'] = (12,8)

css = """
table
{
  border-collapse: collapse;
}
th
{
  color: #ffffff;
  background-color: #000000;
}
td
{
  background-color: #cccccc;
}
table, th, td
{
  font-family:Arial, Helvetica, sans-serif;
  border: 1px solid black;
  text-align: right;
}
"""


def plotData(NQuery, input_table, FigureStrBase, SurfMin=1e-1*u.M_sun/u.pc**2,
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
    if interactive:
        from matplotlib import pyplot
        from matplotlib import _pylab_helpers
        backend = getattr(matplotlib.backends, 'backend_{0}'.format(matplotlib.rcParams['backend']).lower())
        # backend = getattr(matplotlib.backends, 'backend')
        canvas = backend.FigureCanvas(figure)
        figmanager = backend.FigureManager(canvas, 1)
        # canvas = matplotlib.backend_bases.FigureCanvas(figure)
        # figmanager = matplotlib.backend_bases.FigureManagerBase(canvas, 1)
        figmanager.canvas.figure.number = 1
        _pylab_helpers.Gcf.set_active(figmanager)
    else:
        canvas = FigureCanvasAgg(figure)
    ax = figure.gca()

    d = input_table
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

    UniqueAuthor = list(set(Author[Use]))[4]
    NUniqueAuthor = len(UniqueAuthor)

    #print d
    #print d[Use]
    # print 'Authors:', UniqueAuthor

    #colors = random.sample(matplotlib.colors.cnames, NUniqueAuthor)
    colors = list(matplotlib.cm.jet(np.linspace(0,1,NUniqueAuthor)))
    random.shuffle(colors)

    # NOTE this does NOT work with mpld3
    # ax.loglog()

    scatters = []
    labels = []

    markers = ['o', 's']
    for iAu,color in zip(UniqueAuthor, colors) :
        UsePlot = (Author == iAu) & Use
        ObsPlot = ((Author == iAu) & (~IsSim)) & Use
        SimPlot = ((Author == iAu) & (IsSim)) & Use

        if any(ObsPlot):
            print iAu
            scatters.append(ax.scatter(np.log10(SurfDens[ObsPlot]), np.log10(VDisp[ObsPlot]),
                        marker=markers[0],
                        s=(np.log10(np.array(Rad[ObsPlot]))-np.log10(RadMin.value)+0.5)**3.,
                        color=color, alpha=0.5))

            # for row in d[ObsPlot]:
            #     row_html = [str(j) for j in d[ObsPlot].pformat(html=True)]
            #     labels.append("\n ".join(row_html))
            labels = ['<h1>{title}</h1>'.format(title=i) for i in range(len(d[ObsPlot]))]

        if any(SimPlot):
            scatters.append(ax.scatter(np.log10(SurfDens[SimPlot]), np.log10(VDisp[SimPlot]),
                        marker=markers[1],
                        s=(np.log10(np.array(Rad[SimPlot]))-np.log10(RadMin.value)+0.5)**3.,
                        color=color, alpha=0.5))

            # for row in d[SimPlot]:
            #     row_html = [str(j) for j in d[SimPlot].pformat(html=True)]

            #     labels.append("\n ".join(row_html))

    if any(Obs):
        ax.scatter(np.log10(SurfDens[Obs]), np.log10(VDisp[Obs]),
                    marker=markers[0],
                    s=(np.log10(np.array(Rad[Obs]))-np.log10(RadMin.value)+0.5)**3.,
                    facecolors='none', edgecolors='black',
                    alpha=0.5)

    if any(Sim):
        ax.scatter(np.log10(SurfDens[Sim]), np.log10(VDisp[Sim]),
                    marker=markers[1],
                    s=(np.log10(np.array(Rad[Sim]))-np.log10(RadMin.value)+0.5)**3.,
                    facecolors='none', edgecolors='black',
                    alpha=0.5)

    ax.set_xlabel('$\Sigma$ [M$_{\odot}$ pc$^{-2}$]', fontsize=16)
    ax.set_ylabel('$\sigma$ [km s$^{-1}$]', fontsize=16)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    ax.set_xlim((np.log10(SurfMin.to(u.M_sun/u.pc**2).value),
                 np.log10(SurfMax.to(u.M_sun/u.pc**2).value)))
    ax.set_ylim((np.log10(VDispMin.to(u.km/u.s).value),
                 np.log10(VDispMax.to(u.km/u.s).value)))

    # ax.legend(UniqueAuthor, loc='center left', bbox_to_anchor=(1.0, 0.5),
    #           prop={'size':12}, markerscale = .7, scatterpoints = 1)

    labels = ['<h1>{title}</h1>'.format(title=i) for i in range(len(d))]

    tooltip = plugins.PointHTMLTooltip(scatters[0], labels,
                                   voffset=10, hoffset=10)
    plugins.connect(figure, tooltip)

    # figure.savefig(FigureStrBase+NQuery+'.png',bbox_inches='tight',dpi=150)
    # figure.savefig(FigureStrBase+NQuery+'.pdf',bbox_inches='tight',dpi=150)

    if interactive:
        # from matplotlib import pyplot as plt
        # plt.ion()
        # plt.show()

        mpld3.show()

    return FigureStrBase+NQuery+'.png'

def clearPlotOutput(FigureStrBase,TooOld) :

    for fl in glob.glob(FigureStrBase+"*.png") + glob.glob(FigureStrBase+"*.pdf"):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

def timeString() :

    TimeString=datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return TimeString

if __name__ == "__main__":

    SurfMin = 1e-1*u.M_sun/u.pc**2
    SurfMax = 1e5*u.M_sun/u.pc**2
    VDispMin = 1e-1*u.km/u.s
    VDispMax = 3e2*u.km/u.s
    RadMin = 1e-2*u.pc
    RadMax = 1e3*u.pc

    NQuery=timeString()
    FigureStrBase='Output_Sigma_sigma_r_'
    TooOld=300

    clearPlotOutput(FigureStrBase,TooOld)

    d = table.Table.read("/Users/eric/Dropbox/Florence-Workshop/hands_on_before_Florence_yay/merged_table.ipac", format='ascii.ipac')

    html = plotData(NQuery,d, FigureStrBase,SurfMin,SurfMax,VDispMin,VDispMax,RadMin,RadMax)

    # d.show_in_browser(jsviewer=True)
