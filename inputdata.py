#Importing standard libraries
import numpy as np
import pandas as pd  
import pvlib as pvl

loc_friedberg = [50.330, 8.759]
loc_nazaire = [47.279, -2.212]

#tmy_friedberg, months_selected_tmy_friedberg, inputs_tmy_friedberg, metadata_tmy_friedberg  = pvl.iotools.get_pvgis_tmy(*loc_friedberg, outputformat = 'csv', startyear = 2005, endyear = 2020, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
#tmy_nazaire, months_selected_tmy_nazaire, inputs_tmy_nazaire, metadata_tmy_nazaire = pvl.iotools.get_pvgis_tmy(*loc_nazaire, outputformat = 'csv', startyear = 2005, endyear = 2020, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

hourly_friedberg, inputs_hourly_friedberg, metadata_hourly_friedberg = pvl.iotools.get_pvgis_hourly(*loc_friedberg, outputformat = 'csv', peakpower = 6, loss = 14, mountingplace = 'building', raddatabase = 'PVGIS-SARAH2', url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
hourly_nazaire, inputs_hourly_nazaire, metadata_hourly_nazaire = pvl.iotools.get_pvgis_hourly(*loc_nazaire, outputformat = 'csv', peakpower = 6, loss = 14, mountingplace = 'building', raddatabase = 'PVGIS-SARAH2', url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

#horizon_friedberg, metadata_horizon_friedberg = pvl.iotools.get_pvgis_horizon(*loc_friedberg, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
#horizon_nazaire, metadata_horizon_nazaire = pvl.iotools.get_pvgis_horizon(*loc_nazaire, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

#tmy_friedberg.to_csv('tmy_friedberg.csv')
#tmy_nazaire.to_csv('tmy_nazaire.csv')
#hourly_friedberg.to_csv('hourly_friedberg.csv')
#hourly_nazaire.to_csv('hourly_nazaire.csv')
#horizon_friedberg.to_csv('horizon_friedberg.csv')
#horizon_nazaire.to_csv('horizon_nazaire.csv')

cons_konstanz = pd.read_csv("CESI-THM-Project1-Load-Profile.csv", header = 0, names = ['timestamp (UTC)', 'dishwasher', 'ev', 'freezer', 'grid export', 'grid import', 'heat pump', 'pv', 'refrigerator', 'washing machine'], usecols = [0,2,3,4,5,6,7,8,9,10], delimiter = ";").fillna(0)
cons_konstanz["total energy consuption"] = (cons_konstanz["dishwasher"] + cons_konstanz["ev"] + cons_konstanz["freezer"] + cons_konstanz["heat pump"] + cons_konstanz["refrigerator"] + cons_konstanz["washing machine"])
cons_konstanz["energy balance"] = (cons_konstanz["grid import"] - cons_konstanz["grid export"] + cons_konstanz["pv"])
cons_konstanz["rounded timestamp"] = (
    (pd.to_datetime(cons_konstanz["timestamp (UTC)"]) - pd.Timedelta(minutes=10))
    .dt.round('h') + pd.Timedelta(minutes=10)
)
cons_konstanz = cons_konstanz.drop(columns = ['timestamp (UTC)'])
cons_konstanz_grouped = cons_konstanz.groupby(cons_konstanz["rounded timestamp"]).mean()

merged_hourly_dataset = pd.merge_ordered(hourly_friedberg, hourly_nazaire,  on = 'time', suffixes = ('_FB', '_NZ')).fillna(0)
merged_hourly_dataset['time'] = pd.to_datetime(merged_hourly_dataset['time'])
merged_hourly_dataset.to_csv('merged_hourly_dataset.csv')

merged_fully_dataset = pd.merge_ordered(merged_hourly_dataset, cons_konstanz_grouped, left_on = 'time', right_on = 'rounded timestamp').fillna(0)
merged_fully_dataset.to_csv('merged_fully_dataset.csv')
