"""Compare the direction and inclusiveness of numbered limits across two passages."""
from collections import Counter
from decimal import Decimal
import re

OPERATORS = {
    '<=': ('less than or equal to', 'no more than', 'at most', 'not greater than',
           '不大于', '不高于', '不超过', '小于等于', '小于或等于', '至多', '最多', '≤', '<='),
    '>=': ('greater than or equal to', 'no less than', 'at least', 'not less than',
           '不低于', '不少于', '不小于', '大于等于', '大于或等于', '至少', '≥', '>='),
    '<': ('less than', 'smaller than', 'lower than', 'below', '低于', '小于', '少于', '<'),
    '>': ('greater than', 'higher than', 'more than', 'above', '超过', '高于', '大于', '>'),
}
lookup = {term: key for key, terms in OPERATORS.items() for term in terms}
terms = sorted(lookup, key=len, reverse=True)
pattern = '|'.join((r'(?<![A-Za-z])' if term[0].isascii() and term[0].isalpha() else '')
                   + re.escape(term) for term in terms)
BOUND = re.compile(r'(?P<operator>' + pattern + r')(?:为|是)?\s*'
                   r'(?P<number>[+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)', re.I)

def limits(text):
    return Counter((lookup[m['operator'].casefold()], Decimal(m['number'].replace('−','-'))) for m in BOUND.finditer(text))

def without_limits(text):
    return BOUND.sub(lambda m: m['number'], text)
