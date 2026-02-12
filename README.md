## Home Assistant Custom Component: 🍦 Hjem-Is

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/supersej/Hjem-IS/releases)
[![maintainer](https://img.shields.io/badge/maintainer-Supersej-blue.svg)](https://github.com/supersej)
[![buy_me_a_coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/darkdk)



A sensor for getting information about the next time Hjem-Is comes to visit. 
It will automatically pull your coordinates from HA (if set).
If not set you can set it manually.
You give it coordinates and it will list the closest stop for you to choose from.
You can add multiple stops if you want to.

After installing the integration using HACS and restarting your server you simply add a Hjem-Is stop by clicking the button below or by going to Devices & Services and adding it from there.

[![add-integration-shield]][add-integration]


|Parameter| What to put |
|--|--|
| Name | This is the name you want for the sensor in Home Assistant |
| Latitude | Latitude coordinate close to the stop you want |
| Longitude | Longitude coordinate close to the stop you want |


**Attributes:**
```
id
Address
Google Estimate time
Origintal Google estimate time
Coordinates
  latitude
  longitude
Position
Arrival date
Car stop present
depo
Upcomming plan events dates
Point visited
Distance
```


