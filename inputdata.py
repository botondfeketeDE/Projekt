# Importing standard libraries
import numpy as np
import pandas as pd  
import pvlib as pvl
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

loc_friedberg = [50.330, 8.759]
loc_nazaire = [47.279, -2.212]

def main():
    # Parameters to set manually
    location = "FRIEDBERG"
    location = "ST_NAZAIRE"
    start_date = pd.to_datetime("2022-02-27T00")
    days_to_simulate = 2
    battery_eff = 0.9
    battery_charge = 4000
    battery_discharge = -5000
    battery_capacity = 10000
    battery_state = 0
    peak_power = 6
    network_loss = 14

    def get_location_data(location):
        if location == "FRIEDBERG":
            #Checking if data for Friedberg already downloaded
            if os.path.exists('tmy_friedberg.csv') and os.path.exists('hourly_friedberg.csv') and os.path.exists('horizon_friedberg.csv'):
                tmy_friedberg = pd.read_csv('tmy_friedberg.csv')
                hourly_friedberg = pd.read_csv('hourly_friedberg.csv')
                horizon_friedberg = pd.read_csv('horizon_friedberg.csv')
            else:
                #Downloading Friedberg's data
                tmy_friedberg, months_selected_tmy_friedberg, inputs_tmy_friedberg, metadata_tmy_friedberg = pvl.iotools.get_pvgis_tmy(
                    *loc_friedberg, outputformat='csv', startyear=2005, endyear=2020, url='https://re.jrc.ec.europa.eu/api/v5_2/'
                )
                hourly_friedberg, inputs_hourly_friedberg, metadata_hourly_friedberg = pvl.iotools.get_pvgis_hourly(
                    *loc_friedberg, outputformat='csv', peakpower=peak_power, loss=network_loss, pvcalculation=True, 
                    optimal_surface_tilt=True, optimalangles=True, surface_azimuth=178, surface_tilt=38, 
                    mountingplace='building', raddatabase='PVGIS-SARAH2', url='https://re.jrc.ec.europa.eu/api/v5_2/'
                )
                horizon_friedberg, metadata_horizon_friedberg = pvl.iotools.get_pvgis_horizon(*loc_friedberg, url='https://re.jrc.ec.europa.eu/api/v5_2/')
            #Returning Friedberg's data sheets
            return tmy_friedberg, hourly_friedberg, horizon_friedberg
        elif location == "ST_NAZAIRE":
            #Checking if data for St. Nazaire already downloaded
            if os.path.exists('tmy_nazaire.csv') and os.path.exists('hourly_nazaire.csv') and os.path.exists('horizon_nazaire.csv'):
                tmy_nazaire = pd.read_csv('tmy_nazaire.csv')
                hourly_nazaire = pd.read_csv('hourly_nazaire.csv')
                horizon_nazaire = pd.read_csv('horizon_nazaire.csv')
            else:
                #Downloading St. Nazaire's data
                tmy_nazaire, months_selected_tmy_nazaire, inputs_tmy_nazaire, metadata_tmy_nazaire = pvl.iotools.get_pvgis_tmy(
                    *loc_nazaire, outputformat='csv', startyear=2005, endyear=2020, url='https://re.jrc.ec.europa.eu/api/v5_2/'
                )            
                hourly_nazaire, inputs_hourly_nazaire, metadata_hourly_nazaire = pvl.iotools.get_pvgis_hourly(
                    *loc_nazaire, outputformat='csv', peakpower=peak_power, loss=network_loss, pvcalculation=True, 
                    optimal_surface_tilt=True, optimalangles=True, surface_tilt=38, 
                    mountingplace='building', raddatabase='PVGIS-SARAH2', url='https://re.jrc.ec.europa.eu/api/v5_2/'
                )
                horizon_nazaire, metadata_horizon_nazaire = pvl.iotools.get_pvgis_horizon(*loc_nazaire, url='https://re.jrc.ec.europa.eu/api/v5_2/')
            #Returning St. Nazaire's data sheets
            return tmy_nazaire, hourly_nazaire, horizon_nazaire
        else:
            print("Invalid location:", location)
            return "NO VALID LOCATION"
    
    def get_yearly_location_data(location):
        #Calling get_location_data function
        tmy, hourly, horizon = get_location_data(location)
        hour = pd.to_datetime(hourly["time"]).dt.hour
        #Calculating electricity price
        if location == "FRIEDBERG":
            # Fixed electricity price in Germany
            hourly['price_per_kwh'] = 0.3194
        elif location == "ST_NAZAIRE":
            # Peak and off-peak electricity prices in France
            peak_hours_mask = (hour >= 8) & (hour < 20)
            # Assign prices based on conditions
            hourly.loc[peak_hours_mask, 'price_per_kwh'] = 0.26706
            hourly.loc[~peak_hours_mask, 'price_per_kwh'] = 0.20458
        else:
            location_data_yearly['price_per_kwh'] = "Unknown price"
        #Converting time to timestamp format and correcting different from UTC
        hourly['time'] = pd.to_datetime(hourly['time']) + pd.Timedelta(hours = 1)
        #Removing time zone and year
        hourly['time'] = hourly['time'].dt.tz_localize(None).dt.strftime('%m-%d %H:%M:%S')
        #Grouping by the avarage values of the timestamp
        hourly_grouped = hourly.groupby(hourly["time"]).mean().reset_index()
        hourly_grouped.to_csv('hourly_grouped_data.csv')
        #Returning avarage weather condition values to each timestamp of a year
        return hourly_grouped
    
    def get_household_data():
        #Reading relevant data from the sample household dataset from Koblenz, Filling not know data with zero 
        cons_konstanz = pd.read_csv(
            "CESI-THM-Project1-Load-Profile.csv", header=0, 
            names=[
                'timestamp (UTC)', 'dishwasher', 'ev', 'freezer', 'grid export', 
                'grid import', 'heat pump', 'pv', 'refrigerator', 'washing machine'
            ], usecols=[0, 2, 3, 4, 5, 6, 7, 8, 9, 10], delimiter=","
        ).fillna(0)
        #Calculating total energy consumption
        cons_konstanz["total energy consumption"] = (
            cons_konstanz["dishwasher"] + cons_konstanz["ev"] + cons_konstanz["freezer"] + 
            cons_konstanz["heat pump"] + cons_konstanz["refrigerator"] + cons_konstanz["washing machine"]
        )
        #Calculating energy balance
        cons_konstanz["energy balance"] = (
            cons_konstanz["grid import"] - cons_konstanz["grid export"] + cons_konstanz["pv"]
        )
        #Rounding timestamps to the nearest 10 min of an hour to compare them with the PVGIS library data
        cons_konstanz["rounded timestamp"] = (
            (pd.to_datetime(cons_konstanz["timestamp (UTC)"]) - pd.Timedelta(minutes=10))
            .dt.round('h') + pd.Timedelta(minutes=10)
        )
        #Droping the old timestamp column
        cons_konstanz = cons_konstanz.drop(columns=['timestamp (UTC)'])
        
        #Removing year from the rounded timestamp
        cons_konstanz['rounded timestamp'] = cons_konstanz['rounded timestamp'].dt.strftime('%m-%d %H:%M:%S')
        #Grouping by the avarage values of the new timestamp
        cons_konstanz_grouped = cons_konstanz.groupby(cons_konstanz["rounded timestamp"]).mean().reset_index()
        cons_konstanz_grouped.to_csv('cons_household.csv')
        #Returning avarage consumption values to each timestamp of a year
        return cons_konstanz_grouped
    
    def merge_data(location):
        #Calling get_household_data function
        consumption_yearly = get_household_data()
        #Calling get_yearly_location_data
        location_data_yearly = get_yearly_location_data(location)
        #Merging household data and location data, Filling not known data with zero
        merged_dataset = pd.merge_ordered(
            location_data_yearly, consumption_yearly, left_on='time', right_on='rounded timestamp'
        ).fillna(0)
        #Removing rounded timestamp from the columns
        merged_dataset = merged_dataset.drop(columns=['rounded timestamp'])
        #Returning with the merged dataset and the associated location
        merged_dataset.to_csv('merged_dataset.csv')
        return merged_dataset
    
    def simulate_microgrid(location):
        # Creating microgrid list
        microgrid = []
        # Defining helper variables
        date = start_date
        index_start = 0
        iterator = 0
        # Calling merge_data function
        dataset = merge_data(location)
        # Generate a copy from data, which can be modified
        iterated_dataset = dataset.copy()

        # Iterating through the dataset
        for i in range(len(iterated_dataset)):
            # Correcting timestamps with year data
            iterated_dataset.loc[i, 'time'] = str(date.year) + '-' + dataset.loc[i, 'time']
            # datetime.strptime cannot handle the date: Feb 29
            try:
                # Parsing the date
                iterated_dataset.loc[i, 'time'] = datetime.strptime(iterated_dataset.loc[i, 'time'], '%Y-%m-%d %H:%M:%S')
            except Exception as Febr29_detected:
                print(f"datetime.strptime cannot handle Feb 29: {Febr29_detected}")
                # Dropping Febr29
                iterated_dataset.drop(i, inplace=True)
                dataset.drop(i, inplace=True)

        for i in range(len(iterated_dataset)):
            # Finding the start date of the year
            if iterated_dataset['time'].iloc[i].strftime('%m-%d') == date.strftime('%m-%d'):
                # Setting index_start and iterator
                index_start = i
                iterator = i
                # Breaking the cycle after index_start was found
                break

        # Checking if index_start exists
        if index_start != -1:
            # Iterating as long as all the microgrid data are not saved
            while len(microgrid) < days_to_simulate * 24:
                iterated_dataset.loc[iterator, 'time'] = str(date.year) + '-' + dataset['time'].iloc[iterator]
                # datetime.strptime cannot handle the date: Feb 29
                try:
                    # Parsing the date
                    iterated_dataset.loc[iterator, 'time'] = datetime.strptime(iterated_dataset.loc[iterator, 'time'], '%Y-%m-%d %H:%M:%S')
                except Exception as Febr29_detected:
                    print(f"datetime.strptime cannot handle Feb 29: {Febr29_detected}")
                    # Dropping Febr29
                    iterated_dataset.drop(i, inplace=True)
                    dataset.drop(i, inplace=True)

                # Finding common days with the date
                if iterated_dataset['time'].iloc[iterator].strftime('%m-%d') == date.strftime('%m-%d'):
                    # Appending data to microgrid
                    microgrid.append(iterated_dataset.iloc[iterator])
                    # After 24 data rows, jumping to the next day
                    if iterator % 24 == 23:
                        date += pd.Timedelta(days=1)

                # Increasing iterator
                iterator += 1
                # Resetting iterator, if necessary
                iterator %= len(iterated_dataset)
            # Converting microgrid to data frame
            microgrid = pd.DataFrame(data = microgrid)
            microgrid.to_csv('microgrid.csv')
            # Returning simulated microgrid
            return microgrid
        else:
            print("No date found")
            return None
        
    def simulate_battery(location):
        #Creating lists and stack variables
        battery_values = []
        grid_usage = []
        energy_consumption_battery = 0
        #Calling merge_dataset function
        merged_dataset = merge_data(location)
        for i in range(len(merged_dataset)):
            #Defining energy balance: last genereted - last consumpted
            balance = merged_dataset["P"].iloc[i] - merged_dataset["total energy consumption"].iloc[i]
            #Define start case
            if i == 0:
                #Balance negative, battery is not charged
                if balance <= 0:
                    battery_values.append(0)
                    grid_usage.append(balance)
                #Balance positive and smaller than charging capacity
                elif balance > 0 and balance <= battery_charge / battery_eff:
                    battery_values.append(balance * battery_eff)
                    grid_usage.append(0)
                #Balance positive and reaches battery charging capacity
                else:
                    battery_values.append(battery_charge * battery_eff)
                    grid_usage.append(-(balance - battery_charge))
            #Define battery state recursive
            else:
                # Fully charging speed, not fully charged battery
                if balance >= battery_charge and (battery_values[i - 1] + battery_charge * battery_eff) <= battery_capacity:
                    energy_consumption_battery = 0
                    battery_values.append(battery_values[i - 1] + battery_charge * battery_eff)
                    grid_usage.append(-(balance - battery_charge))
                # Fully charging speed, fully charged battery
                elif balance >= battery_charge and (battery_values[i - 1] + battery_charge * battery_eff) > battery_capacity:
                    energy_consumption_battery = 0
                    battery_values.append(battery_capacity)
                    grid_usage.append(-(balance - battery_charge) - (battery_charge - (battery_capacity - battery_values[i - 1]) / battery_eff))
                # Not fully charging speed, not fully charged battery
                elif balance < battery_charge and balance >= 0 and (battery_values[i - 1] + balance * battery_eff) <= battery_capacity:
                    energy_consumption_battery = 0
                    battery_values.append(battery_values[i - 1] + balance * battery_eff)
                    grid_usage.append(0)
                # Not fully charging speed, fully charged battery
                elif balance < battery_charge and balance >= 0 and (battery_values[i - 1] + balance * battery_eff) > battery_capacity:
                    energy_consumption_battery = 0
                    battery_values.append(battery_capacity)
                    grid_usage.append(-(balance - (battery_capacity - battery_values[i - 1]) / battery_eff))
                # Fully discharging speed, not fully discharged battery
                elif balance <= battery_discharge * battery_eff and (battery_values[i - 1] + battery_discharge) >= 0:
                    energy_consumption_battery = -battery_discharge
                    battery_values.append(battery_values[i - 1] + battery_discharge)
                    grid_usage.append(balance + battery_discharge)
                # Fully discharging speed, fully discharged battery
                elif balance <= battery_discharge * battery_eff and (battery_values[i - 1] + battery_discharge) < 0:
                    energy_consumption_battery = battery_values[i - 1]
                    battery_values.append(0)
                    grid_usage.append(balance + battery_discharge - (battery_values[i - 1] + battery_discharge))
                # Not fully discharging speed, not fully discharged battery
                elif balance > battery_discharge * battery_eff and balance < 0 and (battery_values[i - 1] + battery_discharge) >= 0:
                    energy_consumption_battery = balance / battery_eff
                    battery_values.append(battery_values[i - 1] + (balance / battery_eff))
                    grid_usage.append(0)
                # Not fully discharging speed, fully discharged battery
                elif balance > battery_discharge * battery_eff and balance < 0 and (battery_values[i - 1] + battery_discharge) < 0:
                    energy_consumption_battery = battery_values[i - 1]
                    battery_values.append(0)
                    grid_usage.append(-battery_values[i - 1] - battery_discharge)
                else:
                    print("Error in battery simulation")
        #Adding battery state to the data set               
        merged_dataset["battery"] = battery_values
        #Saving data in a CSV file
        merged_dataset.to_csv('merged_fully_dataset.csv')
        return merged_dataset
    
    def simulate_microgrid_with_battery(location):
        #Calling simulate_microgrid function
        microgrid = simulate_microgrid(location)
        #creating a timestamp column for microgrid
        microgrid["timestamp"] = pd.to_datetime(microgrid["time"])
        #Modifing time column
        microgrid["time"] = microgrid['timestamp'].dt.strftime('%m-%d %H:%M:%S')
        #Parsing in data frame, cutting all columns excepted time and timestamp
        microgrid = pd.DataFrame(microgrid[['time', 'timestamp']])
        #Calling get_household_data function
        battery = pd.DataFrame(data = simulate_battery(location))
        # Setting timestamp for battery
        battery["timestamp"] = 0
        pd.to_datetime(battery['timestamp'])
        # Define helper list
        data_list = []
        #Iterating through the microgrid rows
        for i in range(days_to_simulate * 24):
            #Getting index of microgrid
            battery.loc[microgrid.index[i], "timestamp"] = pd.to_datetime(microgrid['timestamp'].iloc[i])
            #Getting microgrid values 
            data_list.append(battery.iloc[microgrid.index[i]])
        #Casting data_list to data frame
        data_list = pd.DataFrame(data = data_list)
        #Grouping by timestamp
        data_list.groupby('timestamp')
        #Dropping time column
        data_list = data_list.drop(columns=['time'])
        data_list.to_csv('microgrid.csv')
        # Returning simulated microgrid
        return data_list
    
    #Calling simulate_microgrid_with_battery funciton
    data = simulate_microgrid_with_battery(location)
    
    
    timestamp = data['timestamp']
    solar_energy = data['pv']
    consumption = data['total energy consumption']

    # Zeitreihen-Diagramm erstellen
    plt.figure(figsize=(14, 7))
    plt.plot(timestamp, solar_energy, label='Solar Energy (kWh)', color='orange')
    plt.plot(timestamp, consumption, label='Total Energy Consumption (kWh)', color='blue')

    # Achsenbeschriftungen und Titel hinzufügen
    plt.xlabel('Timestamp')
    plt.ylabel('Energy (kWh)')
    plt.title('Solar Energy Production vs. Total Energy Consumption')
    plt.legend()

    # Datumformat für x-Achse anpassen
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))

    # Diagramm anzeigen
    plt.tight_layout()
    plt.show()
    
    
    # Daten für den Energieverbrauch pro Gerät
    devices = ['Refrigerator', 'Washing Machine', 'Heat Pump']
    energy_consumption = [data['refrigerator'].sum(), data['washing machine'].sum(), data['heat pump'].sum()]

    # Balkendiagramm erstellen
    plt.figure(figsize=(10, 6))
    plt.bar(devices, energy_consumption, color=['blue', 'green', 'red'])

    # Achsenbeschriftungen und Titel hinzufügen
    plt.xlabel('Devices')
    plt.ylabel('Energy Consumption (kWh)')
    plt.title('Energy Consumption by Device')

    # Diagramm anzeigen
    plt.tight_layout()
    plt.show()
    
    # Daten für Streudiagramm
    poa_direct = data['poa_direct']
    temp_air = data['temp_air']

    # Streudiagramm erstellen
    plt.figure(figsize=(8, 6))
    plt.scatter(temp_air, poa_direct, color='green', alpha=0.5)

    # Achsenbeschriftungen und Titel hinzufügen
    plt.xlabel('Air Temperature (°C)')
    plt.ylabel('POA Direct (W/m^2)')
    plt.title('Scatter Plot: Air Temperature vs. POA Direct')

    # Diagramm anzeigen
    plt.tight_layout()
    plt.show()
    
    # Daten für Histogramm
    wind_speed = data['wind_speed']

    # Histogramm erstellen
    plt.figure(figsize=(8, 6))
    plt.hist(wind_speed, bins=20, color='skyblue', edgecolor='black')

    # Achsenbeschriftungen und Titel hinzufügen
    plt.xlabel('Wind Speed (m/s)')
    plt.ylabel('Frequency')
    plt.title('Histogram: Wind Speed Distribution')

    # Diagramm anzeigen
    plt.tight_layout()
    plt.show()
    
    data['weekday'] = data['timestamp'].dt.dayofweek
    average_consumption_by_weekday = data.groupby('weekday')['total energy consumption'].mean()
    # Namen der Wochentage für die Darstellung
    weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']

    # Plot erstellen
    plt.figure(figsize=(10, 6))
    plt.bar(weekdays, average_consumption_by_weekday)
    plt.xlabel('Wochentag')
    plt.ylabel('Durchschnittsverbrauch')
    plt.title('Durchschnittsverbrauch nach Wochentag')
    plt.show()
    
main()