import os
import random

out_f = "figure_extraction_testtable.csv"
with open(out_f, "w+") as f:
    f.write("conf,doi,correct,not-found,found\n")

for conf in os.listdir("../data-collection/pdfs-cleanup/"):
    selected_doi = random.choice(os.listdir(f"../data-collection/pdfs-cleanup/{conf}")).split(".")[0]
    with open(out_f, "a") as f:
        f.write(f"{conf},{selected_doi},,,\n")
