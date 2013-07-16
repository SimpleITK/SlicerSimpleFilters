import os,sys
import unittest
import SimpleITK as sitk
import sitkUtils
from __main__ import vtk, qt, ctk, slicer
from glob import glob
import json
from collections import OrderedDict
import re
import threading
import Queue
from time import sleep

#
# SimpleFilters
#

class SimpleFilters:

  # Use class-level scoped variable for module consants
  if not __file__.endswith("SimpleFilters.py"):
    import inspect
    __file__ = inspect.getframeinfo(inspect.currentframe())[0]

  ICON_DIR = os.path.dirname(os.path.realpath(__file__)) + '/Resources/Icons/'
  JSON_DIR = os.path.dirname(os.path.realpath(__file__)) + '/Resources/json/'


  def __init__(self, parent):
    parent.title = "Simple Filters"
    parent.categories = ["Filtering"]
    parent.dependencies = []
    parent.contributors = ["Bradley Lowekamp (MSC/NLM), Steve Pieper (Isomics), Jean-Christophe Fillion-Robin (Kitware)"]
    parent.helpText = """
    This is a meta module which contains interfaces for many Simple ITK image filters.
    """
    parent.acknowledgementText = """
This work could not have been done without the support of the Slicer Community, the Insight Consortium, or the Insight Toolkit."
""" # replace with organization, grant and thanks.
    self.parent = parent

    parent.icon = qt.QIcon("%s/ITK.png" % self.ICON_DIR)

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['SimpleFilters'] = self.runTest

  def runTest(self):
    tester = SimpleFiltersTest()
    tester.runTest()


#
# qSimpleFiltersWidget
#

class SimpleFiltersWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

    jsonFiles = glob(SimpleFilters.JSON_DIR+"*.json")
    jsonFiles.sort(cmp=lambda x,y: cmp(os.path.basename(x), os.path.basename(y)))

    self.jsonFilters = []

    for fname in jsonFiles:
      try:
        fp = file(fname, "r")
        j = json.load(fp,object_pairs_hook=OrderedDict)
        if j["name"] in dir(sitk):
          self.jsonFilters.append(j)
        else:
          import sys
          sys.stderr.write("Unknown SimpleITK class \"{0}\".\n".format(j["name"]))
      except Exception as e:
        import sys
        sys.stderr.write("Error while reading \"{0}\". Exception: {1}\n".format(fname, e))


    self.filterParameters = None


  def setup(self):
    # Instantiate and connect widgets ...

    #
    # Filters Area
    #
    filtersCollapsibleButton = ctk.ctkCollapsibleButton()
    filtersCollapsibleButton.text = "Filters"
    self.layout.addWidget(filtersCollapsibleButton)
    # Layout within the dummy collapsible button
    filtersFormLayout = qt.QFormLayout(filtersCollapsibleButton)

    # filter search
    self.searchBox = ctk.ctkSearchBox()
    filtersFormLayout.addRow("Search:", self.searchBox)
    self.searchBox.connect("textChanged(QString)", self.onSearch)

    # filter selector
    self.filterSelector = qt.QComboBox()
    filtersFormLayout.addRow("Filter:", self.filterSelector)

    # add all the filters listed in the json files
    for idx,j in enumerate(self.jsonFilters):
      name = j["name"]
      self.filterSelector.addItem(name, idx)

    # connections
    self.filterSelector.connect('currentIndexChanged(int)', self.onFilterSelect)


    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    self.filterParameters = FilterParameters(parametersCollapsibleButton)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = True
    self.layout.addWidget(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)

    # Add vertical spacer
    self.layout.addStretch(1)


    statusLabel = qt.QLabel("Status: ")
    self.currentStatusLabel = qt.QLabel("Idle")
    hlayout = qt.QHBoxLayout()
    hlayout.addStretch(1)
    hlayout.addWidget(statusLabel)
    hlayout.addWidget(self.currentStatusLabel)
    self.layout.addLayout(hlayout)



    # Initlial Selection
    self.filterSelector.currentIndexChanged(self.filterSelector.currentIndex)

  def onSearch(self, searchText):
    # add all the filters listed in the json files
    self.filterSelector.clear()
    # split text on whitespace of and string search
    searchTextList = searchText.split()
    for idx,j in enumerate(self.jsonFilters):
      lname = j["name"].lower()
      # require all elements in list, to add to select. case insensitive
      if  reduce(lambda x, y: x and (lname.find(y.lower())!=-1), [True]+searchTextList):
        self.filterSelector.addItem(j["name"],idx)


  def onFilterSelect(self, selectorIndex):
    self.filterParameters.destroy()
    if selectorIndex < 0:
      return
    jsonIndex= self.filterSelector.itemData(selectorIndex)
    json = self.jsonFilters[jsonIndex]
    self.filterParameters.create(json)

    if "briefdescription" in self.jsonFilters[jsonIndex]:
      tip=self.jsonFilters[jsonIndex]["briefdescription"]
      tip=tip.rstrip()
      self.filterSelector.setToolTip(tip)
    else:
      self.filterSelector.setToolTip("")

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = True

  def onApplyButton(self):
    self.filterParameters.prerun()

    logic = SimpleFiltersLogic()

    print self.filterParameters.filter

    self.onLogicRunStart()

    try:

      logic.run(self.filterParameters.filter, self.filterParameters.output, *self.filterParameters.inputs)

    except:
      # if there was an exception during start-up make sure to finish
      self.onLogicRunFinished()
      raise

  def onLogicRunStart(self):
    self.applyButton.setDisabled(True)
    self.currentStatusLabel.text = "Running"

  def onLogicRunFinished(self):
    self.applyButton.setDisabled(False)
    self.currentStatusLabel.text = "Idle"


