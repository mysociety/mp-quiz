import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


class CurrentMP(BaseModel):
    person_id: int
    name: str
    party: str | None
    constituency: str


class DataDump(BaseModel):
    current_mps: dict[int, CurrentMP]
    current_mp_lookup: dict[str, list[int]]
    former_mp_lookup: dict[str, list[int]]


def clean_text(text: str) -> str:
    # Convert text to lowercase
    text = text.lower()

    # Remove punctuation and whitespace
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "", text)

    # Remove any sequential duplicate characters
    text = re.sub(r"(.)\1+", r"\1", text)

    # Order text alphabetically
    text = "".join(sorted(text))

    return text


def create_json():

    df = pd.read_parquet(
        "https://pages.mysociety.org/politician_data/data/uk_politician_data/latest/simple_memberships.parquet"
    )

    # limit to chamber = commons
    # limit to end_date = 9999-12-31

    df = df[(df["chamber"] == "commons")]

    df["person_id"] = df["person_id"].str.split("/").str[-1].astype(int)

    current_mp_ids = df[df["end_date"].isnull()]["person_id"]

    # others is any person_id that isn't in current_mp_ids
    other_mps_ids = df[~df["person_id"].isin(current_mp_ids)]["person_id"]

    good_cols = ["person_id", "nice_name", "party", "constituency", "end_date"]

    df = df[good_cols]

    df = df.rename(columns={"nice_name": "name"})

    # limit to current_mps and make the currentMp lookup
    current_mp_list = df[
        df["person_id"].isin(current_mp_ids) & df["end_date"].isnull()
    ].to_dict(orient="records")
    current_mp_list = {
        x["person_id"]: CurrentMP.model_validate(x) for x in current_mp_list
    }

    alt_names = pd.read_parquet(
        "https://pages.mysociety.org/politician_data/data/uk_politician_data/latest/person_alternative_names.parquet"
    )

    alt_names["person_id"] = alt_names["person_id"].str.split("/").str[-1].astype(int)

    # limit to just person_ids in df

    alt_names = alt_names

    # we want to create a nice name, where it's either the 'name' column (if populated) or joining given name and family name

    alt_names["nice_name"] = alt_names["name"].fillna(
        alt_names["given_name"] + " " + alt_names["family_name"]
    )

    # make a dictionary of nice_name to a list of person_ids (in case multiple people share a name)

    nice_name_to_current_person_id = (
        alt_names[alt_names["person_id"].isin(current_mp_ids)]
        .groupby("nice_name")["person_id"]
        .apply(list)
        .to_dict()
    )

    nice_name_to_current_person_id["Liz Truss"] = [24941]

    nice_name_to_former_person_id = (
        alt_names[alt_names["person_id"].isin(other_mps_ids)]
        .groupby("nice_name")["person_id"]
        .apply(list)
        .to_dict()
    )

    # now - we want to make sure that there isn't a "shorter" former person name
    # that is a substring of a current person name
    # this will block matching on the longer name

    to_pop = []

    current_name_clean_li = []
    for x in nice_name_to_current_person_id:
        for partial_len in range(1, len(x)):
            current_name_clean_li.append((x, clean_text(x[:partial_len])))

    former_name_clean_li = [(x, clean_text(x)) for x in nice_name_to_former_person_id]

    for current_name, current_name_clean in current_name_clean_li:
        for former_name, former_name_clean in former_name_clean_li:
            if current_name_clean.startswith(former_name_clean):
                to_pop.append(former_name)

    to_pop = list(set(to_pop))
    for name in to_pop:
        nice_name_to_former_person_id.pop(name)

    data = DataDump(
        current_mps=current_mp_list,
        current_mp_lookup=nice_name_to_current_person_id,
        former_mp_lookup=nice_name_to_former_person_id,
    )

    with Path("docs", "data", "mp_data.json").open("w") as f:
        f.write(data.model_dump_json())
