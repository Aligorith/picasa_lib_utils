# Utility for parsing Picasa settings files from a folder

import sys

import configparser	   # (Python's builtin "INI" parser)
import datetime
from enum import (Enum, IntEnum)
import json
import pathlib
import re


###################################################
# Picasa Per-File Settings Bits and Pieces

# String Processing Utility - Wrapper Stripping
#
# Extract the value from a string of form:
#   f(x)
# where "f" is the prefix, and "x" is the value we want
#
# NOTE: Manual instead of regex, as it's not worth running up a regex for this
def strip_prefix_wrapper(picasaStr, prefix):
	full_prefix = prefix + "("
	end_suffix  = ")"
	
	if not picasaStr.startswith(prefix) and picasaStr.endswith(end_suffix):
		raise ValueError(f"Prefix-wrapper string doesn't follow expected form: '{picasaStr}'")
	
	# Extract just the value
	full_prefix_len = len(full_prefix)
	end_suffix_len  = len(end_suffix) + 1
	
	value_str = picasaStr[full_prefix_len : -end_suffix_len]
	assert value_str != ""
	
	return value_str

# =================================================

# Enum: Rotation Modes
class ePicasaRotateMode(IntEnum):
	# Normal / No Rotation (rotate(0))
	NO_ROTATION = 0
	
	# Rotate Clockwise (i.e. To Right)
	CW = 1
	
	# Flip Upside Down
	FLIP = 2
	
	# Rotate Counter-Clockwise (i.e. To Left)
	CCW = 3


# Parse Picasa Rotation String
def parse_picasa_rotate_string(rotateStr):
	# These always take the form:
	#   "rotate(x)"
	# where "x" is one of (0, 1, 2, 3)
	value_str = strip_prefix_wrapper(rotateStr, "rotate")
	
	# Explicitly pattern match for better parsing safety
	if value_str == "3":
		return ePicasaRotateMode.CCW
	elif value_str == "2":
		return ePicasaRotateMode.FLIP
	elif value_str == "1":
		return ePicasaRotateMode.CW
	elif value_str == "0":
		return ePicasaRotateMode.NO_ROTATION
	else:
		print("Unknown rotation mode value: '{value-str}'", out=sys.stderr)
		return ePicaseRotateMode.NO_ROTATION

# =================================================

# Offsets Rect - All stored coordinates are relative (i.e. in 0.0 - 1.0 range)
class PicasaCropRect:
	# ctor
	def __init__(self, hashStr, left, top, right, bottom):
		# The original hash-string this was derived from
		self.hash = hashStr
		
		# Store the relative coordinates
		# TODO: Store as a named-tuple internally?
		self.left = left
		self.top = top
		self.right = right
		self.bottom = bottom
	
	# Convert filter settings to JSON representation
	def to_json(self):
		result = {
			'hash64': self.hash,
			
			'left'  : self.left,
			'top'   : self.top,
			'right' : self.right,
			'bottom': self.bottom
		}
		return result


# Convert Picasa crop/rect string into a hex-string
def extract_hexstr64_from_croprect64(picasaStr):
	for prefix in { "rect64(", "crop64(" }:
		# Match found?
		if picasaStr.startswith(prefix):
			# Extract the value part
			match = strip_prefix_wrapper(picasaStr, prefix)
			
			# Check that result is 4 pairs of hex characters
			#assert len(match) == 4*4
			
			# Return the result
			return match
	else:
		# No match found
		raise ValueError(f"crop64 / rect64 string with unexpected format encountered: '{picasaStr}'")


# Parse Picasa "crop64" / "rect64" hashString value
# ! If processing the "crop64" or "rect64" values, these must be pre-processed
#   using extract_hexstr64_from_croprect64() to get rid of the prefix first
def parse_picasa_croprect_64_string(hashStr):
	# From info on the web:
	# 1) This value is represented as a 64-bit hexadecimal number
	# 2) First, it should be broken into four 16-bit values
	# 3) Each of these four values should then be divided by the max
	#    unsigned 16-bit value, to get values in the 0-1 range
	# 4) From those four values, you get the relative coords for the rectangle
	#    (i.e. left, top, right, bottom)
	# 5) To get absolute coordinates, you multiply by the image dimensions
	U16_BASE = 16
	MAX_U16_VALUE = 65535
	
	left   = int(hashStr[0:4],   U16_BASE) / MAX_U16_VALUE
	top    = int(hashStr[4:8],   U16_BASE) / MAX_U16_VALUE
	right  = int(hashStr[8:12],  U16_BASE) / MAX_U16_VALUE
	bottom = int(hashStr[12:16], U16_BASE) / MAX_U16_VALUE
	
	return PicasaCropRect(hashStr, left, top, right, bottom)

