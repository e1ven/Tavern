#!/bin/bash
echo "Checking Code"

source tmp/env/bin/activate
echo "Validating code correctness.."
# Run our manual validations.
./utils/validate.sh
if [ "$?" -ne 0 ]
    then
    echo "Aborting due to code issue."
    stop 2
fi

# Run style tests against the code
for i in `find . -maxdepth 1 -name "*.py"`
do
    if [ $(sinceFileArg $i lastrun_validate_$i) -gt 0 ]
    then
        echo -e "\t $i"
        pep8 --show-source --show-pep8 --ignore=E501,E303 $i
        if [ "$?" -ne 0 ]
        then
            echo "Aborting due to unfixable style issue."
            stop 2
        fi
    fi
    writearg lastrun_validate_$i `date +%s`
done



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