#!/usr/bin/env python3
"""
pH Calibration Helper Script for Pioreactor

This script helps calibrate the Vernier FPH-BTA pH probe by:
1. Reading voltage values from standard buffer solutions
2. Calculating linear calibration (slope and intercept)
3. Updating the Pioreactor config with calibration values
4. Optionally restarting the pH sensor to apply changes

Usage:
    python3 calibrate_ph.py
"""

import subprocess
import time
from datetime import datetime


def get_current_voltage():
    """Get the current voltage reading from the pH probe"""
    try:
        result = subprocess.run(
            [
                "mosquitto_sub",
                "-h", "localhost",
                "-t", "pioreactor/+/+/pioreactor_read_serial/0x48_A2",
                "-u", "pioreactor",
                "-P", "raspberry",
                "-C", "5",
                "-W", "3"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse the last reading
        lines = [line for line in result.stdout.strip().split('\n') if line]
        if lines:
            last_reading = lines[-1].split()[-1]
            return float(last_reading)
        return None
    except Exception as e:
        print(f"Error reading voltage: {e}")
        return None


def calculate_calibration(ph_values, voltages):
    """Calculate linear calibration from pH and voltage pairs"""
    import numpy as np

    # Fit linear model: voltage = slope * pH + intercept
    coefs = np.polyfit(ph_values, voltages, 1)
    slope = coefs[0]
    intercept = coefs[1]

    return slope, intercept


def update_config(slope, intercept):
    """Update the Pioreactor config with new calibration values"""
    try:
        # Update slope
        subprocess.run(
            ["bash", "-l", "-c", f"crudini --set ~/.pioreactor/config.ini fph_bta.config slope {slope}"],
            check=True
        )
        # Update intercept
        subprocess.run(
            ["bash", "-l", "-c", f"crudini --set ~/.pioreactor/config.ini fph_bta.config intercept {intercept}"],
            check=True
        )
        print(f"✓ Config updated: slope={slope:.6f}, intercept={intercept:.6f}")
        return True
    except Exception as e:
        print(f"Error updating config: {e}")
        return False


def restart_ph_sensor():
    """Restart the pH sensor to apply new calibration"""
    try:
        # Kill existing sensor
        subprocess.run(["pkill", "-f", "vernier_fph_bta"], check=False)
        time.sleep(2)

        # Start sensor
        subprocess.run(
            ["bash", "-l", "-c", "nohup pio run vernier_fph_bta > /tmp/ph.log 2>&1 &"],
            check=True
        )
        print("✓ pH sensor restarted")
        return True
    except Exception as e:
        print(f"Error restarting sensor: {e}")
        return False


def main():
    print("=" * 60)
    print("Pioreactor pH Calibration Helper")
    print("=" * 60)
    print()
    print("This script will help you calibrate your pH probe using")
    print("standard buffer solutions (typically pH 4, 7, and 10).")
    print()

    # Collect calibration points
    ph_values = []
    voltages = []

    num_points = int(input("How many calibration points? (recommended: 3) "))
    print()

    for i in range(num_points):
        print(f"Calibration Point {i+1}/{num_points}")
        print("-" * 40)

        ph = float(input("  Enter buffer pH value: "))

        print("  Place probe in buffer solution and wait for reading to stabilize...")
        input("  Press Enter when ready to measure voltage")

        # Take multiple readings and average
        print("  Reading voltage...", end="", flush=True)
        readings = []
        for _ in range(5):
            voltage = get_current_voltage()
            if voltage is not None:
                readings.append(voltage)
            time.sleep(0.5)

        if readings:
            avg_voltage = sum(readings) / len(readings)
            print(f" {avg_voltage:.4f}V")
            ph_values.append(ph)
            voltages.append(avg_voltage)
            print(f"  ✓ Recorded: pH {ph} = {avg_voltage:.4f}V")
        else:
            print(" Failed to read voltage")
            print(f"  ✗ Skipping point {i+1}")

        print()

    if len(ph_values) < 2:
        print("Error: Need at least 2 calibration points")
        return

    # Calculate calibration
    print("Calculating calibration...")
    slope, intercept = calculate_calibration(ph_values, voltages)

    print()
    print("Calibration Results:")
    print("-" * 40)
    print(f"  Slope:     {slope:.6f}")
    print(f"  Intercept: {intercept:.6f}")
    print()
    print("Data points:")
    for ph, v in zip(ph_values, voltages):
        calculated_v = slope * ph + intercept
        error = abs(v - calculated_v)
        print(f"  pH {ph:4.1f}: measured={v:.4f}V, fitted={calculated_v:.4f}V, error={error:.4f}V")
    print()

    # Ask to apply calibration
    apply = input("Apply this calibration to config? [Y/n]: ").strip().lower()
    if apply in ["", "y", "yes"]:
        if update_config(slope, intercept):
            restart = input("Restart pH sensor to apply changes? (y/n) ").lower().strip()
            if restart == 'y':
                restart_ph_sensor()
                print()
                print("✓ Calibration complete!")
                print()
                print("The pH sensor is now using the new calibration.")
                print("Monitor the readings to verify accuracy.")
            else:
                print()
                print("✓ Calibration saved to config")
                print("  Restart the pH sensor manually to apply changes:")
                print("  pkill -f vernier_fph_bta && pio run vernier_fph_bta &")
    else:
        print("Calibration not applied.")

    # Save calibration log
    log_file = f"/tmp/ph_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, 'w') as f:
        f.write(f"pH Calibration - {datetime.now()}\n")
        f.write(f"Slope: {slope:.6f}\n")
        f.write(f"Intercept: {intercept:.6f}\n")
        f.write(f"Data points:\n")
        for ph, v in zip(ph_values, voltages):
            f.write(f"  pH {ph}: {v:.4f}V\n")
    print(f"\nCalibration log saved to: {log_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalibration cancelled.")
    except Exception as e:
        print(f"\nError: {e}")
