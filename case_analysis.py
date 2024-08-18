from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
import io
import os

def get_font(font_size):
    # List of font files to try
    font_files = [
        "Arial.ttf",
        "Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttf",
    ]
    
    for font_file in font_files:
        if os.path.exists(font_file):
            return ImageFont.truetype(font_file, font_size)
    
    # If none of the above fonts are found, use the default
    return ImageFont.load_default()

def create_circle_chart(sizes, colors):
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.3))
    ax.add_artist(plt.Circle((0, 0), 0.70, fill=False, edgecolor='white', linewidth=2))
    plt.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    return Image.open(buf)

# Create main image
width, height = 1800, 2400
image = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(image)

# Load fonts
title_font = get_font(60)
header_font = get_font(40)
text_font = get_font(30)

# Colors
blue = "#007bff"
green = "#28a745"
orange = "#ffc107"
red = "#dc3545"
purple = "#6f42c1"

# Title
draw.text((width//2, 100), "AI-Powered SDLC Optimization", fill=blue, font=title_font, anchor="mm")
draw.text((width//2, 170), "Enhancing Efficiency, Quality, and ROI", fill=blue, font=header_font, anchor="mm")

# SDLC Circle
sdlc_chart = create_circle_chart([1, 1, 1, 1, 1], [blue, green, orange, red, purple])
image.paste(sdlc_chart, (width//2 - 250, 250), sdlc_chart)

# SDLC Phases
phases = ["Requirements", "Design", "Development", "Testing", "Deployment"]
benefits = ["30% faster", "25% quicker", "35% boost", "40% less defects", "35% fewer issues"]
y_pos = 800
for phase, benefit in zip(phases, benefits):
    draw.text((width//4, y_pos), f"{phase}:", fill=blue, font=header_font, anchor="rm")
    draw.text((width//4 + 20, y_pos), benefit, fill=green, font=text_font, anchor="lm")
    y_pos += 70

# ROI and Financial Impact
draw.text((width//2, 1200), "ROI and Financial Impact", fill=blue, font=header_font, anchor="mm")
financial_impacts = [
    "15-25% Development Cost Reduction",
    "10-20% Revenue Increase",
    "20-30% Maintenance Cost Savings",
    "30-40% Reduction in Post-Release Defects"
]
y_pos = 1250
for impact in financial_impacts:
    draw.text((width//2, y_pos), "•", fill=orange, font=header_font, anchor="mm")
    draw.text((width//2 + 20, y_pos), impact, fill="black", font=text_font, anchor="lm")
    y_pos += 50

# Team Efficiency Gains
draw.text((3*width//4, 800), "Team Efficiency Gains", fill=blue, font=header_font, anchor="mm")
efficiency_gains = [
    "Product Managers: 15-25%",
    "Delivery Leads: 10-20%",
    "Developers: 20-30%",
    "QA Team: 25-35%",
    "Business Analysts: 20-30%"
]
y_pos = 850
for gain in efficiency_gains:
    draw.text((3*width//4, y_pos), "•", fill=red, font=header_font, anchor="mm")
    draw.text((3*width//4 + 20, y_pos), gain, fill="black", font=text_font, anchor="lm")
    y_pos += 50

# Competitive Advantages
draw.text((width//2, 1500), "Competitive Advantages", fill=blue, font=header_font, anchor="mm")
advantages = [
    "Faster Time-to-Market: 20-30% reduction",
    "Increased Team Capacity: 15-25% without additional hiring",
    "Improved Product Quality: 30-40% defect reduction",
    "Enhanced Customer Satisfaction",
    "Attraction and Retention of Top Talent"
]
y_pos = 1550
for advantage in advantages:
    draw.text((width//2, y_pos), "•", fill=green, font=header_font, anchor="mm")
    draw.text((width//2 + 20, y_pos), advantage, fill="black", font=text_font, anchor="lm")
    y_pos += 50

# Risk Mitigation
draw.text((width//2, 1850), "Risk Mitigation", fill=blue, font=header_font, anchor="mm")
risks = [
    "Reduced dependency on individual knowledge",
    "Improved code consistency and best practices",
    "Better documentation and knowledge retention",
    "Enhanced security checks and dependency management"
]
y_pos = 1900
for risk in risks:
    draw.text((width//2, y_pos), "•", fill=red, font=header_font, anchor="mm")
    draw.text((width//2 + 20, y_pos), risk, fill="black", font=text_font, anchor="lm")
    y_pos += 50

# Bottom Line
draw.rectangle([0, height-150, width, height], fill=blue)
draw.text((width//2, height-75), "Empowering Teams, Optimizing Processes, Maximizing ROI", fill="white", font=header_font, anchor="mm")

# Save the image
output_file = "ai_sdlc_optimization_infographic.png"
image.save(output_file)
print(f"Infographic saved as {output_file}")
print(f"Full path: {os.path.abspath(output_file)}")

# Try to open the file automatically
try:
    import webbrowser
    webbrowser.open('file://' + os.path.abspath(output_file))
except Exception as e:
    print(f"Could not open the file automatically. Error: {e}")
    print("Please open the PNG file manually in your image viewer.")