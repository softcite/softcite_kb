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


### rOpenSci

```bash
python3 populate/rOpenSci_import.py --config my_config.json
```


