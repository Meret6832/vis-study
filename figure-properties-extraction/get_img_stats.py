import json
import os
import pandas as pd
import re
import webcolors
from PIL import Image

TOP_N_COLORS = 10

df = pd.DataFrame(columns=["conf", "doi", "fig_num", "width", "height", "colors", "visual_density"])

white_thresh = 250 - 8


def get_non_white(colors):
    colors = colors
    white_frac = 0
    for color, frac in colors:
        r, g, b = webcolors.hex_to_rgb(f"#{color}")
        if r >= white_thresh and g >= white_thresh and b >= white_thresh:
            white_frac += frac
    return 1 - white_frac


for conf in os.listdir("../figure-extraction/extracted/"):
    for fig in os.listdir(f"../figure-extraction/extracted/{conf}/figures"):
        if "Figure" not in fig:  # Skip Tables
            continue

        img_path = f"../figure-extraction/extracted/{conf}/figures/{fig}"
        img = Image.open(img_path)
        img.convert("RGB")

        path_match = re.search(r"../figure-extraction/extracted/(.+\-.+)/figures/(10_.+\-.+)\-Figure([0-9]+)", img_path)
        conf = path_match[1]
        doi = path_match[2].replace("__", ".").replace("--", "/")
        fig_num = int(path_match[3])
        data_path = f"../figure-extraction/extracted/{path_match[1]}/data/{path_match[2]}.json"

        print(doi, fig_num)

        with open(data_path, "r") as data_f:
            data = json.load(data_f)

        # Get size
        w, h = img.size

        # Get colors
        color_dict = {}
        for x in range(w):
            for y in range(h):
                r, g, b = img.getpixel((x, y))
                hex = f"{r:02X}{g:02X}{b:02X}"
                if hex in color_dict.keys():
                    color_dict[hex] += 1
                else:
                    color_dict[hex] = 1

        for k, v in color_dict.items():
            color_dict[k] = v / (w*h)

        colors = sorted(color_dict.items(), key=lambda x: x[1], reverse=True)

        visual_density = get_non_white(colors)

        df.loc[len(df)] = [conf, doi, fig_num, w, h, str(colors), visual_density]

df.to_csv("img_properties2.csv")
