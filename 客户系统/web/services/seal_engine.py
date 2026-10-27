# -*- coding: utf-8 -*-
"""
盖章小工具 - 核心引擎
功能：封面识别、三页生成（封面/署名/资质）、删除原封面、转PDF、合并下载
流程：上传docx → 识别封面项目名与报告类型 → 选择资质等级/印章 → 生成三页
      → 替换原封面 → LibreOffice 转 PDF → 三页PDF+正文PDF合并 → 下载
"""
import os, re, shutil, subprocess, datetime, zipfile
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Pt, Mm, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
# LibreOffice 路径：Windows 走安装目录，Linux（Ubuntu）直接用 soffice 命令
if os.name == "nt":
    _so = r"C:\Program Files\LibreOffice\program\soffice.exe"
    if not os.path.exists(_so):
        _so = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
    SOFFICE = _so
else:
    SOFFICE = "soffice"

# A4 尺寸（pt）
A4_W, A4_H = 595.3, 841.9
MM = 72 / 25.4  # 1mm 对应的 pt

# ---------------- 公司与人员配置 ----------------
COMPANY = "河北鑫奥工程咨询有限公司"
ISSUE_ORG_A = "中国工程咨询协会"      # 甲级发证机关
ISSUE_ORG_B = "河北省工程咨询协会"    # 乙级发证机关
CERT_NO = {"甲级": "甲032024011415", "乙级": "乙032025010063"}
CERT_FILE = {"甲级": "鑫奥新甲级.png", "乙级": "鑫奥新乙级.jpg"}
SEAL_FILE = {"公章": "鑫奥公章.png", "技术成果章": "鑫奥技术章.png"}

# 署名页人员（姓名 → 手写签名图）
SIGNATURES = {
    "文德芳": "签名_文德芳.png",
    "田贵桃": "签名_田贵桃.png",
    "屠立亚": "签名_屠立亚.png",
    "王芬芬": "签名_王芬芬.png",
    "席照辉": "签名_席照辉.png",
}
SIGNATURE_SOURCE = {
    "文德芳": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image1.png"),
    "田贵桃": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image2.png"),
    "屠立亚": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image3.jpeg"),
    "王芬芬": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image4.png"),
    "席照辉": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image5.png"),
    "马立亚": os.path.join(ASSETS_DIR, "工程师签名", "马立亚.png"),
    "杨亚杰": os.path.join(ASSETS_DIR, "工程师签名", "杨亚杰.png"),
    "吴梦莹": os.path.join(ASSETS_DIR, "工程师签名", "吴梦莹.png"),
    "张喆": os.path.join(ASSETS_DIR, "工程师签名", "张喆.png"),
}

# 网页端校对人员下拉可选项（4 位工程师手写签名）
REVIEWER_OPTIONS = ["马立亚", "杨亚杰", "吴梦莹", "张喆"]
PROF_STAMPS = {
    "文德芳": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image7.png"),  # 文德芳执业章
    "田贵桃": os.path.join(ASSETS_DIR, "署名页模板内嵌图", "image6.png"),  # 田贵桃执业章
}

# ---------------- 封面识别 ----------------
REPORT_TYPES = [
    "可行性研究报告", "项目建议书", "资金申请报告", "节能报告", "节能评估报告",
    "社会稳定风险评估报告", "PPP项目绩效评价报告", "绩效评价报告", "专项债券实施方案",
    "实施方案", "初步设计", "可行性研究", "规划编制",
]

def _parse_cover_lines(lines):
    """从文本行中识别报告类型与项目名称（docx / PDF 共用）"""
    if not lines:
        return "", "", ["未在文档前部识别到文本封面，请手动填写"]
    type_line = None
    for t in lines:
        for rt in REPORT_TYPES:
            if rt in t:
                type_line = t
                break
        if type_line:
            break
    name_lines = []
    if type_line is not None:
        idx = lines.index(type_line)
        for t in lines[:idx]:
            if len(t) < 3:
                continue
            if any(k in t for k in ["有限公司", "咨询公司", "二〇", "年", "月"]):
                continue
            name_lines.append(t)
    project_name = " ".join(name_lines) if name_lines else (lines[0] if lines else "")
    report_type = type_line.strip() if type_line else ""
    if report_type:
        for rt in REPORT_TYPES:
            if rt in report_type:
                report_type = rt
                break
    return project_name, report_type, []

