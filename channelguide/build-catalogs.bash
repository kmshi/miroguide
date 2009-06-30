#!/bin/bash
#
# This script is designed to handle downloads from Launchpad and
# integrate them into miroguide.com
#
# Matt Kivela
# December, 2008
#
# Updated by Paul Swartz to allow different .po names, and to use Git instead of SVN
# March 2009

# Variables:
  tempfile="./po.temp"
  locale_dir=`dirname $0`/guide/locale
  php_dir_base="$locale_dir/.."
  staging="$locale_dir/staging"

# Pre-requisite Checks
  which msgfmt > /dev/null
    if [ "$?" == 0 ]
    then
      echo "msgfmt is present."
    else
      echo "You are missing msgfmt on this machine! Install gettext before running this script."
      exit
    fi

  which xgettext > /dev/null
    if [ "$?" == 0 ]
    then
      echo "xgettext is present."
    else
      echo "You are missing xgettext on this machine! Install gettext before running this script."
      exit
    fi

# Check that $1 is not null
  if [ -z $1 ]
  then
    echo "This script expects to be given the directory from Launchpad the to download."
    echo "i.e. if you received the link from launchpad like this:"
    echo "http://launchpadlibrarian.net/12761495/launchpad-export.tar.gz"
    echo "Then call this script like this:"
    echo "./build-catalogs 12761495"
    exit
  else
    echo > /dev/null
  fi

# Download files:
  # First, make sure there is no launchpad files hanging around:
    rm launchpad-export* > /dev/null 2>&1

  # Ok, now download it:
    wget http://launchpadlibrarian.net/$1/launchpad-export.tar.gz

# Extract files:
  tar -xvf ./launchpad-export.tar.gz > /dev/null 2>&1

for po_name in django djangojs; do
  rm -rf $staging

  # Initialize:
  mkdir $staging

  if [ $po_name = django ]; then
      base_name=miro-guide
  else
      base_name=javascript
  fi
  mv po/$base_name/$base_name-* $staging/. > /dev/null 2>&1

# Ok, now let's process them:
  ls $staging/*.po > $tempfile

count=$(grep -c . $tempfile)
  count=$((count+1))
    loop=1
      while [ "$loop" -lt "$count" ]
        do
          # What is the original file from Launchpad?
            original=$(tail -$loop $tempfile | head -1)
          # What is the languague?
            lang=$(echo $original | sed 's/^.*-//g' | sed 's/.po.*$//g')
            long_lang=$(head -1 $original | sed 's/^# //g' | sed 's/ translation.*//g')
            echo "Processing "$long_lang" ("$lang") from $base_name"
          # Does this language already have a directory?  If not, make one.
            if [ ! -e "$locale_dir/$lang" ]
            then
              echo "Directory for $lang doesn't exist, creating directory."
              mkdir $locale_dir/$lang
              mkdir $locale_dir/$lang/LC_MESSAGES/
            else
              echo > /dev/null
            fi
          # Move the po file to the final location:
            mv $original $locale_dir/$lang/LC_MESSAGES/$po_name.po
          # run msgfmt to generate binary:
            msgfmt $locale_dir/$lang/LC_MESSAGES/$po_name.po -o $locale_dir/$lang/LC_MESSAGES/$po_name.mo
        loop=$((loop+1))
        done
done
# Now let's cleanup files and commit:

  # First, let's warn people before the continue:
    echo "************************************************************"
    echo "*                                                          *"
    echo "* Cleanup & Commit                                         *"
    echo "*                                                          *"
    echo "* This step will cleanup temporary files and commit        *"
    echo "* changes in Subversion.                                   *"
    echo "* You should choose 1, unless you're debugging.            *"
    echo "* Press 1 <enter>                                          *"
    echo "* Press x <enter> to exit                                  *"
    echo "*                                                          *"
    echo "************************************************************"

    read -t 600 choice
    case $choice in
      1)
        # Remove temporary / no longer needed files:
          rm -rf ./po.temp
          rm -rf ./launchpad-export.tar.gz
          rm -rf $staging
          rm -rf po

        # Check for new files to add to git
          git add $locale_dir

        # And let's commit our files:
          echo "Please run this command manually:  git commit -m 'Automated check-in from build-catalogs.bash for Launchpad file # $1'"
        ;;
      *)
        echo "You are the weakest link.  Goodbye."
    esac
