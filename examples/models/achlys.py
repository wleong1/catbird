from catbird import *
import math

# This is how we enable syntax
# Only enable what you need, or it runs slowly!
class AchlysFactory(Factory):
    def set_defaults(self):
        # Dictionaries limit enabled syntax to exactly what is specified
        executioner_enable_dict={
            "obj_type": ["Transient"],
            "system" : ["TimeSteppers"]
        } 
        mesh_enable_dict={
            "obj_type": ["FileMesh"]
        }
        self.enable_syntax("Executioner")
        self.enable_syntax("Executioner", executioner_enable_dict)
        #self.enable_syntax("Mesh", mesh_enable_dict)
        # self.enable_syntax("Variables")
        # self.enable_syntax("Kernels")
        # self.enable_syntax("AuxVariables")
        # self.enable_syntax("AuxKernels")
        # self.enable_syntax("Materials")
        # self.enable_syntax("BCs")
        # self.enable_syntax("Postprocessors")
        # self.enable_syntax("Outputs")

# This class represents the boilerplate input deck
class AchlysModel(MooseModel):
    def load_default_syntax(self):
        self.add_syntax("Mesh", obj_type="FileMesh")
        # self.add_syntax("AuxVariables")
        # self.add_syntax("AuxKernels")
        # self.add_syntax("Variables")
        # self.add_syntax("Materials")
        # self.add_syntax("Kernels")
        # self.add_syntax("BCs")
        self.add_syntax("Executioner", obj_type="Transient")
        # self.add_syntax("Executioner.TimeSteppers")
        # self.add_syntax("Postprocessors")
        # self.add_syntax("Outputs", action="CommonOutputAction")

    def __init__(self,factory_in):
        super().__init__(factory_in)
        assert isinstance(factory_in,AchlysFactory)
        self._concretise_model()

    def _concretise_model(self):
        # Set mesh attributes
        self.mesh.file='mesh.e'

        # Set executioner attributes
        self.executioner.solve_type='NEWTON'
        self.executioner.petsc_options_iname='-ksp_type -pc_type -pc_factor_mat_solver_package -pc_factor_shift_type'
        self.executioner.petsc_options_value='bcgs lu superlu_dist NONZERO'        
        self.executioner.line_search='l2'
        self.executioner.scheme='bdf2'        
        self.executioner.automatic_scaling=True
        self.executioner.compute_scaling_once=False
        self.executioner.residual_and_jacobian_together=True
        self.executioner.reuse_preconditioner=True
        self.executioner.reuse_preconditioner_max_linear_its=20
        self.executioner.end_time=1e5
        self.executioner.dtmin=1e-2

        # # timestepping options
        # [TimeStepper]
        #   type = IterationAdaptiveDT
        #   optimal_iterations = 12
        #   cutback_factor = 0.8
        #   growth_factor = 1.2
        #   dt = 10 
        # []


        # # Add variables
        # var_name="temperature"
        # self.add_variable(var_name,
        #                    family="LAGRANGE",
        #                    order="FIRST",
        #                    initial_condition=coolantTemp)

        # # Add kernels
        # self.add_kernel("heat_conduction",kernel_type="HeatConduction", variable=var_name)


        # # Add materials
        # # Thermal conductivities
        # self.add_material("cucrzr_thermal_conductivity",
        #                    "PiecewiseLinearInterpolationMaterial",
        #                    xy_data=[20,  318,
        #                             50,  324,
        #                             100, 333,
        #                             150, 339,
        #                             200, 343,
        #                             250, 345,
        #                             300, 346,
        #                             350, 347,
        #                             400, 347,
        #                             450, 346,
        #                             500, 346],
        #                    variable=var_name,
        #                    property='thermal_conductivity',
        #                    block='pipe')

 
        # # Add boundary conditions
        # surfHeatFlux=10e6   # W/m^2
        # self.add_bc("heat_flux_in",
        #              "NeumannBC",
        #              variable=var_name,
        #              boundary='top',
        #              value=surfHeatFlux)

        # self.add_bc("heat_flux_out",
        #              "ConvectiveHeatFluxBC",
        #              variable=var_name,
        #              boundary='internal_boundary',
        #              T_infinity=coolantTemp,
        #              heat_transfer_coefficient='heat_transfer_coefficient')

        # # Add Exodus output
        # self.outputs.exodus=True

        # # Add postprocessor
        # self.add_postprocessor("max_temp","ElementExtremeValue",variable=var_name)
