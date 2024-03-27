import json
import logging
import os
import pytesseract
from pytesseract import Output
from typing import Union

from PIL import ImageGrab, Image, ImageDraw

from RPA.Desktop import Desktop
from RPA.Windows import Windows

from configuration import TableConfiguration
from preprocess import preprocess_image

MAX_DISTANCE = 25
MAX_VERTICAL_VARIANCE = 5


def save_image_to_artifacts(image, filename):
    image.save(f"{os.getenv('ROBOT_ARTIFACTS')}/{filename}")


def get_element_coordinates(locator: str, image_path: str = None):
    windows_library = Windows()
    element = windows_library.get_element(locator)
    element_box = (element.left, element.top, element.right, element.bottom)
    image = ImageGrab.grab(bbox=element_box)
    if image_path:
        image.save(image_path)
    element = windows_library.get_element(locator)
    return image, (element.left, element.top)


def find_texts(
    image_in: Union[str, Image.Image],
    image_out: str = None,
    configuration: TableConfiguration = None,
    max_combination_distance=None,
):
    tesseract_oem_mode = configuration.tesseract_oem_mode
    tesseract_psm_mode = configuration.tesseract_psm_mode
    tesseract_configurations = f" {configuration.tesseract_configurations}"
    zoom_factor = configuration.zoom_factor
    # # Initialize variables
    text_blocks = []
    current_text = ""
    start_x, start_y, end_x, end_y = 0, 0, 0, 0

    target_image, original_image = preprocess_image(image_in, configuration)

    if image_out:
        save_image_to_artifacts(target_image, image_out)

    custom_config = rf"--oem {tesseract_oem_mode} --psm {tesseract_psm_mode}{tesseract_configurations}"
    ocr_data = pytesseract.image_to_data(
        target_image,
        output_type=Output.DICT,
        lang=configuration.language,
        config=custom_config,
    )

    if max_combination_distance is None:
        # Process OCR results
        for i in range(len(ocr_data["text"])):
            text = ocr_data["text"][i].strip()
            if text != "":
                logging.warning(
                    f'index {i} text:{ocr_data["text"][i]} left:{ocr_data["left"][i]} conf:{ocr_data["conf"][i]}'
                )
            if (
                text != ""
                and int(ocr_data["conf"][i]) >= configuration.confidence_level
            ):  # Conf = confidence of having foud a word. 100 is the max. TODO: make configurable
                current_text = text
                start_x, start_y = ocr_data["left"][i], ocr_data["top"][i] - 5
                end_x, end_y = (
                    start_x + ocr_data["width"][i],
                    start_y + ocr_data["height"][i],
                )
                middle_x = (start_x + end_x) // 2 / zoom_factor
                middle_y = (start_y + end_y) // 2 / zoom_factor
                text_blocks.append(
                    {
                        "text": current_text,
                        "x": int(middle_x),
                        "y": int(middle_y),
                        "left": start_x / zoom_factor,
                        "top": start_y / zoom_factor,  # - 2,
                        "right": end_x / zoom_factor,
                        "bottom": end_y / zoom_factor,
                    }
                )
                # if current_text == "XXX":
                #     logging.warning("\nSTILL DETECTING SINGLE WORD: XXX\n")
                # elif current_text == "YYY":
                #     logging.warning("\nSTILL DETECTING SINGLE WORD: YYY\n")
    else:
        # Quick and dirty way to reintroduce combining texts to this function.

        # we will combine the found texts if they are approximately on the same line and close enough together
        last_word_end = 0
        for i in range(len(ocr_data["text"])):

            # Check if the current text is on the same line as the previous
            # allowing MAX_VERTICAL_VARIANCE pixels variance
            same_line = (
                abs(ocr_data["top"][i] - start_y) <= MAX_VERTICAL_VARIANCE * zoom_factor
            )
            # Calculate horizontal distance from the end of the last word to the start of the current word
            distance = (ocr_data["left"][i] - last_word_end) / zoom_factor
            # If on the same line and within MAX_DISTANCE pixels on the original scale, concatenate
            if same_line and distance <= max_combination_distance:
                current_text += " " + ocr_data["text"][i]
                end_x = ocr_data["left"][i] + ocr_data["width"][i]
                end_y = max(end_y, ocr_data["top"][i] + ocr_data["height"][i])
            else:
                # Otherwise, store the current text block
                middle_x = (start_x + end_x) // 2 / zoom_factor
                middle_y = (start_y + end_y) // 2 / zoom_factor
                text_blocks.append(
                    {
                        "text": current_text,
                        "x": int(middle_x),
                        "y": int(middle_y),
                    }
                )
                # ... and start start a new block for the text of this iteration of the loop.
                current_text = ocr_data["text"][i]
                start_x, start_y = ocr_data["left"][i], ocr_data["top"][i]
                end_x, end_y = (
                    start_x + ocr_data["width"][i],
                    start_y + ocr_data["height"][i],
                )
                # Update the end position of the last word
                last_word_end = ocr_data["left"][i] + ocr_data["width"][i]

        # Don't forget to add the last text block
        if current_text != "":
            middle_x = (start_x + end_x) // 2 / zoom_factor
            middle_y = (start_y + end_y) // 2 / zoom_factor
            text_blocks.append(
                {
                    "text": current_text,
                    "x": int(middle_x),
                    "y": int(middle_y),
                }
            )

    return text_blocks, original_image


