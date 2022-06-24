# -*- coding: utf-8 -*-
from urllib.parse import parse_qsl
from aiida.parsers import Parser

class DftkParser(Parser):
    """`Parser` implementation for DFTK."""

    def parse(self, **kwargs):
        """Parse DFTK output files."""
        pass