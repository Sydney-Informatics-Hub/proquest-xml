import re

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
    return re.sub('\n( ?\n)+', '\n\n', text)
