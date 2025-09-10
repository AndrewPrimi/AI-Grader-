# evaluator.py
import re
import json

def evaluate_submission(student_code: str, ground_truth_code: str = "") -> str:
    grade = 0
    confidence = 0.0
    feedback = ""
    
    if "def " not in student_code:
        feedback = "No function definition found."
        grade = 0
        confidence = 0.3
    else:
        body_lines = [line.strip() for line in student_code.split("\n")[1:] if line.strip()]
        if not body_lines or all("pass" in line for line in body_lines):
            feedback = "Function signature is present but no implementation logic found."
            grade = 2
            confidence = 0.4
        else:
            try:
                local_scope = {}
                exec(student_code, {}, local_scope)
                func_name = re.findall(r'def (\w+)\(', student_code)[0]
                func = local_scope[func_name]
                
                test_cases = [
                    ("A man a plan a canal Panama", True),
                    ("Racecar", True),
                    ("Hello World", False),
                    ("", True),
                    (" ", True)
                ]
                
                passed = 0
                for inp, expected in test_cases:
                    if func(inp) == expected:
                        passed += 1
                
                total = len(test_cases)
                grade = int((passed / total) * 100)
                confidence = round(passed / total, 2)
                feedback = f"Passed {passed}/{total} test cases."
                
                if grade == 100:
                    feedback += " Excellent work."
                elif grade >= 60:
                    feedback += " Good job, minor issues."
                else:
                    feedback += " Needs improvement."
                    
            except Exception as e:
                feedback = f"Error during execution: {e}"
                grade = 1
                confidence = 0.2
    
    result = {
        "grade": grade,
        "confidence": confidence,
        "feedback": feedback
    }
    
    return json.dumps(result, indent=2)