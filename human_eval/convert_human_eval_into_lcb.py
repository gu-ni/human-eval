# %%
import re
import ast
import json


def convert_test(test_str: str) -> str:
    testcases = []

    # 1. 멀티라인 assert를 한 줄로 합침
    normalized_lines = []
    current_line = ''
    inside_assert = False

    for line in test_str.splitlines():
        line = line.strip()
        if line.startswith("assert"):
            if current_line:  # 이전 줄 있으면 저장
                normalized_lines.append(current_line)
            current_line = line
            inside_assert = True
        elif inside_assert and line:  # 줄 계속 이어짐
            current_line += ' ' + line
        else:
            if current_line:
                normalized_lines.append(current_line)
                current_line = ''
            inside_assert = False

    if current_line:  # 마지막 줄
        normalized_lines.append(current_line)

    # 2. 각 assert 줄에 대해 변환
    pattern_equal = re.compile(
        r'assert\s+candidate\s*\((.*?)\)\s*==\s*(.+?)(?:,\s*["\'].*["\'])?$',
        re.DOTALL
    )
    pattern_is = re.compile(
        r'assert\s+candidate\s*\((.*?)\)\s*is\s+(True|False)(?:,\s*["\'].*["\'])?$',
        re.DOTALL
    )
    pattern_pos = re.compile(
        r'assert\s+candidate\s*\((.*?)\)(?:,\s*["\'].*["\'])?$',
        re.DOTALL
    )
    pattern_neg = re.compile(
        r'assert\s+not\s+candidate\s*\((.*?)\)(?:,\s*["\'].*["\'])?$',
        re.DOTALL
    )

    for line in normalized_lines:
        try:
            # pattern 1: candidate(...) == ...
            match = pattern_equal.match(line)
            if match:
                input_args = match.group(1).strip()
                output_str = " ".join(match.group(2).splitlines())
                parsed_output = ast.literal_eval(output_str)

            # pattern 2: candidate(...) is True/False
            else:
                match = pattern_is.match(line)
                if match:
                    input_args = match.group(1).strip()
                    parsed_output = match.group(2) == "True"

                # pattern 3: candidate(...) → True
                else:
                    match = pattern_pos.match(line)
                    if match:
                        input_args = match.group(1).strip()
                        parsed_output = True

                    # pattern 4: not candidate(...) → False
                    else:
                        match = pattern_neg.match(line)
                        if match:
                            input_args = match.group(1).strip()
                            parsed_output = False
                        else:
                            continue  # 어떤 패턴에도 안 맞음

            # input serialization
            args_list = ast.literal_eval(f"[{input_args}]")

            if len(args_list) == 1:
                single_arg = args_list[0]
                input_serialized = single_arg if isinstance(single_arg, str) else json.dumps(single_arg)
            else:
                input_serialized = json.dumps(args_list)

            output_serialized = json.dumps(parsed_output)

            testcases.append({
                "input": input_serialized,
                "output": output_serialized,
                "testtype": "functional"
            })

        except Exception:
            continue  # 파싱 실패 시 건너뜀

    return json.dumps(testcases)


def convert_humaneval_to_livecodebench(task: dict) -> dict:
    
    def extract_starter_code(prompt: str, entry_point: str) -> str:
        # 정규식으로 해당 entry_point 함수 시그니처 추출
        match = re.search(
            rf"def\s+{re.escape(entry_point)}\s*\((.*?)\)(\s*->\s*[^\n:]+)?\s*:",
            prompt
        )

        if match:
            args = match.group(1).strip()
            return_type = match.group(2).strip() if match.group(2) else ""
            return f"class Solution:\n    def {entry_point}(self, {args}){return_type}:\n        "
        else:
            return ""
        
    task_id = task["task_id"]
    entry_point = task["entry_point"]
    prompt = task["prompt"]
    test_code = task["test"]

    # starter_code 추출: class Solution: + def ...:
    starter_code = extract_starter_code(prompt, entry_point)

    # public_test_cases 생성
    public_test_cases = convert_test(test_code)

    return {
        "question_title": entry_point,
        "question_content": prompt,
        "platform": "HumanEval",
        "question_id": task_id,
        "contest_id": task_id,
        "contest_date": "2021-01-01T00:00:00",
        "starter_code": starter_code,
        "difficulty": "easy",
        "public_test_cases": public_test_cases,
        "private_test_cases": "",
        "metadata": json.dumps({"func_name": entry_point})
    }


def convert_humaneval_jsonl_to_livecodebench(input_path: str, output_path: str):
    converted_lines = []

    with open(input_path, "r", encoding="utf-8") as infile:
        for line in infile:
            task = json.loads(line)
            converted = convert_humaneval_to_livecodebench(task)
            converted_lines.append(json.dumps(converted, ensure_ascii=False))

    with open(output_path, "w", encoding="utf-8") as outfile:
        for line in converted_lines:
            outfile.write(line + "\n")


# %%
convert_humaneval_jsonl_to_livecodebench(
    input_path="/home/work/users/PIL_ghj/LLM/datasets/human-eval/data/HumanEval.jsonl",
    output_path="/home/work/users/PIL_ghj/LLM/datasets/human-eval/data/HumanEval_in_lcb_format.jsonl"
)
# %%
