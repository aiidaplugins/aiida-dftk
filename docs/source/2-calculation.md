# 2. Running an example DFTK Calculation on Silicon using AiiDA

This tutorial provides an example to run a DFTK calculation on a
silicon crystal using AiiDA.

Before proceeding, make sure you've completed
the [development environment setup tutorial](1-setup.md).
This will ensure that you have both the Julia and Python sides
ready for DFTK calculations through AiiDA.
In this example we will assume you have set up the DFTK code
under the label `DFTK@jed`.

The calculation is based on a silicon CIF file,
which you can download at
[Si.cif](https://github.com/aiidaplugins/aiida-dftk/raw/b59e9b9395366002c8591776ad293275952c0001/examples/Silicon/Si.cif).

## Single calculation python script
The following script runs a DFTK calculation using the basic DFTK workchain:

```python
import aiida
import os.path
from aiida import engine, orm
from aiida_dftk.workflows.base import DftkBaseWorkChain

# Load the default Aiida profile
aiida.load_profile()

# Get builder for setting up the workchain
builder = DftkBaseWorkChain.get_builder()

# Attach code to run calculation:
# Note: Change the label here to whatever you have set it up as.
builder.dftk.code = orm.load_code('DFTK')

# Attach the structure from the CIF file
file = os.path.abspath("Si.cif")
structure = orm.CifData(file=file).get_structure()
builder.dftk.structure = structure

# Specify the k-point mesh
kpoints = orm.KpointsData()
kpoints.set_kpoints_mesh([4, 4, 4])
builder.kpoints = kpoints

# Specify pseudopotentials
ppf = orm.load_group("PseudoDojo/0.5/PBE/SR/standard/upf")
builder.dftk.pseudos = ppf.get_pseudos(structure=structure)

# Setup some DFTK-specific parameters (all units in Hartree / atomic units)
# See some explanation below.
builder.dftk.parameters = orm.Dict({
    "model_kwargs": {
        "xc": [":gga_x_pbe", ":gga_c_pbe"],  # Exchange-correlation functional
        "temperature": 0.001,                # Electronic temperature
        "smearing": {
            "$symbol": "Smearing.Gaussian"   # Type of smearing
        }
    },
    "basis_kwargs": {
        "Ecut": 20  # Plane-wave cutoff energy
    },
    "scf": {
        "$function": "self_consistent_field",  # Single-point SCF
        "checkpointfile": "scfres.jld2",  # Checkpoint and output file
        "$kwargs": {
            "tol": 1e-6,    # Convergence tolerance
            "maxiter": 100  # Maximum SCF iterations
        }
    },
    "postscf": [
        {
            "$function": "compute_forces_cart"  # Compute Cartesian forces
        },
    ]
})

# Set options to use 1 process only
builder.dftk.metadata.options.withmpi = False
builder.dftk.metadata.options.resources = {'num_machines': 1, 'num_mpiprocs_per_machine': 1}

# Finally we run the calculation
result = engine.run(builder)
```
Note that the parameters specified above as an `orm.Dict` are thin
wrappers around the arguments and keyword arguments of appropriate
Julia functions in DFTK.
See the [`AiidaDFTK` documentation](https://mfherbst.github.io/AiidaDFTK.jl/stable/input_output/)
as well as the [DFTK documentation](https://docs.dftk.org) for details.

---

Instead of using the DFTK workchain (which automatically restarts and reschedules
calculations) you can also run a single calculation only. THis is done by running
DFTK `CalcJob`, which is done using the builder
```python
from aiida.plugins import CalculationFactory
builder = CalculationFactory('dftk').get_builder()
```
and replacing all `builder.dftk.<x.y.z>` parts in the above script by simply
a `builder.<x.y.z>` prefix.

---

## Visualizing the Provenance Graph

After execution, first find the PK of the calculation:
```bash
verdi process list -a
```

Then generate a provenance graph for the calculation
with the following command:

```bash
verdi node graph generate [PK from above]
```
