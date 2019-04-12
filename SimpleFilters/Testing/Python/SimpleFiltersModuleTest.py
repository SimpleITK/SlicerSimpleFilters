from __future__ import print_function
import unittest
import qt
import slicer

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

    # make sure all events are processed before moving on
    qt.QApplication.flush()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def test_SimpleFilters1(self):

    m = slicer.util.mainWindow()
    m.moduleSelector().selectModule('SimpleFilters')

    print("testing my test....")

    testWidget = slicer.modules.SimpleFiltersWidget

    # Run through all the loaded filters and get the widget to generate the GUI
    for filterIdx in range(testWidget.filterSelector.count):
      someJSON=slicer.modules.SimpleFiltersWidget.jsonFilters[filterIdx]
      testWidget.filterSelector.setCurrentIndex(filterIdx)
      self.delayDisplay("Testing filter \"{0}\" ({1} of {2}).".format(someJSON["name"], filterIdx, testWidget.filterSelector.count),msec=100 )

    return True
