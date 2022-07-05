#!/bin/bash

mkdir public

# run pycodestyle
pycodestyle > public/pycodestyle.txt
score=$(wc -l < public/pycodestyle.txt)

# badge color
if [[ $score -ge 50 ]]
then
  color=red
fi

if [[ $score -ge 31 && $score -lt 50 ]]
then
  color=orange
fi

if [[ $score -ge 10 && $score -lt 30 ]]
then
  color=yellow
fi

if [[ $score -lt 10 ]]
then
  color=green
fi

# badge generation
anybadge --value=$score --file=public/pycodestyle.svg --label="pycodestyle errors" --color=$color
echo "Pycodestyle errors count was $score"

if [ $score -lt 9 ]
then
  exit 0
else
  exit 1
fi
