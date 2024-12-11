# Departures
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![Static Badge](https://img.shields.io/badge/code_owner-alex--jung-green)
![GitHub Release](https://img.shields.io/github/v/release/alex-jung/ha-deaprtures)
![GitHub License](https://img.shields.io/github/license/alex-jung/ha-departures)

![Big_512](https://github.com/user-attachments/assets/67e3ba87-94ea-4d27-b891-f6cbab779830)

This integration provides information about next departure(s) for different transport types like Bus, Subway, Tram etc.

> The currently release uses only **static time plans** extracted from [GTFS](https://gtfs.org/documentation/schedule/reference/) files.
> Implementation of real time departures (e.g. via REST-API) is ongoing and will be available first in releases greater 2.0.0

***
## Installation

### HACS Installation (recommended)

> HACS integration is ongoing!

Until it's finished you can install the integration by adding this repository as a custom repository in HACS, and install as normal.

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `ha_departures`.
1. Download all the files from the `custom_components/ha_departures/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant

## Configuration

### Start integration dialog
The configuration of integration is made via Home Assistant GUI
1. Open `Settings` / `Devices & services`
2. Click on `Add Integration` button
3. Search for `Public Transport Departures`
4. Click on integration to start [configuration dialog](#Configure-a-new-station)

### Configure a new station
#### Step 1 - Choose the API endpoint providing departures information and enter stop name 
> Currently is only `Verkehrsverbund Großraum Nürnberg` is supported. If you know an endpoint for you region, let me know. I will add the endpoint to the list.

![image](https://github.com/user-attachments/assets/6341bb9c-58b1-4d94-bfc5-277dea779d37)


#### Step 2 - Choose stop
> In this step `ha-departures` integration will search for all locations matching provided stop name.
> Please select one of them from the list 

![image](https://github.com/user-attachments/assets/88ca190f-b6dd-426d-b0ed-62929282645f)

#### Step 3 - Choose the connections
> You will get list of connections provided by the API for selected stop
> Select all connection(s) you are interesting in and click on `OK`

![image](https://github.com/user-attachments/assets/2e51a94b-ef8a-4422-8e3b-dec921a1a366)

As result a new `Hub` is created incl. new sensor(s) for each direction you selected in previous step:
![image](https://github.com/user-attachments/assets/e3d4de2c-adda-4414-8f8a-d8c52e0bdd38)

![image](https://github.com/user-attachments/assets/7a54e888-df7f-4098-a644-f93279f043d7)

### Reconfigure an entry
You can any time add or remove connections to existing `hub's` (stop locations)
![image](https://github.com/user-attachments/assets/425685e2-743d-45ea-90da-7ef2b31b177e)

Just click on `configure` button, select or deselct the connections and click on `OK`, Integration will remove obsolete and add new connections to the Home Assistant.

## Usage in dashboard

### Option 1 (show departure time)
Add a custom template sensor in your _configuration.yaml_
```yaml
sensor:
  - platform: template
    sensors:
      furth_197:
        friendly_name: 'Fürth Hauptbahnhof - Bus 179 - Fürth Süd(only time)'
        value_template: "{{ (as_datetime(states('sensor.furth_hauptbahnhof_bus_179_furth_sud'))).strftime('%H:%m') }}"
```
Add entity (or entites) card to your Dashboars(don't forget to reload yaml before)\
```yaml
type: entities
entities:
  - entity: sensor.furth_197
    name: Fürth Hauptbahnhof - Bus 179 - Fürth Süd
    icon: mdi:bus
```
![image](https://github.com/user-attachments/assets/d813c9e4-0d5f-498e-81de-6abc88430c8c)

### Option 2 (with time-bar-card)
To get more fancy stuff, you can use e.g. [time-bar-card](https://github.com/rianadon/timer-bar-card) to visualize remaining time to next departure:
yaml conifuguration:
```yaml
type: custom:timer-bar-card
name: Abfahrten Fürth-Hbf
invert: true
entities:
  - entity: sensor.furth_hauptbahnhof_u_bahn_u1_furth_hardhohe
    bar_width: 30%
    name: U1 - Hardhöhe
    guess_mode: true
    end_time:
      state: true
  - entity: sensor.furth_hauptbahnhof_bus_179_furth_sud
    bar_width: 30%
    name: 179 - Fürth Süd
    guess_mode: true
    end_time:
      state: true
```
Result looks like there:\
![ezgif-3-136a167cd5](https://github.com/user-attachments/assets/3b8b8a09-1067-4d90-924a-729616c6e765)

### Option 3 (ha-departures-card)
> Development is ongoing
