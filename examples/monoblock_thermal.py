from catbird import *
import os
import subprocess
import sys
import math

# This is how we enable syntax
# Only enable what you need, or it runs slowly!
class MonoblockFactory(Factory): 
    def set_defaults(self):
        executioner_enable_dict={
            "obj_type": ["Steady","Transient"]
        }
        self.enable_syntax("Executioner", executioner_enable_dict)
        self.enable_syntax("Mesh")
        # self.enable_syntax("Problem")
        # self.enable_syntax("Variables")
        # self.enable_syntax("Kernels")
        # self.enable_syntax("BCs")
        # self.enable_syntax("Materials")
        # self.enable_syntax("VectorPostprocessors")
        # self.enable_syntax("Outputs")


# This class represents the boilerplate input deck
class MonoblockModel(MooseModel): 
    def load_default_syntax(self):
        self.add_syntax("Executioner", obj_type="Steady")
        self.add_syntax("Mesh",
                        action="SetupMeshAction")
        #self.add_syntax("Variables")
        #self.add_syntax("Kernels")
        #self.add_syntax("BCs")
        #self.add_syntax("Materials")
        #self.add_syntax("Outputs", action="CommonOutputAction")

# Just a struct to store geometric parameters
class MonoblockGeometry():
    def __init__(self):
        self.pipeThick=1.5e-3     # m
        self.pipeIntDiam=12e-3    # m
        self.intLayerThick=1e-3   # m
        self.monoBThick=3e-3      # m
        self.monoBArmHeight=8e-3  # m
        self.monoBDepth=12e-3     # m        
        self.pipeExtDiam=self.pipeIntDiam + 2*self.pipeThick
        self.intLayerIntDiam=self.pipeExtDiam
        self.intLayerExtDiam=self.intLayerIntDiam + 2*self.intLayerThick
        self.monoBWidth=self.intLayerExtDiam + 2*self.monoBThick
        self.pipeIntCirc=math.pi * self.pipeIntDiam

        # Mesh Sizing
        self.meshRefFact=1
        self.meshDens=1e3 # divisions per metre (nominal)
               
        # Number of divisions along the top section of the monoblock armour.
        self.monoBArmDivs=int(self.monoBArmHeight * self.meshDens * self.meshRefFact)

        # Number of divisions around each quadrant of the circumference of the pipe,
        # interlayer, and radial section of the monoblock armour.
        self.pipeCircSectDivs=2 * int(self.monoBWidth/2 * self.meshDens * self.meshRefFact / 2)

        # Number of radial divisions for the pipe, interlayer, and radial section of
        # the monoblock armour respectively.
        self.pipeRadDivs=max(int(self.pipeThick * self.meshDens * self.meshRefFact), 3)
        self.intLayerRadDivs=max(int(self.intLayerThick * self.meshDens * self.meshRefFact), 5)
        self.monoBRadDivs=max(int((self.monoBWidth-self.intLayerExtDiam)/2 * self.meshDens * self.meshRefFact), 5)

        # Number of divisions along monoblock depth (i.e. z-dimension).
        self.extrudeDivs=max(2 * int(self.monoBDepth * self.meshDens * self.meshRefFact / 2), 4)
        self.monoBElemSize=self.monoBDepth / self.extrudeDivs
        tol=self.monoBElemSize / 10
        ctol=self.pipeIntCirc / (8 * 4 * self.pipeCircSectDivs)

        
