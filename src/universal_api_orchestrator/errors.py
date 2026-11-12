class IntegrationError(Exception):
    """Error público estable que no contiene tokens, URLs secretas ni cuerpos del proveedor."""
    def __init__(self, code: str, status: int | None = None):
        self.code, self.status = code, status
        super().__init__(code)
