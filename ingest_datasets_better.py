import numpy as np
from astropy import table
from astropy.table import Table,Column
from astropy import units as u

def fix_logical(t):
    """
    Convert a boolean column from string to boolean
    """
    newcols = []
    for col in t.columns.values():
        if col.dtype.str.endswith('S5') or col.dtype.str.endswith('S4'):
            falses = col == 'False'
            trues = col == 'True'
            if np.all(falses | trues):
                col = t.ColumnClass(trues, name=col.name)
        newcols.append(col)
    return Table(newcols)

def reorder_columns(tbl, order):
    """
    Sort the columns into an order set by the order list
    """
    cols = [tbl[colname] for colname in order]
    return Table(cols)

def rename_columns(tbl, mapping = {'name':'Names', 'id':'IDs',
                                   'surfdens':'SurfaceDensity',
                                   'vdisp':'VelocityDispersion',
                                   'radius':'Radius','is_sim':'IsSimulated'}):
    """
    Rename table columns inplace
    """

    for k,v in mapping.items():
        if k in tbl.colnames:
            tbl.rename_column(k,v)

def set_units(tbl, units={'SurfaceDensity':u.M_sun/u.pc**2,
                          'VelocityDispersion':u.km/u.s,
                          'Radius':u.pc}):
    """
    Set the units of the table to the specified units.
    WARNING: this *overwrites* existing units, it does not convert them!
    """
    for k,v in units.items():
        if k not in tbl.colnames:
            raise KeyError("{0} not in table: run `rename_columns` first.".format(k))
        tbl[k].unit = v

def add_name_column(tbl, name):
    """
    Add the person's name as a column
    """
    tbl.add_column(table.Column(name='Names', data=[name]*len(tbl)), index=0)

def append_table(merged_table, table_to_add):
    """
    Append a new table to the original
    """
    for row in table_to_add:
        merged_table.add_row(row)
