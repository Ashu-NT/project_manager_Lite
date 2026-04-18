from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from src.core.platform.documents import Document, DocumentStorageKind
from ui.platform.shared.styles.ui_config import UIConfig as CFG

try:  # pragma: no cover - optional runtime dependency
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except Exception:  # pragma: no cover - safe desktop fallback
    QPdfDocument = None
    QPdfView = None


_PDF_RUNTIME_AVAILABLE = QPdfDocument is not None and QPdfView is not None


@dataclass(frozen=True)
class DocumentPreviewState:
    status_label: str
    summary: str
    can_open: bool
    open_label: str
    local_file: Path | None = None
    preview_as_pdf: bool = False


def build_document_preview_state(document: Document | None) -> DocumentPreviewState:
    if document is None:
        return DocumentPreviewState(
            status_label="No document selected",
            summary="Select a document to inspect its metadata, preview state, and linked business records.",
            can_open=False,
            open_label="Open Source",
        )

    if document.storage_kind == DocumentStorageKind.FILE_PATH:
        candidate = Path(document.storage_uri).expanduser()
        if not candidate.exists() or not candidate.is_file():
            return DocumentPreviewState(
                status_label="Local file missing",
                summary=(
                    "The document points to a local file path, but the file is not available on this runtime. "
                    "Desktop users can reconnect the path or update the record."
                ),
                can_open=False,
                open_label="Open File",
            )
        if candidate.suffix.lower() == ".pdf":
            if _PDF_RUNTIME_AVAILABLE:
                return DocumentPreviewState(
                    status_label="Embedded PDF preview",
                    summary="This local PDF can be previewed directly in the desktop document library.",
                    can_open=True,
                    open_label="Open PDF",
                    local_file=candidate,
                    preview_as_pdf=True,
                )
            return DocumentPreviewState(
                status_label="PDF open-only",
                summary=(
                    "This runtime can open the PDF file, but the embedded Qt PDF preview component is not available. "
                    "The future web client can render the same record through a browser viewer."
                ),
                can_open=True,
                open_label="Open PDF",
                local_file=candidate,
            )
        return DocumentPreviewState(
            status_label="File open-only",
            summary="This local document is available for desktop opening, but embedded preview is currently optimized for PDFs.",
            can_open=True,
            open_label="Open File",
            local_file=candidate,
        )

    if document.storage_kind == DocumentStorageKind.EXTERNAL_URL:
        return DocumentPreviewState(
            status_label="Browser-linked",
            summary="This document lives at an external URL. Open it in the browser now, and future web delivery can route it through a browser-native viewer.",
            can_open=bool(document.storage_uri.strip()),
            open_label="Open URL",
        )

    return DocumentPreviewState(
        status_label="Metadata reference",
        summary=(
            "This record is a controlled document reference for another system. The platform keeps the metadata and business links here, "
            "while the source system remains the document host."
        ),
        can_open=False,
        open_label="Open Source",
    )


class DocumentPreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document: Document | None = None
        self._preview_state = build_document_preview_state(None)
        self._pdf_document = QPdfDocument(self) if _PDF_RUNTIME_AVAILABLE else None
        self._pdf_view = QPdfView(self) if _PDF_RUNTIME_AVAILABLE else None
        self._setup_ui()
        self.set_document(None)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        root.setSpacing(CFG.SPACING_SM)

        header = QLabel("Preview")
        header.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(header)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(
            f"font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY}; font-size: 10pt;"
        )
        root.addWidget(self.status_label)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        root.addWidget(self.summary_label)

        self.stack = QStackedLayout()
        self.stack.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel()
        self.placeholder.setWordWrap(True)
        self.placeholder.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.placeholder.setMinimumHeight(180)
        self.placeholder.setStyleSheet(
            f"""
            QLabel {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 10px;
                padding: 12px;
                color: {CFG.COLOR_TEXT_SECONDARY};
            }}
            """
        )
        self.stack.addWidget(self.placeholder)

        if self._pdf_view is not None and self._pdf_document is not None:
            self._pdf_view.setDocument(self._pdf_document)
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self._pdf_view.setMinimumHeight(260)
            self.stack.addWidget(self._pdf_view)
        root.addLayout(self.stack, 1)

        self.open_button = QPushButton("Open Source")
        self.open_button.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.open_button.setMinimumWidth(CFG.BUTTON_MIN_WIDTH_SM)
        self.open_button.clicked.connect(self.open_document)
        root.addWidget(self.open_button, 0, Qt.AlignLeft)

    def set_document(self, document: Document | None) -> None:
        self._document = document
        self._preview_state = build_document_preview_state(document)
        self.status_label.setText(self._preview_state.status_label)
        self.summary_label.setText(self._preview_state.summary)
        self.placeholder.setText(self._build_placeholder_text(document, self._preview_state))
        self.open_button.setText(self._preview_state.open_label)
        self.open_button.setEnabled(self._preview_state.can_open)

        if (
            self._preview_state.preview_as_pdf
            and self._preview_state.local_file is not None
            and self._pdf_document is not None
            and self._pdf_view is not None
        ):
            try:
                self._pdf_document.load(str(self._preview_state.local_file))
            except Exception:
                self.stack.setCurrentWidget(self.placeholder)
                self.placeholder.setText(
                    "The PDF file exists, but this runtime could not render it inline. Use the open action instead."
                )
            else:
                self.stack.setCurrentWidget(self._pdf_view)
            return

        self.stack.setCurrentWidget(self.placeholder)

    def open_document(self) -> None:
        if self._document is None or not self._preview_state.can_open:
            return
        url = self._build_open_url(self._document, self._preview_state)
        if url is None:
            QMessageBox.information(
                self,
                "Document Preview",
                "This document does not currently expose a direct open target from the platform library.",
            )
            return
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self,
                "Document Preview",
                "The document target could not be opened from this runtime.",
            )

    @staticmethod
    def _build_open_url(document: Document, state: DocumentPreviewState) -> QUrl | None:
        if document.storage_kind == DocumentStorageKind.FILE_PATH and state.local_file is not None:
            return QUrl.fromLocalFile(str(state.local_file))
        if document.storage_kind == DocumentStorageKind.EXTERNAL_URL and document.storage_uri.strip():
            return QUrl(document.storage_uri.strip())
        return None

    @staticmethod
    def _build_placeholder_text(document: Document | None, state: DocumentPreviewState) -> str:
        if document is None:
            return "Choose a document from the library table to review its preview state."
        lines = [
            f"Storage: {document.storage_kind.value.replace('_', ' ').title()}",
            f"URI: {document.storage_uri or '-'}",
        ]
        if document.file_name:
            lines.append(f"File: {document.file_name}")
        lines.append("")
        lines.append(state.summary)
        return "\n".join(lines)


__all__ = ["DocumentPreviewState", "DocumentPreviewWidget", "build_document_preview_state"]
