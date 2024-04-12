# -*- coding: utf-8 -*-
"""`CalcJob` implementation for DFTK."""
import io
import json
import typing as ty

from aiida import orm
from aiida.common import datastructures, exceptions
from aiida.engine import CalcJob
from aiida_pseudo.data.pseudo import UpfData
from pymatgen.core import units


class DftkCalculation(CalcJob):
    """`CalcJob` implementation for DFTK."""

    _DEFAULT_PREFIX = 'DFTK'
    _DEFAULT_INPUT_EXTENSION = 'json'
    _DEFAULT_STDOUT_EXTENSION = 'txt'
    _DEFAULT_SCFRES_SUMMARY_NAME = 'self_consistent_field.json'
    _SUPPORTED_POSTSCF = ['compute_forces_cart', 'compute_stresses_cart','compute_bands']
    _PSEUDO_SUBFOLDER = './pseudo/'

    @staticmethod
    def _merge_dicts(dict1, dict2):
        """Recursively merge dict2 into dict1."""
        for key, value in dict2.items():
            if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
                DftkCalculation._merge_dicts(dict1[key], value)
            else:
                dict1[key] = value

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)
        # Inputs
        spec.input('metadata.options.prefix', valid_type=str, default=cls._DEFAULT_PREFIX)
        spec.input('metadata.options.stdout_extension', valid_type=str, default=cls._DEFAULT_STDOUT_EXTENSION)
        spec.input('metadata.options.withmpi', valid_type=bool, default=True)

        spec.input('structure', valid_type=orm.StructureData, help='structure')
        spec.input_namespace('pseudos', valid_type=UpfData, help='The pseudopotentials.', dynamic=True)
        spec.input('kpoints', valid_type=orm.KpointsData, help='kpoint mesh or kpoint path')
        spec.input('parameters', valid_type=orm.Dict, help='input parameters')
        spec.input('settings', valid_type=orm.Dict, required=False, help='Various special settings.')

        options = spec.inputs['metadata']['options']
        options['parser_name'].default = 'dftk'
        options['resources'].default = {'num_machines': 1, 'num_mpiprocs_per_machine': 1}
        options['input_filename'].default = f'{cls._DEFAULT_PREFIX}.{cls._DEFAULT_INPUT_EXTENSION}'

        # Exit codes
        spec.exit_code(101, 'ERROR_MISSING_FORCES_FILE', message='The output file containing forces is missing.')
        spec.exit_code(102, 'ERROR_MISSING_STRESSES_FILE', message='The output file containing stresses is missing.')
        spec.exit_code(500, 'ERROR_SCF_CONVERGENCE_NOT_REACHED', message='The SCF minimization cycle did not converge.')

        # Outputs
        spec.output('output_parameters', valid_type=orm.Dict, help='output parameters')
        spec.output('output_structure', valid_type=orm.Dict, required=False, help='output structure')
        spec.output(
            'output_kpoints', valid_type=orm.KpointsData, required=False, help='kpoints array, if generated by DFTK'
        )
        spec.output('output_forces', valid_type=orm.ArrayData, required=False, help='forces array')
        spec.output('output_stresses', valid_type=orm.ArrayData, required=False, help='stresses array')

        # TODO: bands and DOS implementation required on DFTK side
        # spec.output('output_bands', valid_type=orm.BandsData, required=False,
        #     help='eigenvalues array')
        # spec.output('output_dos')

        spec.default_output_node = 'output_parameters'

    def validate_inputs(self):
        """Validate input parameters.

        Check that the post-SCF function(s) are supported.
        """
        parameters = self.inputs.parameters.get_dict()
        if 'postscf' in parameters:
            for postscf in parameters['postscf']:
                if postscf['$function'] not in self._SUPPORTED_POSTSCF:
                    raise exceptions.InputValidationError(f"Unsupported postscf function: {postscf['$function']}")

    def validate_pseudos(self):
        """Valdiate the pseudopotentials.

        Check that there is a one-to-one map of kinds in the structure to pseudopotentials.
        """
        kinds = [kind.name for kind in self.inputs.structure.kinds]
        if set(kinds) != set(self.inputs.pseudos.keys()):
            pseudos_str = ', '.join(list(self.inputs.pseudos.keys()))
            kinds_str = ', '.join(list(kinds))
            raise exceptions.InputValidationError(
                'Mismatch between the defined pseudos and the list of kinds of the structure.\n'
                f'Pseudos: {pseudos_str};\nKinds:{kinds_str}'
            )

    def validate_kpoints(self):
        """Validate the k-points intput.

        Check that the input k-points provide a k-points mesh.
        """
        try:
            self.inputs.kpoints.get_kpoints_mesh()
        except AttributeError as exc:
            raise exceptions.InputValidationError('The kpoints input does not have a valid mesh set.') from exc

    def _generate_inputdata(
        self, parameters: orm.Dict, structure: orm.StructureData, pseudos: dict, kpoints: orm.KpointsData
    ) -> ty.Tuple[dict, list]:
        """Generate the input dict (json) for DFTK.

        :param parameters: a dict defines the calculation parameters for DFTK
        :param structre: a StructureDate define the crystal
        :param pseudos: a dict contains the pseudos
        :param kpoints: a KpointData
        :return: dict for the DFTK json input
        :return: list of a pseudos needed to be copied
        """

        local_copy_pseudo_list = []

        data = {'periodic_system': {}, 'model_kwargs': {}, 'basis_kwargs': {}, 'scf': {}, 'postscf': []}
        data['periodic_system']['bounding_box'] = [[x * units.ang_to_bohr for x in vec] for vec in structure.cell]
        data['periodic_system']['atoms'] = []
        for site in structure.sites:
            data['periodic_system']['atoms'].append({
                'symbol': site.kind_name,
                'position': [X * units.ang_to_bohr for X in list(site.position)],
                'pseudopotential': f'{self._PSEUDO_SUBFOLDER}{pseudos[site.kind_name].filename}'
            })
            pseudo = pseudos[site.kind_name]
            local_copy_pseudo_list.append((pseudo.uuid, pseudo.filename, f'{self._PSEUDO_SUBFOLDER}{pseudo.filename}'))
        data['basis_kwargs']['kgrid'], data['basis_kwargs']['kshift'] = kpoints.get_kpoints_mesh()
        DftkCalculation._merge_dicts(data, parameters.get_dict())

        return data, local_copy_pseudo_list

    def _generate_cmdline_params(self) -> ty.List[str]:
        # Define the command based on the input settings
        cmd_params = []
        cmd_params.extend(['-e', 'using AiidaDFTK; AiidaDFTK.run()', self.metadata.options.input_filename])
        return cmd_params

    def _generate_retrieve_list(self, parameters: orm.Dict) -> list:
        """Generate the list of files to retrieve based on the type of calculation requested in the input parameters.

        :param parameters: input parameters
        :returns: list of files to retreive
        """
        parameters = parameters.get_dict()
        retrieve_list = [f"{item['$function']}.hdf5" for item in parameters['postscf']]
        retrieve_list.append(f'{self._DEFAULT_PREFIX}.log')
        retrieve_list.append('timings.json')
        retrieve_list.append(f'{self._DEFAULT_PREFIX}.{self._DEFAULT_STDOUT_EXTENSION}')
        retrieve_list.append(f'{self._DEFAULT_SCFRES_SUMMARY_NAME}')
        return retrieve_list

    def prepare_for_submission(self, folder):
        """Create the input file(s) from the input nodes.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files needed by
            the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        self.validate_inputs()
        self.validate_pseudos()
        self.validate_kpoints()

        # Generate the input file content
        arguments = [self.inputs.parameters, self.inputs.structure, self.inputs.pseudos, self.inputs.kpoints]
        input_filecontent, local_copy_list = self._generate_inputdata(*arguments)

        # write input file
        input_filename = folder.get_abs_path(self.metadata.options.input_filename)
        with io.open(input_filename, 'w', encoding='utf-8') as stream:
            json.dump(input_filecontent, stream)

        # prepare command line parameters
        cmdline_params = self._generate_cmdline_params()

        # prepare retrieve list
        retrieve_list = self._generate_retrieve_list(self.inputs.parameters)

        # Set up the `CodeInfo` to pass to `CalcInfo`
        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = cmdline_params
        codeinfo.stdout_name = f'{self._DEFAULT_PREFIX}.{self._DEFAULT_STDOUT_EXTENSION}'
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # Set up the `CalcInfo` so AiiDA knows what to do with everything
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.stdout_name = f'{self._DEFAULT_PREFIX}.{self._DEFAULT_STDOUT_EXTENSION}'
        calcinfo.retrieve_list = retrieve_list
        calcinfo.local_copy_list = local_copy_list

        return calcinfo
