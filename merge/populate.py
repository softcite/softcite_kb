import os
import sys
import argparse
from populate_staging_area import StagingArea
import populate_from_r
import populate_from_wikidata
import populate_from_mentions

def populate_from_import(stagingArea, reset=False):
    if reset:
        stagingArea.reset()          

    # populate from R sources
    print("Add R imported documents to the staging area graph...")
    populate_from_r.populate(stagingArea)

    # populate from Wikidata sources
    print("Add Wikidata imported documents to the staging area graph...")
    populate_from_wikidata.populate(stagingArea)

    # populate from extracted mention source
    populate_from_mentions.populate(stagingArea)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Populate the staging area graph with imported document resources")
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--reset", action="store_true", help="reset existing graph and re-ingest all imported resources") 

    args = parser.parse_args()
    config_path = args.config
    to_reset = args.reset

    stagingArea = StagingArea(config_path=config_path)
    populate_from_import(stagingArea, reset=to_reset)
