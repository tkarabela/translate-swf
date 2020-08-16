#!/usr/bin/env python3
import pyTranslateSwf
import sys


def main():
    cli = pyTranslateSwf.PyTranslateSwfCLI()
    return cli.run(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
