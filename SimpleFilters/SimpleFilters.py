import os
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
  def __init__(self, parent):
    parent.title = "SimpleFilters" # TODO make this more human readable by adding spaces
    parent.categories = ["Filtering"]
    parent.dependencies = []
    parent.contributors = ["Bradley Lowekamp (MSC/NLM)"] 
    parent.helpText = """
    This is a meta module which contains interfaces for many Simple ITK image filters.
    """
    parent.acknowledgementText = """
""" # replace with organization, grant and thanks.
    self.parent = parent

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

    pathToJSON = os.path.dirname(os.path.realpath(__file__)) + '/Resources/json/'
    print("pathToJSON: ",pathToJSON)
    print(__file__)
    jsonFiles = glob(pathToJSON+"*.json")

    self.jsonFilters = []
  
    for fname in jsonFiles:
      try:
        fp = file(fname, "r")
        j = json.load(fp,object_pairs_hook=OrderedDict)
        self.jsonFilters.append(j)
      except:
        print "Error while reading $1", fname
    
    self.filterParameters = None
    

  def setup(self):
    # Instantiate and connect widgets ...

    print "Calling setup..."

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "SimpleFilters Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    
    #
    # filter selector
    # 
    self.filterSelector = qt.QComboBox()
    self.layout.addWidget(self.filterSelector)
    
    # add all the filters listed in the json files
    for j in self.jsonFilters:
      name = j["name"]
      # TODO: make the name pretty
      self.filterSelector.addItem(name)

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

  def onFilterSelect(self, jsonIndex):
    json = self.jsonFilters[jsonIndex]
    print json

    self.filterParameters.destroy()
    self.filterParameters.create(json)

  def cleanup(self):
    pass

  def onSelect(self):
    #TODO figure out when to enable
    self.applyButton.enabled = True

  def onApplyButton(self):
    logic = SimpleFiltersLogic()
    print("Run the algorithm")

    inputImages = []

    for i in self.filterParameters.inputs:
      imgNodeName = i.GetName()
      img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(imgNodeName) )
      inputImages.append(img)

    img = self.filterParameters.filter.Execute(*inputImages)
    
    imgNodeName = self.filterParameters.output.GetName()
    sitkUtils.PushToSlicer(img, imgNodeName, overwrite=True)

    print("done")

  def onReload(self,moduleName="SimpleFilters"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)

    # delete the old widget instance
    if hasattr(globals()['slicer'].modules, widgetName):
      getattr(globals()['slicer'].modules, widgetName).cleanup()

    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()
    setattr(globals()['slicer'].modules, widgetName, globals()[widgetName.lower()])

  def onReloadAndTest(self,moduleName="SimpleFilters"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")


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


  def hasImageData(self,volumeNode):
    """This is a dummy logic method that 
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def thread_doit(self):
    try:
      self.main_queue.put(lambda:self.main_queue_stop)
    except Exception as e:
      print "Exception:", e
      self.main_queue.put(lambda:self.main_queue_stop)

  def main_queue_start(self):
    """Begins monitoring of main_queue for callables"""
    self.main_queue_running = True
    qt.QTimer.singleShot(10, self.main_queue_process)

  def main_queue_stop(self):
    """Begins monitoring of main_queue for callables"""
    self.main_queue_running = False
    print "Stopping queue process"

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

  def run(self, *args):
    """
    Run the actual algorithm
    """
    
    if self.thread.is_alive():
      print "already executing"
      return

    
    self.thread = threading.Thread( target=lambda:self.thread_doit())
    self.thread.start()

    self.main_queue_start()
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

  def __del__(self):
    self.destroy()

  def create(self, json):
    if not self.parent:
      raise "no parent"

    self.frame = qt.QFrame(self.parent)
    #self.parent.layout().addWidget(self.frame)
    self.widgets.append(self.frame)

    parametersFormLayout = self.parent.layout()

    # You can't use exec in a function that has a subfunction, unless you specify a context.
    exec( 'self.filter = sitk.{0}()'.format(json["name"]))  in globals(), locals()

    #
    # input volume selectors
    #
    self.inputs = []
    for n in range(json["number_of_inputs"]):
      inputSelector = slicer.qMRMLNodeComboBox()
      self.widgets.append(inputSelector)
      inputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      inputSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
      inputSelector.selectNodeUponCreation = True
      inputSelector.addEnabled = False
      inputSelector.removeEnabled = False
      inputSelector.noneEnabled = False
      inputSelector.showHidden = False
      inputSelector.showChildNodeTypes = False
      inputSelector.setMRMLScene( slicer.mrmlScene )
      inputSelector.setToolTip( "Pick the input to the algorithm." )

      inputSelectorLabel = qt.QLabel("Input Volume: ")
      self.widgets.append(inputSelectorLabel)

      # connect and verify parameters
      inputSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node,i=n:self.onInputSelect(node,i))

      
      # add to layout after connection
      parametersFormLayout.addRow(inputSelectorLabel, inputSelector)

      self.inputs.append(inputSelector.currentNode())

    for member in json["members"]:
      t = member["type"]
    
      if "dim_vec" in member and int(member["dim_vec"]):
        m = re.search(r"<([a-zA-Z ]+)>", t)
        if m:
          t = m.group(1)
            
#        if t in ["double", "float"]:
        w = ctk.ctkCoordinatesWidget()
        self.widgets.append(w)
        
        print(help(w.setCoordinates))

        exec('w.setCoordinates(*self.filter.Get{0}())'.format(member["name"]))  in globals(), locals()
        
        print dir(w)
        print type(w.coordinates)
        print w.coordinates
          
        # TODO for default
            
      elif t in ["double", "float"]:
        w = qt.QDoubleSpinBox()
        self.widgets.append(w)

        v = str(member["default"])
        if v[-1] == 'f':
          v = v[:-1]
        w.setValue(float(v))
        w.connect("valueChanged(double)", lambda val,name=member["name"]:self.onScalarChanged(name,val))

      elif t == "bool":
        w = qt.QCheckBox()
        self.widgets.append(w)

        if member["default"].lower != "true":
          w.setChecked(False)
        w.connect("stateChanged(int)", lambda val,name=member["name"]:self.onScalarChanged(name,bool(val)))

      elif t in ["uint8_t", "int8_t",
               "uint16_t", "int16_t",
               "uint32_t", "int32_t",
               "uint64_t", "int64_t",
               "unsigned int", "int"]:
        
        w = qt.QSpinBox()
        self.widgets.append(w)

        v = str(member["default"])
        if v[-1] == 'u':
          v = v[:-1]
        w.setValue(int(v))
        w.connect("valueChanged(int)", lambda val,name=member["name"]:self.onScalarChanged(name,val))

      else:
        continue

      if "briefdescriptionSet" in member and len(member["briefdescriptionSet"]):
        w.setToolTip(member["briefdescriptionSet"])
      elif "detaileddescriptionSet" in member:
        w.setToolTip(member["detaileddescriptionSet"])

      l = qt.QLabel(member["name"]+": ")
      self.widgets.append(l)

      parametersFormLayout.addRow(l,w)


    #
    # output volume selector
    #
    outputSelector = slicer.qMRMLNodeComboBox()
    self.widgets.append(outputSelector)
    outputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    outputSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    outputSelector.selectNodeUponCreation = False
    outputSelector.addEnabled = True
    outputSelector.removeEnabled = True
    outputSelector.noneEnabled = False
    outputSelector.showHidden = False
    outputSelector.showChildNodeTypes = False
    outputSelector.setMRMLScene( slicer.mrmlScene )
    outputSelector.setToolTip( "Pick the output to the algorithm." )

    outputSelectorLabel = qt.QLabel("Output Volume: ")
    self.widgets.append(outputSelectorLabel)

    outputSelector.connect("nodeActivated(vtkMRMLNode*)", lambda node:self.onOutputSelect(node))

    # add to layout after connection
    parametersFormLayout.addRow(outputSelectorLabel, outputSelector)

    
    self.output = outputSelector.currentNode()


  def onInputSelect(self, mrmlNode, n):
    self.inputs[n] = mrmlNode
    print "onInputSelect"
    print self.filter

  def onOutputSelect(self, mrmlNode):
    self.output = mrmlNode
    print "onOutputSelect"
    print self.filter

  def onScalarChanged(self, name, val):
    exec( 'self.filter.Set{0}(val)'.format(name)) in globals(), locals()
    print "onScalarChanged"
    print self.filter

  def destroy(self):
    for w in self.widgets:
      self.parent.layout().removeWidget(w)
      w.deleteLater()
      w.setParent(None)
    self.widgets = []
  

class SimpleFiltersTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SimpleFilters1()

  def test_SimpleFilters1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        print('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        print('Loading %s...\n' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading\n')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = SimpleFiltersLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
