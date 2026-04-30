from __future__ import annotations

from datetime import date
from pathlib import Path
from struct import unpack
from typing import Iterable
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


EMU_PER_PIXEL = 9525
MAX_IMAGE_WIDTH_EMU = int(6.2 * 914400)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "Звіт_виконання_проєкту_PyPaint.docx"


def paragraph(text: str, *, bold: bool = False, size: int | None = None, center: bool = False) -> str:
    runs = run(text, bold=bold, size=size)
    justify = '<w:jc w:val="center"/>' if center else ""
    return (
        "<w:p>"
        f"<w:pPr>{justify}</w:pPr>"
        f"{runs}"
        "</w:p>"
    )


def spacer() -> str:
    return "<w:p/>"


def run(text: str, *, bold: bool = False, size: int | None = None) -> str:
    properties = []
    if bold:
        properties.append("<w:b/>")
    if size is not None:
        properties.append(f'<w:sz w:val="{size}"/>')
    props = f"<w:rPr>{''.join(properties)}</w:rPr>" if properties else ""
    return f"<w:r>{props}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        signature = file.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"{path.name} is not a PNG file")
        _length = file.read(4)
        chunk = file.read(4)
        if chunk != b"IHDR":
            raise ValueError(f"{path.name} has no IHDR chunk")
        width, height = unpack(">II", file.read(8))
    return width, height


def image_paragraph(rid: str, width_px: int, height_px: int, name: str) -> str:
    width_emu = width_px * EMU_PER_PIXEL
    height_emu = height_px * EMU_PER_PIXEL
    if width_emu > MAX_IMAGE_WIDTH_EMU:
        scale = MAX_IMAGE_WIDTH_EMU / width_emu
        width_emu = int(width_emu * scale)
        height_emu = int(height_emu * scale)

    return f"""
<w:p>
  <w:pPr><w:jc w:val="center"/></w:pPr>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0"
        xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
        <wp:extent cx="{width_emu}" cy="{height_emu}"/>
        <wp:docPr id="1" name="{escape(name)}"/>
        <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:nvPicPr>
                <pic:cNvPr id="0" name="{escape(name)}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{rid}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="{width_emu}" cy="{height_emu}"/>
                </a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>
""".strip()


def content_types(image_count: int) -> str:
    overrides = """
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
""".strip()
    defaults = """
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
""".strip()
    if image_count:
        defaults += '\n  <Default Extension="png" ContentType="image/png"/>'
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
{defaults}
{overrides}
</Types>
"""


def package_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def app_props() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>
"""


