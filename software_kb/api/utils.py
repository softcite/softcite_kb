import sys
import os
import requests
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

