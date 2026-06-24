from ninja import Schema


class BranchSchema(Schema):
    id: int
    name: str
    address: str
    phone: str
    email: str
    working_hours: dict
    coordinates: dict
    is_active: bool
