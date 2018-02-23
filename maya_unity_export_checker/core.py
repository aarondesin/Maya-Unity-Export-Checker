# UNITY EXPORT CHECKER (V2)
# Aaron Desin

# IMPORTS
import pymel.core as pm
import maya.mel as mel

# CONSTANTS
MAIN_WINDOW_DIMENSIONS = [384,512]
MAIN_WINDOW_RESIZEABLE = False
MAIN_WINDOW_TITLE = 'Unity Export Checker'
MAIN_WINDOW_ICON_TITLE = 'Unity Checker'
MAIN_WINDOW_CONTENT_PADDING = 8
MAIN_WINDOW_CONTENT_SPACING = 8
MAIN_WINDOW_LINE_SPACING = 2
CHECKLIST_TEXT_WIDTH = 192
CHECKLIST_BUTTONAREA_WIDTH = 128
CHECKLIST_COLUMN_WIDTHS = (CHECKLIST_TEXT_WIDTH, CHECKLIST_BUTTONAREA_WIDTH)
LOG_SCROLL_AREA_HEIGHT = 240
LOG_CHARACTERS_PER_LINE = 66
MAX_LOG_HEIGHT = 512
MAIN_BUTTON_AREA_HEIGHT = 64
HEADER_STYLE = 'boldLabelFont'
FRAME_BORDER_STYLE = 'etchedIn'
LINE_HEIGHT = 13

# All known default geometry object names
DEFAULT_OBJECT_NAMES = ['pCone','pCube','pCylinder', 'pHelix',
	'pPipe','pPlane','pPrism','pPyramid','pSolid','pSphere','pTorus']
	
# All known default material names
DEFAULT_MATERIAL_NAMES = ['anisotropic','bifrostAeroMaterial', 
	'bifrostFoamMaterial','bifrostLiquidMaterial','blinn', 
	'hairTubeShader','lambert','layeredShader','oceanShader','phong', 
	'phongE','rampShader','ShaderfxShader','shadingMap','StingrayPBS', 
	'surfaceShader','useBackground']

