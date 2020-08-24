import re
import nltk
import numpy as np
import pandas as pd

from bs4 import BeautifulSoup, NavigableString, Tag

# HTML block elements from
# https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
BLOCK_ELEMENTS = [
    'address', 'article', 'aside', 'blockquote', 'details',
    'dialog', 'dd', 'div', 'dl', 'dt', 'fieldset', 'figcaption',
    'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5',
    'h6', 'header', 'hgroup', 'hr', 'li', 'main', 'nav', 'ol',
    'p', 'pre', 'section', 'table', 'ul'
]


def _break_up_block_elements(tag: Tag):
    """Insert newlines before all block elements in a BeautifulSoup tag,
       recursively."""
    if hasattr(tag, 'children'):
        for child in list(tag.children):
            if child.name in BLOCK_ELEMENTS:
                child.insert_before(NavigableString('\n'))
            _break_up_block_elements(child)


def get_text_from_html(html_text: str):
    """
    Get cleaned text from HTML, stripping all HTML tags while
    attempting to preserve spaces between paragraphs/elements.
    
    html_text (str): HTML markup to be cleaned
    """
    soup = BeautifulSoup(html_text, 'lxml')
    body = soup.find('body')
    _break_up_block_elements(body)
    text = body.get_text(separator=' ')
    # Remove additional newlines
    text = re.sub('\n( ?\n)+', '\n\n', text)
    return '\n'.join(s.strip() for s in text.splitlines())


def filter_company_reports(docs):
    """
    Filter out Company Data reports from dictionaries
    consisting of ProquestXml objects
    """
    filtered_dictionary = dict()
    for key, value in docs.items():
        if value.get('DFS/PubFrosting/Title') != 'Company Data Report': 
            filtered_dictionary[key] = value
    return filtered_dictionary


def enter_query():
    """
    Create a word list for querying the product of 
    concordance_dataframe()
    """
    word_list = []
    user_input = input("Please enter the words you wish to query separated by commas (e.g. rights,freedoms,liberties). If you wish to query multiple words at the same time, separate them using a space (e.g. freedoms,human rights,liberties)")
    if len(user_input) > 0:
        word_list.append(user_input.split(','))
    else:
        print("No words were entered, please try again.")
    return word_list[0]


def concordance_dataframe(dataframe, words):
    """
    Concordance function
    Process the dataframe created from ProquestXml objects
    """
    
    df = dataframe
    word_list = words
    df['tokenised_text'] = df['text'].map(nltk.word_tokenize)
    df['text_object'] = df['tokenised_text'].map(nltk.Text)
    
    # Apply concordance_list to each row
    def concordance_object(row):
        result = []
        for word in word_list:
            list_object = row.concordance_list(word)
            result.append(list_object)
        return result
    
    # Apply concordance_object to df
    df['concordance_list'] = df['text_object'].map(concordance_object)
    
    # Unnest first level of lists within "concordance_list"
    df = df.explode('concordance_list')
    df['concordance_list'] = df['concordance_list'].map(lambda x: np.nan if x==[] else x)
    df.reset_index(inplace = True, drop = True) 
    
    # Unnest the next level
    df = df.explode('concordance_list')
    df.reset_index(inplace = True, drop = True)  ## problem line
    
    # Select the columns of interest and drop NAs
    df[["left", "query", "right", "offset", "left_print", "right_print", "line"]] = df['concordance_list'].apply(pd.Series)
    df = df[['id', 'title', 'date_published', 'publication', 'author1_last_name', 'author1_first_name', 'other_authors', 'article_type', 'left', 'query', 'right']]
    df = df.dropna(subset=['query'])
    
    # Process text for readability
    df['left'] = df['left'].apply(' '.join)
    df['right'] = df['right'].apply(' '.join)

    # Drop duplicates
    df = df.drop_duplicates(subset=['left'], keep='first', inplace=False)
    
    return df