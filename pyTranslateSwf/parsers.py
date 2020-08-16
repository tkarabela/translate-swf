"""
pyTranslateSwf.parsers module
=============================

Code to extract and replace strings in extracted SWF assets.

This module is to be used in conjunction with the JPEXS Flash Decompiler
(https://github.com/jindrapetrik/jpexs-decompiler), which can get
assets out of the SWF file and get modified assets back in. You can use
JPEXS GUI to do that.

Currently, there are two types of assets that can be processed:

  * 'texts' - see JPEXSPlainTextParser - export from JPEXS in 'Plain Text' format
  * 'scripts' - see JPEXSActionScriptParser - export from JPEXS in 'ActionScript' format

The Parser subclasses can extract strings from the files and also replace them.
For convenience, you can run get_parsers_for_directory() function over the directory
where you exported the assets and it will create the parsers for you (extracting strings
in the process).

The Parser subclasses are used as follows:

    >>> parser = JPEXSActionScriptParser("./scripts/test.as")
    >>> input_strings = parser.get_extracted_strings()
    >>> output_strings = [my_translate_function(s) for s in input_strings]
    >>> parser.replace_strings(output_strings)
    >>> parser.save()

See the pyTranslateSwf.translators module to see how translation is implemented.

Note that the parsers do some Japanese-specific detection heuristics.

"""

import itertools
from typing import List, Union
import io
import re
import os.path as op
import os
try:
    import regex
except ImportError:
    regex = None
    print("Warning - 'regex' module is not installed, JPEXSActionScriptParser heuristics will be less effective")


class Parser:
    """
    A base class for extracting and replacing text snippet in files
    """
    def __init__(self, path_or_file: Union[str, io.TextIOBase]):
        self.path: str = None
        self.data: str = None

        if isinstance(path_or_file, str):
            self.path = path_or_file
            with open(self.path, encoding="utf-8") as fp:
                self.data: str = fp.read()
        elif isinstance(path_or_file, io.TextIOBase):
            self.data: str = path_or_file.read()
        else:
            raise TypeError("Expected str or TextIO")

        self.strings: List[str] = self._extract_strings()

    def _extract_strings(self) -> List[str]:
        raise NotImplementedError

    def get_extracted_strings(self):
        return self.strings

    def replace_strings(self, strings: List[str]):
        raise NotImplementedError

    def save(self, path: str=None):
        output_path = path if path is not None else self.path

        with open(output_path, "w", encoding="utf-8") as fp:
            fp.write(self.data)

    def __repr__(self):
        return f"<{self.__class__.__name__} path={self.path!r}>"


class JPEXSPlainTextParser(Parser):
    """Parser for text blocks exported via JPEXS decompiler in 'plain text' format"""
    SEPARATOR = "\n--- RECORDSEPARATOR ---\n"

    def _extract_strings(self) -> List[str]:
        return self.data.split(self.SEPARATOR)

    def replace_strings(self, strings: List[str]):
        if len(strings) != len(self.strings):
            raise ValueError("String count mismatch")

        self.data = self.SEPARATOR.join(strings)


