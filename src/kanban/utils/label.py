class KanbanLabelTemplate:
    def __init__(self, 
        id: int,
        location_name: str,
        part_number: str,
        part_manufacturer: str,
        part_description: str,
        unit_of_measure_abbreviation: str,
        reorder_point: int,
        kanban_quantity: int,
        number_of_cards: int,
        **kwargs
    ) -> None:
        self.id = id
        self.location_name = location_name
        self.part_number = part_number
        self.part_manufacturer = part_manufacturer
        self.part_description = part_description
        self.unit_of_measure_abbreviation = unit_of_measure_abbreviation
        self.reorder_point = reorder_point
        self.kanban_quantity = kanban_quantity
        self.number_of_cards = number_of_cards

    def render(self, card_number: int, template: str) -> str:
        return template.format(
            id=self.id,
            location_name=self.location_name,
            part_number=self.part_number,
            part_manufacturer=self.part_manufacturer,
            part_description=self.part_description,
            unit_of_measure_abbreviation=self.unit_of_measure_abbreviation,
            reorder_point=self.reorder_point,
            kanban_quantity=self.kanban_quantity,
            number_of_cards=self.number_of_cards,
            card_number=card_number,
        )
