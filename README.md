# duo_lab_maker
Scripts to create virtual Duo training environment

<pre>
usage: fake_names_2_users_csv.py [-h] [-f CONF_FILE] [-i CSV_FILE] [-same_pw]
                                 [-u] [-g] [-be]

This script reads a csv file pulled down from fakenamegenerator.com and
attempts to create .ldif files for OpenLDAP

optional arguments:
  -h, --help    show this help message and exit
  -f CONF_FILE  config file
  -i CSV_FILE   CSV file to use for input
  -same_pw      Use passwd in config file for all users
  -u            Use to spit out user info in .ldif form
  -g            Use to spit out group info in .ldif form
  -be           Use this for Duo Bulk Enrollment
  
</pre>
