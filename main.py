
from __future__ import annotations

import os
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.textfield import MDTextField
from kivymd.uix.fitimage import FitImage

import arabic_reshaper
from bidi.algorithm import get_display


__version__ = "1.0"


# =========================================================
# مسیرهای برنامه
# =========================================================

RESOURCE_DIR = Path(__file__).resolve().parent
DB_PATH = None
ATTACHMENTS_DIR = None

BANNER_IMAGE_PATH = str(RESOURCE_DIR / "M.png")
TITLE_FONT_PATH = RESOURCE_DIR / "Almas.Font.ttf"
BODY_FONT_PATH = RESOURCE_DIR / "Vazirmatn-Regular.ttf"


# =========================================================
# تنظیمات پنجره فقط برای دسکتاپ
# =========================================================

if platform not in ("android", "ios"):
    try:
        Window.size = (400, 760)
        Window.clearcolor = (0.04, 0.05, 0.07, 1)
    except Exception:
        pass


# =========================================================
# فونت‌ها
# =========================================================

TITLE_FONT = "Roboto"
BODY_FONT = "Roboto"

try:
    if BODY_FONT_PATH.exists():
        LabelBase.register(
            name="Vazirmatn",
            fn_regular=str(BODY_FONT_PATH)
        )

        # Roboto را نیز به فونت فارسی متصل می‌کنیم
        LabelBase.register(
            name="Roboto",
            fn_regular=str(BODY_FONT_PATH)
        )

        BODY_FONT = "Vazirmatn"

        print("BODY FONT LOADED:", BODY_FONT_PATH)

except Exception as e:
    print("BODY FONT LOAD ERROR:", e)


try:
    if TITLE_FONT_PATH.exists():
        LabelBase.register(
            name="Almas",
            fn_regular=str(TITLE_FONT_PATH)
        )

        TITLE_FONT = "Almas"

        print("TITLE FONT LOADED:", TITLE_FONT_PATH)

    else:
        TITLE_FONT = BODY_FONT

except Exception as e:
    print("TITLE FONT LOAD ERROR:", e)
    TITLE_FONT = BODY_FONT


print("ACTIVE TITLE FONT =", TITLE_FONT)
print("ACTIVE BODY FONT  =", BODY_FONT)


# =========================================================
# فارسی / RTL
# =========================================================

def fa(text: str) -> str:
    if text is None:
        return ""

    s = str(text)

    try:
        return get_display(
            arabic_reshaper.reshape(s)
        )
    except Exception:
        return s


# =========================================================
# تبدیل تاریخ میلادی به شمسی
# =========================================================

