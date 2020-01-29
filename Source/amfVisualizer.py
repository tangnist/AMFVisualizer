#####################################
######   AMF Scenario Editor  #######
#####################################
# Author: Tanguy Ropitault          #
# email: tanguy.ropitault@nist.gov  #
#####################################

######################################################################################################
# NIST-developed software is provided by NIST as a public service. You may use, copy                 #
# and distribute copies of the software in any medium, provided that you keep intact this            #
# entire notice. You may improve, modify and create derivative works of the software or              #
# any portion of the software, and you may copy and distribute such modifications or                 #
# works. Modified works should carry a notice stating that you changed the software                  #
# and should note the date and nature of any such change. Please explicitly                          #
# acknowledge the National Institute of Standards and Technology as the source of the                #
# software.                                                                                          #
#
# NIST-developed software is expressly provided "AS IS." NIST MAKES NO                               #               
# WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT OR ARISING BY                                      #
# OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED                                       #
# WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,                                     #
# NON-INFRINGEMENT AND DATA ACCURACY. NIST NEITHER REPRESENTS                                        #
# NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE                                            #
# UNINTERRUPTED OR ERROR-FREE, OR THAT ANY DEFECTS WILL BE                                           #
# CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS                                       #
# REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF,                                          #
# INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY,                                            #
# RELIABILITY, OR USEFULNESS OF THE SOFTWARE.                                                        #
#                                                                                                    #
#                                                                                                    #
# You are solely responsible for determining the appropriateness of using                            #
# and distributing the software and you assume all risks associated with its use, including          #
# but not limited to the risks and costs of program errors, compliance with applicable               #
# laws, damage to or loss of data, programs or equipment, and the unavailability or                  #
# interruption of operation. This software is not intended to be used in any situation               #
# where a failure could cause risk of injury or damage to property. The software                     #
# developed by NIST employees is not subject to copyright protection within the United               #
# States.                                                                                            #
######################################################################################################


# First, and before importing any Enthought packages, set the ETS_TOOLKIT
# environment variable to qt4, to tell Traits that we will use Qt.
import os
os.environ['ETS_TOOLKIT'] = 'qt4'
from pyface.qt import QtGui
from traits.api import HasTraits, Instance, on_trait_change
from traitsui.api import View, Item
from mayavi.core.ui.api import MayaviScene, MlabSceneModel, \
        SceneEditor
from mayavi import mlab
from mayavi.api import Engine
from mayavi.modules.labels import Labels
from traits.api import HasTraits, Range, Instance, \
    on_trait_change, Button, Bool, Enum, List, Array
from mayavi.tools.mlab_scene_model import \
    MlabSceneModel
from traitsui.api import Group, HGroup, HSplit, VSplit, Item, View
from tvtk.pyface.scene_editor import SceneEditor
from mayavi.core.ui.mayavi_scene import MayaviScene
import vtk
import argparse
import numpy as np
import os
from pathlib import Path
from traits.api \
    import HasTraits, HasStrictTraits, Str, Int, Regex, List,Float
from traitsui.menu \
    import Menu, Action, Separator
from traitsui.api import CheckListEditor
from pyface.api import GUI
import xml.etree.ElementTree as ET


#########################################
######      Global Variables       ######
#########################################
# File and Folder variable
AMF_FOLDER = "scenarios" # The folder containing the AMF files
AMF_SAVED_PREFIX = "Modified" # Prefix added when a new AMF file is generated after a new material is assigned to an object
AMF_FILE = "" # The AMF file to visualize

DICT_MATERIAL = {}  # The dictionnary that contains the Material library properties (right now, the Material ID is used as a key and the only property is the material Name)
LIST_AMF_OBJECTS = [] # The list that contains the ObjectGeometry objects of the AMF file
CURRENT_SELECTED_OBJECT = -1 # Last object picked-up in the visualizer
AMF_ROOT = 0 # The AMF file root
AMF_TREE = 0 # The AMF file tree

#########################################
######   End Global Variables      ######
#########################################


# Force the render (inspired by https://python.hotexamples.com/examples/pyface.api/GUI/set_busy/python-gui-set_busy-method-examples.html)
def force_render():
    _gui = GUI()
    orig_val = _gui.busy
    _gui.set_busy(busy=True)
    _gui.set_busy(busy=orig_val)
    _gui.process_events()

