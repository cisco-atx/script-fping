"""Worker logic for fping execution.

This module contains the main logic for executing fping across specified subnets,
processing the output, and generating a report based on the results. It uses
concurrent threads to run fping in parallel for multiple subnets, and it handles the output to create a structured report in Excel format.

File path: workers.py
"""

import ipaddress
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from netcore import GenericHandler, XLBW


def run_fping(subnets, fqdn, filters, connector, ctx):
    output_data = {}

    def fping_task(subnet):
        output_data[subnet] = {}

        cmd = ["fping -A"]
        if fqdn: cmd.append(fqdn)
        cmd.append(f"-g {subnet}")

        try:
            ctx.log(f"Running {' '.join(cmd)}")
            handler = GenericHandler(
                hostname=connector["jumphost_ip"],
                username=connector["jumphost_username"],
                password=connector["jumphost_password"],
                handler="NETMIKO",
                read_timeout_override=1000
            )
            output_data[subnet] = handler.sendCommand(' '.join(cmd))
            handler.close()
        except Exception as exc:
            ctx.log(f"Error processing {subnet}: {exc}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(fping_task, subnets)

    generate_report(output_data, fqdn, filters, ctx)
    ctx.log("Fping execution finished")

def generate_report(output_data, fqdn, filters, ctx):

    dump_data = {}

    regex_pattern = re.compile(r"^(\d+.\d+.\d+.\d+)\s+is\s+(\S+)")
    if fqdn:
        regex_pattern = re.compile(r"^(\S+)\s+\((\d+.\d+.\d+.\d+)\)\s+is\s+(\S+)")

    for subnet, output in output_data.items():
        for line in output.splitlines():
            match = regex_pattern.match(line)
            if match:
                if fqdn:
                    ip, hostname, status = match.groups()
                else:
                    ip, status = match.groups()
                    hostname = "N/A"

                dump_data[ip] = {
                    "ip": ip,
                    "Hostname": hostname,
                    "Subnet": subnet,
                    "Status": status,
                }

    refactored_data = {}

    idx = 0
    for subnet in output_data.keys():
        all_ips = list(ipaddress.ip_network(subnet).hosts())
        for ip in all_ips:
            ip_str = str(ip)
            if ip_str in dump_data:
                if "-a" in filters:
                    if dump_data[ip_str]["Status"] == "alive":
                        idx += 1
                        refactored_data[idx] = dump_data[ip_str]
                elif "-u" in filters:
                    if dump_data[ip_str]["Status"] == "unreachable":
                        idx += 1
                        refactored_data[idx] = dump_data[ip_str]
                else:
                    idx += 1
                    refactored_data[idx] = dump_data[ip_str]

    filename = f"Fping_{datetime.now():%Y-%m-%d_%H.%M}.xlsx"
    path = os.path.join(ctx.output_dir, filename)

    wb = XLBW(path)
    ws = wb.add_worksheet("Fping")
    wb.dump(refactored_data, ws)
    wb.close()