#
# SimpleFiltersLogic
#

class SimpleFiltersLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    self.main_queue = Queue.Queue()
    self.main_queue_running = False
    self.thread = threading.Thread()

  def __del__(self):
    if self.main_queue_running:
      self.main_queue_stop

  def thread_doit(self,filter,*inputImages):
    try:
      img = filter.Execute(*inputImages)
      self.main_queue.put(lambda img=img:self.updateOutput(img))
    except Exception as e:
      msg = e.message
      self.main_queue.put(lambda :qt.QMessageBox.critical(slicer.util.mainWindow(),
                                                          "Exception durring execution of{0}".format(filter.GetName()),
                                                          msg))
    finally:
      self.main_queue.put(self.main_queue_stop)

  def main_queue_start(self):
    """Begins monitoring of main_queue for callables"""
    self.main_queue_running = True
    qt.QTimer.singleShot(10, self.main_queue_process)

  def main_queue_stop(self):
    """End monitoring of main_queue for callables"""
    self.main_queue_running = False
    print "Stopping queue process"
    slicer.modules.SimpleFiltersWidget.onLogicRunFinished()

  def main_queue_process(self):
    """processes the main_queue of callables"""
    try:
      # this sleep is needed to allow the other thread to aquire the GIL and resume executing

      while not self.main_queue.empty():
        sleep(0)
        f = self.main_queue.get_nowait()
        if callable(f):
          f()

      sleep(0)
      if self.main_queue_running:
        qt.QTimer.singleShot(10, self.main_queue_process)

    except Exception as e:
      print e

  def updateOutput(self,img):

    nodeWriteAddress=sitkUtils.GetSlicerITKReadWriteAddress(self.outputNodeName)
    sitk.WriteImage(img,nodeWriteAddress)

    node = slicer.util.getNode(self.outputNodeName)

    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID( node.GetID() )
    slicer.app.applicationLogic().PropagateVolumeSelection(0)

  def run(self, filter, outputMRMLNode, *inputs):
    """
    Run the actual algorithm
    """

    if self.thread.is_alive():
      print "already executing"
      return

    inputImages = []

    # ensure everything is updated, redawn etc before we begin processing
    qt.QApplication.flush()

    for i in inputs:
      imgNodeName = i.GetName()
      img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(imgNodeName) )
      inputImages.append(img)

    self.output = None
    self.outputNodeName = outputMRMLNode.GetName()

    self.thread = threading.Thread( target=lambda f=filter,i=inputImages:self.thread_doit(f,*inputImages))

    self.main_queue_start()
    self.thread.start()

#
# Class to manage parameters
#

