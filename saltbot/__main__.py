'''
Saltbot
---

'''

import os


if __name__ == '__main__':
    print(os.path.abspath(__file__))

    from saltbot.control import main
    main()
