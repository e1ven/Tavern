#!/bin/bash
source tmp/env/bin/activate
echo "Running unit tests"
nosetests --with-doctest --with-coverage --cover-package=libtavern,webtav . tests/libtavern/
if [ "$?" -ne 0 ]
then
    exit 2
fi
echo "Generating docs"
mkdir -p docs/html/
sphinx-apidoc -f -H Tavern -T -o datafiles/documentation-generator/ .
sphinx-build -b html -d datafiles/documentation-generator/_build/doctree datafiles/documentation-generator/ docs/code_documentation/