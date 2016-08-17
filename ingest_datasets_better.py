import numpy as np
from astropy import table
from astropy.table import Table,Column
from astropy import units as u
from astropy import log
import re
import string

unit_mapping = {'SurfaceDensity':u.M_sun/u.pc**2,
                'VelocityDispersion':u.km/u.s,
                'Radius':u.pc}

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

def fix_bad_colnames(tbl):
    """
    Remove bad characters in column names
    """
    badchars = re.compile("[^A-Za-z0-9_]")
    for k in tbl.colnames:
        if badchars.search(k):
            tbl.rename_column(k, badchars.sub("", k))
            print("Renamed {0} to {1}".format(k, badchars.sub("", k)))

def fix_bad_types(tbl):
    """
    For all columns that *can* be converted to float, convert them to float
    """
    log.debug("Fixing bad types")
    columns = []
    for columnname, column in tbl.columns.items():
        try:
            col = Column(data=column.astype('float'), name=column.name,
                         unit=column.unit)
            columns.append(col)
            log.debug("Converted column {0} from {1} to {2}"
                      .format(column.name, column, col))
        except:
            columns.append(column)
    return Table(columns)

def set_units(tbl, units=unit_mapping):
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

def convert_units(tbl, units=unit_mapping):
    """
    Convert from the units used in the table to the specified units.
    """
    log.debug("unit mapping: {0}".format(unit_mapping))
    for k,v in units.items():
        if k not in tbl.colnames:
            raise KeyError("{0} not in table: run `rename_columns` first.".format(k))
        log.debug("unit key:{0} value:{1} tbl[k]={2}".format(k,v,tbl[k]))
        tbl[k] = tbl[k].to(v)
        tbl[k].unit = v

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

def add_timestamp_column(tbl, timestamp):
    """
    Add the current date and time as a column
    """
    tbl.add_column(table.Column(name='Timestamp', data=[timestamp]*len(tbl)))

def add_is_gal_column(tbl, is_gal):
    """
    Add IsGalactic column
    """
    tbl.add_column(table.Column(name='IsGalactic', data=[is_gal]*len(tbl)))

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

def add_is_gal_if_needed(tbl, is_gal=True):
    """
    Add is_gal if no is_gal column is provided
    """
    if 'IsGalactic' not in tbl.colnames:
        tbl.add_column(table.Column(data=[is_gal]*(len(tbl)), name='IsGalactic'))

def ignore_duplicates(table, duplicates):
    """
    If entries in upload data duplicate entries already in table, ignore them.
    Needs list of duplicates, which is constructed elsewhere.
    """
    to_delete = []
    for row in table:
        name = row['Names']
        id   = row['IDs']
        if id in duplicates:
            if duplicates[id] == name:
                to_delete.append(row.index)
 
    table.remove_rows(to_delete) 

def update_duplicates(merged_table, duplicates):
    """
    If entries in upload data duplicate entries already in table, remove
    the versions already in the table. Needs list of duplicates, which is 
    constructed elsewhere.
    """

    to_delete = []
    for row in merged_table:
        name = row['Names']
        id   = row['IDs']
        if id in duplicates:
            if duplicates[id] == name:
                to_delete.append(row.index)
 
    merged_table.remove_rows(to_delete) 


