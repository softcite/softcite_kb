import re
from bs4 import BeautifulSoup

orcid_pattern = r'([0-9]{4}\-[0-9]{4}\-[0-9]{4}\-[0-9]{3}[a-zA-Z0-9])'
regex_orcid = re.compile(orcid_pattern)

repo_patterns = ["https://github.com/", "https://github.com/", "https://gitlab.com/", "https://bitbucket.org/", "https://sourceforge.net/projects/"]

def is_git_repo(url):
    for repo in repo_patterns:
        if url.find(repo) != -1:
            return True
    return False

def process_r_author_field(author_field):

    # first get each person clause
    author_field = author_field.replace("\n", " ")
    if author_field.startswith("c(") and author_field.endswith(")"):
        author_field = author_field[2:-1]

    #print(author_field)

    person_strings = []
    while len(author_field)>0:
        pos2 = author_field.find('person(')
        if pos2 == -1:
            break;

        pos3 = author_field.find('person(', pos2+1)
        if pos3 == -1:
            pos3 = len(author_field)-1

        local_string = author_field[pos2:pos3]
        local_string = local_string.replace("person(", "")
        if local_string.endswith("), "):
            local_string = local_string[:-3]

        person_strings.append(local_string)
        author_field = author_field[pos3:]

    persons = []
    for person_string in person_strings:
        #print("\nPerson")
        person = {}
        person_string = person_string.strip()
        #print(person_string)
        ind = 0
        while ind != -1:
            if len(person_string) <= 1:
                break

            if person_string.startswith("\""):
                # we don't have a known attribute, but directly a person name component
                attribute = 'given'
            else:
                ind = person_string.find("=")
                attribute = None

            if ind != -1:
                if attribute is None:
                    attribute = person_string[0:ind].strip(", ")
            
                # do we have a list as value?
                if person_string[ind:].strip().startswith('=c(') or person_string[ind:].strip().startswith('= c('):
                    ind2 = person_string.find("),", ind)
                else:
                    if attribute == 'comment':
                        ind_com = person_string.find("\"", ind)
                        ind2 = person_string.find("\"", ind_com+1)
                        if ind2 != -1:
                            # shift the last "
                            ind2 += 1
                    else:
                        ind2 = person_string.find(", ", ind)
                
                if ind2 == -1:
                    ind2 = len(person_string)

                value = person_string[ind:ind2].strip(" =\"")

                if value.startswith("c("):
                    # this is an array
                    value = value[2:].strip()
                    pieces = value.split(",")
                    values = []
                    for piece in pieces:
                        values.append(piece.strip(" \""))
                    value = values

                if attribute == 'comment':
                    # we extract the orcid if present
                    # normally the value is a list, but not sure
                    orcid = None
                    if isinstance(value, str):
                        result_match = regex_orcid.search(value)
                        if not result_match is None:
                            orcid = result_match.group(1)
                    else:
                        for val in value:
                            result_match = regex_orcid.search(val)
                            if not result_match is None:
                                orcid = result_match.group(1)
                                break
                    if orcid != None:
                        person['orcid'] = orcid
                
                if attribute in person:
                    person[attribute] = person[attribute] + ' ' + value
                else:
                    person[attribute] = value

                person_string = person_string[ind2:]
                person_string = person_string.strip(" ,)")

        persons.append(person)

    return persons


def process_author_field(author_field):

    # first get each person clause
    author_field = author_field.replace("\n", " ")

    persons = []

    pos = 0
    pieces = []
    while pos != -1:
        new_pos = author_field.find("],", pos)
        if new_pos != -1:
            local_subfield = author_field[pos:new_pos+2]
            # try sub-segment for ")," boundaries
            extra_pos = local_subfield.find("),")
            if extra_pos != -1:
                pieces.append(local_subfield[:extra_pos+2].strip())
                pieces.append(local_subfield[extra_pos+2:].strip())
            else:
                pieces.append(local_subfield.strip())
            pos = new_pos+2
        else:
            # last piece
            pieces.append(author_field[pos:].strip())
            pos = -1

    for piece in pieces:
        #print(piece)
        person = {}
        last_pos = len(piece)
        pos = piece.find("<");
        orcid = None
        if pos != -1:
            # find last occuring > in this piece
            pos2 = piece.find(">");
            # try to fish an orcid there 
            result_match = regex_orcid.search(piece[pos:pos2])
            if not result_match is None:
                orcid = result_match.group(1)
            if pos < last_pos:
                last_pos = pos
        if orcid != None:
            person['orcid'] = orcid

        pos = piece.find("[");
        if pos != -1:
            pos2 = piece.find("]", pos);
            if pos2 != -1:
                # roles are there
                subpieces = piece[pos+1:pos2].split(",")
                roles = []
                for subpiece in subpieces:
                    if subpiece.endswith(")"):
                        subpiece = subpiece[:-1]
                    roles.append(subpiece.strip(" \""))
                if len(roles)>0:
                    person["roles"] = roles

            if pos < last_pos:
                last_pos = pos

        pos = piece.find("(");
        if pos != -1:
            pos2 = piece.find(")", pos);
            if pos2 != -1:
                # comment
                person["comment"] = clean_field(piece[pos+1:pos2])
            if pos < last_pos:
                last_pos = pos

        # forname name
        person["full_name"] = piece[:last_pos].strip()

        persons.append(person)
        
    return persons

def process_maintainer_field(maintainer_field):
    '''
    very simple field with single person full name and email
    '''
    person = {}
    pos = maintainer_field.find("<")
    if pos != -1:
        pos2 = maintainer_field.find(">")
        if pos2 != -1:
            person["email"] = maintainer_field[pos+1:pos2].strip()
            if person["email"].find(" at "):
                person["email"] = person["email"].replace(" at ", "@")
        person["full_name"] = maintainer_field[:pos].strip()
    else:
        person["full_name"] = maintainer_field.strip()
    return person

def process_url_field(url_field):
    '''
    we can have a list of URL (rOpenSci), possibly with mark-up (cran) 
    '''
    urls = []
    pieces = url_field.split(",\n")
    for piece in pieces:
        piece = piece.strip()

        subpieces = piece.split(",")
        for subpiece in subpieces:
            subpiece = subpiece.strip()

            if subpiece.startswith("<a"):
                soup = BeautifulSoup(subpiece, "lxml")
                subpiece = soup.text
            urls.append(subpiece)

    return urls

def process_boolean_field(boolean_field):
    boolean_field = boolean_field.strip().lower()
    if boolean_field == 'no' or boolean_field == 'false':
        return False
    else:
        return True

def process_dependency_field(dependency_field, role):
    dependency_field = dependency_field.replace("\n", " ")
    dependencies = []

    pieces = dependency_field.split(", ")
    for piece in pieces:
        piece = piece.strip()
        package = {}
        soup = BeautifulSoup(piece, "lxml")
        if soup.find('a') != None:
            #package["package"] = soup.find('a').text
            package["package"] = soup.text
        else:
            ind = piece.find("(")
            if ind != -1:
                package["package"] = piece[:ind]
                package["version"] = piece[ind+1:-1]
            else:
                package["package"] = piece
        package["role"] = role
        dependencies.append(package)
    return dependencies

def clean_field(string):
    string = string.replace("\n", " ")
    string = string.replace("\t", " ")
    string = re.sub(r"\s+", " ", string)
    return string.strip()
