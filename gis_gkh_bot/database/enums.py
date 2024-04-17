from enum import Enum as pyEnum


class UserRolesEnum(pyEnum):
    """User roles."""

    USER = 'user'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'


class ExecutorStatusEnum(pyEnum):
    """Executor statuses."""

    UO = "УО"
    RSO = "РСО"


class OrganizationStatusEnum(pyEnum):
    ACTIVE = "действующая"
    LIQUIDATING = "ликвидируется"
    LIQUIDATED = "ликвидирована"
    BANKRUPT = "банкротство"
    REORGANIZING = "в процессе присоединения к другому юрлицу, с последующей ликвидацией"
