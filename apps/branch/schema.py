from ninja import Schema


class BranchesGetResponse(Schema):
    name: str
    slug: str
