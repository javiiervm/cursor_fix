import os
import base64

# The exact base64 string for a 1x1 pixel 100% transparent PNG
png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Get the absolute path of the directory where this script is currently located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Define the full output path (same directory, named 'transparent_cursor.png')
output_path = os.path.join(current_directory, "transparent_cursor.png")

# Decode the base64 string and write the binary data to the file
with open(output_path, "wb") as f:
    f.write(base64.b64decode(png_b64))

print(f"Success! Transparent PNG created at: {output_path}")
