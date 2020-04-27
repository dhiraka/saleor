import graphene

from .resolvers import resolve_wallets
from .types import Wallet
from ..core.fields import PrefetchingConnectionField


class WalletQueries(graphene.ObjectType):
    wallets = PrefetchingConnectionField(
        Wallet,
        description="List of wallets of authenticated user",
    )

    def resolve_wallets(self, info, **_kwargs):
        return resolve_wallets(info)
