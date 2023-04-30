<?php
/****************************************************************/
/*						Prvni projekt z IPP						*/
/*						  Vojtech Jahoda						*/
/*																*/
/*					Analyzátor kódu v IPPcode20					*/
/*					 		 parse.php							*/
/*							11.03.2020							*/
/****************************************************************/
$label_array = array(); // pole na ukladani aparametru rozsireni

//kontrola var podle RegEx
function verify_var($string){
	if(preg_match('/^(GF@|LF@|TF@)([a-z,A-Z,_, -, $, &, %, *, !, ?][\w,_, -, $, &, %, *, !, ?]*)$/',$string)){
		preg_match_all('/^(GF@|LF@|TF@)([a-z,A-Z,_, -, $, &, %, *, !, ?][\w,_, -, $, &, %, *, !, ?]*)$/',$string,$matches);
		$matches[2][0] = $matches[0][0];
		$matches[1][0] = "var";
		return $matches;
	}
	return NULL;
}

//kontrola navesti podle RegEx
function verify_label($string){
	global $label_array;
	if(preg_match('/^([a-z,A-Z,_, -, $, &, %, *, !, ?][\w,_, -, $, &, %, *, !, ?]*)$/',$string)){
		preg_match_all('/^([a-z,A-Z,_, -, $, &, %, *, !, ?][\w,_, -, $, &, %, *, !, ?]*)$/',$string,$matches);
		array_push($label_array, $matches[0][0]);// push do pole labelu kvuli rozsireni
		return $matches;
	}
	return NULL;
}

function check_string($string){
	preg_match_all('/[^\\\\,0-9]+|\\\\\d{3}/m', $string, $matches);
	return $matches;
}

//nasledna kontrola vystupu programu pro escape sequence a zlepseni citelnosti
function string_translate($string){
	$count = 1;
	while ($count != 0) { $string = preg_replace("/(>.*)(')(.*<)/",'\1&apos;\3',$string,-1,$count);}
	$count = 1;
	while ($count != 0) { $string = preg_replace('/(>.*)(")(.*<)/','\1&quot;\3',$string,-1,$count);}
	$count = 1;
	while ($count != 0) { $string = preg_replace('/><\/instruction>/',">\n  </instruction>",$string,-1,$count);}
	return $string;
}

//overeni správnosti symbolu tj. string/bool/int/nil
function verify_symb($string){
	if(preg_match('/^(nil)@(nil)$/',$string)){
		preg_match_all('/^(nil)@(nil)$/',$string,$matches);
		return $matches;
	} elseif(preg_match('/^(bool)@(true|false)$/',$string)){
		preg_match_all('/^(bool)@(true|false)$/',$string,$matches);
		return $matches;
	} elseif(preg_match('/^(int)@([+-]?\d+)$/',$string)){
		preg_match_all('/^(int)@([+-]?\d+)$/',$string,$matches);
		return $matches;
	} elseif(preg_match('/^(string)@(.*)$/',$string)){
		preg_match_all('/^(string)@(.*)$/',$string,$matches);
		return $matches;
	} else{
		return verify_var($string);
	}
}

//obejkt instrukce, který dokáže rozpoznat a uložit argumety podle inicializace
class master_instruction{
	function __construct($params,$param_count,$arg_types=[NULL]){
		$this->err_code = 0; //pormenna na návrat chyby
		if (count($params) == $param_count){
			$this->name = $params[0];
			for ($i=1; $i < 4; $i++) { //kotnrola počtu argumentu
				if(isset($arg_types[$i-1])){
					$this->arg($i,$arg_types[$i-1],$params[$i]);
				}
			}
		}else{
			$this->err_code = 23;
		}
	}
	//fce na ulozeni chyb a nasledna dynamicka tvorba promennych objektu
	function arg($order,$type,$content){
		switch ($type) {
			case "var":
				if ($matches = verify_var($content)){
					$this->arg_name{$order} = $matches[2][0];
					$this->arg_type{$order} = $matches[1][0];
				} else {
					$this->err_code = 23;
				}
				break;
			case "label":
				if ($matches = verify_label($content)){
					$this->arg_name{$order} = $matches[1][0];
					$this->arg_type{$order} = "label";
				} else {
					$this->err_code = 23;
				}
				break;
			case "symb":
				if ($matches = verify_symb($content)){
					$this->arg_name{$order} = $matches[2][0];
					$this->arg_type{$order} = $matches[1][0];
				} else {
					$this->err_code = 23;
				}
				break;
			case "type":
				if(preg_match('/^(int|string|bool)$/',$content)){
					preg_match_all('/^(int|string|bool)$/',$content,$matches);
					$this->arg_name{$order} = $matches[1][0];
					$this->arg_type{$order} = "type";
				} else {
					$this->err_code = 23;
				}
				break;
			default:
				$this->err_code = 99;
				return NULL;
				break;
		}
	}
	
}

