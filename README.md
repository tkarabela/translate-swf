# pyTranslateSwf

*Japanese-to-English translation tool for SWF (Adobe Flash) files*

This Python tool can be used to extract strings from SWF assets for translation,
do the translation itself (cloud-based or offline), and write translated strings
back to the assets. You will also need the open-source [JPEXS Flash Decompiler] to move
assets in and out of the SWF file. 

pyTranslateSwf is licensed under the MIT license (see `LICENSE.txt`).

## Installation

You will need Python 3.6+ and the following libraries:

...if you wish to use Microsoft Azure translation service (recommended):

```sh
pip install regex uuid requests
```

...if you wish to use the provided offline translator:

```sh
pip install regex jamdict stanza
```

## Quickstart

We will be using the [JPEXS Flash Decompiler] and `translateSfw.py` script to interact with the library.
You can use `-h` to get help: `translateSfw.py -h` or `translateSfw.py translate -h`.

### 1) Export assets from SWF file

* Download the [JPEXS Flash Decompiler] and open your SWF file in the GUI.
* In the asset tree, select the `texts` and `scripts` folders and click the `Export Selection`
  button in the ribbon above. Make sure to export text as "Plain Text" and scripts as "ActionScript".
* Save the assets into a directory (this will be your working directory, it should now have
  `texts` and `scripts` subdirectories).

### 2) Gather strings for translation

In your working directory, run the following:

```sh
translateSfw.py gather
```

This will generate a JSON file with all the (unique) extracted strings, ready for
translation. *Note that this is unlikely to extract 100% of the texts, notably texts saved as bitmap/vector graphics
and any string literals in ActionScript which the heuristic missed.* 

### 3) Run machine translation (optional)

If you are using Microsoft Azure (recommended), run the following:

```sh
translateSfw.py translate azure --azure-subscription-key <YOUR-KEY> --azure-subscription-region <YOUR-REGION>
```

You can also use the offline translation backend (which will generate much lower quality text):

```sh
translateSfw.py translate offline
```

### 4) Export translated strings back into assets

In your working directory, run the following:

```sh
translateSfw.py export
```

This will modify the assets with the new strings. *Do not run `gather` or `export` again after doing this,
as the script would get confused by the new strings in assets. If you wish to do something
differently, delete the assets and start again by export them (see Step 1).*

### 5) Import new assets and generate SWF file

* Assuming you still have [JPEXS Flash Decompiler] window open with your original SWF loaded,
  click the `Import Text` and `Import Scripts` buttons in the ribbon above to load your modified assets
  from the working directory.
* When this is done, click `Save As...` in the ribbon and generate your translated SWF file.

## Translation backends

Currently, there are two available backends for machine translation:
[Microsoft Azure Cognitive Services Translator] (cloud-based, "proper" machine translation)
and custom offline solution (dictionary-based, marginally usable). It's recommended
to use Microsoft Azure if possible - you will need a subscription key to do that.

Input text | Translation (Microsoft Azure) | Translation (offline translator)
------------ | ------------- | -------------
こんにちは世界 | Hello world | KONNICHI HA the world

Additionally, you can skip the machine translation step and translate the
extracted strings yourself. They are stored as JSON.

## Diving into the library

The `Translator` subclasses are used as follows:

```py
from pyTranslateSwf import OfflineTranslator, MicrosoftAzureTranslator

translator = OfflineTranslator()
input_strings = ["こんにちは世界"]
output_strings = translator.translate_all(input_strings)
print(output_strings[0])
```

The `Parser` subclasses are used as follows:

```py
from pyTranslateSwf import JPEXSActionScriptParser, JPEXSPlainTextParser

parser = JPEXSActionScriptParser("./scripts/test.as")
input_strings = parser.get_extracted_strings()
output_strings = [my_translate_function(s) for s in input_strings]
parser.replace_strings(output_strings)
parser.save()
```

Refer to module and class docstrings for more info.

[JPEXS Flash Decompiler]: https://github.com/jindrapetrik/jpexs-decompiler
[Microsoft Azure Cognitive Services Translator]: https://azure.microsoft.com/en-us/services/cognitive-services/translator/
