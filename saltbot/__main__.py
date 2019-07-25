#! /usr/bin/env python3.7

try:
    from . import saltbot
except ImportError:
    import saltbot
import sys


if __name__ == "__main__":
    saltbot.main(saltbot.parse_args(sys.argv[1:]))
