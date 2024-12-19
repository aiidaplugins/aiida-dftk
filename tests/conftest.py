import logging
from pathlib import Path
import pytest

import aiida_dftk.calculations

pytest_plugins = 'aiida.manage.tests.pytest_fixtures'

_LOGGER = logging.getLogger(__name__)
_julia_project_path = Path(__file__).parent /  "julia_environment"


def pytest_sessionstart():
    """Instantiates the test Julia environment before any test runs."""
    import subprocess

    with open(_julia_project_path / "Project.toml", "w") as f:
        f.write(f"""
[deps]
AiidaDFTK = "26386dbc-b74b-4d9a-b75a-41d28ada84fc"

[compat]
AiidaDFTK = "{aiida_dftk.calculations._AIIDA_DFTK_VERSION_SPEC}"
""")

    # Pkg.Registry.add() seems necessary for GitHub Actions
    subprocess.run(['julia', f'--project={_julia_project_path}', '-e', 'using Pkg; Pkg.Registry.add(); Pkg.resolve();'], check=True)


@pytest.fixture
def get_dftk_code(aiida_local_code_factory):
    """Return an ``InstalledCode`` instance configured to run DFTK calculations on localhost."""

    def _get_code():
        return aiida_local_code_factory(
            'dftk',
            'julia',
            label='dftk',
            prepend_text=f"""\
                export JULIA_PROJECT="{_julia_project_path}"
            """,
        )

    return _get_code

@pytest.fixture
def generate_structure():
    """Return a ``StructureData`` representing either bulk silicon or a water molecule."""

    def _generate_structure(structure_id='silicon'):
        """Return a ``StructureData`` representing bulk silicon or a snapshot of a single water molecule dynamics.
        :param structure_id: identifies the ``StructureData`` you want to generate. Either 'silicon' or 'water'.
        """
        from aiida.orm import StructureData

        if structure_id == 'silicon':
            param = 5.43
            cell = [[param / 2., param / 2., 0], [param / 2., 0, param / 2.], [0, param / 2., param / 2.]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
            structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='Si', name='Si')
        elif structure_id == 'silicon_perturbed':
            param = 5.43
            cell = [[param / 2., param / 2., 0], [param / 2., 0, param / 2.], [0, param / 2., param / 2.]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0.05, 0., 0.), symbols='Si', name='Si')
            structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='Si', name='Si')
        elif structure_id == 'water':
            structure = StructureData(cell=[[5.29177209, 0., 0.], [0., 5.29177209, 0.], [0., 0., 5.29177209]])
            structure.append_atom(position=[12.73464656, 16.7741411, 24.35076238], symbols='H', name='H')
            structure.append_atom(position=[-29.3865565, 9.51707929, -4.02515904], symbols='H', name='H')
            structure.append_atom(position=[1.04074437, -1.64320127, -1.27035021], symbols='O', name='O')
        elif structure_id == 'uranium':
            param = 5.43
            cell = [[param / 2., param / 2., 0], [param / 2., 0, param / 2.], [0, param / 2., param / 2.]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0., 0., 0.), symbols='U', name='U')
            structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='U', name='U')
        else:
            raise KeyError(f'Unknown structure_id="{structure_id}"')
        return structure

    return _generate_structure


@pytest.fixture
def generate_kpoints_mesh():
    """Return a `KpointsData` node."""

    def _generate_kpoints_mesh(npoints):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.orm import KpointsData

        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([npoints] * 3)

        return kpoints

    return _generate_kpoints_mesh

# TODO: It would be nicer to automatically download the psp through aiida-pseudo
@pytest.fixture
def load_psp():
    """Return the pd_nc_sr_pbe_standard_0.4.1_upf pseudopotential for an element"""

    def _load_psp(element: str):
        from aiida import plugins
        from pathlib import Path

        if element != "Si":
            raise ValueError("Only the Si psp is available for the moment.")

        UpfData = plugins.DataFactory('pseudo.upf')
        with open((Path(__file__) / ".." / "pseudos" / (element + ".upf")).resolve(), "rb") as stream:
            return UpfData(stream)

    return _load_psp


# TODO: Something like this should exist in aiida! We shouldn't have to do it ourselves just to capture why the test failed.
@pytest.fixture
def submit_and_await_success(submit_and_await):
    """
    Submits a process or process builder to the engine.
    Validates that the process succeeds, or logs a report if it doesn't.
    """

    def _submit_and_await_success(*args, **kwargs):
        from aiida.cmdline.utils.common import get_calcjob_report, get_workchain_report
        from aiida.orm.nodes.process import CalcJobNode, WorkChainNode

        result = submit_and_await(*args, **kwargs)

        if result.exit_status != 0:
            if isinstance(result, CalcJobNode):
                _LOGGER.warning("Report of CalcJobNode:")
                _LOGGER.warning(get_calcjob_report(result))
            elif isinstance(result, WorkChainNode):
                _LOGGER.warning("Report of WorkChainNode:")
                _LOGGER.warning(get_workchain_report(result, "REPORT"))

                # Also log reports of all child calcjobs:
                for link in result.base.links.get_outgoing(CalcJobNode):
                    if isinstance(link.node, CalcJobNode):
                        _LOGGER.warning("Report of child CalcJobNode:")
                        _LOGGER.warning(get_calcjob_report(link.node))

            assert result.exit_status == 0

        return result

    return _submit_and_await_success