###################################################
# Picasa Filter Settings

# TODO's
# * Reconsider if we really want to save the original values "inline"
#   with the "Str" suffix, or whether an alternative solution would
#   work better.


# Baseclass for Picasa Filters
# ! This is just a tag to make working with the other ones easier
class PicasaFilterSettings:
	# ctor
	# < commandStr: (str) Name of the command, as saved in the Picasa.ini file
	# < paramsStr: (str) String of comma-separated parameter values
	def __init__(self, commandStr, paramsStr):
		# Store the args from the Picasa-file as-is
		self.commandStr = commandStr
		self.paramsStr  = paramsStr
		
		# Unpack the parameters
		self.params = paramsStr.split(",")
	
	# Convert filter settings to JSON representation
	# ! Subclasses should override and call this as their basis
	def to_json(self):
		result = {
			'command': self.commandStr,
			'params': self.paramsStr,
		}
		return result

# =================================================

# Crop Filter
# e.g.  "filters=crop64=1,1b502e26c807e353;"
class PicasaCropFilter(PicasaFilterSettings):
	# ctor
	def __init__(self, commandStr, params):
		super(PicasaCropFilter, self).__init__(commandStr, params)
		
		# Unpack arg 2 to get the crop rect
		assert len(self.params) == 2
		self.cropRect = parse_picasa_croprect_64_string(self.params[1])
	
	# ! Override: PicasaFilterSettings.to_json()
	def to_json(self):
		result = super(PicasaCropFilter, self).to_json()
		result['cropRect'] = self.cropRect.to_json()
		return result

# =================================================

# Tilt filter
class PicasaTiltFilter(PicasaFilterSettings):
	# ctor
	def __init__(self, commandStr, params):
		super(PicasaTiltFilter, self).__init__(commandStr, params)
		
		# Unpack arg 2 to get the strengthening amount (a float)
		# Range:   -1.0 <= v <= 1.0
		assert len(self.params) == 3
		
		self.amountStr = self.params[1]
		self.amount = float(self.amountStr)
		
		# TODO: Figure out how to map "amount" to rotation in degrees / radians
	
	# ! Override: PicasaFilterSettings.to_json()
	def to_json(self):
		result = super(PicasaTiltFilter, self).to_json()
		result['amount'] = self.amountStr
		return result

# =================================================

# Fill Light Filter (i.e. main-tab 'Fill' slider')
class PicasaFillLightFilter(PicasaFilterSettings):
	# ctor
	def __init__(self, commandStr, params):
		super(PicasaFillLightFilter, self).__init__(commandStr, params)
		
		# Unpack arg 2 to get the fill strength (a float)
		assert len(self.params) == 2
		
		self.fillStr = self.params[1]
		self.fill = float(self.fillStr)
	
	# ! Override: PicasaFilterSettings.to_json()
	def to_json(self):
		result = super(PicasaFillLightFilter, self).to_json()
		result['fill'] = self.fillStr
		return result

# =================================================

