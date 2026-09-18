import datetime
import matplotlib.pyplot as plt
import numpy as np
from skyfield.api import load

# 1. Load astronomical timescale
ts = load.timescale()
now = datetime.datetime.now(datetime.timezone.utc)

# 2. Ingest real-world TLE data from CelesTrak
print("Fetching live orbital data from CelesTrak...")
stations_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle'
satellites = load.tle_file(stations_url)
by_name = {sat.name: sat for sat in satellites}

# Select the International Space Station
iss = by_name['ISS (ZARYA)']
print(f"Propagating orbit for: {iss.name} (NORAD ID: {iss.model.satnum})")

# 3. Propagate the orbit forward across 95 minutes (~1 revolution)
minutes_range = np.linspace(0, 95, 190)
times = ts.utc(now.year, now.month, now.day, now.hour, now.minute + minutes_range)

geocentric = iss.at(times)
subpoint = geocentric.subpoint()

latitudes = subpoint.latitude.degrees
longitudes = subpoint.longitude.degrees

# Instantaneous position (t = 0)
current_time = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)
current_state = iss.at(current_time).subpoint()
curr_lat = current_state.latitude.degrees
curr_lon = current_state.longitude.degrees
curr_alt = current_state.elevation.km

print("\n" + "="*45)
print(f" LIVE POSITION AT {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f" Latitude  : {curr_lat:.4f}°")
print(f" Longitude : {curr_lon:.4f}°")
print(f" Altitude  : {curr_alt:.2f} km")
print("="*45 + "\n")

# 4. Plot Ground Track on 2D Mercator Projection
plt.figure(figsize=(12, 6))
plt.xlim(-180, 180)
plt.ylim(-90, 90)
plt.grid(True, linestyle='--', alpha=0.5)

# Handle trajectory wraparound at +/- 180 longitude
diff = np.diff(longitudes)
split_indices = np.where(np.abs(diff) > 180)[0] + 1
lon_segments = np.split(longitudes, split_indices)
lat_segments = np.split(latitudes, split_indices)

for seg_lon, seg_lat in zip(lon_segments, lat_segments):
    plt.plot(seg_lon, seg_lat, color='dodgerblue', linewidth=2, 
             label='Predicted Trajectory' if seg_lon is lon_segments[0] else "")

# Mark live position
plt.scatter(curr_lon, curr_lat, color='crimson', s=100, zorder=5, label='Live Spacecraft Position')
plt.annotate(f" ISS ({curr_lat:.1f}°, {curr_lon:.1f}°)\n Alt: {curr_alt:.0f} km", 
             (curr_lon + 3, curr_lat + 3), fontsize=9, fontweight='bold', color='darkred')

plt.title(f"Spacecraft Orbital Ground Track: {iss.name}\nTimestamp (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}", fontsize=12)
plt.xlabel("Longitude (°)")
plt.ylabel("Latitude (°)")
plt.legend(loc='lower left')
plt.tight_layout()

# Save the plot
plt.savefig("iss_orbit_track.png", dpi=300)
print("Ground track map saved as 'iss_orbit_track.png'.")
