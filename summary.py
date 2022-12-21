import pandas as pd
import numpy as np
import argparse
import dataframe_image as dfi

ap = argparse.ArgumentParser()
ap.add_argument("-f", "--filename", type=str, required = False, default = "log.csv")
ap.add_argument("-bn", "--browser_name", type=str, required = False, default = "msedge.exe")
args = vars(ap.parse_args())

def summary(filename=args["filename"], browser_name=args["browser_name"]):
    df = pd.read_csv(filename)

    browser_df = df[(df["name"] == browser_name)].reset_index(drop = True)
    # browser_df = browser_df[(browser_df["Upload Speed (Mb/s)"] > 0.5) | (browser_df["Download Speed (Mb/s)"] > 0.5)].reset_index(drop = True)

    upload_speed = browser_df[browser_df["Upload Speed (Mb/s)"] > 0.5]
    upload_speed = upload_speed["Upload Speed (Mb/s)"]

    # find min, max, and average upload speed
    min_upload_speed = min(upload_speed)
    max_upload_speed = max(upload_speed)
    avg_upload_speed = np.average(upload_speed)

    # get index
    min_upload_index = upload_speed.values.tolist().index(min_upload_speed)
    max_upload_index = upload_speed.values.tolist().index(max_upload_speed)

    # get condition
    min_upload_condition = browser_df.iloc[min_upload_index]["condition"]
    max_upload_condition = browser_df.iloc[max_upload_index]["condition"]
    avg_upload_condition = np.nan

    # find min, max, and average download speed
    download_speed = browser_df[browser_df["Download Speed (Mb/s)"] > 0.5]
    download_speed = download_speed["Download Speed (Mb/s)"]

    min_download_speed = min(download_speed)
    max_download_speed = max(download_speed)
    avg_download_speed = np.average(download_speed)

    # get index
    min_download_index = download_speed.values.tolist().index(min_download_speed)
    max_download_index = download_speed.values.tolist().index(max_download_speed)

    # get condition
    min_download_condition = browser_df.iloc[min_download_index]["condition"]
    max_download_condition = browser_df.iloc[max_download_index]["condition"]
    avg_download_condition = np.nan

    # summary dataframe

    upload_speed_summary = [min_upload_speed, avg_upload_speed, max_upload_speed]
    download_speed_summary = [min_download_speed, avg_download_speed, max_download_speed]
    upload_condition = [min_upload_condition, avg_upload_condition, max_upload_condition]
    download_condition = [min_download_condition, avg_download_condition, max_download_condition]

    summary_df = pd.DataFrame({
        "speed" : ["min", "average", "max"],
        "upload speed (Mb/s)" : upload_speed_summary,
        "download speed (Mb/s)" : download_speed_summary,
        "upload condition" : upload_condition,
        "download condition" : download_condition
    })
    summary_df.set_index("speed", inplace = True)
    styled_df = summary_df.style.background_gradient()
    dfi.export(styled_df, "benchmark-result.png")
    print("Summary saved!")

    return styled_df

if __name__ == "__main__":
    summary()