from catbird import *
import math

# This is how we enable syntax
# Only enable what you need, or it runs slowly!
class AchlysFactory(Factory):
    def set_defaults(self):
        # Dictionaries limit enabled syntax to exactly what is specified
        executioner_enable_dict={
            "obj_type": ["Transient","IterationAdaptiveDT"],
            "system" : ["TimeStepper"],
        }
        mesh_enable_dict={
            "obj_type": ["FileMesh"]
        }
        aux_kernel_enable_dict={
            "collection_type": ["ParsedAux"]
        }
        kernel_enable_dict={
            "collection_type": ["ADTimeDerivative","ADCoupledForce","ADMatDiffusion","ADCoupledTimeDerivative","ADMatReaction"]
        }
        material_enable_dict={
            "collection_type": ["ADParsedMaterial","ADGenericConstantMaterial"]
        }
        bcs_enable_dict={
            "collection_type": ["ADDirichletBC"]
        }
        pp_enable_dict={
            "collection_type": ["ADSideDiffusiveFluxIntegral","ADInterfaceDiffusiveFluxIntegral"]
        }

        self.enable_syntax("Executioner", executioner_enable_dict)
        self.enable_syntax("Mesh", mesh_enable_dict)
        self.enable_syntax("Variables")
        self.enable_syntax("AuxVariables")
        self.enable_syntax("Kernels",kernel_enable_dict)
        self.enable_syntax("AuxKernels",aux_kernel_enable_dict)
        self.enable_syntax("Materials",material_enable_dict)
        self.enable_syntax("BCs", bcs_enable_dict)
        self.enable_syntax("Postprocessors",pp_enable_dict)
        self.enable_syntax("Outputs")

# Data structure for material property values
class AchlysMaterial():
    def __init__(self,name_in, block_str_in):
        self.name=name_in
        self.block_str=block_str_in

        self.rho=6.3222e28
        self.D0=4.1e-7
        self.k0_1=8.96e-17
        self.k0_2=8.96e-17

        self.p0_1=1e13
        self.p0_2=1e13
        self.E_d=0.39
        self.E_t_1=0.39
        self.E_t_2=0.39
        self.E_p_1=0.87
        self.E_p_2=1.0
        self.n_1=1.3e-3
        self.n_2=4e-4