# FineTune Filter (i.e. "finetune2")
class PicasaFinetuneFilter(PicasaFilterSettings):
	# ctor
	def __init__(self, commandStr, params):
		super(PicasaFinetuneFilter, self).__init__(commandStr, params)
		self.unpack_settings_from_params()
	
	# Unpack settings from the parameters
	def unpack_settings_from_params(self):
		# Fill = (float :: 0.0 <= v <= 1.0)
		self.fillStr = self.params[1]
		self.fill    = float(self.fillStr)
		
		# Highlight = (float :: 0.0 <= v <= 0.5)
		# NOTE: Unsure if the max is 0.5 or 0.48; The UI consistently only allowed setting 0.48
		self.highlightStr = self.params[2]
		self.highlight    = float(self.highlightStr)
		
		# Shadow = (float :: 0.0 <= v <= 0.5)
		# NOTE: Unsure if the max is 0.5 or 0.48; The UI consistently only allowed setting 0.48
		self.shadowStr = self.params[3]
		self.shadow    = float(self.shadowStr)
		
		# Autocolor - HexString
		self.autocolorStr = self.params[4]
		# ... color object ...
		
		# Color Temperature = (float :: -1.0 <= v <= 1.0)
		# XXX: Primaries for this?
		self.colorTempStr = self.params[5]
		self.colorTemp    = float(self.colorTempStr)
	
	# ! Override: PicasaFilterSettings.to_json()
	def to_json(self):
		result = super(PicasaFinetuneFilter, self).to_json()
		
		result['fill']      = self.fillStr
		result['highlight'] = self.highlightStr
		result['shadow']    = self.shadow
		result['autocolor'] = self.autocolorStr
		result['colorTemp'] = self.colorTempStr
		
		return result

# =================================================

# Sharpen filter
class PicasaSharpenFilter(PicasaFilterSettings):
	# ctor
	def __init__(self, commandStr, params):
		super(PicasaSharpenFilter, self).__init__(commandStr, params)
		
		# Unpack arg 2 to get the strengthening amount (a float)
		# * Default: 0.6
		# * Range:   0.0 <= v <= 3.0
		assert len(self.params) == 2
		
		self.amountStr = self.params[1]
		self.amount = float(self.amountStr)
	
	# ! Override: PicasaFilterSettings.to_json()
	def to_json(self):
		result = super(PicasaSharpenFilter, self).to_json()
		result['amount'] = self.amountStr
		return result

# =================================================

# Entrypoint for Picasa Filter Parsing
# < filterString: (str) One part of the stack of filters applied.
#                       This has the form:
#                       "command=p1,p2,...,pn"
def parse_picasa_filter(filterString):
	# Split the filterString into "command" vs "parameters" parts
	#print("split = '%s' => %s'" % (filterString, filterString.split("=", 1)))
	commandStr, paramsStr = filterString.split("=", 1)
	
	# Delegate to the appropriate filter
	if commandStr == "finetune2":
		return PicasaFinetuneFilter(commandStr, paramsStr)
	elif commandStr == "crop64":
		return PicasaCropFilter(commandStr, paramsStr)
	elif commandStr == "tilt":
		return PicasaTiltFilter(commandStr, paramsStr)
	elif commandStr == "fill":
		return PicasaFillLightFilter(commandStr, paramsStr)
	elif commandStr == "unsharp2":
		return PicasaSharpenFilter(commandStr, paramsStr)
	else:
		print(f"WARNING: filter '{commandStr}' is not yet supported")
		return PicasaFilterSettings(commandStr, paramsStr)

###################################################
# Picasa Settings Objects - Per File / Image

# Picasa settings object for a image / video
class PicasaFileSettings:
	# ctor
	# < filename: (str) Just the name of the file, with no path
	# < path: (Path) Full path to the file, including the filename arg
	# < sourceData: (configparser.ItemsView | dict) Source data to unpack from 
	def __init__(self, filename, path, sourceData):
		self.filename = filename
		self.path = path
		
		self.unpack_original_settings(sourceData)
	
	# Picasa Unpacking ----------------------------
	
	# Entrypoint for unpacking data from the Picasa section
	def unpack_original_settings(self, sourceData):
		# Star
		# NOTE: Assume that it never says "star = no"
		self.star = "star" in sourceData.keys()
		
		# Cropping
		CROP_KEY = "crop"
		if CROP_KEY in sourceData.keys():
			cropHash  = extract_hexstr64_from_croprect64(sourceData[CROP_KEY])
			self.crop = parse_picasa_croprect_64_string(cropHash)
		else:
			self.crop = None
		
		# Rotation
		ROTATE_KEY = "rotate"
		if ROTATE_KEY in sourceData.keys():
			# Unpack from rotate regex
			self.rotate = parse_picasa_rotate_string(sourceData[ROTATE_KEY])
		else:
			self.rotate = ePicasaRotateMode.NO_ROTATION
		
		# Filters
		FILTERS_KEY = "filters"
		if FILTERS_KEY in sourceData.keys():
			# Get the list of filter strings
			filters = sourceData[FILTERS_KEY].split(";")
			
			# Parse + Process These
			# NOTE: The if case is to handle the trailing semicolon
			self.filters = [
				parse_picasa_filter(f)
				for f in filters
				if f != ""
			]
		else:
			self.filters = []
	
	# Json Serialisation --------------------------
	
	# Entrypoint for serialising to JSON
	def to_json(self):
		# Create output dict
		result = {}
		
		# Convert the data
		result['star'] = self.star
		
		if self.rotate is not ePicasaRotateMode.NO_ROTATION:
			result['rotate'] = self.rotate
		
		if self.crop is not None:
			result['crop'] = self.crop.to_json()
		
		if self.filters:
			result['filters'] = [
					f.to_json()
					for f in self.filters
				]
		
		# Return the serialised result
		return result
		

