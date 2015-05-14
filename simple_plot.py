import os
import glob
import numpy as np
import matplotlib
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import datetime
import time
import random
from astropy import units as u
import mpld3
from mpld3 import plugins
import pdb

matplotlib.rcParams['figure.figsize'] = (12, 8)

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


def plotData_Sigma_sigma(NQuery, table, FigureStrBase,
                         SurfMin=1e-1*u.M_sun/u.pc**2,
                         SurfMax=1e5*u.M_sun/u.pc**2,
                         VDispMin=1e-1*u.km/u.s,
                         VDispMax=3e2*u.km/u.s,
                         RadMin=1e-2*u.pc,
                         RadMax=1e3*u.pc,
                         interactive=False):
    """
    SurfMin
    SurfMax
    VDispMin
    VDispMax
    RadMin
    RadMax
    """
    return plotData(NQuery, table, FigureStrBase,
                    variables=('SurfaceDensity',
                               'VelocityDispersion',
                               'Radius'),
                    xMin=SurfMin,
                    xMax=SurfMax,
                    yMin=VDispMin,
                    yMax=VDispMax,
                    zMin=RadMin,
                    zMax=RadMax,
                    interactive=interactive)


def plotData(NQuery, input_table, FigureStrBase, variables, xMin, xMax,
             yMin, yMax, zMin, zMax, interactive=False, show_log=True):
    """
    This is where documentation needs to be added

    Parameters
    ----------
    NQuery
    FigureStrBase : str
        The start of the output filename, e.g. for "my_file.png" it would be
        my_file
    xMin
    xMax
    yMin
    yMax
    zMin
    zMax
    """

    figure = matplotlib.figure.Figure()
    if interactive:
        from matplotlib import pyplot
        from matplotlib import _pylab_helpers
        backend = getattr(matplotlib.backends, 'backend_{0}'.format(matplotlib.rcParams['backend']).lower())
        canvas = backend.FigureCanvas(figure)
        figmanager = backend.FigureManager(canvas, 1)
        figmanager.canvas.figure.number = 1
        _pylab_helpers.Gcf.set_active(figmanager)
    else:
        figure = matplotlib.figure.Figure()
        canvas = FigureCanvasAgg(figure)
    ax = figure.gca()

    d = input_table
    Author = d['Names']
    Run = d['IDs']
    x_ax = d[variables[0]]
    y_ax = d[variables[1]]
    z_ax = d[variables[2]]
    if d['IsSimulated'].dtype == 'bool':
        IsSim = d['IsSimulated']
    else:
        IsSim = d['IsSimulated'] == 'True'

    label_dict = \
        {'SurfaceDensity': '$\Sigma$ [M$_{\odot}$ pc$^{-2}$]',
         'VelocityDispersion': '$\sigma$ [km s$^{-1}$]',
         'Radius': '$R$ [pc]'}

    # selects surface density points wthin the limits
    Use_x_ax = (x_ax > xMin) & (x_ax < xMax)
    Use_y_ax = (y_ax > yMin) & (y_ax < yMax)
    Use_z_ax = (z_ax > zMin) & (z_ax < zMax)
    # intersects the three subsets defined above
    Use = Use_x_ax & Use_y_ax & Use_z_ax

    UniqueAuthor = list(set(Author[Use]))
    NUniqueAuthor = len(UniqueAuthor)

    colors = list(matplotlib.cm.jet(np.linspace(0, 1, NUniqueAuthor)))
    random.seed(12)
    random.shuffle(colors)

    # NOTE this does NOT work with mpld3
    # ax.loglog()

    scatters = []

    markers = ['o', 's']
    for iAu, color in zip(UniqueAuthor, colors):
        ObsPlot = ((Author == iAu) & (~IsSim)) & Use
        SimPlot = ((Author == iAu) & (IsSim)) & Use

        if show_log:
            plot_x = np.log10(x_ax)
            plot_y = np.log10(y_ax)

        if any(ObsPlot):
            # Change to logs on next commit
            scatter = \
                ax.scatter(plot_x[ObsPlot], plot_y[ObsPlot], marker=markers[0],
                           s=(np.log(np.array(z_ax[ObsPlot]))-np.log(zMin.value)+0.5)**3.,
                           color=color, alpha=0.5, edgecolors='k')

            scatters.append(scatter)

            labels = []

            for row in d[ObsPlot]:
                colnames = ['<h1>{title}</h1>'.format(title=col)
                            for col in row.colnames]
                values = ['<h1>{title}</h1>'.format(title=str(val))
                          for val in row]

                label = ""

                for col, val in zip(colnames, values):
                    label += col+" "+val+" \n "

                labels.append(label)

            tooltip = plugins.PointHTMLTooltip(scatter, labels,
                                               voffset=10, hoffset=10)
            plugins.connect(figure, tooltip)

        if any(SimPlot):
            # Change to logs on next commit
            scatter = \
                ax.scatter(plot_x[SimPlot], plot_y[SimPlot], marker=markers[1],
                           s=(np.log(np.array(z_ax[SimPlot]))-np.log(zMin.value)+0.5)**3.,
                           color=color, alpha=0.5, edgecolors='k')

            scatters.append(scatter)

            labels = []

            for row in d[SimPlot]:
                colnames = ['<h1>{title}</h1>'.format(title=col)
                            for col in row.colnames]
                values = ['<h1>{title}</h1>'.format(title=str(val))
                          for val in row]

                label = ""

                for col, val in zip(colnames, values):
                    label += col+" "+val+" \n "

                labels.append(label)

            tooltip = plugins.PointHTMLTooltip(scatter, labels,
                                               voffset=10, hoffset=10, css=css)
            plugins.connect(figure, tooltip)

    ax.set_xlabel(label_dict[variables[0]], fontsize=16)
    ax.set_ylabel(label_dict[variables[1]], fontsize=16)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # ax.legend(UniqueAuthor, loc='center left', bbox_to_anchor=(1.0, 0.5),
    #           prop={'size':12}, markerscale = .7, scatterpoints = 1)

    if hasattr(mpld3.plugins, 'InteractiveLegendPlugin'):
        plugins.connect(figure,
                        plugins.InteractiveLegendPlugin(scatters,
                                                        UniqueAuthor,
                                                        alpha_unsel=0,
                                                        alpha_sel=0.5))

    # adding fake points to show the size
    axes_limits = ax.axis()
    xax_limits = axes_limits[:2]
    yax_limits = axes_limits[2:]

    # TODO: write a function with this section
    # TODO: change position based on user input
    xfake = [0.1, 0.1, 0.1]
    yfake = [0.85, 0.9, 0.95]
    radius = np.array([1e-1, 1e0, 1e1])  # *u.pc #(zMin + zMax)*0.5

    # xfake = [xax_limits[0] + xax_limits[0]*2.,
    #          xax_limits[0] + xax_limits[0]*2.,
    #          xax_limits[0] + xax_limits[0]*2.]
    # yfake = [yax_limits[1] - yax_limits[1]*0.01,
    #          yax_limits[1] - yax_limits[1]*0.3,
    #          yax_limits[1] - yax_limits[1]*0.6]

    ax.scatter(np.array(xfake), np.array(yfake), marker='+',
               s=(np.log(np.array(radius))-np.log(zMin.value)+0.5)**3.,
               transform=ax.transAxes,
               facecolors='g')
    for xf, yf, rad in zip(xfake, yfake, radius):
        ax.text(xf + 0.05, yf-0.01, str(rad) + ' ' + str(zMin.unit),
                transform=ax.transAxes)

    if show_log:
        ax.set_xlim(np.log10(xMin.value), np.log10(xMax.value))
        ax.set_ylim(np.log10(yMin.value), np.log10(yMax.value))
    else:
        ax.set_xlim(xMin.value, xMax.value)
        ax.set_ylim(yMin.value, yMax.value)

    html = mpld3.fig_to_html(figure)
    with open("mpld3_"+FigureStrBase+NQuery+'.html', 'w') as f:
       f.write(html)

    # figure.savefig(FigureStrBase+NQuery+'.png',bbox_inches='tight',dpi=150)
    # figure.savefig(FigureStrBase+NQuery+'.pdf',bbox_inches='tight',dpi=150)

    if interactive:
        # from matplotlib import pyplot as plt
        # plt.ion()
        # plt.show()

        mpld3.show()

    return "mpld3_"+FigureStrBase+NQuery+'.html'

def clearPlotOutput(FigureStrBase,TooOld) :

    for fl in glob.glob(FigureStrBase+"*.png") + glob.glob(FigureStrBase+"*.pdf"):
        now = time.time()
        if os.stat(fl).st_mtime < now - TooOld :
            os.remove(fl)

def timeString() :

    TimeString=datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return TimeString
