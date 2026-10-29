"""Print-ready, single-page PDF reports for StatX Analytics matches."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections.abc import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


NAVY = colors.HexColor("#111827")
PITCH_GREEN = colors.HexColor("#0F2D1A")
ACCENT = colors.HexColor("#4ADE80")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
WHITE = colors.white


@dataclass(frozen=True)
class ReportTeamMetrics:
    """Team-level metrics displayed in the report header."""

    name: str
    score: int
    total_xg: float
    possession: float
    shots_on_target: int


@dataclass(frozen=True)
class MatchReportData:
    """All textual and numerical data required by the report."""

    match_id: int
    match_date: datetime
    competition: str
    home: ReportTeamMetrics
    away: ReportTeamMetrics
    key_player_name: str
    tactical_insights: Sequence[str]


@dataclass(frozen=True)
class ReportVisuals:
    """Paths to the three analytics images embedded in the PDF."""

    shot_map: Path
    pass_map: Path
    heatmap: Path


class MatchReportGenerator:
    """Generate a polished one-page A4 portrait match report."""

    def __init__(self, export_root: Path | str) -> None:
        self.export_root = Path(export_root).expanduser().resolve()

    def generate(self, data: MatchReportData, visuals: ReportVisuals) -> Path:
        """Build and save the report, returning its absolute path."""
        self._validate_visuals(visuals)
        self.export_root.mkdir(parents=True, exist_ok=True)
        output_path = self.export_root / f"match_{data.match_id}_report.pdf"

        document = canvas.Canvas(str(output_path), pagesize=A4, pageCompression=1)
        document.setTitle(f"StatX Analytics - Match {data.match_id}")
        document.setAuthor("StatX Analytics")
        self._draw_page(document, data, visuals)
        document.showPage()
        document.save()

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError("The PDF report could not be created")
        return output_path

    @staticmethod
    def _validate_visuals(visuals: ReportVisuals) -> None:
        missing = [
            path.name
            for path in (visuals.shot_map, visuals.pass_map, visuals.heatmap)
            if not path.is_file() or path.stat().st_size == 0
        ]
        if missing:
            raise FileNotFoundError(
                f"Analytics visuals are missing or empty: {', '.join(missing)}"
            )

    def _draw_page(
        self,
        document: canvas.Canvas,
        data: MatchReportData,
        visuals: ReportVisuals,
    ) -> None:
        width, height = A4
        margin = 28

        document.setFillColor(WHITE)
        document.rect(0, 0, width, height, fill=1, stroke=0)
        self._draw_header(document, data, width, height)
        self._draw_metrics(document, data, margin, width)
        self._draw_visuals(document, data, visuals, margin, width)
        self._draw_tactical_section(document, data.tactical_insights, margin, width)

    def _draw_header(
        self,
        document: canvas.Canvas,
        data: MatchReportData,
        width: float,
        height: float,
    ) -> None:
        header_height = 142
        y = height - header_height
        document.setFillColor(NAVY)
        document.rect(0, y, width, header_height, fill=1, stroke=0)
        document.setFillColor(ACCENT)
        document.rect(0, y, width, 5, fill=1, stroke=0)

        document.setFillColor(PITCH_GREEN)
        document.circle(47, height - 37, 17, fill=1, stroke=0)
        document.setStrokeColor(ACCENT)
        document.setLineWidth(1.5)
        document.circle(47, height - 37, 13, fill=0, stroke=1)
        document.setFillColor(ACCENT)
        document.setFont("Helvetica-Bold", 10)
        document.drawCentredString(47, height - 40.5, "SX")

        document.setFillColor(WHITE)
        document.setFont("Helvetica-Bold", 16)
        document.drawString(72, height - 41, "StatX Analytics")
        document.setFillColor(colors.HexColor("#CBD5E1"))
        document.setFont("Helvetica", 7.5)
        document.drawRightString(
            width - 28,
            height - 33,
            data.competition.upper(),
        )
        document.drawRightString(
            width - 28,
            height - 45,
            data.match_date.strftime("%d/%m/%Y - %H:%M"),
        )

        home_x = 155
        away_x = width - 155
        self._draw_fitted_centered_text(
            document, data.home.name, home_x, height - 89, 140, 14, WHITE
        )
        self._draw_fitted_centered_text(
            document, data.away.name, away_x, height - 89, 140, 14, WHITE
        )

        document.setFillColor(ACCENT)
        document.setFont("Helvetica-Bold", 28)
        document.drawCentredString(
            width / 2,
            height - 99,
            f"{data.home.score}  -  {data.away.score}",
        )
        document.setFillColor(colors.HexColor("#94A3B8"))
        document.setFont("Helvetica-Bold", 7)
        document.drawCentredString(width / 2, height - 116, "SCORE FINAL")

    def _draw_metrics(
        self,
        document: canvas.Canvas,
        data: MatchReportData,
        margin: float,
        width: float,
    ) -> None:
        y = 630
        gap = 8
        card_width = (width - 2 * margin - 2 * gap) / 3
        metrics = (
            ("EXPECTED GOALS", f"{data.home.total_xg:.2f}", f"{data.away.total_xg:.2f}"),
            ("POSSESSION", f"{data.home.possession:.1f}%", f"{data.away.possession:.1f}%"),
            ("TIRS CADRES", str(data.home.shots_on_target), str(data.away.shots_on_target)),
        )
        for index, (label, home_value, away_value) in enumerate(metrics):
            x = margin + index * (card_width + gap)
            document.setFillColor(LIGHT)
            document.roundRect(x, y, card_width, 54, 7, fill=1, stroke=0)
            document.setFillColor(MUTED)
            document.setFont("Helvetica-Bold", 6.5)
            document.drawCentredString(x + card_width / 2, y + 38, label)
            document.setFillColor(PITCH_GREEN)
            document.setFont("Helvetica-Bold", 16)
            document.drawRightString(x + card_width / 2 - 8, y + 14, home_value)
            document.setFillColor(MUTED)
            document.setFont("Helvetica-Bold", 9)
            document.drawCentredString(x + card_width / 2, y + 17, "vs")
            document.setFillColor(NAVY)
            document.setFont("Helvetica-Bold", 16)
            document.drawString(x + card_width / 2 + 8, y + 14, away_value)

    def _draw_visuals(
        self,
        document: canvas.Canvas,
        data: MatchReportData,
        visuals: ReportVisuals,
        margin: float,
        width: float,
    ) -> None:
        document.setFillColor(NAVY)
        document.setFont("Helvetica-Bold", 10)
        document.drawString(margin, 610, "LECTURE VISUELLE DU MATCH")
        document.setStrokeColor(ACCENT)
        document.setLineWidth(2)
        document.line(margin, 605, margin + 54, 605)

        main_width = 360
        secondary_width = width - 2 * margin - main_width - 8
        image_y = 333
        main_height = 264
        secondary_height = 128

        self._draw_image_panel(
            document,
            visuals.shot_map,
            margin,
            image_y,
            main_width,
            main_height,
            "CARTE DES TIRS - MATCH",
        )
        secondary_x = margin + main_width + 8
        self._draw_image_panel(
            document,
            visuals.pass_map,
            secondary_x,
            image_y + secondary_height + 8,
            secondary_width,
            secondary_height,
            f"PASSES - {data.home.name}",
        )
        self._draw_image_panel(
            document,
            visuals.heatmap,
            secondary_x,
            image_y,
            secondary_width,
            secondary_height,
            f"HEATMAP - {data.key_player_name}",
        )

    def _draw_image_panel(
        self,
        document: canvas.Canvas,
        path: Path,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
    ) -> None:
        document.setFillColor(NAVY)
        document.roundRect(x, y, width, height, 5, fill=1, stroke=0)
        document.drawImage(
            ImageReader(str(path)),
            x + 3,
            y + 3,
            width=width - 6,
            height=height - 6,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        document.setFillColor(colors.Color(17 / 255, 24 / 255, 39 / 255, alpha=0.92))
        document.rect(x + 3, y + height - 20, width - 6, 17, fill=1, stroke=0)
        document.setFillColor(WHITE)
        document.setFont("Helvetica-Bold", 6.5)
        document.drawString(x + 9, y + height - 15, self._truncate(label, 36))

    def _draw_tactical_section(
        self,
        document: canvas.Canvas,
        insights: Sequence[str],
        margin: float,
        width: float,
    ) -> None:
        x = margin
        y = 42
        box_width = width - 2 * margin
        box_height = 266
        document.setFillColor(PITCH_GREEN)
        document.roundRect(x, y, box_width, box_height, 9, fill=1, stroke=0)
        document.setFillColor(ACCENT)
        document.rect(x, y + box_height - 5, box_width, 5, fill=1, stroke=0)

        document.setFillColor(WHITE)
        document.setFont("Helvetica-Bold", 14)
        document.drawString(x + 18, y + box_height - 33, "Avis Tactique StatX")
        document.setFillColor(colors.HexColor("#A7F3D0"))
        document.setFont("Helvetica", 7.5)
        document.drawRightString(
            x + box_width - 18,
            y + box_height - 30,
            "SYNTHESE AUTOMATISEE",
        )

        cursor_y = y + box_height - 68
        for insight in list(insights)[:3]:
            document.setFillColor(ACCENT)
            document.circle(x + 23, cursor_y + 2, 3, fill=1, stroke=0)
            document.setFillColor(WHITE)
            document.setFont("Helvetica", 9.5)
            lines = self._wrap_text(insight, box_width - 64, "Helvetica", 9.5)
            for line in lines[:2]:
                document.drawString(x + 36, cursor_y, line)
                cursor_y -= 13
            cursor_y -= 22

        document.setStrokeColor(colors.HexColor("#28643B"))
        document.line(x + 18, y + 25, x + box_width - 18, y + 25)
        document.setFillColor(colors.HexColor("#86A991"))
        document.setFont("Helvetica", 6.5)
        document.drawString(x + 18, y + 12, "Rapport genere automatiquement par StatX Analytics")
        document.drawRightString(x + box_width - 18, y + 12, "CONFIDENTIEL - STAFF TECHNIQUE")

    @staticmethod
    def _draw_fitted_centered_text(
        document: canvas.Canvas,
        text: str,
        center_x: float,
        y: float,
        max_width: float,
        max_size: float,
        color: colors.Color,
    ) -> None:
        size = max_size
        while size > 8 and stringWidth(text, "Helvetica-Bold", size) > max_width:
            size -= 0.5
        document.setFillColor(color)
        document.setFont("Helvetica-Bold", size)
        document.drawCentredString(center_x, y, text)

    @staticmethod
    def _wrap_text(text: str, max_width: float, font: str, size: float) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and stringWidth(candidate, font, size) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        return text if len(text) <= limit else f"{text[: limit - 3]}..."

