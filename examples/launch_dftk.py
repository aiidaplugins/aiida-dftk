from aiida import engine, orm
from aiida.plugins import CalculationFactory

DFTKCalculation = CalculationFactory('dftk')

# Setup the code (assuming 'dftk@localhost' exists)
code = orm.load_code('mpiDFTKtest@juliaMPI_local_direct')  # change the label to whatever you've set up

# Setup the builder
builder = DFTKCalculation.get_builder()
#load silicon structure
cif = orm.CifData(file="/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida_dftk/examples/Si.cif")
Si = cif.get_structure()
builder.structure = Si

#load parameters
Parameters = orm.Dict({
    "model_kwargs": {
        "xc": [
            ":gga_x_pbe",
            ":gga_c_pbe"
        ],
        "temperature": 0.001,
        "smearing": {
            "$symbol": "Smearing.Gaussian"
        }
    },
    "basis_kwargs": {
        "Ecut": 10
    },
    "scf": {
        "$function": "self_consistent_field",
        "checkpointfile": "scfres.jld2",
        "$kwargs": {
            "mixing": {
                 "$symbol": "KerkerDosMixing"
            },
            "is_converged": {
                 "$symbol": "ScfConvergenceEnergy",
                 "$args": 1.0e-6
            }
        }
    },
    "postscf": [
        {
            "$function": "compute_forces_cart"
        }
    ]
})
builder.parameters = Parameters

#set kpoints
kpoints = orm.KpointsData()
kpoints.set_kpoints_mesh([4, 2, 2],offset=[0.5,0.5,0.5])
builder.kpoints = kpoints

#set pseudos
ppf = load_group("SSSP/1.1/PBE/efficiency")
Pseudos = ppf.get_pseudos(structure=Si)
builder.pseudos = Pseudos

# Set the options
builder.metadata.options.withmpi = True
builder.metadata.options.resources = {
    'num_machines': 2,
    'num_mpiprocs_per_machine': 1,
}

builder.code = code

# Run the calculation
result = engine.run(builder)

