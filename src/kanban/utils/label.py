class LabelTemplateBase:
    def __init__(self, 
        id: int,
        part_number: str,
        part_manufacturer: str,
        part_description: str,
        unit_of_measure_abbreviation: str,
        reorder_point: int,
        kanban_quantity: int,
        **kwargs
    ) -> None:
        self.id = id
        self.part_number = part_number
        self.part_manufacturer = part_manufacturer
        self.part_description = part_description
        self.unit_of_measure_abbreviation = unit_of_measure_abbreviation
        self.reorder_point = reorder_point
        self.kanban_quantity = kanban_quantity
        self.qr = f"K{self.id:06d}"

    def render(self) -> str:
        raise NotImplementedError(
            "Subclasses must implement this method" 
        )


class KanbanLabelTemplate(LabelTemplateBase):
    def render(self) -> str:
        return f"""
        Hello world!
        """
