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
                                   'radius':'Radius','is_sim':'IsSimulated'},
                   remove_column='Ignore'):
    """
    Rename table columns inplace
    """

    for k,v in mapping.items():
        if k in tbl.colnames:
            if v == remove_column:
                tbl.remove_column(k)
            elif k != v:
                tbl.rename_column(k,v)

def fix_bad_types(tbl):
    """
    For all columns that *can* be converted to float, convert them to float
    """
    columns = []
    for columnname, column in tbl.columns.items():
        try:
            col = Column(data=column.astype('float'), name=column.name)
            columns.append(col)
        except:
            columns.append(column)
    return Table(columns)

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
        #DEBUG print 'BEFORE unit for',k,":",tbl[k].unit
        if v:
            # only set units if there is a unit to be specified
            tbl[k].unit = v
        #DEBUG print 'AFTER  unit for',k,":",tbl[k].unit

def convert_units(tbl, units={'SurfaceDensity':u.M_sun/u.pc**2,
                          'VelocityDispersion':u.km/u.s,
                          'Radius':u.pc}):
    """
    Set the units of the table to the specified units.
    WARNING: this *overwrites* existing units, it does not convert them!
    """
    for k,v in units.items():
        if k not in tbl.colnames:
            raise KeyError("{0} not in table: run `rename_columns` first.".format(k))
        tbl[k] = tbl[k].to(v)

def add_name_column(tbl, name):
    """
    Add the person's name as a column
    """
    tbl.add_column(table.Column(name='Names', data=[name]*len(tbl)), index=0)

def add_filename_column(tbl, filename):
    """
    Add the filename as a column
    """
    tbl.add_column(table.Column(name='Filename', data=[filename]*len(tbl)))

def append_table(merged_table, table_to_add):
    """
    Append a new table to the original
    """
    for row in table_to_add:
        merged_table.add_row(row)

def add_generic_ids_if_needed(tbl):
    """
    Add numbered IDs if no IDs column is provided
    """
    if 'IDs' not in tbl.colnames:
        tbl.add_column(table.Column(data=np.arange(len(tbl)), name='IDs'))

def add_is_sim_if_needed(tbl, is_sim=True):
    """
    Add is_sim if no is_sim column is provided
    """
    if 'IsSimulated' not in tbl.colnames:
        tbl.add_column(table.Column(data=[is_sim]*(len(tbl)), name='IsSimulated'))
