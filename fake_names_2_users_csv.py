#!/usr/bin/python

# fake_names_2_users_csv.py

# Column headers in FakeNameGenerator file:

# Number	
# Gender	
# NameSet	
# Title	
# GivenName
# MiddleInitial
# Surname
# StreetAddress
# City
# State
# StateFull
# ZipCode
# Country
# CountryFull
# EmailAddress
# Username
# Password
# BrowserUserAgent
# TelephoneNumber
# TelephoneCountryCode
# MothersMaiden
# Birthday
# Age
# TropicalZodiac
# CCType
# CCNumber
# CVV2
# CCExpires
# NationalID
# UPS
# WesternUnionMTCN
# MoneyGramMTCN
# Color
# Occupation
# Company
# Vehicle
# Domain
# BloodType
# Pounds
# Kilograms
# FeetInches
# Centimeters
# GUID
# Latitude
# Longitude

# Pro tip from Matt Hess - DON'T sync the user's phone number when running Directory Sync

import csv
from collections import namedtuple
from configparser import ConfigParser
import sha
from base64 import b64encode
import argparse
import os
import sys
import ldif
import tempfile
import unicodedata

def make_ldap_passwd(passwd):
	ctx = sha.new(passwd)
	passwd_hash = "{SHA}" + b64encode(ctx.digest())
	passwd_hash = str(passwd_hash)
	return passwd_hash

def parse_fake_names_csv(args,email_domain,base_dn,user_cn,passwd,group,group_description):
	with open(csv_file, 'rt') as f:
		f_csv = csv.reader(f)
		headings = next(f_csv)
		# when you unzip the .csv file from fakenamegenerator.com
		# the headers start with a BOM unicode character that needs to be stripped
		bom_free_headings = []
		for h in headings:
			u = h.decode("utf-8-sig")
			h = u.encode("utf-8")
			bom_free_headings.append(h)
		# Now the headings have been stripped of the BOM (Byte Order Mark)
		Row = namedtuple('Row',bom_free_headings)
		member_list = []

		for r in f_csv:
			row = Row(*r)
			sn = row.Surname
			name = row.GivenName + " " + sn
			FirstInitial = row.GivenName[0]
			UserId = (FirstInitial + sn).lower()
			sAMAccountName = UserId
			if email_domain:
				email_domain = email_domain
			else:
				email_domain = row.Domain
			domain_name,tld = email_domain.split(".")
			email = str(UserId + "@" + email_domain)
			userPrincipalName = str(sAMAccountName + "@" + domain_name + ".local")
			distinguishedName = str("CN=" + name + "," + "OU=" + user_cn + "," + base_dn)
			if args.same_pw:
				passwd = str(passwd)
			else: 
				passwd = str(row.Password)
			passwd_hash = make_ldap_passwd(passwd)
			ldap_groupname = str("CN=" + group + ",OU=" + user_cn + "," + base_dn)
			
			#member_list is needed for group ldif file
			group_member_by_uid = str("uid=" + UserId + ",OU=" + user_cn + "," + base_dn)
			member_list.append(group_member_by_uid)

			user_ldap_info = {
				'cn':	[name],
				'sn': 	[sn],
				'uid': 	[UserId],
				'mail': [email],
				'userPassword': [passwd_hash],
				'dn':	[distinguishedName],
				'memberOf':	[ldap_groupname],
				'objectClass':	['person','inetOrgPerson','organizationalPerson']
			}

			group_ldap_info = {
				'dn':	[ldap_groupname],
				'objectClass':	['groupofnames'],
				'cn':	[group],
				'description':	[group_description],
				'member':	member_list
			}

			if args.make_user_ldif:
				write_ldif(user_ldap_info)

			if args.make_duo_bulk_enroll:
				duo_bde = UserId + "," + email
				print(duo_bde)
				# TODO - maybe write this to a file instead of stdout
			
		if args.make_group_ldif:
			#print(group_ldap_info)
			write_ldif(group_ldap_info)




def write_ldif(ldap_info):
	with open(path, 'a') as fd:
		ldif_writer = ldif.LDIFWriter(fd)
		ldif_writer.unparse(base_dn,ldap_info)
		#print(path)
	fd.close()


def ugly_hack(input_file,base_dn):
	# This is required because Bert is probabaly using ldif.LDIFWriter incorrectly
	extra_dn = str("dn: " + base_dn)
	with open(input_file, 'rt') as f:
		for line in f:
			if extra_dn not in line:
				sys.stdout.write(line)
				# TODO - maybe write this to a file instead of stdout
	

# First things first - I require a temp file
fd, path = tempfile.mkstemp()


# Parse command line args
parser = argparse.ArgumentParser(description=
	'''This script reads a csv file pulled down from fakenamegenerator.com and attempts to create .ldif files for OpenLDAP''')
parser.add_argument('-f', dest='conf_file', action='store', help='config file')
parser.add_argument('-i', dest='csv_file', action='store', help='CSV file to use for input')
parser.add_argument('-same_pw', dest='same_pw', action='store_true', help='Use passwd in config file for all users')
parser.add_argument('-u', dest='make_user_ldif', action='store_true', help='Use to spit out user info in .ldif form')
parser.add_argument('-g', dest='make_group_ldif', action='store_true', help='Use to spit out group info in .ldif form')
parser.add_argument('-be', dest='make_duo_bulk_enroll', action='store_true', help='Use this for Duo Bulk Enrollment')

# If no command line args, print help
if len(sys.argv)==1:
	parser.print_help()
	sys.exit(1)

# Read command line args
args = parser.parse_args()

# Read and parse the config file
cfg = ConfigParser()


# Check for a config file - exit if missing
# First try config file specified with -f on command line
if args.conf_file:
	conf_file = args.conf_file
else:
	try:
		cfg.read(conf_file)
	except:
		error = "Can't open config file.  I am slain!"
		print(error)
		sys.exit(1)

# Check for an input file - exit if missing
# First try command line switch, then check config file
if args.csv_file:
	csv_file = args.csv_file
else:
	try:
		cfg.read(conf_file)
		csv_file = str(cfg.get('file_io', 'input_file'))
	except:
		error = "No input specified on command line or in config file"
		print(error)
		sys.exit(1)
	
# Read config file to optionally overwrite some of the values in the CSV input file
cfg.read(conf_file)
email_domain = cfg.get('domain_info', 'email_domain')
base_dn = cfg.get('domain_info', 'base_dn')
user_cn = cfg.get('domain_info', 'user_cn')
passwd = cfg.get('domain_info', 'password')
user_group = cfg.get('domain_info', 'group')
group_description = cfg.get('domain_info', 'group_description')

# Send values from config file to parsing function
parse_fake_names_csv(args,email_domain,base_dn,user_cn,passwd,user_group,group_description)
ugly_hack(path,base_dn)






