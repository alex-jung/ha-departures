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
1. In the `custom_components` directory (folder) create a new folder called `vgn_departures`.
1. Download all the files from the `custom_components/vgn_departures/` directory (folder) in this repository.
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
Integration will load all available stations from GTFS data source.
> NOTE: if your station is not present in the station list, integration will unfortunately not work 

Start enter your station name in field to reduce the list and then choose station you are interesting in from the list:\
![image](https://github.com/user-attachments/assets/e65635ec-2bc6-4eba-b73d-7b476bea1049)

In the next step you can select directions splitted by transport types and trip names:
![image](https://github.com/user-attachments/assets/96f402dd-a5c6-44d2-ad61-677adf38f7fe)

As result new sensor(s) will be created:
![image](https://github.com/user-attachments/assets/39ca6db8-8660-410d-9e2b-e4a92e055609)

### Reconfigure an entry
The directions you choosen in the [previous step](#Configure-a-new-station) can be reconfigured via GUI:
![image](https://github.com/user-attachments/assets/03864ffd-2420-4ca0-97e8-03d64f0189ae)

Here you can remove obsolete directions or add new by selection them in dialog.

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

### Option 3 (vgn-departures-card)
> Development is ongoing