import os
from PIL import Image

def process_logo(logo_path, opacity=0.8):
    logo = Image.open(logo_path).convert("RGBA")
    
    # Remove white background
    datas = logo.getdata()
    new_data = []
    for item in datas:
        if item[0] > 220 and item[1] > 220 and item[2] > 220:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    logo.putdata(new_data)
    
    # Apply global opacity
    datas = logo.getdata()
    new_data = []
    for item in datas:
        new_data.append((item[0], item[1], item[2], int(item[3] * opacity)))
    logo.putdata(new_data)
    return logo

def create_sample():
    main_img_path = r"F:\Cem_copok\photo.jpg"
    logo_path = r"F:\Cem_copok\logo.jpg"
    out_br = r"C:\Users\Admin\.gemini\antigravity\brain\6d9e3217-4ee3-484b-9388-5f870b0fcb5b\sample_br.png"
    out_tc = r"C:\Users\Admin\.gemini\antigravity\brain\6d9e3217-4ee3-484b-9388-5f870b0fcb5b\sample_tc.png"
    
    if not os.path.exists(main_img_path):
        main_img = Image.new('RGB', (1024, 768), color = (73, 109, 137))
    else:
        main_img = Image.open(main_img_path).convert("RGBA")
        
    logo = process_logo(logo_path, opacity=0.8)
    
    # Resize logo to 12.5% of main image width (half of previous 25%)
    logo_width = int(main_img.width * 0.125)
    aspect_ratio = logo.height / logo.width
    logo_height = int(logo_width * aspect_ratio)
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
    
    # --- Sample 1: Bottom Right ---
    padding = int(main_img.width * 0.03)
    pos_br = (main_img.width - logo_width - padding, main_img.height - logo_height - padding)
    trans_br = Image.new('RGBA', main_img.size, (0,0,0,0))
    trans_br.paste(logo, pos_br)
    res_br = Image.alpha_composite(main_img.convert("RGBA"), trans_br)
    res_br.save(out_br, format="PNG")
    
    # --- Sample 2: Top Center ---
    pos_tc = (int((main_img.width - logo_width) / 2), padding)
    trans_tc = Image.new('RGBA', main_img.size, (0,0,0,0))
    trans_tc.paste(logo, pos_tc)
    res_tc = Image.alpha_composite(main_img.convert("RGBA"), trans_tc)
    res_tc.save(out_tc, format="PNG")
    
    print("Samples created!")

if __name__ == "__main__":
    create_sample()
