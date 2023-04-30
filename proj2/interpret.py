"""
jmeno: Vojtech Jahoda
login: xjahod06
date: 15.04.2020
version: python3.8
"""
import xml.etree.ElementTree as ET
import argparse
import sys
import re
from copy import deepcopy
import fileinput
import string

#pomocna funkce pro RE na přepis escape sequenci
def escape_encode(match):
	return chr(int(match.group(1)))	

class value_of_var(object):
	"""objekt na ukladani  hodnoty a typu"""
	def __init__(self, value, typ):
		self.value = value
		self.typ = typ
		if self.typ != None:	
			self.setvalue(self.typ,self.value)
	
	#vypis jednotlivych proměnnych
	def __str__(self):
		if self.typ == 'nil':
			return ''
		if self.typ == 'bool':
			if self.value == True:
				return 'true'
			else:
				return 'false'
		if self.typ == 'float':
			return str(self.value.hex())
		return str(self.value)
	
	#definovani jednotlivych hodnot ze stringu na datovy typ
	def setvalue(self,typ,value=None):
		self.typ = typ
		if typ == 'int':
			try:
				self.value = int(value)
			except ValueError as e:
				print(e,file=sys.stderr)
				sys.exit(32)
		elif typ == 'bool':
			if value.lower() == 'false':
				self.value = False
			elif value.lower() == 'true':
				self.value = True
		elif typ == 'nil':
			self.value = None
		elif typ == 'string':
			if value == None:
				self.value = ''
			else:
				self.value = re.sub(r"\\(\d{3})", escape_encode, value)
				#print(self.value)
		elif typ == 'float':
			try:
				self.value = float.fromhex(value)
			except ValueError as e:
				print(e,file=sys.stderr)
				sys.exit(32)
	
	def full_print(self):
		print('->full print:',self.typ,self.value)

#overeni promenne jestli je definovana a inicializovana
def validate_variable(frame,name,order,stop='yes'):
	if not name in frame:
		error_end(54,instruction_order=order)
	if frame[name].typ == None:
		if stop == 'yes':
			error_end(56,instruction_order=order)

#presun hodnoty do promenne v ramci
def move_instruction(frame,name,typ,value,order):
	if not name in frame:
		error_end(54,'move',order)
	if typ == 'var':
		frame_name = value.split('@')
		if frame_name[0] == 'GF':
			var = get_var_from_frame(global_frame,frame_name[1],order)
		elif frame_name[0] == 'TF' and temp_frame_defined == True:
			var = get_var_from_frame(temp_frame,frame_name[1],order)
		elif frame_name[0] == 'LF' and len(frame_stack) > 0:
			var = get_var_from_frame(frame_stack[-1],frame_name[1],order)
		else:
			error_end(55,'move',order)
		frame[name] = deepcopy(var)
	else:
		frame[name].setvalue(typ,value)
	#print(name,' set type:',frame[name].typ,' value:',frame[name].value)

#vypis na STDOUT
def write_instruction(frame,name,order):
	validate_variable(frame,name,order)
	print(frame[name],end='')
	#print('__',name,'__WRITE:',frame[name].value,'TYPE:',frame[name].typ)

#push symb (pouze hodnoty ne cele promenne) na stack
def pushs_instruction(frame,name,stack,order):
	validate_variable(frame,name,order)
	stack.append(deepcopy(frame[name]))

#ulozeni hodnoty ze stacku do promenne
def pops_instruction(frame,name,stack,order):
	if not name in frame:
		error_end(54,'pops',order)
	try:
		frame[name] = stack[-1]
	except IndexError as e:
		error_end(56,'pops',order)
	stack.pop()

#ziska hodnotu promenne z ramce
def get_var_from_frame(frame,name,order,stop='yes'):
	validate_variable(frame,name,order,stop)
	return frame[name]

#zmena hodnoty int na char
def int2char_instruction(frame,name,arg,order,var_list=None):
	if not name in frame:
		error_end(54,'int2char',order)
	if var_list == True:
		symb = arg
	else:
		symb = check_value(arg.attrib['type'],arg.text,order)
	if symb.typ != 'int':
		error_end(53,'int2char',order)
	try:
		char = chr(symb.value)	
	except ValueError:
		error_end(58,'int2char',order)
	frame[name].value = char
	frame[name].typ = 'string'
	#print('convert ',arg.text,' as ',char)

