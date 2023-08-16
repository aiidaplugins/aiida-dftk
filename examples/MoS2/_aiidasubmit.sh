#!/bin/bash
exec > _scheduler-stdout.txt
exec 2> _scheduler-stderr.txt


"/home/max/.julia/bin/mpiexecjl" "-np" "2" "/usr/bin/julia" "--project=/home/max/Desktop/Aiida_DFTK_Test/aiida-dftk/AiidaDFTK.jl" "-e" "using AiidaDFTK; AiidaDFTK.run()" "DFTK.json"   
