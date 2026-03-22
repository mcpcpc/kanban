class LabelTemplateBase:
    def __init__(self, 
        id: int,
        bin_location: str,
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
        self.bin_location = bin_location
        self.part_number = part_number
        self.part_manufacturer = part_manufacturer
        self.part_description = part_description
        self.unit_of_measure_abbreviation = unit_of_measure_abbreviation
        self.reorder_point = reorder_point
        self.kanban_quantity = kanban_quantity
        self.number_of_cards = number_of_cards

    def render(self) -> str:
        raise NotImplementedError(
            "Subclasses must implement this method" 
        )


class KanbanLabelTemplate(LabelTemplateBase):
    def render(self) -> str:
        return f"""
^XA
^PW533
^MNY
^LL329
^LH0,0
^LT10
^LS-50
^MD15
^PR1
^PON
^FO16,12
^BQN,2,6,H
^FDQA,{self.id:06d}^FS
^FO162,18
^A0N,32,32
^FD{self.id:06d}^FS
^FO392,18
^A0N,32,32
^FD{self.bin_location}^FS
^FO162,55
^A0N,28,28
^FD{self.part_number}^FS
^FO162,99
^A0N,28,28
^FD{self.part_manufacturer}^FS
^FO240,130
^A0N,20,20
^TBL,345,62
^FD{self.part_description}^FS
^FO162,254
^A0N,26,26
^FDQty: {self.kanban_quantity}^FS
^FO270,254
^A0N,26,26
^FDROP: {self.reorder_point}^FS
^FO392,254
^A0N,26,26
^FDCARD:1 of {self.number_of_cards}^FS
^PQ1
^XZ
        """