def main():
    # Get path to MOOSE
    moose_path=os.environ['MOOSE_DIR']

    # Path to executable and inputs
    module_name="heat_conduction"
    app_name=module_name+"-opt"
    app_path=os.path.join(moose_path,"modules",module_name)
    app_exe=os.path.join(app_path,app_name)

    # Create a factory of available objects from our MOOSE executable
    factory=MonoblockFactory(app_exe)
     
    config_name="monoblock_config.json"
    factory.write_config(config_name)

    # Create a boiler plate MOOSE model from a template
    model=MonoblockModel(factory)

    # Set executioner attributes
    model.executioner.solve_type='PJFNK'
    model.executioner.petsc_options_iname='-pc_type -pc_hypre_type'
    model.executioner.petsc_options_value='hypre boomeramg'

    # Set mesh attributes
    model.second_order=False

    # Add mesh generators (using kwarg syntax)
    geom=MonoblockGeometry()
    # model.add_mesh_generator("mesh_monoblock",
    #                          "PolygonConcentricCircleMeshGenerator",
    #                          num_sides=4,
    #                          polygon_size=geom.monoBWidth / 2,
    #                          polygon_size_style='apothem',
    #                          ring_radii=[ geom.pipeIntDiam / 2,
    #                                       geom.pipeExtDiam / 2,
    #                                       geom.intLayerExtDiam / 2 ],
    #                          num_sectors_per_side=[geom.pipeCircSectDivs,
    #                                                geom.pipeCircSectDivs,
    #                                                geom.pipeCircSectDivs,
    #                                                geom.pipeCircSectDivs],
    #                          ring_intervals=[1, geom.pipeRadDivs, geom.intLayerRadDivs],
    #                          background_intervals=geom.monoBRadDivs,
    #                          preserve_volumes='on',
    #                          flat_side_up=True,
    #                          ring_block_names='void pipe interlayer',
    #                          background_block_names='monoblock',
    #                          interface_boundary_id_shift=1000,
    #                          external_boundary_name='monoblock_boundary',
    #                          generate_side_specific_boundaries=True)

    model.add_mesh_generator("mesh_armour",
                             "GeneratedMeshGenerator",
                             dim=2,
                             xmin=(geom.monoBWidth/-2),
                             xmax=(geom.monoBWidth/2),
                             ymin=(geom.monoBWidth/2),
                             ymax=(geom.monoBWidth/2+geom.monoBArmHeight),
                             nx=(geom.pipeCircSectDivs),
                             ny=(geom.monoBArmDivs),
                             boundary_name_prefix='armour')

  #   model.add_mesh_generator("combine_meshes",
  #                            "StitchedMeshGenerator",
  #                            inputs='mesh_monoblock mesh_armour',
  #                            stitch_boundaries_pairs='monoblock_boundary armour_bottom',
  #                            clear_stitched_boundary_ids=true)

  #   model.add_mesh_generator("delete_void",
  #                            "BlockDeletionGenerator",
  #                            input="combine_meshes",
  #                            block="void",
  #                            new_boundary="internal_boundary")

  #   model.add_mesh_generator("merge_block_names",
  #                            "RenameBlockGenerator",
  #                            input="delete_void",
  #                            old_block='4 0',
  #                            new_block='armour armour')

  #   model.add_mesh_generator("merge_boundary_names",
  #                            "RenameBoundaryGenerator",
  #                            input=merge_block_names,
  #                            old_boundary='armour_top armour_left 10002 15002 armour_right 10004 15004 10003 15003'
  #                            new_boundary='top left left left right right right bottom bottom'

  #   model.add_mesh_generator("extrude",
  #                            "AdvancedExtruderGenerator",
  #                            input="merge_boundary_names",
  #                            direction='0 0 1',
  #                            heights=geom.monoBDepth,
  #                            num_layers=geom.extrudeDivs)

  #  model.add_mesh_generator("name_node_centre_x_bottom_y_back_z",
  #                           "BoundingBoxNodeSetGenerator",
  #                           input="extrude",
  #                           bottom_left=[-geom.ctol,
  #                                        (geom.monoBWidth/-2)-geom.ctol,
  #                                       -geom.tol],
  #                           top_right=[geom.ctol,
  #                                      (geom.monoBWidth/-2)+geom.ctol,
  #                                      geom.tol],
  #                           new_boundary="centre_x_bottom_y_back_z")
                             
  #  model.add_mesh_generator("name_node_centre_x_bottom_y_front_z",
  #                           "BoundingBoxNodeSetGenerator",
  #                           input="name_node_centre_x_bottom_y_back_z",
  #                           bottom_left=[-geom.ctol,
  #                                        (geom.monoBWidth/-2)-geom.ctol,
  #                                        geom.monoBDepth-tol],
  #                           top_right=[geom.ctol,
  #                                      (geom.monoBWidth/-2)+geom.ctol,
  #                                      geom.monoBDepth+geom.tol],
  #                           new_boundary="centre_x_bottom_y_front_z")
                        
  #   model.add_mesh_generator("name_node_left_x_bottom_y_centre_z",
  #                            "BoundingBoxNodeSetGenerator",
  #                            input="name_node_centre_x_bottom_y_front_z",
  #                            bottom_left=[(geom.monoBWidth/-2)-geom.ctol,
  #                                          (geom.monoBWidth/-2)-geom.ctol,
  #                                          geom.monoBDepth/2)-geom.tol]
  #                            top_right=[(geom.monoBWidth/-2)+geom.ctol,
  #                                       (geom.monoBWidth/-2)+geom.ctol,
  #                                       (geom.monoBDepth/2)+geom.tol],
  #                            new_boundary="left_x_bottom_y_centre_z"
  #                            )
    
  # model.add_mesh_generator("name_node_right_x_bottom_y_centre_z",
  #                          "BoundingBoxNodeSetGenerator",
  #                          input="name_node_left_x_bottom_y_centre_z",
  #                          bottom_left=[(geom.monoBWidth/2)-geom.ctol,
  #                                       (geom.monoBWidth/-2)-geom.ctol,
  #                                       (geom.monoBDepth/2)-geom.tol],
  #                          top_right=[(geom.monoBWidth/2)+geom.ctol,
  #                                     (geom.monoBWidth/-2)+geom.ctol,
  #                                     (geom.monoBDepth/2)+geom.tol],
  #                          new_boundary="right_x_bottom_y_centre_z")
  
  # # Add variables
    # var_name="T"
    # model.add_variable(var_name, initial_condition=300.0)

    # # Add kernels
    # model.add_kernel("heat_conduction", kernel_type="HeatConduction", variable=var_name)
    # model.add_kernel("time_derivative", kernel_type="HeatConductionTimeDerivative", variable=var_name)

    # # Add boundary conditions
    # model.add_bc("t_left",
    #              bc_type="DirichletBC",
    #              variable=var_name,
    #              value = 300,
    #              boundary='left')

    # model.add_bc("t_right",
    #              bc_type="FunctionDirichletBC",
    #              variable=var_name,
    #              function = "'300+5*t'",
    #              boundary = 'right')

    # # Add materials
    # model.add_material("thermal",
    #                    mat_type="HeatConductionMaterial",
    #                    thermal_conductivity=45.0,
    #                    specific_heat=0.5)

    # model.add_material("density",
    #                    mat_type="GenericConstantMaterial",
    #                    prop_names='density',
    #                    prop_values=8000.0)

    # model.outputs.exodus=True
    # model.add_output("csv",output_type="CSV",
    #                  file_base='thermal_out',
    #                  execute_on='final')    
        
    # # Add some input syntax that wasn't in the vanilla boilerplate model
    # model.add_syntax("VectorPostprocessors")
    # model.add_to_collection("VectorPostprocessors",
    #                         "VectorPostprocessor",
    #                         "t_sampler",
    #                         collection_type="LineValueSampler",
    #                         variable=var_name,
    #                         start_point='0 0.5 0',
    #                         end_point='2 0.5 0',
    #                         num_points=20,                            
    #                         sort_by='x')
    
    # Write out our input file
    input_name="monoblock_thermal.i"
    model.write(input_name)

    # # Run
    # args=[app_exe,'-i',input_name]
    # moose_process=subprocess.Popen(args)
    # stream_data=moose_process.communicate()[0]
    # retcode=moose_process.returncode 

    # # Return moose return code
    # sys.exit(retcode)

if __name__ == "__main__":
    main()

    
