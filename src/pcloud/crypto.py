"""
pCloud crypto support for encrypted filenames, folder keys, and file decryption.
Translated from pCloud's Go crypto implementation.
"""

import base64
import hmac
import struct
import hashlib
import logging
from hashlib import sha1, sha512
from typing import Tuple, Optional

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA1, SHA512
from Crypto.Protocol.KDF import PBKDF2
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)

# Constants for sector-based file decryption
SECTOR_SIZE = 4096
AUTH_SIZE = 32
TREE_SECTORS = 128

MAX_LEVEL_SIZE = [
    4096,
    528384,
    67637248,
    8657571840,
    1108169199616,
    0x810204081000,
    0x40810204081000,
]


class FolderKey:
    """Represents a decrypted folder Content Encryption Key (CEK)."""
    
    def __init__(self, type_: int, flags: int, aes_key: bytes, hmac_key: bytes):
        self.type = type_
        self.flags = flags
        self.aes_key = aes_key
        self.hmac_key = hmac_key


class ParsedPrivateKey:
    """Represents a parsed pCloud private key blob."""
    
    def __init__(self, type_: int, flags: int, salt: bytes, key: bytes):
        self.type = type_
        self.flags = flags
        self.salt = salt
        self.key = key


class ParsedPublicKey:
    """Represents a parsed pCloud public key blob."""
    
    def __init__(self, type_: bytes, flags: bytes, key: bytes):
        self.type = type_
        self.flags = flags
        self.key = key


class KeyPair:
    """Represents a decrypted RSA key pair for pCloud crypto operations."""
    
    def __init__(
        self,
        private_key: ParsedPrivateKey,
        public_key: ParsedPublicKey,
        rsa_priv: RSA.RsaKey,
        rsa_pub: RSA.RsaKey
    ):
        self.private_key = private_key
        self.public_key = public_key
        self.rsa_priv = rsa_priv
        self.rsa_pub = rsa_pub
    
    def decrypt_folder_key(self, encrypted_key: str) -> FolderKey:
        """Decrypt a folder's Content Encryption Key (CEK) using RSA-OAEP (SHA-1)."""
        if not self.rsa_priv:
            raise ValueError("Private key not loaded")
        
        enc = base64_url_decode(encrypted_key)
        cipher = PKCS1_OAEP.new(self.rsa_priv, hashAlgo=SHA1)
        dec = cipher.decrypt(enc)
        
        if len(dec) < 41:
            raise ValueError("Decrypted folder key too short")
        
        type_ = struct.unpack('<I', dec[0:4])[0]
        flags = struct.unpack('<I', dec[4:8])[0]
        aes_key = dec[8:40]
        hmac_key = dec[40:]
        
        return FolderKey(type_, flags, aes_key, hmac_key)

    def decrypt_file_key(self, encrypted_key: str) -> FolderKey:
        """Decrypt a file's Content Encryption Key (CEK) using RSA-OAEP (SHA-1).
        The format matches decrypt_folder_key (type|flags|AES|HMAC).
        """
        return self.decrypt_folder_key(encrypted_key)


# Helper functions

