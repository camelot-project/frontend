from __future__ import unicode_literals
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


label_dict_html = \
    {'SurfaceDensity': '\u03A3 [M\u2609 pc\u207B\u00B2]',
     'VelocityDispersion': "\u03C3 [km s\u207B\u00B9]",
     'Radius': '$R$ [pc]'}

label_dict_png = \
    {'SurfaceDensity': u'$\Sigma$ [M$_{\odot}$ pc$^{-2}$]',
     'VelocityDispersion': u"$\sigma$ [km s$^{-1}$]",
     'Radius': u'$R$ [pc]'}


def plotData_Sigma_sigma(NQuery, table, FigureStrBase,
                         SurfMin=1e-1*u.M_sun/u.pc**2,
                         SurfMax=1e5*u.M_sun/u.pc**2,
                         VDispMin=1e-1*u.km/u.s,
                         VDispMax=3e2*u.km/u.s,
                         RadMin=1e-2*u.pc,
                         RadMax=1e3*u.pc,
                         **kwargs):
    """
    SurfMin
    SurfMax
    VDispMin
    VDispMax
    RadMin
    RadMax
    """
    return plotData(NQuery, table, FigureStrBase,
                    xvariable="SurfaceDensity",
                    yvariable="VelocityDispersion",
                    zvariable="Radius",
                    xMin=SurfMin,
                    xMax=SurfMax,
                    yMin=VDispMin,
                    yMax=VDispMax,
                    zMin=RadMin,
                    zMax=RadMax,
                    **kwargs)


