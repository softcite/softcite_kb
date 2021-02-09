# Softcite Knowledge Base

This repository contains the tools for creating, populating and updating the Softcite Knowledge Base, dedicated to research software. 

We define first research software as the software mentioned in the scientific litterature, considering that these mentions characterize research software usage. The core of the Knwoledge Base is thus relying on the import of resources on software usage in the scientific literature. We further match mentionned software to software entities from different curated software resources. Via software dependencies, we then identify relations to more general resources on software, which constitutes an enlarged view on research software, providing a richer view.  

## Requirements and install

The presents tools are implemented in Python and should work correctly with Python 3.5 or higher. An ArangoDB server must be installed, see the [installation](https://www.arangodb.com/download-major/) of the Open Source community server. 

Get the github repo:

```sh
git clone https://github.com/kermitt2/softcite_kb
cd softcite_kb
```
It is strongly advised to setup first a virtual environment to avoid falling into one of these gloomy python dependency marshlands:

```sh
virtualenv --system-site-packages -p python3 env
source env/bin/activate
```

Install the dependencies:

```sh
pip3 install -r requirements.txt
```

## Create the Knowledge Base

The KB uses ArangoDB to store multi-model representations. Be sure to have an ArangoDB server installed and running. Indicate the server host and port of ArangoDB in the config file - if not default (`localhost:8529`) - together with the `username` and `password` to be used for transactions. In the following, we suppose that the config file is `my_config.json`, if not indicated the file `config.json` will be used by default. 

## Populate the Knowledge Base

The main sources of data are currently:

- Wikidata software entities

- rOpenSci's R-universe package system and CRAN for R ecosystem

- The extraction of software mentions and citations in the scientific literature, thanks to the [Softcite software mention recognizer](https://github.com/ourresearch/software-mentions)

- Public information available via GitHub API

### Import Wikidata software entities

The import is realized via the JSON Wikidata dump. Entities corresponding to software (except video games) are imported to seed the KB, together with some relevant entities in relation to software corresponding to persons, organizations and close concepts (programming language, OS, license). 

A recent full Wikidata json dump compressed with bz2 (which is more compact) is needed, which can be dowloaded [here](https://dumps.wikimedia.org/wikidatawiki/entities/). There is no need to uncompressed the json dump.

The import is launched as follow, with `latest-all.json.bz2` as Wikidata dump file:

```bash
python3 populate/Wikidata_import.py --config my_config.json latest-all.json.bz2
```

### Import rOpenSci metadata

From the project root, launch:

```bash
python3 populate/rOpenSci_import.py --config my_config.json
```

This will populate the rOpenSci import document database from scratch or update it if already present. 

To force the import to recreate the rOpenSci database from scratch, use:

```bash
python3 populate/rOpenSci_import.py --config my_config.json --reset
```

The import uses a cache to avoid reloading the JSON from the rOpenSci API. The metadata are reloaded only when a new version of a package is available.

### Import CRAN metadata



### GitHub public data