def align_to_16(data: bytes) -> bytes:
    """Return a zero-padded copy of data aligned to a 16-byte boundary."""
    if len(data) % 16 == 0:
        return data
    aligned = bytearray(((len(data) // 16) + 1) * 16)
    aligned[:len(data)] = data
    return bytes(aligned)


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """XOR two equal-length byte slices and return a new bytes object."""
    if len(a) != len(b):
        raise ValueError("xor_bytes: lengths must match")
    return bytes(x ^ y for x, y in zip(a, b))


def remove_padding(data: bytes) -> bytes:
    """Trim trailing zero bytes."""
    end = len(data)
    while end > 0 and data[end - 1] == 0:
        end -= 1
    return data[:end]


def base32_encode(data: bytes) -> str:
    """Encode bytes to Base32 without padding and convert to uppercase."""
    enc = base64.b32encode(data).decode('ascii')
    return enc.rstrip('=').upper()


def base32_decode(s: str) -> bytes:
    """Decode a Base32 string (case-insensitive, no padding required)."""
    s = s.upper()
    # Add padding if needed
    padding = (8 - len(s) % 8) % 8
    s += '=' * padding
    return base64.b32decode(s)


def base64_url_decode(s: str) -> bytes:
    """Decode a base64url string (no padding)."""
    return base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4))


def base64_url_encode(data: bytes) -> str:
    """Encode bytes to base64url (no padding)."""
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def swap32(n: int) -> int:
    """Reverse byte order of a 32-bit integer."""
    return (
        ((n >> 24) & 0xFF) |
        ((n >> 8) & 0xFF00) |
        ((n << 8) & 0xFF0000) |
        ((n << 24) & 0xFF000000)
    ) & 0xFFFFFFFF


def decrypt_pctr(block_cipher: AES, iv: bytes, src: bytes) -> bytes:
    """
    Implement pCloud's custom PCTR (parallel counter) mode for private key decryption.
    """
    dst = bytearray(len(src))
    counter = 0
    
    for i in range(0, len(src), 16):
        # Create counter block
        ctr = bytearray(16)
        struct.pack_into('>I', ctr, 0, swap32(counter))
        
        # XOR with IV
        ctr = bytes(ctr[j] ^ iv[j] for j in range(16))
        
        # Encrypt counter
        tmp = block_cipher.encrypt(ctr)
        
        # XOR with source
        end = min(i + 16, len(src))
        for j in range(i, end):
            dst[j] = tmp[j - i] ^ src[j]
        
        counter += 1
    
    return bytes(dst)


# Main crypto functions

def encrypt_filename(name: str, key: FolderKey) -> str:
    """
    Encrypt a filename using pCloud's encryption scheme.
    The encrypted name is Base32 encoded (upper-case, no padding).
    """
    name_bytes = name.encode('utf-8')
    aligned = align_to_16(name_bytes)
    
    if len(aligned) == 16:
        # Exactly one block: XOR with first 16 bytes of HMAC key, then AES-ECB
        xored = xor_bytes(aligned, key.hmac_key[:16])
        cipher = AES.new(key.aes_key, AES.MODE_ECB)
        out = cipher.encrypt(xored)
        return base32_encode(out)
    
    # Longer: HMAC of unpadded tail (after first 16), IV = first 16 bytes of HMAC
    data_after_first = aligned[16:]
    unpadded_after_first = remove_padding(data_after_first)
    
    h = hmac.new(key.hmac_key, unpadded_after_first, sha512)
    iv = h.digest()[:16]
    
    cipher = AES.new(key.aes_key, AES.MODE_CBC, iv)
    enc = cipher.encrypt(aligned)
    
    return base32_encode(enc)


def decrypt_filename(encrypted_name: str, key: FolderKey) -> str:
    """Decrypt a Base32-encoded pCloud filename using the folder key."""
    enc_bytes = base32_decode(encrypted_name)
    cipher = AES.new(key.aes_key, AES.MODE_ECB)
    
    if len(enc_bytes) == 16:
        # One block: AES-ECB decrypt then XOR with first 16 of HMAC key, remove zero padding
        dec = cipher.decrypt(enc_bytes)
        xored = xor_bytes(dec, key.hmac_key[:16])
        unpadded = remove_padding(xored)
        result = unpadded.decode('utf-8')
        return result
    
    # Multi-block: first 16 bytes act as IV for the rest
    enc_iv = enc_bytes[:16]
    enc_data = enc_bytes[16:]
    
    cbc = AES.new(key.aes_key, AES.MODE_CBC, enc_iv)
    dec_data = cbc.decrypt(enc_data)
    
    unpadded = remove_padding(dec_data)
    
    # Compute HMAC to get IV for first block
    h = hmac.new(key.hmac_key, unpadded, sha512)
    iv = h.digest()[:16]
    
    cbc2 = AES.new(key.aes_key, AES.MODE_CBC, iv)
    first = cbc2.decrypt(enc_iv)
    
    result = first + unpadded
    
    # Validate UTF-8
    try:
        return result.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("Decrypted text is not valid UTF-8 (likely wrong key)")


def parse_private_key(encoded_key: str) -> ParsedPrivateKey:
    """Parse a base64url-encoded pCloud private key blob."""
    data = base64_url_decode(encoded_key)
    
    if len(data) < 72:
        raise ValueError("Private key too short")
    
    type_ = struct.unpack('<I', data[0:4])[0]
    flags = struct.unpack('<I', data[4:8])[0]
    salt = data[8:72]
    key = data[72:]
    
    return ParsedPrivateKey(type_, flags, salt, key)


def parse_public_key(encoded_key: str) -> ParsedPublicKey:
    """Parse a base64url-encoded pCloud public key blob."""
    data = base64_url_decode(encoded_key)
    
    if len(data) < 8:
        raise ValueError("Public key too short")
    
    type_ = data[0:4]
    flags = data[4:8]
    key = data[8:]
    
    return ParsedPublicKey(type_, flags, key)


def decrypt_private_key(
    password: str,
    encoded_private_key: str,
    encoded_public_key: str
) -> KeyPair:
    """
    Decrypt the user's private key using their crypto password.
    PBKDF2-HMAC-SHA512 (20000 iters) derives AES key + IV; decrypt with custom PCTR.
    """
    priv_key = parse_private_key(encoded_private_key)
    pub_key = parse_public_key(encoded_public_key)
    
    # Derive AES key and IV using PBKDF2.
    derived = PBKDF2(
        password.encode('utf-8'),
        priv_key.salt,
        dkLen=48,
        count=20000,
        hmac_hash_module=SHA512
    )
    aes_key = derived[:32]
    iv = derived[32:48]
    
    # Decrypt private key using PCTR mode
    cipher = AES.new(aes_key, AES.MODE_ECB)
    dec = decrypt_pctr(cipher, iv, priv_key.key)
    
    if len(dec) < 4:
        raise ValueError("Decrypted key too short")
    
    # Trim ASN.1 to exact length based on DER header
    if dec[1] & 0x80 != 0:
        num_len = dec[1] & 0x7F
        key_len = 2 + num_len
        for i in range(num_len):
            key_len += dec[2 + i] << (8 * (num_len - 1 - i))
    else:
        key_len = dec[1] + 2
    
    if key_len > len(dec):
        key_len = len(dec)
    dec = dec[:key_len]
    
    # Parse RSA keys
    try:
        rsa_priv = RSA.import_key(dec)
    except Exception as e:
        raise ValueError(f"Failed to parse decrypted private key: {e}")
    
    try:
        rsa_pub = RSA.import_key(pub_key.key)
    except Exception as e:
        raise ValueError(f"Failed to parse public key: {e}")
    
    return KeyPair(priv_key, pub_key, rsa_priv, rsa_pub)


# File decryption functions

class CipherOffsetsInfo:
    """Offsets structure for sector-based file decryption."""
    
    def __init__(self):
        self.need_master_auth = False
        self.master_auth_offset = 0
        self.plain_size = 0
        self.sectors = 0
        self.cipher_size = 0
        self.tree_levels = 0
        self.last_auth_offset = []
        self.last_auth_length = []
    
    def ensure_levels(self, levels: int):
        """Ensure arrays have enough capacity for tree levels."""
        if len(self.last_auth_offset) < levels:
            self.last_auth_offset.extend([0] * (levels - len(self.last_auth_offset)))
        if len(self.last_auth_length) < levels:
            self.last_auth_length.extend([0] * (levels - len(self.last_auth_length)))


def compute_cipher_offsets(cipher_size: int) -> CipherOffsetsInfo:
    """Compute offsets for encrypted file structure."""
    n = CipherOffsetsInfo()
    
    if cipher_size <= AUTH_SIZE:
        return n
    
    n.cipher_size = cipher_size
    n.need_master_auth = cipher_size > SECTOR_SIZE + AUTH_SIZE
    t = cipher_size - AUTH_SIZE
    
    if n.need_master_auth:
        n.master_auth_offset = t
    else:
        n.master_auth_offset = t + AUTH_SIZE
    
    # Determine tree level
    i = 0
    while i < len(MAX_LEVEL_SIZE) and not (t <= MAX_LEVEL_SIZE[i]):
        i += 1
    
    e = t
    n.tree_levels = i
    n.ensure_levels(i + 1)
    n.last_auth_offset[i] = e
    n.last_auth_length[i] = AUTH_SIZE
    
    while i > 0:
        i -= 1
        r = (t + MAX_LEVEL_SIZE[i] + AUTH_SIZE - 1) // (MAX_LEVEL_SIZE[i] + AUTH_SIZE)
        t -= r * AUTH_SIZE
        r %= TREE_SECTORS
        if r == 0:
            r = TREE_SECTORS
        e -= r * AUTH_SIZE
        n.last_auth_offset[i] = e
        n.last_auth_length[i] = r * AUTH_SIZE
    
    n.plain_size = t
    n.sectors = (t + SECTOR_SIZE - 1) // SECTOR_SIZE
    return n


def level_auth_offset(level: int, e: int) -> int:
    """Calculate auth offset for a given level."""
    r = MAX_LEVEL_SIZE[level + 1] * (e + 1) - SECTOR_SIZE
    while e >= TREE_SECTORS:
        e = e // TREE_SECTORS
        r += e * SECTOR_SIZE
    return r


def data_cipher_offset_by_sectorid(t: int) -> int:
    """Calculate data offset for a sector ID."""
    e = t * SECTOR_SIZE
    while t >= TREE_SECTORS:
        t = t // TREE_SECTORS
        e += t * SECTOR_SIZE
    return e


def cipher_download_offset(t: int, n: CipherOffsetsInfo) -> tuple:
    """Get download offset range for a sector."""
    r = data_cipher_offset_by_sectorid(t)
    i = data_cipher_offset_by_sectorid(t + TREE_SECTORS)
    if t + TREE_SECTORS > n.sectors:
        i = n.cipher_size
    return (r, i, i - r)


def get_last_sectorid_by_size(t: int) -> int:
    """Get last sector ID for a given size."""
    if t == 0:
        return 0
    return (t - 1) // SECTOR_SIZE


def auth_sector_offset(t: int, level: int, n: CipherOffsetsInfo) -> tuple:
    """Get auth window for a sector at a given level."""
    i = get_last_sectorid_by_size(n.plain_size) // TREE_SECTORS
    nn = t // TREE_SECTORS
    s = t % TREE_SECTORS
    
    for o in range(level):
        i = i // TREE_SECTORS
        s = nn % TREE_SECTORS
        nn = nn // TREE_SECTORS
    
    if nn == i:
        n.ensure_levels(level + 1)
        a = n.last_auth_offset[level]
        f = n.last_auth_length[level]
    else:
        a = level_auth_offset(level, nn)
        f = SECTOR_SIZE
    
    return (a, f, s)


def xor_bytes_limit(a: bytes, b: bytes, n: int) -> bytes:
    """XOR two byte arrays up to n bytes."""
    if len(a) < n or len(b) < n:
        n = min(len(a), len(b))
    return bytes(a[i] ^ b[i] for i in range(n))


def xor_exact(a: bytes, b: bytes) -> bytes:
    """XOR two byte arrays of equal length."""
    if len(a) != len(b):
        raise ValueError("xorBytes length mismatch")
    return bytes(a[i] ^ b[i] for i in range(len(a)))


def decrypt_sector(key: FolderKey, cipher_data: bytes, auth: bytes, sector_id: int) -> bytes:
    """Decrypt a single sector using pCloud's sector encryption.
    
    Exactly matches the Go implementation from pcrypto.js decryptSector.
    """
    if len(auth) != 32:
        raise ValueError(f"auth length {len(auth)} != 32")
    
    # n = AES-ECB-DEC(auth, AESKey) - decrypt 32 bytes as two blocks
    blk = AES.new(key.aes_key, AES.MODE_ECB)
    n = bytearray(32)
    n[0:16] = blk.decrypt(auth[0:16])
    n[16:32] = blk.decrypt(auth[16:32])
    
    # o = n[0:8] || n[24:32] (16 bytes total)
    # f = n[8:24] (16 bytes - the IV/HMAC check value)
    o = bytearray(n[0:8])
    o.extend(n[24:32])
    f = bytes(n[8:24])
    
    e = cipher_data
    p = bytearray()
    
    if len(e) < 16:
        # Short data: XOR with o
        p = bytearray(xor_bytes_limit(o, e, len(e)))
        # Update o for HMAC: o = e || o[len(e):]
        o_orig = bytes(o)
        o = bytearray(e)
        o.extend(o_orig[len(e):])
    else:
        # Process full/partial blocks
        u = 0
        tail = None
        
        if len(e) % 16 != 0:
            # Has unaligned tail
            u = len(e) % 16
            l = len(e) - 16 - u
            tail = e[l:]
            e = e[:l]
        
        if len(e) > 0:
            # CBC decrypt main blocks with IV=f
            cbc = AES.new(key.aes_key, AES.MODE_CBC, f)
            pt = cbc.decrypt(e)
            p.extend(pt)
        
        if tail is not None:
            # Handle unaligned tail (ciphertext stealing)
            # v = last ciphertext block or f if no blocks
            if len(e) > 0:
                v = e[-16:]
            else:
                v = f
            
            # Decrypt first 16 bytes of tail
            b = bytearray(blk.decrypt(tail[:16]))
            # XOR with remaining tail bytes
            y = xor_exact(bytes(b[:u]), tail[16:])
            # Construct block: tail[16:] || b[u:]
            g = bytearray(tail[16:])
            g.extend(b[u:])
            # Decrypt with CBC using v as IV
            cbc2 = AES.new(key.aes_key, AES.MODE_CBC, v)
            dec = cbc2.decrypt(bytes(g))
            p.extend(dec)
            p.extend(y)
    
    # Verify HMAC: w = m || uint64(sectorID LE) || o
    sid = bytearray(8)
    tmp = sector_id
    for i in range(8):
        sid[i] = tmp % 256
        tmp //= 256
    
    w = bytes(p) + bytes(sid) + bytes(o)
    mac = hmac.new(key.hmac_key, w, sha512)
    sum_bytes = mac.digest()
    
    if not hmac.compare_digest(sum_bytes[:16], f):
        raise ValueError("sector auth compare fail")
    
    return bytes(p)


def decrypt_file_contents(encrypted_data: bytes, file_key: FolderKey) -> bytes:
    """Decrypt encrypted file data using sector-based decryption."""
    offs = compute_cipher_offsets(len(encrypted_data))
    
    if offs.plain_size < 0 or offs.sectors < 0:
        raise ValueError(f"invalid offsets for size={len(encrypted_data)}")
    
    out = bytearray()
    sector = 0
    
    while sector < offs.sectors:
        # Determine chunk covering up to TREE_SECTORS sectors
        chunk_offset, chunk_end, _ = cipher_download_offset(sector, offs)
        
        if chunk_offset < 0 or chunk_end > len(encrypted_data) or chunk_offset >= chunk_end:
            raise ValueError(f"invalid chunk offsets at sector {sector}")
        
        # Level-0 auth position
        a0_offset, a0_length, a0_authID = auth_sector_offset(sector, 0, offs)
        
        # Number of sectors available from this auth window
        d = a0_length // AUTH_SIZE - a0_authID
        if d <= 0:
            raise ValueError(f"bad auth window d={d} at sector={sector}")
        
        # Data length for this chunk up to first level-0 auth
        p = a0_offset - chunk_offset
        
        # Process up to d sectors in this chunk
        for y in range(d):
            if sector + y >= offs.sectors:
                break
            
            # Compute sector length
            f = SECTOR_SIZE
            if not (a0_offset == SECTOR_SIZE * TREE_SECTORS or y != d - 1):
                f = p - y * SECTOR_SIZE
                if f < 0:
                    raise ValueError(f"negative sector length at sector={sector + y}")
            
            data_start = chunk_offset + y * SECTOR_SIZE
            data_end = data_start + f
            
            if data_start < 0 or data_end > len(encrypted_data):
                raise ValueError(f"data slice OOB sector={sector + y}")
            
            c = encrypted_data[data_start:data_end]
            
            # Auth record for this sector at level 0
            auth_start = a0_offset + (a0_authID + y) * AUTH_SIZE
            auth_end = auth_start + AUTH_SIZE
            
            if auth_end > len(encrypted_data):
                raise ValueError(f"auth slice OOB sector={sector + y}")
            
            h = encrypted_data[auth_start:auth_end]
            
            pt = decrypt_sector(file_key, c, h, sector + y)
            out.extend(pt)
        
        sector += TREE_SECTORS
    
    # Truncate to exact plain size
    if len(out) > offs.plain_size:
        out = out[:offs.plain_size]
    
    return bytes(out)


# File decryption functions

class CipherOffsetsInfo:
    """Offsets structure for sector-based file decryption."""
    
    def __init__(self):
        self.need_master_auth = False
        self.master_auth_offset = 0
        self.plain_size = 0
        self.sectors = 0
        self.cipher_size = 0
        self.tree_levels = 0
        self.last_auth_offset = []
        self.last_auth_length = []
    
    def ensure_levels(self, levels: int):
        """Ensure arrays have enough capacity for tree levels."""
        if len(self.last_auth_offset) < levels:
            self.last_auth_offset.extend([0] * (levels - len(self.last_auth_offset)))
        if len(self.last_auth_length) < levels:
            self.last_auth_length.extend([0] * (levels - len(self.last_auth_length)))


def compute_cipher_offsets(cipher_size: int) -> CipherOffsetsInfo:
    """Compute offsets for encrypted file structure."""
    n = CipherOffsetsInfo()
    
    if cipher_size <= AUTH_SIZE:
        return n
    
    n.cipher_size = cipher_size
    n.need_master_auth = cipher_size > SECTOR_SIZE + AUTH_SIZE
    t = cipher_size - AUTH_SIZE
    
    if n.need_master_auth:
        n.master_auth_offset = t
    else:
        n.master_auth_offset = t + AUTH_SIZE
    
    # Determine tree level
    i = 0
    while i < len(MAX_LEVEL_SIZE) and not (t <= MAX_LEVEL_SIZE[i]):
        i += 1
    
    e = t
    n.tree_levels = i
    n.ensure_levels(i + 1)
    n.last_auth_offset[i] = e
    n.last_auth_length[i] = AUTH_SIZE
    
    while i > 0:
        i -= 1
        r = (t + MAX_LEVEL_SIZE[i] + AUTH_SIZE - 1) // (MAX_LEVEL_SIZE[i] + AUTH_SIZE)
        t -= r * AUTH_SIZE
        r %= TREE_SECTORS
        if r == 0:
            r = TREE_SECTORS
        e -= r * AUTH_SIZE
        n.last_auth_offset[i] = e
        n.last_auth_length[i] = r * AUTH_SIZE
    
    n.plain_size = t
    n.sectors = (t + SECTOR_SIZE - 1) // SECTOR_SIZE
    return n


def level_auth_offset(level: int, e: int) -> int:
    """Calculate auth offset for a given level."""
    r = MAX_LEVEL_SIZE[level + 1] * (e + 1) - SECTOR_SIZE
    while e >= TREE_SECTORS:
        e = e // TREE_SECTORS
        r += e * SECTOR_SIZE
    return r


def data_cipher_offset_by_sectorid(t: int) -> int:
    """Calculate data offset for a sector ID."""
    e = t * SECTOR_SIZE
    while t >= TREE_SECTORS:
        t = t // TREE_SECTORS
        e += t * SECTOR_SIZE
    return e


def cipher_download_offset(t: int, n: CipherOffsetsInfo) -> tuple:
    """Get download offset range for a sector."""
    r = data_cipher_offset_by_sectorid(t)
    i = data_cipher_offset_by_sectorid(t + TREE_SECTORS)
    if t + TREE_SECTORS > n.sectors:
        i = n.cipher_size
    return (r, i, i - r)


def get_last_sectorid_by_size(t: int) -> int:
    """Get last sector ID for a given size."""
    if t == 0:
        return 0
    return (t - 1) // SECTOR_SIZE


def auth_sector_offset(t: int, level: int, n: CipherOffsetsInfo) -> tuple:
    """Get auth window for a sector at a given level."""
    i = get_last_sectorid_by_size(n.plain_size) // TREE_SECTORS
    nn = t // TREE_SECTORS
    s = t % TREE_SECTORS
    
    for o in range(level):
        i = i // TREE_SECTORS
        s = nn % TREE_SECTORS
        nn = nn // TREE_SECTORS
    
    if nn == i:
        n.ensure_levels(level + 1)
        a = n.last_auth_offset[level]
        f = n.last_auth_length[level]
    else:
        a = level_auth_offset(level, nn)
        f = SECTOR_SIZE
    
    return (a, f, s)


def xor_bytes_limit(a: bytes, b: bytes, n: int) -> bytes:
    """XOR two byte arrays up to n bytes."""
    if len(a) < n or len(b) < n:
        n = min(len(a), len(b))
    return bytes(a[i] ^ b[i] for i in range(n))


def xor_exact(a: bytes, b: bytes) -> bytes:
    """XOR two byte arrays of equal length."""
    if len(a) != len(b):
        raise ValueError("xorBytes length mismatch")
    return bytes(a[i] ^ b[i] for i in range(len(a)))


def decrypt_sector(key: FolderKey, cipher_data: bytes, auth: bytes, sector_id: int) -> bytes:
    """Decrypt a single sector using pCloud's sector encryption.
    
    Exactly matches the Go implementation from pcrypto.js decryptSector.
    """
    if len(auth) != 32:
        raise ValueError(f"auth length {len(auth)} != 32")
    
    logger.info(f"Sector {sector_id}: cipher_data_len={len(cipher_data)}, cipher_preview={cipher_data[:32].hex()}...")
    
    # n = AES-ECB-DEC(auth, AESKey) - decrypt 32 bytes as two blocks
    blk = AES.new(key.aes_key, AES.MODE_ECB)
    n = bytearray(32)
    n[0:16] = blk.decrypt(auth[0:16])
    n[16:32] = blk.decrypt(auth[16:32])
    
    logger.info(f"Sector {sector_id}: auth={auth.hex()[:64]}...")
    logger.info(f"Sector {sector_id}: n={bytes(n).hex()}")
    
    # o = n[0:8] || n[24:32] (16 bytes total)
    # f = n[8:24] (16 bytes - the IV/HMAC check value)
    o = bytearray(n[0:8])
    o.extend(n[24:32])
    f = bytes(n[8:24])
    
    logger.info(f"Sector {sector_id}: o={bytes(o).hex()}, f={f.hex()}")
    
    e = cipher_data
    p = bytearray()
    
    if len(e) < 16:
        # Short data: XOR with o
        p = bytearray(xor_bytes_limit(o, e, len(e)))
        # Update o for HMAC: o = e || o[len(e):]
        o_orig = bytes(o)
        o = bytearray(e)
        o.extend(o_orig[len(e):])
    else:
        # Process full/partial blocks
        u = 0
        tail = None
        
        if len(e) % 16 != 0:
            # Has unaligned tail
            u = len(e) % 16
            l = len(e) - 16 - u
            tail = e[l:]
            e = e[:l]
        
        if len(e) > 0:
            # CBC decrypt main blocks with IV=f
            cbc = AES.new(key.aes_key, AES.MODE_CBC, f)
            pt = cbc.decrypt(e)
            p.extend(pt)
        
        if tail is not None:
            # Handle unaligned tail (ciphertext stealing)
            # v = last ciphertext block or f if no blocks
            if len(e) > 0:
                v = e[-16:]
            else:
                v = f
            
            # Decrypt first 16 bytes of tail
            b = bytearray(blk.decrypt(tail[:16]))
            # XOR with remaining tail bytes
            y = xor_exact(bytes(b[:u]), tail[16:])
            # Construct block: tail[16:] || b[u:]
            g = bytearray(tail[16:])
            g.extend(b[u:])
            # Decrypt with CBC using v as IV
            cbc2 = AES.new(key.aes_key, AES.MODE_CBC, v)
            dec = cbc2.decrypt(bytes(g))
            p.extend(dec)
            p.extend(y)
    
    # Verify HMAC: w = m || uint64(sectorID LE) || o
    sid = bytearray(8)
    tmp = sector_id
    for i in range(8):
        sid[i] = tmp % 256
        tmp //= 256
    
    w = bytes(p) + bytes(sid) + bytes(o)
    mac = hmac.new(key.hmac_key, w, sha512)
    sum_bytes = mac.digest()
    
    logger.info(f"Sector {sector_id}: plaintext_len={len(p)}, plaintext_preview={bytes(p)[:32].hex()}...")
    logger.info(f"Sector {sector_id}: o_final={bytes(o).hex()}, sid={bytes(sid).hex()}")
    logger.info(f"Sector {sector_id}: w_len={len(w)}, w_preview={w[:32].hex()}...")
    logger.info(f"Sector {sector_id}: computed_mac={sum_bytes[:16].hex()}, expected_f={f.hex()}")
    
    if not hmac.compare_digest(sum_bytes[:16], f):
        raise ValueError("sector auth compare fail")
    
    return bytes(p)


def decrypt_file_contents(encrypted_data: bytes, file_key: FolderKey) -> bytes:
    """Decrypt encrypted file data using sector-based decryption."""
    offs = compute_cipher_offsets(len(encrypted_data))
    
    if offs.plain_size < 0 or offs.sectors < 0:
        raise ValueError(f"invalid offsets for size={len(encrypted_data)}")
    
    out = bytearray()
    sector = 0
    
    while sector < offs.sectors:
        # Determine chunk covering up to TREE_SECTORS sectors
        chunk_offset, chunk_end, chunk_length = cipher_download_offset(sector, offs)
        
        if chunk_offset < 0 or chunk_end > len(encrypted_data) or chunk_offset >= chunk_end:
            raise ValueError(f"invalid chunk offsets at sector {sector}")
        
        # Level-0 auth position
        a0_offset, a0_length, a0_authID = auth_sector_offset(sector, 0, offs)
        
        # Number of sectors available from this auth window
        d = a0_length // AUTH_SIZE - a0_authID
        if d <= 0:
            raise ValueError(f"bad auth window d={d} at sector={sector}")
        
        # Data length for this chunk up to first level-0 auth
        p = a0_offset - chunk_offset
        
        # Process up to d sectors in this chunk
        for y in range(d):
            if sector + y >= offs.sectors:
                break
            
            # Compute sector length
            f = SECTOR_SIZE
            if not (a0_offset == SECTOR_SIZE * TREE_SECTORS or y != d - 1):
                f = p - y * SECTOR_SIZE
                if f < 0:
                    raise ValueError(f"negative sector length at sector={sector + y}")
            
            data_start = chunk_offset + y * SECTOR_SIZE
            data_end = data_start + f
            
            if data_start < 0 or data_end > len(encrypted_data):
                raise ValueError(f"data slice OOB sector={sector + y}")
            
            c = encrypted_data[data_start:data_end]
            
            # Auth record for this sector at level 0
            auth_start = a0_offset + (a0_authID + y) * AUTH_SIZE
            auth_end = auth_start + AUTH_SIZE
            
            if auth_end > len(encrypted_data):
                raise ValueError(f"auth slice OOB sector={sector + y}")
            
            h = encrypted_data[auth_start:auth_end]
            
            pt = decrypt_sector(file_key, c, h, sector + y)
            out.extend(pt)
        
        sector += TREE_SECTORS
    
    # Truncate to exact plain size
    if len(out) > offs.plain_size:
        out = out[:offs.plain_size]
    
    return bytes(out)
