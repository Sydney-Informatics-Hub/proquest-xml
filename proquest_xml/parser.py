"""Tools for reading/parsing ProQuest XML documents."""
import copy
from typing import List, Set, Dict, Tuple, Optional
from xml.etree import ElementTree

import pandas
import xmltodict
import dpath.util
from bs4 import BeautifulSoup


class ProquestXml:
    """
    Parse a ProQuest XML document and convert it to a Python dictionary.
    """

    def __init__(self, filename: str):
        """
        filename (str): Path to the XML file
        """
        # xmltodict has issues with the encoding of the XML files
        #   so run through ElementTree first
        tree = ElementTree.parse(filename)
        tree_string = ElementTree.tostring(tree.getroot(), encoding='utf-8',
                                           method='xml')
        xml_dict = xmltodict.parse(tree_string)
        # Don't think we need the top-level 'RECORD' node
        self._dict = xml_dict['RECORD']
        self.id = self['GOID']

    def __getitem__(self, y):
        return self._dict[y]

    def show_all_keys(self):
        """
        Print all the keys in the data, indenting keys at lower levels
        to show the structure of the tree.
        """

        def _show(dct, context=''):
            for key, val in dct.items():
                print(context + key)
                if isinstance(val, dict):
                    _show(val,
                          context=context + '  ')

        _show(self._dict)

    def get(self, path: str, default=None):
        """
        Get an item from the nested dictionary using a path like
        '/key1/key2/name'.

        path (str): Location of the item
        """
        return dpath.util.get(self._dict, path, default=default)

    def search(self, path: str):
        """
        Search for items in the nested dictionary using fuzzy
        matching, e.g. 'DFS/PubFrosting/*Title*' to find
        all items under DFS/PubFrosting containing Title
        """
        return dpath.util.search(self._dict, path)

    def get_dict(self):
        """
        Get the XML data as a dictionary.
        """
        return copy.deepcopy(self._dict)

    def get_text(self, clean_html: bool=True):
        """
        Get the main article text, removing HTML tags if necessary.
        """
        is_html = self.get('TextInfo/Text/@HTMLContent') == 'true'
        text = self.get('TextInfo/Text/#text')

        if clean_html and is_html:
            soup = BeautifulSoup(text, "lxml")
            return soup.body.get_text()
        else:
            return text

    def get_terms(self):
        """
        Get the GenSubjTerm's from the document
        """
        def _get_term(term_entry):
            return term_entry['GenSubjValue']

        term_info = self.get('Obj/Terms/GenSubjTerm')
        if term_info is None:
            return None
        elif isinstance(term_info, list):
           terms = [_get_term(entry) for entry in term_info]
        else:
            terms = [_get_term(term_info)]
        return terms

    def get_authors(self) -> List[Dict[str, str]]:
        """
        Get the author information for the article

        :returns: List of dictionaries with author first name and last name,
           in contribution order.
        """
        def _extract_info(author_entry):
            fields = {
                'order': '@ContribOrder',
                'last_name': 'Author/LastNameAtt/LastName',
                'first_name': 'Author/FirstNameAtt/FirstName',
                # Not all entries have last/first name recorded,
                # may have to extract full name
                'full_name': 'Author/OriginalFormAtt/OriginalForm'
            }
            return {field: dpath.util.get(author_entry, path, default=None)
                    for field, path in fields.items()}

        contributors = self.get('Obj/Contributors/Contributor')
        # Multiple authors
        if isinstance(contributors, list):
            authors = [_extract_info(author) for author in contributors]
            authors.sort(key=lambda x: int(x['order']))
        else:
            authors = [_extract_info(contributors)]
        return authors

    def get_article_title(self):
        """
        Return the article title
        """
        return self.get('Obj/TitleAtt/Title')

    def to_record(self, extra_fields: Dict[str, str]=None) -> Dict:
        """
        Get the most important information about the article
        and return it as a flat dictionary.

        extra_fields (dict): A {field_name: dict_path} dictionary
          of extra fields you want to add to the record.
        """
        first_author, *other_authors = self.get_authors()
        record = {
            'id': self.id,
            'title': self.get_article_title(),
            'date_published': pandas.to_datetime(
                self.get('Obj/NumericDate'),
                format='%Y-%m-%d'
            ),
            'publication': self.get('/DFS/PubFrosting/Title'),
            'author1_last_name': first_author['last_name'],
            'author1_first_name': first_author['first_name'],
            'author1_full_name': first_author['full_name'],
            'other_authors': other_authors,
            'article_type': self.get('/Obj/ObjectTypes/mstar'),
            'text': self.get_text()
        }

        if extra_fields is not None:
            for field_name, field_getter in extra_fields.items():
                if isinstance(field_getter, str):
                    record[field_name] = self.get(field_getter)
                elif callable(field_getter):
                    record[field_name] = field_getter(self)

        return record


def create_dataframe(xml_docs: List[ProquestXml], extra_fields=None):
    """
    Create a pandas dataframe from multiple ProquestXml objects.

    xml_docs: a list of ProquestXml documents.
    """
    return pandas.DataFrame.from_records([
        doc.to_record(extra_fields) for doc in xml_docs
    ])
