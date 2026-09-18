import datetime
import math
import time
import os
import numpy as np
from skyfield.api import load, wgs84

# -------------------------------------------------------------
# 1. GROUND STATION CONFIGURATION (Observer Site)
# Default set to Andhra Pradesh region (17.00° N, 81.80° E, 25m alt)
# Modify these coordinates if you want a different ground station.
# -------------------------------------------------------------
GS_LAT = 17.0000
GS_LON = 81.8000
GS_ELEVATION_M = 25.0
ground_station = wgs84.latlon(GS_LAT, GS_LON, elevation_m=GS_ELEVATION_M)

print("Initializing Spaceflight Telemetry Engine...")
ts = load.timescale()

# Fetch latest authoritative ephemeris
stations_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle'
satellites = load.tle_file(stations_url)
by_name = {sat.name: sat for sat in satellites}
target_sat = by_name['ISS (ZARYA)']

# -------------------------------------------------------------
# 2. ORBITAL PASS PREDICTOR (Next 48 Hours)
# -------------------------------------------------------------
def compute_next_passes():
    t0 = ts.now()
    t1 = ts.utc(t0.utc_datetime() + datetime.timedelta(days=2))
    
    # Calculate flyovers where elevation exceeds 15 degrees above horizon
    times, events = target_sat.find_events(ground_station, t0, t1, altitude_degrees=15.0)
    
    event_names = ['Rise (AOS)', 'Culmination (Max Elevation)', 'Set (LOS)']
    print("\n" + "="*70)
    print(f" GROUND STATION: ({GS_LAT:.2f}°N, {GS_LON:.2f}°E) | TARGET: {target_sat.name}")
    print(" UPCOMING SATELLITE PASSES (NEXT 48 HOURS, >15° Elevation):")
    print("="*70)
    
    if len(times) == 0:
        print(" No passes above 15° horizon elevation detected in the next 48 hours.")
    else:
        for ti, event in zip(times, events):
            utc_dt = ti.utc_datetime()
            # Convert to Indian Standard Time (IST = UTC + 5:30)
            ist_dt = utc_dt + datetime.timedelta(hours=5, minutes=30)
            event_name = event_names[event]
            
            # Compute topocentric coordinates at this event instant
            difference = target_sat - ground_station
            topocentric = difference.at(ti)
            alt, az, distance = topocentric.altaz()
            
            print(f" [{ist_dt.strftime('%Y-%m-%d %H:%M:%S')} IST] - {event_name:<28} | Az: {az.degrees:6.2f}° | El: {alt.degrees:5.2f}°")
    print("="*70 + "\n")

# Run pass calculation once before launching the real-time loop
compute_next_passes()
input("Press Enter to initiate live telemetry stream...")

# -------------------------------------------------------------
# 3. REAL-TIME FLIGHT TELEMETRY STREAM
# -------------------------------------------------------------
try:
    while True:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        t = ts.utc(now_utc.year, now_utc.month, now_utc.day, 
                   now_utc.hour, now_utc.minute, now_utc.second + now_utc.microsecond/1e6)
        
        # Geocentric state vector (Earth-centered inertial frame)
        geocentric = target_sat.at(t)
        subpoint = geocentric.subpoint()
        
        # Velocity calculation: derived from state vector velocity (km/s)
        # Skyfield provides velocity in AU/day; convert to km/s
        AU_KM = 149597870.7
        DAY_SEC = 86400.0
        vx, vy, vz = geocentric.velocity.au_per_d
        v_vector_kms = np.array([vx, vy, vz]) * (AU_KM / DAY_SEC)
        scalar_velocity = np.linalg.norm(v_vector_kms)
        
        # Relative ground station vector (Topocentric frame: Azimuth, Elevation, Slant Range)
        difference = target_sat - ground_station
        topocentric = difference.at(t)
        alt, az, distance = topocentric.altaz()
        
        # Clear screen for live dashboard refresh
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("="*65)
        print("          MISSION OPERATIONS: LIVE FLIGHT TELEMETRY          ")
        print("="*65)
        print(f" TARGET CRAFT     : {target_sat.name} (NORAD #{target_sat.model.satnum})")
        print(f" UTC TIMESTAMP    : {now_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]} UTC")
        print("-" * 65)
        print(" [ORBITAL STATE]")
        print(f" Sub-Sat Latitude : {subpoint.latitude.degrees:9.4f}°")
        print(f" Sub-Sat Longitude: {subpoint.longitude.degrees:9.4f}°")
        print(f" Altitude (AGL)   : {subpoint.elevation.km:9.2f} km")
        print(f" Orbital Velocity : {scalar_velocity:9.3f} km/s  ({scalar_velocity * 3600:.1f} km/h)")
        print("-" * 65)
        print(" [GROUND STATION TRACKING / ANTENNA POINTING]")
        print(f" Azimuth (Bearing): {az.degrees:9.2f}°")
        print(f" Elevation Angle  : {alt.degrees:9.2f}°")
        print(f" Slant Range (LOS): {distance.km:9.2f} km")
        
        # Line-of-sight acquisition status
        if alt.degrees > 0:
            print(" SIGNAL STATUS    : >> IN LINE OF SIGHT (AOS ACTIVE) <<")
        else:
            print(" SIGNAL STATUS    : HORIZON OCCLUDED (LOS INACTIVE)")
        print("="*65)
        print(" Press Ctrl+C to disconnect flight telemetry.")
        
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nTelemetry connection closed by user.")
