import sys
import os
import requests
import functools
from random import randint, choices

pmc_base_web = "https://www.ncbi.nlm.nih.gov/pmc/articles/"

def unpaywalling_doi(unpaywall_base, unpaywall_email, doi):
    """
    Check the Open Access availability of the DOI via Unpaywall, return the best download URLs (best first).
    Return empty list of not available following Unpaywall. 
    We use the Unpaywall API to get fresh information.
    """
    urls = []
    if not unpaywall_base.endswith("/"):
        unpaywall_base += "/"
    response = requests.get(unpaywall_base + doi, 
        params={'email': unpaywall_email}, verify=False, timeout=10).json()
    if response['best_oa_location'] and response['best_oa_location']['url_for_pdf']:
        urls.append(response['best_oa_location']['url_for_pdf'])

    if response['best_oa_location']['url'].startswith(pmc_base_web):
        url.append(response['best_oa_location']['url']+"/pdf/")

    # we have a look at the other "oa_locations", which might have a `url_for_pdf` ('best_oa_location' has not always a 
    # `url_for_pdf`, for example for Elsevier OA articles)
    for other_oa_location in response['oa_locations']:
        # for a PMC file, we can concatenate /pdf/ to the base, eg https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7029158/pdf/
        # but the downloader will have to use a good User-Agent and follow redirection
        if other_oa_location['url'].startswith(pmc_base_web) and not other_oa_location['url']+"/pdf/" in urls:
            urls.append(other_oa_location['url']+"/pdf/")
        if other_oa_location['url_for_pdf'] and other_oa_location['url_for_pdf'] not in urls:
            urls.append(other_oa_location['url_for_pdf'])
    return urls


async def pdf_streamer(url, chunk_size=8000):
    print(url)
    user_agent = { 'User-Agent': _get_random_user_agent() }
    r = requests.get(url, stream=True, allow_redirects=True, headers=user_agent)
    if r.url != url:
        print("redirect:", r.url)
        print(r.status_code)
    for chunk in r.iter_content(chunk_size):
        yield chunk


def _get_random_user_agent():
    '''
    This is a simple random/rotating user agent covering different devices and web clients/browsers
    Note: rotating the user agent without rotating the IP address (via proxies) might not be a good idea if the same server
    is harvested - but in our case we are harvesting a large variety of different Open Access servers
    '''
    user_agents = ["Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0",
                   "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"]
    weights = [0.2, 0.3, 0.5]
    user_agent = choices(user_agents, weights=weights, k=1)

    return user_agent[0]

def sortMentionWithContexts(kb, mention_ids):
    ''' 
    Given a list mention identifiers, retrieve the full object and sort the list based on mention informativeness:
    we sort by number of annotations in the mention snippet, then by the length of the snippet
    '''
    full_mentions = []
    for mention_id in mention_ids:
        cursor = kb.db.aql.execute(
            'FOR mention IN citations ' +
            '  FILTER mention._id == "' + mention_id + '"' +
            '  RETURN mention')

        for mention in cursor:
            full_mentions.append(mention)
            break

    full_mentions_sorted = sorted(full_mentions, key=functools.cmp_to_key(_sorting_full_mentions))

    result = []
    for full_mention in full_mentions_sorted:
        result.append(full_mention["_id"])

    return result

def _sorting_full_mentions(mentionX, mentionY):

    # we sort by number of annotations in the mention snippet, then by the length of the snippet
    
    # number of annotations
    nbAnnotationsX = 0
    '''
    if "P6166" in mentionX["claims"] and len(mentionX["claims"]["P6166"]) > 0 and "value" in mentionX["claims"]["P6166"][0]:
        # software name annotation
        if _non_propagated_field(mentionX["claims"]["P6166"][0]):
            nbAnnotationsX += 1
    '''
    if "P348" in mentionX["claims"] and len(mentionX["claims"]["P348"]) > 0 and "value" in mentionX["claims"]["P348"][0]:
        # version
        if _non_propagated_field(mentionX["claims"]["P348"][0]):
            nbAnnotationsX += 1
    
    if "P123" in mentionX["claims"] and len(mentionX["claims"]["P123"]) > 0 and "value" in mentionX["claims"]["P123"][0]:
        # publisher
        if _non_propagated_field(mentionX["claims"]["P123"][0]):
            nbAnnotationsX += 1
    
    if "P854" in mentionX["claims"] and len(mentionX["claims"]["P854"]) > 0 and "value" in mentionX["claims"]["P854"][0]:
        # url
        if _non_propagated_field(mentionX["claims"]["P854"][0]):
            nbAnnotationsX += 1

    nbAnnotationsY = 0
    '''
    if "P6166" in mentionY["claims"] and len(mentionY["claims"]["P6166"]) > 0 and "value" in mentionY["claims"]["P6166"][0]:
        # software name annotation
        if _non_propagated_field(mentionY["claims"]["P6166"][0]):
            nbAnnotationsY += 1
    '''
    if "P348" in mentionY["claims"] and len(mentionY["claims"]["P348"]) > 0 and "value" in mentionY["claims"]["P348"][0]:
        # version
        if _non_propagated_field(mentionY["claims"]["P348"][0]):
            nbAnnotationsY += 1
    
    if "P123" in mentionY["claims"] and len(mentionY["claims"]["P123"]) > 0 and "value" in mentionY["claims"]["P123"][0]:
        # publisher
        if _non_propagated_field(mentionY["claims"]["P123"][0]):
            nbAnnotationsY += 1
    
    if "P854" in mentionY["claims"] and len(mentionY["claims"]["P854"]) > 0 and "value" in mentionY["claims"]["P854"][0]:
        # url
        if _non_propagated_field(mentionY["claims"]["P854"][0]):
            nbAnnotationsY += 1

    if nbAnnotationsX < nbAnnotationsY:
        return 1
    
    if nbAnnotationsX > nbAnnotationsY:
        return -1

    # if same number of annotations, we look at the snippet length
    snippetLengthX = 0
    if "P7081" in mentionX["claims"] and len(mentionX["claims"]["P7081"]) > 0 and "value" in mentionX["claims"]["P7081"][0]:
        snippetX = mentionX["claims"]["P7081"][0]["value"]
        snippetLengthX = len(snippetX)
    
    snippetLengthY = 0
    if "P7081" in mentionY["claims"] and len(mentionY["claims"]["P7081"]) > 0 and "value" in mentionY["claims"]["P7081"][0]:
        snippetY = mentionY["claims"]["P7081"][0]["value"]
        snippetLengthY = len(snippetY)

    if snippetLengthX < snippetLengthY: 
        return 1
    
    if snippetLengthX > snippetLengthY:
        return -1
    
    return 0

def _non_propagated_field(statement):
    '''
    if the statement has coordinates/offsets in the qualifiers, it is not a propagated field and is anchor in the current context
    '''
    if "qualifiers" in statement: 
        return True
    else:
        return False