//objekt na ukladani statistik pro rozsireni STATP, nacteni z parametru programu
class statistics{
	
	function __construct(){
		$this->filename = null;
		$this->comment = 0;
		$this->jump = 0;
		$this->label = 0;
		$this->loc = 0;
		$this->output_stats = array();
	}
	//funkce která se volá na konci rpogramu, pokud je něco nastaveno tak se to vypise do statistik
	function write_down() {
		if (!isset($this->filename)){
			if (count($this->output_stats) != 0){
				fwrite(STDERR, "[10] Chybí-li pri zadani --loc, --comments, --labels nebo --jumps, parametr --stats\n");
				exit(10);
			}
			return;
		}
		$out = fopen($this->filename, "w+") or die("Unable to open file!");
		foreach ($this->output_stats as $line) {
			switch ($line) {
				case 'loc':
					fwrite($out, $this->loc."\n");
					break;
				case 'jumps':
					fwrite($out, $this->jump."\n");
					break;
				case 'labels':
					fwrite($out, $this->label."\n");
					break;
				case 'comments':
					fwrite($out, $this->comment."\n");
					break;
				
				default:
					break;
			}
		}
		fclose($out);
	}
}

$stats = new statistics();

unset($argv[0]);
$i = 1;
while (count($argv) != 0) {
	switch ($argv[$i]) {
		case '--help':
			if (count($argv) == 1){
				echo "program parse.php\n";
				echo "program je urcen na preklad z ippcode20 do XML a nasledneho generovani\n";
				echo "--help        pro zobrazeni teto napovedy\n";
				echo "pro rozsireni STATP\n";
				echo "--stats       pro urceni ulozeni souboru\n";
				echo "--loc         pro vypis poctu radku\n";
				echo "--jumps       pro vypis poctu skoku podminenych/nepodminenych\n";
				echo "--labels      pro vypis poctu poucitych unikatnich navesti\n";
				echo "--comments    pro vypis poctu komentaru\n";
				return;
			}else{
				fwrite(STDERR, "[10] help je samostatny argument \n");
				exit(10);
			}
			break;
		case '--loc':
			array_push($stats->output_stats, "loc");
			break;
		case '--jumps':
			array_push($stats->output_stats, "jumps");
			break;
		case '--labels':
			array_push($stats->output_stats, "labels");
			break;
		case '--comments':
			array_push($stats->output_stats, "comments");
			break;
		default:
			$stats_file = getopt(null,array("stats:"));
			if (isset($stats_file['stats'])){
				$stats->filename = $stats_file['stats'];
				if ($argv[$i] == "--stats") {
					unset($argv[$i+1]);
				}
				break;
			}
			fwrite(STDERR, "[10] neplatny parametr\n");
			exit(10);
	}
	
	unset($argv[$i]);
	$i++;
}


$instruction_array = array();
$start = True;

//hlavni cyklus cteni radku
while ($line = fgets(STDIN)) {
	preg_match_all('/^([^#\s]*)\s*([^#\s]*)\s*([^#\s]*)\s*([^#\s]*)\s*\s?(#.*)?/',$line,$matches);
	$split = array();
	for ($i=1; $i < 6; $i++) {
		if ($matches[$i][0] != ""){
			if (substr($matches[$i][0], 0,1) == '#'){
				$stats->comment++;
				continue;
			}
			$split[$i-1] = $matches[$i][0];
		}
	}
	//kontorla hlavicky programu
	if ($start == True){
		if(!isset($split[0])){continue;}
		
		if (count($split) == 1 and strtoupper($split[0]) == ".IPPCODE20"){
			$start = False;
			continue;
		}else{
			fwrite(STDERR, "[21] chybná nebo chybějící hlavička ve zdrojovém kódu zapsaném v IPPcode20\n");
			exit(21);
		}
	}
	if(!isset($split[0])){continue;}
	//urceni typu instrukce
	switch ($split[0] = strtoupper($split[0])){
		case "READ":
			array_push($instruction_array,new master_instruction($split,3, ["var", "type"]));
			break;
		case "JUMPIFEQ":
		case "JUMPIFNEQ":
			$stats->jump++;
			array_push($instruction_array,new master_instruction($split,4, ["label", "symb", "symb"]));
			break;
		case "MOVE":
		case "INT2CHAR":
		case "TYPE":
		case "NOT":
		case "STRLEN":
			array_push($instruction_array,new master_instruction($split,3, ["var", "symb"]));
			break;
		case "RETURN":
			$stats->jump++;
		case "POPFRAME":
		case "PUSHFRAME":
		case "CREATEFRAME":
		case "BREAK":
			array_push($instruction_array,new master_instruction($split,1));
			break;
		case "JUMP":
		case "CALL":
			$stats->jump++;
		case "LABEL":
			array_push($instruction_array,new master_instruction($split,2, ["label"]));
			break;
		case "EXIT":
		case "WRITE":
		case "PUSHS":
		case "DPRINT":
			array_push($instruction_array,new master_instruction($split,2, ["symb"]));
			break;
		case "DEFVAR":
		case "POPS":
			array_push($instruction_array,new master_instruction($split,2, ["var"]));
			break;
		case "MUL":
		case "IDIV":
		case "ADD":
		case "SUB":
		case "LG":
		case "GT":
		case "EQ":
		case "AND":
		case "OR":
		case "STRI2INT":
		case "CONCAT":
		case "GETCHAR":
		case "SETCHAR":
			array_push($instruction_array,new master_instruction($split,4, ["var", "symb", "symb"]));
			break;
		default:
			fwrite(STDERR, "[22] neznámý nebo chybný operační kód ve zdrojovém kódu zapsaném v IPPcode20\n");
			exit(22);
	}
	//kontrola chyby pri vytvareni objektu
	if (end($instruction_array)->err_code != 0){
		fwrite(STDERR, "[".end($instruction_array)->err_code."] jiná lexikální nebo syntaktická chyba zdrojového kódu zapsaného v IPPcode20\n");
		exit(end($instruction_array)->err_code);
	}
	
}
if (count($instruction_array) == 0){
	exit(0);
}
$stats->loc = count($instruction_array);
$stats->label = count(array_unique($label_array));

///vypis XML dokumentu
$counter = 1;
$toXML = new DomDocument('1.0', "UTF-8");
$toXML->formatOutput = true;
$program = $toXML->createElement("program");
$program = $toXML->appendChild($program);

$language = $toXML->createAttribute("language");
$language->value = "IPPcode20";
$program->appendChild($language);

//vypis instukrci
foreach ($instruction_array as $instruction) {
	if ($instruction->err_code == 0){
		
		$instruction_to_print = $toXML->createElement("instruction");
		$program->appendChild($instruction_to_print);
		
		$instruction_order = $toXML->createAttribute("order");
		$instruction_order->value = $counter++;
		$instruction_to_print->appendChild($instruction_order);
		
		$instruction_opcode = $toXML->createAttribute("opcode");
		$instruction_opcode->value = $instruction->name;
		$instruction_to_print->appendChild($instruction_opcode);
		
		for ($i=1; $i < 4; $i++) {
			if (isset($instruction->arg_name{$i}) && isset($instruction->arg_type{$i})){		
				$arg = $toXML->createElement("arg$i");	
				$instruction_to_print->appendChild($arg);
				
				$arg_type = $toXML->createAttribute("type");
				$arg_type->value = $instruction->arg_type{$i};
				$arg->appendChild($arg_type);
				
				$arg_text = $toXML->createTextNode($instruction->arg_name{$i});
				$arg->appendChild($arg_text);	
			}
		}
	}
	else{
		fwrite(STDERR, "[23] jiná lexikální nebo syntaktická chyba zdrojového kódu zapsaného v IPPcode20\n");
		exit(23);
	}
}
$stats->write_down();
echo string_translate($toXML->saveXML(null,LIBXML_NOEMPTYTAG));
?>