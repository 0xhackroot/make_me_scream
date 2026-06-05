#!/usr/bin/env python3
"""
ScreamCPU - silent background daemon
Monitors CPU temp and plays sounds from sounds/ folder.

Sound files (put your own in sounds/):
    sounds/warm.mp3      (or .wav) - plays at 60-74C
    sounds/hot.mp3       (or .wav) - plays at 75-84C
    sounds/meltdown.mp3  (or .wav) - plays at 85C+

Usage:
    python3 screamcpu.py           # silent daemon mode
    python3 screamcpu.py --test    # verbose mode to debug
"""

import os
import time
import subprocess
import glob
import signal
import sys

# --- Config ---
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

LEVELS = [
    {"name": "meltdown", "min": 85, "sound": "meltdown"},
    {"name": "hot",      "min": 75, "sound": "hot"},
    {"name": "warm",     "min": 60, "sound": "warm"},
    {"name": "cool",     "min": 0,  "sound": None},
]

TEST_MODE = "--test" in sys.argv

def log(msg):
    if TEST_MODE:
        print(msg, flush=True)

# --- Temp reading ---
def get_cpu_temp():
    # Method 1: psutil
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        log(f"  [psutil] keys found: {list(temps.keys())}")
        for key in ("coretemp", "k10temp", "zenpower", "acpitz", "cpu_thermal"):
            if key in temps:
                readings = [t.current for t in temps[key] if t.current > 0]
                if readings:
                    log(f"  [psutil] using '{key}': {readings}")
                    return max(readings)
    except Exception as e:
        log(f"  [psutil] failed: {e}")

    # Method 2: thermal_zone sysfs
    try:
        zones = sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp"))
        log(f"  [sysfs] zones found: {zones}")
        for zone in zones:
            with open(zone) as f:
                val = int(f.read().strip()) / 1000.0
                if 10 < val < 120:
                    log(f"  [sysfs] using {zone}: {val}C")
                    return val
    except Exception as e:
        log(f"  [sysfs] failed: {e}")

    # Method 3: sensors command
    try:
        import re
        out = subprocess.check_output(["sensors"], text=True, stderr=subprocess.DEVNULL)
        log(f"  [sensors cmd] output:\n{out}")
        matches = re.findall(r"[+](\d+\.\d+).C", out)
        if matches:
            log(f"  [sensors cmd] readings: {matches}")
            return max(float(m) for m in matches)
    except Exception as e:
        log(f"  [sensors cmd] failed: {e}")

    return None

def get_level(temp):
    for lvl in LEVELS:
        if temp >= lvl["min"]:
            return lvl
    return LEVELS[-1]

# --- Sound ---
def find_sound_file(name):
    for ext in ("mp3", "wav", "ogg", "flac"):
        path = os.path.join(SOUNDS_DIR, f"{name}.{ext}")
        if os.path.exists(path):
            return path
    return None

def start_sound(path):
    for player in (
        ["mpg123", "-q", path],
        ["mpv", "--no-terminal", "--quiet", path],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
        ["aplay", "-q", path],
        ["paplay", path],
    ):
        try:
            proc = subprocess.Popen(
                player,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log(f"  [sound] playing with '{player[0]}': {path}")
            return proc
        except FileNotFoundError:
            log(f"  [sound] '{player[0]}' not found, trying next...")
            continue
    log("  [sound] ERROR: no audio player found! install mpg123.")
    return None

def kill_sound(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()

# --- Test mode ---
def run_test():
    print("=== ScreamCPU test mode ===\n")
    print(f"sounds dir: {SOUNDS_DIR}")
    for name in ("warm", "hot", "meltdown"):
        f = find_sound_file(name)
        print(f"  {name}: {'FOUND -> ' + f if f else 'NOT FOUND'}")

    print()
    temp = get_cpu_temp()
    if temp is None:
        print("ERROR: could not read CPU temperature.")
        print("Run: sudo apt install lm-sensors && sudo sensors-detect")
    else:
        print(f"CPU temp: {temp}C  ->  level: {get_level(temp)['name']}")

    print()
    print("Playing each sound file now...")
    for name in ("warm", "hot", "meltdown"):
        f = find_sound_file(name)
        if f:
            print(f"  playing {name}...", end=" ", flush=True)
            proc = start_sound(f)
            if proc:
                proc.wait()
                print("done")
            else:
                print("FAILED (no audio player)")
        else:
            print(f"  {name}: skipped (file not found)")
    print("\nTest complete.")

# --- Main daemon loop ---
def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT,  lambda *_: sys.exit(0))

    current_proc  = None
    current_level = None

    while True:
        temp = get_cpu_temp()
        log(f"temp: {temp}C")

        if temp is not None:
            level = get_level(temp)
            log(f"level: {level['name']}")

            if level["name"] != current_level:
                log(f"level changed: {current_level} -> {level['name']}")
                kill_sound(current_proc)
                current_proc  = None
                current_level = level["name"]

            if level["sound"]:
                if current_proc is None or current_proc.poll() is not None:
                    time.sleep(2)
                    temp = get_cpu_temp()
                    if temp is not None:
                        new_level = get_level(temp)
                        if new_level["name"] != current_level:
                            current_level = new_level["name"]
                            level = new_level

                    if level["sound"]:
                        sound_file = find_sound_file(level["sound"])
                        if sound_file:
                            current_proc = start_sound(sound_file)
                        else:
                            log(f"  [sound] file not found for level '{level['name']}'")
        time.sleep(1)

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    else:
        main()
