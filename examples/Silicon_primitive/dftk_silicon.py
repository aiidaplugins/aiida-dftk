# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.plugins import CalculationFactory

DFTKCalculation = CalculationFactory('dftk')

# Setup the code (assuming 'dftk@localhost' exists)
# change the label to whatever you've set up
code = orm.load_code('DFTKdebug@local_direct')

# load silicon structure
cif = orm.CifData(file='/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida-dftk/examples/Silicon_primitive/Si.cif')
structure = cif.get_structure()

# load parameters
parameters = orm.Dict({
    'model_kwargs': {
        'xc': [':gga_x_pbe', ':gga_c_pbe'],
        'temperature': 0.001,  # Electronic temperature in Hartree
        'smearing': {
            '$symbol': 'Smearing.Gaussian'  # Type of smearing
        }
    },
    'basis_kwargs': {
        'Ecut': 6
    },
    'scf': {
        '$function': 'self_consistent_field',
        'checkpointfile': 'scfres.jld2',
        '$kwargs': {
            'is_converged': {
                '$symbol': 'ScfConvergenceEnergy',
                '$args': 1.0e-2
            },
            'maxiter': 100
        }
    },
    'postscf': [
        # {
        #     "$function": "compute_forces_cart"
        # },
        # {
        #     "$function": "compute_stresses_cart"
        # }
    ]
})

# set kpoints
kpoints = orm.KpointsData()
# must be set for inspect_process to work
kpoints.set_cell_from_structure(structure)
kpoints.set_kpoints_mesh([2, 2, 2])

# set pseudos
ppf = load_group('PseudoDojo/0.5/PBE/SR/standard/upf')
pseudos = ppf.get_pseudos(structure=structure)

parameters_dict = {
    'code': code,
    'structure': structure,
    'pseudos': pseudos,
    'pseudo_rcut': orm.Float(10.0),
    'kpoints': kpoints,
    'parameters': parameters,
    'metadata': {
        'options': {
            'withmpi': False,
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1,
            }
        }
    }
}

# Run the calculation
result = engine.submit(DFTKCalculation, **parameters_dict)