def get_window_coordinates(locator: str, image_path: str = None):
    window = Windows().control_window(locator)
    window_box = (window.left, window.top, window.right, window.bottom)
    image = ImageGrab.grab(bbox=window_box)
    if image_path:
        image.save(image_path)
    return image, (window.left, window.top)


def find_and_click(
    locator,
    search_word,
    configuration=None,
    image_path=None,
    max_combination_distance: float = None,
):
    """
    Finds given text from the screen and clicks it
    Arguments:
    - locator: locator for the window from where to find the text
    - search_word: text to look for
    - configuration: ???
    - image_path: path where to save the window from where to search the text
    - max_combination_distance: If found texts are within this number of pixel horizontally, the texts are considered to be part of same text
    """
    image, offsets = get_window_coordinates(locator, image_path=image_path)
    texts, image = find_texts(
        original_target_image=image,
        configuration=configuration,
        image_out=image_path,
        max_combination_distance=max_combination_distance,
    )
    result = find_matching(
        texts, search_word, inclusive=False, case_sensitive=True, offsets=offsets
    )
    if result:
        padding = 5
        print(f"RESULT: {result}")
        Desktop().click(result[0]["point"])
        draw = ImageDraw.Draw(image)
        if max_combination_distance is None:
            left, top, right, bottom = (
                result[0]["match"]["left"] - padding,
                result[0]["match"]["top"] - padding,
                result[0]["match"]["right"] + padding,
                result[0]["match"]["bottom"] + padding,
            )
            draw.rectangle([left, top, right, bottom], outline="red", width=2)
        image.show()
    else:
        raise ValueError(f"Could not find text: {search_word}")


def find_matching(
    texts,
    search,
    inclusive: bool = False,
    case_sensitive: bool = False,
    offsets: tuple = (0, 0),
):
    print(f"FINDING MATCH FOR: {search}\n")
    matches = []
    for text in texts:
        logging.warning(text)
        search = search if case_sensitive else search.lower()
        image_text = text["text"] if case_sensitive else text["text"].lower()
        image_text = image_text.strip()
        if inclusive and search in image_text:
            matches.append(
                {
                    "text": text["text"],
                    "point": f"point:{int(text['x'])+offsets[0]},{int(text['y'])+offsets[1]}",
                    "match": text,
                }
            )
        elif not inclusive and search == image_text:
            matches.append(
                {
                    "text": text["text"],
                    "point": f"point:{int(text['x'])+offsets[0]},{int(text['y'])+offsets[1]}",
                    "match": text,
                }
            )
    return matches


def combine_by_top_range(dicts):
    """
    Takes the read OCR table data as input and then determines, which individual found words
    are on the same row. This is determined based on the top (y) coordinate of each found word.

    A word is considered to be start of a new row if the top value of the word
    is not within 8 pixels (abs) of the top row of any existing rows.

    Returns a dictionary where each key is top coordtinate of a row.
    Under each of these keys are the words as a list that make the row.
    Each word is in the same format as it was in the input.

    The returned dictionary is ordered based on y values.
    The list of words for each key is ordered based on x value.
    """
    combined = {}
    for d in dicts:
        top_value = d["top"] - 4
        found = False
        for key in combined:
            if abs(top_value - key) <= 8:  # This should be made a parameter.
                # Adding the word to existing row
                combined[key].append(d)
                found = True
                break
        if not found:
            # Creating key to row dictionary with top value of the word as the key.
            combined[top_value] = [d]

    # Sort each list within the combined dictionary based on 'left' values
    for key in combined:
        combined[key].sort(key=lambda x: x["left"])

    # Sort the combined dictionary by its keys (the 'top' values)
    return dict(sorted(combined.items()))


