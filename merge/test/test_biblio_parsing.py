import re 
import sys
from pybtex.database import parse_string
from pybtex import format_from_string
import json
import argparse

sys.path.append('.')
sys.path.append('..')

from merge.populate_staging_area import StagingArea

ref_field = { "References": [ { "raw": "Scott Fortmann-Roe (2015). Consistent and Clear Reporting of Results from Diverse Modeling Techniques: The A3 Method. Journal of Statistical Software, 66(7), 1-23. URL http://www.jstatsoft.org/v66/i07/." }, 
                              { "bibtex": "@Article{,\n    title = {Consistent and Clear Reporting of Results from Diverse\n      Modeling Techniques: The A3 Method},\n    author = {Scott Fortmann-Roe},\n    journal = {Journal of Statistical Software},\n    year = {2015},\n    volume = {66},\n    number = {7},\n    pages = {1--23},\n    url = {http://www.jstatsoft.org/v66/i07/},\n  }" }, 
                              { "bibtex": "@Article{,\
    title = {Combinacion de metodos factoriales y de analisis de\
      conglomerados en R: el paquete FactoClass},\
    author = {C.E. Pardo and P.C. DelCampo},\
    journal = {Revista Colombiana de Estadistica},\
    year = {2007},\
    volume = {30},\
    pages = {231-245},\
    number = {2},\
    url = {www.matematicas.unal.edu.co/revcoles},}"},
                              { "bibtex": "@Article{,\
    title = {S4 Classes for Distributions},\
    author = {P. Ruckdeschel and M. Kohl and T. Stabla and F.\
      Camphausen},\
    language = {English},\
    year = {2006},\
    journal = {R News},\
    year = {2006},\
    volume = {6},\
    number = {2},\
    pages = {2--6},\
    month = {May},\
    pdf = {https://CRAN.R-project.org/doc/Rnews/Rnews_2006-2.pdf},\
  }"},
                              { "bibtex": "@Article{,\
    author = {James S Ware and Kaitlin E Samocha and J Homsy and Mark J\
      Daly},\
    year = {2015},\
    title = {Interpreting de novo variation in human disease using\
      denovolyzeR.},\
    journal = {Curr. Protoc. Hum. Genet.},\
    volume = {87},\
    number = {7},\
    chapter = {25},\
    pages = {1},\
    pages = {15},\
    doi = {10.1002/0471142905.hg0725s87},\
    note = {R package version 0.2.0},\
    url = {http://denovolyzeR.org},\
  }"},
                              { "bibtex": "@Article{toto,\
    author = {Roozbeh Valavi and Jane Elith and José J. Lahoz-Monfort\
      and Gurutzeta Guillera-Arroita},\
    title = {blockCV: An R package for generating spatially or\
      environmentally separated folds for k-fold cross-validation of\
      species distribution models},\
    journal = {Methods in Ecology and Evolution},\
    volume = {10},\
    number = {2},\
    pages = {225-232},\
    year = {2019},\
    author = {Roozbeh Valavi and Jane Elith and José J. Lahoz-Monfort\
      and Gurutzeta Guillera-Arroita},\
  }"}
  ] }


def test_biblio(stagingArea):

    if "References" in ref_field:
        for reference in ref_field["References"]:
            if "bibtex" in reference:
                bibtex_str = reference["bibtex"]
                # force a key if not present, for having valid parsing
                bibtex_str = bibtex_str.replace("@Article{,", "@Article{toto,")
                biblio = None
                #try:
                biblio = parse_string(bibtex_str, "bibtex")
                #except:
                #    print("Failed to parse the bibtext string:", bibtex_str)

                if biblio != None:
                    for key in biblio.entries:
                        print(key)
                        local_title = biblio.entries[key].fields["title"]
                        local_authors = biblio.entries[key].persons
                        if "author" in local_authors:
                            all_authors = local_authors["author"]
                            first_author_last_name = all_authors[0].last_names[0]

                        text_format_ref = format_from_string(bibtex_str, style="plain")
                        res_format_ref = ""
                        for line_format_ref in text_format_ref.split("\n"):
                            if line_format_ref.startswith("\\newblock"):
                                res_format_ref += line_format_ref.replace("\\newblock", "")
                            elif len(line_format_ref.strip()) != 0 and not line_format_ref.startswith("\\"):
                                res_format_ref += line_format_ref

                        res_format_ref = res_format_ref.strip()
                        res_format_ref = res_format_ref.replace("\\emph{", "")
                        res_format_ref = res_format_ref.replace("\\url{", "")
                        res_format_ref = res_format_ref.replace("}", "")
                        print(res_format_ref)

                        print(stagingArea.biblio_glutton_lookup(raw_ref=res_format_ref, title=local_title, first_author_last_name=first_author_last_name))

            if "raw" in reference:
                # this can be sent to GROBID
                print(reference["raw"])
                print(stagingArea.biblio_glutton_lookup(raw_ref=reference["raw"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Test bibliographicla reference processing during import/populate of the KB")
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 

    args = parser.parse_args()
    config_path = args.config

    stagingArea = StagingArea(config_path=config_path)
    test_biblio(stagingArea)