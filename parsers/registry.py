from typing import Dict
from parsers.base import LanguageParser

class ParserRegistry:
    """Registry to map file languages to their respective parsers."""
    
    _parsers: Dict[str, LanguageParser] = {}

    @classmethod
    def register(cls, language: str, parser: LanguageParser):
        cls._parsers[language.lower()] = parser

    @classmethod
    def get_parser(cls, language: str) -> LanguageParser:
        if not language:
            raise ValueError("No language specified for parsing.")
            
        parser = cls._parsers.get(language.lower())
        if not parser:
            raise NotImplementedError(f"Unsupported language: {language}")
            
        return parser
