import re 
import sys

sys.path.append('.')
sys.path.append('..')

from common import process_author_field, process_r_author_field, process_maintainer_field, process_url_field

known_attributes = ['role', 'given', 'email', 'comment', 'family']

r_author_fields = [ 'c(person(given = \"Greg Finak\", role=c(\"aut\",\"cre\",\"cph\"), email=\"gfinak@fredhutch.org\"),\nperson(given = \"Paul Obrecht\", role=c(\"ctb\")),\nperson(given = \"Ellis Hughes\", role=c(\"ctb\")),\nperson(\"Kara\", \"Woo\", role = \"rev\",\ncomment = \"Kara reviewed the package for ropensci, see <https://github.com/ropensci/onboarding/issues/230>\"),\nperson(\"William\", \"Landau\", role = \"rev\",\ncomment = \"William reviewed the package for ropensci, see <https://github.com/ropensci/onboarding/issues/230>\"))',
                  'person("Karthik", "Ram", role = c("aut", "cre"), email = "karthik.ram@gmail.com", comment = c(ORCID = "0000-0002-0233-1757"))',
                  'c(person(given = \"Lluís\",\nfamily = \"Revilla Sancho\",\nrole = c(\"aut\", \"cre\"),\nemail = \"lluis.revilla@gmail.com\",\ncomment = c(ORCID = \"0000-0001-9747-2570\")),\nperson(given = \"Zebulun\",\nfamily = \"Arendsee\",\nrole = \"rev\"),\nperson(given = \"Jennifer Chang\",\nrole = \"rev\"))'
                ]

