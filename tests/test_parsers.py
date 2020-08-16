from pyTranslateSwf import JPEXSPlainTextParser, JPEXSActionScriptParser
from io import StringIO


def test_plain_text_parser_1():
    input_string = ""
    input_file = StringIO(input_string)
    parser = JPEXSPlainTextParser(input_file)
    assert parser.get_extracted_strings() == [""]
    parser.replace_strings([""])
    assert parser.data == ""


def test_plain_text_parser_2():
    input_string = """いち"""
    input_file = StringIO(input_string)
    parser = JPEXSPlainTextParser(input_file)
    assert parser.get_extracted_strings() == ["いち"]
    parser.replace_strings(["one"])
    assert parser.data == "one"


def test_plain_text_parser_3():
    input_string = """いち\n--- RECORDSEPARATOR ---\nに"""
    input_file = StringIO(input_string)
    parser = JPEXSPlainTextParser(input_file)
    assert parser.get_extracted_strings() == ["いち", "に"]
    parser.replace_strings(["one", "two"])
    assert parser.data == """one\n--- RECORDSEPARATOR ---\ntwo"""


def test_plain_text_parser_4():
    input_string = """いち\n--- RECORDSEPARATOR ---\nに\n--- RECORDSEPARATOR ---\n\tさん"""
    input_file = StringIO(input_string)
    parser = JPEXSPlainTextParser(input_file)
    assert parser.get_extracted_strings() == ["いち", "に", "\tさん"]
    parser.replace_strings(["one", "two", "three"])
    assert parser.data == """one\n--- RECORDSEPARATOR ---\ntwo\n--- RECORDSEPARATOR ---\nthree"""


ACTIONSCRIPT_INPUT_STRING = """\
package test {
  public dynamic class MyClip extends MovieClip {
    function my_test() : * {
      this.text0 = "";
      this.text1 = "some ascii text";
      this.text2 = "some ascii text with いち some Japanese";
      this.text3 = "<html>simple html</html>";
      this.text4 = "<html>advanced-html-1<font color=\\'#AFFFFFF\\'>advanced-html-2</font>&nbsp;advanced-html-3</html>";
      this.text5 = "いち。"; // short Japanese with punctuation
      this.text6 = "いち"; // short Japanese without punctuation
      this.text7 = "いちにさん一二三"; // long Japanese without punctuation
      this.text8 = "<html>simple html with replacement to be escaped</html>";
    }
  }
}
"""

ACTIONSCRIPT_OUTPUT_STRING_HTML = """\
package test {
  public dynamic class MyClip extends MovieClip {
    function my_test() : * {
      this.text0 = "";
      this.text1 = "some ascii text";
      this.text2 = "some ascii text with いち some Japanese";
      this.text3 = "<html>REPLACE1</html>";
      this.text4 = "<html>REPLACE2<font color=\\'#AFFFFFF\\'>REPLACE3</font>&nbsp;REPLACE4</html>";
      this.text5 = "いち。"; // short Japanese with punctuation
      this.text6 = "いち"; // short Japanese without punctuation
      this.text7 = "いちにさん一二三"; // long Japanese without punctuation
      this.text8 = "<html>REPLACE7'nbsp;</html>";
    }
  }
}
"""

ACTIONSCRIPT_OUTPUT_STRING_HEURISTIC = """\
package test {
  public dynamic class MyClip extends MovieClip {
    function my_test() : * {
      this.text0 = "";
      this.text1 = "some ascii text";
      this.text2 = "some ascii text with いち some Japanese";
      this.text3 = "<html>REPLACE1</html>";
      this.text4 = "<html>REPLACE2<font color=\\'#AFFFFFF\\'>REPLACE3</font>&nbsp;REPLACE4</html>";
      this.text5 = "REPLACE5"; // short Japanese with punctuation
      this.text6 = "いち"; // short Japanese without punctuation
      this.text7 = "REPLACE6"; // long Japanese without punctuation
      this.text8 = "<html>REPLACE7'nbsp;</html>";
    }
  }
}
"""


def test_actionscript_parser_html():
    input_file = StringIO(ACTIONSCRIPT_INPUT_STRING)
    parser = JPEXSActionScriptParser(input_file, mode=JPEXSActionScriptParser.MODE_HTML)
    assert parser.get_extracted_strings() == [
        '',
        'simple html',
        '',
        '',
        'advanced-html-1',
        'advanced-html-2',
        '',
        'advanced-html-3',
        '',
        '',
        'simple html with replacement to be escaped',
        '']
    parser.replace_strings([
        '',
        'REPLACE1',
        '',
        '',
        'REPLACE2',
        'REPLACE3',
        '',
        'REPLACE4',
        '',
        '',
        'REPLACE7"<&nbsp;\n',
        ''])
    assert parser.data == ACTIONSCRIPT_OUTPUT_STRING_HTML


def test_actionscript_parser_heuristic():
    input_file = StringIO(ACTIONSCRIPT_INPUT_STRING)
    parser = JPEXSActionScriptParser(input_file, mode=JPEXSActionScriptParser.MODE_HEURISTIC)
    assert parser.get_extracted_strings() == [
        '',
        'simple html',
        '',
        '',
        'advanced-html-1',
        'advanced-html-2',
        '',
        'advanced-html-3',
        '',
        'いち。',
        'いちにさん一二三',
        '',
        'simple html with replacement to be escaped',
        '']
    parser.replace_strings([
        '',
        'REPLACE1',
        '',
        '',
        'REPLACE2',
        'REPLACE3',
        '',
        'REPLACE4',
        '',
        'REPLACE5',
        'REPLACE6',
        '',
        'REPLACE7"<&nbsp;\n',
        ''])
    assert parser.data == ACTIONSCRIPT_OUTPUT_STRING_HEURISTIC
