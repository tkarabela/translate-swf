"""
pyTranslateSwf.cli module
=========================

The commandline interface used by the translateSwf.py script.

Run translateSwf.py -h to learn more.

"""

import argparse
from textwrap import dedent
from typing import List
from .parsers import get_parsers_for_directory, JPEXSActionScriptParser
from .corpus import ParallelCorpus
from .translators import OfflineTranslator, MicrosoftAzureTranslator


class PyTranslateSwfCLI:
    SUBPARSER_DEST = "command"

    COMMAND_GATHER = "gather"
    COMMAND_TRANSLATE = "translate"
    COMMAND_EXPORT = "export"

    GATHERED_JSON_FILENAME = "pyTranslateSwf-all-strings.json"

    TRANSLATION_PROVIDER_OFFLINE = "offline"
    TRANSLATION_PROVIDER_AZURE = "azure"
    OPTIONS_TRANSLATION_PROVIDER = (
        TRANSLATION_PROVIDER_OFFLINE,
        TRANSLATION_PROVIDER_AZURE
    )

    def __init__(self):
        self.parser = parser = argparse.ArgumentParser(description=dedent(self.run.__doc__),
                                                       formatter_class=argparse.RawDescriptionHelpFormatter)
        subparsers = parser.add_subparsers(dest=self.SUBPARSER_DEST)

        subparser_gather = subparsers.add_parser(self.COMMAND_GATHER, description=self.run_gather.__doc__)
        subparser_gather.add_argument("--mode",
                                      choices=JPEXSActionScriptParser.MODES,
                                      default=JPEXSActionScriptParser.MODE_HEURISTIC,
                                      help="ActionScript string literal filtering method"
                                           " (default: 'heuristic')")

        subparser_translate = subparsers.add_parser(self.COMMAND_TRANSLATE, description=self.run_translate.__doc__)
        subparser_translate.add_argument("provider",
                                         choices=self.OPTIONS_TRANSLATION_PROVIDER,
                                         help="translation service to use: either Microsoft Azure (recommended)"
                                              " or offline")
        subparser_translate.add_argument("--azure-subscription-key",
                                         help="Microsoft Azure translation subscription key")
        subparser_translate.add_argument("--azure-endpoint-url",
                                         default=MicrosoftAzureTranslator.DEFAULT_ENDPOINT_URL,
                                         help=f"Microsoft Azure endpoint URL (default:"
                                              f" {MicrosoftAzureTranslator.DEFAULT_ENDPOINT_URL})")
        subparser_translate.add_argument("--azure-subscription-region",
                                         help="Microsoft Azure subscription region (default: none)")

        subparser_export = subparsers.add_parser(self.COMMAND_EXPORT, description=self.run_export.__doc__)
        subparser_export.add_argument("--mode",
                                      choices=JPEXSActionScriptParser.MODES,
                                      default=JPEXSActionScriptParser.MODE_HEURISTIC,
                                      help="ActionScript string literal filtering method"
                                           " (default: 'heuristic') - make sure to use the same mode"
                                           " in `gather` and `export`!")

    def run(self, argv: List[str]) -> int:
        """
        This script does Japanese-to-English translation of assets from SWF (Flash) files
        exported by the JPEXS decompiler. This script is to be run from the directory
        where the assets have been exported (ie. on the same level as the 'texts' and
        'scripts' directories).

        The process has the following steps:

            1. In JPEXS, open your SWF file and use the 'Export Selection' button to export 'texts' and 'scripts'
               into a directory. Be sure to export 'texts' as 'Plain Text' and 'scripts' as 'ActionScript'.

            2. Run `translateSwf.py gather`, this will gather strings to be translated into a single JSON file.

            3. Run `translateSwf.py translate`, this will process the JSON file and produce machine translation
               according to selected method, see `translateSwf.py translate -h`.

               Alternatively, you can also modify the JSON yourself and skip this step.

            4. Run `translateSwf.py export`, this will write new strings from JSON file back into the asset files.

            5. In JPEXS, click the 'Import Text' and 'Import Scripts' buttons to import the modified assets,
               then 'Save As' your modified SWF.

        Note that after running step 4. `translateSwf.py export`, you should not run `gather` or `translate` again,
        since these would get confused by the translated assets. If you want to re-do the translation, delete
        exported assets and start with step 1.

        """
        args = self.parser.parse_args(argv)
        command = getattr(args, self.SUBPARSER_DEST)

        if command == self.COMMAND_GATHER:
            mode = args.mode
            return self.run_gather(mode=mode)
        elif command == self.COMMAND_TRANSLATE:
            provider = args.provider
            azure_subscription_key = args.azure_subscription_key
            azure_endpoint_url = args.azure_endpoint_url
            azure_subscription_region = args.azure_subscription_region
            return self.run_translate(provider=provider,
                                      azure_subscription_key=azure_subscription_key,
                                      azure_endpoint_url=azure_endpoint_url,
                                      azure_subscription_region=azure_subscription_region)
        elif command == self.COMMAND_EXPORT:
            mode = args.mode
            return self.run_export(mode=mode)
        else:
            raise NotImplementedError

    def run_gather(self, mode: str) -> int:
        """Export translatable strings from JPEXS exported assets (texts, ActionScript) into a single JSON file"""
        parsers = get_parsers_for_directory(".", actionscript_mode=mode)

        all_strings = set()

        for parser in parsers:
            strings = parser.get_extracted_strings()
            if strings:
                print(f"{len(strings): 6d} string occurrences in {parser.path}")
            for string in strings:
                all_strings.add(string)

        print(f"\n{len(all_strings): 6d} unique strings extracted in total ({sum(map(len, all_strings))} chars)")

        corpus = ParallelCorpus()
        corpus.orig_to_translation = {string: string for string in all_strings}
        corpus.to_json(self.GATHERED_JSON_FILENAME)

        print("\nWrote", self.GATHERED_JSON_FILENAME)
        return 0

    def run_translate(self,
                      provider: str,
                      azure_subscription_key,
                      azure_endpoint_url,
                      azure_subscription_region) -> int:
        """Translate strings in JSON file using cloud API (recommended) or offline Python libraries"""
        if provider == self.TRANSLATION_PROVIDER_OFFLINE:
            print("Using OfflineTranslator provider")
            translator = OfflineTranslator()
        elif provider == self.TRANSLATION_PROVIDER_AZURE:
            print("Using MicrosoftAzureTranslator provider")
            translator = MicrosoftAzureTranslator(subscription_key=azure_subscription_key,
                                                  endpoint_url=azure_endpoint_url,
                                                  subscription_region=azure_subscription_region)
        else:
            raise NotImplementedError

        print("Reading JSON corpus from", self.GATHERED_JSON_FILENAME)
        corpus = ParallelCorpus.from_json(self.GATHERED_JSON_FILENAME)
        original_strings = list(corpus.orig_to_translation.keys())

        print("Translating...")
        translated_strings = translator.translate_all(original_strings)

        new_corpus = ParallelCorpus()
        new_corpus.orig_to_translation = dict(zip(original_strings, translated_strings))
        new_corpus.to_json(self.GATHERED_JSON_FILENAME)
        print("Wrote", self.GATHERED_JSON_FILENAME)
        return 0

    def run_export(self, mode: str) -> int:
        """Write translations from JSON file back into exported assets (texts, ActionScript)"""
        print("Reading JSON corpus from", self.GATHERED_JSON_FILENAME)
        corpus = ParallelCorpus.from_json(self.GATHERED_JSON_FILENAME)

        parsers = get_parsers_for_directory(".", actionscript_mode=mode)
        error_count = 0

        for parser in parsers:
            path = parser.path
            original_strings = parser.get_extracted_strings()
            translated_strings = []

            if not original_strings:
                continue

            print("Exporting translation to", path)

            for original_string in original_strings:
                translated_string = corpus.orig_to_translation.get(original_string)
                if translated_string is None:
                    print(f"Warning - missing translation for {original_string!r}")
                    error_count += 1
                    translated_strings.append(original_string)
                else:
                    translated_strings.append(translated_string)

            parser.replace_strings(translated_strings)
            parser.save()

        print(f"\nAll done, there were {error_count} errors.")
        return 0 if error_count == 0 else 1
