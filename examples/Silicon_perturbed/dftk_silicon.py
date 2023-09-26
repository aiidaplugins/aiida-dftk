# -*- coding: utf-8 -*-
from aiida import engine, orm
from aiida.plugins import CalculationFactory

DFTKCalculation = CalculationFactory('dftk')

# Setup the code (assuming 'dftk@localhost' exists)
code = orm.load_code('DFTK@local_direct')  # change the label to whatever you've set up

# Setup the builder
builder = DFTKCalculation.get_builder()
#load silicon structure
cif = orm.CifData(file='/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida_dftk/examples/Silicon_perturbed/Si.cif')
structure = cif.get_structure()
builder.structure = structure

#load parameters
Parameters = orm.Dict({
    'model_kwargs': {
        'xc': [':gga_x_pbe', ':gga_c_pbe']
    },
    'basis_kwargs': {
        'Ecut': 20
    },
    'scf': {
        '$function': 'self_consistent_field',
        'checkpointfile': 'scfres.jld2',
        '$kwargs': {
            'is_converged': {
                '$symbol': 'ScfConvergenceEnergy',
                '$args': 1.0e-6
            },
            'maxiter': 100
        }
    },
    'postscf': [{
        '$function': 'compute_forces_cart'
    }, {
        '$function': 'compute_stresses_cart'
    }]
})
builder.parameters = Parameters

#set kpoints
kpoints = orm.KpointsData()
kpoints.set_kpoints_mesh([4, 4, 4])
builder.kpoints = kpoints

#set pseudos
ppf = load_group('PseudoDojo/0.4/PBE/SR/standard/upf')
Pseudos = ppf.get_pseudos(structure=structure)
builder.pseudos = Pseudos

# Set the options
builder.metadata.options.withmpi = True
builder.metadata.options.resources = {
    'num_machines': 1,
    'num_mpiprocs_per_machine': 2,
}

builder.code = code

# Run the calculation
result = engine.run(builder)
