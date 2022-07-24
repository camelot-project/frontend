from warnings import warn
from textwrap import wrap
from astropy.io.ascii import ipac,core
from astropy.extern import six
from astropy.utils.exceptions import AstropyUserWarning

class IpacSpecifiableWidth(ipac.Ipac):
    def write(self, table, widths=None):
        """
        Write ``table`` as list of strings with optional specified widths

        Parameters
        ----------
        table: `~astropy.table.Table`
            Input table data
        widths: list
            A list of integer line widths

        Returns
        -------
        lines : list
            List of strings corresponding to ASCII table

        """
        # Set a default null value for all columns by adding at the end, which
        # is the position with the lowest priority.
        # We have to do it this late, because the fill_value
        # defined in the class can be overwritten by ui.write
        self.data.fill_values.append((core.masked, 'null'))

        # Check column names before altering
        self.header.cols = list(six.itervalues(table.columns))
        self.header.check_column_names(self.names, self.strict_names, self.guessing)

        core._apply_include_exclude_names(table, self.names, self.include_names, self.exclude_names)

        # Now use altered columns
        new_cols = list(six.itervalues(table.columns))
        # link information about the columns to the writer object (i.e. self)
        self.header.cols = new_cols
        self.data.cols = new_cols

        # Write header and data to lines list
        lines = []
        # Write meta information
        if 'comments' in table.meta:
            for comment in table.meta['comments']:
                if len(str(comment)) > 78:
                    warn('Comment string > 78 characters was automatically wrapped.',
                         AstropyUserWarning)
                for line in wrap(str(comment), 80, initial_indent='\\ ', subsequent_indent='\\ '):
                    lines.append(line)
        if 'keywords' in table.meta:
            keydict = table.meta['keywords']
            for keyword in keydict:
                try:
                    val = keydict[keyword]['value']
                    lines.append('\\{0}={1!r}'.format(keyword.strip(), val))
                    # meta is not standardized: Catch some common Errors.
                except TypeError:
                    pass

        # Usually, this is done in data.write, but since the header is written
        # first, we need that here.
        self.data._set_fill_values(self.data.cols)

        # get header and data as strings to find width of each column
        for i, col in enumerate(table.columns.values()):
            col.headwidth = max([len(vals[i]) for vals in self.header.str_vals()])
        # keep data_str_vals because they take some time to make
        data_str_vals = []
        col_str_iters = self.data.str_vals()
        for vals in zip(*col_str_iters):
            data_str_vals.append(vals)

        for i, col in enumerate(table.columns.values()):
            # FIXME: In Python 3.4, use max([], default=0).
            # See: https://docs.python.org/3/library/functions.html#max
            if data_str_vals:
                col.width = max([len(vals[i]) for vals in data_str_vals])
            else:
                col.width = 0

        if widths is None:
            widths = [max(col.width, col.headwidth) for col in list(table.columns.values())]
        # then write table
        self.header.write(lines, widths)
        self.data.write(lines, widths, data_str_vals)

        return lines

def ipac_writer(table, outfilename, widths):
    linemaker = IpacSpecifiableWidth()
    lines = linemaker.write(table, widths)
    with open(outfilename, 'w') as f:
        f.write("\n".join(lines))
