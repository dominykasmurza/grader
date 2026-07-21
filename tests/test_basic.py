from grader.grader import normalize_answer, normalize_part, parse_score_map_arg, question_code_for

def test_normalize_answer():
    assert normalize_answer("true") == "T"
    assert normalize_answer("0") == "F"

def test_normalize_part():
    assert normalize_part("Theory Part A") == "A"
    assert normalize_part("part b") == "B"

def test_score_map():
    assert parse_score_map_arg("0:0,1:0.25,2:0.5,3:0.75,4:1")[3] == 0.75

def test_question_code():
    assert question_code_for("A", 1) == "A01"
