import re 
import sys
from software_kb.merging.populate_staging_area import StagingArea
from software_kb.kb.knowledge_base import _init_count
import argparse

def test_reference_aggregation(stagingArea):
    entity1 = {
        "claims": {
            "P348": [
                {
                    "value": "20.0",
                    "datatype": "string",
                    "references": [
                        {
                            "P248": {
                                "value": "software-mentions",
                                "datatype": "string"
                            }
                        }
                    ]
                } 
            ],
            "P6166": [
                {
                    "value": "SPSS",
                    "datatype": "string",
                    "references": [
                        {
                            "P248": {
                                "value": "software-mentions",
                                "datatype": "string"
                            }
                        }
                    ]
                }
            ]
        }
    }

    entity2 = {
        "claims": {
            "P348": [
                {
                    "value": "20.0",
                    "datatype": "string",
                    "references": [
                        {
                            "P248": {
                                "value": "software-mentions",
                                "datatype": "string"
                            }
                        }
                    ]
                } 
            ],
            "P6166": [
                {
                    "value": "SPSS",
                    "datatype": "string",
                    "references": [
                        {
                            "P248": {
                                "value": "Q2086703",
                                "datatype": "wikibase-item"
                            }
                        }
                    ]
                }
            ]
        }
    }

    print("entity1:", entity1)
    print("entity2:", entity2)
    result = stagingArea.aggregate_no_merge(entity1, entity2)
    print("aggregate_no_merge:", result)

    result = stagingArea.aggregate_with_merge(entity1, entity2)
    print("aggregate_with_merge:", result)


def test_full_aggregation(stagingArea):

    entity1 = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}
    entity2 = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P123":[{"value":"IBM","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}

    print("\nentity1:", entity1)
    print("entity2:", entity2)
    result = stagingArea.aggregate_no_merge(entity1, entity2)
    print("aggregate_no_merge:", result)

    result = stagingArea.aggregate_with_merge(entity1, entity2)
    print("aggregate_with_merge:", result)

def test_init_count():
    entity1 = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}
    entity2 = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P123":[{"value":"IBM","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}

    print("\nentity1:", entity1)
    entity1 = _init_count(entity1)
    print(entity1)

    print("\nentity2:", entity1)
    entity2 = _init_count(entity1)
    print(entity2)

def test_normalization(stagingArea):
    entity = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value": 179088,"datatype": "url","references": [{"P248": {"value": "software-mentions","datatype": "string","count": 20}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}

    print("\nentity1:", entity)
    stagingArea.normalize_entity(entity)
    print("\nentity1 normalized:", entity)

    entity = {"claims":{"P31":[{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string", "count": 200}}]},{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"rOpenSci","datatype":"string"}}]},{"value":"Q7397","datatype":"wikibase-item","references":[{"P248":{"value":"CRAN","datatype":"string"}}]}],"P348":[{"value":"20.0","datatype":"string","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}],"P460":[{"value":179088,"datatype":"url","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]},{"value": 179088,"datatype": "url","references": [{"P248": {"value": "software-mentions","datatype": "string","count": 20}}]},{"value":"Q181596","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string"}}]}]}}

    print("\nentity2:", entity)
    stagingArea.normalize_entity(entity)
    print("\nentity2 normalized:", entity)

    entity = {"claims":{"P31":[{"value":"this is testing","datatype":"wikibase-item","references":[{"P248":{"value":"software-mentions","datatype":"string", "count": 200}}]},{"value":"this is test- ing","datatype":"wikibase-item","references":[{"P248":{"value":"rOpenSci","datatype":"string"}}]},{"value":"this is test-ing","datatype":"wikibase-item","references":[{"P248":{"value":"CRAN","datatype":"string"}}]}]}}

    print("\nentity3:", entity)
    stagingArea.normalize_entity(entity)
    print("\nentity3 normalized:", entity)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Test simple entity aggregation")
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 

    args = parser.parse_args()
    config_path = args.config

    test_init_count()

    stagingArea = StagingArea(config_path=config_path)
    test_reference_aggregation(stagingArea)
    test_full_aggregation(stagingArea)
    test_normalization(stagingArea)
