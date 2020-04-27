import graphene
import graphene_django_optimizer as gql_optimizer

from ...wallet import models


def resolve_wallets(info: graphene.ResolveInfo):
    queryset = models.Wallet.objects.filter(user=info.context.user)
    return gql_optimizer.query(queryset, info)
