"""
pyTranslateSwf.corpus module
============================

ParallelCorpus is a helper class to store (original, translated) string pairs.
It is just a glorified cache; anything resembling NLP is done in pyTranslateSwf.translators.

"""


import json
from typing import Dict


class ParallelCorpus:
    """Helper class to store (original, translated) string pairs"""
    def __init__(self):
        self.orig_to_translation: Dict[str, str] = {}

    def to_dict(self):
        serialized = {
            "strings": [
                {"orig": orig,
                 "tran": translation}
                for orig, translation in sorted(self.orig_to_translation.items())
            ]
        }

        return serialized

    def to_json(self, path: str):
        serialized = self.to_dict()

        with open(path, "w", encoding="utf-8") as fp:
            json.dump(serialized, fp, ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, serialized: Dict):
        obj = cls()
        for d in serialized["strings"]:
            obj.orig_to_translation[d["orig"]] = d["tran"]

        return obj

    @classmethod
    def from_json(cls, path: str):
        with open(path, encoding="utf-8") as fp:
            serialized = json.load(fp)
            return cls.from_dict(serialized)
