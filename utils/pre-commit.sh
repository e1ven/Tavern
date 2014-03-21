#!/bin/bash
echo "Checking Code before checkin. To skip use git commit --no-verify"

source tmp/env/bin/activate
echo "Validating code for project specific gotchas.."
# Run our manual validations.
./utils/validate.sh
if [ "$?" -ne 0 ]
    then
    echo "Aborting due to code issue."
    stop 2
fi

echo "Checking Code against Python standards.."
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
sphinx-apidoc -f -H Tavern -T -o docs/documentation_sources/ .
sphinx-build -b html -d docs/documentation_sources/_build/doctree docs/documentation_sources/ docs/html
sphinx-build -b text -d docs/documentation_sources/_build/doctree docs/documentation_sources/ docs/text

echo "Adding docs to git"
find docs/ -exec git add {} \; > /dev/null 2>&1

echo "Ignoring the following files-"
git ls-files . --exclude-standard --other