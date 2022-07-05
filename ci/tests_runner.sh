#!/bin/bash

mkdir public

# run tests
coverage run manage.py test --exclude-tag=future

# badge result
result=$?
if [ $result = 1 ]
then
  value="failing"
  color="red"
else
  value="passed"
  color="green"
fi

# badge generation
anybadge --value=$value --file=public/tests.svg --label="tests" --color=$color

# coverage reporting
coverage report --omit="manage.py,main/migrations/*"
coverage html --omit="manage.py,main/migrations/*"

# exitcode
if [ $result = 0 ]
then
  exit 0
else
  exit 1
fi