# Class that represents an AMF object in the visualizer
class ObjectGeometry:
    def __init__(self, xmlObjectID, name, geometry,materialId):
        self.xmlObjectID = xmlObjectID # The object ID in the AMF file
        self.name = name # The object name in the AMF file
        self.geometry = geometry # The 3D geometry of the object (constructed from the AMF file)
        self.materialId = materialId # The Material ID associated to the object

# The visualization handler
class Visualization(HasTraits):
    engine1 = Instance(Engine, args=())
    sceneView1 = Instance(MlabSceneModel, ()) # The scene model
    # Initialize the GUI Values
    GUI_OBJECT_NAME = Str("")
    GUI_ID = Str("")
    GUI_MATERIAL_ID = Str("")
    GUI_MATERIAL_NAME = Str("")
    GUI_CHANGE_REPRESENTATION = Bool
    GUI_CHANGE_MATERIAL = Str
    GUI_MATERIAL_LIBRARY = List([''])
  
    # Initialize the picker
    @on_trait_change('sceneView1.activated')
    def initializePicker(self):
        picker = self.sceneView1.mayavi_scene.on_mouse_pick(self.picker_callback, type = 'cell')
        picker.tolerance = 0.01
 
    #  Perform an action depending if an AMF object was picked or not
    def picker_callback(self, picker):
        global LIST_AMF_OBJECTS, CURRENT_SELECTED_OBJECT, DICT_MATERIAL
        
        # Catch the errors here
        output=vtk.vtkFileOutputWindow()
        output.SetFileName("log.txt")
        vtk.vtkOutputWindow().SetInstance(output)
      
        picker_outside = True 
        # Check if the object picked belongs to our LIST_AMF_OBJECTS
        for i in range(len(LIST_AMF_OBJECTS)):
            if picker.actor in LIST_AMF_OBJECTS[i].geometry.actor.actors:
                # The user picked an object in our LIST_AMF_OBJECTS
                picker_outside = False

                # Update the visualization
                LIST_AMF_OBJECTS[i].geometry.actor.mapper.scalar_visibility = False # Disable the scalar colors assigned to the object
                LIST_AMF_OBJECTS[i].geometry.actor.property.color = (1, 0, 0) # Color the picked object in red
                LIST_AMF_OBJECTS[i].geometry.actor.property.line_width = 8 # Increase slighly the size of the wireframe edges
              
                # Update the GUI
                self.GUI_OBJECT_NAME = LIST_AMF_OBJECTS[i].name
                self.GUI_ID = LIST_AMF_OBJECTS[i].xmlObjectID
                self.GUI_MATERIAL_ID = LIST_AMF_OBJECTS[i].materialId
                self.GUI_MATERIAL_NAME = DICT_MATERIAL[LIST_AMF_OBJECTS[i].materialId]
               
                CURRENT_SELECTED_OBJECT = i  
                # LIST_AMF_OBJECTS[i].geometry.actor.actor.scale = (1,1,2) # Just a placeholder in case we want to slightly increase the height of the selected object
            else:
                # The object was not picked - Reapply the original Scalar Color and line width
                LIST_AMF_OBJECTS[i].geometry.actor.mapper.scalar_visibility = True
                LIST_AMF_OBJECTS[i].geometry.actor.property.line_width = 2
                # LIST_AMF_OBJECTS[i].geometry.actor.actor.scale = (1,1,1) # Just a placeholder to assign the orignal height to the object
    
        if picker_outside:
            # The picker did not select an object belonging to our LIST_AMF_OBJECTS
            self.GUI_MATERIAL_ID = ""
            self.GUI_OBJECT_NAME = ""
            self.GUI_ID = "No Object Selected"
            self.GUI_MATERIAL_NAME = ""
            CURRENT_SELECTED_OBJECT = -1

          
    # When clicked, change the objects in the visualizer from wireframe to surface representation and vice-versa
    # TODO: No real purpose now but could be useful if we plan to apply material textures
    @on_trait_change('GUI_CHANGE_REPRESENTATION')
    def switchSurfaceWireframe(self):
        global LIST_AMF_OBJECTS
        # Update the rendering
        if self.GUI_CHANGE_REPRESENTATION:
            # Apply Surface
            for i in range(len(LIST_AMF_OBJECTS)):
                # Placeholder code to apply texture
                # LIST_AMF_OBJECTS[i].surface.actor.actor.property.representation = 'surface'
                # textureFile = tvtk.JPEGReader()
                # textureFile.file_name= TextureFolder +  str(LIST_AMF_OBJECTS[i].materialId) + ".jpg" #any jpeg file
                # wallTexture1 = tvtk.Texture(input_connection=textureFile.output_port, interpolate=0)
                # LIST_AMF_OBJECTS[i].surface.actor.enable_texture = True
                # LIST_AMF_OBJECTS[i].surface.actor.tcoord_generator_mode = 'plane'
                # LIST_AMF_OBJECTS[i].surface.actor.actor.texture = wallTexture1   
                LIST_AMF_OBJECTS[i].geometry.actor.actor.property.representation = 'surface'  
        else:
            # Apply Wireframe
            for i in range(len(LIST_AMF_OBJECTS)):
                LIST_AMF_OBJECTS[i].geometry.actor.actor.property.representation = 'wireframe'
                LIST_AMF_OBJECTS[i].geometry.actor.enable_texture = False

        # Update the rendering
        force_render()
        self.sceneView1.render()
        self.sceneView1.mayavi_scene.render() 


    # Handle new material assigmment 
    @on_trait_change('GUI_CHANGE_MATERIAL')
    def update_material_test(self):
            global CURRENT_SELECTED_OBJECT, LIST_AMF_OBJECTS, AMF_ROOT, AMF_TREE
            if CURRENT_SELECTED_OBJECT != -1:
                # Apply the new color corresponding to the newly material assigned to the selected object 
                dataset = mlab.pipeline.get_vtk_src(LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].geometry) # Get the dataset associated with the object
                currentScalar = dataset[0].point_data.scalars.to_array()   # Get the scalars, i.e, the material ID color
                newScalar = np.full_like(currentScalar,self.GUI_CHANGE_MATERIAL)  # Create the new scalar color
                LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].geometry.mlab_source.trait_set(scalars = newScalar)  # Apply the color to the object
                LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].geometry.actor.mapper.scalar_visibility = True
                LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].materialId = self.GUI_CHANGE_MATERIAL  # Update the object material ID

                # Update the GUI with the material Name and Material ID
                self.GUI_MATERIAL_ID = LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].materialId
                self.GUI_MATERIAL_NAME = DICT_MATERIAL[LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].materialId]

                # Update the AMF File of the selected object with the new material selected
                idObject = LIST_AMF_OBJECTS[CURRENT_SELECTED_OBJECT].xmlObjectID
                pathToUpdate = "./object/[@id=\""+idObject+"\"]/mesh/volume"
                volumesToUpdate = AMF_ROOT.findall(pathToUpdate) # Get all the volumes corresponding to the selected object
                for i in range(len(volumesToUpdate)):
                    volumesToUpdate[i].attrib["materialid"] = self.GUI_CHANGE_MATERIAL
                       
                # Save a new AMF file incuding the changes of Material
                amfFileToSave = AMF_SAVED_PREFIX + AMF_FILE
                amfFileToSave = str(Path(AMF_FOLDER) / amfFileToSave) 
                AMF_TREE.write(amfFileToSave)

            force_render()
            self.sceneView1.render()
            self.sceneView1.mayavi_scene.render()
             

    ################################################################
    ##########     INITIALIZE THE VISUALIZATION     ################
    ################################################################

    # Parse the AMF file and create the visualization 
    def __init__(self):
        global LIST_AMF_OBJECTS, AMF_TREE, AMF_ROOT, DICT_MATERIAL
        self.engine1.start()
             
        amfFileToParse = str(Path(AMF_FOLDER) / AMF_FILE) 
        try:
            AMF_TREE = ET.parse(amfFileToParse) 
        except OSError as e:
            print("Error:",e)
            exit()

        AMF_ROOT = AMF_TREE.getroot()
        objectsDict =  {} 
        # By default, we add a material with ID 0 that corresponds to the case where no material is assigned to a volume
        # Obviously, this choice imposes to use Material ID in the library with an ID greater than 0 TODO: Check if it's the case once we know how to manage the material library
        noMaterialID = "0"
        DICT_MATERIAL[noMaterialID] = "No Material"

        # Start by handling the material in the AMF file to build the material library
        for tMaterial in AMF_ROOT.iter('material'):
            # Iterate through all the material in the scenario
            materialID = tMaterial.attrib['id']
            for tName in tMaterial.iter('metadata'):
                materialName = tName.text # Get the material Name
                DICT_MATERIAL[materialID] = materialName # Add the material to the material dictionary
    

        # Handle the case where no Material exists in the AMF file - For example NISTGaithersburg.xml
        # Here is just a placeholder for the default material library
        # In this implementation, we will create a fake material made of 100 materials (completely arbitrary choice)
        if len(DICT_MATERIAL) == 1:
            # No Material defined 
            nbMaterial = 100
            for i in range(1,nbMaterial+1):
                DICT_MATERIAL[str(i)] = "FakematerialName" + str(i)

        for tObject in AMF_ROOT.iter('object'):
            # Iterate through all the objects in the AMF File
            coordinateX = []
            coordinateY = []
            coordinateZ = []
            DONOTADD = False
            xmlObjectID = tObject.attrib['id'] # Get the Object ID
            for tName in tObject.iter('metadata'):
                xmlObjectName = tName.text # Get the object Name
                # There is a bug in the way geodata scenario are generated
                # It includes twice every object so we handle that here 
                # TODO: Fix the geodata scenarios generation and update the code accordingly
                if xmlObjectName in objectsDict:
                    # If an object with the same name has already been parsed, flag it
                    DONOTADD = True
                else:
                    # The object does not exist in the object dictionnary, just add it to the objects dictionary
                    objectsDict[xmlObjectName] = True
                

            # Get the X, Y, Z coordinates corresponding to an object
            for tcoordinatesX in tObject.iter('x'):
                # Get x coordinates
                coordinateX.append(float(tcoordinatesX.text))
            for tcoordinatesY in tObject.iter('y'):
                # Get y coordinates
                coordinateY.append(float(tcoordinatesY.text))
            for tcoordinatesZ in tObject.iter('z'):
                # Get z coordinates
                coordinateZ.append(float(tcoordinatesZ.text))
          

            for tVolume in tObject.iter('volume'):
                # Iterate over the volume, i.e., the triangles connections and material
                # Please note that an object can be defined with more than one volume
                try:  
                    materialId = tVolume.attrib['materialid'] # Get the material ID associated to the triangles connections
                except KeyError:
                    # It's possible that a volume is not having any material assigned - Handle it
                    # print("Warning: Object :", xmlObjectName, " is not having any material associated to it") TODO Commented for now
                    materialId = None
                
                v1 = [] # First vertex
                v2 = [] # Second vertex
                v3 = [] # Third vertex
                for tTriangles in tVolume.iter('triangle'):
                    # Iterate over the triangles of a volume
                    for tFirstPoint in tTriangles.iter('v1'):
                        # Get First vertex
                        v1.append(int(tFirstPoint.text))
                    for tSecondPoint in tTriangles.iter('v2'):
                        # Get Second vertex
                        v2.append(int(tSecondPoint.text))
                    for tThirdPoint in tTriangles.iter('v3'):
                        # Get Third vertex
                        v3.append(int(tThirdPoint.text))
                  
                # Get the final triangles coordinates by connecting the vertices to their associated coordinates
                finalX = []
                finalY = []
                finalZ = []
                for index in range(len(v1)):
                    finalX.append([coordinateX[v1[index]],coordinateX[v2[index]],coordinateX[v3[index]]])
                    finalY.append([coordinateY[v1[index]],coordinateY[v2[index]],coordinateY[v3[index]]])
                    finalZ.append([coordinateZ[v1[index]],coordinateZ[v2[index]],coordinateZ[v3[index]]])

                # Create the triangles connections
                triangles = [(i*3, (i*3)+1, (i*3)+2 ) for i in range(0, len(finalX))]

                # Manage automatically the color of each volume depending on the material ID
                # The colormap is having 0:nbMaterial+1 possible values
                # We define a scalar that we associate with the volume
                if materialId == None:
                    # Assign the No Material ID in case no material was assigned to a volume
                    materialId = noMaterialID
                color = np.ones(np.asarray(finalX).shape)*int(materialId) 

              
                if DONOTADD == False:
                    # Add the volume to the visualization only it it was not added previously

                    # Create the volume to visualize
                    volume = mlab.triangular_mesh(finalX, finalY, finalZ,triangles,scalars = color, vmin=0, vmax=len(DICT_MATERIAL)-1, colormap = 'Spectral' ,   representation = 'wireframe', name = "volume:"+xmlObjectName,  figure = self.sceneView1.mayavi_scene,  reset_zoom = False)
                    volume.module_manager.scalar_lut_manager.lut.number_of_colors = 256
                   
                    # Create a label for each volume
                    labels = Labels()
                    vtk_data_source = volume
                    self.engine1.add_filter(labels, vtk_data_source)
                    labels.mapper.label_format = (xmlObjectName)
                    labels.number_of_labels = 1
                    labels.mask.filter.random_mode = False
    
                    # Store the objects 
                    currentObject = ObjectGeometry(xmlObjectID,xmlObjectName,volume,materialId)
                    LIST_AMF_OBJECTS.append(currentObject)
        
        # Present the Material ID library ordered in the GUI
        materialIDSorted = sorted(list(DICT_MATERIAL.keys()), key=int)
        self.GUI_MATERIAL_LIBRARY =materialIDSorted
        HasTraits.__init__(self)


    
    # GUI Definition
    view = View(             
        HSplit(
                
                Group(Item('sceneView1', editor=SceneEditor(scene_class=MayaviScene),
                           height=800, width=700, show_label=False, resizable=True),
                        # Group used to inspect the different objects of the scenario 
                        HGroup(Group(
                            Item(name = 'GUI_CHANGE_REPRESENTATION', label = 'Wireframe/Surface'),
                            Item(name = 'GUI_ID', label = 'ID',style='readonly'),
                            Item(name = 'GUI_OBJECT_NAME',label = 'Name',style='readonly'),
                            Item(name='GUI_MATERIAL_ID', label = 'Material ID',style='readonly'),
                            Item(name='GUI_MATERIAL_NAME', label = 'Material Name',style='readonly'),
                            label = 'Object Inspector',
                            show_border = True),     
                            #  visible_when='GUI_ID != "1"',          #TODO Can allow to hide or display the group       
                            ),
                        # Group used to edit the objects material (TODO: On-Hold as no convergence for the material ID library management)
                        HGroup(Group(
                            Item(name='GUI_CHANGE_MATERIAL', editor=CheckListEditor(name='GUI_MATERIAL_LIBRARY'),label ='Change Material'),                 
                             label = 'Object Editor',
                             show_border = True),        
                             )   
                      ),
                ),
                resizable=True,
                )

