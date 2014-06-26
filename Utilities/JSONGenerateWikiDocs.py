#!/usr/bin/env python
#
# JSONGenerateWikiDocs.py
#
# This scripts read in the SimpleITK JSON descriptions of filters, and
# the text output produces if for inclusion in a Wiki for
# documentation.
#
# Usage: Utilities/JSONGenerateWikiDocs.py SimpleFilters/Resources/json/*.json
#

import json
import sys
try:
    from collections import OrderedDict
except ImportError:
    import ordereddict as OrderedDict

# This script takes one argument the name of a json file.
#

print """{| border="1" style="border-collapse:collapse;"
|-
! Filter Name
! Brief Description
! ITK Class"""

entryFormat = "|-\n! {0}\n! {1}\n! [http://www.itk.org/Doxygen/html/classitk_1_1{2}.html {2}]"
for fname in sys.argv[1:]:

    with file( fname, "r" ) as fp:
        j = json.load( fp,object_pairs_hook=OrderedDict )


    jsonName = j["name"]

    if "briefdescription" in j:
        jsonBrief = j["briefdescription"]
    else:
        jsonBrief = ""

    if "itk_name" in j:
        jsonITK = j["itk_name"]
    elif "filter_type" in j:
        filter_type = j["filter_type"]
        if filter_type.startswith("itk::"):
            filter_type = filter_type[len("itk::"):]
        i=filter_type.find('<')
        if (i)!=-1:
            filter_type=filter_type[:i]
        jsonITK = filter_type
    else:
        jsonITK = jsonName

    print entryFormat.format(jsonName, jsonBrief, jsonITK)

print "|}"