class FilterParameters(object):
  """ This class is for managing the widgets for the parameters for a filter
  """

  def __init__(self, parent=None):
    self.parent = parent
    self.widgets = []
    self.json = json
    self.filter = None
    self.inputs = []
    self.output = None
    self.prerun_callbacks = []

  def __del__(self):
    self.destroy()

  def BeautifyCamelCase(self, str):
    reCamelCase = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    return reCamelCase.sub(r' \1',str)

  def create(self, json):
    if not self.parent:
      raise "no parent"

    parametersFormLayout = self.parent.layout()

    # You can't use exec in a function that has a subfunction, unless you specify a context.
    exec( 'self.filter = sitk.{0}()'.format(json["name"]))  in globals(), locals()

    self.prerun_callbacks = []
    self.inputs = []

    #
    # input volume selectors
    #
    for n in range(json["number_of_inputs"]):

      w = self.createInputWidget(n)

      inputSelectorLabel = qt.QLabel("Input Volume: ")
      self.widgets.append(inputSelectorLabel)

      # add to layout after connection
      parametersFormLayout.addRow(inputSelectorLabel, w)

      self.inputs.append(w.currentNode())

    #end for each input

    if json["template_code_filename"] == "KernelImageFilter":
      w = self.createVectorWidget("KernelRadius","std::vector<uint32_t>")
      self.widgets.append(w)
      self.addWidgetWithToolTipAndLabel(w,{"briefdescriptionSet":"Radius of structuring element","name":"KernelRadius"})

      labels=["Annulus","Box","Ball","Cross"]
      w = self.createEnumWidget("KernelType",labels)
      self.addWidgetWithToolTipAndLabel(w,{"briefdescriptionSet":"Structuring element","name":"Kernel Type"})

    elif json["template_code_filename"] == "RegionGrowingImageFilter"\
          or json["template_code_filename"] == "FastMarchingImageFilter":

      name="SeedList"
      if (json["template_code_filename"] == "FastMarchingImageFilter"):
        name="TrialPoints"

      fiducialSelector = slicer.qMRMLNodeComboBox()
      self.widgets.append(fiducialSelector)
      fiducialSelector.nodeTypes = ( ("vtkMRMLAnnotationHierarchyNode"), "" )
      fiducialSelector.addAttribute("vtkMRMLAnnotationHierarchyNode", "MainChildType", "vtkMRMLAnnotationFiducialNode" )
      fiducialSelector.selectNodeUponCreation = True
      fiducialSelector.addEnabled = True
      fiducialSelector.removeEnabled = False
      fiducialSelector.renameEnabled = True
      fiducialSelector.noneEnabled = False
      fiducialSelector.showHidden = False
      fiducialSelector.showChildNodeTypes = True
      fiducialSelector.setMRMLScene( slicer.mrmlScene )
      fiducialSelector.setToolTip( "Pick the Fiducial node for the seed list." )

      fiducialSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node,name=name:self.onFiducialListNode(name,node))
      self.prerun_callbacks.append(lambda w=fiducialSelector,name=name:self.onFiducialListNode(name,w.currentNode()))

      fiducialSelectorLabel = qt.QLabel("{0}: ".format(name))
      self.widgets.append(fiducialSelectorLabel)

      #todo set tool tip
      # add to layout after connection
      parametersFormLayout.addRow(fiducialSelectorLabel, fiducialSelector)


    for member in json["members"]:
      w = None
      if "type" in member:
        t = member["type"]

      if "dim_vec" in member and int(member["dim_vec"]):
        if member["itk_type"].endswith("IndexType") or member["itk_type"].endswith("PointType"):
          isPoint = member["itk_type"].endswith("PointType")

          fiducialSelector = slicer.qMRMLNodeComboBox()
          self.widgets.append(fiducialSelector)
          fiducialSelector.nodeTypes = ( ("vtkMRMLAnnotationFiducialNode"), "" )
          fiducialSelector.selectNodeUponCreation = True
          fiducialSelector.addEnabled = False
          fiducialSelector.removeEnabled = False
          fiducialSelector.renameEnabled = True
          fiducialSelector.noneEnabled = False
          fiducialSelector.showHidden = False
          fiducialSelector.showChildNodeTypes = True
          fiducialSelector.setMRMLScene( slicer.mrmlScene )
          fiducialSelector.setToolTip( "Pick the Fiducial for the Point or Index" )

          fiducialSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node,w=fiducialSelector,name=member["name"],isPt=isPoint:self.onFiducialNode(name,w,isPt))
          self.prerun_callbacks.append(lambda w=fiducialSelector,name=member["name"],isPt=isPoint:self.onFiducialNode(name,w,isPt))

          w1 = fiducialSelector

          fiducialSelectorLabel = qt.QLabel("{0}: ".format(member["name"]))
          self.widgets.append(fiducialSelectorLabel)

          icon = qt.QIcon(SimpleFilters.ICON_DIR+"Fiducials.png")

          toggle = qt.QPushButton(icon, "")
          toggle.setCheckable(True)
          toggle.toolTip = "Toggle Fiducial Selection"
          self.widgets.append(toggle)

          w2 = self.createVectorWidget(member["name"],t)

          hlayout = qt.QHBoxLayout()
          hlayout.addWidget(fiducialSelector)
          hlayout.setStretchFactor(fiducialSelector,1)
          hlayout.addWidget(w2)
          hlayout.setStretchFactor(w2,1)
          hlayout.addWidget(toggle)
          hlayout.setStretchFactor(toggle,0)
          w1.hide()

          self.widgets.append(hlayout)

          toggle.connect("clicked(bool)", lambda checked,ptW=w2,fidW=w1:self.onToggledPointSelector(checked,ptW,fidW))

          parametersFormLayout.addRow(fiducialSelectorLabel, hlayout)

        else:
          w = self.createVectorWidget(member["name"],t)
      elif "enum" in member:
        w = self.createEnumWidget(member["name"],member["enum"])
      elif t == "InterpolatorEnum":
        labels=["Nearest Neighbor",
                "Linear",
                "BSpline",
                "Gaussian",
                "Label Gaussian",
                "Hamming Windowed Sinc",
                "Cosine Windowed Sinc",
                "Welch Windowed Sinc",
                "Lanczos Windowed Sinc",
                "Blackman Windowed Sinc"]
        values=["sitk.sitkNearestNeighbor",
                "sitk.sitkLinear",
                "sitk.sitkBSpline",
                "sitk.sitkGaussian",
                "sitk.sitkLabelGaussian",
                "sitk.sitkHammingWindowedSinc",
                "sitk.sitkCosineWindowedSinc",
                "sitk.sitkWelchWindowedSinc",
                "sitk.sitkLanczosWindowedSinc",
                "sitk.sitkBlackmanWindowedSinc"]

        w = self.createEnumWidget(member["name"],labels,values)
        pass
      elif t == "PixelIDValueEnum":
        labels=["int8_t",
                "uint8_t",
                "int16_t",
                "uint16_t",
                "uint32_t",
                "int32_t",
                "float",
                "double"]
        values=["sitk.sitkInt8",
                "sitk.sitkUInt8",
                "sitk.sitkInt16",
                "sitk.sitkUInt16",
                "sitk.sitkInt32",
                "sitk.sitkUInt32",
                "sitk.sitkFloat32",
                "sitk.sitkFloat64"]
        w = self.createEnumWidget(member["name"],labels,values)
      elif t in ["double", "float"]:
        w = self.createDoubleWidget(member["name"])
      elif t == "bool":
        w = self.createBoolWidget(member["name"])
      elif t in ["uint8_t", "int8_t",
               "uint16_t", "int16_t",
               "uint32_t", "int32_t",
               "uint64_t", "int64_t",
               "unsigned int", "int"]:
        w = self.createIntWidget(member["name"],t)
      else:
        import sys
        sys.stderr.write("Unknown member \"{0}\" of type \"{1}\"\n".format(member["name"],member["type"]))

      if w:
        self.addWidgetWithToolTipAndLabel(w,member)


    # end for each member

    #
    # output volume selector
    #
    outputSelector = slicer.qMRMLNodeComboBox()
    self.widgets.append(outputSelector)
    outputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    outputSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    outputSelector.selectNodeUponCreation = True
    outputSelector.addEnabled = True
    outputSelector.removeEnabled = False
    outputSelector.renameEnabled = True
    outputSelector.noneEnabled = False
    outputSelector.showHidden = False
    outputSelector.showChildNodeTypes = False
    outputSelector.baseName = json["name"]+" Output"
    outputSelector.setMRMLScene( slicer.mrmlScene )
    outputSelector.setToolTip( "Pick the output to the algorithm." )

    outputSelectorLabel = qt.QLabel("Output Volume: ")
    self.widgets.append(outputSelectorLabel)

    outputSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node:self.onOutputSelect(node))

    # add to layout after connection
    parametersFormLayout.addRow(outputSelectorLabel, outputSelector)

    self.output = outputSelector.currentNode()

  def createInputWidget(self,n):
      inputSelector = slicer.qMRMLNodeComboBox()
      self.widgets.append(inputSelector)
      inputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      inputSelector.selectNodeUponCreation = True
      inputSelector.addEnabled = False
      inputSelector.removeEnabled = False
      inputSelector.noneEnabled = False
      inputSelector.showHidden = False
      inputSelector.showChildNodeTypes = False
      inputSelector.setMRMLScene( slicer.mrmlScene )
      inputSelector.setToolTip( "Pick the input to the algorithm." )

      # connect and verify parameters
      inputSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node,i=n:self.onInputSelect(node,i))
      return inputSelector

  def createEnumWidget(self,name,enumList,valueList=None):

    w = qt.QComboBox()
    self.widgets.append(w)

    exec 'default=self.filter.Get{0}()'.format(name) in globals(), locals()

    if valueList is None:
      valueList = ["self.filter."+e for e in enumList]

    for e,v in zip(enumList,valueList):
      w.addItem(e,v)

      # check if current item is default, set if it is
      exec 'itemValue='+v  in globals(), locals()
      if itemValue  == default:
        w.setCurrentIndex(w.count-1)

    w.connect("currentIndexChanged(int)", lambda selectorIndex,n=name,selector=w:self.onEnumChanged(n,selectorIndex,selector))
    return w

  def createVectorWidget(self,name,type):
    m = re.search(r"<([a-zA-Z ]+)>", type)
    if m:
      type = m.group(1)

    w = ctk.ctkCoordinatesWidget()
    self.widgets.append(w)

    if type in ["double", "float"]:
      w.setDecimals(5)
      w.minimum=-3.40282e+038
      w.maximum=3.40282e+038
      w.connect("coordinatesChanged(double*)", lambda val,widget=w,name=name:self.onFloatVectorChanged(name,widget,val))
    else:
      w.setDecimals(0)
      w.connect("coordinatesChanged(double*)", lambda val,widget=w,name=name:self.onIntVectorChanged(name,widget,val))

    exec('default = self.filter.Get{0}()'.format(name)) in globals(), locals()
    w.coordinates = ",".join(str(x) for x in default)
    return w

  def createIntWidget(self,name,type="int"):

    w = qt.QSpinBox()
    self.widgets.append(w)

    if type=="uint8_t":
      w.setRange(0,255)
    elif type=="int8_t":
      w.setRange(-128,127)
    elif type=="uint16_t":
      w.setRange(0,65535)
    elif type=="int16_t":
      w.setRange(-32678,32767)
    elif type=="uint32_t" or  type=="uint64_t" or type=="unsigned int":
      w.setRange(0,2147483647)
    elif type=="int32_t" or  type=="uint64_t" or type=="int":
      w.setRange(-2147483648,2147483647)

    exec('default = self.filter.Get{0}()'.format(name)) in globals(), locals()
    w.setValue(int(default))
    w.connect("valueChanged(int)", lambda val,name=name:self.onScalarChanged(name,val))
    return w

  def createBoolWidget(self,name):
    exec('default = self.filter.Get{0}()'.format(name)) in globals(), locals()
    w = qt.QCheckBox()
    self.widgets.append(w)

    w.setChecked(default)

    w.connect("stateChanged(int)", lambda val,name=name:self.onScalarChanged(name,bool(val)))

    return w

  def createDoubleWidget(self,name):
    exec('default = self.filter.Get{0}()'.format(name)) in globals(), locals()
    w = qt.QDoubleSpinBox()
    self.widgets.append(w)

    w.setRange(-3.40282e+038, 3.40282e+038)
    w.decimals = 5

    w.setValue(default)
    w.connect("valueChanged(double)", lambda val,name=name:self.onScalarChanged(name,val))

    return w

  def addWidgetWithToolTipAndLabel(self,widget,memberJSON):
    tip=""
    if "briefdescriptionSet" in memberJSON and len(memberJSON["briefdescriptionSet"]):
      tip=memberJSON["briefdescriptionSet"]
    elif "detaileddescriptionSet" in memberJSON:
      tip=memberJSON["detaileddescriptionSet"]

    # remove trailing white space
    tip=tip.rstrip()

    l = qt.QLabel(self.BeautifyCamelCase(memberJSON["name"])+": ")
    self.widgets.append(l)

    widget.setToolTip(tip)
    l.setToolTip(tip)

    parametersFormLayout = self.parent.layout()
    parametersFormLayout.addRow(l,widget)

  def onToggledPointSelector(self, fidVisible, ptWidget, fiducialWidget):
    ptWidget.setVisible(False)
    fiducialWidget.setVisible(False)

    ptWidget.setVisible(not fidVisible)
    fiducialWidget.setVisible(fidVisible)

    if ptWidget.visible:
      # Update the coordinate values to envoke the changed signal.
      # This will update the filter from the widget
      ptWidget.coordinates = ",".join(str(x) for x in ptWidget.coordinates.split(',') )

  def onInputSelect(self, mrmlNode, n):
    self.inputs[n] = mrmlNode

    if n == 0 and self.inputs[0]:
        imgNodeName = self.inputs[0].GetName()
        img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(imgNodeName) )

  def onPrimaryInputSelect(self, img):
    pass

  def onOutputSelect(self, mrmlNode):
    self.output = mrmlNode

  def onFiducialNode(self, name, mrmlWidget, isPoint):
    if not mrmlWidget.visible:
      return
    annotationFiducialNode = mrmlWidget.currentNode()

    # point in physical space
    coord = [0,0,0]
    annotationFiducialNode.GetFiducialCoordinates(coord)

    # HACK transform from RAS to LPS
    coord = [-coord[0],-coord[1],coord[2]]

    if not isPoint and len(self.inputs) and self.inputs[0]:
      imgNodeName = self.inputs[0].GetName()
      img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(imgNodeName) )
      coord = img.TransformPhysicalPointToIndex(coord)
    exec('self.filter.Set{0}(coord)'.format(name))

  def onFiducialListNode(self, name, mrmlNode):
    annotationHierarchyNode = mrmlNode

    # list of points in physical space
    coords = []

    # get the first in the list
    for listIndex in range(annotationHierarchyNode.GetNumberOfChildrenNodes()):
      if annotationHierarchyNode.GetNthChildNode(listIndex) is None:
        continue

      annotation = annotationHierarchyNode.GetNthChildNode(listIndex).GetAssociatedNode()
      if annotation is None:
        continue

      coord = [0,0,0]
      annotation.GetFiducialCoordinates(coord)
      coords.append(coord)

    if self.inputs[0]:
      imgNodeName = self.inputs[0].GetName()
      img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(imgNodeName) )

      # HACK transform from RAS to LPS
      coords = [ [-pt[0],-pt[1],pt[2]] for pt in coords]

      idx_coords = [img.TransformPhysicalPointToIndex(pt) for pt in coords]

      exec('self.filter.Set{0}(idx_coords)'.format(name))

  def onScalarChanged(self, name, val):
    exec('self.filter.Set{0}(val)'.format(name))

  def onEnumChanged(self, name, selectorIndex, selector):
    data=selector.itemData(selectorIndex)
    exec('self.filter.Set{0}({1})'.format(name,data))

  def onIntVectorChanged(self, name, widget, val):
    coords = [int(x) for x in widget.coordinates.split(',')]
    exec('self.filter.Set{0}(coords)'.format(name))

  def onFloatVectorChanged(self, name, widget, val):
    coords = [float(x) for x in widget.coordinates.split(',')]
    exec('self.filter.Set{0}(coords)'.format(name))


  def prerun(self):
    for f in self.prerun_callbacks:
      f()

  def destroy(self):

    for w in self.widgets:
      #self.parent.layout().removeWidget(w)
      w.deleteLater()
      w.setParent(None)
    self.widgets = []
