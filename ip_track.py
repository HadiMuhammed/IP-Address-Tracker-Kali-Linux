import argparse
import math
import os
import sys
import time
import requests

GLOBALPING_API_URL = "https://api.globalping.io/v1/measurements"

def fetch_live_landmarks(target_ip, limit=20, continent="EU", api_token=None):
    payload = {
        "type": "ping",
        "target": target_ip,
        "limit": limit,
        "measurementOptions": {"packets": 3},
    }
    
    if continent:
        payload["locations"] = [{"continent": continent.upper()}]

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    loc_str = f" in {continent.upper()}" if continent else " globally"
    print(f"[*] Dispatching GlobalPing probes{loc_str} to target {target_ip} (limit: {limit})...")
    
    try:
        response = requests.post(GLOBALPING_API_URL, json=payload, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[-] Network error connecting to Globalping API: {e}")
        sys.exit(1)

    if response.status_code == 429:
        print("\n[-] Rate limit exceeded (429). Pass a token using --token or GLOBALPING_TOKEN env.")
        sys.exit(1)

    if response.status_code != 202:
        print(f"[-] Failed to create measurement: {response.status_code} - {response.text}")
        sys.exit(1)

    data = response.json()
    measurement_id = data.get("id")
    print(f"[*] Measurement ID: {measurement_id}. Awaiting results...")

    result_url = f"{GLOBALPING_API_URL}/{measurement_id}"
    for _ in range(25):
        time.sleep(3)
        try:
            res = requests.get(result_url, headers=headers, timeout=10)
            result_data = res.json()
        except requests.exceptions.RequestException:
            continue

        if result_data.get("status") == "finished":
            raw_results = result_data.get("results", [])
            landmarks = []

            for item in raw_results:
                probe = item.get("probe", {})
                result_block = item.get("result", {})

                if "error" in result_block or not probe.get("latitude") or not probe.get("longitude"):
                    continue

                stats = result_block.get("stats", {})
                min_rtt = stats.get("min")

                if min_rtt is not None and min_rtt > 0:
                    landmarks.append({
                        "name": f"{probe.get('city', 'Unknown')}, {probe.get('country', 'Unknown')}",
                        "lat": float(probe["latitude"]),
                        "lon": float(probe["longitude"]),
                        "min_rtt_ms": float(min_rtt),
                    })

            return landmarks

    print("[-] Timed out waiting for Globalping results.")
    sys.exit(1)

def estimate_coordinates_spherical_weighted(landmarks):
    if not landmarks:
        return {"success": False, "message": "No valid landmark data received."}

    total_weight = 0.0
    x_sum = 0.0
    y_sum = 0.0
    z_sum = 0.0
    valid_landmarks = 0

    for lm in landmarks:
        rtt = lm["min_rtt_ms"]
        # Exponential decay weight prevents single jitter spikes from skewing results
        weight = math.exp(-0.05 * rtt)

        lat_rad = math.radians(lm["lat"])
        lon_rad = math.radians(lm["lon"])

        # Map 2D coordinates to 3D Cartesian space on a unit sphere
        x = math.cos(lat_rad) * math.cos(lon_rad)
        y = math.cos(lat_rad) * math.sin(lon_rad)
        z = math.sin(lat_rad)

        x_sum += x * weight
        y_sum += y * weight
        z_sum += z * weight
        total_weight += weight
        valid_landmarks += 1

    if total_weight == 0 or valid_landmarks == 0:
        return {"success": False, "message": "Calculation weight evaluated to zero."}

    x_avg = x_sum / total_weight
    y_avg = y_sum / total_weight
    z_avg = z_sum / total_weight

    hyp = math.sqrt(x_avg**2 + y_avg**2)
    lat_rad = math.atan2(z_avg, hyp)
    lon_rad = math.atan2(y_avg, x_avg)

    return {
        "lat": math.degrees(lat_rad),
        "lon": math.degrees(lon_rad),
        "success": True,
        "valid_probes": valid_landmarks
    }

def main():
    parser = argparse.ArgumentParser(description="Reliable Multi-Vantage IP Geolocation via Spherical RTT Weighting.")
    parser.add_argument("target", help="Target IP address, domain, or test server.")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Number of global probes to query (default: 20).")
    parser.add_argument("-c", "--continent", default="EU", help="Restrict probes to a specific continent code (e.g., EU, NA). Pass empty string for global.")
    parser.add_argument("-t", "--token", help="Globalping API token.")

    args = parser.parse_args()
    api_token = args.token or os.environ.get("GLOBALPING_TOKEN")

    landmarks = fetch_live_landmarks(
        args.target, 
        limit=args.limit, 
        continent=args.continent if args.continent else None, 
        api_token=api_token
    )
    print(f"[*] Gathered raw metrics from {len(landmarks)} probes.")

    print("[*] Computing spherical RTT-weighted centroid...")
    estimation = estimate_coordinates_spherical_weighted(landmarks)

    if estimation["success"]:
        lat = estimation["lat"]
        lon = estimation["lon"]
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        print("\n[+] Estimation Successful:")
        print(f"Estimated Latitude:  {lat:.4f}°")
        print(f"Estimated Longitude: {lon:.4f}°")
        print(f"Valid Probes Used:   {estimation['valid_probes']}")
        print(f"\nGoogle Maps Link:\n{maps_url}")
    else:
        print(f"[-] Estimation failed: {estimation['message']}")

if __name__ == "__main__":
    main()