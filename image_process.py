from PIL import Image
import imageio
import numpy as np

# Load the GIF image using imageio.get_reader() with memtest=False
gif_path = "meerkat.gif"
reader = imageio.get_reader(gif_path, memtest=False)

# Process each frame to remove the white background
processed_frames = []
for frame in reader:
    frame = np.array(frame)
    if frame.shape[-1] == 3:  # If there is no alpha channel, add one
        r, g, b = np.rollaxis(frame, axis=-1)
        a = np.ones_like(r) * 255
        frame = np.dstack([r, g, b, a])
    else:
        r, g, b, a = np.rollaxis(frame, axis=-1)
        frame = np.dstack([r, g, b, a])

    mask = (r == 255) & (g == 255) & (b == 255)
    frame[mask] = [255, 255, 255, 0]
    processed_frames.append(frame)

# Save the processed frames as a new GIF
output_gif_path = "meerkat_transparent.gif"
imageio.mimsave(output_gif_path, processed_frames, format='GIF', duration=reader.get_meta_data().get('duration', 0.1))

print(f"Processed GIF saved to {output_gif_path}")