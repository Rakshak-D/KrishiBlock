from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, Sequence

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

from app.config import get_settings


settings = get_settings()
SECP256K1_ORDER = int('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141', 16)
GENESIS_SEED = 'agrichain_genesis_block'


@dataclass(frozen=True)
class WalletIdentity:
    address: str
    public_key: str
    private_key_encrypted: str


@dataclass(frozen=True)
class SignedTransaction:
    payload_hash: str
    signature: str
    signer_public_key: str
    signer_address: str


@dataclass(frozen=True)
class MinedBlock:
    block_hash: str
    previous_hash: str
    merkle_root: str
    difficulty: int
    nonce: int
    hash_attempts: int
    mining_duration_ms: int
    hash_rate_hps: float
    block_height: int


class WalletSigner:
    def __init__(self, private_key: ec.EllipticCurvePrivateKey, address: str, public_key_pem: str) -> None:
        self._private_key = private_key
        self.address = address
        self.public_key_pem = public_key_pem

    def sign_hash(self, payload_hash: str) -> SignedTransaction:
        der_signature = self._private_key.sign(payload_hash.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        r_value, s_value = decode_dss_signature(der_signature)
        signature = f'{r_value:064x}{s_value:064x}'
        return SignedTransaction(
            payload_hash=payload_hash,
            signature=signature,
            signer_public_key=self.public_key_pem,
            signer_address=self.address,
        )


def _serialize_value(value: object) -> str:
    if isinstance(value, Decimal):
        return f'{value:.2f}'
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.isoformat()
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    return str(value)


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(',', ':'), default=_serialize_value)


def get_genesis_hash() -> str:
    return _sha256(GENESIS_SEED)


def calculate_merkle_root(transaction_hashes: Sequence[str]) -> str:
    if not transaction_hashes:
        return _sha256('empty_merkle_root')
    level = [str(item) for item in transaction_hashes]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_sha256(level[index] + level[index + 1]) for index in range(0, len(level), 2)]
    return level[0]


def derive_wallet_address(public_key_pem: str) -> str:
    public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
    encoded = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return f"agr1{hashlib.sha256(encoded).hexdigest()[:40]}"


def generate_wallet_identity() -> WalletIdentity:
    private_key = ec.generate_private_key(ec.SECP256K1())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    encrypted_private_key = _fernet().encrypt(private_key_pem.encode('utf-8')).decode('utf-8')
    return WalletIdentity(
        address=derive_wallet_address(public_key_pem),
        public_key=public_key_pem,
        private_key_encrypted=encrypted_private_key,
    )


def decrypt_private_key(encrypted_private_key: str) -> ec.EllipticCurvePrivateKey:
    private_key_pem = _fernet().decrypt(encrypted_private_key.encode('utf-8'))
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError('Unsupported wallet private key format.')
    return private_key


def get_wallet_signer(*, address: str, public_key: str, encrypted_private_key: str) -> WalletSigner:
    return WalletSigner(decrypt_private_key(encrypted_private_key), address, public_key)


def get_platform_signer() -> WalletSigner:
    digest = hashlib.sha256(f'{settings.SECRET_KEY}:platform-signer'.encode('utf-8')).digest()
    private_value = (int.from_bytes(digest, 'big') % (SECP256K1_ORDER - 1)) + 1
    private_key = ec.derive_private_key(private_value, ec.SECP256K1())
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    return WalletSigner(private_key, derive_wallet_address(public_key_pem), public_key_pem)


def hash_listing(data: Mapping[str, object]) -> str:
    return _sha256(_canonical_json(data))


def build_transaction_payload(
    *,
    tx_id: str,
    user_id: str,
    tx_type: str,
    amount: Decimal | float | int | str,
    balance_after: Decimal | float | int | str,
    reference_id: str | None,
    description: str,
    created_at: datetime,
) -> dict[str, object]:
    return {
        'id': tx_id,
        'user_id': user_id,
        'type': tx_type,
        'amount': Decimal(str(amount)).quantize(Decimal('0.01')),
        'balance_after': Decimal(str(balance_after)).quantize(Decimal('0.01')),
        'reference_id': reference_id,
        'description': description,
        'created_at': created_at,
    }


def hash_transaction_payload(payload: Mapping[str, object]) -> str:
    return _sha256(_canonical_json(payload))


def sign_transaction_payload(payload: Mapping[str, object], signer: WalletSigner) -> SignedTransaction:
    payload_hash = hash_transaction_payload(payload)
    return signer.sign_hash(payload_hash)


