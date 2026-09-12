# IP Address Tracker (BEFORE USING - READ LIMITAION SECTION GIVEN BELOW)
Constraint Based Geolocation Tracking - Multivantage IP Pinging Rount Trip Time to Distance conversation

This tool works best with Hacking OS (Kali Linux etc)

Robust multi-vantage IP geolocation using RTT-weighted centroiding of global ping measurements.

This small CLI tool dispatches GlobalPing probes to a target IP address or hostname, collects per-probe minimum RTTs, and estimates the target's geographic coordinates by computing an RTT-weighted centroid of valid probes. The result includes an estimated latitude/longitude and a Google Maps link.

---

## Features

- Query GlobalPing's measurement API to collect global ping measurements.
- Filter out probes with errors or missing coordinates.
- Compute an RTT-weighted geographic centroid (closer probes have larger weight).
- Simple CLI with options for probe count and API token.

---

## Limitation
For the multivantage-point measurements, I use the GlobalPing API service. Because its probes are primarily located in Europe, IP tracking works most reliably for targets in Europe. Tracking IP addresses in other regions may produce inaccurate coordinates due to increased intercontinental network latency and noise.

## Requirements

- Python 3.8+ (works with modern Python 3.x)
- requests library

Install the dependency:

```bash
pip install requests
```

(You may prefer to use a virtual environment.)

---

## Installation

Clone the repository (if not already):

```bash
git clone https://github.com/HadiMuhammed/IP-Address-Tracker.git
cd IP-Address-Tracker
```

No additional build step is required â€” the tool is a single Python script: `ip_track.py`.

---

## Usage

Basic usage:

```bash
python ip_track.py <target>
```

Examples:

```bash
# Estimate the location of Google's public DNS
python ip_track.py 8.8.8.8

# Use a custom probe limit (number of probes to request)
python ip_track.py example.com --limit 20

# Provide a GlobalPing API token as an argument
python ip_track.py 1.2.3.4 --token YOUR_GLOBALPING_TOKEN

# Or set the token via environment variable
export GLOBALPING_TOKEN=YOUR_GLOBALPING_TOKEN
python ip_track.py 1.2.3.4
```

Options:

- target (positional): Target IP address or domain to analyze.
- -l, --limit: Number of global probes to query (default: 15).
- -t, --token: GlobalPing API token for higher rate limits (or set `GLOBALPING_TOKEN` env var).

---

## Example output

After collecting measurements the script prints the estimated coordinates and a Google Maps link:

```
[*] Successfully gathered live RTT metrics from 12 valid probes.
[*] Computing RTT-weighted geographic center...

[+] Estimation Successful:
Estimated Latitude:  37.3854Â°
Estimated Longitude: -122.0838Â°

Google Maps Link:
https://www.google.com/maps/search/?api=1&query=37.3854,-122.0838
```

---

## How it works (Algorithm)

1. The script posts a measurement request to GlobalPing's API to create ping probes against the target (the API returns a measurement id).
2. It polls the measurement result endpoint until results are ready (or times out).
3. For each successful probe result containing geographic coordinates and RTT stats, the script extracts the probe's latitude, longitude, and minimum RTT (ms).
4. It computes a weighted centroid where each probe's weight is 1 / (RTT^2) so that nearby probes (lower RTT) influence the estimate more strongly:
   - weighted_lat = sum(lat_i * weight_i)
   - weighted_lon = sum(lon_i * weight_i)
   - final_lat = weighted_lat / sum(weights)
   - final_lon = weighted_lon / sum(weights)

This approach reduces the influence of distant or high-latency probes.

---

## Notes, limitations & troubleshooting

- Rate limits: If you receive HTTP 429, you have exceeded the free hourly quota for your IP address. You can pass a GlobalPing API token via `--token` or `GLOBALPING_TOKEN` environment variable to use a higher quota.
- Timeout: The script polls the measurement for up to ~20 iterations with a 3-second sleep between polls (â‰ˆ60 seconds of polling plus request time). If*