def plotData(NQuery, input_table, FigureStrBase, html_dir=None, png_dir=None,
             xvariable='SurfaceDensity', yvariable='VelocityDispersion',
             zvariable='Radius',
             xMin=None, xMax=None, yMin=None, yMax=None, zMin=None, zMax=None,
             interactive=False, show_log=True, min_marker_width=3,
             max_marker_width=0.05):
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
    min_marker_width : int or float, optional
        Sets the pixel width of the smallest marker to be plotted. If <1,
        it is interpreted to be a fraction of the total pixels along the
        shortest axis.
    max_marker_width : int or float, optional
        Sets the pixel width of the smallest marker to be plotted. If <1,
        it is interpreted to be a fraction of the total pixels along the
        shortest axis.

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
    x_ax = d[xvariable]
    y_ax = d[yvariable]
    z_ax = d[zvariable]

    # Check if limits are given
    if xMin is None:
        xMin = x_ax.min()
    if xMax is None:
        xMax = x_ax.max()

    if yMin is None:
        yMin = y_ax.min()
    if yMax is None:
        yMax = y_ax.max()

    if zMin is None:
        zMin = z_ax.min()
    if zMax is None:
        zMax = z_ax.max()

    if d['IsSimulated'].dtype == 'bool':
        IsSim = d['IsSimulated']
    else:
        IsSim = d['IsSimulated'] == 'True'

    if show_log:
        if not label_dict_html[xvariable].startswith('log'):
            label_dict_html[xvariable] = 'log ' + label_dict_html[xvariable]
            label_dict_html[yvariable] = 'log ' + label_dict_html[yvariable]
        if not label_dict_png[xvariable].startswith('log'):
            label_dict_png[xvariable] = 'log ' + label_dict_png[xvariable]
            label_dict_png[yvariable] = 'log ' + label_dict_png[yvariable]

    # Select points within the limits
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

    # Set marker sizes based on a minimum and maximum pixel size, then scale
    # the rest between.

    bbox = \
        ax.get_window_extent().transformed(figure.dpi_scale_trans.inverted())

    min_axis_size = min(bbox.width, bbox.height) * figure.dpi

    if max_marker_width < 1:
        max_marker_width *= min_axis_size

    if min_marker_width < 1:
        min_marker_width *= min_axis_size

    marker_conversion = max_marker_width / \
        (np.log10(z_ax[Use].max())-np.log10(z_ax[Use].min()))

    marker_widths = (marker_conversion *
                     (np.log10(np.array(z_ax))-np.log10(z_ax[Use].min())) +
                     min_marker_width)

    marker_sizes = marker_widths**2

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
                           s=marker_sizes[ObsPlot],
                           color=color, alpha=0.5, edgecolors='k',
                           label=iAu)

            scatters.append(scatter)

            labels = []

            for row in d[ObsPlot]:
                colnames = ['<div>{title}</div>'.format(title=col)
                            for col in row.colnames]
                values = ['<div>{title}</div>'.format(title=str(val))
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
                           s=marker_sizes[SimPlot],
                           color=color, alpha=0.5, edgecolors='k',
                           label=iAu)

            scatters.append(scatter)

            labels = []

            for row in d[SimPlot]:
                colnames = ['<div>{title}</div>'.format(title=col)
                            for col in row.colnames]
                values = ['<div>{title}</div>'.format(title=str(val))
                          for val in row]

                label = ""

                for col, val in zip(colnames, values):
                    label += col+" "+val+" \n "

                labels.append(label)

            tooltip = plugins.PointHTMLTooltip(scatter, labels,
                                               voffset=10, hoffset=10, css=css)
            plugins.connect(figure, tooltip)

    ax.set_xlabel(label_dict_html[xvariable], fontsize=16)
    ax.set_ylabel(label_dict_html[yvariable], fontsize=16)

    # Set plot limits. Needed for conversion of pixel units to plot units.

    # Pad the maximum marker width on.
    inv = ax.transData.inverted()
    pad_x, pad_y = inv.transform((marker_widths.max(), marker_widths.max())) - \
        inv.transform((0.0, 0.0))

    if show_log:
        ax.set_xlim(np.log10(xMin.value)-pad_x, np.log10(xMax.value)+pad_x)
        ax.set_ylim(np.log10(yMin.value)-pad_y, np.log10(yMax.value)+pad_y)
    else:
        ax.set_xlim(xMin.value - pad_x, xMax.value + pad_x)
        ax.set_ylim(yMin.value - pad_y, yMax.value + pad_y)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # ax.legend(UniqueAuthor, loc='center left', bbox_to_anchor=(1.0, 0.5),
    #           prop={'size':12}, markerscale = .7, scatterpoints = 1)

    if hasattr(mpld3.plugins, 'InteractiveLegendPlugin'):
        plugins.connect(figure,
                        plugins.InteractiveLegendPlugin(scatters,
                                                        UniqueAuthor,
                                                        alpha_unsel=0.0,
                                                        alpha_over=0.5))

    # Adding fake points to show the size

    # Try floor and ceil. Pick the one closest to the max/min.
    max_z = round_to_pow_10(z_ax[Use].max())
    min_z = round_to_pow_10(z_ax[Use].min())
    mid_z = round_to_pow_10((max_z + min_z) / 2., log=False)
    if mid_z == max_z:
        fake_z_marker_width = np.array([max_z])
    elif mid_z == max_z or mid_z == min_z:
        fake_z_marker_width = np.array([max_z, min_z])
    else:
        fake_z_marker_width = np.array([max_z, mid_z, min_z])

    fake_marker_sizes = (marker_conversion *
                         (fake_z_marker_width-np.log10(z_ax[Use].min())) +
                         min_marker_width)**2

    # Set the axis fraction to plot the points at. Adjust if the largest
    # will overlap with the next.
    sep_ax_frac = 0.05

    if np.sqrt(fake_marker_sizes[0])/float(min_axis_size) > 0.05:
        sep_ax_frac = np.sqrt(fake_marker_sizes[0])/float(min_axis_size) \
            + 0.005

    xfake = [0.1] * fake_z_marker_width.shape[0]
    yfake = [0.95 - sep_ax_frac*x for x in range(fake_z_marker_width.shape[0])]

    # xfake = [xax_limits[0] + xax_limits[0]*2.,
    #          xax_limits[0] + xax_limits[0]*2.,
    #          xax_limits[0] + xax_limits[0]*2.]
    # yfake = [yax_limits[1] - yax_limits[1]*0.01,
    #          yax_limits[1] - yax_limits[1]*0.3,
    #          yax_limits[1] - yax_limits[1]*0.6]

    ax.scatter(np.array(xfake), np.array(yfake), marker='+',
               s=fake_marker_sizes,
               transform=ax.transAxes,
               facecolors='g')
    for xf, yf, rad in zip(xfake, yfake, fake_z_marker_width):
        ax.text(xf + 0.05, yf-0.01, str(10**rad) + ' ' + str(zMin.unit),
                transform=ax.transAxes)

    # Saving the plots

    if html_dir is None:
        html_dir = ""

    if png_dir is None:
        png_dir = ""

    html_file = os.path.join(html_dir, FigureStrBase+NQuery+'.html')
    png_file = os.path.join(png_dir, FigureStrBase+NQuery+".png")

    html = mpld3.fig_to_html(figure)
    with open(html_file, 'w') as f:
       f.write(html)

    if interactive:
        # from matplotlib import pyplot as plt
        # plt.ion()
        # plt.show()

        mpld3.show()

    # Clear out the plugins
    plugins.clear(figure)

    # Use latex labels for the mpl outputted plot
    ax.set_xlabel(label_dict_png[xvariable], fontsize=16)
    ax.set_ylabel(label_dict_png[yvariable], fontsize=16)

    # Shrink current axis by 20%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # Put a legend to the right of the current axis
    legend = ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    legend.draw_frame(False)

    figure.savefig(png_file, bbox_inches='tight', dpi=150)
    # figure.savefig(FigureStrBase+NQuery+'.pdf',bbox_inches='tight',dpi=150)

    return html_file, png_file


def round_to_pow_10(value, log=True):
    '''
    Use ceil and floor on a given value and return the value which is the
    closest.
    '''

    if log:
        log_value = np.log10(value)
    else:
        log_value = value

    ceil = np.ceil(log_value)

    floor = np.floor(log_value)

    if np.abs(ceil - log_value) < np.abs(log_value - floor):
        return ceil
    else:
        return floor