#convertovani floatu na INT a naopak podle parametru operator
def float_convert_instruction(frame,name,arg,order,operator,var_list = None):
	if not name in frame:
		error_end(54,operator,order)
	if var_list == True:
		symb = arg
	else:
		symb = check_value(arg.attrib['type'],arg.text,order)
	if operator == 'INT2FLOAT':
		if symb.typ != 'int':
			error_end(53,operator,order)
		try:
			convert = float(symb.value)
		except ValueError:
			error_end(58,'int2float',order)
		frame[name].value = convert
		frame[name].typ = 'float'

	elif operator == 'FLOAT2INT':
		if symb.typ != 'float':
			error_end(53,operator,order)
		try:
			convert =  int(symb.value)	
		except ValueError:
			error_end(58,'float2int',order)
		frame[name].value = convert
		frame[name].typ = 'int'

#vrati objekt value_of_var bud z ramce a nebo ze zadanych hodnot
def check_value(typ,text,order,stop='yes'):
	if typ == 'var':
		frame_name = text.split('@')
		if frame_name[0] == 'GF':
			return get_var_from_frame(global_frame,frame_name[1],order,stop)
		elif frame_name[0] == 'TF' and temp_frame_defined == True:
			return get_var_from_frame(temp_frame,frame_name[1],order,stop)
		elif frame_name[0] == 'LF' and len(frame_stack) > 0:
			return get_var_from_frame(frame_stack[-1],frame_name[1],order,stop)
		else:
			error_end(55,'',order)
	else:
		return value_of_var(text,typ)

