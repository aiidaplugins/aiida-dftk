from aiida import engine, orm
from aiida.plugins import CalculationFactory
from aiida_dftk.workflows import DftkBaseWorkChain


# Setup the code (assuming 'dftk@localhost' exists)
code = orm.load_code('DFTK@local_direct')  # change the label to whatever you've set up

#load silicon structure
cif = orm.CifData(file="/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida_dftk/examples/WorkChain_Si_kpoints_distance/Si.cif")
structure = cif.get_structure()

#load parameters
parameters = orm.Dict({
    "model_kwargs": {
        "xc": [
            ":gga_x_pbe",
            ":gga_c_pbe"
        ]
    },
    "basis_kwargs": {
        "Ecut": 6
    },
    "scf": {
        "$function": "self_consistent_field",
        "checkpointfile": "scfres.jld2",
        "$kwargs": {
            "is_converged": {
                 "$symbol": "ScfConvergenceEnergy",
                 "$args": 1.0e-2
            },
            "maxiter": 100
        }
    },
    "postscf": [
        {
            "$function": "compute_forces_cart"
        },
        {
            "$function": "compute_stresses_cart"
        }
    ]
})

#set pseudos
ppf = load_group("PseudoDojo/0.4/PBE/SR/standard/upf")
pseudos = ppf.get_pseudos(structure=structure)


base_parameters_dict = {
        'kpoints_distance': orm.Float(1),
        'dftk': {
            'code': code,
            'structure': structure,
            'pseudos': pseudos,
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
    }





# Run the calculation
result = engine.run(DftkBaseWorkChain, **base_parameters_dict)

