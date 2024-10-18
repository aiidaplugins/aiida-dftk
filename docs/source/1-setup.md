# 1. Setting Up the Development Environment for AiidaDFTK Calculations

In this tutorial, we will guide you through setting up a development environment for running [DFTK](https://docs.dftk.org/stable/) calculations using AiiDA. The tutorial is divided into two main sections:
1. **Julia Side**: Creating a Julia project and installing AiidaDFTK.
2. **Python Side**: Setting up aiida-core, installing the aiida-DFTK plugin, defining an AiiDA computer, code, and managing pseudopotentials.

---

## Part 1: Julia Side

### Preliminary: Installing Julia
In this tutorial we will call the computer where you want to run the DFTK
calculations `jed`.
On `jed` first install Julia.
For this [download the Julia binaries](https://julialang.org/downloads/)
and follow the [installation instructions](https://julialang.org/downloads/platform/).
In this tutorial we will assume Julia is available under the path `path/to/julia`.

### Steps to Set Up a Julia Project
1. **Launch a Julia REPL**: E.g. by executing `path/to/julia`.
2. **Activate a New Environment**: In the Julia REPL,
   create a new environment (essentially a new Julia project)
   using the following commands:
   ```julia
   import Pkg
   Pkg.activate("path/to/new/environment")
   ```
   Replace `path/to/new/environment` with the directory where you wish to
   create the new environment. This will generate a folder
   containing `Project.toml` and `Manifest.toml` files.
3. **Install AiidaDFTK**: While still in the Julia REPL,
   initialize the project by adding packages you'll need.
   For this tutorial we will only need `AiidaDFTK`.
    ```julia
    import Pkg
    Pkg.add("AiidaDFTK")
    ```
4. **Optional configuration:** See the details in the [DFTK documentation
   on running DFTK on clusters](https://docs.dftk.org/stable/tricks/compute_clusters/#Setting-up-local-preferences)
   on how
   to set up a `LocalPreferences.toml` file. This file allows to specify
   a cluster-specific configuration for libraries such as BLAS, LAPACK, FFT etc.
   This is optional, but can improve performance.

The new Julia project is now ready and includes `AiidaDFTK` and its dependency `DFTK`.
You can now proceed with DFTK calculations in this isolated environment.

---

## Part 2: Python Side

### Step 1: Setting Up aiida-core
Follow the [official aiida-core setup tutorial](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/get_started.html).
Make sure you have a working `aiida-core` installation.

### Step 2: Installing the aiida-DFTK Plugin
Install the aiida-dftk plugin repository from github and install it locally:
```bash
pip install git+https://github.com/aiidaplugins/aiida-dftk.git
```

### Step 3: Defining an AiiDA Computer
For a detailed guide on defining a new computer in AiiDA,
consult the [official AiiDA tutorial](https://aiida.readthedocs.io/projects/aiida-core/en/latest/howto/run_codes.html).
In this tutorial we will assume the new computer is available under
the name `jed`.

### Step 4: Register DFTK as an Aiida code
DFTK, when run through AiidaDFTK, should be registered as a code in the AiiDA database.
This can be done using:
```bash
verdi code create core.code.installed \
    --label DFTK \
    --description "Julia DFTK" \
    --computer jed \
    --filepath-executable "path/to/julia" \
    --prepend-text 'export JULIA_PROJECT="path/to/new/environment"' \
    --default-calc-job-plugin dftk \
    --append-text '' \
    --no-use-double-quotes
```
The first two flags are description, the third specifies the computer from Step 3,
the fourth and fifth the path to the Julia executable from Part 1
as well as the setup (prepended commands), which needs to be done
to select the correct project folder with `AiidaDFTK` from Part 1.
In this case this consists simply of exporting the environment variable,
which tells Julia, which project folder to use. In some setup additional steps
might be needed here, such as loading modules, which provide Julia or
one of the vendor-specific libraries configured in Part 1, Step 4.
The last three flags select `dftk` as the default input plugin and specify
to use the default values for `append_text` and `use_double_quotes`.

### Step 5: Managing Pseudopotentials
DFTK supports both HGH and UPF pseudopotentials. For realistic calculations,
UPF format is recommended. We suggest using pseudo-dojo, which can be installed
using the aiida-pseudo plugin. Follow this
[detailed tutorial](https://aiida-pseudo.readthedocs.io/en/latest/)
for more information. Here's how to install pseudo-dojo 0.5 PBE pseudopotentials
with scalar relativistic effects in UPF format:
```bash
aiida-pseudo install pseudo-dojo -v 0.5 -x PBE -r SR -f upf
```

---

Congratulations! You've successfully set up your development environment for AiidaDFTK
and are ready to proceed with your calculations.
