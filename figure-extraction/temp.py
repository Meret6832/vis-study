import os

top_dirs = [
    "extracted"
]

for top_dir in top_dirs:
    for conf in os.listdir(top_dir):
        for file in os.listdir(f"{top_dir}/{conf}/figures"):
            if "-978-" in file:
                replace_lower = file.split("_")[0] + "__" + "_".join(file.split("_")[1:])
                new_file = replace_lower.split("-")[0] + "--" + "-".join(replace_lower.split("-")[1:])
            else:
                replace_lower = "__".join(file.split("_"))
                new_file = "--".join(replace_lower.split("-")[:-2]) + "-" + "-".join(replace_lower.split("-")[-2:])
            print(file, "->", new_file)
            os.rename(f"{top_dir}/{conf}/figures/{file}", f"{top_dir}/{conf}/figures/{new_file}")


#     print(dir)

# file = "10_1145-3597503_3608137.pdf"
# file = "10_1145-3597503_3608137-Figure13-1.pdf"
# file = "10_1007-978-3-031-70797-1_3-Figure2-1.png"

# replace_lower = "__".join(file.split("_"))
# print(replace_lower)
# new_file = "--".join(replace_lower.split("-")[:-2]) + "-" + "-".join(replace_lower.split("-")[-2:])
# # new_file = "--".join(replace_lower.split("-"))
# print(new_file)
