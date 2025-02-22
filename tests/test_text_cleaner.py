import json
from src.utils.text_cleaner import clean_text_for_json, clean_documents

def test_clean_text_for_json():
    # Test cases from our problematic documents
    test_cases = {
        'windows_path': (
            r"ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied: 'C:\\Users\\Asia\\anaconda3'",
            r"ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied: 'C:/Users/Asia/anaconda3'"
        ),
        'command_syntax': (
            r"When using the command \d <database name>",
            r"When using the command \\d <database name>"
        ),
        'trailing_backslash': (
            r"/var/lib/postgresql/data\\",
            r"/var/lib/postgresql/data/"
        ),
        'mixed_line_endings': (
            "line1\r\nline2\rline3\nline4",
            "line1\nline2\nline3\nline4"
        )
    }
    
    for case_name, (input_text, expected) in test_cases.items():
        result = clean_text_for_json(input_text)
        assert result == expected, f"Failed {case_name}: expected {expected}, got {result}"
        
        # Verify the cleaned text can be JSON serialized
        try:
            json.dumps({"text": result})
        except json.JSONDecodeError as e:
            assert False, f"Failed to JSON serialize {case_name}: {e}"

def test_clean_documents():
    # Test with our actual problematic documents
    test_docs = {
        '691a6329': 'Change the mounting path. Replace it with one of following:\n-v /e/zoomcamp/...:/var/lib/postgresql/data\n-v /c:/.../ny_taxi_postgres_data:/var/lib/postgresql/data\\ (leading slash in front of c:)',
        '3d99504a': 'When using the command \\d <database name> you get the error column `c.relhasoids does not exist`.\nResolution:\nUninstall pgcli\nReinstall pgclidatabase "ny_taxi" does not exist\nRestart pc',
        '7779cff5': "When I run pip install grpcio==1.42.0 tensorflow-serving-api==2.7.0 to install the libraries in windows machine,  I was getting the below error :\nERROR: Could not install packages due to an OSError: [WinError 5] Access is denied: 'C:\\\\Users\\\\Asia\\\\anaconda3\\\\Lib\\\\site-packages\\\\google\\\\protobuf\\\\internal\\\\_api_implementation.cp39-win_amd64.pyd'\nConsider using the `--user` option or check the permissions.\nSolution description :\nI was able to install the libraries using below command:\npip --user install grpcio==1.42.0 tensorflow-serving-api==2.7.0\nAsia Saeed",
        '9c89ef22': 'Got the same warning message as Warrie Warrie when using "mlflow.xgboost.autolog()"\nIt turned out that this was just a warning message and upon checking MLflow UI (making sure that no "tag" filters were included), the model was actually automatically tracked in the MLflow.\nAdded by Bengsoon Chuah, Asked by Warrie Warrie, Answered by Anna Vasylytsya & Ivan Starovit'
    }
    
    cleaned_docs = clean_documents(test_docs)
    
    # Verify all documents can be JSON serialized
    try:
        json.dumps(cleaned_docs)
    except json.JSONDecodeError as e:
        assert False, f"Failed to JSON serialize cleaned documents: {e}"
        
    # Verify specific cleanings
    assert '\\\\' not in cleaned_docs['7779cff5'], "Windows paths not properly cleaned"
    assert cleaned_docs['3d99504a'].count('\\d') == 1, "Command syntax not properly escaped"
    assert cleaned_docs['691a6329'].endswith('c:)'), "Trailing backslash not properly handled" 