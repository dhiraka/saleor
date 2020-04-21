import graphene

from ..core.connection import CountableDjangoObjectType
from ..core.types import Money
from ...wallet import models


class WalletTransaction(CountableDjangoObjectType):
    class Meta:
        description = "An object representing a single wallet transaction."
        interfaces = [graphene.relay.Node]
        model = models.WalletTransaction
        filter_fields = ["id"]
        only_fields = [
            "id",
            "created",
            "wallet",
            "transaction_type",
            "amount",
            "ledger_amount",
            "source",
            "reason",
            "description",
        ]


class Wallet(CountableDjangoObjectType):
    current_balance = graphene.Field(Money, description="Current Wallet Balance.")
    current_limit = graphene.Field(Money, description="Current Wallet Balance.")

    class Meta:
        description = "An object representing a single wallet."
        interfaces = [graphene.relay.Node]
        model = models.Wallet
        filter_fields = ["id"]
        only_fields = [
            "id",
            "user",
            "credit_limit",
            "currency",
            "current_balance_amount",
            "current_balance",
            "source",
            "reason",
            "description",
        ]

    @staticmethod
    def resolve_current_balance(root: models.Wallet, _info):
        return root.get_current_balance()

    @staticmethod
    def resolve_credit_limit(root: models.Wallet, _info):
        return root.get_credit_limit()
