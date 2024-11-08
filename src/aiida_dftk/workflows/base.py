# -*- coding: utf-8 -*-
"""Base DFTK WorkChain implementation."""
from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.engine import BaseRestartWorkChain, ProcessHandlerReport, process_handler, while_
from aiida.plugins import CalculationFactory

from aiida_dftk.utils import create_kpoints_from_distance, validate_and_prepare_pseudos_inputs

DftkCalculation = CalculationFactory('dftk')


class DftkBaseWorkChain(BaseRestartWorkChain):
    """Base DFTK Workchain to perform a DFT calculation. Validates parameters and restart."""

    _process_class = DftkCalculation

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)

        spec.input('kpoints',
                   valid_type=orm.KpointsData,
                   required=False,
                   help='An explicit k-points mesh or list. Either this or `kpoints_distance` '
                        'must be provided.')
        spec.input('kpoints_distance',
                   valid_type=orm.Float,
                   required=False,
                   help='The minimum desired distance in 1/Å between k-points in reciprocal space. The explicit '
                        'k-point mesh will be generated automatically by a calculation function based on the input '
                        'structure.')
        spec.expose_inputs(DftkCalculation,
                           namespace='dftk',
                           exclude=('kpoints',))

        spec.outline(
            cls.setup,
            cls.validate_kpoints,
            cls.validate_pseudos,
            cls.validate_resources,
            while_(cls.should_run_process)(
                cls.prepare_process,
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        spec.expose_outputs(DftkCalculation)

        spec.exit_code(201, 'ERROR_INVALID_INPUT_PSEUDO_POTENTIALS',
            message='`pseudos` could not be used to get the necessary pseudos.')
        spec.exit_code(202, 'ERROR_INVALID_INPUT_KPOINTS',
            message='Neither the `kpoints` nor the `kpoints_distance` input was specified.')
        spec.exit_code(203, 'ERROR_INVALID_INPUT_RESOURCES',
            message='Neither the `options` nor `automatic_parallelization` input was specified.')
        spec.exit_code(204, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED',
            message='The `metadata.options` did not specify both `resources.num_machines` and `max_wallclock_seconds`.')

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """
        super().setup()
        self.ctx.restart_calc = None
        self.ctx.inputs = AttributeDict(self.exposed_inputs(DftkCalculation, 'dftk'))

    # TODO: We probably want to handle the kpoint distance on the Julia side instead.
    def validate_kpoints(self):
        """Validate the inputs related to k-points.

        Either an explicit `KpointsData` with given mesh/path, or a desired k-points distance should be specified. In
        the case of the latter, the `KpointsData` will be constructed for the input `StructureData` using the
        `create_kpoints_from_distance` calculation function.
        """

        # if both specified or both not specified
        if ('kpoints' in self.inputs) == ('kpoints_distance' in self.inputs):  # Both are present or both are absent
            return self.exit_codes['ERROR_INVALID_INPUT_KPOINTS']


        try:
            kpoints = self.inputs.kpoints
        except AttributeError:
            inputs = {
                'structure': self.inputs.dftk.structure,
                'distance': self.inputs.kpoints_distance,
                'metadata': {'call_link_label': 'create_kpoints_from_distance'}
            }
            kpoints = create_kpoints_from_distance(**inputs)  # pylint: disable=unexpected-keyword-arg

        self.ctx.inputs.kpoints = kpoints

    def validate_pseudos(self):
        """Validate the inputs related to pseudopotentials.

        The pseudo potentials should be defined explicitly in the `pseudos` namespace
        """
        structure = self.ctx.inputs.structure
        pseudos = self.inputs.dftk.get('pseudos', None)

        try:
            self.ctx.inputs.pseudos = validate_and_prepare_pseudos_inputs(structure, pseudos)
        except ValueError as exception:
            self.report(f'{exception}')
            return self.exit_codes.ERROR_INVALID_INPUT_PSEUDO_POTENTIALS  # pylint: disable=no-member


    # TODO: This is weird. Shouldn't aiida already handle this internally?
    def validate_resources(self):
        """Validate the inputs related to the resources.

        `metadata.options` should at least contain the options `resources` and `max_wallclock_seconds`,
        where `resources` should define the `num_machines`.
        """
        num_machines = self.ctx.inputs.metadata.options.get('resources', {}).get('num_machines', None)
        max_wallclock_seconds = self.ctx.inputs.metadata.options.get('max_wallclock_seconds', None)

        if num_machines is None or max_wallclock_seconds is None:
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED  # pylint: disable=no-member


    def prepare_process(self):
        """Prepare the inputs for the next calculation.

        If a `restart_calc` has been set in the context, its `remote_folder` will be used as the `parent_folder` input
        for the next calculation and the `restart_mode` is set to `restart`. Otherwise, no `parent_folder` is used and
        `restart_mode` is set to `from_scratch`.
        """

        # AiidaDFTK will automatically check the existance of a checkpoint(scfres.jld2) and restart from it
        if self.ctx.restart_calc:
            self.ctx.inputs.parent_folder = self.ctx.restart_calc.outputs.remote_folder

    def report_error_handled(self, calculation, action):
        """Report an action taken for a calculation that has failed.

        This should be called in a registered error handler if its condition is met and an action was taken.

        :param calculation: the failed calculation node
        :param action: a string message with the action taken
        """
        self.report(f'{calculation.process_label}<{calculation.pk}> failed with exit status {calculation.exit_status}: {calculation.exit_message}')
        self.report(f'Action taken: {action}')

    @process_handler(priority=500, exit_codes=[DftkCalculation.exit_codes.ERROR_SCF_CONVERGENCE_NOT_REACHED])
    def handle_scf_convergence_not_reached(self, _):
        """Handle unconverged SCF calculations."""
        return None

    # Just as a blueprint, delete after ^ is implemented
    # TODO: What exactly is this doing?
    @process_handler(priority=580, exit_codes=[
        DftkCalculation.exit_codes.ERROR_SCF_CONVERGENCE_NOT_REACHED,
        DftkCalculation.exit_codes.ERROR_POSTSCF_OUT_OF_WALLTIME
        ])
    def handle_recoverable_SCF_unconverged_and_POSTSCF_out_of_walltime_(self, calculation):
        """Handle `ERROR_SCF_CONVERGENCE_NOT_REACHED` and `ERROR_POSTSCF_OUT_OF_WALLTIME` exit code: calculations shut down neatly and we can simply restart."""
        try:
            self.ctx.inputs.structure = calculation.outputs.output_structure
        except exceptions.NotExistent:
            self.ctx.restart_calc = calculation
            self.ctx.inputs.metadata.options.max_wallclock_seconds = 3600
            self.ctx.inputs.parameters['scf']['$kwargs']['maxiter'] = 100
            self.report_error_handled(calculation, 'restart from the last calculation, set max_wallclock_seconds as 3600s, maxiter as 100')
        else:
            self.ctx.restart_calc = None
            self.report_error_handled(calculation, 'out of walltime: structure changed, so restarting from scratch')

        return ProcessHandlerReport(True)
