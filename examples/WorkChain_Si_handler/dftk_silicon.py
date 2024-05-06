# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.plugins import CalculationFactory

from aiida_dftk.workflows.base import DftkBaseWorkChain

# Setup the code (assuming 'dftk@localhost' exists)
# change the label to whatever you've set up
code = orm.load_code('DFTK_mpi@local_slurm')

# load silicon structure
cif = orm.CifData(
    file='/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida-dftk/examples/Silicon_primitive/Si.cif')
structure = cif.get_structure()


# load parameters
parameters = orm.Dict({
    'model_kwargs': {
        'xc': [':gga_x_pbe', ':gga_c_pbe']
    },
    'basis_kwargs': {
        'Ecut': 12
    },
    'scf': {
        '$function': 'self_consistent_field',
        'checkpointfile': 'scfres.jld2',
        '$kwargs': {
            'is_converged': {
                '$symbol': 'ScfConvergenceDensity',
                '$args': 1.0e-8
            },
            'maxiter': 1  # for testing the scf_convergence_not_reached exit code
        }
    },
    'postscf': [{
        "$function": "compute_bands",
        "$kwargs": {
            "kpath": [
                [
                    0.0,
                    0.0,
                    0.0
                ],
                [
                    0.1,
                    0.0,
                    0.1
                ],
                [
                    0.2,
                    0.0,
                    0.2
                ],
                [
                    0.3,
                    0.0,
                    0.3
                ],
                [
                    0.4,
                    0.0,
                    0.4
                ],
                [
                    0.5,
                    0.0,
                    0.5
                ],
                [
                    0.5,
                    0.0,
                    0.5
                ],
                [
                    0.525,
                    0.05,
                    0.525
                ],
                [
                    0.55,
                    0.1,
                    0.55
                ],
                [
                    0.575,
                    0.15,
                    0.575
                ],
                [
                    0.6,
                    0.2,
                    0.6
                ],
                [
                    0.625,
                    0.25,
                    0.625
                ]
            ]
        }
    },{
        "$function": "compute_forces_cart"
    },{
        "$function": "compute_stresses_cart"
    }
    ]
})

# set kpoints
kpoints = orm.KpointsData()
# must be set for inspect_process to work
kpoints.set_cell_from_structure(structure)
kpoints.set_kpoints_mesh([6, 6, 6])

# set pseudos
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
