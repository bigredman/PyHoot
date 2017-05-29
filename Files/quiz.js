var PLAYERS_IN_LINE = 3;
var state = "Registration";
var timer = window.setInterval(getnames, 1000);
var number_of_questions = null;

// FIXME: Change the order they work to the same way as game
function switch_screens() {
	switch (state) {
		case "Opening":
			start = "Registration";
			color = "#0D407F"; //Macragge Blue
			break;
		case "Answer":
			start = "Question";
			color = "#EE3823"; //Jokaero Orange
			break;
		case "Question":
			//If something was loaded to ans it means that I already did one question
			if (document.getElementById("ans").innerHTML) {
				start = "Leaderboard";
			} else {
				start = "Opening";
			}
			color = "#FFFFFF" //White
			break;
		case "Leaderboard":
			start = "Answer";
			color = "Orange"; //Jokaero Orange
			break;
		case "Finish":
			start = "Leaderboard";
			color = "#96A5A9"; //Celestra Grey
			break;
	}
	var state_style_display = document.getElementById(state).style.display;
	var start_style_display = document.getElementById(start).style.display;
	state_style_display = [start_style_display, start_style_display = state_style_display][0];
	document.getElementById(state).style.display = state_style_display;
	document.getElementById(start).style.display = start_style_display;
	document.body.style.background = color
}

function get_join_number() {
	xmlrequest(
		"get_join_number",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				xmlDoc = parse_xml_from_string(this.responseText);
				document.getElementById("join_number").innerHTML = xmlDoc.getElementsByTagName("join_number")[0].textContent;
			}
		}
	);
}

function getnames() {
	xmlrequest("getnames", function() {
		if (this.readyState == 4 && this.status == 200) {
			xmlDoc = parse_xml_from_string(this.responseText);
			players = xmlDoc.getElementsByTagName("player");
			string_players = "";
			for (i = 0; i < players.length; i++) {
				string_players += players[i].getAttribute("name");
				if (i % PLAYERS_IN_LINE === 0 && i !== 0) {
					string_players += "<br/>";
				} else if ((i + 1) < players.length) {
					string_players += "&emsp;";
				}
			}
			document.getElementById("names").innerHTML = string_players;
		}
	});
}

//continue only if at least one user is online
function check_moveable() {
	if (document.getElementById("names").innerHTML.length > 0) {
		change_Registeration_Opening();
	}
}

function change_Registeration_Opening() {
	state = "Opening";
	set_timer("5");
	clearInterval(timer);
	timer = window.setInterval(check_timer_change, 1000);
	getinfo();
	switch_screens();
}

function check_move_question() {
	xmlrequest("check_move_question",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				if (xmlstring_to_boolean(this.responseText)) {
					//HACK: check if you can change it to to check_move_next_page insteed
					clearInterval(timer);
					change_Question_Answer();
				}
			}
		}
	);
}

function change_Question_Answer() {
	xmlrequest("get_answers",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				// FIXME: If you didn't answer you will stay in place
				xmlrequest("order_move_all_not_answered", null);
				xmlDoc = parse_xml_from_string(this.responseText);
				answer_html = document.getElementById("ans");
				answer_html.innerHTML = "";
				list_answers = xmlDoc.getElementsByTagName("answer");
				for (var i = 0; i < list_answers.length; i++) {
					answer_html.innerHTML += document.getElementById(list_answers[i].getAttribute("answer") + "_answer").innerHTML + "<br />";
				}
				state = "Answer";
				switch_screens();
				clearInterval(timer);
				set_timer("5");
				timer = window.setInterval(check_timer_change, 1000);
			}
		}
	);
}

function change_Opening_Question() {
	order_move_all_players();
	xmlrequest("start_question", null);
	state = "Question";
	switch_screens();
}

function change_Answer_Leaderboard() {
	xmlrequest("get_xml_leaderboard",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				parser = new DOMParser();
				xmlDoc = parser.parseFromString(this.responseText, "text/xml");
				leaderboard = document.getElementById("Leaderboard");
				//TODO: Move as much as I can into the HTML page
				var list_players = xmlDoc.getElementsByTagName("Player");
				var lb = "<table>";
				for (i = 0; i < list_players.length; i++) {
					player = list_players[i];
					lb += "<tr>" +
						"   <td>" +
						player.getAttribute("name") +
						"   </td>" +
						"   <td>" +
						player.getAttribute("score") +
						"   </td>" +
						"</tr>";
				}
				lb += "</table>";
				document.getElementById("Leaderboard_content").innerHTML = lb;
				order_move_all_players();
				state = "Leaderboard";
				switch_screens();
				set_timer("5");
				timer = window.setInterval(check_timer_change, 1000);
			}
		}
	);
}

function getinfo() {
	xmlrequest("get_information",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				parser = new DOMParser();
				xmlDoc = parser.parseFromString(this.responseText,
					"text/xml");
				quiz = xmlDoc.getElementsByTagName("Quiz")[0];
				document.getElementById("quiz_name").innerHTML =
					quiz.getAttribute("name");
				document.getElementById("number_questions").innerHTML =
					quiz.getAttribute("number_of_questions") + " questions";
			}
		}
	);
}

function get_winner() {
	var oTable = document.getElementById("Leaderboard_content").getElementsByTagName("table")[0];

	var oCells = oTable.rows.item(0).cells;

	document.getElementById("Finish_name").innerHTML = oCells.item(0).innerHTML;
	document.getElementById("Finish_score").innerHTML = oCells.item(1).innerHTML;
}

function order_move_all_players() {
	xmlrequest("order_move_all_players", null);
}

function set_timer(new_time) {
	xmlrequest("set_timer_change?new_time=" + new_time, null);
}

function check_timer_change() {
	xmlrequest("check_timer_change",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				if (xmlstring_to_boolean(this.responseText)) {
					clearInterval(timer);
					if (state == "Opening") {
						move_to_next_question();
					}
					if (state == "Answer") {
						change_Answer_Leaderboard();
					}
					if (state == "Leaderboard") {
						if (number_of_questions > -1) {
							move_to_next_question();
						} else {
							xmlrequest("set_ended?new=True", null);
							order_move_all_players();
							state = "Finish";
							// WIP
						}
					}
				}
			}
		}
	);
}

function move_to_next_question() {
	xmlrequest("move_to_next_question",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				// Take the xml we got, parse it and compare the
				// argument "number_of_questions" bigger than 0
				if (parse_xml_from_string(this.responseText).getElementsByTagName(
						"question")[0].getAttribute(
						"number_of_questions") >= 0) {
					get_question();
				} else {
					state = "Finish";
					get_winner();
					switch_screens();
					clearInterval(timer);
				}
			}
		}
	);
}


function get_question() {
	xmlrequest("get_question",
		function() {
			if (this.readyState == 4 && this.status == 200) {
				xmlDoc = parse_xml_from_string(this.responseText);
				question = xmlDoc.getElementsByTagName("Question")[0];
				set_timer(question.getAttribute("duration"));
				timer = window.setInterval(check_move_question, 1000);
				document.getElementById("question_title").innerHTML =
					question.childNodes[1].textContent;
				var questionsID = ["A_answer", "B_answer", "C_answer", "D_answer"];
				for (i = 0; i < 4; i++) {
					document.getElementById(questionsID[i]).innerHTML =
						xmlDoc.getElementsByTagName("Answer")[i].textContent;
				}
				state = "Question";
				change_Opening_Question();
			}
		}
	);
}