author_fields = [ 'Yihui Xie <a href="https://orcid.org/0000-0003-0645-5666"><img alt="ORCID iD" src="CRAN_Package_knitr_files/orcid.svg" style="width:16px; height:16px; margin-left:4px; margin-right:4px; vertical-align:middle"></a> [aut,\n    cre],\n  Adam Vogt [ctb],\n  Alastair Andrew [ctb],\n  Alex Zvoleff [ctb],\n  Andre Simon [ctb] (the CSS files under inst/themes/ were derived from\n    the Highlight package http://www.andre-simon.de),\n  Aron Atkins [ctb],\n  Aaron Wolen [ctb],\n  Ashley Manton [ctb],\n  Atsushi Yasumoto <a href="https://orcid.org/0000-0002-8335-495X"><img alt="ORCID iD" src="CRAN_Package_knitr_files/orcid.svg" style="width:16px; height:16px; margin-left:4px; margin-right:4px; vertical-align:middle"></a>\n    [ctb],\n  Ben Baumer [ctb],\n  Brian Diggs [ctb],\n  Brian Zhang [ctb],\n  Cassio Pereira [ctb],\n  Christophe Dervieux [ctb],\n  David Hall [ctb],\n  David Hugh-Jones [ctb],\n  David Robinson [ctb],\n  Doug Hemken [ctb],\n  Duncan Murdoch [ctb],\n  Elio Campitelli [ctb],\n  Ellis Hughes [ctb],\n  Emily Riederer [ctb],\n  Fabian Hirschmann [ctb],\n  Fitch Simeon [ctb],\n  Forest Fang [ctb],\n  Frank E Harrell Jr [ctb] (the Sweavel package at inst/misc/Sweavel.sty),\n  Garrick Aden-Buie [ctb],\n  Gregoire Detrez [ctb],\n  Hadley Wickham [ctb],\n  Hao Zhu [ctb],\n  Heewon Jeon [ctb],\n  Henrik Bengtsson [ctb],\n  Hiroaki Yutani [ctb],\n  Ian Lyttle [ctb],\n  Hodges Daniel [ctb],\n  Jake Burkhead [ctb],\n  James Manton [ctb],\n  Jared Lander [ctb],\n  Jason Punyon [ctb],\n  Javier Luraschi [ctb],\n  Jeff Arnold [ctb],\n  Jenny Bryan [ctb],\n  Jeremy Ashkenas [ctb, cph] (the CSS file at\n    inst/misc/docco-classic.css),\n  Jeremy Stephens [ctb],\n  Jim Hester [ctb],\n  Joe Cheng [ctb],\n  Johannes Ranke [ctb],\n  John Honaker [ctb],\n  John Muschelli [ctb],\n  Jonathan Keane [ctb],\n  JJ Allaire [ctb],\n  Johan Toloe [ctb],\n  Jonathan Sidi [ctb],\n  Joseph Larmarange [ctb],\n  Julien Barnier [ctb],\n  Kaiyin Zhong [ctb],\n  Kamil Slowikowski [ctb],\n  Karl Forner [ctb],\n  Kevin K. Smith [ctb],\n  Kirill Mueller [ctb],\n  Kohske Takahashi [ctb],\n  Lorenz Walthert [ctb],\n  Lucas Gallindo [ctb],\n  Marius Hofert [ctb],\n  Martin Modrák [ctb],\n  Michael Chirico [ctb],\n  Michael Friendly [ctb],\n  Michal Bojanowski [ctb],\n  Michel Kuhlmann [ctb],\n  Miller Patrick [ctb],\n  Nacho Caballero [ctb],\n  Nick Salkowski [ctb],\n  Niels Richard Hansen [ctb],\n  Noam Ross [ctb],\n  Obada Mahdi [ctb],\n  Qiang Li [ctb],\n  Ramnath Vaidyanathan [ctb],\n  Richard Cotton [ctb],\n  Robert Krzyzanowski [ctb],\n  Romain Francois [ctb],\n  Ruaridh Williamson [ctb],\n  Scott Kostyshak [ctb],\n  Sebastian Meyer [ctb],\n  Sietse Brouwer [ctb],\n  Simon de Bernard [ctb],\n  Sylvain Rousseau [ctb],\n  Taiyun Wei [ctb],\n  Thibaut Assus [ctb],\n  Thibaut Lamadon [ctb],\n  Thomas Leeper [ctb],\n  Tim Mastny [ctb],\n  Tom Torsney-Weir [ctb],\n  Trevor Davis [ctb],\n  Viktoras Veitas [ctb],\n  Weicheng Zhu [ctb],\n  Wush Wu [ctb],\n  Zachary Foster [ctb]',
                  'Matthew Strimas-Mackey [aut, cre]\n(<https://orcid.org/0000-0001-8929-7776>),\nEliot Miller [aut],\nWesley Hochachka [aut],\nCornell Lab of Ornithology [cph]'
                ]

maintainer_fields = [ 'Alexander Zizka <alexander.zizka@idiv.de>',
                      'Yihui Xie  <xie at yihui.name>'
                    ]

url_fields = [ 'https://docs.ropensci.org/c14bazAAR,\nhttps://github.com/ropensci/c14bazAAR',
              '<a href="https://yihui.org/knitr/">https://yihui.org/knitr/</a>',
              'https://github.com/CornellLabofOrnithology/auk,\nhttps://cornelllabofornithology.github.io/auk/'
            ]

pattern_person = r'person\((.+)\)[\)|,|\n]'
regex_person = re.compile(pattern_person)

orcid_pattern = r'([0-9]{4}\-[0-9]{4}\-[0-9]{4}\-[0-9]{4})'
regex_orcid = re.compile(orcid_pattern)

for author_field in r_author_fields:
    print(author_field.replace("\n", " "))
    persons = process_r_author_field(author_field)
    print(persons, "\n")

for author_field in author_fields:
    print(author_field.replace("\n", " "))
    persons = process_author_field(author_field)
    print(persons, "\n")

for maintainer_field in maintainer_fields:
    print(maintainer_field.replace("\n", " "))
    persons = process_maintainer_field(maintainer_field)
    print(persons, "\n")

for url_field in url_fields:
    print(url_field.replace("\n", " "))
    urls = process_url_field(url_field)
    print(urls, "\n")