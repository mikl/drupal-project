#!/bin/sh

# Remove a bunch of files we do not want on prod, due to security risks
# or space saving concerns.
cd web
rm -fv core/authorize.php core/*.dist core/*.txt core/install.php update.php web.config
