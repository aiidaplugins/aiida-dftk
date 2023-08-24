#!/bin/bash
exec > _scheduler-stdout.txt
exec 2> _scheduler-stderr.txt


#export the project path
export JULIA_PROJECT="/home/max/Desktop/Aiida_DFTK_Test/AiidaDFTK/AiidaDFTK.jl"

"/usr/bin/julia" "-e" "using AiidaDFTK; AiidaDFTK.run()" "DFTK.json"  > 'DFTK.txt' 
