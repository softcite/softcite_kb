import os
import json
import sys
sys.path.append('.')
sys.path.append('..')

from populate.cran_import import _convert_raw_package_record 

sample_html = "resources/CRAN_Package_knitr.html"
if not os.path.exists(sample_html):
    sample_html = "test/resources/CRAN_Package_knitr.html"

with open(sample_html) as file:
    content_html = file.read()

package_json = {}
package_json['Package'] = "knitr"
package_json = _convert_raw_package_record(content_html, package_json)

print(package_json)