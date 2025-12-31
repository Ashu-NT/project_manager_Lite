# ui/style_utils.py
from PySide6.QtWidgets import QTableWidget, QHeaderView
from PySide6.QtCore import Qt

def style_table(table: QTableWidget):
    """
    Apply a consistent, professional style to tables:
    - Alternate row colors
    - Nice headers
    - Full-row selection
    - No vertical header
    """

    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setWordWrap(False)
    table.setMouseTracking(True)

    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(table.fontMetrics().height() + 8)


    hh = table.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.Stretch) # comment this to adjust column width manually
    #hh.setStretchLastSection(True)  -- Active this to adjust columns width manually
    hh.setHighlightSections(False)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    # Style via stylesheet
    table.setStyleSheet("""
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f7f9fc;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
        }
        QTableWidget::item {
            padding: 2px 6px;
        }
        QTableWidget::item:selected {
            background-color: #cfe6ff;
            color: #000000;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            color: #555555;
            padding: 4px 6px;
            border: 0px;
            border-right: 1px solid #d0d0d0;
            font-weight: 600;
        }
        QHeaderView::section:last {
            border-right: 0px;
        }
    """)