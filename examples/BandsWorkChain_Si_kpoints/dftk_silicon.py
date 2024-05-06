# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.plugins import CalculationFactory

from aiida_dftk.workflows.bands import DftkBandsWorkChain

# Setup the code (assuming 'dftk@localhost' exists)
code = orm.load_code('DFTK_mpi@local_slurm')  # change the label to whatever you've set up

#load silicon structure
cif = orm.CifData(
    file='/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida-dftk/examples/BandsWorkChain_Si_kpoints/Si.cif'
)
structure = cif.get_structure()

#load parameters
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
                '$symbol': 'ScfConvergenceEnergy',
                '$args': 1.0e-8
            },
            'maxiter': 1
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
                ]
            ]
        }
    }, {
        '$function': 'compute_forces_cart'
    }, {
        '$function': 'compute_stresses_cart'
    }]
})

#set pseudos
ppf = load_group('PseudoDojo/0.4/PBE/SR/standard/upf')
pseudos = ppf.get_pseudos(structure=structure)

base_parameters = {
    'kpoints_distance': orm.Float(1),
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
                }
            }
        }
    }
}

bands_parameters = {
    'bands_kpoints_distance': orm.Float(2),
    'dftk_base': base_parameters
}

# Run the calculation
result = engine.submit(DftkBandsWorkChain, **bands_parameters)
