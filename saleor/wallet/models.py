import enum
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from prices import Money

from .exceptions import InsufficientWalletBalance


class WalletTransactionType(enum.Enum):
    Credit = 'Credit'
    Debit = 'Debit'


class WalletQueryset(models.QuerySet):
    def delete(self):
        self.update(deleted=True)

    def active(self):
        return self.filter(is_active=True)


class WalletManager(models.Manager):
    use_for_related_fields = True

    def with_deleted(self):
        return WalletQueryset(self.model, using=self._db)

    def deleted(self):
        return self.with_deleted().filter(deleted=True)

    def get_queryset(self):
        return self.with_deleted().exclude(deleted=True)


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="wallet",
    )
    deleted = models.NullBooleanField(editable=False)

    currency = models.CharField(
        max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH,
        default=settings.DEFAULT_CURRENCY,
        editable=False,
    )
    current_balance = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=0,
        editable=False,
    )
    credit_limit = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=0,
        editable=False,
    )

    created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()

    objects = WalletManager()

    def get_current_balance(self):
        return Money(self.current_balance,
                     self.currency or settings.DEFAULT_CURRENCY)

    def get_credit_limit(self):
        return Money(self.credit_limit,
                     self.currency or settings.DEFAULT_CURRENCY)

    def can_spend(self, amount: Decimal):
        return amount <= (self.current_balance + self.credit_limit)

    def deposit(self, amount: Decimal, transaction_type: WalletTransactionType,
                source: str,
                reason: str, description: str) -> "WalletTransaction":
        """Deposits a value to the wallet.
        Also creates a new transaction with the deposit
        value.
        """
        assert transaction_type == WalletTransactionType.Credit
        ledger_amount = self.current_balance + amount
        wallet_transaction = self.wallet_transactions.create(
            transaction_type=transaction_type,
            amount=amount,
            ledger_amount=ledger_amount,
            source=source,
            reason=reason,
            description=description,
        )
        self.current_balance = ledger_amount
        self.save()

        return wallet_transaction

    def withdraw(self, amount: Decimal, transaction_type: WalletTransactionType,
                 source: str,
                 reason: str, description: str) -> "WalletTransaction":
        """Withdraw's a value from the wallet.
        Also creates a new transaction with the withdraw
        value.
        Should the withdrawn amount is greater than the
        balance this wallet currently has, it raises an
        :mod:`InsufficientBalance` error. This exception
        inherits from :mod:`django.db.IntegrityError`. So
        that it automatically rolls-back during a
        transaction lifecycle.
        """
        assert transaction_type == WalletTransactionType.Debit

        if not self.can_spend(amount):
            raise InsufficientWalletBalance('This wallet has insufficient balance.')

        ledger_amount = self.current_balance - amount
        wallet_transaction = self.wallet_transactions.create(
            transaction_type=transaction_type,
            amount=-amount,
            ledger_amount=ledger_amount,
            source=source,
            reason=reason,
            description=description,
        )
        self.current_balance = ledger_amount
        self.save()

        return wallet_transaction


class WalletTransactionQueryset(models.QuerySet):
    def delete(self):
        self.update(deleted=True)


class WalletTransactionManager(models.Manager):
    use_for_related_fields = True

    def with_deleted(self):
        return WalletTransactionQueryset(self.model, using=self._db)

    def deleted(self):
        return self.with_deleted().filter(deleted=True)

    def get_queryset(self):
        return self.with_deleted().exclude(deleted=True)


class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.NullBooleanField(editable=False)
    wallet = models.ForeignKey(Wallet, related_name='wallet_transactions', null=True,
                               on_delete=models.SET_NULL)
    transaction_type = models.CharField(max_length=40,
                                        choices=[(_type, _type.value) for _type in
                                                 WalletTransactionType])
    amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        editable=False,
    )
    ledger_amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        editable=False,
    )
    source = models.CharField(max_length=40)
    reason = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()

    objects = WalletTransactionManager()