def parse_cover_from_docx(docx_path):
    """读取 docx 第一个分页前的文本，识别报告类型与项目名称"""
    doc = Document(docx_path)
    lines = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        lines.append(t)
        # 遇到分页符视为封面结束
        if p._p.findall(qn('w:r') + '/' + qn('w:br')):
            brs = p._p.findall('.//' + qn('w:br'))
            if any(b.get(qn('w:type')) == 'page' for b in brs):
                break
    return _parse_cover_lines(lines)

def parse_cover_from_pdf(pdf_path):
    """从 PDF 首页提取文本，识别报告类型与项目名称（文字型 PDF 适用）"""
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text("text")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    doc.close()
    if not lines:
        return "", "", ["PDF 首页未识别到文字（可能是扫描件/图片版封面），请手动填写"]
    return _parse_cover_lines(lines)

# ---------------- 工具函数 ----------------
def chinese_date(dt=None):
    """2026-10 → 二〇二六年十月"""
    dt = dt or datetime.datetime.now()
    digits = "〇一二三四五六七八九"
    def cn_year(n):
        return "".join(digits[int(c)] for c in str(n))
    def cn_month(n):
        if n == 10: return "十"
        if n == 11: return "十一"
        if n == 12: return "十二"
        return digits[n]
    return f"{cn_year(dt.year)}年{cn_month(dt.month)}月"

if os.name == "nt":
    CN_FONT_SONG = "宋体"
    CN_FONT_HEI = "黑体"
else:
    CN_FONT_SONG = "Noto Serif CJK SC"
    CN_FONT_HEI = "Noto Sans CJK SC"


def _map_cn_font(name_cn):
    """把中文习惯字体名映射为当前系统真实存在的字体名。

    Windows 有“宋体/黑体”，Ubuntu 只有思源字体。
    不映射的话 LibreOffice 转 PDF 时查不到该字体，
    会回退到无中文字形的字体，中文显示为方块。
    """
    if name_cn in ("宋体", "SimSun"):
        return CN_FONT_SONG
    if name_cn in ("黑体", "SimHei"):
        return CN_FONT_HEI
    return name_cn


def set_run_font(run, name_cn="宋体", size_pt=14, bold=False):
    name_cn = _map_cn_font(name_cn)
    run.font.name = name_cn
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name_cn)
    rFonts.set(qn('w:ascii'), name_cn)
    rFonts.set(qn('w:hAnsi'), name_cn)

def _fix_all_run_fonts(doc):
    """强制修正文档内所有 rFonts（正文、段落标记、表格与样式表）。"""
    roots = [doc.element.body]
    try:
        roots.append(doc.styles.element)
    except Exception:
        pass
    for root in roots:
        for rFonts in root.iter(qn('w:rFonts')):
            old = rFonts.get(qn('w:eastAsia')) or rFonts.get(qn('w:ascii')) or "宋体"
            fixed = _map_cn_font(old)
            for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                key = qn(attr)
                if key in rFonts.attrib:
                    del rFonts.attrib[key]
            rFonts.set(qn('w:eastAsia'), fixed)
            rFonts.set(qn('w:ascii'), fixed)
            rFonts.set(qn('w:hAnsi'), fixed)


