import copy
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class OCRConfiguration:
    """Configuration for OCR and pre-processing."""

    # These are parameters to adjust OCR pre-processing
    # and the behavior of the OCR itself
    tesseract_oem_mode: int = 3
    tesseract_psm_mode: int = 6
    # -c preserve_interword_spaces=1
    tesseract_configurations: str = ""
    language: str = "eng"
    zoom_factor: int = 8
    brightness: float = 1.4
    contrast: float = 1.2
    confidence_level: int = 40
    # Threshold for binarization. If -1, no binarization is done.
    threshold: int = 190
    invert_colors: bool = False
    sharpen: bool = False
    # display preprocessed image prior it is sent to OCR
    show_pre_ocr_image: bool = False
    # display image showing recognized table and its columns
    show_post_recognition_image: bool = False

    def clone(self):
        # Create a deep copy of the current instance and return it.
        # This ensures that mutable objects are also copied and independent.
        return copy.deepcopy(self)


@dataclass
class TableConfiguration(OCRConfiguration):
    """Configuration for OCR table reading.

    Requires headers and columns to be defined.

    :param OCRConfiguration: configuration for OCR
    """

    headers: List[str] = field(default_factory=list)
    margins: Dict[str, int] = field(default_factory=dict)
    column_definitions: Dict[str, Dict] = field(default_factory=dict)
    # by default all columns are highlighted, but you can specify which ones
    column_highlights: List[str] = field(default_factory=list)
    # any column in this collection will be cropped into separate images
    column_to_crop: List[str] = field(default_factory=list)

    def set_margins(self, bottom: int = 0, top: int = 0):
        self.margins["bottom"] = bottom
        self.margins["top"] = top

    def set_column(self, column_name: str, left: int = 0, width: int = 50):
        self.column_definitions[column_name] = {"left": {"mod": left}, "width": width}

    def set_fixed_column(self, column_name: str, position: int = 0, width: int = 50):
        self.column_definitions[column_name] = {
            "left": {"fixed": position},
            "width": width,
        }

    def set_inherited_column(
        self,
        column_name: str,
        inherited_column_name: str,
        width: int = 50,
        side: str = "right",
    ):
        self.column_definitions[column_name] = {
            "left": {"column": inherited_column_name, "side": side},
            "width": width,
        }

    def remove_column(self, column_name: str):
        self.column_definitions.pop(column_name, None)