# This class represents the boilerplate input deck
class AchlysModel(MooseModel):
    def load_default_syntax(self):
        self.add_syntax("Mesh", obj_type="FileMesh")
        self.add_syntax("AuxVariables")
        self.add_syntax("AuxKernels")
        self.add_syntax("Variables")
        self.add_syntax("Materials")
        self.add_syntax("Kernels")
        self.add_syntax("BCs")
        self.add_syntax("Executioner", obj_type="Transient")
        self.add_syntax("Executioner.TimeStepper", obj_type="IterationAdaptiveDT")
        self.add_syntax("Postprocessors")
        self.add_syntax("Outputs", action="CommonOutputAction")

    def __init__(self,factory_in):
        super().__init__(factory_in)
        assert isinstance(factory_in,AchlysFactory)
        self._concretise_model()


    def _add_achlys_materials(self,mats):
        self.active_blocks=[]
        for mat in mats:
            self._add_achlys_material(mat)
            self.active_blocks.append(mat.block_str)

        block_str=" ".join(self.active_blocks)


        # Global properties
        self.add_material("trap_1_reaction",
                          "ADParsedMaterial",
                          coupled_variables='trapped_1',
                          property_name='trap_1_reaction',
                          material_property_names='trapping_rate_1 trap_density_1',
                          expression='trapping_rate_1 * (trap_density_1 - trapped_1)',
                          block=block_str)

        self.add_material("trap_2_reaction",
                          "ADParsedMaterial",
                          property_name='trap_2_reaction',
                          coupled_variables='trapped_2',
                          material_property_names='trapping_rate_2 trap_density_2',
                          expression='trapping_rate_2 * (trap_density_2 - trapped_2)',
                          block=block_str)

    def _add_achlys_material(self,mat):
        assert isinstance(mat,AchlysMaterial)

        # Global constant
        k_b=8.6e-5

        # Add materials
        self.add_material("D_{}".format(mat.name),
                         "ADParsedMaterial",
                         property_name='D',
                         coupled_variables='Temperature',
                         constant_names='D0 E_d kb',
                         constant_expressions='{} {} {}'.format(mat.D0,mat.E_d,k_b),
                         expression='D0 * exp(-E_d / (kb * Temperature))',
                         block=mat.block_str)

        self.add_material("trapping_factor_{}_1".format(mat.name),
                          "ADParsedMaterial",
                          property_name='trapping_rate_1',
                          coupled_variables='Temperature',
                          constant_names='k0_1 E_t_1 kb rho',
                          constant_expressions='{} {} {} {}'.format(mat.k0_1,mat.E_t_1,k_b,mat.rho),
                          expression='k0_1 * rho * exp(-E_t_1 / (kb * Temperature))',
                          block=mat.block_str)

        self.add_material("trapping_factor_{}_2".format(mat.name),
                          "ADParsedMaterial",
                          property_name='trapping_rate_2',
                          coupled_variables='Temperature',
                          constant_names = 'k0_2 E_t_2 kb rho',
                          constant_expressions = '{} {}  {} {}'.format(mat.k0_2,mat.E_t_2,k_b,mat.rho),
                          expression = 'k0_2 * rho * exp(-E_t_2 / (kb * Temperature))',
                          block=mat.block_str)

        self.add_material("detrapping_factor_{}_1".format(mat.name),
                          "ADParsedMaterial",
                          property_name='detrapping_rate_1',
                          coupled_variables='Temperature',
                          constant_names='p0_1 E_p_1 kb',
                          constant_expressions='{} {} {}'.format(mat.p0_1, mat.E_p_1,k_b),
                          expression='-p0_1 * exp(-E_p_1 / (kb * Temperature))',
                          block=mat.block_str)

        self.add_material("detrapping_factor_{}_2".format(mat.name),
                          "ADParsedMaterial",
                          property_name='detrapping_rate_2',
                          coupled_variables='Temperature',
                          constant_names='p0_2 E_p_2 kb',
                          constant_expressions='{} {} {}'.format(mat.p0_2, mat.E_p_2,k_b),
                          expression='-p0_2 * exp(-E_p_2 / (kb * Temperature))',
                          block=mat.block_str)

        self.add_material("trap_density_{}_1".format(mat.name),
                          "ADParsedMaterial",
                          property_name='trap_density_1',
                          constant_names='n_1',
                          constant_expressions='{}'.format(mat.n_1),
                          expression='n_1',
                          block=mat.block_str)

        self.add_material("trap_density_{}_2".format(mat.name),
                          "ADParsedMaterial",
                          property_name='trap_density_2',
                          constant_names='n_2',
                          constant_expressions='{}'.format(mat.n_2),
                          expression='n_2',
                          block=mat.block_str)

        self.add_material("atomic_density_{}".format(mat.name),
                          "ADGenericConstantMaterial",
                          prop_names='rho',
                          prop_values='{}'.format(mat.rho),
                          block=mat.block_str)


    def _concretise_model(self):
        # Set mesh attributes
        self.mesh.file='breeder_unit.e'

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

        # Timestepper attribute
        self.executioner.timestepper.optimal_iterations=12
        self.executioner.timestepper.cutback_factor=0.8
        self.executioner.timestepper.growth_factor=1.2
        self.executioner.timestepper.dt=10

        # Aux variables
        aux_variables=["Temperature","H3_source","total_trapped","total_mobile","total_retention"]
        for var_name in aux_variables:
            self.add_aux_variable(var_name)

        # Aux var initial conditions
        self.auxvariables.objects["Temperature"].initial_condition=500
        self.auxvariables.objects["H3_source"].initial_condition=1e-12

        # Aux kernel
        self.add_aux_kernel("total_mobile",
                            "ParsedAux",
                            variable="total_mobile",
                            coupled_variables='mobile',
                            expression='mobile * 6.3222e28')

        self.add_aux_kernel("total_trapped",
                            "ParsedAux",
                            variable="total_trapped",
                            coupled_variables='trapped_1 trapped_2',
                            expression='(trapped_1 + trapped_2) * 6.3222e28')

        self.add_aux_kernel("total_retention",
                            "ParsedAux",
                            variable="total_retention",
                            coupled_variables='mobile trapped_1 trapped_2',
                            expression='(mobile + trapped_1 + trapped_2) * 6.3222e28')

        # Add variables
        variables=["mobile","trapped_1","trapped_2"]
        for var_name in variables:
            self.add_variable(var_name)

        # Add materials - TODO: add params
        multiplier= AchlysMaterial("multiplier", "Beryllium")
        steel = AchlysMaterial("steel","EUROFER Perf_Steel")
        breeder = AchlysMaterial("breeder", "KALOS")
        materials=[multiplier, steel, breeder]
        self._add_achlys_materials(materials)
        #purge_gas = AchlysMaterial("purge_gas", "h_he")
        #coolant = AchlysMaterial("coolant","helium")

        # Add kernels
        block_str=" ".join(self.active_blocks)
        self.add_kernel("time_derivative_mobile","ADTimeDerivative",variable="mobile",block=block_str)
        self.add_kernel("source_term","ADCoupledForce",variable="mobile",v="H3_source",block=block_str)
        self.add_kernel("diffusion","ADMatDiffusion",variable="mobile",diffusivity="D",block=block_str)
        self.add_kernel("coupled_time_derivative_trap_1","ADCoupledTimeDerivative",variable="mobile",v="trapped_1",block=block_str)
        self.add_kernel("coupled_time_derivative_trap_2","ADCoupledTimeDerivative",variable="mobile",v="trapped_2",block=block_str)

        self.add_kernel("time_derivative_trap_1","ADTimeDerivative",variable="trapped_1",block=block_str)
        self.add_kernel("trapping_1","ADMatReaction",variable="trapped_1",v="mobile",reaction_rate="trap_1_reaction",block=block_str)
        self.add_kernel("detrapping_1","ADMatReaction",variable="trapped_1",reaction_rate="detrapping_rate_1",block=block_str)

        self.add_kernel("time_derivative_trap_2","ADTimeDerivative",variable="trapped_2",block=block_str)
        self.add_kernel("trapping_2","ADMatReaction",variable="trapped_2",v="mobile",reaction_rate="trap_2_reaction",block=block_str)
        self.add_kernel("detrapping_2","ADMatReaction",variable="trapped_2",reaction_rate="detrapping_rate_2",block=block_str)

        # Add boundary conditions
        boundary_list=["Beryllium_air", "EUROFER_air", "EUROFER_H_He", "EUROFER_Helium", "Perf_Steel_H_He"]
        boundary_str=" ".join(boundary_list)
        self.add_bc("outflow",
                    "ADDirichletBC",
                    variable="mobile",
                    boundary=boundary_str,
                    value=0)

        # Add postprocessors

        self.add_postprocessor("tritium_extraction",
                               "ADSideDiffusiveFluxIntegral",
                               variable="total_mobile",
                               diffusivity="D",
                               boundary="Perf_Steel_H_He")

        # Turn on outputs
        self.outputs.console=True
        self.outputs.exodus=True
        self.outputs.csv=True
