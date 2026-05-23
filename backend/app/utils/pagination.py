def paginate(page: int = 1, limit: int = 20) -> tuple[int, int]:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    offset = (page - 1) * limit
    return offset, limit
