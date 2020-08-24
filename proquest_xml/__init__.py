"""Utilities for handling ProQuest XML documents."""

__author__ = """Marius Mather"""
__email__ = 'marius.mather@sydney.edu.au'
__version__ = '0.1.1'

from .parser import ProquestXml, create_dataframe
from .utils import filter_company_reports, enter_query, concordance_dataframe

__all__ = ['ProquestXml', 'create_dataframe']