class unity_export_checker(object):

	# METHODS
	def __init__(self):
		self.main_window = None
		self.success_dialog = None
		self.selected_objects = []
		self.log_results = ''
		
		# Ordered list of function names
		# Functions will be executed in this order
		self.lookup_order = ['NONGEOMETRY', 'CONSHISTORY', 'UNFROZENTR', 
			'TOOMANYUVS', 'DEFAULTOBJNAMES', 'DEFAULTMATNAMES']
			
		# List of all functions available in the program
		self.functions = {
			'NONGEOMETRY': self.checker_function (
				self.is_not_geometry, 
				self.remove_from_selection, 
				'Selected non-geometry objects'),
			'CONSHISTORY': self.checker_function (
				self.has_construction_history, 
				self.clear_construction_history, 
				'Non-empty construction history'),
			'UNFROZENTR': self.checker_function (
				self.has_nonzero_transform, 
				self.freeze_transform, 
				'Unfrozen transforms'),
			'TOOMANYUVS': self.checker_function (
				self.has_more_than_two_uvs, 
				self.remove_extra_uvs, 
				'More than two UV sets'),
			'DEFAULTOBJNAMES': self.checker_function (
				self.object_has_default_name, 
				None, 'Default object names'),
			'DEFAULTMATNAMES': self.checker_function (
				self.materials_with_default_names, 
				None, 'Default material names')
		}
		
		# List of default option settings for each function
		# These will be used the first time the user starts the program
		self.options = {
			'NONGEOMETRY':     self.checker_option.CLEANUP,
			'CONSHISTORY':     self.checker_option.CHECK,
			'UNFROZENTR':      self.checker_option.CHECK,
			'TOOMANYUVS':      self.checker_option.CHECK,
			'DEFAULTOBJNAMES': self.checker_option.CHECK,
			'DEFAULTMATNAMES': self.checker_option.CHECK
		}
		
		self.show_UI()
		
	# Initializes and displays the tool UI
	def show_UI (self):

		# Init main window
		if (pm.window("main_window", exists=True)):
			pm.deleteUI ("main_window")
		self.main_window = pm.window (t=MAIN_WINDOW_TITLE, 
			wh=MAIN_WINDOW_DIMENSIONS, s=MAIN_WINDOW_RESIZEABLE)
		
		# Main vertical layout
		window_v_layout = pm.columnLayout (adj=True, 
			rs=MAIN_WINDOW_CONTENT_SPACING, 
			h=MAIN_WINDOW_DIMENSIONS[1])
		
		# Checklist scroll layout
		checklist_scroll_layout = pm.scrollLayout (cr=True)
		
		# Checklist vertical layout
		checklist_vertical_layout = pm.columnLayout (adj=True)
		
		# Checklist header
		checklist_frame_layout = pm.frameLayout (l='Checker Options')
		
		opVars = pm.language.Env.optionVars
		
		# Show function checklist
		for fn_name in self.lookup_order:
		
			# If option is in opVars, use that value
			# Otherwise, use default value
			fn = self.functions[fn_name]
			if fn_name in opVars:
				option = opVars[fn_name]
				self.options[fn_name] = option
			else:
				option = self.options[fn_name]
		
			# Per-row layout
			checklist_row_layout = pm.rowLayout (nc=2, cl2=('right','center'), 
				cw2=CHECKLIST_COLUMN_WIDTHS)
			
			# Function description label
			pm.text (l=fn.desc, align='right')
			
			# Begin radio buttons
			radio_row_layout = pm.rowLayout (nc=3)
			collection = pm.radioCollection()

			# Draw skip radio button
			set_skip = pm.Callback (self.set_option, fn_name, 
				self.checker_option.SKIP)
			skip_button = pm.radioButton (l='Skip', onc=set_skip)
			
			# Draw check radio button
			if fn.checkFn:
				set_check = pm.Callback (self.set_option, fn_name, 
					self.checker_option.CHECK)
				check_button = pm.radioButton (l='Check', onc=set_check)
				
			# Draw cleanup radio button
			if fn.cleanupFn:
				set_cleanup = pm.Callback (self.set_option, fn_name, 
					self.checker_option.CLEANUP)
				cleanup_button = pm.radioButton (l='Cleanup', onc=set_cleanup)
				
			# End radio row collection
			pm.setParent('..')
			
			# End radio row layout
			pm.setParent('..')
			
			# End per-row layout
			pm.setParent ('..')
			
			# Set selected radio button based on selected option
			if option is self.checker_option.SKIP:
				selected = skip_button
			elif option is self.checker_option.CHECK:
				selected = check_button
			else:
				selected = cleanup_button
			
			pm.radioCollection (collection, edit=True, select=selected)
			
		# End checklist vertical layout
		pm.setParent ('..')
		
		# End checklist scroll layout
		pm.setParent ('..')
		
		log_frame_layout = pm.frameLayout (l='Log Output')
		
		# Start log scroll layout
		log_scroll_layout = pm.scrollLayout (cr=True, h=LOG_SCROLL_AREA_HEIGHT)
		
		# Log text object
		# The -32 is prevent the horizontal scrollbar from appearing
		self.log_text = pm.text (l=self.log_results, h=MAX_LOG_HEIGHT, 
			al='left', w=MAIN_WINDOW_DIMENSIONS[0]-32, ww=True)
		
		# End log scroll layout
		pm.setParent ('..')
		
		pm.setParent ('..')
		
		# Start button horizontal layout
		button_h_layout = pm.rowLayout(nc=3, cw3=(128,128,128),
			ct3=('both','both','both'), h=MAIN_BUTTON_AREA_HEIGHT)
		
		# If Run and Export Selected, check and attempt to export
		pm.button (l='Run and Export Selected', c=self.check_and_export)
		
		# If Check/Cleanup, run check and cleanup
		pm.button (l='Run', c=self.check)
		
		# If Cancel, close the window
		pm.button (l='Close', c=self.close_main_window)
		
		# End button horizontal layout
		pm.setParent ('..')
		
		# End main vertical layout
		pm.setParent ('..')
		
		pm.showWindow (self.main_window)
		
	
	# Sets an option in opVars
	def set_option (self, fn_name, option):
		self.options[fn_name] = option
		pm.language.Env.optionVars[fn_name] = option
		
	# Main check method
	def do_check (self, selected_objects):
	
		self.flagged_objects = {}
		self.cleaned_objects = {}
		objects_were_flagged = False
	
		# For each function
		for fn_name in self.lookup_order:
			
			# Skip if selected
			fn_option = self.options[fn_name]
			if fn_option is self.checker_option.SKIP:
				continue
				
			# Initialize count for function
			fn_group = self.functions[fn_name]
			self.flagged_objects[fn_group] = []
			
			is_cleanup = False
			
			# If check is selected
			if fn_option is self.checker_option.CHECK:
				self.flagged_objects[fn_group] = []
				
			# If cleanup is selected
			elif fn_option is self.checker_option.CLEANUP:
				self.cleaned_objects[fn_group] = []
				is_cleanup = True
				
			# Raise ValueError on invalid options
			elif fn_option is None:
				raise ValueError ('Option is None for function %s!' % (fn_name))
			else:
				raise ValueError ('Invalid option %s for function %s!' % 
					(fn_option, fn_name))
				
			# Iterate over selected objects
			for selected_object in selected_objects:
				if selected_object is None:
					continue
					
				do_flag = fn_group.checkFn(selected_object)
				if do_flag:
					objects_were_flagged = True
					if is_cleanup:
						self.cleaned_objects[fn_group].append (selected_object)
						fn_group.cleanupFn (selected_object)
					else:
						self.flagged_objects[fn_group].append (selected_object)
				
		# Print output to console
		result_string = "\n-----Check Complete-----\n"
		
		# Print flagged objects
		if len(self.flagged_objects) is not 0:
			result_string += "\n---Flagged Objects---"
			for key, value in self.flagged_objects.items():
				if len(value) is 0:
					continue
				result_string += "\n" + key.desc + ": "
				for flagged_object in value:
					result_string += flagged_object + " "
				
		# Print cleaned objects
		if len(self.cleaned_objects) is not 0:
			result_string += "\n\n---Cleaned Objects---"
			for key, value in self.cleaned_objects.items():
				result_string += "\n" + key.desc + ": "
				for cleaned_object in value:
					result_string += cleaned_object + " "

		# Update log
		self.log_results = self.word_wrap(result_string, LOG_CHARACTERS_PER_LINE)
		line_count = self.log_results.count('\n')
		log_height = line_count * LINE_HEIGHT
		pm.text (self.log_text, edit=True, label=result_string, h=log_height)
		
		if objects_were_flagged:
			return False
		return True
		
	# Performs check on all selected object
	# Returns true if no issues are found, false otherwise
	def check (self, *_):
		# Get all selected objects
		# Prompt the user if nothing is selected
		self.selected_objects = pm.ls(sl=1, type='dagNode')
		if len(self.selected_objects) is 0:
			pm.confirmDialog(m="No objects selected!", ma="left")
			return
			
		# Return true if ready to export
		ready_to_export = self.do_check(self.selected_objects)
		if ready_to_export:
			pm.confirmDialog(m="No issues found!", ma="left")
			return True
		else:
			pm.confirmDialog(m="Problems were found! Check log for details.", 
				ma="left")
			return False
		
	# Checks all selected objects and exports if no problems found
	def check_and_export (self, *_):
		ready_to_export = self.check()
		if ready_to_export:
			self.export_selected()
			self.close_main_window()
			
	# Exports all selected objects
	def export_selected (self):
		if len(self.selected_objects) is 0:
			pm.confirmDialog(m="No valid objects are selected!", ma="left")
			return
			
		filepath = pm.fileDialog2 (cap='FBX Export', ff='FBX export', ds=2)[0]
		print filepath
		
		self.do_export_as_fbx (filepath)
		
	# Exports an FBX to the specified path
	def do_export_as_fbx (self, path):
		#mel.eval('FBXExportInAscii -v true')
		pm.mel.FBXExportInAscii (v=True)
		#mel.eval('FBXExport -f ' + filename + ' -s')
		pm.mel.FBXExport (s=True, f=path)

		
	# Returns true if an object is not geometry
	def is_not_geometry (self, node):
		relatives = pm.listRelatives(node)
		for relative in relatives:
			if pm.nodeType(relative) == "mesh":
				return False
		
		return True
		
	# Removes the given object from the current selection
	def remove_from_selection (self, node):
		pm.select (node, d=True)

	# Returns true if the given object has a construction history that is not
	# cleared, false otherwise
	def has_construction_history (self, node):
		history = pm.listHistory (node)
		return len (history) > 1
		
	# Clears the given object's construction history
	def clear_construction_history (self, node):
		pm.general.delete (node, ch=True)

	# Returns true if the given object has any unfrozen transform attributes
	def has_nonzero_transform (self, node):
		translation = node.getTranslation()
		if not tuple(translation) == (0,0,0):
			return True
			
		rotation = node.getRotation()
		if not tuple(rotation) == (0,0,0):
			return True
	
		scale = node.getScale()
		if not tuple(scale) == (1,1,1):
			return True

		return False
		
	# Freezes the transform of the given object
	def freeze_transform (self, node):
		pm.general.makeIdentity(node, a=True)

	# Returns true if the given object has more than two UV sets
	def has_more_than_two_uvs (self, node):
		uv_sets = pm.modeling.polyUVSet (node, query=True, allUVSets=True)
		if uv_sets == None:
			return False
		if (len(uv_sets) > 2):
			return True
		return False
		
	# Removes any extra UV maps from the given object
	def remove_extra_uvs (self, node):
		all_uv_sets = pm.modeling.polyUVSet (node, query=True, allUVSets=True)
		num_uv_sets = len (all_uv_sets)
		i = 2
		while i < num_uv_sets:
			uv_set = all_uv_sets[i]
			pm.modeling.polyUVSet (node, delete=True, uvSet=uv_set)
			i += 1

	# Returns true if the given object has a default name, false otherwise
	def object_has_default_name (self, node):
		object_name = node
		for name in DEFAULT_OBJECT_NAMES:
			if object_name.find(name) != -1:
				return True
				
		return False
	
	# Returns a list of all materials with default names attached to the 
	# given object.
	def materials_with_default_names (self, node):
		flagged = False
		
		# Iterate over materials about to be exported
		for mat in self.get_materials (node):
			if self.material_has_default_name (mat):
				fn = self.functions['DEFAULTMATNAMES']
				self.flagged_objects[fn].append(mat)
				flagged = True
		
		return flagged
	
	# Returns true if the given material has a default name, false otherwise
	def material_has_default_name (self, mat):
		for default_name in DEFAULT_MATERIAL_NAMES:
			if mat.find(default_name) != -1:
				return True
				
		return False
		
	# Returns a list of all the materials attached to the given object
	def get_materials (self, node):
		geometry = node.getShape()
		if geometry is None:
			return None
			
		materials = []
		shading_groups = geometry.connections(type='shadingEngine')
		for shading_group in shading_groups:
		
			shading_group_mats = shading_group.connections(type='materialInfo')
			for sg_mat in shading_group_mats:
				for material_type in DEFAULT_MATERIAL_NAMES:
					found_materials = sg_mat.connections(type=material_type)
					materials.extend (found_materials)
			
		return materials
			
	# Closes the main UI window
	def close_main_window (self, *_):
		pm.deleteUI(self.main_window, wnd=True)
		
	def word_wrap (self, in_str, line_length):
		i = line_length
		str_len = len (in_str)
		while str_len > i:
			added = in_str[:i] + '\n' + in_str[i:]
			i += line_length + 1
			in_str = added
		return in_str
		
		
	# Class to hold the description and various aspects of a check function
	class checker_function(object):
		def __init__(self, checkFn, cleanupFn, desc):
			self.checkFn = checkFn
			self.cleanupFn = cleanupFn
			self.desc = desc
			
	# "Enum" to hold different option values
	class checker_option(object):
		SKIP    = 0
		CHECK   = 1
		CLEANUP = 2
			
# Boilerplate
if __name__ == "__main__":
	instance = unity_export_checker()