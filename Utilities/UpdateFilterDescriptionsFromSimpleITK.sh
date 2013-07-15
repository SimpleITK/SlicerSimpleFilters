#!/bin/bash
#
# UpdateFilterDescriptionsFromSimpleITK.sh
#
# This file gives the commands needed to merge upstream changes
# from the SimpleITK repository for the BasicFilters Json description.
#
# It is based on work by Brad King used to update VNL third party
# module [1] and the work by Kent Williams to update DoubleConversion third
# party module [2] in ITK.
#
# [1] Modules/ThirdParty/VNL/src/README-ITK.txt
# [2] Modules/ThirdParty/DoubleConversion/src/UpdateDoubleConversionFromGoogle.sh
#
echo "-------------------------------------------------------"
echo This script will update the SimpleITK filter descriptions
echo from http://itk.org/SimpleITK.git
echo "-------------------------------------------------------"
if [ ! -f UpdateFilterDescriptionsFromSimpleITK.sh ]
then
    echo The current working directory $(pwd) is not the top level
    echo of the SimpleFiltersDescriptions source code tree. Please change
    echo to the SimpleFiltersDescriptions source directory and re-run 
    echo this script
    exit 1
fi
#
# Once the merge has been done
# EDIT THIS SCRIPT to change the hash tag at which to begin the
# next update...
#
git branch sitk-upstream UPDATE-HERE

#
# Make a temp directory to handle the import of the upstream source
mkdir sitk-tmp
cd sitk-tmp
#
# base a temporary git repo off of the parent SimpleFiltersDescriptions directory
git init
#
# pull in the upstream branch
git pull .. sitk-upstream
#
# empty out all existing source
rm -rf *
#
# download and copy the necessary double-conversion source
echo Cloning upstream HEAD from http://itk.org/SimpleITK.git
echo NOTE: to check out a particular revision for merging
echo you have to add a git checkout '<hash>'
echo or git checkout '<branchname>'
echo after the git clone command
git clone git://itk.org/SimpleITK.git sitk
#
# recover the upstream commit date.
cd sitk
upstream_date="$(git log -n 1 --format='%cd')"
upstream_hash="$(git rev-parse --short=8 HEAD)"
cd ..

mkdir -p BasicFilters/json
cp -r sitk/Code/BasicFilters/json/*.json BasicFilters/json

# get rid of SimpleITK clone
rm -rf sitk
#
# add upstream files in Git
git add --all

#
# commit new source
GIT_AUTHOR_NAME='SimpleITK Maintainers' \
GIT_AUTHOR_EMAIL='insight-developers@itk.org' \
GIT_AUTHOR_DATE="${upstream_date}" \
git commit -q -m "SimpleITK ${upstream_hash} Filter descriptions (reduced)

This tree was extracted from upstream SimpleITK by the following shell script:
  ./UpdateFilterDescriptionsFromSimpleITK.sh"

#
# push to the sitk-upstream branch in the
# ITK tree
git push .. HEAD:sitk-upstream
cd ..
#
# get rid of temporary repository
rm -fr sitk-tmp
#
# checkout a new update branch off of the master.
git checkout -b update-sitk master
#
# use subtree merge to bring in upstream changes
git merge -s recursive -X subtree=BasicFilters/json sitk-upstream

# Obtain hash tag at which begin the next update
sitk_upstream_hash="$(git rev-parse --short=8 sitk-upstream)"

echo "---------------------------------"
echo 1. If there are conflicts, resolve them and commit.
echo
echo "---------------------------------"
echo 2. Edit line \"git branch sitk-upstream\" in UpdateFilterDescriptionsFromSimpleITK.sh
echo script with hash tag ${sitk_upstream_hash}.
echo
echo Associated commit message should be:
echo "  Update UpdateFilterDescriptionsFromSimpleITK.sh for ${upstream_hash} snapshot"
echo
echo "---------------------------------"
echo 3. Submit a pull request or directly merge topic update-sitk into master

