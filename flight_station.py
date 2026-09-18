import datetime
import math
import time
import os
import sys
import numpy as np
from skyfield.api import load, wgs84

# Ground Station: Andhra Pradesh
GS_LAT = 17.0000
GS_LON = 81.8000
GS_ELEVATION_M = 25.0
ground_station = wgs84.latlon(GS_LAT, GS_LON, elevation_m=GS_ELEVATION_M)

ts = load.timescale()

# Curated ISRO Fleet Catalog
FLEET = {
    "1": (44804, "CARTOSAT-3", "High-Resolution Optical Imaging [LEO]"),
    "2": (54361, "OCEANSAT-3 (EOS-06)", "Ocean Surface & Atmospheric Payload [LEO]"),
    "3": (41783, "SCATSAT-1", "Weather Forecasting & Wind Vector Tracking [LEO]"),
    "4": (45026, "GSAT-30", "High-Power C/Ku-band Telecommunications [GEO]"),
}

print("\n" + "="*70)
print("             ISRO FLEET ASSET MISSION CONSOLE                 ")
print("="*70)
for key, (norad_id, name, desc) in FLEET.items():
    print(f" [{key}] NORAD #{norad_id:<5} : {name:<20} | {desc}")
print("="*70)

choice = input("Select an ISRO asset to track [1-4] (default: 1): ").strip()
target_norad, display_name, mission_desc = FLEET.get(choice, FLEET["1"])

# Direct ephemeris ingest for the selected NORAD catalog number
ephem_url = f'https://celestrak.org/NORAD/elements/gp.php?CATNR={target_norad}&FORMAT=tle'
print(f"\nFetching live orbital element vector for NORAD #{target_norad}...")

try:
    satellites = load.tle_file(ephem_url, reload=True)
    if not satellites:
        raise ValueError("Empty ephemeris received.")
    target_sat = satellites[0]
except Exception as e:
    print(f"Error: Unable to fetch orbital data for NORAD #{target_norad}: {e}")
    sys.exit(1)

# Pass Predictor
def compute_next_passes():
    t0 = ts.now()
    t1 = ts.utc(t0.utc_datetime() + datetime.timedelta(days=2))
    times, events = target_sat.find_events(ground_station, t0, t1, altitude_degrees=15.0)
    event_names = ['Rise (AOS)', 'Culmination (Max Elevation)', 'Set (LOS)']
    
    print("\n" + "="*70)
    print(f" OBSERVER SITE : ({GS_LAT:.2f}°N, {GS_LON:.2f}°E) | TARGET: {target_sat.name}")
    print(f" MISSION ROLE  : {mission_desc}")
    print(" UPCOMING GROUND STATION PASSES (NEXT 48 HOURS, >15° Elevation):")
    print("="*70)
    
    if len(times) == 0:
        print(" No passes above 15° horizon elevation detected (or craft is in Geostationary Orbit).")
    else:
        for ti, event in zip(times, events):
            utc_dt = ti.utc_datetime()
            ist_dt = utc_dt + datetime.timedelta(hours=5, minutes=30)
            difference = target_sat - ground_station
            topocentric = difference.at(ti)
            alt, az, distance = topocentric.altaz()
            print(f" [{ist_dt.strftime('%Y-%m-%d %H:%M:%S')} IST] - {event_names[event]:<28} | Az: {az.degrees:6.2f}° | El: {alt.degrees:5.2f}°")
    print("="*70 + "\n")

compute_next_passes()
input("Press Enter to launch live telemetry stream...")

try:
    while True:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        t = ts.utc(now_utc.year, now_utc.month, now_utc.day, 
                   now_utc.hour, now_utc.minute, now_utc.second + now_utc.microsecond/1e6)
        
        geocentric = target_sat.at(t)
        subpoint = geocentric.subpoint()
        
        # Velocity conversion
        AU_KM = 149597870.7
        DAY_SEC = 86400.0
        vx, vy, vz = geocentric.velocity.au_per_d
        v_vector = np.array([vx, vy, vz]) * (AU_KM / DAY_SEC)
        speed = np.linalg.norm(v_vector)
        
        # Topocentric coordinates
        difference = target_sat - ground_station
        topocentric = difference.at(t)
        alt, az, distance = topocentric.altaz()
        
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("="*65)
        print("          ISRO MISSION TELEMETRY & TRACKING CONSOLE          ")
        print("="*65)
        print(f" CRAFT NAME       : {target_sat.name} (NORAD #{target_norad})")
        print(f" MISSION PROFILE  : {mission_desc}")
        print(f" UTC TIMESTAMP    : {now_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} UTC")
        print("-" * 65)
        print(" [ORBITAL DYNAMICS]")
        print(f" Sub-Sat Latitude : {subpoint.latitude.degrees:9.4f}°")
        print(f" Sub-Sat Longitude: {subpoint.longitude.degrees:9.4f}°")
        print(f" Altitude (AGL)   : {subpoint.elevation.km:9.2f} km")
        print(f" Scalar Velocity  : {speed:9.3f} km/s  ({speed * 3600:.1f} km/h)")
        print("-" * 65)
        print(" [GROUND ANTENNA POINTING ANGLES]")
        print(f" Azimuth (Bearing): {az.degrees:9.2f}°")
        print(f" Elevation Angle  : {alt.degrees:9.2f}°")
        print(f" Slant Range (LOS): {distance.km:9.2f} km")
        
        if alt.degrees > 0:
            print(" LINK STATUS      : >> IN LINE OF SIGHT (AOS ACTIVE) <<")
        else:
            print(" LINK STATUS      : HORIZON OCCLUDED (LOS INACTIVE)")
        print("="*65)
        print(" Press Ctrl+C to stop.")
        
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nTelemetry stream disconnected.")
