from dataclasses import dataclass


@dataclass(frozen=True)
class LabelTemplateBase:
    kanban_id: int
    part_number: str
    part_manufacturer: str
    part_description: str
    unit_of_measure_abbreviation: str
    reorder_point: int
    kanban_quantity: int

    def __post_init__(self) -> None:
        self.qr = f"K{self.kanban_id:06d}"

    def render(self) -> str:
        raise NotImplementedError(
            "Subclasses must implement this method" 
        )


class KanbanLabelTemplate(LabelTemplateBase):
    def render(self) -> str:
        return f"""
        Hello world!
        """