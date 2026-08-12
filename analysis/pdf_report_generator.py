"""
pdf_report_generator.py
Generate PDF flight reports using reportlab and matplotlib.
"""

import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from analysis.flight_analyzer import FlightAnalyzer
from analysis.wind_estimator import WindEstimator

class PDFReportGenerator:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.analyzer = FlightAnalyzer(data)
        self.metrics = self.analyzer.get_metrics()
        self.wind = WindEstimator(data)
        self.wind_speed, self.wind_direction = self.wind.get_wind()

    def _create_plot(self) -> bytes:
        """Create a matplotlib figure with altitude and temperature plots."""
        if not self.data:
            return None
        times = [datetime.fromisoformat(d['timestamp']) for d in self.data]
        altitudes = [d['altitude'] for d in self.data]
        temperatures = [d['temperature'] for d in self.data]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax1.plot(times, altitudes, color='blue', linewidth=2)
        ax1.set_ylabel('Altitude (m)')
        ax1.grid(True, alpha=0.3)
        ax2.plot(times, temperatures, color='orange', linewidth=2)
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        # Save to BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def generate(self) -> bytes:
        """Generate PDF and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']

        # Custom style for centered title
        center_style = ParagraphStyle(
            'CenterTitle',
            parent=styles['Title'],
            alignment=TA_CENTER,
            fontSize=18,
            spaceAfter=12
        )

        story = []

        # Title
        story.append(Paragraph("TuniLoon Flight Report", center_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        story.append(Spacer(1, 0.25*mm))

        # Metrics table
        m = self.metrics
        data = [
            ['Metric', 'Value'],
            ['Start Time', m.get('start_time', 'N/A')],
            ['End Time', m.get('end_time', 'N/A')],
            ['Duration (hours)', f"{m.get('duration_hours', 0):.2f}"],
            ['Max Altitude (m)', f"{m.get('max_altitude', 0):.0f}"],
            ['Min Temperature (°C)', f"{m.get('min_temperature', 0):.1f}"],
            ['Max Temperature (°C)', f"{m.get('max_temperature', 0):.1f}"],
            ['Avg Ascent Rate (m/s)', f"{m.get('avg_ascent_rate', 0):.1f}"],
            ['Avg Descent Rate (m/s)', f"{m.get('avg_descent_rate', 0):.1f}"],
            ['Total Distance (km)', f"{m.get('total_distance_km', 0):.2f}"],
            ['Wind Speed (m/s)', f"{self.wind_speed:.1f}"],
            ['Wind Direction (°)', f"{self.wind_direction:.1f}"],
            ['Landing Location', f"{m.get('landing_location', (0,0))[0]:.4f}, {m.get('landing_location', (0,0))[1]:.4f}"],
        ]
        table = Table(data, colWidths=[80*mm, 80*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.25*mm))

        # Plot image
        plot_bytes = self._create_plot()
        if plot_bytes:
            img = Image(io.BytesIO(plot_bytes), width=160*mm, height=100*mm)
            story.append(img)

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
