"""Loan middleware (slice 3: every loan API response carries no-store)."""


class NoStoreForLoansMiddleware:
    """Attach Cache-Control: no-store to loan responses, including errors.

    Views set the header on their direct responses; this covers errors
    rendered by the global exception handler (400/403/404) on loan paths.
    """

    LOAN_PREFIXES = ("/api/v1/loans", "/api/v1/staff/loans")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.LOAN_PREFIXES):
            response["Cache-Control"] = "no-store"
        return response
