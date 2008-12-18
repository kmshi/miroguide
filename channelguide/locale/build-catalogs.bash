#!/bin/bash
#
# This script is designed to handle downloads from Launchpad and
# integrate them into miroguide.com
#
# Matt Kivela
# December, 2008
#

# Variables:
  tempfile="./po.temp"
  base_name="miro-guide"
  staging="/data/miroguide/channelguide/locale/staging"
  po_name="django"
  php_dir_base="/data/miroguide/channelguide"

# Initialize:
  mkdir $staging

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
  mv $base_name-* $staging/. > /dev/null 2>&1

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
            echo "Processing "$long_lang" ("$lang")"          
          # Does this language already have a directory?  If not, make one.
            if [ ! -e "./$lang" ]
            then
              echo "Directory for $lang doesn't exist, creating directory."
              mkdir ./$lang
              mkdir ./$lang/LC_MESSAGES/
            else
              echo > /dev/null
            fi
          # Move the po file to the final location:
            mv $original ./$lang/LC_MESSAGES/$po_name.po
          # run msgfmt to generate binary:
          # This is not needed for miroguide, just the po files are used.
            # msgfmt ./$lang/LC_MESSAGES/$po_name.po -o ./$lang/LC_MESSAGES/$po_name.mo    
        loop=$((loop+1))
        done


# Let's now built the new $base_name.pot file to upload to Launchpad

  # First, let's warn people before the continue:
    echo "************************************************************"
    echo "*                                                          *"
    echo "* Translations done.                                       *"
    echo "*                                                          *"
    echo "* To generate $base_name.pot to upload to Launchpad,       "
    echo "* Press 1 <enter>                                          *"
    echo "* Press c <enter> to continue                              *"
    echo "*                                                          *"
    echo "* If you do generate the democracy.pot, you will see a     *"
    echo "* a number of error messages, do not be alarmed.           *"
    echo "* You will need to manually upload getdemocracy.pot.       *"
    echo "************************************************************"

    read -t 600 choice
    case $choice in
      1)
        # First, make sure there is a getdemocracy.pot so there isn't an error in the next step
          if [ ! -e "./$base_name.pot" ]
          then
            echo "$base_name.pot doesn't exist; creating empty file to fill."
            echo > ./$base_name.pot
          else
            echo "$base_name.pot exists; continuing."
          fi
        # And no search for strings to put in the po template:
          find $php_dir_base/ -iname "*.py" -exec xgettext -C -j -o ./$base_name.pot --keyword=_ {} \; 
        ;;
      *)
        echo "Alrighty, continuing on.";
        ;;
     esac

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

        # Chown the directories
          chown -R apache:pcf-web /data/miroguide/channelguide/locale

        # Check for new files to add to subversion:
          svn status | grep "\?" | awk '{print $2}' | xargs svn add

        # And let's commit our files:
          echo "Please run this command manually:  svn commit . -m 'Automated check-in from build-catalogs.bash for Launchpad file # $1'"
        ;;
      *)
        echo "You are the weakest link.  Goodbye."
    esac 
