import requests

BASE_URL = "https://goai247.com/en/chat"  # or your staging/internal endpoint
# adjust depending on how the bot API works (HTTP, websocket, etc.)

def send_message(session, message):
    # This is illustrative — adjust based on actual request shape
    resp = session.post(BASE_URL, json={"message": message})
    print(resp.json())
    resp.raise_for_status()
    return resp.json()

def test_greeting():
    session = requests.Session()
    out = send_message(session, "Hello!")
    assert "Hi" in out.get("reply", ""), f"Unexpected reply: {out}"

def test_unknown_input():
    session = requests.Session()
    out = send_message(session, "!@#$%^&* random gibberish ???")
    # Expect a fallback or safe response
    assert "sorry" in out.get("reply", "").lower() or "can you" in out.get("reply", "").lower()

# Add more test cases below: edge-cases, multi-turn, context, long conversation, etc.
#add main function to run the tests
if __name__ == "__main__":
    test_greeting()
    test_unknown_input()