def gregorian_to_jalali(year, month, day):

    month_days = [
        0, 31, 59, 90, 120, 151,
        181, 212, 243, 273, 304, 334
    ]

    if year > 1600:
        jalali_year = 979
        adjusted_year = year - 1600
    else:
        jalali_year = 0
        adjusted_year = year - 621

    adjusted_year_for_leap = (
        adjusted_year + 1
        if month > 2
        else adjusted_year
    )

    days = (
        365 * adjusted_year
        + (adjusted_year_for_leap + 3) // 4
        - (adjusted_year_for_leap + 99) // 100
        + (adjusted_year_for_leap + 399) // 400
        - 80
        + day
        + month_days[month - 1]
    )

    jalali_year += 33 * (days // 12053)

    days %= 12053

    jalali_year += 4 * (days // 1461)

    days %= 1461

    if days > 365:
        jalali_year += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jalali_month = 1 + days // 31
        jalali_day = 1 + days % 31
    else:
        jalali_month = 7 + (days - 186) // 30
        jalali_day = 1 + (days - 186) % 30

    return jalali_year, jalali_month, jalali_day


# =========================================================
# TextField فارسی
# =========================================================

class FarsiMDTextField(MDTextField):

    raw_text = StringProperty("")
    _is_updating = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.bind(
            raw_text=self._on_raw_text_change
        )

    def _on_raw_text_change(self, instance, value):

        if self._is_updating:
            return

        self._is_updating = True

        shaped = fa(value) if value else ""

        if self.text != shaped:
            self.text = shaped

        self._is_updating = False

    def insert_text(
        self,
        substring,
        from_undo=False
    ):

        if self._is_updating:
            return super().insert_text(
                substring,
                from_undo=from_undo
            )

        self._is_updating = True

        self.raw_text += substring

        shaped = fa(self.raw_text)

        self.text = shaped

        self.cursor = (len(self.text), 0)

        self._is_updating = False

    def do_backspace(
        self,
        from_undo=False,
        mode="bkspc"
    ):

        if self._is_updating:
            return super().do_backspace(
                from_undo=from_undo,
                mode=mode
            )

        if self.raw_text:

            self._is_updating = True

            self.raw_text = self.raw_text[:-1]

            shaped = (
                fa(self.raw_text)
                if self.raw_text
                else ""
            )

            self.text = shaped

            self.cursor = (len(self.text), 0)

            self._is_updating = False


# =========================================================
# KV
# =========================================================

KV = '''
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<NoteCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(16)
    spacing: dp(10)
    radius: [28, 28, 28, 28]
    md_bg_color: 0.09, 0.11, 0.15, 0.96
    elevation: 3
    ripple_behavior: True
    shadow_softness: 8
    shadow_offset: 0, 2

    canvas.before:
        Color:
            rgba: 0.18, 0.24, 0.34, 0.18
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [28, 28, 28, 28]

    MDBoxLayout:
        adaptive_height: True
        spacing: dp(8)

        MDIcon:
            icon: "notebook-outline"
            theme_text_color: "Custom"
            text_color: 0.43, 0.74, 1, 1
            size_hint_x: None
            width: dp(28)

        MDLabel:
            text: root.title if root.title else app.fa("بدون عنوان")
            halign: "right"
            bold: True
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            font_name: app.title_font_name
            font_style: "Subtitle1"
            font_size: sp(16)
            shorten: True
            shorten_from: "left"

    MDLabel:
        text: root.preview
        halign: "right"
        theme_text_color: "Custom"
        text_color: 0.84, 0.86, 0.91, 1
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
        font_name: app.body_font_name
        font_style: "Body1"
        font_size: sp(14)

    MDLabel:
        text: root.keywords_text
        halign: "right"
        theme_text_color: "Custom"
        text_color: 0.55, 0.82, 1, 1
        size_hint_y: None
        height: self.texture_size[1]
        font_name: app.body_font_name
        font_size: sp(12)

    MDBoxLayout:
        adaptive_height: True
        spacing: dp(6)
        padding: 0, dp(4), 0, 0

        MDLabel:
            text: root.date_text
            halign: "right"
            theme_text_color: "Custom"
            text_color: 0.62, 0.66, 0.74, 1
            font_name: app.body_font_name
            font_size: sp(11)

        Widget:

        MDIconButton:
            icon: "paperclip"
            theme_icon_color: "Custom"
            icon_color: 0.7, 0.83, 1, 1
            on_release: app.show_attachments(root.note_id)

        MDIconButton:
            icon: "pencil-outline"
            theme_icon_color: "Custom"
            icon_color: 0.5, 0.9, 0.75, 1
            on_release: app.open_note_editor(root.note_id)

        MDIconButton:
            icon: "delete-outline"
            theme_icon_color: "Custom"
            icon_color: 1, 0.5, 0.5, 1
            on_release: app.confirm_delete_note(root.note_id)


<HomeScreen>:
    name: "home"

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        md_bg_color: 0.04, 0.05, 0.07, 1

        MDFloatLayout:
            size_hint_y: None
            height: dp(290)

            FitImage:
                source: app.banner_image if app.banner_exists else ""
                size_hint: 1, 1
                pos_hint: {"x": 0, "y": 0}
                radius: [0, 0, 34, 34]
                opacity: 1 if app.banner_exists else 0
                allow_stretch: True
                keep_ratio: False

            MDCard:
                size_hint: 1, 1
                pos_hint: {"x": 0, "y": 0}
                radius: [0, 0, 34, 34]
                elevation: 0
                md_bg_color: 0.02, 0.04, 0.08, 0.50

            MDBoxLayout:
                orientation: "vertical"
                size_hint: 1, 1
                pos_hint: {"x": 0, "y": 0}
                padding: dp(18), dp(18), dp(18), dp(18)
                spacing: dp(12)

                Widget:
                    size_hint_y: None
                    height: dp(12)

                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(8)

                    Widget:

                    MDLabel:
                        text: app.fa(" الجامع المرتضی")
                        halign: "right"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        font_name: app.title_font_name
                        font_style: "Subtitle1"
                        font_size: sp(24)

                MDLabel:
                    text: app.fa("یادداشت‌هایت را سریع، مرتب و زیبا ذخیره کن")
                    halign: "right"
                    theme_text_color: "Custom"
                    text_color: 0.90, 0.92, 0.97, 1
                    font_name: app.body_font_name
                    font_size: sp(13)
                    size_hint_y: None
                    height: self.texture_size[1]

                Widget:

                FarsiMDTextField:
                    id: search_field
                    hint_text: app.fa("جستجو در عنوان، متن و کلیدواژه...")
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(58)
                    padding: dp(12), 0
                    font_name: app.body_font_name
                    halign: "right"
                    line_color_focus: 0.30, 0.64, 1, 1
                    text_color_normal: 1, 1, 1, 1
                    text_color_focus: 1, 1, 1, 1
                    hint_text_color_normal: 0.85, 0.87, 0.92, 1
                    md_bg_color: 0.08, 0.10, 0.14, 0.75
                    on_raw_text: app.refresh_notes(self.raw_text)

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                id: notes_container
                orientation: "vertical"
                adaptive_height: True
                spacing: dp(12)
                padding: dp(12), dp(6), dp(12), dp(92)

        MDFloatingActionButton:
            icon: "plus"
            pos_hint: {"right": 0.95}
            y: dp(18)
            md_bg_color: 0.22, 0.58, 1, 1
            elevation_normal: 8
            on_release: app.open_note_editor()


<ViewerScreen>:
    name: "viewer"

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        md_bg_color: 0.04, 0.05, 0.07, 1

        MDCard:
            orientation: "vertical"
            size_hint_y: None
            height: dp(94)
            radius: [0, 0, 28, 28]
            padding: dp(12)
            elevation: 0
            md_bg_color: 0.07, 0.09, 0.13, 1

            canvas.before:
                Color:
                    rgba: 0.10, 0.15, 0.24, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 28, 28]

            MDBoxLayout:
                adaptive_height: True

                MDIconButton:
                    icon: "arrow-right"
                    theme_icon_color: "Custom"
                    icon_color: 0.75, 0.84, 1, 1
                    on_release: app.go_home()

                MDLabel:
                    id: viewer_title
                    text: app.fa("مشاهده یادداشت")
                    halign: "right"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    font_name: app.title_font_name
                    font_style: "Subtitle1"
                    font_size: sp(20)

                MDIconButton:
                    icon: "pencil-outline"
                    theme_icon_color: "Custom"
                    icon_color: 0.45, 0.95, 0.72, 1
                    on_release: app.open_note_editor(app.viewer_note_id)

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                spacing: dp(12)
                padding: dp(12), dp(4), dp(12), dp(40)

                MDCard:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16)
                    radius: [24, 24, 24, 24]
                    md_bg_color: 0.09, 0.11, 0.15, 1
                    elevation: 2

                    MDLabel:
                        id: viewer_note_title
                        text: ""
                        halign: "right"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        font_name: app.title_font_name
                        font_size: sp(20)
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(8)

                    MDLabel:
                        id: viewer_date
                        text: ""
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.62, 0.66, 0.74, 1
                        font_name: app.body_font_name
                        font_size: sp(12)
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(8)

                    MDLabel:
                        id: viewer_keywords
                        text: ""
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.55, 0.82, 1, 1
                        font_name: app.body_font_name
                        font_size: sp(13)
                        size_hint_y: None
                        height: self.texture_size[1]

                MDCard:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16)
                    radius: [24, 24, 24, 24]
                    md_bg_color: 0.10, 0.12, 0.17, 1
                    elevation: 2

                    MDLabel:
                        text: app.fa("متن کامل یادداشت")
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.88, 0.92, 1, 1
                        bold: True
                        font_name: app.title_font_name
                        font_size: sp(14)
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(10)

                    MDLabel:
                        id: viewer_content
                        text: ""
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.90, 0.92, 0.96, 1
                        font_name: app.body_font_name
                        font_size: sp(15)
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]


<EditorScreen>:
    name: "editor"

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        md_bg_color: 0.04, 0.05, 0.07, 1

        MDCard:
            orientation: "vertical"
            size_hint_y: None
            height: dp(94)
            radius: [0, 0, 28, 28]
            padding: dp(12)
            elevation: 0
            md_bg_color: 0.07, 0.09, 0.13, 1

            canvas.before:
                Color:
                    rgba: 0.10, 0.15, 0.24, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [0, 0, 28, 28]

            MDBoxLayout:
                adaptive_height: True

                MDIconButton:
                    icon: "arrow-right"
                    theme_icon_color: "Custom"
                    icon_color: 0.75, 0.84, 1, 1
                    on_release: app.go_home()

                MDLabel:
                    id: editor_title
                    text: app.fa("یادداشت جدید")
                    halign: "right"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    font_name: app.title_font_name
                    font_style: "Subtitle1"
                    font_size: sp(20)

                MDIconButton:
                    icon: "content-save-outline"
                    theme_icon_color: "Custom"
                    icon_color: 0.45, 0.95, 0.72, 1
                    on_release: app.save_current_note()

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                spacing: dp(12)
                padding: dp(12), dp(4), dp(12), dp(100)

                MDCard:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16)
                    radius: [24, 24, 24, 24]
                    md_bg_color: 0.09, 0.11, 0.15, 1
                    elevation: 2

                    MDLabel:
                        text: app.fa("اطلاعات یادداشت")
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.84, 0.90, 1, 1
                        font_name: app.title_font_name
                        font_size: sp(14)
                        bold: True
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(8)

                    FarsiMDTextField:
                        id: title_input
                        hint_text: app.fa("عنوان یادداشت")
                        mode: "fill"
                        multiline: False
                        halign: "right"
                        font_name: app.body_font_name
                        line_color_focus: 0.30, 0.64, 1, 1

                    Widget:
                        size_hint_y: None
                        height: dp(10)

                    FarsiMDTextField:
                        id: keywords_input
                        hint_text: app.fa("کلیدواژه‌ها را با ویرگول جدا کنید")
                        mode: "rectangle"
                        multiline: False
                        halign: "right"
                        font_name: app.body_font_name
                        line_color_focus: 0.30, 0.64, 1, 1

                MDCard:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16)
                    radius: [24, 24, 24, 24]
                    md_bg_color: 0.10, 0.12, 0.17, 1
                    elevation: 2

                    MDLabel:
                        text: app.fa("متن یادداشت")
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color: 0.88, 0.92, 1, 1
                        bold: True
                        font_name: app.title_font_name
                        font_size: sp(14)
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(10)

                    FarsiMDTextField:
                        id: content_input
                        hint_text: app.fa("اینجا بنویس...")
                        mode: "rectangle"
                        multiline: True
                        halign: "right"
                        font_name: app.body_font_name
                        line_color_focus: 0.30, 0.64, 1, 1

                MDCard:
                    orientation: "vertical"
                    adaptive_height: True
                    padding: dp(16)
                    radius: [24, 24, 24, 24]
                    md_bg_color: 0.09, 0.11, 0.15, 1
                    elevation: 2

                    MDBoxLayout:
                        adaptive_height: True

                        MDLabel:
                            text: app.fa("فایل‌های ضمیمه")
                            halign: "right"
                            theme_text_color: "Custom"
                            text_color: 0.88, 0.92, 1, 1
                            bold: True
                            font_name: app.title_font_name
                            font_size: sp(14)

                        Widget:

                        MDRaisedButton:
                            text: app.fa("افزودن فایل")
                            font_name: app.body_font_name
                            md_bg_color: 0.21, 0.58, 1, 1
                            on_release: app.open_file_manager()

                    Widget:
                        size_hint_y: None
                        height: dp(8)

                    MDBoxLayout:
                        id: attachments_container
                        orientation: "vertical"
                        adaptive_height: True
                        spacing: dp(8)
'''


# =========================================================
# Database
# =========================================================

class Database:

    def __init__(self, db_path: Path):

        self.db_path = db_path

        self._ensure()

    def connect(self):

        conn = sqlite3.connect(
            str(self.db_path)
        )

        conn.row_factory = sqlite3.Row

        return conn

    def _ensure(self):

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.connect() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    attachments TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    def create_note(
        self,
        title,
        content,
        keywords,
        attachments
    ):

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.connect() as conn:

            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO notes
                (
                    title,
                    content,
                    keywords,
                    attachments,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    content,
                    json.dumps(
                        keywords,
                        ensure_ascii=False
                    ),
                    json.dumps(
                        attachments,
                        ensure_ascii=False
                    ),
                    now,
                    now
                )
            )

            conn.commit()

            return cur.lastrowid

    def update_note(
        self,
        note_id,
        title,
        content,
        keywords,
        attachments
    ):

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.connect() as conn:

            conn.execute(
                """
                UPDATE notes
                SET
                    title=?,
                    content=?,
                    keywords=?,
                    attachments=?,
                    updated_at=?
                WHERE id=?
                """,
                (
                    title,
                    content,
                    json.dumps(
                        keywords,
                        ensure_ascii=False
                    ),
                    json.dumps(
                        attachments,
                        ensure_ascii=False
                    ),
                    now,
                    note_id
                )
            )

            conn.commit()

    def delete_note(self, note_id):

        with self.connect() as conn:

            conn.execute(
                "DELETE FROM notes WHERE id=?",
                (note_id,)
            )

            conn.commit()

    def get_note(self, note_id):

        with self.connect() as conn:

            row = conn.execute(
                "SELECT * FROM notes WHERE id=?",
                (note_id,)
            ).fetchone()

            return dict(row) if row else None

    def search_notes(self, query=""):

        q = (
            query or ""
        ).strip().lower()

        with self.connect() as conn:

            rows = conn.execute(
                """
                SELECT *
                FROM notes
                ORDER BY updated_at DESC
                """
            ).fetchall()

        results = []

        for row in rows:

            item = dict(row)

            try:
                item["keywords"] = json.loads(
                    item["keywords"] or "[]"
                )
            except Exception:
                item["keywords"] = []

            try:
                item["attachments"] = json.loads(
                    item["attachments"] or "[]"
                )
            except Exception:
                item["attachments"] = []

            if not q:

                results.append(item)

                continue

            searchable = " ".join(
                [
                    item["title"],
                    item["content"],
                    " ".join(item["keywords"]),
                ]
            ).lower()

            if q in searchable:

                results.append(item)

        return results


# =========================================================
# Widgets
# =========================================================

class NoteCard(MDCard):

    note_id = NumericProperty(0)

    title = StringProperty("")

    preview = StringProperty("")

    keywords_text = StringProperty("")

    date_text = StringProperty("")


class HomeScreen(MDScreen):
    pass


class ViewerScreen(MDScreen):
    pass


class EditorScreen(MDScreen):
    pass


# =========================================================
# Application
# =========================================================

class NotesApp(MDApp):

    viewer_note_id = None

    def fa(self, text: str) -> str:

        return fa(text)

    def build(self):

        global DB_PATH
        global ATTACHMENTS_DIR

        # ---------------------------------------------
        # مسیر قابل نوشتن برنامه
        # ---------------------------------------------

        self.app_data_dir = Path(
            self.user_data_dir
        )

        self.app_data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        DB_PATH = (
            self.app_data_dir
            / "notes_app.db"
        )

        ATTACHMENTS_DIR = (
            self.app_data_dir
            / "attachments"
        )

        ATTACHMENTS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # ---------------------------------------------
        # Database
        # ---------------------------------------------

        self.db = Database(DB_PATH)

        self.current_note_id = None

        self.current_attachments = []

        self.dialog = None

        self.title_font_name = TITLE_FONT

        self.body_font_name = BODY_FONT

        self.banner_image = BANNER_IMAGE_PATH

        self.banner_exists = Path(
            self.banner_image
        ).exists()

        print(
            "APP DATA DIR:",
            self.app_data_dir
        )

        print(
            "DATABASE:",
            DB_PATH
        )

        print(
            "ATTACHMENTS:",
            ATTACHMENTS_DIR
        )

        print(
            "BANNER:",
            self.banner_image
        )

        # ---------------------------------------------
        # Theme
        # ---------------------------------------------

        self.theme_cls.theme_style = "Dark"

        self.theme_cls.primary_palette = "Blue"

        self.theme_cls.accent_palette = "LightBlue"

        try:

            self.theme_cls.font_styles[
                "Subtitle1"
            ] = [
                self.title_font_name,
                sp(16),
                False,
                0.15
            ]

            self.theme_cls.font_styles[
                "Body1"
            ] = [
                self.body_font_name,
                sp(14),
                False,
                0.15
            ]

            self.theme_cls.font_styles[
                "Button"
            ] = [
                self.body_font_name,
                sp(14),
                True,
                0.15
            ]

        except Exception as e:

            print(
                "FONT STYLE SET ERROR:",
                e
            )

        # ---------------------------------------------
        # KV
        # ---------------------------------------------

        Builder.load_string(KV)

        from kivymd.uix.screenmanager import MDScreenManager

        self.sm = MDScreenManager()

        self.home_screen = HomeScreen()

        self.viewer_screen = ViewerScreen()

        self.editor_screen = EditorScreen()

        self.sm.add_widget(
            self.home_screen
        )

        self.sm.add_widget(
            self.viewer_screen
        )

        self.sm.add_widget(
            self.editor_screen
        )

        # ---------------------------------------------
        # Android / Desktop file picker
        # ---------------------------------------------

        self.file_manager = None

        if platform not in ("android", "ios"):

            try:

                from kivymd.uix.filemanager import MDFileManager

                self.file_manager = MDFileManager(
                    exit_manager=self.close_file_manager,
                    select_path=self.select_path,
                    preview=True,
                )

            except Exception as e:

                print(
                    "DESKTOP FILE MANAGER ERROR:",
                    e
                )

        # ---------------------------------------------
        # Startup
        # ---------------------------------------------

        Clock.schedule_once(
            lambda dt: self.refresh_notes(""),
            0.2
        )

        Clock.schedule_once(
            lambda dt: self.apply_font_fixes(),
            0.2
        )

        return self.sm

    # =================================================
    # Fonts
    # =================================================

    def apply_font_fixes(self):

        try:

            self.home_screen.ids.search_field.font_name = (
                self.body_font_name
            )

        except Exception:
            pass

        try:

            self.editor_screen.ids.title_input.font_name = (
                self.body_font_name
            )

            self.editor_screen.ids.keywords_input.font_name = (
                self.body_font_name
            )

            self.editor_screen.ids.content_input.font_name = (
                self.body_font_name
            )

        except Exception:
            pass

    # =================================================
    # Messages
    # =================================================

    def show_message(self, text):

        try:

            Snackbar(
                text=self.fa(text),
                duration=2
            ).open()

        except Exception:

            print(text)

    # =================================================
    # Date
    # =================================================

    def format_date(self, iso_text):

        try:

            dt = datetime.fromisoformat(
                iso_text
            )

            year, month, day = (
                gregorian_to_jalali(
                    dt.year,
                    dt.month,
                    dt.day
                )
            )

            return (
                f"{year:04d}/"
                f"{month:02d}/"
                f"{day:02d} - "
                f"{dt:%H:%M}"
            )

        except Exception:

            return iso_text

    # =================================================
    # Keywords
    # =================================================

    def clean_keywords(self, raw_text):

        parts = [
            x.strip()
            for x in raw_text
            .replace("،", ",")
            .split(",")
        ]

        return [
            p for p in parts if p
        ]

    # =================================================
    # Refresh notes
    # =================================================

    def refresh_notes(self, query=""):

        container = (
            self.home_screen
            .ids
            .notes_container
        )

        container.clear_widgets()

        notes = self.db.search_notes(
            query
        )

        if not notes:

            lbl = MDLabel(
                text=self.fa(
                    "یادداشتی پیدا نشد"
                ),
                halign="center",
                size_hint_y=None,
                height=dp(80),
                font_name=self.body_font_name,
                font_size=sp(14),
                theme_text_color="Custom",
                text_color=(
                    0.82,
                    0.86,
                    0.94,
                    1
                ),
            )

            container.add_widget(lbl)

            return

        for note in notes:

            preview = (
                note["content"][:140]
                + (
                    "..."
                    if len(note["content"]) > 140
                    else ""
                )
            )

            keywords_text = (
                " | ".join(note["keywords"])
                if note["keywords"]
                else
                "بدون کلیدواژه"
            )

            card = NoteCard(
                note_id=note["id"],
                title=self.fa(
                    note["title"]
                ),
                preview=self.fa(
                    preview
                ),
                keywords_text=self.fa(
                    keywords_text
                ),
                date_text=self.fa(
                    "آخرین ویرایش: "
                    + self.format_date(
                        note["updated_at"]
                    )
                ),
            )

            card.bind(
                on_release=lambda instance,
                nid=note["id"]:
                self.open_note_viewer(nid)
            )

            container.add_widget(card)

            card.opacity = 0

            Animation(
                opacity=1,
                d=0.18
            ).start(card)

    # =================================================
    # Home
    # =================================================

    def go_home(self):

        self.sm.current = "home"

        self.refresh_notes(
            self.home_screen
            .ids
            .search_field
            .raw_text
        )

    # =================================================
    # Viewer
    # =================================================

    def open_note_viewer(self, note_id):

        note = self.db.get_note(
            note_id
        )

        if not note:

            self.show_message(
                "یادداشت پیدا نشد"
            )

            return

        try:

            kws = json.loads(
                note["keywords"] or "[]"
            )

        except Exception:

            kws = []

        self.viewer_note_id = note_id

        self.viewer_screen.ids.viewer_title.text = (
            self.fa("مشاهده یادداشت")
        )

        self.viewer_screen.ids.viewer_note_title.text = (
            self.fa(
                note["title"]
                or
                "بدون عنوان"
            )
        )

        self.viewer_screen.ids.viewer_date.text = (
            self.fa(
                "آخرین ویرایش: "
                + self.format_date(
                    note["updated_at"]
                )
            )
        )

        self.viewer_screen.ids.viewer_keywords.text = (
            self.fa(
                (
                    "کلیدواژه‌ها: "
                    + " | ".join(kws)
                )
                if kws
                else
                "کلیدواژه‌ای ثبت نشده"
            )
        )

        self.viewer_screen.ids.viewer_content.text = (
            self.fa(
                note["content"]
                or ""
            )
        )

        self.sm.current = "viewer"

    # =================================================
    # Editor
    # =================================================

    def open_note_editor(
        self,
        note_id=None
    ):

        self.current_note_id = note_id

        self.current_attachments = []

        self.editor_screen.ids.title_input.raw_text = ""

        self.editor_screen.ids.keywords_input.raw_text = ""

        self.editor_screen.ids.content_input.raw_text = ""

        self.editor_screen.ids.attachments_container.clear_widgets()

        if note_id is None:

            self.editor_screen.ids.editor_title.text = (
                self.fa("یادداشت جدید")
            )

            self.render_attachments()

        else:

            note = self.db.get_note(
                note_id
            )

            if note:

                self.editor_screen.ids.editor_title.text = (
                    self.fa("ویرایش یادداشت")
                )

                self.editor_screen.ids.title_input.raw_text = (
                    note["title"]
                )

                self.editor_screen.ids.content_input.raw_text = (
                    note["content"]
                )

                try:

                    kws = json.loads(
                        note["keywords"]
                        or "[]"
                    )

                except Exception:

                    kws = []

                try:

                    atts = json.loads(
                        note["attachments"]
                        or "[]"
                    )

                except Exception:

                    atts = []

                self.editor_screen.ids.keywords_input.raw_text = (
                    "، ".join(kws)
                )

                self.current_attachments = atts

                self.render_attachments()

        self.sm.current = "editor"

    # =================================================
    # Save
    # =================================================

    def save_current_note(self):

        title = (
            self.editor_screen
            .ids
            .title_input
            .raw_text
            .strip()
        )

        content = (
            self.editor_screen
            .ids
            .content_input
            .raw_text
            .strip()
        )

        keywords = self.clean_keywords(
            self.editor_screen
            .ids
            .keywords_input
            .raw_text
            .strip()
        )

        if not title:

            self.show_message(
                "عنوان را وارد کنید"
            )

            return

        if not content:

            self.show_message(
                "متن یادداشت را وارد کنید"
            )

            return

        if self.current_note_id is None:

            self.db.create_note(
                title,
                content,
                keywords,
                self.current_attachments
            )

            self.show_message(
                "یادداشت ذخیره شد"
            )

        else:

            self.db.update_note(
                self.current_note_id,
                title,
                content,
                keywords,
                self.current_attachments
            )

            self.show_message(
                "یادداشت ویرایش شد"
            )

        self.go_home()

    # =================================================
    # Delete dialog
    # =================================================

    def confirm_delete_note(
        self,
        note_id
    ):

        self.dialog = MDDialog(
            title=self.fa(
                "حذف یادداشت"
            ),
            text=self.fa(
                "آیا مطمئن هستید؟"
            ),
            buttons=[
                MDFlatButton(
                    text=self.fa(
                        "انصراف"
                    ),
                    font_name=self.body_font_name,
                    on_release=lambda x:
                    self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text=self.fa(
                        "حذف"
                    ),
                    font_name=self.body_font_name,
                    md_bg_color=(
                        0.9,
                        0.25,
                        0.25,
                        1
                    ),
                    on_release=lambda x:
                    self.delete_note_and_close(
                        note_id
                    )
                ),
            ],
        )

        self.dialog.open()

    def delete_note_and_close(
        self,
        note_id
    ):

        if self.dialog:

            self.dialog.dismiss()

        self.db.delete_note(
            note_id
        )

        self.refresh_notes(
            self.home_screen
            .ids
            .search_field
            .raw_text
        )

        self.show_message(
            "حذف شد"
        )

    # =================================================
    # File picker
    # =================================================

    def open_file_manager(self):

        # ---------------------------------------------
        # Android
        # ---------------------------------------------

        if platform == "android":

            try:

                from plyer import filechooser

                filechooser.open_file(
                    on_selection=self.android_file_selected
                )

                return

            except Exception as e:

                print(
                    "ANDROID FILE PICKER ERROR:",
                    e
                )

                self.show_message(
                    "باز کردن انتخاب فایل ممکن نیست"
                )

                return

        # ---------------------------------------------
        # Desktop
        # ---------------------------------------------

        if self.file_manager:

            try:

                self.file_manager.show(
                    str(Path.home())
                )

            except Exception as e:

                print(
                    "FILE MANAGER ERROR:",
                    e
                )

                self.show_message(
                    "باز کردن فایل ممکن نیست"
                )

    # =================================================
    # Android selected file
    # =================================================

    def android_file_selected(
        self,
        selection
    ):

        if not selection:

            return

        try:

            path = selection[0]

        except Exception:

            return

        self.copy_attachment(
            path
        )

    # =================================================
    # Desktop selected file
    # =================================================

    def close_file_manager(
        self,
        *args
    ):

        if self.file_manager:

            try:

                self.file_manager.close()

            except Exception:
                pass

    def select_path(
        self,
        path
    ):

        self.close_file_manager()

        self.copy_attachment(
            path
        )

    # =================================================
    # Copy attachment
    # =================================================

    def copy_attachment(
        self,
        path
    ):

        try:

            p = Path(path)

            if (
                not p.exists()
                or
                not p.is_file()
            ):

                self.show_message(
                    "فایل معتبر نیست"
                )

                return

        except Exception:

            self.show_message(
                "فایل معتبر نیست"
            )

            return

        try:

            target = (
                ATTACHMENTS_DIR
                /
                p.name
            )

            counter = 1

            while target.exists():

                target = (
                    ATTACHMENTS_DIR
                    /
                    f"{p.stem}_{counter}{p.suffix}"
                )

                counter += 1

            shutil.copy2(
                str(p),
                str(target)
            )

            saved = str(
                target.resolve()
            )

            if (
                saved
                not in
                self.current_attachments
            ):

                self.current_attachments.append(
                    saved
                )

            self.render_attachments()

            self.show_message(
                "فایل افزوده شد"
            )

        except Exception as e:

            print(
                "COPY ATTACHMENT ERROR:",
                e
            )

            self.show_message(
                "خطا در کپی فایل"
            )

    # =================================================
    # Render attachments
    # =================================================

    def render_attachments(self):

        container = (
            self.editor_screen
            .ids
            .attachments_container
        )

        container.clear_widgets()

        if not self.current_attachments:

            container.add_widget(
                MDLabel(
                    text=self.fa(
                        "هنوز فایلی اضافه نشده است"
                    ),
                    halign="right",
                    size_hint_y=None,
                    height=dp(36),
                    font_name=self.body_font_name,
                    font_size=sp(13),
                    theme_text_color="Custom",
                    text_color=(
                        0.84,
                        0.87,
                        0.94,
                        1
                    ),
                )
            )

            return

        for path in self.current_attachments:

            item = OneLineAvatarIconListItem(
                text=self.fa(
                    os.path.basename(path)
                )
            )

            try:

                item.font_name = (
                    self.body_font_name
                )

            except Exception:
                pass

            icon = IconLeftWidget(
                icon="file-outline"
            )

            item.add_widget(
                icon
            )

            delete_btn = MDIconButton(
                icon="delete-outline",
                theme_icon_color="Custom",
                icon_color=(
                    1,
                    0.45,
                    0.45,
                    1
                ),
                on_release=lambda x,
                p=path:
                self.remove_attachment(p)
            )

            item.add_widget(
                delete_btn
            )

            container.add_widget(
                item
            )

    # =================================================
    # Remove attachment
    # =================================================

    def remove_attachment(
        self,
        path
    ):

        self.current_attachments = [
            p
            for p in self.current_attachments
            if p != path
        ]

        self.render_attachments()

        self.show_message(
            "فایل حذف شد"
        )

    # =================================================
    # Show attachments
    # =================================================

    def show_attachments(
        self,
        note_id
    ):

        note = self.db.get_note(
            note_id
        )

        if not note:

            self.show_message(
                "یادداشت پیدا نشد"
            )

            return

        try:

            attachments = json.loads(
                note["attachments"]
                or "[]"
            )

        except Exception:

            attachments = []

        if not attachments:

            self.show_message(
                "ضمیمه‌ای وجود ندارد"
            )

            return

        text = "\\n".join(
            f"• {Path(p).name}"
            for p in attachments
        )

        self.dialog = MDDialog(
            title=self.fa(
                "فایل‌های ضمیمه"
            ),
            text=self.fa(
                text
            ),
            buttons=[
                MDFlatButton(
                    text=self.fa(
                        "بستن"
                    ),
                    font_name=self.body_font_name,
                    on_release=lambda x:
                    self.dialog.dismiss()
                )
            ]
        )

        self.dialog.open()


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":
    NotesApp().run()

