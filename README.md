## Home Assistant Custom Component: Hjem-Is
Home Assistant Custom Component: Hjem-Is



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


