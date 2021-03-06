import sys
import json

sys.path.append('.')
sys.path.append('..')

#from merge.merge import _capitalized_variant

string_input_test = ['knitr', 'STATA', 'Stata', "MICROSOFT WORD"]
string_output_expected = [None, 'Stata', None, "Microsoft Word"] 

def _capitalized_variant(term):
    '''
    For a term all upper-cased, generate the term variant with only first letter of term components upper-cased
    '''
    if not term.isupper():
        return None

    term_variant = ''
    start = True
    for c in term:
        if start:
            start = False
            term_variant += c
        else:
            if c == ' ' or c == '-':
                start = True
                term_variant += c
            else:
                term_variant += c.lower()
    return term_variant

for i, string in enumerate(string_input_test):
    variant = _capitalized_variant(string)
    if variant != string_output_expected[i]:
        print("Test failed for", string, " -> expected:", string_output_expected[i], "/ actual:", variant)