#vsechny aritmeticke, bool a porovnavaci instrukce, deleni podle operatoru
def operator_instruction(frame,name,body,operator,order,var_list=None):
	if not name in frame:
		error_end(54,operator,order)
	if var_list == True:
		if body[0] == None:
			symb_1 = body[1]
		else:
			symb_1 = body[0]
			symb_2 = body[1]
	else:
		symb_1 = check_value(body[1].attrib['type'],body[1].text,order)
		try:
			symb_2 = check_value(body[2].attrib['type'],body[2].text,order)
		except IndexError:
			if operator != 'NOT':
				error_end(54,operator,order)
	if operator in ['ADD','SUB','MUL','IDIV','DIV']:
		if not symb_1.typ in ['int','float'] or not symb_2.typ in ['int','float'] or symb_2.typ != symb_1.typ:
			error_end(53,operator,order)
		if operator == 'ADD':
			frame[name].value = symb_1.value + symb_2.value
		elif operator == 'SUB':
			frame[name].value = symb_1.value - symb_2.value
		elif operator == 'MUL':
			frame[name].value = symb_1.value * symb_2.value
		elif operator == 'IDIV':
			if symb_1.typ == 'int' and symb_1.typ == 'int':
				try:
					frame[name].value = int(symb_1.value // symb_2.value)
				except ZeroDivisionError as e:
					print(e,file=sys.stderr)
					error_end(57,operator,order)
			else:
				error_end(53,operator,order)
		elif operator == 'DIV':
			try:
				frame[name].value = float(symb_1.value / symb_2.value)
			except ZeroDivisionError as e:
				print(e,file=sys.stderr)
				error_end(57,operator,order)
		if type(frame[name].value) == float:
			frame[name].typ = 'float'
		else:
			frame[name].typ = 'int'
	elif operator in ['LT','GT','EQ']:
		if symb_1.typ == symb_2.typ and (symb_1.typ != 'nil' or symb_2.typ != 'nil') or ((symb_1.typ == 'nil' or symb_2.typ == 'nil') and operator == 'EQ'):
			if operator == 'LT':
				frame[name].value = symb_1.value < symb_2.value
			elif operator == 'GT':
				frame[name].value = symb_1.value > symb_2.value
			elif operator == 'EQ':
				frame[name].value = symb_1.value == symb_2.value
		else:
			error_end(53,operator,order)
		frame[name].typ = 'bool'
	elif operator == 'NOT':
		if symb_1.typ == 'bool':
			frame[name].value = not symb_1.value
			frame[name].typ = 'bool'
			#print(name,'[',frame[name],'] => ',operator,symb_1)s
			return
		else:
			error_end(53,operator,order)
	elif operator in ['OR','AND']:
		if symb_1.typ != 'bool' or symb_2.typ != 'bool':
			error_end(53,operator,order)
		if operator == 'AND':
			frame[name].value = symb_1.value and symb_2.value
		elif operator == 'OR':
			frame[name].value = symb_1.value or symb_2.value
		frame[name].typ = 'bool'


	#print(name,'[',frame[name],'] => ',symb_1,' ',operator,' ',symb_2)

#definuje promennou v ramci
def defvar_instruction(frame,name,order):
	if name in frame:
		error_end(52,'defvar',order)
	frame[name] = value_of_var(None, None)

#prepis stringu na cislo
def stri2int_instruction(frame,name,arg_1,arg_2,order,var_list=None):
	if not name in frame:
		error_end(54,'stri2int',order)
	if var_list == True:
		symb_1 = arg_1
		symb_2 = arg_2
	else:
		symb_1 = check_value(arg_1.attrib['type'],arg_1.text,order)
		symb_2 = check_value(arg_2.attrib['type'],arg_2.text,order)
	if symb_1.typ == 'string' and symb_2.typ == 'int':
		if symb_2.value < 0:
			error_end(58,'stri2int',order)
		try:
			frame[name].value = ord(symb_1.value[symb_2.value])
			#print(name,'=',frame[name],'=>',symb_1.value,'[',symb_2.value,']')
			frame[name].typ = 'int'
		except IndexError:
			error_end(58,'stri2int',order)
	else:
		error_end(53,'stri2int',order)

#cteni z STDIN, nebo po zadani souboru --input z souboru
def read_instruction(frame,name,arg,order):
	global input_counter #citas radku v souboru se vstupy
	if not name in frame:
		error_end(54,'read',order)
	if arg.attrib['type'] == 'type':
		try:
			if input_data == None:
				var = input()
			else:
				var = input_data[input_counter]
				if var[-1] == '\n':
					var = var[:-1]
				input_counter += 1
		except:
			frame[name].setvalue('nil')
			return
		if var == None:
			frame[name].setvalue('nil')
		elif arg.text == 'int':
			try:
				frame[name].value,frame[name].typ = int(var), 'int'
			except:
				frame[name].setvalue('nil')
		elif arg.text == 'float':
			try:
				frame[name].value,frame[name].typ = float.fromhex(var), 'float'
			except:
				frame[name].setvalue('nil')
		elif arg.text == 'string':
			frame[name].value,frame[name].typ = var, 'string'
		elif arg.text == 'bool':
			if var.lower() == 'true':
				frame[name].value = True
				frame[name].typ = 'bool'
			else:
				frame[name].value = False
				frame[name].typ = 'bool'
		#print(name,frame[name].value,frame[name].typ)
	else:
		error_end(53,'read',order)

#spojeni 2 stringu
def concat_instruction(frame,name,arg_1,arg_2,order):
	if not name in frame:
		error_end(54,'concat',order)
	symb_1 = check_value(arg_1.attrib['type'],arg_1.text,order)
	symb_2 = check_value(arg_2.attrib['type'],arg_2.text,order)
	if symb_1.typ == 'string' and symb_2.typ == 'string':
		frame[name].value = symb_1.value + symb_2.value
		frame[name].typ = 'string'
	else:
		error_end(53,'concat',order)
	#print(name,'=>',frame[name].value,'=',symb_1.value,'+',symb_2.value)

#vraci delku stringu v instrukci
def strlen_instruction(frame,name,arg,order):
	if not name in frame:
		error_end(54,'strlen',order)
	symb = check_value(arg.attrib['type'],arg.text,order)
	if symb.typ == 'string':
		frame[name].value = int(len(symb.value))
		frame[name].typ = 'int'
		#print(name,'len',frame[name])
	else:
		error_end(53,'strlen',order)

#bud ziska char na dane pozici ve stringu, nebo ji nahradi (urcuje se podle operatoru)
def get_set_char_instruction(frame,name,arg_1,arg_2,operator,order):
	if not name in frame:
		error_end(54,operator,order)
	symb_1 = check_value(arg_1.attrib['type'],arg_1.text,order)
	symb_2 = check_value(arg_2.attrib['type'],arg_2.text,order)
	if operator == 'GETCHAR':
		if symb_1.typ == 'string' and symb_2.typ == 'int':
			if symb_2.value < 0:
				error_end(58,operator,order)
			try:
				frame[name].value = symb_1.value[symb_2.value]
				frame[name].typ = 'string'
				#print(name,'=',frame[name].value,'=>',symb_1.value,'[',symb_2.value,']')
			except:
				error_end(58,operator,order)
		else:
			error_end(53,operator,order)
	elif operator == 'SETCHAR':
		validate_variable(frame,name,order)
		if frame[name].typ == 'string' and symb_1.typ == 'int' and symb_2.typ == 'string':
			if symb_1.value < 0:
				error_end(58,operator,order)
			try:
				#print(name,'=',frame[name].value,'[',symb_1.value,']','<=',symb_2.value)
				s = list(frame[name].value)
				s[symb_1.value] = symb_2.value[0]
				frame[name].value = "".join(s)
				frame[name].typ = 'string'
				#print(frame[name].value)
			except:
				error_end(58,operator,order)
		else:
			error_end(53,operator,order)

#vraci nazev datoveho typu jako string
def type_instruction(frame,name,arg,order):
	if not name in frame:
		error_end(54,'type',order)
	symb = check_value(arg.attrib['type'],arg.text,order,stop='no')
	if symb.typ == None:
		frame[name].value = ''
	else:
		frame[name].value = symb.typ
	frame[name].typ = 'string' 
	#print(name,frame[name].value)

#podminene skoky v programu
def jump_eq_instruction(label,arg_1,arg_2,i,operator,order,var_list=None):
	if var_list == True:
		symb_1 = arg_1
		symb_2 = arg_2
	else:
		symb_1 = check_value(arg_1.attrib['type'],arg_1.text,order)
		symb_2 = check_value(arg_2.attrib['type'],arg_2.text,order)
	if symb_1.typ == symb_2.typ or symb_1.typ == 'nil' or symb_2.typ == 'nil':
		if operator == 'JUMPIFEQ':
			if symb_1.value == symb_2.value:
				return label_list[label] - 1
			else:
				return i
		if operator == 'JUMPIFNEQ':
			if symb_1.value != symb_2.value:
				return label_list[label] - 1
			else:
				return i
	else:
		error_end(53,operator,order)

#overi validitu jedntlivych XML tagu a podle arg_count urci kolik argumentu ma dana instukce mit
def check_valid_xml(instruction,arg_count):
	arg_list = ['arg'+str(i+1) for i in range(arg_count)]
	instruction[:] = sorted(instruction,key=lambda arg: arg.tag)
	if len(instruction[:]) != arg_count:
		error_end(32,instruction.attrib['opcode'],instruction.attrib['order'])
	#print(instruction[0])
	if instruction.tag != 'instruction':
		error_end(32,instruction.attrib['opcode'],instruction.attrib['order'])
	for arg in instruction:
		if not arg.tag in arg_list:
			error_end(32,instruction.attrib['opcode'],instruction.attrib['order'])

#zjednoduseny vypis error hlasek	
def error_end(code,instruction_name='',instruction_order=''):
	print("error on instruction",instruction_name,' no.',instruction_order,file=sys.stderr)
	sys.exit(code)

#vypis jednotlivych slovniku pro instrukci BREAK
def write_down_dictionary(dictionary,indent=0):
	if len(dictionary) == 0:
		print(indent*' ',"empty",file=sys.stderr)
	for name in dictionary:
		print(indent*' ',name,"\tvalue: "+str(dictionary[name].value),"\ttype: "+str(dictionary[name].typ),file=sys.stderr)

#vypis aktualnich dat programu na STDERR
def break_instruction(instruction,global_frame,temp_frame,frame_stack,temp_frame_defined,stack_symb,i):
	print("position",instruction.attrib['order'],file=sys.stderr)
	print("completed instructions: ",g,file=sys.stderr)
	print("\nglobal frame: ",file=sys.stderr)
	write_down_dictionary(global_frame,len("global frame: "))
	print("\ntemp frame:",file=sys.stderr)
	write_down_dictionary(temp_frame,len("temp frame: "))
	print("\nlocal frame: ",file=sys.stderr)
	write_down_dictionary(frame_stack[-1],len("local frame: "))
	if len(frame_stack) > 0:
		print("\nframes on stack: ",file=sys.stderr)
		for frame in frame_stack:
			if frame_stack[-1] == frame:
				print(len("frames on stac")*' ','[LF]',file=sys.stderr)
			else:
				print(len("frames on stac")*' ','['+str(frame_stack.index(frame))+']',file=sys.stderr)
			write_down_dictionary(frame,len("frames on stack: "))
	if temp_frame_defined == True:
		print("\nin frame: True",file=sys.stderr)
	else:
		print("\nin frame: False",file=sys.stderr)
	print("symbol stack: ",stack_symb,file=sys.stderr)
	print(file=sys.stderr)

class statistics(object):
	"""objekt na ukladani statistics pro rozsireni STATI"""
	def __init__(self, file, output_list):
		self.file = file
		self.output_list = output_list
		self.validity = False
		self.insts = 0
		self.vars = 0
		self.verify()

	def verify(self):
		if self.file == None and len(self.output_list) == 0:
			return
		if self.file == None and len(self.output_list) != 0: 
			print("invalid arg combination",file=sys.stderr)
			sys.exit(10)

	def write(self):
		if self.file == None:
			return
		try:
			f = open(self.file,"w+")
		except Exception as e:
			print(e,file=sys.stderr)
			sys.exit(12)
		for line in self.output_list:
			if line == '--insts':
				f.write(str(self.insts)+"\n")
			elif line == '--vars':
				f.write(str(self.vars)+"\n")

#pocita maximalni počet proměnny v ramcich pro rozsireni STATI
def max_variables(global_frame,temp_frame,frame_stack,max_var):
	global_count = sum(map(lambda x : global_frame[x].typ != None, global_frame))
	temp_count = sum(map(lambda x : temp_frame[x].typ != None, temp_frame))
	if len(frame_stack) > 0:
		local_count = sum(map(lambda x : frame_stack[-1][x].typ != None, frame_stack[-1]))
	else:
		local_count = 0
	count = global_count + temp_count + local_count
	if count > max_var:
		return count
	else:
		return max_var

ar = []

#parsovani argumentu programu
parser = argparse.ArgumentParser(description='Interpret XML reprezentace kodu', usage='%(prog)s [OPTIONS]')
group = parser.add_argument_group()
group.add_argument('--source',metavar='file',help='vstupni soubor s XML reprezentaci zdrojoveho kodu')
group.add_argument('--input',metavar='file',help='soubor se vstupy pro samotnou interpretaci zadaneho zdrojoveho kodu')
group_stati = parser.add_argument_group('stati')
group_stati.add_argument('--stats',metavar='file',help='soubor pro vypis statistik rozsireni STATI')
group_stati.add_argument('--insts',action='count',help='vypis poctu vykonanych instrukci behem interpretace do statistik')
group_stati.add_argument('--vars',action='count',help='vypis maximalniho poctu inicializovanych promennych pritomnych ve vsech platnych ramcich behem interpretace zadaneho programu do statistik')
args = parser.parse_args()

stati_out = []
for arg in sys.argv:
	if arg in ['--vars','--insts']:
		stati_out.append(arg)

stati = statistics(args.stats,stati_out)

#print("source:",args.source)
#print("input:",args.input)

if args.source == None and args.input == None:
	print("interpret.py: error: one of the arguments --source --input is required",file=sys.stderr)
	sys.exit(10)

if args.source != None:
	try:
		tree = ET.parse(args.source)
		root = tree.getroot()
	except ET.ParseError as e:
		print(e,file=sys.stderr)
		sys.exit(31)
	except FileNotFoundError as e:
		print(e,file=sys.stderr)
		sys.exit(11)
else:
	try:
		tree = ET.parse(sys.stdin)
		root = tree.getroot()
	except ET.ParseError as e:
		print(e,file=sys.stderr)
		sys.exit(31)
	except FileNotFoundError as e:
		print(e,file=sys.stderr)
		sys.exit(11)

if args.input != None:
	try:
		f = open(args.input,'r')
		input_data = f.readlines()
	except FileNotFoundError as e:
		print(e,file=sys.stderr)
		sys.exit(11)
else:
	input_data = None

if not root.attrib['language'].lower() == 'ippcode20':
	print("unknown language",file=sys.stderr)
	sys.exit(32)

try:
	a = root[0]
except IndexError:
	sys.exit(0)

input_counter = 0

stack_symb = []
global_frame = {}

stack_frame = {}
defvar_instruction(stack_frame,'stack',0)

frame_stack = [] 

temp_frame = {}
temp_frame_defined = False

position_stack = []

i = 0
g = 0
label_list = {}

for instruction in root:
	try:
		instruction.attrib['opcode']
		instruction.attrib['order']
	except KeyError as e:
		print("KeyError",e,file=sys.stderr)
		sys.exit(32)
	if not instruction.attrib['order'].isdigit():
		error_end(32,instruction.attrib['opcode']+" not a numeric order",instruction.attrib['order'])
		

try:
	root = sorted(root,key=lambda instruction: int(instruction.attrib['order']))
except KeyError as e:
	print(e,file=sys.stderr)
	sys.exit(32)

seen = []

for instruction in root:
	if int(instruction.attrib['order']) <= 0:
		error_end(32,instruction.attrib['opcode'],instruction.attrib['order'])
	if not instruction.attrib['order'] in seen:
		seen.append(instruction.attrib['order'])
	else:
		error_end(32,"MOVE wrong order",instruction.attrib['order'])
	#print(instruction.tag,instruction.attrib)
	if instruction.attrib['opcode'].upper() == 'LABEL':
		if instruction[0].attrib['type'] == 'label':
			if instruction[0].text in label_list:
				error_end(52,instruction.attrib['opcode'],instruction.attrib['order'])
			else:
				label_list[instruction[0].text] = i
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])
	i += 1

