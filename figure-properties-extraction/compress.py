import ast
import pandas as pd


df = pd.read_csv("img_properties.csv", index_col=0)
df["colors"] = df.apply(lambda row: ast.literal_eval(row.colors)[:10], axis=1)

df.to_csv("img_properties_small.csv")