def find_header_row(rows, header_texts):
    for key, val in rows.items():
        # logging.warning(f"key: {key} val: {val}")
        # Check if all header texts are in the 'text' key of the row
        row_texts = [item["text"] for item in val]
        logging.warning(f"row_texts: {row_texts}")
        if all(item in row_texts for item in header_texts):

            # Making sure that the row only contains the given headers!
            # Otherwise a row with texts "abc defg" would be valid
            # in situation where we know that row contains only "abcd"
            # When comparing we only take into account texs longer than 1 character
            # because borders and other graphical glitches may be read as single characters
            for actual_header in row_texts:
                if len(actual_header) > 1:
                    if actual_header not in row_texts:
                        continue
                else:
                    # The row contains (and only contains wanted headers and the length of row is larger than 1)
                    # We shall assume thatthis is the header row
                    return key, val
    return None, None


def get_item_attribute(items, target_text, attribute):
    for item in items:
        if item["text"] == target_text:
            attr = item.get(attribute)
            return int(attr) if isinstance(attr, float) else attr
    return None


def determine_column(header, column_definitions):
    for col_name, col_def in column_definitions.items():
        if header["left"] >= col_def["left"] and header["right"] <= (
            col_def["left"] + col_def["width"]
        ):
            return col_name
    return None


def calculate_column_definitions(configuration, header):
    column_definitions = configuration.column_definitions
    result = {}

    for key, val in column_definitions.items():
        result[key] = {}
        if "fixed" in val["left"]:
            result[key]["left"] = val["left"]["fixed"]
        elif "mod" in val["left"]:
            logging.warning(f"KEY: {key}")
            result[key]["left"] = (
                get_item_attribute(header, key, "left") + val["left"]["mod"]
            )
        elif "column" in val["left"]:

            result[key]["left"] = (
                get_item_attribute(header, val["left"]["column"], "left") + val["width"]
            )
        result[key]["width"] = val["width"]
    return result


def draw_post_recognition_image(image, configuration, data, header, column_definitions):
    original_image = image.copy()
    draw = ImageDraw.Draw(image)

    # Draw lines for each group
    for top, group in data.items():
        if not group:
            continue
        smallest_left = min(group, key=lambda x: x["left"])["left"]
        largest_right = max(group, key=lambda x: x["right"])["right"]
        # Draw a horizontal red line
        draw.line([(smallest_left, top), (largest_right, top)], fill="red", width=2)

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    # Pink color with transparency
    pink_transparent = (255, 192, 203, 128)  # RGBA
    lightblue_transparent = (173, 216, 230, 128)  # RGBA
    red = (255, 0, 0)  # RGB for red
    # Draw rectangles
    table_top = header[0]["bottom"]
    table_bottom = image.size[1]
    index = 1

    column_highlights = configuration.column_highlights
    for key, val in column_definitions.items():
        left = val["left"]
        width = val["width"]
        right = left + width
        column_definitions[key]["right"] = right

        if key in configuration.column_to_crop:
            cropped_image = original_image.crop((left, table_top, right, table_bottom))
            save_image_to_artifacts(cropped_image, f"column_{key.lower()}.png")
        # Draw vertical red lines
        if len(column_highlights) == 0 or key in column_highlights:
            if index % 2 == 0:
                draw.rectangle(
                    [left, table_top, right, table_bottom], fill=pink_transparent
                )
            else:
                draw.rectangle(
                    [left, table_top, right, table_bottom],
                    fill=lightblue_transparent,
                )
            draw.line([(left, table_top), (left, table_bottom)], fill=red, width=1)
            draw.line([(right, table_top), (right, table_bottom)], fill=red, width=1)
        index += 1
    return draw, overlay, table_top, table_bottom


