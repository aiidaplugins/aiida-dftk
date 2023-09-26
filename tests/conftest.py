# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,too-many-statements
"""Initialise a text database and profile for pytest."""
import os

import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='session')
def filepath_tests():
    """Return the absolute filepath of the `tests` folder.
    .. warning:: if this file moves with respect to the `tests` folder, the implementation should change.
    :return: absolute filepath of `tests` folder which is the basepath for all test resources.
    """
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def filepath_fixtures(filepath_tests):
    """Return the absolute filepath to the directory containing the file `fixtures`."""
    return os.path.join(filepath_tests, 'fixtures')


@pytest.fixture(scope='function')
def fixture_sandbox():
    """Return a `SandboxFolder`."""
    from aiida.common.folders import SandboxFolder
    with SandboxFolder() as folder:
        yield folder


@pytest.fixture
def fixture_localhost(aiida_localhost):
    """Return a localhost `Computer`."""
    localhost = aiida_localhost
    localhost.set_default_mpiprocs_per_machine(1)
    return localhost


@pytest.fixture
def fixture_code(fixture_localhost):
    """Return a ``Code`` instance configured to run calculations of given entry point on localhost ``Computer``."""

    def _fixture_code(entry_point_name):
        from aiida.common import exceptions
        from aiida.orm import Code

        label = f'test.{entry_point_name}'

        try:
            return Code.objects.get(label=label)  # pylint: disable=no-member
        except exceptions.NotExistent:
            return Code(
                label=label,
                input_plugin_name=entry_point_name,
                remote_computer_exec=[fixture_localhost, '/bin/true'],
            )

    return _fixture_code


@pytest.fixture
def serialize_builder():
    """Serialize the given process builder into a dictionary with nodes turned into their value representation.
    :param builder: the process builder to serialize
    :return: dictionary
    """

    def serialize_data(data):
        # pylint: disable=too-many-return-statements
        from aiida.orm import BaseType, Code, Dict
        from aiida.plugins import DataFactory

        StructureData = DataFactory('core.structure')
        UpfData = DataFactory('pseudo.upf')

        if isinstance(data, dict):
            return {key: serialize_data(value) for key, value in data.items()}

        if isinstance(data, BaseType):
            return data.value

        if isinstance(data, Code):
            return data.full_label

        if isinstance(data, Dict):
            return data.get_dict()

        if isinstance(data, StructureData):
            return data.get_formula()

        if isinstance(data, UpfData):
            return f'{data.element}<md5={data.md5}>'

        return data

    def _serialize_builder(builder):
        return serialize_data(builder._inputs(prune=True))  # pylint: disable=protected-access

    return _serialize_builder


@pytest.fixture
def generate_calc_job():
    """Fixture to construct a new `CalcJob` instance and call `prepare_for_submission` for testing `CalcJob` classes.
    The fixture will return the `CalcInfo` returned by `prepare_for_submission` and the temporary folder that was passed
    to it, into which the raw input files will have been written.
    """

    def _generate_calc_job(folder, entry_point_name, inputs=None):
        """Fixture to generate a mock `CalcInfo` for testing calculation jobs."""
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import CalculationFactory

        manager = get_manager()
        runner = manager.get_runner()

        process_class = CalculationFactory(entry_point_name)
        process = instantiate_process(runner, process_class, **inputs)

        calc_info = process.prepare_for_submission(folder)

        return calc_info

    return _generate_calc_job


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


@pytest.fixture(scope='session')
def generate_parser():
    """Fixture to load a parser class for testing parsers."""

    def _generate_parser(entry_point_name):
        """Fixture to load a parser class for testing parsers.
        :param entry_point_name: entry point name of the parser class
        :return: the `Parser` sub class
        """
        from aiida.plugins import ParserFactory
        return ParserFactory(entry_point_name)

    return _generate_parser


@pytest.fixture
def generate_remote_data():
    """Return a `RemoteData` node."""

    def _generate_remote_data(computer, remote_path, entry_point_name=None):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.common.links import LinkType
        from aiida.orm import CalcJobNode, RemoteData
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string('aiida.calculations', entry_point_name)

        remote = RemoteData(remote_path=remote_path)
        remote.computer = computer

        if entry_point_name is not None:
            creator = CalcJobNode(computer=computer, process_type=entry_point)
            creator.set_option('resources', {'num_machines': 1, 'num_mpiprocs_per_machine': 1})
            remote.base.links.add_incoming(creator, link_type=LinkType.CREATE, link_label='remote_folder')
            creator.store()

        return remote

    return _generate_remote_data


@pytest.fixture
def generate_bands_data():
    """Return a `BandsData` node."""

    def _generate_bands_data():
        """Return a `BandsData` instance with some basic `kpoints` and `bands` arrays."""
        from aiida.plugins import DataFactory
        import numpy
        BandsData = DataFactory('core.array.bands')  #pylint: disable=invalid-name
        bands_data = BandsData()

        bands_data.set_kpoints(numpy.array([[0., 0., 0.], [0.625, 0.25, 0.625]]))

        bands_data.set_bands(
            numpy.array([[-5.64024889, 6.66929678, 6.66929678, 6.66929678, 8.91047649],
                         [-1.71354964, -0.74425095, 1.82242466, 3.98697455, 7.37979746]]),
            units='eV'
        )

        return bands_data

    return _generate_bands_data


@pytest.fixture
def generate_workchain():
    """Generate an instance of a `WorkChain`."""

    def _generate_workchain(entry_point, inputs):
        """Generate an instance of a `WorkChain` with the given entry point and inputs.
        :param entry_point: entry point name of the work chain subclass.
        :param inputs: inputs to be passed to process construction.
        :return: a `WorkChain` instance.
        """
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import WorkflowFactory

        process_class = WorkflowFactory(entry_point)
        runner = get_manager().get_runner()
        process = instantiate_process(runner, process_class, **inputs)

        return process

    return _generate_workchain
