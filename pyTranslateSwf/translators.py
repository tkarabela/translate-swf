"""
pyTranslateSwf.translators module
=================================

Code to do machine translation (offline or cloud-based).

This module can translate Japanese to English using one of the following:

  * Microsoft Azure Cognitive Services (cloud-based, recommended)
     - see MicrosoftAzureTranslator
     - requires Python modules: requests, uuid
     - requires Azure subscription key
  * custom offline solution (dictionary-based, low quality)
     - see OfflineTranslator
     - requires Python modules: stanza, jamdict, jaconv

Translations are batched and cached using pyTranslateSwf.corpus.ParallelCorpus
into file in current directory.

The Translator subclasses are used as follows:

    >>> translator = OfflineTranslator()
    >>> input_strings = ["こんにちは世界"]
    >>> output_strings = translator.translate_all(input_strings)
    >>> output_strings[0]
    "KONNICHI HA the world"

"""

import re
import os.path as op
from typing import List
from .corpus import ParallelCorpus

try:
    import stanza
    from jamdict import Jamdict
    import jaconv
except ImportError:
    stanza = None
    Jamdict = None
    jaconv = None
    print("Warning - cannot import one of 'stanza', 'jamdict', 'jaconv' modules"
          " - OfflineTranslator will not be available")

try:
    import uuid
    import requests
except ImportError:
    uuid = None
    requests = None
    print("Warning - cannot import one of 'uuid', 'requests' modules - MicrosoftAzureTranslator will not be available")


class Translator:
    """Base class for Japanese-to-English translators"""
    CACHE_NAME = None
    BATCH_SIZE = 500

    def __init__(self):
        self.cache = ParallelCorpus()
        self.load_cache()

    def load_cache(self):
        if self.CACHE_NAME and op.exists(self.CACHE_NAME):
            print("Loading translator cache", self.CACHE_NAME)
            self.cache = ParallelCorpus.from_json(self.CACHE_NAME)

    def write_cache(self):
        if self.CACHE_NAME:
            self.cache.to_json(self.CACHE_NAME)

    def translate_all(self, all_input_strings: List[str]) -> List[str]:
        """Translate given strings in batches of Translator.BATCH_SIZE, caching the results"""
        all_output_strings = []

        for i in range(0, len(all_input_strings), self.BATCH_SIZE):
            print("Progress:", i, "/", len(all_input_strings))
            # generate a slice of input, to play nice with cloud APIs
            input_strings = all_input_strings[i:i+self.BATCH_SIZE]

            # see which input strings we need to translate
            unknown_input_strings = [input_string for input_string in input_strings
                                     if input_string not in self.cache.orig_to_translation]
            unknown_input_strings_translation = self._translate_all(unknown_input_strings)

            # put new translations into cache
            for k, v in zip(unknown_input_strings, unknown_input_strings_translation):
                self.cache.orig_to_translation[k] = v

            # generate results based on cache
            for k in input_strings:
                all_output_strings.append(self.cache.orig_to_translation[k])

        self.write_cache()
        return all_output_strings

    def _translate_all(self, input_strings: List[str]) -> List[str]:
        """The actual translation logic"""
        raise NotImplementedError


class OfflineTranslator(Translator):
    """
    Offline 'translator' based on stanza, jamdict (dictionary) and jaconv (kana romanization)

    Results are pretty bad, but you don't need cloud API to use it.

    To use this class, make sure to:
      - pip install stanza jamdict jaconv
      - run `stanza.download('ja')` in Python console once, to download the resources for Stanza

    """
    CACHE_NAME = "pyTranslateSwf-cache-OfflineTranslator.json"
    BATCH_SIZE = 100

    def __init__(self):
        super().__init__()

        # stanza.download('ja')
        self.nlp = stanza.Pipeline('ja')
        self.jmd = Jamdict()

        self._translate_jmd_cache = {}

    def _translate_all(self, input_strings: List[str]) -> List[str]:
        return [self._translate(s) for s in input_strings]

    def _translate(self, string: str) -> str:
        """The actual translation logic"""
        if not string or string.isspace():
            return ""

        doc = self.nlp(string)  # run annotation over a sentence
        input_tokens = []
        output_tokens = []

        for sentence in doc.to_dict():
            for d in sentence:
                token = d["text"]
                input_tokens.append(token)
                if d["upos"] in ("NOUN", "VERB"):
                    x = self._translate_jmd(token)
                else:
                    x = self._transliterate(token).upper()
                output_tokens.append(x)

        return " ".join(output_tokens).replace("( ", "(").replace(" )", ")").replace(" .", ".")

    def _translate_jmd(self, token: str) -> str:
        if token in self._translate_jmd_cache:
            return self._translate_jmd_cache[token]

        result = self.jmd.lookup(token)

        # get first dictionary meaning
        try:
            meaning = result.entries[0].senses[0].text()
            meaning = meaning.split("/")[0]
            meaning = re.sub(r",.*|to |\(.+\)", "", meaning)
            output = self._translate_jmd_cache[token] = meaning.strip()
            return output
        except Exception:
            pass

        # get first radical meaning
        try:
            meaning = result.chars[0].meanings()[0]
            meaning = meaning.split("/")[0]
            meaning = re.sub(r",.*|to |\(.+\)", "", meaning)
            output = self._translate_jmd_cache[token] = meaning.strip()
            return output
        except Exception:
            pass

        output = self._translate_jmd_cache[token] = self._transliterate(token).upper()
        return output

    @staticmethod
    def _transliterate(token: str) -> str:
        s = jaconv.kata2hira(token)
        s = jaconv.kana2alphabet(s)
        return s


class MicrosoftAzureTranslator(Translator):
    """
    Online translation using Microsoft Azure Cognitive Services v3.0 API

    """
    CACHE_NAME = "pyTranslateSwf-cache-MicrosoftAzureTranslator.json"
    BATCH_SIZE = 100
    DEFAULT_ENDPOINT_URL = "https://api.cognitive.microsofttranslator.com"

    def __init__(self,
                 subscription_key: str,
                 endpoint_url: str=DEFAULT_ENDPOINT_URL,
                 subscription_region: str=None):
        super().__init__()

        if subscription_key is None:
            raise ValueError("You must provide Microsoft Azure subscription key")

        self.url = endpoint_url + "/translate?api-version=3.0&from=ja&to=en"
        self.headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        if subscription_region:
            self.headers["Ocp-Apim-Subscription-Region"] = subscription_region

    def _translate_all(self, input_strings: List[str]) -> List[str]:
        if not input_strings:
            return []

        body = [{"text": input_string} for input_string in input_strings]

        request = requests.post(self.url, headers=self.headers, json=body)
        request.raise_for_status()
        response = request.json()

        output_strings = []

        for d in response:
            try:
                output_string = d["translations"][0]["text"]
                output_strings.append(output_string)
            except Exception:
                output_strings.append("[UNTRANSLATED]")
                print("Error - something got wrong when parsing Microsoft Azure JSON response")

        if len(output_strings) != len(input_strings):
            raise ValueError("String count mismatch from Microsoft Azure JSON response")

        return output_strings