def core_props() -> str:
    today = date.today().isoformat()
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Звіт виконання проєкту PyPaint</dc:title>
  <dc:subject>Системне програмування</dc:subject>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{today}T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{today}T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"""


def document_rels(images: Iterable[Path]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for index, _image in enumerate(images, start=1):
        lines.append(
            f'  <Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/image{index}.png"/>'
        )
    lines.append("</Relationships>")
    return "\n".join(lines)


def document_xml(body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def build_report() -> None:
    images = [
        PROJECT_ROOT / "report_assets" / "screenshot_main_window.png",
        PROJECT_ROOT / "report_assets" / "screenshot_clear_confirmation.png",
        PROJECT_ROOT / "report_assets" / "screenshot_help_dialog.png",
        PROJECT_ROOT / "examples" / "example_1_house.png",
    ]

    for image in images:
        if not image.exists():
            raise FileNotFoundError(f"Missing image: {image}")

    parts = [
        paragraph("Звіт виконання проєкту PyPaint", bold=True, size=34, center=True),
        paragraph("Окремий звіт за пунктами плану доопрацювання графічного редактора", size=24, center=True),
        paragraph(f"Дата формування: {date.today().strftime('%d.%m.%Y')}", center=True),
        spacer(),
        paragraph("1. Загальна характеристика", bold=True, size=28),
        paragraph(
            "У межах проєкту PyPaint було проаналізовано та доопрацьовано графічний редактор на PyQt6. "
            "Результатом стали покращення інтерфейсу, вбудована довідка всередині застосунку, "
            "папка з прикладами робіт та підготовлені ілюстрації для захисту проєкту."
        ),
        spacer(),
        paragraph("2. Виконання пунктів плану", bold=True, size=28),
        paragraph("Пункт 1. Зовнішній інтерфейс графічного редактора", bold=True, size=24),
        paragraph(
            "Статус: виконано. Інтерфейс побудований на зрозумілих для користувача назвах: "
            "\"Новий\", \"Зберегти\", \"Олівець\", \"Лінія\", \"Прямокутник\", \"Еліпс\", "
            "\"Стирачка\", \"Колір\", \"Фон\". Для зменшення помилок додано механізми "
            "скасування і повторення дій (Undo/Redo), а також діалоги підтвердження перед "
            "очищенням полотна та перед втратою незбережених змін."
        ),
        paragraph(
            "Критерії логічності та стандартизованості виконано через групування інструментів "
            "на окремі панелі: файлові операції, інструменти малювання, властивості, історія дій "
            "та редагування. Підказки ToolTip і статусний рядок зменшують потребу щось запам'ятовувати "
            "під час переходу між діями."
        ),
        image_paragraph("rId1", *png_size(images[0]), "Головне вікно PyPaint"),
        paragraph("Рис. 1. Головне вікно PyPaint з розділенням команд на функціональні групи.", center=True),
        image_paragraph("rId2", *png_size(images[1]), "Підтвердження очищення полотна"),
        paragraph("Рис. 2. Діалог підтвердження для запобігання помилковому очищенню полотна.", center=True),
        spacer(),
        paragraph("Пункт 2. Підсистема довідкової інформації", bold=True, size=24),
        paragraph(
            "Статус: виконано. У проєкті використовується файл help/index.html, а сама довідка "
            "відкривається безпосередньо в інтерфейсі програми у вбудованому вікні. "
            "Користувач отримує доступ до пояснення інструментів, властивостей, роботи з файлами "
            "та скасування помилок без переходу в зовнішній браузер."
        ),
        image_paragraph("rId3", *png_size(images[2]), "Вбудована довідка PyPaint"),
        paragraph("Рис. 3. Вбудоване вікно довідки з описом можливостей редактора.", center=True),
        spacer(),
        paragraph("Пункт 3. Папка з прикладами редагування", bold=True, size=24),
        paragraph(
            "Статус: виконано. Додано окрему папку examples з кількома демонстраційними зображеннями "
            "та текстовим описом їх призначення. Приклади показують використання ліній, прямокутників, "
            "еліпсів, зміни фону та сценаріїв зі стирачкою. Ці матеріали можна використовувати як "
            "демонстрацію можливостей програми під час захисту."
        ),
        image_paragraph("rId4", *png_size(images[3]), "Приклад з папки examples"),
        paragraph("Рис. 4. Один з підготовлених прикладів для демонстрації можливостей редактора.", center=True),
        spacer(),
        paragraph("Пункт 4. Поділ команд і параметрів на функціональні групи", bold=True, size=24),
        paragraph(
            "Статус: виконано. Команди розподілено на логічні панелі інструментів. Для користувача "
            "доступні окремі групи для роботи з файлами, малюванням, властивостями, історією дій "
            "та редагуванням. У меню \"Вигляд\" реалізовано керування видимістю кожної панелі через "
            "toggleViewAction(), що відповідає вимозі увімкнення та вимкнення функціональних груп."
        ),
        spacer(),
        paragraph("Пункт 5. Зовнішній дизайн та ергономіка", bold=True, size=24),
        paragraph(
            "Статус: виконано частково. Програма вже має світлий робочий простір, компактні панелі, "
            "підказки, статусний рядок та узгоджені назви дій українською мовою. Це позитивно впливає "
            "на сприйняття і базову ергономіку. Водночас можливе подальше покращення візуального стилю: "
            "є сенс розвинути систему іконок, детальніше пропрацювати відступи й типографіку та додати "
            "більш виразну візуальну ієрархію елементів інтерфейсу."
        ),
        spacer(),
        paragraph("3. Підсумок", bold=True, size=28),
        paragraph(
            "За підсумком роботи проєкт PyPaint відповідає основним вимогам плану доопрацювання. "
            "Реалізовано зрозумілий зовнішній інтерфейс, засоби запобігання помилкам, функції Undo/Redo, "
            "вбудовану довідку, приклади робіт у окремій папці та можливість керувати видимістю панелей. "
            "Найближчим резервом розвитку залишається поглиблення зовнішнього дизайну відповідно до "
            "принципів software ergonomics."
        ),
    ]

    body = "\n".join(parts)

    with ZipFile(REPORT_PATH, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types(len(images)))
        archive.writestr("_rels/.rels", package_rels())
        archive.writestr("docProps/app.xml", app_props())
        archive.writestr("docProps/core.xml", core_props())
        archive.writestr("word/document.xml", document_xml(body))
        archive.writestr("word/_rels/document.xml.rels", document_rels(images))
        for index, image in enumerate(images, start=1):
            archive.write(image, f"word/media/image{index}.png")

    print(REPORT_PATH)


if __name__ == "__main__":
    build_report()
