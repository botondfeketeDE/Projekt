#Importing standard libraries
import numpy as np
import pandas as pd  
import pvlib as pvl

loc_friedberg = [50.330, 8.759]
loc_nazaire = [47.279, -2.212]
battery_eff = 0.9
battery_charge = 4000
battery_discharge = -5000
battery_capacity = 10000

#tmy_friedberg, months_selected_tmy_friedberg, inputs_tmy_friedberg, metadata_tmy_friedberg  = pvl.iotools.get_pvgis_tmy(*loc_friedberg, outputformat = 'csv', startyear = 2005, endyear = 2020, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
#tmy_nazaire, months_selected_tmy_nazaire, inputs_tmy_nazaire, metadata_tmy_nazaire = pvl.iotools.get_pvgis_tmy(*loc_nazaire, outputformat = 'csv', startyear = 2005, endyear = 2020, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

hourly_friedberg, inputs_hourly_friedberg, metadata_hourly_friedberg = pvl.iotools.get_pvgis_hourly(*loc_friedberg, outputformat = 'csv', peakpower = 6, loss = 14, pvcalculation = True, optimal_surface_tilt = True, optimalangles = True, surface_azimuth = 178, surface_tilt = 38, mountingplace = 'building', raddatabase = 'PVGIS-SARAH2', url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
hourly_nazaire, inputs_hourly_nazaire, metadata_hourly_nazaire = pvl.iotools.get_pvgis_hourly(*loc_nazaire, outputformat = 'csv', peakpower = 6, loss = 14, pvcalculation = True, optimal_surface_tilt = True, optimalangles = True, surface_tilt = 38, mountingplace = 'building', raddatabase = 'PVGIS-SARAH2', url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

#horizon_friedberg, metadata_horizon_friedberg = pvl.iotools.get_pvgis_horizon(*loc_friedberg, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')
#horizon_nazaire, metadata_horizon_nazaire = pvl.iotools.get_pvgis_horizon(*loc_nazaire, url = 'https://re.jrc.ec.europa.eu/api/v5_2/')

#tmy_friedberg.to_csv('tmy_friedberg.csv')
#tmy_nazaire.to_csv('tmy_nazaire.csv')
#hourly_friedberg.to_csv('hourly_friedberg.csv')
#hourly_nazaire.to_csv('hourly_nazaire.csv')
#horizon_friedberg.to_csv('horizon_friedberg.csv')
#horizon_nazaire.to_csv('horizon_nazaire.csv')

cons_konstanz = pd.read_csv("CESI-THM-Project1-Load-Profile.csv", header = 0, names = ['timestamp (UTC)', 'dishwasher', 'ev', 'freezer', 'grid export', 'grid import', 'heat pump', 'pv', 'refrigerator', 'washing machine'], usecols = [0,2,3,4,5,6,7,8,9,10], delimiter = ";").fillna(0)
cons_konstanz["total energy consumption"] = (cons_konstanz["dishwasher"] + cons_konstanz["ev"] + cons_konstanz["freezer"] + cons_konstanz["heat pump"] + cons_konstanz["refrigerator"] + cons_konstanz["washing machine"])
cons_konstanz["energy balance"] = (cons_konstanz["grid import"] - cons_konstanz["grid export"] + cons_konstanz["pv"])
cons_konstanz["rounded timestamp"] = (
    (pd.to_datetime(cons_konstanz["timestamp (UTC)"]) - pd.Timedelta(minutes=10))
    .dt.round('h') + pd.Timedelta(minutes=10)
)
cons_konstanz = cons_konstanz.drop(columns = ['timestamp (UTC)'])
cons_konstanz_grouped = cons_konstanz.groupby(cons_konstanz["rounded timestamp"]).mean()

#hourly_friedberg["battery"] = hourly_friedberg.apply(lambda row: (hourly_friedberg["battery"].iloc[-1]

merged_hourly_dataset = pd.merge_ordered(hourly_friedberg, hourly_nazaire,  on = 'time', suffixes = ('_FB', '_NZ')).fillna(0)
merged_hourly_dataset['time'] = pd.to_datetime(merged_hourly_dataset['time'])
merged_hourly_dataset.to_csv('merged_hourly_dataset.csv')

merged_fully_dataset = pd.merge_ordered(merged_hourly_dataset, cons_konstanz_grouped, left_on = 'time', right_on = 'rounded timestamp').fillna(0)

battery_fb_values = []
grid_usage_fb = []
energy_consumption_battery_fb = 0

for i in range(len(merged_fully_dataset)):
    balance_fb = merged_fully_dataset["P_FB"].iloc[i] - merged_fully_dataset["total energy consumption"].iloc[i]
    if i == 0:
        if balance_fb <= 0:
            battery_fb_values.append(0)
            grid_usage_fb.append(balance_fb)
        elif balance_fb > 0 and balance_fb <= battery_charge / battery_eff:
            battery_fb_values.append(balance_fb * battery_eff)
            grid_usage_fb.append(0)
        else:
            battery_fb_values.append(battery_charge * battery_eff)
            grid_usage_fb.append(-(balance_fb - battery_charge))
    else:
        # Fully charging speed, not fully charged battery
        if balance_fb >= battery_charge and (battery_fb_values[i-1] + battery_charge * battery_eff) <= battery_capacity:
            energy_consumption_battery_fb = 0
            battery_fb_values.append(battery_fb_values[i-1] + battery_charge * battery_eff)
            grid_usage_fb.append(-(balance_fb - battery_charge))
        # Fully charging speed, fully charged battery
        elif balance_fb >= battery_charge and (battery_fb_values[i-1] + battery_charge * battery_eff) > battery_capacity:
            energy_consumption_battery_fb = 0
            battery_fb_values.append(battery_capacity)
            grid_usage_fb.append(-(balance_fb - battery_charge) - (battery_charge - (battery_capacity - battery_fb_values[i-1]) / battery_eff))
        # Not fully charging speed, not fully charged battery
        elif balance_fb < battery_charge and balance_fb >= 0 and (battery_fb_values[i-1] + balance_fb * battery_eff) <= battery_capacity:
            energy_consumption_battery_fb = 0
            battery_fb_values.append(battery_fb_values[i-1] + balance_fb * battery_eff)
            grid_usage_fb.append(0)
        # Not fully charging speed, fully charged battery
        elif balance_fb < battery_charge and balance_fb >= 0 and (battery_fb_values[i-1] + balance_fb * battery_eff) > battery_capacity:
            energy_consumption_battery_fb = 0
            battery_fb_values.append(battery_capacity)
            grid_usage_fb.append(-(balance_fb - (battery_capacity - battery_fb_values[i-1]) / battery_eff))
        # Fully discharging speed, not fully discharged battery
        elif balance_fb <= battery_discharge * battery_eff and (battery_fb_values[i-1] + battery_discharge) >= 0:
            energy_consumption_battery_fb = -battery_discharge
            battery_fb_values.append(battery_fb_values[i-1] + battery_discharge)
            grid_usage_fb.append(balance_fb + battery_discharge)
        # Fully discharging speed, fully discharged battery
        elif balance_fb <= battery_discharge * battery_eff and (battery_fb_values[i-1] + battery_discharge) < 0:
            energy_consumption_battery_fb = battery_fb_values[i-1]
            battery_fb_values.append(0)
            grid_usage_fb.append(balance_fb + battery_discharge - (battery_fb_values[i-1] + battery_discharge))
        # Not fully discharging speed, not fully discharged battery
        elif balance_fb > battery_discharge * battery_eff and balance_fb < 0 and (battery_fb_values[i-1] + battery_discharge) >= 0:
            energy_consumption_battery_fb = balance_fb / battery_eff
            battery_fb_values.append(battery_fb_values[i-1] + (balance_fb / battery_eff))
            grid_usage_fb.append(0)
        # Not fully discharging speed, fully discharged battery
        elif balance_fb > battery_discharge * battery_eff and balance_fb < 0 and (battery_fb_values[i-1] + battery_discharge) < 0:
            energy_consumption_battery_fb = battery_fb_values[i-1]
            battery_fb_values.append(0)
            grid_usage_fb.append(-battery_fb_values[i-1] - battery_discharge)
        else:
            print("Error in battery simulation")
            	       
merged_fully_dataset["battery_FB"] = battery_fb_values

merged_fully_dataset.to_csv('merged_fully_dataset.csv')

print(merged_fully_dataset.describe())