def add_para(doc, text="", font="宋体", size=14, bold=False, align=None,
             before=0, after=0, line=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line:
        pf.line_spacing = Pt(line)
    if text:
        r = p.add_run(text)
        set_run_font(r, font, size, bold)
    return p

def add_paragraph_image(doc, img_path, width_pt):
    """行内插图（居中）"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.add_picture(img_path, width=Pt(width_pt))
    return p

def add_floating_image(doc, img_path, width_pt, x_mm, y_mm, opacity=1.0):
    """在页面绝对位置插入浮动图片（章/水印）。x_mm,y_mm 为相对页面左上角的毫米坐标。"""
    from PIL import Image as PILImage
    with PILImage.open(img_path) as im:
        w, h = im.size
    height_pt = width_pt * h / w
    width_emu = int(width_pt * 12700)
    height_emu = int(height_pt * 12700)
    x_emu = int(x_mm * 36000)
    y_emu = int(y_mm * 36000)

    p = doc.add_paragraph()
    run = p.add_run()
    rId, image_part = doc.part.get_or_add_image(img_path)
    drawing = OxmlElement('w:drawing')
    wp = OxmlElement('wp:anchor')
    wp.set(qn('wp:distT'), "0"); wp.set(qn('wp:distB'), "0")
    wp.set(qn('wp:distL'), "0"); wp.set(qn('wp:distR'), "0")
    wp.set(qn('wp:simplePos'), "0")
    wp.set(qn('wp:relativeHeight'), "0")
    wp.set(qn('wp:behindDoc'), "0")
    wp.set(qn('wp:locked'), "0")
    wp.set(qn('wp:layoutInCell'), "1")
    wp.set(qn('wp:allowOverlap'), "1")
    # simplePos
    sp = OxmlElement('wp:simplePos'); sp.set(qn('wp:x'), "0"); sp.set(qn('wp:y'), "0"); wp.append(sp)
    # positionH
    posh = OxmlElement('wp:positionH'); posh.set(qn('wp:relativeFrom'), "page")
    off = OxmlElement('wp:posOffset'); off.text = str(x_emu); posh.append(off); wp.append(posh)
    # positionV
    posv = OxmlElement('wp:positionV'); posv.set(qn('wp:relativeFrom'), "page")
    off2 = OxmlElement('wp:posOffset'); off2.text = str(y_emu); posv.append(off2); wp.append(posv)
    # extent
    ext = OxmlElement('wp:extent'); ext.set(qn('wp:cx'), str(width_emu)); ext.set(qn('wp:cy'), str(height_emu)); wp.append(ext)
    # effectExtent
    ee = OxmlElement('wp:effectExtent'); ee.set(qn('wp:l'), "0"); ee.set(qn('wp:t'), "0"); ee.set(qn('wp:r'), "0"); ee.set(qn('wp:b'), "0"); wp.append(ee)
    # wrapNone
    wn = OxmlElement('wp:wrapNone'); wp.append(wn)
    # docPr
    dp = OxmlElement('wp:docPr'); dp.set('id', str(abs(hash(img_path)) % 100000)); dp.set('name', "seal"); wp.append(dp)
    # graphic
    g = OxmlElement('a:graphic'); g.set(qn('a:uri'), "http://schemas.openxmlformats.org/drawingml/2006/main")
    gd = OxmlElement('a:graphicData'); gd.set('uri', "http://schemas.openxmlformats.org/drawingml/2006/picture")
    pic = OxmlElement('pic:pic')
    nv = OxmlElement('pic:nvPicPr')
    cnv = OxmlElement('pic:cNvPr'); cnv.set('id', "0"); cnv.set('name', "seal"); nv.append(cnv)
    cnvpr = OxmlElement('pic:cNvPicPr'); nv.append(cnvpr)
    pic.append(nv)
    blipf = OxmlElement('pic:blipFill')
    blip = OxmlElement('a:blip'); blip.set(qn('r:embed'), rId)
    blipf.append(blip)
    st = OxmlElement('a:stretch'); sf = OxmlElement('a:fillRect'); st.append(sf); blipf.append(st)
    pic.append(blipf)
    spPr = OxmlElement('pic:spPr')
    xfrm = OxmlElement('a:xfrm')
    ooff = OxmlElement('a:off'); ooff.set('x', "0"); ooff.set('y', "0"); xfrm.append(ooff)
    oext = OxmlElement('a:ext'); oext.set('cx', str(width_emu)); oext.set('cy', str(height_emu)); xfrm.append(oext)
    spPr.append(xfrm)
    prst = OxmlElement('a:prstGeom'); prst.set('prst', "rect"); av = OxmlElement('a:avLst'); prst.append(av); spPr.append(prst)
    pic.append(spPr)
    gd.append(pic); g.append(gd); wp.append(g)
    drawing.append(wp)
    run._element.append(drawing)
    return p

# ---------------- 水印渲染 ----------------
def render_watermark(img_path, text, out_path, opacity=0.45):
    """在证书图片上渲染斜向水印：'仅限于{项目名}项目使用'（浮于证书文字上方）"""
    with Image.open(img_path) as im:
        im = im.convert("RGBA")
        w, h = im.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # 字体：按图大小缩放
    font_size = int(min(w, h) * 0.045)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", font_size)
    except Exception:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", font_size)
    # 斜向铺满：45 度，多行
    color = (255, 80, 80, int(255 * opacity))
    step = int(font_size * 2.6)
    draw_line = ImageDraw.Draw(overlay)
    n = int((w + h) / step) + 2
    for i in range(-n // 2, n // 2 + 1):
        x0 = -h + i * step
        y0 = h - 20
        draw_line.text((x0, y0), text, font=font, fill=color)
    overlay = overlay.rotate(45, expand=False, resample=Image.BICUBIC)
    # rotate 后可能超出，重新裁回
    out = Image.alpha_composite(im, overlay)
    out.save(out_path, "PNG")
    return out_path


def make_signature_image(name, out_path):
    """生成手写风格签名图（楷体 + 轻微倾斜 + 笔画抖动），透明底 PNG。
    当校对人员姓名没有现成的手写签名素材时使用。"""
    import random
    size = 260
    font = None
    if os.name == "nt":
        candidates = (r"C:\Windows\Fonts\simkai.ttf", r"C:\Windows\Fonts\STKAITI.TTF",
                      r"C:\Windows\Fonts\msyh.ttc")
    else:
        # Linux/Ubuntu 常用中文字体（楷体不常见，用黑体/思源兜底）
        candidates = ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                      "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                      "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                      "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc")
    for fp in candidates:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size)
                break
            except Exception:
                continue
    if font is None:
        raise RuntimeError("找不到可用的中文字体，无法自动生成签名（改用现成签名素材即可）")
    bbox = font.getbbox(name)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 40
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((pad - bbox[0], pad - bbox[1]), name, font=font, fill=(0, 0, 0, 255))
    # 逐字轻微旋转 + 整体倾斜，模拟手写
    im = im.rotate(random.uniform(3, 8), expand=True, resample=Image.BICUBIC,
                   fillcolor=(0, 0, 0, 0))
    im.save(out_path, "PNG")
    return out_path

# ---------------- 三页生成（三个独立 docx → 各自转 PDF → 合并） ----------------
def build_cover_page(project_name, report_type, out_path, date_text=None):
    """第一页：封面（与模板 PDF 对齐：单位 y≈700pt，公章由 PDF 层盖在单位下方）"""
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Emu(int(A4_W * 914400 / 72)); sec.page_height = Emu(int(A4_H * 914400 / 72))
    sec.left_margin = Mm(31.75); sec.right_margin = Mm(31.75)
    sec.top_margin = Mm(25.4); sec.bottom_margin = Mm(25.4)
    date_text = date_text or chinese_date()

    # 顶部留白后写项目名称（最多两行，模板断点：地名列表/工程名）
    for _ in range(4):
        add_para(doc, "", size=14, line=24)
    name_parts = split_name_lines(project_name, 2)
    for part in name_parts:
        add_para(doc, part, font="黑体", size=22, bold=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER, after=8, line=34)
    add_para(doc, "", size=14, line=24)
    add_para(doc, report_type, font="黑体", size=26, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, after=0, line=38)
    # 中部留白：单位推到 y≈700pt（模板位置），日期在其下
    for _ in range(16):
        add_para(doc, "", size=14, line=24)
    add_para(doc, COMPANY, font="宋体", size=16, bold=False,
             align=WD_ALIGN_PARAGRAPH.CENTER, after=6, line=26)
    add_para(doc, date_text, font="宋体", size=16, align=WD_ALIGN_PARAGRAPH.CENTER, line=26)
    doc.save(out_path)
    return out_path


def _find_docx_media(docx_path, stem):
    """返回 docx 包内 word/media/<stem>.* 的实际路径，找不到返回 None。"""
    with zipfile.ZipFile(docx_path) as z:
        for name in z.namelist():
            if name.startswith("word/media/" + stem + "."):
                return name
    return None


def _replace_docx_media(docx_path, media_name, new_image_path):
    """替换 docx 包内指定媒体文件，保持原有显示尺寸与位置不变。"""
    tmp = docx_path + ".media.tmp"
    with zipfile.ZipFile(docx_path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == media_name:
                with open(new_image_path, "rb") as fh:
                    data = fh.read()
            zout.writestr(item, data)
    os.replace(tmp, docx_path)


def build_signature_page(project_name, report_type, level, out_path, reviewer="马立亚"):
    """第二页：署名页 —— 直接复制用户模板《署名页格式.docx》并替换文字，版式完全一致。
    reviewer：校对人员姓名（可在网页上修改，默认屠立亚）"""
    tpl = os.path.join(ASSETS_DIR, "署名页格式.docx")
    shutil.copy(tpl, out_path)

    # 用所选校对人员的签名替换模板中的签字图，位置与尺寸完全沿用模板，
    # 保证与上方“项目负责人/总工程师”人名的文字左边缘对齐。
    sig_src = SIGNATURE_SOURCE.get(reviewer)
    if not (sig_src and os.path.exists(sig_src)):
        try:
            sig_src = os.path.join(os.path.dirname(out_path), "_reviewer_sig.png")
            make_signature_image(reviewer, sig_src)
        except Exception:
            sig_src = None
    if sig_src and os.path.exists(sig_src):
        media = _find_docx_media(out_path, "image3")
        if media:
            _replace_docx_media(out_path, media, sig_src)

    doc = Document(out_path)
    paras = doc.paragraphs
    cert_no = CERT_NO[level]
    issue_org = ISSUE_ORG_A if level == "甲级" else ISSUE_ORG_B

    # --- 段落1：标题（项目名行 + 报告类型行，宋体14居中，无缩进）---
    p1 = paras[1]
    for r in list(p1.runs):
        r._element.getparent().remove(r._element)
    # 彻底清除段落缩进（模板自带 firstLine=112pt 会导致居中偏移），强制居中
    pPr = p1._element.get_or_add_pPr()
    for ind in pPr.findall(qn('w:ind')):
        pPr.remove(ind)
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.first_line_indent = Pt(0)
    p1.paragraph_format.left_indent = Pt(0)
    p1.paragraph_format.line_spacing = Pt(24)
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(0)
    name_parts = split_name_lines(project_name, 2)
    parts = name_parts + [report_type]
    for i, part in enumerate(parts):
        r = p1.add_run(part)
        set_run_font(r, "宋体", 14)
        if i < len(parts) - 1:  # 行间插入显式换行符（独立 w:br）
            br = OxmlElement('w:br')
            r._element.append(br)

    # --- 段落6/7：发证机关、证书编号 ---
    for pidx, text in ((6, f"发证机关：{issue_org}"), (7, f"证书编号：{cert_no}")):
        p = paras[pidx]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        r = p.add_run(text)
        set_run_font(r, "宋体", 14)

    # 校对人员签名图已在复制模板后直接替换图片内容，位置与尺寸沿用模板，无需删除或重插。

    # --- 删除文档末尾的多余空段落，防止内容被挤出到第 2 页 ---
    body_el = doc.element.body
    for child in reversed(list(body_el)):
        if child.tag == qn('w:p'):
            p_el = child
            has_text = p_el.findall('.//' + qn('w:t'))
            has_draw = p_el.findall('.//' + qn('w:drawing'))
            if not has_text and not has_draw:
                body_el.remove(child)
            else:
                break
        elif child.tag == qn('w:sectPr'):
            continue
        else:
            break
    _fix_all_run_fonts(doc)
    doc.save(out_path)
    return out_path


def build_cert_page(project_name, level, out_path):
    """第三页：资质证书页（加水印；章用证书扫描件自带的章，不再额外贴章）"""
    doc = Document()
    sec = doc.sections[0]
    cert_img = os.path.join(ASSETS_DIR, CERT_FILE[level])
    with Image.open(cert_img) as im:
        cw, ch = im.size
    if level == "甲级":
        # 横向页，边距归零让证书铺满整页（与模板一致）
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width = Emu(int(A4_H * 914400 / 72))
        sec.page_height = Emu(int(A4_W * 914400 / 72))
        sec.left_margin = 0; sec.right_margin = 0
        sec.top_margin = 0; sec.bottom_margin = 0
        avail_w, avail_h = A4_H - 20, A4_W - 20
    else:
        sec.page_width = Emu(int(A4_W * 914400 / 72)); sec.page_height = Emu(int(A4_H * 914400 / 72))
        sec.left_margin = 0; sec.right_margin = 0
        sec.top_margin = 0; sec.bottom_margin = 0
        avail_w, avail_h = A4_W - 20, A4_H - 20
    # 加水印
    wm_text = f"仅限于{project_name}项目使用"
    wm_out = os.path.join(os.path.dirname(out_path), "_wm_cert.png")
    render_watermark(cert_img, wm_text, wm_out)
    # 缩放居中整页（cert_w 单位即 pt，直接传给 add_picture）
    scale = min(avail_w / cw, avail_h / ch)
    cert_w = int(cw * scale)
    table = doc.add_table(rows=1, cols=1)
    table.alignment = 1
    cell = table.cell(0, 0)
    cell.width = Emu(int(A4_W * 914400 / 72))
    cell_para = cell.paragraphs[0]
    cell_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_img = cell_para.add_run()
    run_img.add_picture(wm_out, width=Pt(cert_w))
    doc.save(out_path)
    return out_path


def build_cert_page_pdf(project_name, level, seal_img, out_pdf):
    """第三页：资质证书页 —— 纯 PDF 层生成（彻底绕开 LibreOffice 排版失真）。
    证书图铺满整页 + 公章盖在单位名称文字上（不加水印）。"""
    import fitz
    cert_img = os.path.join(ASSETS_DIR, CERT_FILE[level])
    # 1) 证书图（不加水印，用户要求去除）
    wm_out = cert_img
    # 压缩证书图（原扫描件很大，PNG 插进 PDF 会到数十 MB；压成 JPEG 后体积缩小 20 倍以上）
    comp = os.path.join(os.path.dirname(out_pdf), "_wm_cert_comp.jpg")
    with Image.open(wm_out) as im:
        im = im.convert("RGB")
        maxside = 1600
        if max(im.size) > maxside:
            ratio = maxside / max(im.size)
            im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
        im.save(comp, "JPEG", quality=88)
        cw, ch = im.size
    if level == "甲级":
        pw, ph = A4_H, A4_W          # 横向页
    else:
        pw, ph = A4_W, A4_H          # 竖版页
    # 2) 证书图铺满页面（四周留 7pt）
    scale = min((pw - 14) / cw, (ph - 14) / ch)
    w, h = cw * scale, ch * scale
    x0, y0 = (pw - w) / 2, (ph - h) / 2
    doc = fitz.open()
    page = doc.new_page(width=pw, height=ph)
    page.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h), filename=comp)
    # 3) 公章盖在证书图"单位名称"文字上（传统盖章习惯；乙级章心按渲染像素实测=公司名文字中心）
    seal_d = 110
    if level == "甲级":
        sx, sy = 284 - seal_d / 2, 163 - seal_d / 2
    else:
        sx, sy = 271 - seal_d / 2, 189 - seal_d / 2
    page.insert_image(fitz.Rect(sx, sy, sx + seal_d, sy + seal_d), filename=seal_img)
    doc.save(out_pdf, garbage=4)
    doc.close()
    return out_pdf


def build_three_pages_pdf(project_name, report_type, level, seal_type, out_dir, reviewer="马立亚"):
    """三页生成：封面/署名页由 docx→PDF（版式对齐模板，校对签名在 docx 内替换为所选工程师手写签名），
    资质页由纯 PDF 层生成，合并后再在 PDF 层盖封面公章与署名页公章"""
    cover_docx = os.path.join(out_dir, "p1_封面.docx")
    sig_docx = os.path.join(out_dir, "p2_署名页.docx")
    build_cover_page(project_name, report_type, cover_docx)
    build_signature_page(project_name, report_type, level, sig_docx, reviewer)

    p_cover = docx_to_pdf(cover_docx, out_dir)
    p_sig = docx_to_pdf(sig_docx, out_dir)
    seal_img = os.path.join(ASSETS_DIR, SEAL_FILE[seal_type])
    cert_pdf = os.path.join(out_dir, "p3_资质页.pdf")
    build_cert_page_pdf(project_name, level, seal_img, cert_pdf)

    three_pdf = os.path.join(out_dir, "三页.pdf")
    merge_pdfs([p_cover, p_sig, cert_pdf], three_pdf)

    # PDF 层盖章：封面公章、署名页公章；校对人员手写签名也在此层插入
    apply_stamps_to_pdf(three_pdf, seal_img, CERT_NO[level], level, reviewer=reviewer)
    return three_pdf

def split_name_lines(name, max_lines=2):
    """项目名称拆行：优先在最后一个顿号后断（模板风格：地名列表/工程名两行）；
    若断后第一行过长（>18字符）则回退到最接近中点的顿号断点"""
    if not name:
        return [""]
    if len(name) <= 18:
        return [name]
    # 收集所有顿号后的断点位置
    breaks = []
    for i, ch in enumerate(name):
        if ch in "、，。/·— ":
            pos = i + 1
            if pos < len(name):
                breaks.append(pos)
    if breaks:
        # 优先取最后一个顿号断点；若第一行过长，取使两行最平衡且首行<=18的断点
        last = breaks[-1]
        if len(name[:last]) <= 18:
            return [name[:last], name[last:]]
        best = None
        best_gap = None
        for pos in breaks:
            if len(name[:pos]) > 18:
                continue
            gap = abs(pos - (len(name) - pos))
            if best_gap is None or gap < best_gap:
                best_gap = gap
                best = pos
        if best is not None:
            return [name[:best], name[best:]]
    mid = len(name) // 2
    return [name[:mid], name[mid:]]

def mm_from_pt(pt):
    return pt / MM

# ---------------- 删除原封面 ----------------
def remove_cover(docx_path, out_path):
    """删除 docx 第一个分页符之前的所有段落（封面）"""
    doc = Document(docx_path)
    body = doc.element.body
    to_remove = []
    done = False
    for child in list(body):
        if child.tag == qn('w:p'):
            # 检查是否含分页符
            brs = child.findall('.//' + qn('w:br'))
            has_page = any(b.get(qn('w:type')) == 'page' for b in brs)
            to_remove.append(child)
            if has_page:
                done = True
                break
        elif child.tag == qn('w:tbl'):
            # 封面若含表格，表格前的段落删掉；表格本身保留（谨慎）
            pass
        else:
            break
    for c in to_remove:
        body.remove(c)
    doc.save(out_path)
    return out_path

# ---------------- PDF 转换与合并 ----------------
def docx_to_pdf(docx_path, out_dir):
    """LibreOffice 无头转 PDF"""
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                    "--outdir", out_dir, docx_path],
                   check=True, capture_output=True, timeout=180)
    base = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    return os.path.join(out_dir, base)

def merge_pdfs(pdf_paths, out_path):
    try:
        from pypdf import PdfWriter
    except ImportError:
        from PyPDF2 import PdfWriter
    writer = PdfWriter()
    for p in pdf_paths:
        writer.append(p)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def merge_report_pdf(report_pdf, three_pages_pdf, out_path):
    """把三页 PDF 插到原报告 PDF 最前面，并删除原报告第一页（封面）。
    原 PDF 其余内容字节级保留（不经过任何排版引擎），彻底避免格式错乱。"""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        from PyPDF2 import PdfReader, PdfWriter
    writer = PdfWriter()
    writer.append(three_pages_pdf)
    reader = PdfReader(report_pdf)
    n = len(reader.pages)
    start = 1 if n > 1 else 0   # 删除原 PDF 第一页封面（仅当多于 1 页时）
    writer.append(reader, pages=(start, n))
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


# ---------------- PDF 层盖章 ----------------
def apply_stamps_to_pdf(pdf_path, seal_img, cert_no, level, reviewer="马立亚"):
    """在三页 PDF 的封面/署名页按模板坐标加盖单位公章。
    坐标基于 A4（595x842pt，原点左上角），取自模板 PDF 实测位置。"""
    import fitz
    doc = fitz.open(pdf_path)

    # 第 1 页封面：公章盖在单位名称下方（模板中心约 348,728，直径 100pt）
    doc[0].insert_image(fitz.Rect(294, 674, 394, 774), filename=seal_img)

    # 第 2 页署名页：章盖右侧中部（模板 box 267-384 x 232-347，中心 325,289，直径 117pt）
    doc[1].insert_image(fitz.Rect(266.5, 230.5, 383.5, 347.5), filename=seal_img)

    # 校对人员手写签名已在 build_signature_page 中通过替换模板签字图完成，
    # 位置与尺寸完全沿用模板，此处不再重复插入。

    # 第 3 页资质页：公章与斜向水印已在生成时合成进 PDF（build_cert_page_pdf），此处不再重复

    tmp = pdf_path + ".tmp.pdf"
    doc.save(tmp, garbage=4)
    doc.close()
    os.replace(tmp, pdf_path)
    return pdf_path
