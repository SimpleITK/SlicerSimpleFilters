#-----------------------------------------------------------------------------
set(MODULE_NAME SimpleFilters)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

file(GLOB SimpleFilters_JSON RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}" "Resources/json/*.json")
set(MODULE_PYTHON_RESOURCES
  "Resources/Icons/ITK.png"
  "Resources/Icons/Fiducials.png"
  ${SimpleFilters_JSON}
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()

