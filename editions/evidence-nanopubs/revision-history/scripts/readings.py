"""Match directly asserted measurements to the passages quoted by a nanopublication."""
from decimal import Decimal
import re

UNITS = {
    'mm': ('m', '0.001'), 'cm': ('m', '0.01'), 'm': ('m', '1'), 'km': ('m', '1000'),
    'ms': ('s', '0.001'), 's': ('s', '1'), 'min': ('s', '60'), 'h': ('s', '3600'),
    'mg': ('g', '0.001'), 'g': ('g', '1'), 'kg': ('g', '1000'),
    'mV': ('V', '0.001'), 'V': ('V', '1'), 'Pa': ('Pa', '1'), 'kPa': ('Pa', '1000'),
    '%': ('%', '1'), '°C': ('°C', '1'),
}
MEASUREMENT = re.compile(
    r'(?<![\w.])(?P<number>[+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)\s*'
    r'(?P<unit>' + '|'.join(map(re.escape, sorted(UNITS, key=len, reverse=True))) + r')(?![A-Za-z0-9/²³^])',
    flags=re.ASCII)

def readings(text):
    result = {}
    for match in MEASUREMENT.finditer(text):
        dimension, factor = UNITS[match['unit']]
        number = Decimal(match['number'].replace('−', '-')) * Decimal(factor)
        result[number, dimension] = match[0]
    return result
