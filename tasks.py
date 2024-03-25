from robocorp.tasks import task
from OCRLibrary import ocr_table, TableConfiguration


@task
def main_ocr_task():
    table_headers = [
        "Date",
        "Payee",
    ]
    table_conf = TableConfiguration()

    table_conf.tesseract_psm_mode = 11
    table_conf.brightness = 1.2
    table_conf.threshold = 200
    table_conf.contrast = 1.0
    table_conf.confidence_level = 0
    table_conf.invert_colors = False
    table_conf.sharpen = True
    table_conf.headers = table_headers

    table_conf.set_column("Date", left=-2, width=80)
    table_conf.set_column("Payee", left=-5, width=350)
    table_conf.set_column("Category", left=-5, width=350)
    table_conf.set_column("Amount", left=-10, width=90)
    table_conf.set_column("Balance", left=-5, width=70)

    table_conf.set_margins(bottom=-10, top=30)
    table_conf.show_pre_ocr_image = True
    table_conf.show_post_recognition_image = True

    table_conf.column_to_crop.append("Amount")
    table_conf.column_to_crop.append("Balance")
    table = ocr_table(
        configuration=table_conf,
        image_in="images/table.png",
        result_json="output/result_table.json",
    )
    for row in table:
        print(row)

    # table2_conf = table_conf.clone()
