"""QWebChannel bridge: JS invokes ``markerClicked(id)``; Python emits ``pointSelected``."""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class MapBridge(QObject):
    """
    Registered as ``bridge`` on the page.

    JavaScript calls ``bridge.markerClicked(id)`` (slot). Python code should connect
    to :py:attr:`pointSelected`.
    """

    pointSelected = pyqtSignal(str)

    @pyqtSlot(str)
    def markerClicked(self, marker_id: str) -> None:
        """Invoked from Leaflet when a marker is clicked."""
        print(f"[MapBridge] markerClicked: {marker_id}")
        self.pointSelected.emit(marker_id)
