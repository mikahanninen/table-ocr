import logging
from PIL import Image, ImageFilter, ImageEnhance
from configuration import TableConfiguration
from typing import Union


def grayscale_image(image):
    return image.convert("L")


def get_binary(image, threshold=100):
    return image.point(lambda p: p > threshold and 255)


def zoom_image(image, configuration):
    zoom_factor = configuration.zoom_factor
    return image.resize(
        (int(image.width * zoom_factor), int(image.height * zoom_factor))
    )


def brighten_image(image, configuration: Union[TableConfiguration, float]):
    brightness = (
        configuration.brightness
        if isinstance(configuration, TableConfiguration)
        else configuration
    )
    enhancer = ImageEnhance.Brightness(image)
    preprocessed_image = enhancer.enhance(brightness)
    return preprocessed_image


def contrast_image(image, configuration: Union[TableConfiguration, float]):
    contrast = (
        configuration.contrast
        if isinstance(configuration, TableConfiguration)
        else configuration
    )
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(contrast)


def sharpen_image(image, configuration):
    if configuration.sharpen:
        # preprocessed_image = preprocessed_image.filter(ImageFilter.SHARPEN)
        preprocessed_image = image.filter(
            ImageFilter.UnsharpMask(radius=1, percent=200, threshold=2)
        )
        return preprocessed_image
    return image


def binarize_image(image, configuration: Union[TableConfiguration, int]):
    threshold_value = (
        configuration.threshold
        if isinstance(configuration, TableConfiguration)
        else configuration
    )
    invert_colors = (
        configuration.invert_colors
        if isinstance(configuration, TableConfiguration)
        else False
    )
    logging.warning(f"threshold_value: {threshold_value}")
    logging.warning(f"invert_colors: {invert_colors}")
    logging.warning(f"image: {type(image)}")
    min_color = 255 if invert_colors else 0
    max_color = 0 if invert_colors else 255
    # target_image = target_image.point(lambda p: p if p <= threshold else 255)
    # Apply thresholding
    if threshold_value > 0:
        preprocessed_image = image.point(
            lambda p: max_color if p > threshold_value else min_color, "1"
        )
        return preprocessed_image
    else:
        return image


def noise_reduct_image(image):
    # Noise Reduction (Simple Blur)
    return image.filter(ImageFilter.GaussianBlur(1))


def preprocess_image(
    image_in: Union[str, Image.Image], configuration: TableConfiguration
):
    original_target_image = (
        Image.open(image_in).convert("RGBA") if isinstance(image_in, str) else image_in
    )

    preprocessed_image = grayscale_image(original_target_image)
    preprocessed_image = zoom_image(preprocessed_image, configuration)
    preprocessed_image = brighten_image(preprocessed_image, configuration)
    preprocessed_image = contrast_image(preprocessed_image, configuration)
    preprocessed_image = sharpen_image(preprocessed_image, configuration)
    preprocessed_image = binarize_image(preprocessed_image, configuration)

    if configuration.show_pre_ocr_image:
        preprocessed_image.show()
    return preprocessed_image, original_target_image
