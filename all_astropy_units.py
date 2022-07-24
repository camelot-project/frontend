import astropy.units as u
import inspect

allunits = set()
for unitname,unit in inspect.getmembers(u):
    if isinstance(unit, u.UnitBase):
        try:
            for name in unit.names:
                allunits.add(name)
        except AttributeError:
            continue

print(allunits)