################################################################################
# The QWidget containing the visualization, this is pure PyQt4 code.
class MayaviQWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.visualization = Visualization()
        # If you want to debug, beware that you need to remove the Qt
        # input hook.
        # QtCore.pyqtRemoveInputHook()
        # import pdb ; pdb.set_trace()
        # QtCore.pyqtRestoreInputHook()

        # The edit_traits call will generate the widget to embed.
        self.ui = self.visualization.edit_traits(parent=self,
                                                 kind='subpanel').control
        layout.addWidget(self.ui)
        self.ui.setParent(self)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    # By default, we force the user to provide an AMF file to parse
    parser.add_argument('-f', action='store', dest='AMF_FILE',
                        help='The AMf file to parsse')
    argument = parser.parse_args()
    if argument.AMF_FILE  == None:
        print("Error: Please provide an AMF file to parse with the -f parameter")
        exit()
    else:  
        AMF_FILE =  argument.AMF_FILE 
 
    
    #####################################################
    #########          Qt Interface            ##########
    #####################################################
    # Don't create a new QApplication, it would unhook the Events
    # set by Traits on the existing QApplication. Simply use the
    # '.instance()' method to retrieve the existing one.
    app = QtGui.QApplication.instance()
    container = QtGui.QWidget()
    layout = QtGui.QGridLayout(container)
    mayavi_widget = MayaviQWidget(container)

    layout.addWidget(mayavi_widget, 0, 0)
    container.show()
    window = QtGui.QMainWindow()
    window.setCentralWidget(container)
    window.show()
    window.setWindowTitle("AMF scenario Visualizer")

    # Start the main event loop.
    app.exec_()