def ocr_table(
    configuration: TableConfiguration,
    image_in: Union[str, Image.Image] = None,
    result_json: str = None,
):
    """
    Read table with OCR as specified in the given configuration.

    Arguments:
    - configuration: details on how OCR should be done
    - image_in: PIL image or path to the image.
    - result_json: if given the result JSON will be written into this file
    """
    logging.warning(f"CONFIGURATION: {configuration}")
    table = []
    headers = configuration.headers
    top_margin = configuration.margins["top"]
    bottom_margin = configuration.margins["bottom"]

    data, image = find_texts(
        image_in=image_in,
        configuration=configuration,
        image_out="preprocessed_image_for_tesseract.png",
    )
    data = combine_by_top_range(data)
    top, header = find_header_row(data, headers)
    if top is None or header is None:
        raise ValueError(f"Could not find header row with texts: {headers}")
    else:
        print(f"\nHEADER {top} = {header}")
    column_definitions = calculate_column_definitions(configuration, header)
    logging.warning(
        f"\n\nFINALIZED COLUMN DEFINITIONS\n{'-'*40}\n{json.dumps(column_definitions, indent=4)}\n\n"
    )
    draw, overlay, table_top, table_bottom = draw_post_recognition_image(
        image, configuration, data, header, column_definitions
    )
    # Construct table
    for _, row in data.items():
        table_row = {}
        for column in row:
            if column["top"] < (table_top + top_margin):
                continue
            if column["bottom"] > (table_bottom + bottom_margin):
                break
            column_name = determine_column(column, column_definitions)
            if column_name:
                if column_name in table_row.keys():
                    table_row[column_name] += " " + column["text"]
                else:
                    table_row[column_name] = column["text"]
                # Draw a black dot
                radius = 3
                left_up_point = (column["x"] - radius, column["y"] - radius)
                right_down_point = (column["x"] + radius, column["y"] + radius)
                draw.ellipse([left_up_point, right_down_point], fill="black")

            print(f"column_name:{column_name} column_text:{column['text']}")

        if len(table_row.keys()) > 0:
            # Adding the row to the table to be returned
            # and adding a clickable point for it as keys x and y
            smallest_left = min(row, key=lambda x: x["left"])["left"]
            largest_right = max(row, key=lambda x: x["right"])["right"]
            smallest_top = min(row, key=lambda x: x["top"])["top"]
            largest_bottom = max(row, key=lambda x: x["bottom"])["bottom"]
            table_row["x"] = int((smallest_left + largest_right) / 2)
            table_row["y"] = int((smallest_top + largest_bottom) / 2)
            table.append(table_row)

    # Add empty values for columns that were not found
    for row in table:
        for key in column_definitions.keys():
            row.setdefault(key, "")
    # Merge overlay with the original image
    combined = Image.alpha_composite(image.convert("RGBA"), overlay)
    if configuration.show_post_recognition_image:
        combined.show()
    save_image_to_artifacts(combined, "table_rows_and_columns_identified.png")

    print(f"\nCOLUMN DEFINITIONS:\n{json.dumps(column_definitions, indent=4)}\n")

    if result_json:
        with open(result_json, "w", encoding="utf-8") as outfile:
            json.dump(table, outfile, ensure_ascii=False, indent=4)
    return table


def get_locator_for_clicking_row_of_the_read_table(table, wanted_items_on_row):
    """
    Returns X and Y coordinates for clicking of the row as a string of format:
    point:x, y
    """
    row = get_row_from_read_ocr_table(table, wanted_items_on_row)
    x = int(row["x"])
    y = int(row["y"])
    return "point:" + str(x) + "," + str(y)


def get_row_from_read_ocr_table(table, wanted_items_on_row):
    """
    Returns the first matching row from read ocr table.
    Arguments:
    wanted_items_on_row: dictionary with keys and values
    representing the data that the row must contain on each row.
    Each key represents the column
    and each value represents wanted value in that column
    """
    for row in table:
        for key in wanted_items_on_row.keys():
            if key in row.keys() and row[key] == wanted_items_on_row[key]:
                return row
    raise ValueError(
        "No row found from the read ocr table with given specs: " + wanted_items_on_row
    )


def calibrate_read_table_coordinates_to_global_coordinates(
    table, window_left, window_top
):
    """
    The table read with function ocr tables has its coordinates in format where
    X and Y coodinates are relative to the top left corner of the window.

    This keyword modifies these coordinates to be the coordinates on the screen.

    Arguments:
    - table: data returned by ocr_tables() function (represents data in a table)
    - top: top y coordinate of the window that contains the table found with ocr_tables function
    - left: leftmost x coordinates of the window that contains the table found with ocr_tables function
    """
    for item in table:
        item["x"] = int(window_left + item["x"])
        item["y"] = int(window_top + item["y"])

    return table
