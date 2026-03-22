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
^PW788
^MNY
^LL486
^LH0,0
^LT0
^LS0
^MD20
^PR4
^PON
^FO24,18
^BQN,2,9,H
^FDQA,{self.id:06d}^FS
^FO240,26
^A0N,48,48
^FD{self.id:06d}^FS
^FO580,26
^A0N,48,48
^FD{self.bin_location}^FS
^FO240,80
^A0N,42,42
^FD{self.part_number}^FS
^FO240,148
^A0N,36,36
^FD{self.part_manufacturer}^FS
^FO240,192
^A0N,30,30
^TBL,535,62
^FD{self.part_description}^FS
^FO240,374
^A0N,38,38
^FDQty:{self.kanban_quantity}^FS
^FO400,374
^A0N,38,38
^FDROP:{self.reorder_point}^FS
^FO580,374
^A0N,38,38
^FDCARD:1/{self.number_of_cards}^FS
^PQ1
^XZ
        """
