import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageEnhance, ImageTk

canvas, contrast_label, threshold_label, brightness_label = None, None, None, None
# Load your image (replace 'your_image.jpg' with the path to your image)
original_image = Image.open(sys.argv[1])
original_width, original_height = original_image.size

# Create a window
window = tk.Tk()
window.title("Image Adjustment Tool")
window.minsize(original_width + 200, original_height + 200)


def update_image(*args):
    if (
        canvas is None
        or brightness_label is None
        or contrast_label is None
        or threshold_label is None
    ):
        return
    # Update scale labels with current values
    brightness_label.config(text=f"Brightness: {brightness_scale.get():.1f}")
    threshold_label.config(text=f"Threshold: {threshold_scale.get():.0f}")
    contrast_label.config(text=f"Contrast: {contrast_scale.get():.1f}")

    brightness_factor = brightness_scale.get()
    threshold_factor = int(threshold_scale.get())
    contrast_factor = contrast_scale.get()

    # Adjust brightness
    enhancer = ImageEnhance.Brightness(original_image)
    preprocessed_image = enhancer.enhance(brightness_factor)

    # Adjust contrast
    enhancer = ImageEnhance.Contrast(preprocessed_image)
    preprocessed_image = enhancer.enhance(contrast_factor)

    # # Apply zoom
    # new_width = original_width * zoom_factor
    # new_height = original_height * zoom_factor
    # zoomed_image = contrast_image.resize((new_width, new_height))
    # # Apply thresholding
    if threshold_factor > 1:
        preprocessed_image = preprocessed_image.convert("L")
        preprocessed_image = preprocessed_image.point(
            lambda p: 255 if p > threshold_factor else 0, "1"
        )

    # Update the image on canvas
    photo = ImageTk.PhotoImage(preprocessed_image)
    canvas.itemconfig(image_on_canvas, image=photo)
    canvas.image = photo  # Prevent garbage collection
    canvas.config(scrollregion=canvas.bbox(tk.ALL))


def copy_to_clipboard():
    clipboard_content = f"""
    table_conf.brightness = {brightness_scale.get():.1f}
    table_conf.threshold = {threshold_scale.get():.0f}
    table_conf.contrast = {contrast_scale.get():.1f}
    """
    window.clipboard_clear()
    window.clipboard_append(clipboard_content)


# Frame for sliders and labels
frame_controls = tk.Frame(window)
frame_controls.pack(fill=tk.X)

# Brightness control
brightness_label = ttk.Label(frame_controls, text="Brightness: 1.00")
brightness_label.pack(side="left")
brightness_scale = ttk.Scale(
    frame_controls, from_=0.1, to_=2.0, orient="horizontal", command=update_image
)
brightness_scale.set(1.4)  # Default value
brightness_scale.pack(side="left")

# Zoom control
threshold_label = ttk.Label(frame_controls, text="Zoom: 1")
threshold_label.pack(side="left")
threshold_scale = ttk.Scale(
    frame_controls,
    from_=1,
    to_=256,
    orient="horizontal",
    command=update_image,
)
threshold_scale.set(190)  # Default value
threshold_scale.pack(side="left")

# Contrast control
contrast_label = ttk.Label(frame_controls, text="Contrast: 1.00")
contrast_label.pack(side="left")
contrast_scale = ttk.Scale(
    frame_controls, from_=0.1, to_=2.0, orient="horizontal", command=update_image
)
contrast_scale.set(1.2)  # Default value
contrast_scale.pack(side="left")

# Button to copy values to clipboard
copy_button = ttk.Button(
    frame_controls, text="Copy to Clipboard", command=copy_to_clipboard
)
copy_button.pack(side="left")

# Frame for the canvas and scrollbars
frame_canvas = tk.Frame(window)
frame_canvas.pack(fill=tk.BOTH, expand=True)

# Canvas with scrollbars
canvas = tk.Canvas(frame_canvas, bg="white")
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scroll_x = tk.Scrollbar(frame_canvas, orient="horizontal", command=canvas.xview)
scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
scroll_y = tk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

# Add the image to the canvas
photo_image = ImageTk.PhotoImage(
    original_image.resize((600, int(600 * (original_height / original_width))))
)
image_on_canvas = canvas.create_image(0, 0, anchor=tk.NW, image=photo_image)
canvas.image = photo_image  # Prevent garbage collection

# Initial configuration for scrolling based on the image size
canvas.config(scrollregion=canvas.bbox(tk.ALL))

update_image()

window.mainloop()
