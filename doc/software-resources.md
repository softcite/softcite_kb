# Identifying existing curated resources on software

We can distinguish:
* Collaborative development platform (e.g. GitHub, GitLab, Bitbucket, ...), this is mostly where the actual software publication and development work takes place today
* Distribution/package systems (CPAN, CRAN, CTAN, PyPI, Maven Central, NPM, ...)
* Aggregator for software information (swMath, ASCL service, Papers with code, SciCrunch)
* Aggregator for software code and package (libraries.io, versioneye, World of Code, SoftwareHeritage)
* Archive supporting software deposit (Zenodo, SoftwareHeritage, Code Ocean)
* Tools supporing the collaborative development ecosystem: build/continuous integration service (travis, circleci, Jenkins, GitHub Actions, etc.), test coverage (coverall, codecov, etc.), image system (DockerHub), documentation (readthedoc), etc.
* Cloud-based computing infrastructure via Jupyter or Jupyter-style Notebooks environment: Google Colab, Azure Notebooks, Kaggle, Amazon Sagemaker, CoCalc, ...

which will be connected somehow to main scholarly services, e.g. for Open Access ones: 
* Scholar article repository (arXiv, bioRxiv, HAL, PMC, ...)
* Scholar article metadata aggregator/resolver (CrossRef, MAG, WoS, Scopus, ...)
* Data sharing repository (Zenodo, Dryad, figshare, Harvard Dataverse, WormBase, etc. hundred? others...)
* Discovery tools (Google Scholar, Semantic Scholar, Primo, Summons, ...)

## Resources covering research software

The following lists group resources in term of their level of curation:

### Curated research software resources

These resources and service are characterized by the involvement of expert human curation and rely on rich metadata schema. The volume of entries is usually small.  

- [swMath](https://swmath.org/): service for software in Mathematics with more than 30.000 curated entries

- FDI Lab [SciCrunch](https://scicrunch.org/): curated research resources, including software, for identification and citation purposes

- [ASCL](https://ascl.net/) service for software in Astrophysics with over 2.000 curated entries 

- [TAPoR 3](http://tapor.ca) contains a list of 1500 curated software/tools in Digital Humanities (see https://lehkost.github.io/tools-dh-proceedings/index.html) 

- [Wikidata](https://wikidata.org) has around 12,000 software entities, excluding video games. The knowlegde base goes beyond software with related entities such as persons (authors, developers), licenses, institutions, etc.

### Partially curated research software resources

The metadata descriptions are curated by the authors themselves or crowdsourced. The volume of entries is often larger than the previous category. 

- [Zenodo](https://zenodo.org/ ) lists some 44.000 software deposits (they are or will be preserved in mirror at some point automatically at SoftwareHeritage). Zenodo metadata is CC-0 license. Software deposits come normally from the Zenodo/GitHub integration. Note that some appears to be dataset generated/used by software (e.g. https://zenodo.org/record/4148730) or documentation on a software (https://zenodo.org/record/4053076). This should be explained by the fact that many GitHub repositories correspond to data or documentation.

In Zenodo, each software version has an independent entry/deposit, but these entries are grouped when related to the same software, e.g.
https://zenodo.org/search?page=1&size=20&q=conceptrecid:4070073&all_versions&sort=-version. By default the versions are nicely conflated in the display of search results. There are around 44.000 software and 101.000 versions, given that software and versions have each a distinct DOIs, we are in the range of 150.000 DOIs for software at Zenodo. Finally a [REST API](https://developers.zenodo.org/#rest-api) and a [OAI-PMH service](https://developers.zenodo.org/#oai-pmh) are available for data access.

- [FigShare](https://figshare.com) lists 17K software deposits.

- [Papers with code](https://paperswithcode.com) initiative in Machine Learning, with over 34.000 entries

- [rOpenSci](https://ropensci.org/) package manager is a community-curated scientific R package environment for build, maintenance, delivery, documentation, etc. (around 350 packages covered)

- some specialized research software registries: [Biocontainers](https://biocontainers.pro) (9.5K tools), [Bioconda](https://bioconda.github.io) (7K), [Debian Med](https://wiki.debian.org/DebianMed).

- [Biii](https://biii.eu) is a crowdsourced registry with 1,336 software entries

- [BioTools](https://bio.tools) in Biomedicine (around 17,000 entries), relying on author registration. It covers tools in biomedicine, but also includes databases, services, etc. (note: on covid-19 tools, https://bio.tools/t?domain=covid-19 and it uses keyphrase lookup to find tool mentions in PMC, see https://github.com/bio-tools/pub2tools)

Other minor or inactive resources include CoMSES (800 computational models), mloss.org (for Machine Learning, 674 entries), SBGrid (structural biology, 450 entries), CSDMS portal (Geosciences, 300 entries)

### "Raw" research software resources

Some general software service and aggregators providing useful information: 

- [libraries.io](https://libraries.io): aggregator of software package/library objects. Free API requests are subject to a 60/request/minute rate limit based on the api_key. The data is CC-BY-SA, but the tool itself is AGPL.

- GitHub, Gitlab, Bitbucket

- General dependency management systems like CRAN, Maven, NPM, etc. can provide interesting metadata (in particular CRAN) and usage information

- [Software Heritage](https://www.softwareheritage.org) provides in a central place a huge archive of Open source software. [World of Code](https://arxiv.org/abs/2010.16196) rather offers a sandbox of GitHub mirrors for research studies. 

### Other

List of programming languages: 

- https://foldoc.org/source.html

- Bill Kinnersley's computer language list (2500)
https://web.archive.org/web/20160506170543/http://people.ku.edu/~nkinners/LangList/Extras/langlist.htm

- https://hopl.info/ 
(Do not copy, do not reproduce!)

A lis of Open Source Sofware licenses: https://libraries.io/licenses
