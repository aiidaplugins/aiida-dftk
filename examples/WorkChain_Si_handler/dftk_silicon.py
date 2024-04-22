# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.plugins import CalculationFactory

from aiida_dftk.workflows.base import DftkBaseWorkChain

# Setup the code (assuming 'dftk@localhost' exists)
code = orm.load_code('DFTK_mpi@local_slurm')  # change the label to whatever you've set up

#load silicon structure
cif = orm.CifData(file='/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida-dftk/examples/Silicon_primitive/Si.cif')
structure = cif.get_structure()


#load parameters
parameters = orm.Dict({
    'model_kwargs': {
        'xc': [':gga_x_pbe', ':gga_c_pbe']
    },
    'basis_kwargs': {
        'Ecut': 6
    },
    'scf': {
        '$function': 'self_consistent_field',
        'checkpointfile': 'scfres.jld2',
        '$kwargs': {
            'is_converged': {
                '$symbol': 'ScfConvergenceDensity',
                '$args': 1.0e-10
            },
            'maxiter': 6  #for testing the scf_convergence_not_reached exit code
        }
    },
    'postscf': [{
        '$function': 'compute_forces_cart'
    }, {
        '$function': 'compute_stresses_cart'
    }]
})

#set kpoints
kpoints = orm.KpointsData()
kpoints.set_cell_from_structure(structure)  #must be set for inspect_process to work
kpoints.set_kpoints_mesh([12, 12, 12])

#set pseudos
ppf = load_group('PseudoDojo/0.4/PBE/SR/standard/upf')
pseudos = ppf.get_pseudos(structure=structure)

#        'kpoints_distance': orm.Float(0.6),  # 1 / Angstrom
base_parameters_dict = {
    'kpoints': kpoints,
    'dftk': {
        'code': code,
        'structure': structure,
        'pseudos': pseudos,
        'parameters': parameters,
        'metadata': {
            'options': {
                'withmpi': True,
                'resources': {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 2,
                },
                'max_wallclock_seconds': 1000
            }
        }
    }
}

# Run the calculation
result = engine.submit(DftkBaseWorkChain, **base_parameters_dict)
