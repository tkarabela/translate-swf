"""
pyTranslateSwf package
======================

This library implements tools to translate SWF (Flash) files from Japanese to English.

  * pyTranslateSwf.parsers - code to extract and replace strings in extracted SWF assets
  * pyTranslateSwf.translators - code to do machine translation (offline or cloud-based)
  * pyTranslateSwf.corpus - helper class to store (original, translated) string pairs
  * pyTranslateSwf.cli - the commandline interface used by the translateSwf.py script

"""

from .parsers import Parser, JPEXSPlainTextParser, JPEXSActionScriptParser, get_parsers_for_directory
from .translators import Translator, OfflineTranslator, MicrosoftAzureTranslator
from .corpus import ParallelCorpus
from .cli import PyTranslateSwfCLI
