"""Measure what a wallpaper costs: sample backboardd (the process that composites the screen) on a
USB-connected iPhone and summarise it the way techniques.md §H reports it.

usage:  python measure_backboardd.py LABEL [--seconds 60] [--warmup 5]

Lay the phone flat on the Home Screen with the wallpaper applied; a foreground app or holding the phone
(gyro) raises the numbers. Needs:
  * pymobiledevice3 (found via $PMD3, PATH, or tools/pmd3 under the working directory)
  * Developer Mode on the phone (iOS 27 mounts the developer disk image by itself)
  * `pymobiledevice3 remote tunneld` running with administrator rights (iOS 17 and later)
Every run is appended to out/perf/measurements.csv under the working directory.
"""
import argparse
import csv
import datetime
import json
import os
import shutil
import statistics
import subprocess
import sys


def pmd3():
    for cand in (os.environ.get("PMD3"), shutil.which("pymobiledevice3"),
                 os.path.join("tools", "pmd3", "Scripts", "pymobiledevice3.exe"),
                 os.path.join("tools", "pmd3", "bin", "pymobiledevice3")):
        if cand and os.path.exists(cand):
            return cand
    sys.exit("pymobiledevice3 not found: install it or set PMD3")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--warmup", type=int, default=5)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    cmd = [pmd3(), "developer", "dvt", "sysmon", "process", "monitor", "process", "--tunnel", "",
           "-f", "name=backboardd", "--choose", "first", "-i", "1000",
           "-d", str((a.seconds + a.warmup) * 1000), "-k", "cpuUsage", "-k", "physFootprint"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    rows = [json.loads(line) for line in p.stdout.splitlines() if line.startswith("{")][a.warmup:]
    if not rows:
        sys.exit("no samples:\n" + (p.stderr or p.stdout)[-800:])
    cpu = [r["cpuUsage"] for r in rows]
    q = statistics.quantiles(cpu, n=10)
    res = dict(time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), label=a.label, samples=len(cpu),
               mean=round(statistics.mean(cpu), 1), median=round(statistics.median(cpu), 1),
               p10=round(q[0], 1), p90=round(q[-1], 1), mem_mib=round(rows[-1]["physFootprint"] / 2 ** 20))
    print(f"{a.label}: mean {res['mean']}%  median {res['median']}%  p10–p90 {res['p10']}–{res['p90']}%  "
          f"end memory {res['mem_mib']} MiB  ({len(cpu)} samples)")
    log = os.path.join("out", "perf", "measurements.csv")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    new = not os.path.exists(log)
    with open(log, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res))
        if new:
            w.writeheader()
        w.writerow(res)


if __name__ == "__main__":
    main()
