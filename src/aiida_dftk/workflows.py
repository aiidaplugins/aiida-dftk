# -*- coding: utf-8 -*-
from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.engine import BaseRestartWorkChain, ProcessHandlerReport, process_handler, while_
from aiida.plugins import CalculationFactory

DftkCalculation = CalculationFactory('dftk')

class DftkBaseWorkChain(BaseRestartWorkChain):
    """Base DFTK workchain which manages error handling and restarts."""

    _process_class = DftkCalculation

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)

        spec.input('kpoints', valid_type=orm.KpointsData, required=False,
            help='explicit k-points or Monkhorst-Pack mesh')
        spec.input('kpoints_distance', valid_type=orm.Float, required=False,
            help='minimum desired distance in 1/A between k-points in reciprocal space')
        spec.expose_inputs(DftkCalculation, namespace='dftk', exclude=('kpoints',))
        spec.inputs_validator = cls.validate_inputs

        spec.outline(
            cls.setup,
            while_(cls.should_run_process)(
                cls.prepare_process,
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        spec.expose_outputs(DftkCalculation)

    @classmethod
    def validate_inputs(cls, value, _):
        pass
