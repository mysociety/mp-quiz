import json
from pathlib import Path

import pandas as pd


def create_json():

    df = pd.read_parquet("https://pages.mysociety.org/politician_data/data/uk_politician_data/latest/simple_memberships.parquet")

    # limit to chamber = commons
    # limit to end_date = 9999-12-31

    df = df[(df["chamber"] == "commons") & (df["end_date"].isnull())]

    df["person_id"] = df["person_id"].str.split("/").str[-1].astype(int)

    good_cols = ["person_id", "nice_name", "party", "constituency"]

    df = df[good_cols]

    df = df.rename(columns={"nice_name": "name"})

    alt_names = pd.read_parquet("https://pages.mysociety.org/politician_data/data/uk_politician_data/latest/person_alternative_names.parquet")

    alt_names["person_id"] = alt_names["person_id"].str.split("/").str[-1].astype(int)

    # limit to just person_ids in df

    alt_names = alt_names[alt_names["person_id"].isin(df["person_id"])]

    # we want to create a nice name, where it's either the 'name' column (if populated) or joining given name and family name

    alt_names["nice_name"] = alt_names["name"].fillna(alt_names["given_name"] + " " + alt_names["family_name"])

    # make a dictionary of nice_name to person_id

    nice_name_to_person_id = alt_names.set_index("nice_name")["person_id"].to_dict()

    # write to docs/data/current_mp.json each a json dictionary of person_id to the other columns in df
    df = df.set_index("person_id")
    df.to_json(Path("docs", "data", "current_mp.json"), orient="index")

    # write the person_id to nice_name dictionary to docs/data/person_id_to_nice_name.json

    with open(Path("docs","data","nice_name_lookup.json"), "w") as f:
        json.dump(nice_name_to_person_id, f)


