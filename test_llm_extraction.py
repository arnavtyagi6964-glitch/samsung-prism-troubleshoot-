import json
from pathlib import Path

from app.services import extract_context_response
from app.schemas import print_validation_errors, validate_context_response


def load_test_data():
    data_dir = Path(__file__).parent / "data"
    
    with open(data_dir / "input.txt", "r") as f:
        complaints = [line.strip() for line in f if line.strip()]
    
    with open(data_dir / "siis_responses.json", "r") as f:
        siis_data = json.load(f)
    
    responses_map = {}
    for item in siis_data.get("responses", []):
        query = item["original_query"]
        if query.startswith("1. "):
            query = query[3:]
        responses_map[query] = item["siis_response"]
    
    return complaints, responses_map


def test_first_complaint():
    complaints, responses_map = load_test_data()
    
    complaint = complaints[0]
    response_obj = responses_map.get(complaint)
    
    if not response_obj:
        print(f"No SIIS response found for: {complaint[:50]}...")
        return
    
    siis_text = f"{response_obj['title']}: {response_obj['content']}"
    
    print(f"Complaint: {complaint[:80]}...")
    print(f"SIIS Title: {response_obj['title']}")
    print("\n--- Running LLM extraction ---\n")
    
    try:
        result = extract_context_response(complaint, siis_text)
        
        print("=== EXTRACTED GOAL ===")
        goal = result.contexts[0]
        print(f"Goal: {goal.goal}")
        print(f"Title: {goal.title}")
        print(f"Score: {goal.score}")
        print(f"Actions: {len(goal.actions)}")
        
        for i, action in enumerate(goal.actions):
            print(f"\n  Action {i+1}: {action.actionName} ({action.category})")
            print(f"  Description: {action.description}")
            for j, sg in enumerate(action.stepGroups):
                print(f"  StepGroup {j+1}: {len(sg.steps)} steps")
                for step in sg.steps:
                    print(f"    - {step}")
                if sg.actionableDeeplink:
                    print(f"    Actionable: {sg.actionableDeeplink.deeplink}")
                if sg.validationDeeplink:
                    print(f"    Validation: {sg.validationDeeplink.deeplink} (key: {sg.validationDeeplink.key})")
        
        print("\n=== VALIDATION ===")
        errors = validate_context_response(result)
        print_validation_errors(errors)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    test_first_complaint()