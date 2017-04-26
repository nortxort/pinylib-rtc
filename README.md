## Pinylib-RTC

WebRTC module for tinychat chat rooms.

This is the WebRTC version of pinylib. The structure and the coding style is the same as the original pinylib. Since tinychat is still in beta stage, this version should also be seen as a sort of beta version.

It was based on the [POC](https://github.com/notnola/TcRTC) by [notnola](https://github.com/notnola)


## Setting up

Examples shown here, assumes you are using windows.

pinylib-rtc was developed using [python 2.7.10](https://www.python.org/downloads/windows/ "python for windows") so this is the recomended python interpreter. Later versions of python should work to, aslong as they are from the 2.7 family. I have not tested it with python 3, but with a few changes to client.py i think it would be possible.

### Requirements

pinylib-rtc requires 4 libraries that are not part of the standard python library, these being:

* [websocket-client](https://github.com/websocket-client/websocket-client)
* [requests](https://github.com/kennethreitz/requests "requests")
* [colorama](https://github.com/tartley/colorama "Colorama")
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/ "beautifulsoup4")

These can all be installed form a command prompt with pip.

`pip install websocket-client requests colorama beautifulsoup4`


## Run the client

Run the client by typing `python path\to\client.py` in a command prompt.

## Submitting an issue.
Issues posted should be about pinylib-rtc and **only** pinylib-rtc. 

Before submitting an issue, please read through the [issues](https://github.com/nortxort/pinylib-rtc/issues) section, including already closed issues. If you do not find an answer to your issue, then please provide as much info as possible when opening an issue. Possible info could be:

* Python version including subversion.
* Pinylib-rtc version.
* Debug log.
* How to reproduce the issue/error.


## Author
* [nortxort](https://github.com/nortxort)


## License

The MIT License (MIT)

Copyright (c) 2017 Notnola

Copyright (c) 2017 Nortxort

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice
shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Acknowledgments
*Thanks to the following people who in some way or another, has helped with this project*

* [notnola](https://github.com/notnola)