#print(label_list)

max_var = 0

i = 0
while i < len(root):
	g += 1
	instruction = root[i]
	if instruction.attrib['opcode'].upper() == 'DEFVAR':
		check_valid_xml(instruction,1)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				defvar_instruction (global_frame,frame_name[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				defvar_instruction(temp_frame,frame_name[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				defvar_instruction(frame_stack[-1],frame_name[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])
				
	elif instruction.attrib['opcode'].upper() == 'WRITE':
		check_valid_xml(instruction,1)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				write_instruction(global_frame,frame_name[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				write_instruction(temp_frame,frame_name[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				write_instruction(frame_stack[-1],frame_name[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
				
		elif arg.attrib['type'] == 'string' or arg.attrib['type'] == 'bool' or arg.attrib['type'] == 'nil' or arg.attrib['type'] == 'int' or arg.attrib['type'] == 'float':
			print(value_of_var(arg.text,arg.attrib['type']),end='')
		else:
			error_end(32,instruction.attrib['opcode'],instruction.attrib['order'])
	
	elif instruction.attrib['opcode'].upper() == 'MOVE':
		check_valid_xml(instruction,2)
		arg= instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				move_instruction(global_frame,frame_name[1],instruction[1].attrib['type'],instruction[1].text,instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				move_instruction(frame_stack[-1],frame_name[1],instruction[1].attrib['type'],instruction[1].text,instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				move_instruction(temp_frame,frame_name[1],instruction[1].attrib['type'],instruction[1].text,instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

				
	elif instruction.attrib['opcode'].upper() == 'PUSHS':
		check_valid_xml(instruction,1)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				pushs_instruction(global_frame,frame_name[1],stack_symb,instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				pushs_instruction(temp_frame,frame_name[1],stack_symb,instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				pushs_instruction(frame_stack[-1],frame_name[1],stack_symb,instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		if arg.attrib['type'] == 'string' or arg.attrib['type'] == 'bool' or arg.attrib['type'] == 'nil' or arg.attrib['type'] == 'int' or arg.attrib['type'] == 'float':
			stack_symb.append(value_of_var(arg.text,arg.attrib['type']))
	
	elif instruction.attrib['opcode'].upper() == 'POPS':
		check_valid_xml(instruction,1)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				pops_instruction(global_frame,frame_name[1],stack_symb,instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				pops_instruction(temp_frame,frame_name[1],stack_symb,instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				pops_instruction(frame_stack[-1],frame_name[1],stack_symb,instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])
	
	elif instruction.attrib['opcode'].upper() == 'INT2CHAR':
		check_valid_xml(instruction,2)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				int2char_instruction(global_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				int2char_instruction(temp_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				int2char_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])		
	
	elif instruction.attrib['opcode'].upper() in ['ADD','SUB','MUL','IDIV','LT','GT','EQ','AND','OR','NOT','DIV']:
		if instruction.attrib['opcode'] == 'NOT':
			check_valid_xml(instruction,2)
		else:
			check_valid_xml(instruction,3)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				operator_instruction(global_frame,frame_name[1],instruction,instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				operator_instruction(temp_frame,frame_name[1],instruction,instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				operator_instruction(frame_stack[-1],frame_name[1],instruction,instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'CREATEFRAME':
		check_valid_xml(instruction,0)
		temp_frame.clear()
		temp_frame_defined = True

	elif instruction.attrib['opcode'].upper() == 'PUSHFRAME':
		check_valid_xml(instruction,0)
		if temp_frame_defined == True:
			frame_stack.append(deepcopy(temp_frame))
			temp_frame.clear()
			temp_frame_defined = False
		else:
			error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'POPFRAME':
		check_valid_xml(instruction,0)
		try:
			temp_frame .clear()
			temp_frame = deepcopy(frame_stack[-1])
			del frame_stack[-1]
			temp_frame_defined = True
		except IndexError:
			error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'STRI2INT':
		check_valid_xml(instruction,3)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				stri2int_instruction(global_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				stri2int_instruction(temp_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				stri2int_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'READ':
		check_valid_xml(instruction,2)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				read_instruction(global_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				read_instruction(temp_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				read_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'CONCAT':
		check_valid_xml(instruction,3)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				concat_instruction(global_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				concat_instruction(temp_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				concat_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction[2],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'STRLEN':
		check_valid_xml(instruction,2)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				strlen_instruction(global_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				strlen_instruction(temp_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				strlen_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() in ['GETCHAR','SETCHAR']:
		check_valid_xml(instruction,3)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				get_set_char_instruction(global_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				get_set_char_instruction(temp_frame,frame_name[1],instruction[1],instruction[2],instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				get_set_char_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction[2],instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'TYPE':
		check_valid_xml(instruction,2)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				type_instruction(global_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				type_instruction(temp_frame,frame_name[1],instruction[1],instruction.attrib['order'])
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				type_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction.attrib['order'])
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'JUMP':
		check_valid_xml(instruction,1)
		if instruction[0].attrib['type'] == 'label':
			if instruction[0].text in label_list:
				i = label_list[instruction[0].text]-1
			else:
				error_end(52,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'CALL':
		check_valid_xml(instruction,1)
		if instruction[0].attrib['type'] == 'label':
			if instruction[0].text in label_list:
				position_stack.append(i)
				i = label_list[instruction[0].text]-1
			else:
				error_end(52,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'RETURN':
		check_valid_xml(instruction,0)
		try:
			i = position_stack[-1]
			position_stack.pop()
		except IndexError:
			error_end(56,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() in ['JUMPIFEQ','JUMPIFNEQ']:
		check_valid_xml(instruction,3)
		if instruction[0].attrib['type'] == 'label':
			if instruction[0].text in label_list:
				i = jump_eq_instruction(instruction[0].text,instruction[1],instruction[2],i,instruction.attrib['opcode'].upper(),instruction.attrib['order'])
			else:
				error_end(52,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'EXIT':
		check_valid_xml(instruction,1)
		symb = check_value(instruction[0].attrib['type'],instruction[0].text,instruction.attrib['order'])
		if symb.typ == 'int':
			if 0 <= symb.value <= 49:
				sys.exit(symb.value)
			else:
				error_end(57,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'DPRINT':
		check_valid_xml(instruction,1)
		symb = check_value(instruction[0].attrib['type'],instruction[0].text,instruction.attrib['order'])
		print(symb.value,file=sys.stderr)

	elif instruction.attrib['opcode'].upper() == 'BREAK':
		check_valid_xml(instruction,0)
		break_instruction(instruction,global_frame,temp_frame,frame_stack,temp_frame_defined,stack_symb,i,g)

	elif instruction.attrib['opcode'].upper() == 'LABEL':
		check_valid_xml(instruction,1)
		pass

	#prepis stack instrukci na normalni pomoci "fake" ramce a promenne
	elif instruction.attrib['opcode'].upper() in ['ADDS','SUBS','MULS','IDIVS','LTS','GTS','EQS','ANDS','ORS','NOTS','DIVS']:
		check_valid_xml(instruction,0)
		symb_2 = stack_symb.pop()
		if instruction.attrib['opcode'].upper() != 'NOTS':
			symb_1 = stack_symb.pop()
		else:
			symb_1 = None

		operator_instruction(stack_frame,'stack',[symb_1,symb_2],instruction.attrib['opcode'].upper()[:-1],instruction.attrib['order'],True)
		pushs_instruction(stack_frame,'stack',stack_symb,instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'CLEARS':
		check_valid_xml(instruction,0)
		stack_symb.clear()

	elif instruction.attrib['opcode'].upper() == 'STRI2INTS':
		check_valid_xml(instruction,0)
		symb_2 = stack_symb.pop()
		symb_1 = stack_symb.pop()
		stri2int_instruction(stack_frame,'stack',symb_1,symb_2,instruction.attrib['order'],True)
		pushs_instruction(stack_frame,'stack',stack_symb,instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() == 'INT2CHARS':
		check_valid_xml(instruction,0)
		symb_1 = stack_symb.pop()
		int2char_instruction(stack_frame,'stack',symb_1,instruction.attrib['order'],True)
		pushs_instruction(stack_frame,'stack',stack_symb,instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() in ['INT2FLOATS','FLOAT2INTS']:
		check_valid_xml(instruction,0)
		symb_1 = stack_symb.pop()
		int2char_instruction(stack_frame,'stack',symb_1,instruction.attrib['order'],True)
		float_convert_instruction(stack_frame,'stack',symb_1,instruction.attrib['order'],instruction.attrib['opcode'].upper()[:-1],True)
		pushs_instruction(stack_frame,'stack',stack_symb,instruction.attrib['order'])


	elif instruction.attrib['opcode'].upper() in ['JUMPIFEQS','JUMPIFNEQS']:
		check_valid_xml(instruction,1)
		if instruction[0].attrib['type'] == 'label':
			if instruction[0].text in label_list:
				symb_2 = stack_symb.pop()
				symb_1 = stack_symb.pop()
				i = jump_eq_instruction(instruction[0].text,symb_1,symb_2,i,instruction.attrib['opcode'].upper()[:-1],instruction.attrib['order'],True)
			else:
				error_end(52,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	elif instruction.attrib['opcode'].upper() in ['INT2FLOAT','FLOAT2INT']:
		check_valid_xml(instruction,2)
		arg = instruction[0]
		if arg.attrib['type'] == 'var':
			frame_name = arg.text.split('@')
			if frame_name[0] == 'GF':
				float_convert_instruction(global_frame,frame_name[1],instruction[1],instruction.attrib['order'],instruction.attrib['opcode'].upper())
			elif frame_name[0] == 'TF' and temp_frame_defined == True:
				float_convert_instruction(temp_frame,frame_name[1],instruction[1],instruction.attrib['order'],instruction.attrib['opcode'].upper())
			elif frame_name[0] == 'LF' and len(frame_stack) > 0:
				float_convert_instruction(frame_stack[-1],frame_name[1],instruction[1],instruction.attrib['order'],instruction.attrib['opcode'].upper())
			else:
				error_end(55,instruction.attrib['opcode'],instruction.attrib['order'])
		else:
			error_end(53,instruction.attrib['opcode'],instruction.attrib['order'])

	else:
		print("unknown instruction",instruction.attrib['opcode']," order: ",instruction.attrib['order'],file=sys.stderr)
		sys.exit(32)

	i += 1
	max_var = max_variables(global_frame,temp_frame,frame_stack,max_var)

stati.insts = g
stati.vars = max_var
stati.write()