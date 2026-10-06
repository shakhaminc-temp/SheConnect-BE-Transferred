import os

file_path = 'c:/Users/sanik/OneDrive/Desktop/Sheconnect/clone/SheConnect-BE-Transferred/app/utils/email_templates.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_sos = False
for i, line in enumerate(lines):
    if line.startswith('def get_sos_email_html'):
        in_sos = True
        new_lines.append(line)
        continue
    
    if in_sos:
        if 'maps_url = f"https://www.google.com/maps?q={lat},{lng}"' in line:
            new_lines.append(line)
            new_lines.append('    location_display = f"<div style=\'font-size: 18px; font-weight: bold; color: #111827; margin-bottom: 10px;\'>{location_name}</div>" if location_name and location_name != "Unknown Location" else ""' + '\n')
        elif 'Their current location is:' in line:
            new_lines.append(line)
            new_lines.append('            </p>\n')
            new_lines.append('            {location_display}\n')
            new_lines.append('            <p style="font-size: 14px; color: #6b7280; margin-top: 0;">\n')
            new_lines.append('                Coordinates: {lat}, {lng}\n')
        elif '</p>' in line and 'Their current location is:' in lines[i-1]:
            continue # Skip the closing p tag since we added it
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
