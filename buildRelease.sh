#!/bin/bash
rm release/*
(cd ../../; python2 ./generator.pyc hs_tibber utf-8)
markdown2 --extras tables,fenced-code-blocks,strike,target-blank-links doc/log14464.md > release/log14464.html
(cd release; zip -r 14464_hs_tibber.hslz *)
