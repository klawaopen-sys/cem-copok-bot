import os
import json

def search_logs():
    brain_dir = "C:/Users/Admin/.gemini/antigravity-ide/brain"
    if not os.path.exists(brain_dir):
        print(f"Directory {brain_dir} not found.")
        return
        
    print(f"Searching all transcript.jsonl files under {brain_dir}...")
    for item in os.listdir(brain_dir):
        item_path = os.path.join(brain_dir, item)
        if os.path.isdir(item_path):
            transcript_path = os.path.join(item_path, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(transcript_path):
                try:
                    with open(transcript_path, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if "remote" in line.lower() or "github.com" in line.lower():
                                data = json.loads(line)
                                # Check tool calls or outputs
                                if "tool_calls" in data:
                                    for tc in data["tool_calls"]:
                                        if tc.get("name") == "run_command":
                                            cmd = tc.get("args", {}).get("CommandLine", "")
                                            print(f"Found command in {item}: {cmd}")
                                if "content" in data:
                                    content = data["content"]
                                    if "github.com" in content.lower():
                                        print(f"Found content in {item} (line {line_num})")
                except Exception as e:
                    pass

if __name__ == "__main__":
    search_logs()
