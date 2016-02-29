#!/bin/sh

DOCUMENTROOT=web

# Prepare the scaffold files if they are not already present
if [ ! -f $DOCUMENTROOT/autoload.php ]
  then
    composer drupal-scaffold
    mkdir -p $DOCUMENTROOT/modules
    mkdir -p $DOCUMENTROOT/themes
    mkdir -p $DOCUMENTROOT/profiles
fi

# Prepare the services file for installation
if [ ! -f $DOCUMENTROOT/sites/default/services.yml ]
  then
    cp $DOCUMENTROOT/sites/default/default.services.yml $DOCUMENTROOT/sites/default/services.yml
fi
