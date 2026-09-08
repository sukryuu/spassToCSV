import base64
import binascii
import csv
import hashlib
import os
import sys
from getpass import getpass
from io import StringIO

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

VERSION = "2026-06-13-4"
NULL_MARKER = "&&&NULL&&&"

BITWARDEN_HEADERS = [
    "folder",
    "favorite",
    "type",
    "name",
    "notes",
    "fields",
    "reprompt",
    "login_uri",
    "login_username",
    "login_password",
    "login_totp",
]

URL_KEYS = {"origin_url", "host_url", "url", "site"}
USERNAME_KEYS = {"username_value", "username", "user_id", "email"}
PASSWORD_KEYS = {"password_value", "password"}
NAME_KEYS = {"name", "title", "site_name"}
NOTE_KEYS = {"note", "memo", "note_detail"}
TOTP_KEYS = {"totp", "otp_secret", "otpauth"}


def decrypt_spass(file_path, password):
    with open(file_path, "rb") as f:
        raw_data = f.read()

    decoded = base64.b64decode(raw_data.strip())

    if len(decoded) < 36:
        raise ValueError("Decoded data is too short (minimum 36 bytes required)")

    salt = decoded[:20]
    iv = decoded[20:36]
    ciphertext = decoded[36:]

    key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        dklen=32,
        iterations=70_000,
    )

    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    plaintext_padded = cipher.decrypt(ciphertext)
    plaintext = unpad(plaintext_padded, AES.block_size)

    return plaintext.decode("utf-8")


def decode_field(value):
    if not value:
        return ""

    if NULL_MARKER in value:
        return ""

    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True)
        text = decoded.decode("utf-8")

        if NULL_MARKER in text:
            return ""

        if text and all(c.isprintable() or c.isspace() for c in text):
            return text
    except (binascii.Error, UnicodeDecodeError):
        pass

    return value


def parse_spass_payload(payload):
    lines = [line.strip("\r") for line in payload.splitlines()]
    table_chunks = []
    current_chunk = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "next_table":
            if current_chunk:
                table_chunks.append(current_chunk)
            current_chunk = []
            continue
        if not current_chunk and ";" not in stripped:
            continue
        current_chunk.append(stripped)

    if current_chunk:
        table_chunks.append(current_chunk)

    all_records = []

    for chunk in table_chunks:
        reader = csv.reader(StringIO("\n".join(chunk)), delimiter=";")
        rows = list(reader)

        if not rows:
            continue

        raw_headers = [field.strip() for field in rows[0]]
        headers = []

        for index, header in enumerate(raw_headers, start=1):
            decoded_header = decode_field(header)
            if not decoded_header:
                decoded_header = f"column_{index}"
            headers.append(decoded_header)

        for fields in rows[1:]:
            padded_fields = fields + [""] * (len(headers) - len(fields))
            record = {}

            for header, field in zip(headers, padded_fields):
                record[header] = decode_field(field.strip())

            all_records.append(record)

    return all_records


def extract_value(record, keys):
    for key in keys:
        if key in record and record[key]:
            return record[key]
    return ""


def map_to_bitwarden(records):
    bw_records = []

    for record in records:
        name = extract_value(record, NAME_KEYS)
        url = extract_value(record, URL_KEYS)
        username = extract_value(record, USERNAME_KEYS)
        password = extract_value(record, PASSWORD_KEYS)
        note = extract_value(record, NOTE_KEYS)
        totp = extract_value(record, TOTP_KEYS)

        if not name and url:
            name = url

        if not name and not url and not username and not password:
            continue

        bw_record = {
            "folder": "",
            "favorite": "",
            "type": "login",
            "name": name,
            "notes": note,
            "fields": "",
            "reprompt": "0",
            "login_uri": url,
            "login_username": username,
            "login_password": password,
            "login_totp": totp,
        }
        bw_records.append(bw_record)

    return bw_records


def export_to_csv(records, output_path):
    if not records:
        print("No records to export.")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BITWARDEN_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    print(f"{len(records)} records exported to '{output_path}'")


def main():
    print(f"spass_decryptor {VERSION}")

    if len(sys.argv) < 2:
        print("Usage: python spass_to_bitwarden.py <input.spass> [output.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else "bw_password.csv"

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)

    password = getpass("Enter Samsung Pass password: ")

    try:
        payload = decrypt_spass(input_file, password)

        if os.environ.get("SPASS_DEBUG"):
            with open("debug_payload.txt", "w", encoding="utf-8") as f:
                f.write(payload)
            print("Debug payload written to debug_payload.txt")

        raw_records = parse_spass_payload(payload)
        bw_records = map_to_bitwarden(raw_records)
        export_to_csv(bw_records, output_file)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
