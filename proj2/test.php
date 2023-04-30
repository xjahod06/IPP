<?php

/**
jmeno: Vojtech Jahoda
login: xjahod06
date: 15.04.2020
version: php7.4
 */
class test
{
	function __construct($state,$part,$name,$dir,$rc=0,$expect_rc=0,$out_error_file=Null){
		$this->state = $state;
		$this->part = $part;
		$this->name = $name;
		$this->dir = $dir;
		$this->rc = $rc;
		$this->expect_rc = $expect_rc;
		$this->out_error_file = $out_error_file;
	}
}

function Error($code, $text) {
    fprintf(STDERR, "error: %d\v%s\n",$code,$text);
    exit($code);
}

$params = getopt("hd:rp:i:j:", array("help", "directory:", "recursive", "parse-script:", "int-script:","parse-only","int-only","jexamxml:"));

if ($argc == 2) {
	if ($argv[1] == "-h" || $argv[1] == "--help"){
		echo "help:\n";
		echo "-h, --help                            Tento výpis.\n";
		echo "-d <CESTA>, --directory <CESTA>       Nastavi slozku pro testy, defaultne tato.\n";
		echo "-r, --recursive                       Prohledá i všechny podadresare.\n";
		echo "-p <CESTA>, --parse-script <CESTA>    Nastavi cestu k parse.php, defaultne ./parse.php.\n";
		echo "-i <CESTA>, --int-script <CESTA>      Nastavi cestu k interpret.py, defaultne ./interpret.py.\n";
		echo "--parse-only                          Pouze test parseru.\n";
		echo "--int-only                            Pouze test interpretu.\n"; 
		echo "--jexamxml <CESTA>                    umístění .jar balíčku pro nástroj A7Soft JExamXML.\n"; 
		exit;
	}
} elseif (array_key_exists("help", $params) || array_key_exists("h", $params)){
	exit(10);
}

$dir = "./";
$recursive = False;
$parse = "./parse.php";
$interpret = "./interpret.py";
$only = "both";
$jexamxml_jar = "/pub/courses/ipp/jexamxml/jexamxml.jar";

if (array_key_exists("d", $params)) $dir = $params["d"];
elseif (array_key_exists("directory", $params)) $dir = $params["directory"];

if (array_key_exists("r", $params) || array_key_exists("recursive", $params))$recursive = True;

if (array_key_exists("parse-only", $params)) $only = "parse-only";
if (array_key_exists("int-only", $params)){
	if ($only == "both"){
		$only = "int-only";
	}
	else{
		exit(10);
	}
}

if (array_key_exists("p", $params)) $parse = $params["p"];
elseif (array_key_exists("parse-script", $params)) $parse = $params["parse-script"];

if (array_key_exists("j", $params)) $jexamxml_jar = $params["j"];
elseif (array_key_exists("jexamxml", $params)) $jexamxml_jar = $params["jexamxml"];

if (array_key_exists("i", $params)) $interpret = $params["i"];
elseif (array_key_exists("int-script", $params)) $interpret = $params["int-script"];

/*
echo "dir: ".$dir."\n";
echo "recursive: ".$recursive."\n";
echo "parse: ".$parse."\n";
echo "interpret: ".$interpret."\n";
echo "only: ".$only."\n";
*/

if ($recursive) exec("find ".$dir." -regex '.*\.src$'", $paths);
else exec("find ".$dir." -maxdepth 1 -regex '.*\.src$'", $paths);
//echo "find ".$dir." -maxdepth 1 -regex '.*\.src$'\n";

if (isset($paths) == False){
	Error(11,"no path");
}

$error = $total = 0;

preg_match('/(.*?)([^\/]*(?=\.jar))/m', $jexamxml_jar, $jexamxml_path);

$tests = $tests = $path_array = $files_content = array(); 

foreach ($paths as $src) {
	$total++;

	preg_match('/(.*?)([^\/]*(?=\.src))/m', $src, $path_name);
	$path = $path_name[1];
	$name = $path_name[2];

	array_push($path_array, $path);
	if (!(file_exists($path_name[0].".in"))){
		$f = fopen($path_name[0].".in", 'w') or Error(10,"fail when opening file");
	}
	if (!(file_exists($path_name[0].".out"))){
		$f = fopen($path_name[0].".out", 'w') or Error(10,"fail when opening file");
	}
	if (!(file_exists($path_name[0].".rc"))){
		$f = fopen($path_name[0].".rc", 'w') or Error(10,"fail when opening file");
		fwrite($f, "0");
		fclose($f);
	}
	// 	exec("mkdir diff_".$only." 2>/dev/null");
	if ($only == "parse-only"){
		$parse_return = exec("php7.4 ".$parse." < ".$path_name[0].".src >".$name.".your_out 2>/dev/null; echo $?");

		$test_return = exec("cat ".$path_name[0].".rc");
		if ($test_return != 0){
			if ($parse_return != $test_return){
				//array_push($tests, "error in ".$parse." RC returned[".$parse_return."] expected[".$test_return."] in test: ".$path_name[0]);
				array_push($tests, new test("Error","Parse",$name,$path,$parse_return,$test_return));
				$error++;
			}else{
				//array_push($tests, "OK test: ".$path_name[0]);
				array_push($tests, new test("Correct","Parse",$name,$path));
				
			}
		}else{
			$return_value =  exec("java -jar ".$jexamxml_jar." ".$path_name[0].".out ".$name.".your_out ".$name."_diffs.xml  /D ".$jexamxml_path[1]."options;echo $?");
			//echo "return value: ".$return_value."\n";
			if ($return_value != 0){
				//array_push($tests, "error on STDOUT in test: ".$path_name[0]." diff in ".$name."_diffs.xml");
				array_push($tests, new test("Error","JExamXML",$name,$path,0,0,$name."_diffs.xml"));
				$files_content[$name."_diffs.txt"] = file_get_contents($name."_diffs.xml");
				$error++;
			}else{
				//array_push($tests, "OK test: ".$path_name[0]);
				array_push($tests, new test("Correct","Parse",$name,$path));
				exec("rm ".$name."_diffs.xml 2>/dev/null");
			}
		}
		//exec("rm ".$name.".your_out 2>/dev/null");
	}
	else if ($only == "int-only"){
		$int_return = exec("python3.8 ".$interpret." --source ".$path_name[0].".src --input ".$path_name[0].".in >".$name.".your_out 2>/dev/null; echo $?");
		$test_return = exec("cat ".$path_name[0].".rc");
		if ($test_return != 0){
			if ($int_return != $test_return){
				//echo "error in ".$interpret." RC returned[".$int_return."] expected[".$test_return."] in test: ".$path_name[0]."\n";
				//array_push($tests, "error in ".$interpret." RC returned[".$int_return."] expected[".$test_return."] in test: ".$path_name[0]);
				array_push($tests, new test("Error","Interpret",$name,$path,$int_return,$test_return));
				$error++;
			}else{
				//echo "OK test: ".$path_name[0]."\n";
				array_push($tests, new test("Correct","Interpret",$name,$path));
				//array_push($tests, "OK test: ".$path_name[0]);
				
			}
		}else{
			$return_value =  exec("diff ".$path_name[0].".out ".$name.".your_out >".$name."_diffs.txt ;echo $?");
			if ($return_value != 0){
				//echo "error on STDOUT in test: ".$path_name[0]." diff in ".$name."_diffs.txt\n";
				//array_push($tests, "error on STDOUT in test: ".$path_name[0]." diff in ".$name."_diffs.txt");
				array_push($tests, new test("Error","diff",$name,$path,0,0,$name."_diffs.txt"));
				$files_content[$name."_diffs.txt"] = file_get_contents($name."_diffs.txt");
				$error++;
			}else{
				//echo "OK test: ".$path_name[0]."\n";
				//array_push($tests, "OK test: ".$path_name[0]);
				array_push($tests, new test("Correct","Interpret",$name,$path));
				exec("rm ".$name."_diffs.txt ");
			}
		}
		exec("rm ".$name.".your_out");
		
	}
	else if ($only == "both"){
		$parse_return = exec("php7.4 ".$parse." < ".$path_name[0].".src >".$name.".xml 2>/dev/null; echo $?");
		$test_return = exec("cat ".$path_name[0].".rc");
		if ($parse_return != 0){
			if ($parse_return != $test_return){
				//echo "error in ".$parse." RC returned[".$parse_return."] expected[".$test_return."] in test: ".$path_name[0]."\n";
				//array_push($tests, "error in ".$parse." RC returned[".$parse_return."] expected[".$test_return."] in test: ".$path_name[0]);
				array_push($tests, new test("Error","Parse",$name,$path,$parse_return,$test_return));
				$error++;
			}else{
				//echo "OK test: ".$path_name[0]."\n";
				//array_push($tests, "OK test: ".$path_name[0]);
				array_push($tests, new test("Correct","Parse",$name,$path));
			}
		}
		else{
			$int_return = exec("python3.8 ".$interpret." --source ".$name.".xml --input ".$path_name[0].".in >".$name.".your_out 2>/dev/null; echo $?");
			if ($test_return != 0){
				if ($int_return != $test_return){
					//echo "error in ".$interpret." RC returned[".$int_return."] expected[".$test_return."] in test: ".$path_name[0]."\n";
					//array_push($tests, "error in ".$interpret." RC returned[".$int_return."] expected[".$test_return."] in test: ".$path_name[0]);
					array_push($tests, new test("Error","Interpret",$name,$path,$int_return,$test_return));
					$error++;
				}else{
					//echo "OK test: ".$path_name[0]."\n";
					//array_push($tests, "OK test: ".$path_name[0]);
					array_push($tests, new test("Correct","Interpret",$name,$path));
				}
			}else{
				$return_value =  exec("diff ".$path_name[0].".out ".$name.".your_out >".$name."_diffs.txt ;echo $?");
				if ($return_value != 0){
					//echo "error on STDOUT in test: ".$path_name[0]." diff in ".$name."_diffs.txt\n";
					//array_push($tests, "error on STDOUT in test: ".$path_name[0]." diff in ".$name."_diffs.txt");
					array_push($tests, new test("Error","diff",$name,$path,0,0,$name."_diffs.txt"));
					$files_content[$name."_diffs.txt"] = file_get_contents($name."_diffs.txt");
					$error++;
				}else{
					//echo "OK test: ".$path_name[0]."\n";
					//array_push($tests, "OK test: ".$path_name[0]);
					array_push($tests, new test("Correct","Both",$name,$path));
					exec("rm ".$name."_diffs.txt ");
				}
			}
		}
		exec("rm ".$name.".your_out 2>/dev/null");
		exec("rm ".$name.".xml 2>/dev/null");
		
	}
}
if ($total <= 0){
	Error(0,"no test files found");
}
$unique_paths = array_unique($path_array);
$diff_files = array();

?>
<!DOCTYPE html>
<html lang='cs'>
<head>
<title>test results</title>
<meta name="viewport" content="width=device-width, initial-scale=0.85">
<meta charset='utf-8'>
<style type="text/css">
	.error{
		background-color: #ffbac1;
	}
	.correct{
		background-color: #b5ffbf;
	}
	.major_table td{
		min-width: 200px;
		
		border-collapse: collapse;
		text-align: center;
	}
	.correct_back{
		background-color: #00c91b;
	}
	.error_back{
		background-color: #eb4034;
	}
	.full_tab{
		margin: auto;
		text-align: center;
		border-collapse: collapse;
	}
	.full_tab td{
		padding: 5px;
		min-width: 100px
	}
	.full_tab tr{
		border: 1px solid black;
	}
	.full_tab a {
		text-decoration: none;
		color: black;
	}
	.center{
		margin: auto;
		text-align: center;
	}
	.Correct{
		background-color: #b5ffbf;
	}
	.Error{
		background-color: #ffbac1;
	}
	.left-a{
		text-align: left;
	}
	.toggle-button{
		border: 1px solid black;
		border-radius: 5px;
		padding: 5px;
		background-color: #b5ffbf;
	}
	.sidenav {
	  width: 250px;
	  max-height: 95%;
	  position: fixed;/
	  z-index: 1;
	  top: 0;
	  left: 0;
	  background-color: white;
	  overflow-x: hidden;
	  overflow-y: auto;
	  padding-top: 20px;
	  padding-bottom: 20px;
	  transition: 0.5s;
	  border: 1px solid black;
	}

	.sidenav a {
	  padding: 8px 8px 8px 32px;
	  text-decoration: none;
	  font-size: 17px;
	  display: block;
	  transition: 0.1s;
	  color: black;
	}

	.sidenav a:hover {
	  background-color: #e1e1e1;
	}

	.sidenav b {
	  padding: 8px 8px 8px 10px;
	  font-size: 20px;
	  display: block;
	  transition: 0.1s;
	  color: black;
	}

	.sidenav .closebtn {
	  position: absolute;
	  top: 0;
	  right: 25px;
	  font-size: 36px;
	  margin-left: 50px;
	}
	.show_file{
		width: 680px;
		margin: auto;
		padding-bottom: 60px;
	}
	.show_file pre{
		padding: 5px;
		border: 1px solid black;
	}
	.Diff a {
		text-decoration: none;
		color: black;
	}
	.file{
		display: none;
	}
	.menu{
		font-size: 17px;
	}
</style>
</head>
<script type="text/javascript">
Array.prototype.remove = function() {
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
};
function init_button(){
	var def_button = document.getElementsByClassName("toggle-button");
	for(var i=0; i<def_button.length; ++i){
		def_button[i].style.background = 'rgb(181, 255, 191)';
	};
}

var filtr_array = new Array()


function repair_diff(){
	var row_repair = document.getElementsByClassName('Diff');
	for(var i=0; i<row_repair.length; ++i){
		var s = row_repair[i].style;
		s.display = 'table-cell';
	};
}

function toggle_class(class_name,display){
	var els = document.getElementsByClassName(class_name);
	for(var i=0; i<els.length; ++i){
		var s = els[i].style;
		s.display = display;
	};
}

function toggle(class_to_toggle, id) {
	console.log(filtr_array)
	var button = document.getElementById(id);
	//console.log(button.style.background);
	if (button.style.background == 'rgb(181, 255, 191)'){
		filtr_array.push(class_to_toggle);
	}else{
		filtr_array.remove(class_to_toggle);
	}
	console.log(filtr_array);
	button.style.background  = button.style.background === 'rgb(255, 186, 193)' ? 'rgb(181, 255, 191)' : 'rgb(255, 186, 193)';
	toggle_class('test','table-row');
	for(var i = 0; i <filtr_array.length; ++i){
		toggle_class(filtr_array[i],'none');
	};
	repair_diff();
}
function show_file(file) {
	var files = document.getElementsByClassName("file");
	for(var i=0; i<files.length; ++i){
		var s = files[i].style;
		s.display = 'none';
	};
	var file = document.getElementById(file);
	//console.log(file.style.display);
	file.style.display = file.style.display === 'none' ? 'block' : 'none';
}
window.onload = init_button;
</script>
<body>

<div class="sidenav">
	<b>folders:</b>
	<a href="#">Home</a>
  <?php
  foreach ($unique_paths as $path) {
  	echo '<a href="#'.$path.'">'.$path.'</a>';
  }
  ?>
</div>

<h1 class="center">mode: <?echo $only;?></h1>
<br>
<div>
	<table class="major_table" align="center" cellspacing="0" border="1">
		<tr>
			<td>Total</td>
			<td class="error">Errors</td>
			<td class="correct">Correct</td>
		</tr>
		<tr>
			<td rowspan="2"><?php echo $total; ?></td>
			<td class="error"><?php echo $error; ?></td>
			<td class="correct"><?php echo ($total-$error); ?></td>
		</tr>
		<tr>
			<td class="error"><?php echo "[".round((($error/$total)*100),0,$mode=PHP_ROUND_HALF_UP)."%]"; ?></td>
			<td class="correct"><?php echo "[".round(((($total-$error)/$total)*100),0,$mode=PHP_ROUND_HALF_DOWN)."%]"; ?></td>
		</tr>
	</table>
</div>
<br>
<h2 class="center">total extract of tests:</h2>
<br>
<table class="full_tab" cellspacing="0">
<tr style="border: 0;">
	<td colspan="2"></td>
	<td colspan="2"><button onclick="toggle('Correct','correct_toggle')" class="toggle-button" id="correct_toggle">toggle correct tests</button></td>
	<td colspan="2"><button onclick="toggle('Error','error_toggle')" class="toggle-button" id="error_toggle">toggle error tests</button></td>
</tr>	
<tr style="border: 0;">
	<td colspan="2"><button onclick="toggle('Parse','parse_toggle')" class="toggle-button" id="parse_toggle">toggle parse tests</button></td>
	<td colspan="2"><button onclick="toggle('Interpret','int_toggle')" class="toggle-button" id="int_toggle">toggle interpret tests</button></td>
	<td colspan="2"><button onclick="toggle('diff','diff_toggle')" class="toggle-button" id="diff_toggle">toggle diff tests</button></td>
</tr>	
<tr style="border-bottom: 0">
	<td rowspan="2" class="menu">dir</td>
	<td rowspan="2" class="menu">name</td>
	<td rowspan="2" class="menu">test part</td>
	<td rowspan="2" class="menu">state</td>
	<td class="menu" style="padding-bottom: 2px;">returned code</td>
	<td class="menu" style="padding-bottom: 2px;">expected RC</td>
</tr>
<tr class="menu" style="border-top: 0">
	<td colspan="2" style="padding-top: 0">diff file</td>
</tr>

<?php
$lastdir = Null;
foreach ($tests as $test) {
	if ($test->dir != $lastdir){
		echo '<tr class="left-a" id="'.$test->dir.'">';
		echo '<td colspan="6">'.$test->dir.'</td>';
		echo '</tr>';
		$lastdir = $test->dir;
	}

	echo '<tr class="'.$test->state.' '.$test->part.' test">';
	echo '<td></td>';	
	echo '<td class="left-a">'.$test->name.'</td>';
	echo '<td>'.$test->part.'</td>';
	if ($test->state == 'Error'){
		echo '<td class="error_back">'.$test->state.'</td>';
	}else{
		echo '<td class="correct_back">'.$test->state.'</td>';
	}
	if ($test->expect_rc != 0){
		echo '<td title="returned code">'.$test->rc.'</td>';
		echo '<td title="expected RC">'.$test->expect_rc.'</td>';
	}
	elseif ($test->out_error_file != Null) {
			echo '<td colspan="2" title="diff file" class="Diff" id="row-repair"><a href="#'.$test->out_error_file.'" onclick="show_file(\''.$test->out_error_file.'\')">'.$test->out_error_file.'</a></td>';
			array_push($diff_files,$test->out_error_file);
	}
	else{
		echo '<td></td><td></td>';
	}
	echo '</tr>';
}
?>
</table>
<br>
<div class="show_file">
<?php
foreach ($diff_files as $file) {
	$f = $files_content[$file];
	echo '<pre id="'.$file.'" class="file">';
	echo $f;
	echo "</pre>";
	exec("rm ".$file." 2>/dev/null");
}
?>
</div>
</body>
</html>
<?php

/*
foreach ($tests as $err) {
	echo $err->state." ".$err->part." ". $err->name." my: ". $err->rc." expect: ". $err->expect_rc."\n";
}
echo "total  : ".$total."\n";
echo "errors : ".$error." [".round((($error/$total)*100),0,$mode=PHP_ROUND_HALF_UP)."%]\n";
echo "correct: ".($total-$error)." [".round(((($total-$error)/$total)*100),0,$mode=PHP_ROUND_HALF_DOWN)."%]\n";
*/
?>