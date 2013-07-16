cmake_minimum_required(VERSION 2.8.9)

project(SimpleFilters)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/SimpleFilters")
set(EXTENSION_CATEGORY "Filtering")
set(EXTENSION_CONTRIBUTORS "Bradley Lowekamp (MSC/NLM), Steve Pieper (Isomics), Jean-Christophe Fillion-Robin (Kitware)" )
set(EXTENSION_DESCRIPTION "This is a meta module which contains interfaces for many Simple ITK image filters.")
set(EXTENSION_ICONURL "http://viewvc.slicer.org/viewvc.cgi/Slicer4/trunk/Extensions/Testing/SimpleFilters/SimpleFilters.png?revision=21747&view=co")
set(EXTENSION_SCREENSHOTURLS "http://wiki.slicer.org/slicerWiki/images/e/e2/Slicer-r19441-SimpleFilters-screenshot.png")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(SimpleFilters)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