def verify_signature(payload_hash: str, signature_hex: str, public_key_pem: str, signer_address: str | None = None) -> bool:
    try:
        if signer_address and derive_wallet_address(public_key_pem) != signer_address:
            return False
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        if len(signature_hex) != 128:
            return False
        r_value = int(signature_hex[:64], 16)
        s_value = int(signature_hex[64:], 16)
        der_signature = encode_dss_signature(r_value, s_value)
        public_key.verify(der_signature, payload_hash.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def compute_block_hash(*, block_height: int, previous_hash: str, merkle_root: str, created_at: datetime, difficulty: int, nonce: int) -> str:
    payload = '|'.join(
        [
            str(block_height),
            previous_hash,
            merkle_root,
            _serialize_value(created_at),
            str(difficulty),
            str(nonce),
        ]
    )
    return _sha256(payload)


def mine_block(*, block_height: int, previous_hash: str, transaction_hashes: Sequence[str], created_at: datetime, difficulty: int | None = None) -> MinedBlock:
    resolved_difficulty = max(1, int(difficulty or settings.BLOCKCHAIN_DIFFICULTY))
    merkle_root = calculate_merkle_root(transaction_hashes)
    target_prefix = '0' * resolved_difficulty
    nonce = 0
    attempts = 0
    start = time.perf_counter()

    while True:
        block_hash = compute_block_hash(
            block_height=block_height,
            previous_hash=previous_hash,
            merkle_root=merkle_root,
            created_at=created_at,
            difficulty=resolved_difficulty,
            nonce=nonce,
        )
        attempts += 1
        if block_hash.startswith(target_prefix):
            elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))
            hash_rate = round(attempts / max(elapsed_ms / 1000, 0.001), 2)
            return MinedBlock(
                block_hash=block_hash,
                previous_hash=previous_hash,
                merkle_root=merkle_root,
                difficulty=resolved_difficulty,
                nonce=nonce,
                hash_attempts=attempts,
                mining_duration_ms=elapsed_ms,
                hash_rate_hps=hash_rate,
                block_height=block_height,
            )
        nonce += 1


def block_confirmations(block_height: int, current_height: int) -> int:
    return max(0, current_height - block_height + 1)


def verify_chain(transactions: list[Mapping[str, object]]) -> bool:
    if not transactions:
        return True

    ordered = sorted(transactions, key=lambda item: int(item.get('block_height') or 0))
    previous_hash = get_genesis_hash()
    last_height = 0

    for entry in ordered:
        block_height = int(entry.get('block_height') or 0)
        if block_height <= 0 or block_height != last_height + 1:
            return False

        payload = build_transaction_payload(
            tx_id=str(entry.get('id') or ''),
            user_id=str(entry.get('user_id') or ''),
            tx_type=str(entry.get('type') or ''),
            amount=entry.get('amount') or Decimal('0.00'),
            balance_after=entry.get('balance_after') or Decimal('0.00'),
            reference_id=str(entry.get('reference_id')) if entry.get('reference_id') is not None else None,
            description=str(entry.get('description') or ''),
            created_at=entry.get('created_at') if isinstance(entry.get('created_at'), datetime) else datetime.fromisoformat(str(entry.get('created_at'))),
        )
        expected_payload_hash = hash_transaction_payload(payload)
        if str(entry.get('transaction_hash') or '') != expected_payload_hash:
            return False
        if not verify_signature(
            expected_payload_hash,
            str(entry.get('signature') or ''),
            str(entry.get('signer_public_key') or ''),
            str(entry.get('signer_address') or '') or None,
        ):
            return False

        expected_merkle_root = calculate_merkle_root([expected_payload_hash])
        if str(entry.get('merkle_root') or '') != expected_merkle_root:
            return False
        difficulty = int(entry.get('difficulty') or 0)
        nonce = int(entry.get('nonce') or 0)
        created_at = payload['created_at']
        expected_block_hash = compute_block_hash(
            block_height=block_height,
            previous_hash=previous_hash,
            merkle_root=expected_merkle_root,
            created_at=created_at,
            difficulty=difficulty,
            nonce=nonce,
        )
        if str(entry.get('previous_hash') or '') != previous_hash:
            return False
        if str(entry.get('hash') or '') != expected_block_hash:
            return False
        if not expected_block_hash.startswith('0' * max(1, difficulty)):
            return False

        previous_hash = expected_block_hash
        last_height = block_height
    return True
