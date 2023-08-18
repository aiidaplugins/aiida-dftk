#!/bin/bash
exec > _scheduler-stdout.txt
exec 2> _scheduler-stderr.txt


#activate the qespresso env with openmpi
ulimit -s unlimited
eval "$(conda shell.bash hook)"
conda activate qespresso

#export the path contains libmpi.so, so that the system knows where to find the MPI libraries
export LD_LIBRARY_PATH=/home/max/.conda/envs/qespresso/lib:$LD_LIBRARY_PATH

#export the project path
export JULIA_PROJECT="/home/max/Desktop/Aiida_DFTK_Test/aiida-dftk/AiidaDFTK.jl"

'mpirun' '-np' '2' "/usr/bin/julia" "-e" "using AiidaDFTK, MPIPreferences; MPIPreferences.use_system_binary(); AiidaDFTK.run()" "DFTK.json"  > 'DFTK.txt' 
