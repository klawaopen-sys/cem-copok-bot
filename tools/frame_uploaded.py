import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
from tools.news_poster import apply_brand_frame

def main():
    src = r"C:\Users\Admin\.gemini\antigravity-ide\brain\5e6acf71-6ea6-421e-b2ce-2f08cc02268e\media__1782579831448.jpg"
    dest = r"F:\Antigravity\Cem_copok\.tmp\trader_dictionary.jpg"
    
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy(src, dest)
    print(f"✅ Copied image to {dest}")
    
    # Накладаємо рамку
    success = apply_brand_frame(dest, 'trading')
    if success:
        print("✅ Brand frame applied successfully!")
    else:
        print("❌ Failed to apply brand frame.")

if __name__ == "__main__":
    main()
