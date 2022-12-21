from scapy.all import *
import psutil
import time
import argparse
from collections import defaultdict
import os
from threading import Thread
import pandas as pd
from datetime import datetime


ap = argparse.ArgumentParser()
ap.add_argument("-c", "--condition", type=str, required = False, default = None)
ap.add_argument("-to", "--timeout", type=int, required = False, default = 60)
args = vars(ap.parse_args())


if 'log.csv' not in os.listdir():
    log_df = pd.DataFrame({
        "pid" : [],
        "name" : [],
        "create_time" : [],
        "Upload (Mb)" : [],
        "Download (Mb)" : [],
        "Upload Speed (Mb/s)" : [],
        "Download Speed (Mb/s)" : [],
        "condition" : []
    })
    log_df.set_index("pid", inplace = True)
    log_df.to_csv("log.csv")
else:
    pass


# get the all network adapter's MAC addresses
# all_macs = {iface.mac for iface in ifaces.values()}
interfaces = psutil.net_if_addrs()
all_macs = {iface.address for iface in interfaces["eth0"] if iface.family == psutil.AF_LINK}
# A dictionary to map each connection to its correponding process ID (PID)
connection2pid = {}
# A dictionary to map each process ID (PID) to total Upload (0) and Download (1) traffic
pid2traffic = defaultdict(lambda: [0, 0])
# the global Pandas DataFrame that's used to track previous traffic stats
global_df = None
# global boolean for status of the program
is_program_running = True

# Variables for use in the size() function.
Kb = float(1000)
Mb = float(Kb ** 2) # 1,048,576
Gb = float(Kb ** 3) # 1,073,741,824
Tb = float(Kb ** 4) # 1,099,511,627,776
def get_size(B):
    """Credits: https://stackoverflow.com/a/31631711 (Improved version of it.)"""
    """convert to Mb"""

    b = float(B*8)
    if b < Kb:
        b_to_mb = b/1000000
        return f"{b_to_mb:.2f}"
    elif Kb <= b < Mb:
        kb = (B/Kb)
        kb_to_mb = kb/1000
        return f"{kb_to_mb:.2f}"
    elif Mb <= b < Gb:
        mb = (b/Mb)
        return f"{mb:.2f}"
    elif Gb <= b < Tb:
        gb = (b/Gb)
        gb_to_mb = gb * 1000
        return f"{gb_to_mb:.2f}"
    elif Tb <= b:
        tb = (b/Tb)
        tb_to_mb = tb * 1000000
        return f"{tb_to_mb:.2f}"

def process_packet(packet):
    global pid2traffic
    try:
        # get the packet source & destination IP addresses and ports
        packet_connection = (packet.sport, packet.dport)
    except (AttributeError, IndexError):
        # sometimes the packet does not have TCP/UDP layers, we just ignore these packets
        pass
    else:
        # get the PID responsible for this connection from our `connection2pid` global dictionary
        packet_pid = connection2pid.get(packet_connection)
        if packet_pid:
            if packet.src in all_macs:
                # the source MAC address of the packet is our MAC address
                # so it's an outgoing packet, meaning it's upload
                pid2traffic[packet_pid][0] += len(packet)
            else:
                # incoming packet, download
                pid2traffic[packet_pid][1] += len(packet)

def get_connections():
    """A function that keeps listening for connections on this machine
    and adds them to `connection2pid` global variable"""
    global connection2pid
    while is_program_running:
        # using psutil, we can grab each connection's source and destination ports
        # and their process ID
        for c in psutil.net_connections():
            if c.laddr and c.raddr and c.pid:
                # if local address, remote address and PID are in the connection
                # add them to our global dictionary
                connection2pid[(c.laddr.port, c.raddr.port)] = c.pid
                connection2pid[(c.raddr.port, c.laddr.port)] = c.pid
        # sleep for a second, feel free to adjust this
        time.sleep(1)

def print_pid2traffic():
    global global_df
    # initialize the list of processes
    processes = []

    for pid, traffic in pid2traffic.items():
        # `pid` is an integer that represents the process ID
        # `traffic` is a list of two values: total Upload and Download size in bytes
        try:
            # get the process object from psutil
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            # if process is not found, simply continue to the next PID for now
            continue
        # get the name of the process, such as chrome.exe, etc.
        name = p.name()
        # get the time the process was spawned
        try:
            create_time = datetime.fromtimestamp(p.create_time()).strftime('%d-%m-%Y %H:%M:%S')
        except OSError:
            # system processes, using boot time instead
            create_time = datetime.fromtimestamp(psutil.boot_time()).strftime('%d-%m-%Y %H:%M:%S')
        # construct our dictionary that stores process info
        process = {
            "pid": pid, "name": name, "create_time": create_time, "Upload (Mb)": traffic[0],
            "Download (Mb)": traffic[1]
        }
        try:
            # calculate the upload and download speeds by simply subtracting the old stats from the new stats
            process["Upload Speed (Mb/s)"] = traffic[0] - global_df.at[pid, "Upload (Mb)"]
            process["Download Speed (Mb/s)"] = traffic[1] - global_df.at[pid, "Download (Mb)"]
            process["condition"] = args["condition"]
        except (KeyError, AttributeError):
            # If it's the first time running this function, then the speed is the current traffic
            # You can think of it as if old traffic is 0
            process["Upload Speed (Mb/s)"] = traffic[0]
            process["Download Speed (Mb/s)"] = traffic[1]
            process["condition"] = args["condition"]
        # append the process to our processes list
        processes.append(process)
    # construct our Pandas DataFrame
    df = pd.DataFrame(processes)
    try:
        # set the PID as the index of the dataframe
        df = df.set_index("pid")
        # sort by column, feel free to edit this column
        df.sort_values("Download (Mb)", inplace=True, ascending=False)
    except KeyError as e:
        # when dataframe is empty
        pass
    # make another copy of the dataframe just for fancy printing
    printing_df = df.copy()
    try:
        # apply the function get_size to scale the stats like '532.6KB/s', etc.
        printing_df["Download (Mb)"] = printing_df["Download (Mb)"].apply(get_size)
        printing_df["Upload (Mb)"] = printing_df["Upload (Mb)"].apply(get_size)
        printing_df["Download Speed (Mb/s)"] = printing_df["Download Speed (Mb/s)"].apply(get_size)
        printing_df["Upload Speed (Mb/s)"] = printing_df["Upload Speed (Mb/s)"].apply(get_size)
    except KeyError as e:
        # when dataframe is empty again
        pass
    # clear the screen based on your OS
    os.system("cls") if "nt" in os.name else os.system("clear")
    # print our dataframe
    # df_print = printing_df.copy()
    print(printing_df.to_string())
    # concat and save dataframe
    df_log = pd.read_csv("log.csv")
    df_log.set_index("pid", inplace = True)
    df_log_concat = pd.concat([df_log, printing_df])
    df_log_concat.to_csv("log.csv")

    # update the global df to our dataframe
    global_df = df

def print_stats():
    """Simple function that keeps printing the stats"""
    while is_program_running:
        time.sleep(1)
        print_pid2traffic()

if __name__ == "__main__":
    # start the printing thread
    printing_thread = Thread(target=print_stats)
    printing_thread.start()
    # start the get_connections() function to update the current connections of this machine
    connections_thread = Thread(target=get_connections)
    connections_thread.start()

    # start sniffing
    print("Started sniffing")
    sniff(prn=process_packet, store=False, timeout = args["timeout"])
    # connections_thread.stop()
    # setting the global variable to False to exit the program
    is_program_running = False
