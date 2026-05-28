"""Service for printing kanban labels to Zebra printers."""

from kanban.protocols import Printer
from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.setting import SettingRepository
from kanban.services import ServiceResult
from kanban.zebra import KanbanLabelTemplate


class PrintService:
    def __init__(
        self,
        kanban_repo: KanbanRepository,
        setting_repo: SettingRepository,
        printer_factory: type | None = None,
    ) -> None:
        self.kanban_repo = kanban_repo
        self.setting_repo = setting_repo
        self._printer_factory = printer_factory

    def print_cards(self, kanban_id: int) -> ServiceResult:
        kanban = self.kanban_repo.find_with_details(kanban_id)
        if not kanban:
            return ServiceResult(False, "Kanban not found.", "danger")

        settings = self.setting_repo.get()
        if self._printer_factory is None:
            return ServiceResult(False, "No printer configured.", "danger")

        printer: Printer = self._printer_factory(
            settings["printer_hostname"],
            settings["printer_port"],
            settings["printer_timeout_seconds"],
        )
        try:
            for i in range(1, kanban["number_of_cards"] + 1):
                label = KanbanLabelTemplate(**kanban)
                zpl = label.render(i, settings["label_template"])
                printer.print(zpl)
        except Exception as e:
            return ServiceResult(False, f"Print failed: {e}", "danger")

        return ServiceResult(True, "Kanban card(s) printed.")
