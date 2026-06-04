import os
import ast

def check_syntax(directory):
    errors = []
    for root, dirs, files in os.walk(directory):
        # Skip venv or pycache
        if 'venv' in root or '.venv' in root or '__pycache__' in root or '.git' in root or '.tmp' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    ast.parse(source, filename=file_path)
                except SyntaxError as e:
                    errors.append({
                        'file': file_path,
                        'line': e.lineno,
                        'offset': e.offset,
                        'text': e.text,
                        'message': str(e)
                    })
                except Exception as e:
                    errors.append({
                        'file': file_path,
                        'message': f"General Error: {e}"
                    })
    return errors

def main():
    root_dir = "F:/Antigravity"
    print(f"Checking syntax in all python files under {root_dir}...")
    errors = check_syntax(root_dir)
    if not errors:
        print("✅ No syntax errors found in python files!")
    else:
        print(f"❌ Found {len(errors)} errors:")
        for err in errors:
            print("-" * 50)
            print(f"File: {err['file']}")
            if 'line' in err:
                print(f"Line: {err['line']}, Offset: {err['offset']}")
                print(f"Code: {err['text'].strip() if err['text'] else ''}")
            print(f"Error: {err['message']}")
            print("-" * 50)

if __name__ == "__main__":
    main()