class JPEXSActionScriptParser(Parser):
    """
    Parser for HTML string literals in ActionScript

    As we do not want to replace all string literals in the file (which may be identifiers, etc.),
    but only 'shown text' strings, we are going to willfully ignore some string literals.
    Currently, there are two modes for this:

      * mode='html' - this will only process "<html>...</html>" literals, pretty safe
      * mode='heuristic' - the same as 'html' and additionally allowing sentence-like strings
        (including Japanese punctuation), this is less safe but will translate more text

    """
    HTML_MARKUP_PATTERN = re.compile(r"\s*</?[^>]*>\s*|\s*&[a-zA-Z0-9#]+;\s*", re.UNICODE)
    STRING_LITERAL_PATTERN = re.compile(r"\"([^\"]*)\"")  # FIXME does not handle \"
    HTML_TAGS_PATTERN = re.compile(r"<html>.*</html>")
    SENTENCE_PUNCTUATION_PATTERN = re.compile(r"[「」、。？…]")

    MODE_HTML = "html"
    MODE_HEURISTIC = "heuristic"
    MODES = (
        MODE_HTML,
        MODE_HEURISTIC
    )

    def __init__(self, path_or_file: Union[str, io.TextIOBase], mode=MODE_HEURISTIC):
        if mode not in self.MODES:
            raise ValueError(f"Unsupported parser mode, use one of {self.MODES}")
        self.mode = mode

        super().__init__(path_or_file)

    def _ignore_string(self, literal_without_quotes: str) -> bool:
        """Return True if we do not want to 'see' this string literal"""
        if self.mode == self.MODE_HTML:
            if self.HTML_TAGS_PATTERN.fullmatch(literal_without_quotes):
                return False
        elif self.mode == self.MODE_HEURISTIC:
            if self.HTML_TAGS_PATTERN.fullmatch(literal_without_quotes):
                return False

            if self.SENTENCE_PUNCTUATION_PATTERN.search(literal_without_quotes):
                return False

            # strings consisting of 6+ kana/kanji and nothing else
            if regex and regex.fullmatch(r"\p{General_Category=Other_Letter}{6,}", literal_without_quotes):
                return False
        else:
            raise NotImplementedError("Unsupported parser mode")

        return True

    def _extract_strings(self) -> List[str]:
        strings = []

        def string_literal_action(m):
            literal_without_quotes = m.group(1)
            if not self._ignore_string(literal_without_quotes):
                string_chunks = self.HTML_MARKUP_PATTERN.split(literal_without_quotes)
                strings.extend(string_chunks)

        for m in self.STRING_LITERAL_PATTERN.finditer(self.data):
            string_literal_action(m)

        return strings

    def replace_strings(self, strings: List[str]):
        if len(strings) != len(self.strings):
            raise ValueError("String count mismatch")

        i = 0

        # TODO consider making Parser use an AST instead of outputting as we parse, to make this less confusing
        def string_literal_action(m):
            nonlocal i
            literal_without_quotes = m.group(1)
            if not self._ignore_string(literal_without_quotes):
                string_chunks = self.HTML_MARKUP_PATTERN.split(literal_without_quotes)
                new_string_chunks = []
                for _ in string_chunks:
                    new_string_chunk = strings[i]

                    # escape it so that we don't break ActionScript string literal syntax
                    new_string_chunk = re.sub(r"[<\n&]", "", new_string_chunk.replace('"', "'"))

                    new_string_chunks.append(new_string_chunk)
                    i += 1

                markup_chunks = self.HTML_MARKUP_PATTERN.findall(literal_without_quotes)

                # interleave HTML markup and translated strings
                new_literal_without_quotes = "".join("".join(tmp) for tmp in itertools.chain(
                    itertools.zip_longest(new_string_chunks, markup_chunks, fillvalue="")))

                return f'"{new_literal_without_quotes}"'
            else:
                return m.group(0)  # passthrough

        self.data = self.STRING_LITERAL_PATTERN.sub(string_literal_action, self.data)


def _recursive_find_file_extension(starting_dir: str, ext: str):
    # because glob.glob doesn't play nice with Japanese filenames
    for root, dirs, files in os.walk(starting_dir):
        for filename in files:
            if op.splitext(filename)[1] == ext:
                yield op.join(root, filename)


def get_parsers_for_directory(jpexs_export_dir_path: str, actionscript_mode: str="heuristic") -> List[Parser]:
    """
    Return list of Parser objects for files in JPEXS export directory

    Currently, this can parse text files (texts/*.txt) and ActionScript sources (scripts/**/*.as).
    """
    parsers = []

    # text files
    for path in _recursive_find_file_extension(jpexs_export_dir_path, ".txt"):
        parser = JPEXSPlainTextParser(path)
        parsers.append(parser)

    # ActionScript files
    for path in _recursive_find_file_extension(jpexs_export_dir_path, ".as"):
        parser = JPEXSActionScriptParser(path, mode=actionscript_mode)
        parsers.append(parser)

    return parsers