###################################################
# Per-Folder Picasa Settings File

# Root Picasa settings object for a folder
class PicasaFolderSettings:
	# ctor
	# < settingsFilePath: (Path) Path to the settings file - Used to resolve the
	#                     filepaths for checking on the files in question for
	#                     additional metadata
	# < sourceData: (ConfigParser) The data to load the configuration from
	def __init__(self, settingsFilePath, sourceData):
		# Store received data for later
		self.settingsFilePath = settingsFilePath
		
		# Init the basic variables using placeholders
		# TODO: Keep this in sync with the other variants
		# TODO: These should just be set via Parus Parameters
		self.name = ""
		self.date_str = "0.0"
		#self.date_iso = datetime.datetime()
		self.date = 0.0
		
		# Unpack source data
		self.unpack_original_settings(sourceData)
	
	# ----------------------------------------------
	
	# Unpack data from original Picasa INI file
	def unpack_original_settings(self, sourceData):
		# Unpack folder metadata
		# NOTE: This may not exist...
		PICASA_KEY = "Picasa"
		if PICASA_KEY in sourceData.keys():
			picasaMetadata = sourceData[PICASA_KEY]
			
			self.name     = picasaMetadata["name"]  # folder/album name
			
			self.date_str = picasaMetadata["date"]  # unix timestamp string
			self.date     = float(self.date_str)
			
			# NOTE: There's also the `"category" = "Folders on Disk"` property,
			#       but that's rarely relevant in my own collections so cannot
			#       test what the alternative is...
		
		
		# Unpack the per-image settings
		self.files = {}
		
		for filename in sourceData.sections()[1:]:
			# Grab the parsed data for this image
			fileConfigData = sourceData[filename]
			
			# Create settings object for this image
			fileSettingsObj = PicasaFileSettings(filename, self.settingsFilePath, fileConfigData)
			
			# Add parsed image data to our collection
			self.files[filename] = fileSettingsObj
		
	# ----------------------------------------------
	
	# Serialise to JSON representation
	def to_json(self):
		result = {
			'_metadata': {
				'name': self.name,
				'date': self.date_str
			},
			'files': {
				key : self.files[key].to_json()
				for key in self.files
			}
		}
		return result

####################################################
# Parser for Picasa Settings File (for a folder / album)

# Entrypoint for parsing Picasa settings
# < fileN: (Path) Path to a ".picasa.ini" file to load + unpack
def parse_picasa_settings(fileN):
	# Create the parser
	parser = configparser.ConfigParser()
	
	# Try to parse the file
	readResult = parser.read(fileN)
	if len(readResult) == 0:
		print(f"ERROR: Parsing '{fileN} failed")
		return None
	
	# Create the folder settings object
	settings = PicasaFolderSettings(fileN, parser)
	
	# Return the parsed result
	return settings

###################################################

if __name__ == "__main__":
	# Try loading the provided file(s), and spitting out a JSON representation
	args = sys.argv[1:]
	if len(args) == 0:
		print("USAGE: picasa_loader.py <path/1/to/picasa.ini> ...")
		sys.exit(0)
	
	# Try processing this arg...
	for arg in args:
		#print(f"\n=== {arg} ===")
		path = pathlib.Path(arg)
		if path.exists():
			#print(f">> Processing as: '{path}'")
			settings = parse_picasa_settings(path)
			
			settingsJson = settings.to_json()
			
			# TODO: Write json
			formattedJson = json.dumps(settingsJson, indent='\t')
			print(formattedJson)
			
