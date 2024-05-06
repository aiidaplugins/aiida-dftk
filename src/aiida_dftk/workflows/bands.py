"""DFTK bands WorkChain implementation."""

from aiida.engine import WorkChain, ToContext, if_
from aiida.orm import BandsData


from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.engine import BaseRestartWorkChain, ProcessHandlerReport, process_handler, while_
from aiida.plugins import CalculationFactory

from aiida_dftk.utils import create_kpoints_from_distance, validate_and_prepare_pseudos_inputs, seekpath_structure_analysis

from aiida_dftk.workflows.base import DftkBaseWorkChain

DftkCalculation = CalculationFactory('dftk')



class DftkBandsWorkChain(WorkChain):
    """ DFTK Bands Workchain to perform a DFT calculation. Validates parameters and restart."""

    _process_class = DftkCalculation

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)

        spec.input('bands_kpoints', valid_type=orm.KpointsData, required=False,
            help='Explicit kpoints to use for the BANDS calculation. Specify either this or `bands_kpoints_distance`.')
        spec.input('bands_kpoints_distance', valid_type=orm.Float, required=False,
            help='Minimum kpoints distance for the BANDS calculation. Specify either this or `bands_kpoints`.')
        spec.expose_inputs(DftkBaseWorkChain, namespace='dftk_base')

        spec.outline(
            cls.setup,
            # cls.validate_parameters,
            # cls.validate_kpoints,
            # cls.validate_pseudos,
            # cls.validate_resources,
            if_(cls.should_run_seekpath)(
                cls.run_seekpath,
            ),
            # cls.prepare_process,
            cls.run_process,
            # cls.inspect_process,
            cls.results,
        )

        # spec.expose_outputs(DftkCalculation)
        spec.output('band_parameters', valid_type=orm.Dict,
            required=True,
            help='The parameters used in the DftkBaseWorkChain.')
        spec.output('band_structure', valid_type=BandsData,
            required=True,
            help='The band structure data of the final calculation.')
        spec.output('seekpath_parameters', valid_type=orm.Dict,
            required=False,
            help='The parameters used in the SeeKpath call to normalize the input or relaxed structure.')


        spec.exit_code(301, 'ERROR_INVALID_INPUT_KPATH',
            message='Neither the `bands_kpoints` nor the `bands_kpoints_distance` input was specified, or both were specified.')

    def setup(self):
        """ create the inputs dictionary in `self.ctx.inputs`. """

        self.ctx.inputs = AttributeDict(self.exposed_inputs(DftkBaseWorkChain, 'dftk_base'))

    def validate_kpath(self):
        """Validate the inputs related to k-points.
        Either an explicit `KpointsData` with given path, or a desired kpath distance should be specified. 
        """

        # if both specified or both not specified
        if ('bands_kpoints' in self.inputs) == ('bands_kpoints_distance' in self.inputs):  # Both are present or both are absent
            return self.exit_codes['ERROR_INVALID_INPUT_KPOINTS']

        
    def should_run_seekpath(self):
        """Seekpath should only be run if the `bands_kpoints` input is not specified."""
        return 'bands_kpoints' not in self.inputs

    def run_seekpath(self):
        """Run the structure through SeeKpath to get the normalized structure and path along high-symmetry k-points .
        This is only called if the `bands_kpoints` input was not specified.
        """
        inputs = {
            'reference_distance': self.inputs.get('bands_kpoints_distance', None),
            'metadata': {
                'call_link_label': 'seekpath'
            }
        }
        result = seekpath_structure_analysis(self.ctx.inputs.dftk.structure, **inputs)
        self.ctx.bands_kpoints = result['explicit_kpoints']

        if 'parameters' in result:
            self.out('seekpath_parameters', result['parameters'])
        else:
            self.report('No seekpath parameters found')

    def run_process(self):
        """
        Run the DftkBaseWorkChain to perform the DFT calculation.
        Ensures 'compute_bands' is appropriately added or updated in 'postscf'.
        """
        inputs = AttributeDict(self.exposed_inputs(DftkBaseWorkChain, namespace='dftk_base'))
        original_parameters = inputs.dftk.parameters.get_dict()
        postscf_operations = original_parameters.get('postscf', [])

        # Update or add 'compute_bands' in postscf operations
        for operation in postscf_operations:
            if operation.get('$function') == 'compute_bands':
                operation['$kwargs'] = {'kpath': self.ctx.bands_kpoints.get_kpoints().tolist()}
                break
        else:
            postscf_operations.append({
                '$function': 'compute_bands',
                '$kwargs': {'kpath': self.ctx.bands_kpoints.get_kpoints().tolist()}
            })

        # Update and submit with new parameters
        new_parameters = dict(original_parameters, postscf=postscf_operations)
        inputs.dftk.parameters = orm.Dict(dict=new_parameters)
        running = self.submit(DftkBaseWorkChain, **inputs)
        self.report(f'Launching DftkBaseWorkChain<{running.pk}>')
        return ToContext(workchain_bands=running)

    def results(self):
        """Attach the desired output nodes directly as outputs of the workchain."""
        self.report('workchain succesfully completed')
        if 'output_parameters' in self.ctx.workchain_bands.outputs:
            self.out('band_parameters', self.ctx.workchain_bands.outputs.output_parameters)
        else:
            self.report('No output parameters found in workchain_bands.outputs')
        if 'output_bands' in self.ctx.workchain_bands.outputs:
            self.out('band_structure', self.ctx.workchain_bands.outputs.output_bands)
        else:
            self.report('No output bands found in workchain_bands.outputs')