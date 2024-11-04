# 3. Running a DFTK Calculation for MoS2 using AiiDA Common Workflow

## Step 1: Installing aiida-common-workflows for DFTK
First, you'll need to install the `aiida-common-workflows` plugin that supports DFTK,
for which a local fork of the common workflows is needed:
```bash
git clone https://github.com/WuyihanVictor/aiida-common-workflows.git
cd aiida-common-workflows
git checkout dftk_implementation
pip install -e .
```

**Note**: This plugin is compatible with AiiDA v2.0+
and currently supports Quantum Espresso and DFTK.

---

## Step 2: Modifying the Protocol Configuration

Next, you'll need to modify the `protocol.yml` file to specify the DFTK-related
settings. The `protocol.yml` contains various protocol configurations like
'fast', 'moderate', 'precise', etc. Each protocol contains a `base` section
that outlines parameters for the `DFTKBaseWorkChain`.

Here's an example snippet from `protocol.yml`:

```yaml
fast:
    name: "fast"
    description: "fast protocol for testing purposes"
    pseudo_family: "PseudoDojo/0.4/PBE/SR/standard/upf"
    cutoff_stringency: "low"
    base:
        kpoints_distance: 1  # [1/AA]
        dftk:
            parameters:
                model_kwargs:
                    functionals: [":gga_x_pbe", ":gga_c_pbe"]
                    smearing:
                        $symbol: "Smearing.FermiDirac"
                    temperature: 0.00225  # Ha
                scf:
                    $kwargs:
                        maxiter: 100
                        is_converged:
                            $args: 1.0e-4
                            $symbol: "ScfConvergenceDensity"
                    $function: "self_consistent_field"
                    checkpointfile: "scfres.jld2"
                postscf:
                  - $function: "compute_forces_cart"
                  - $function: "compute_stresses_cart"
```

> **Note**: The `base` section in each protocol contains the parameters for `DFTKBaseWorkChain`.

---

## Step 3: Setting Up the Structure

Load the MoS2 structure from a CIF file.

```python
from aiida import orm

cif = orm.CifData(file="/path/to/your/MoS2.cif")
structure = cif.get_structure()
```

---

## Step 4: Using the Common Workflow

Load the DFTK code and the common workflow.

```python
from aiida import orm
from aiida.plugins import WorkflowFactory
from aiida_common_workflows.common import ElectronicType

code = orm.load_code('DFTK@local_direct')
RelaxWorkChain = WorkflowFactory('common_workflows.relax.dftk')
```

### Note on electronic_type

The `electronic_type` option can take the following values:
- `AUTOMATIC`: Follow the protocol or `UNKOWN` type.
- `INSULATOR`: Fixed occupation numbers.
- `METAL`: Uses cold smearing.
- `UNKNOWN`: Uses Gaussian smearing.

By default, the `electronic_type` is set to `METAL`.

---

## Step 5: Running the Calculation

Finally, run the DFTK calculation.

```python
builder = RelaxWorkChain.get_input_generator().get_builder(
    structure=structure,
    engines=engines,
    protocol='fastest',
    electronic_type=ElectronicType.METAL)
result = engine.run(builder)
```

Here, `protocol='fastest'` specifies the protocol to use,
and `electronic_type=ElectronicType.METAL` sets the electronic type.
