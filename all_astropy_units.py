import astropy.units as u

allunits = []
for unit in dir(u):
	try:
		allunits.append(u.__getattribute__(unit).name)
	except:
		continue

print allunits