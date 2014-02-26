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
echo in SimpleFilters/Resources/json from
echo  http://itk.org/SimpleITK.git
echo "-------------------------------------------------------"
if [ ! -f Utilities/UpdateFilterDescriptionsFromSimpleITK.sh ]
then
    echo The current working directory $(pwd) is not the top level
    echo of the SlicerSimpleFilters source code tree. Please change
    echo to the SlicerSimpleFilters source directory and re-run 
    echo this script
    exit 1
fi
if [ $(git show-branch update-sitk &> /dev/null) -eq 0 ]
then
    echo There is an existing update-sitk branch which should be removed.
    exit 1
fi
#
# The origin has a branch "sitk-upstream" which contains imported json
# files as a subtree.
#
git branch -f sitk-upstream origin/sitk-upstream

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
# download and copy the necessary SimpleITK source
echo Cloning upstream HEAD from http://itk.org/SimpleITK.git
echo NOTE: to check out a particular revision for merging
echo you have to add a git checkout '<hash>'
echo or git checkout '<branchname>'
echo after the git clone command
git clone git://itk.org/SimpleITK.git sitk
#
# recover the upstream commit date.
cd sitk
#git checkout  origin/release
upstream_date="$(git log -n 1 --format='%cd')"
upstream_hash="$(git rev-parse --short=8 HEAD)"
cd ..

find ./sitk/Code/ -name \*.json -exec cp {} ./ \;

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
  ./Utilities/UpdateFilterDescriptionsFromSimpleITK.sh"

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
git merge -s recursive -X subtree=SimpleFilters/Resources/json sitk-upstream

echo "---------------------------------"
echo 1. If there are conflicts, resolve them and commit.
echo
echo "---------------------------------"
echo 2. Push the updated \"sitk-upstream\" branch to the origin.
echo
echo "---------------------------------"
echo 3. Submit a pull request or directly merge topic update-sitk into master

