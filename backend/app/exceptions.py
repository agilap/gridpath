class CommitFetchError(Exception):
    pass


class ClassifierError(Exception):
    pass


class FingerprintError(Exception):
    pass


class AuthRequiredError(Exception):
    pass


class RateLimitError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass
